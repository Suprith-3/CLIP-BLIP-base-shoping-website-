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

# --- Orders and Checkout Endpoints ---
ORDERS_FILE = 'data/orders.json'

# Load environment variables manually
def load_env():
    for env_file in ['.env', 'razorpay.env']:
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if '=' in line and not line.startswith('#'):
                            k, v = line.strip().split('=', 1)
                            os.environ[k.strip()] = v.strip()
                print(f"Loaded environment variables from {env_file}")
            except Exception as e:
                print(f"Error loading {env_file}: {e}")

load_env()

# Razorpay Keys
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

# Initialize Razorpay Client dynamically
RAZORPAY_CLIENT = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        import razorpay
        RAZORPAY_CLIENT = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        print("Razorpay client initialized successfully!")
    except ImportError:
        print("WARNING: 'razorpay' package not found. Running in simulated fallback mode.")
    except Exception as e:
        print(f"Error initializing Razorpay client: {e}")
else:
    print("WARNING: Razorpay keys are missing from environment. Checkout will run in simulated fallback mode.")

def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading orders: {e}")
            return []
    return []

def save_orders(orders):
    try:
        os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=4)
    except Exception as e:
        print(f"Error saving orders: {e}")

def get_order_status_info(order):
    created_at = order['created_at']
    multiplier = order.get('delivery_speed_multiplier', 1.0)
    elapsed = (time.time() - created_at) * multiplier
    
    stages = [
        {"name": "Order Placed", "desc": "We have received your order.", "time_offset": 0},
        {"name": "Preparing & Packaging", "desc": "Your items are being packed at our warehouse.", "time_offset": 15},
        {"name": "Shipped", "desc": "Package is in transit with our delivery partner.", "time_offset": 45},
        {"name": "Out for Delivery", "desc": "Delivery agent Rahul Sharma is on the way.", "time_offset": 90},
        {"name": "Delivered", "desc": "Package delivered successfully.", "time_offset": 120}
    ]
    
    manual = order.get('manual_status')
    current_stage_idx = 0
    if manual:
        for i, stage in enumerate(stages):
            if stage['name'].lower() == manual.lower():
                current_stage_idx = i
                break
    else:
        for i, stage in enumerate(stages):
            if elapsed >= stage['time_offset']:
                current_stage_idx = i
                
    stages_response = []
    for i, stage in enumerate(stages):
        status = 'pending'
        if i < current_stage_idx:
            status = 'completed'
        elif i == current_stage_idx:
            status = 'active'
            
        # Realistic timestamp mapping
        time_str = '--:--:--'
        if i <= current_stage_idx:
            offset_seconds = stage['time_offset'] / multiplier
            stage_time = created_at + offset_seconds
            time_str = time.strftime('%I:%M:%S %p', time.localtime(stage_time))
            
        stages_response.append({
            "name": stage['name'],
            "desc": stage['desc'],
            "status": status,
            "time_str": time_str
        })
        
    eta_seconds = max(0, (120 - elapsed) / multiplier)
    eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s remaining" if eta_seconds > 0 else "Delivered"
    if current_stage_idx == len(stages) - 1:
        eta_str = "Delivered"
        
    # Mock Delivery Agent details
    delivery_agent = {
        "name": "Rahul Sharma",
        "phone": "+91 98765 43210",
        "vehicle": "Hero Splendor (DL 3S CE 4812)",
        "rating": "4.9 ★"
    }
    
    return {
        "status": stages[current_stage_idx]['name'],
        "stage_index": current_stage_idx,
        "stages": stages_response,
        "eta": eta_str,
        "elapsed": elapsed,
        "delivery_agent": delivery_agent
    }

