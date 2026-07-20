import json
import os
import time
from flask import Flask, render_template, request, jsonify
from utils.data_generator import generate_synthetic_data
from utils.clip_embeddings import CLIPWrapper
from utils.faiss_index import FAISSIndex
from utils.similarity import calculate_similarity_matrix, cluster_duplicates, compute_tsne

app = Flask(__name__)

# Global state
PRODUCTS = []
PRODUCT_DICT = {}
CLIP_MODEL = None
FAISS_IDX = None
TSNE_COORDS = []

# Complementary category mappings for Task 1
COMPLEMENTARY_MAP = {
    "Phones": ["Cases", "Headphones", "Smartwatches"],
    "Laptops": ["Bags", "Headphones"],
    "T-Shirts": ["Jeans", "Jackets", "Sneakers"],
    "Shirts": ["Jeans", "Watches", "Belts"],
    "Jeans": ["T-Shirts", "Shirts", "Sneakers", "Belts"],
    "Jackets": ["T-Shirts", "Jeans", "Boots"],
    "Running Shoes": ["Water Bottles", "Smartwatches"],
    "Sneakers": ["T-Shirts", "Jeans"],
    "Boots": ["Jackets", "Jeans"],
    "Watches": ["Shirts"],
    "Belts": ["Jeans", "Shirts"],
    "Bags": ["Laptops", "Sunglasses"],
    "Sunglasses": ["T-Shirts", "Bags"],
    "Water Bottles": ["Running Shoes", "Yoga Mats", "Dumbbells"],
    "Yoga Mats": ["Water Bottles", "Resistance Bands"],
    "Dumbbells": ["Water Bottles", "Resistance Bands"],
    "Resistance Bands": ["Yoga Mats", "Dumbbells"],
    "Headphones": ["Phones", "Laptops"]
}