@app.route('/api/orders', methods=['GET', 'POST'])
def handle_orders():
    orders = load_orders()
    
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Validate required fields
        required = ['items', 'shipping_address', 'payment_method', 'total_amount']
        for r in required:
            if r not in data:
                return jsonify({"error": f"Missing required field: {r}"}), 400
                
        import random
        order_id = f"ORD-{int(time.time())}{random.randint(10, 99)}"
        
        # Payment setup
        payment_status = 'Pending'
        rzp_order_id = None
        payment_method = data['payment_method']
        
        if payment_method == 'online':
            if RAZORPAY_CLIENT:
                try:
                    amount_paise = int(float(data['total_amount']) * 100)
                    rzp_order = RAZORPAY_CLIENT.order.create({
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": order_id,
                        "payment_capture": 1
                    })
                    rzp_order_id = rzp_order['id']
                except Exception as e:
                    print(f"Error creating Razorpay order: {e}")
                    return jsonify({"error": f"Razorpay order creation failed: {str(e)}"}), 500
            else:
                # Fallback mock order ID
                rzp_order_id = f"order_mock_{int(time.time())}"
        
        new_order = {
            "id": order_id,
            "items": data['items'],
            "shipping_address": data['shipping_address'],
            "payment_method": payment_method,
            "payment_status": payment_status,
            "total_amount": float(data['total_amount']),
            "created_at": time.time(),
            "delivery_speed_multiplier": 1.0,
            "manual_status": None,
            "razorpay_order_id": rzp_order_id
        }
        
        orders.append(new_order)
        save_orders(orders)
        
        return jsonify({
            "success": True,
            "order": {
                "id": new_order['id'],
                "total_amount": new_order['total_amount'],
                "payment_method": new_order['payment_method'],
                "payment_status": new_order['payment_status'],
                "razorpay_order_id": rzp_order_id,
                "razorpay_key_id": RAZORPAY_KEY_ID
            }
        })
        
    else:
        # GET - return all orders with their current simulated status
        orders_with_status = []
        for o in orders:
            status_info = get_order_status_info(o)
            orders_with_status.append({
                "id": o['id'],
                "items": o['items'],
                "shipping_address": o['shipping_address'],
                "payment_method": o['payment_method'],
                "payment_status": o['payment_status'],
                "total_amount": o['total_amount'],
                "created_at": o['created_at'],
                "status": status_info['status'],
                "stage_index": status_info['stage_index'],
                "eta": status_info['eta']
            })
        # Return newest first
        orders_with_status.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify(orders_with_status)

@app.route('/api/orders/verify', methods=['POST'])
def verify_order_payment():
    data = request.json or {}
    required = ['order_id', 'razorpay_payment_id', 'razorpay_signature']
    
    for r in required:
        if r not in data:
            return jsonify({"error": f"Missing required verification field: {r}"}), 400
            
    orders = load_orders()
    order = next((o for o in orders if o['id'] == data['order_id']), None)
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    verified = False
    
    if RAZORPAY_CLIENT and order.get('razorpay_order_id') and not order.get('razorpay_order_id').startswith('order_mock_'):
        try:
            params_dict = {
                'razorpay_order_id': order['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            }
            RAZORPAY_CLIENT.utility.verify_payment_signature(params_dict)
            verified = True
        except Exception as e:
            print(f"Razorpay payment verification failed: {e}")
            verified = False
    else:
        # Fallback simulated verification
        print("Using simulated validation for verification (razorpay package missing or mock order id)")
        verified = True
        
    if verified:
        order['payment_status'] = 'Paid'
        save_orders(orders)
        return jsonify({"success": True, "message": "Payment verified successfully!"})
    else:
        return jsonify({"error": "Invalid signature. Payment verification failed."}), 400

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_details(order_id):
    orders = load_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    status_info = get_order_status_info(order)
    response_data = {
        "id": order['id'],
        "items": order['items'],
        "shipping_address": order['shipping_address'],
        "payment_method": order['payment_method'],
        "payment_status": order['payment_status'],
        "total_amount": order['total_amount'],
        "created_at": order['created_at'],
        "delivery_speed_multiplier": order.get('delivery_speed_multiplier', 1.0),
        "manual_status": order.get('manual_status'),
        "tracking": status_info
    }
    return jsonify(response_data)

@app.route('/api/orders/<order_id>/advance', methods=['POST'])
def advance_order_status(order_id):
    orders = load_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    data = request.json or {}
    
    # Can set speed multiplier or direct manual status
    if 'multiplier' in data:
        order['delivery_speed_multiplier'] = float(data['multiplier'])
    
    if 'status' in data:
        order['manual_status'] = data['status']
        
    save_orders(orders)
    status_info = get_order_status_info(order)
    return jsonify({
        "success": True,
        "status": status_info['status'],
        "stage_index": status_info['stage_index'],
        "eta": status_info['eta']
    })

# Initialize the system on import so it's ready for WSGI servers like Gunicorn
init_system()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