def init_system():
    global PRODUCTS, PRODUCT_DICT, CLIP_MODEL, FAISS_IDX, TSNE_COORDS
    
    # Copy logo.jpg to static/images/logo.jpg if it exists
    try:
        import shutil
        os.makedirs('static/images', exist_ok=True)
        if os.path.exists('logo.jpg'):
            shutil.copy('logo.jpg', 'static/images/logo.jpg')
            print("Successfully copied logo.jpg to static/images/logo.jpg")
    except Exception as e:
        print(f"Error copying logo.jpg: {e}")
        
    data_path = 'data/synthetic_products.json'
    embeddings_path = 'data/embeddings_cache.json'
    
    # 1. Ensure data exists and is up to date
    if os.path.exists(data_path):
        try:
            with open(data_path, 'r') as f:
                temp_data = json.load(f)
            needs_regen = False
            if not temp_data or len(temp_data) != 200:
                print(f"Dataset size is {len(temp_data) if temp_data else 0}, expected 200. Forcing regeneration...")
                needs_regen = True
            elif temp_data and len(temp_data) > 0 and "picsum.photos" in temp_data[0].get('image_url', ''):
                print("Old picsum dataset detected. Removing and forcing regeneration from Fashion dataset...")
                needs_regen = True
                
            if needs_regen:
                if os.path.exists(data_path):
                    os.remove(data_path)
                if os.path.exists(embeddings_path):
                    os.remove(embeddings_path)
        except Exception as e:
            print(f"Error checking dataset type: {e}")
            
    if not os.path.exists(data_path):
        print("Generating synthetic data from fashion dataset...")
        generate_synthetic_data(data_path)
        
    with open(data_path, 'r') as f:
        PRODUCTS = json.load(f)
        
    for p in PRODUCTS:
        PRODUCT_DICT[p['id']] = p

    # 2. Initialize CLIP
    CLIP_MODEL = CLIPWrapper()
    
    # 3. Compute or Load Embeddings
    embeddings_loaded = False
    if os.path.exists(embeddings_path):
        print("Loading cached embeddings...")
        try:
            with open(embeddings_path, 'r') as f:
                cached_embs = json.load(f)
            # Verify cache matches current products
            if len(cached_embs) == len(PRODUCTS) and all(p['id'] in cached_embs for p in PRODUCTS):
                # Check if embeddings are invalid (e.g. all zeros due to previous failed run)
                first_key = list(cached_embs.keys())[0]
                if all(v == 0.0 for v in cached_embs[first_key]):
                    print("Cached embeddings are invalid (all zeros). Forcing recomputation...")
                    embeddings_loaded = False
                else:
                    for p in PRODUCTS:
                        p['embedding'] = cached_embs[p['id']]
                    embeddings_loaded = True
        except Exception as e:
            print(f"Error loading cache: {e}")
            
    if not embeddings_loaded:
        print("Computing embeddings (this may take a minute)...")
        cached_embs = {}
        for p in PRODUCTS:
            emb = CLIP_MODEL.get_image_embedding(p['image_url'])
            p['embedding'] = emb
            cached_embs[p['id']] = emb
            print(f"Computed for {p['id']}")
            
        with open(embeddings_path, 'w') as f:
            json.dump(cached_embs, f)
            
    # 4. Initialize FAISS
    FAISS_IDX = FAISSIndex()
    FAISS_IDX.build_index(PRODUCTS)
    
    # 5. Precompute baseline t-SNE
    print("Precomputing t-SNE coordinates...")
    embeddings = [p['embedding'] for p in PRODUCTS]
    coords = compute_tsne(embeddings)
    for i, p in enumerate(PRODUCTS):
        p['tsne'] = coords[i]
        
    print("System Initialization Complete.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products')
def get_products():
    # Return products without embeddings to save bandwidth
    safe_products = [{k: v for k, v in p.items() if k != 'embedding'} for p in PRODUCTS]
    return jsonify(safe_products)

@app.route('/api/recommendations/<product_id>')
def get_recommendations(product_id):
    if product_id not in PRODUCT_DICT:
        return jsonify({"error": "Product not found"}), 404
        
    target_product = PRODUCT_DICT[product_id]
    target_subcat = target_product['subcategory']
    target_emb = target_product['embedding']
    
    complementary_subcats = COMPLEMENTARY_MAP.get(target_subcat, [])
    
    # Find all products in complementary subcategories
    candidates = [p for p in PRODUCTS if p['subcategory'] in complementary_subcats and p['id'] != product_id]
    
    if not candidates:
        # Fallback to general FAISS search if no complementary map applies, excluding self
        results = FAISS_IDX.search(target_emb, k=6)
        recommended_ids = [r[0] for r in results if r[0] != product_id][:5]
    else:
        # Rank candidates by embedding similarity to the target product
        # Though they are different categories, CLIP space might group "vibe" or color
        for c in candidates:
            c_emb = c['embedding']
            sim = sum(a*b for a,b in zip(target_emb, c_emb)) # Dot product for normalized vectors
            c['_sim'] = sim
            
        candidates.sort(key=lambda x: x['_sim'], reverse=True)
        recommended_ids = [c['id'] for c in candidates[:5]]
        
    recommended_products = [{k: v for k, v in PRODUCT_DICT[pid].items() if k not in ['embedding', '_sim']} for pid in recommended_ids]
    
    return jsonify({
        "target": {k: v for k, v in target_product.items() if k != 'embedding'},
        "recommendations": recommended_products
    })

@app.route('/api/deduplicate', methods=['POST'])
def deduplicate():
    data = request.json
    threshold = float(data.get('threshold', 0.90))
    
    embeddings = [p['embedding'] for p in PRODUCTS]
    ids = [p['id'] for p in PRODUCTS]
    
    sim_matrix = calculate_similarity_matrix(embeddings)
    clusters, unique_ids = cluster_duplicates(sim_matrix, ids, threshold)
    
    # Prepare response
    cleaned_catalog = [{k: v for k, v in PRODUCT_DICT[pid].items() if k != 'embedding'} for pid in unique_ids]
    
    # Prepare scatter plot data (t-SNE)
    scatter_data = []
    for p in PRODUCTS:
        scatter_data.append({
            "id": p['id'],
            "name": p['name'],
            "category": p['category'],
            "tsne": p['tsne'],
            "is_duplicate": p['id'] not in unique_ids
        })
        
    return jsonify({
        "original_count": len(PRODUCTS),
        "cleaned_count": len(unique_ids),
        "clusters": clusters,
        "cleaned_catalog": cleaned_catalog,
        "scatter_data": scatter_data,
        "similarity_matrix": sim_matrix.tolist()
    })

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"results": []})
        
    start_time = time.time()
    query_emb = CLIP_MODEL.get_text_embedding(query)
    search_results = FAISS_IDX.search(query_emb, k=5)
    
    results = []
    for pid, score in search_results:
        p = PRODUCT_DICT[pid].copy()
        p.pop('embedding', None)
        p['similarity_score'] = score
        results.append(p)
        
    # Get 2D coordinate for query text embedding for viz
    # We use a simple heuristic to place it based on closest neighbors in t-SNE space
    # (Since full t-SNE recompute is slow)
    query_coords = [0, 0]
    if results:
        top_pid = results[0]['id']
        query_coords = PRODUCT_DICT[top_pid]['tsne']
        
    return jsonify({
        "results": results,
        "query_coords": query_coords,
        "time_ms": int((time.time() - start_time) * 1000)
    })

if __name__ == '__main__':
    # Initialize the system before running the server
    init_system()
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
