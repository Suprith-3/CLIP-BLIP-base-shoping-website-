import json
import random
import os
from PIL import Image

def fallback_synthetic_generation(output_path='data/synthetic_products.json'):
    random.seed(42) # For reproducibility
    
    categories = {
        "Clothing": ["T-Shirts", "Shirts", "Jeans", "Jackets"],
        "Footwear": ["Running Shoes", "Sneakers", "Boots"],
        "Electronics": ["Phones", "Laptops", "Headphones", "Smartwatches"],
        "Accessories": ["Watches", "Belts", "Bags", "Sunglasses"],
        "Sports": ["Water Bottles", "Yoga Mats", "Dumbbells", "Resistance Bands"]
    }

    products = []
    pid = 1

    # Base templates to ensure we get exactly 50 items and satisfy duplication requirements
    clothing_base = [
        ("Classic White T-Shirt", "Clothing", "T-Shirts", "A comfortable and breathable classic white t-shirt made from 100% cotton.", 19.99),
        ("Classic White T-Shirt (V-Neck)", "Clothing", "T-Shirts", "A comfortable classic white v-neck t-shirt.", 19.99),
        ("Classic White Tee", "Clothing", "T-Shirts", "100% cotton classic white tee.", 19.99),
        ("Blue Casual Shirt", "Clothing", "Shirts", "A stylish blue casual shirt perfect for everyday wear.", 39.99),
        ("Slim Fit Blue Shirt", "Clothing", "Shirts", "Slim fit blue casual shirt.", 39.99),
        ("Black Denim Jeans", "Clothing", "Jeans", "Durable black denim jeans with a straight fit.", 49.99),
        ("Blue Slim Jeans", "Clothing", "Jeans", "Stylish blue slim fit jeans.", 59.99),
        ("Leather Moto Jacket", "Clothing", "Jackets", "Premium black leather motorcycle jacket.", 129.99),
        ("Denim Jacket", "Clothing", "Jackets", "Classic blue denim jacket.", 69.99),
        ("Graphic Print T-Shirt", "Clothing", "T-Shirts", "Cotton t-shirt with a cool graphic print.", 24.99),
    ]
    
    footwear_base = [
        ("Pro Running Shoes Red", "Footwear", "Running Shoes", "Lightweight red running shoes for optimal performance.", 89.99),
        ("Pro Running Shoes (Red)", "Footwear", "Running Shoes", "Red running shoes, lightweight.", 89.99),
        ("Casual White Sneakers", "Footwear", "Sneakers", "Everyday casual white sneakers.", 59.99),
        ("Everyday Sneakers White", "Footwear", "Sneakers", "White casual sneakers for everyday use.", 59.99),
        ("Leather Work Boots", "Footwear", "Boots", "Durable leather work boots.", 119.99),
        ("Trail Running Shoes", "Footwear", "Running Shoes", "Tough running shoes for trail running.", 99.99),
        ("Black High-Top Sneakers", "Footwear", "Sneakers", "Classic black high-top sneakers.", 64.99),
        ("Winter Snow Boots", "Footwear", "Boots", "Insulated winter snow boots.", 109.99),
    ]

    electronics_base = [
        ("Smartphone X Pro", "Electronics", "Phones", "Latest generation smartphone with advanced camera.", 999.99),
        ("Smartphone Lite", "Electronics", "Phones", "Budget-friendly smartphone with great battery life.", 499.99),
        ("Ultra Thin Laptop 13\"", "Electronics", "Laptops", "Lightweight 13-inch laptop for professionals.", 1299.99),
        ("Gaming Laptop 15\"", "Electronics", "Laptops", "High-performance gaming laptop with dedicated GPU.", 1599.99),
        ("Wireless Noise-Cancelling Headphones", "Electronics", "Headphones", "Premium over-ear wireless headphones.", 299.99),
        ("True Wireless Earbuds", "Electronics", "Headphones", "Compact wireless earbuds with charging case.", 149.99),
        ("Fitness Smartwatch", "Electronics", "Smartwatches", "Smartwatch with heart rate monitor and GPS.", 199.99),
        ("Premium Smartwatch", "Electronics", "Smartwatches", "Luxury smartwatch with stainless steel band.", 349.99),
        ("Tablet 10\"", "Electronics", "Phones", "10-inch tablet for entertainment and productivity.", 399.99),
        ("Wired Studio Headphones", "Electronics", "Headphones", "Professional grade wired studio headphones.", 179.99),
        ("E-Reader", "Electronics", "Laptops", "E-ink reader for books.", 119.99),
        ("Smart Home Hub", "Electronics", "Phones", "Control center for smart home devices.", 89.99),
    ]

    accessories_base = [
        ("Analog Leather Watch", "Accessories", "Watches", "Classic analog watch with brown leather strap.", 89.99),
        ("Digital Sports Watch", "Accessories", "Watches", "Water-resistant digital sports watch.", 49.99),
        ("Black Leather Belt", "Accessories", "Belts", "Genuine black leather belt.", 34.99),
        ("Brown Reversible Belt", "Accessories", "Belts", "Reversible brown to black leather belt.", 39.99),
        ("Canvas Messenger Bag", "Accessories", "Bags", "Durable canvas messenger bag for work or school.", 59.99),
        ("Leather Tote Bag", "Accessories", "Bags", "Spacious leather tote bag.", 119.99),
        ("Aviator Sunglasses", "Accessories", "Sunglasses", "Classic aviator sunglasses with UV protection.", 29.99),
        ("Wayfarer Sunglasses", "Accessories", "Sunglasses", "Stylish wayfarer sunglasses.", 24.99),
        ("Minimalist Wallet", "Accessories", "Bags", "Slim minimalist leather wallet.", 45.99),
        ("Travel Backpack", "Accessories", "Bags", "Large capacity travel backpack.", 79.99),
    ]

    sports_base = [
        ("Insulated Water Bottle", "Sports", "Water Bottles", "24oz insulated stainless steel water bottle.", 24.99),
        ("Glass Water Bottle", "Sports", "Water Bottles", "Eco-friendly glass water bottle with silicone sleeve.", 19.99),
        ("Non-Slip Yoga Mat", "Sports", "Yoga Mats", "Premium non-slip yoga mat with alignment lines.", 39.99),
        ("Thick Exercise Mat", "Sports", "Yoga Mats", "Extra thick exercise mat for comfort.", 29.99),
        ("Adjustable Dumbbells Set", "Sports", "Dumbbells", "Set of adjustable dumbbells up to 50 lbs.", 199.99),
        ("Hex Dumbbell 10lb", "Sports", "Dumbbells", "Single 10lb rubber hex dumbbell.", 24.99),
        ("Resistance Bands Set", "Sports", "Resistance Bands", "Set of 5 resistance bands with different tension levels.", 19.99),
        ("Fabric Booty Bands", "Sports", "Resistance Bands", "Set of 3 fabric resistance bands for glute workouts.", 14.99),
        ("Jump Rope", "Sports", "Resistance Bands", "Adjustable speed jump rope.", 12.99),
        ("Foam Roller", "Sports", "Yoga Mats", "High-density foam roller for muscle recovery.", 22.99),
    ]

    all_items = clothing_base + footwear_base + electronics_base + accessories_base + sports_base
    
    seed_map = {
        "Classic White T-Shirt (V-Neck)": "white_tee",
        "Classic White Tee": "white_tee",
        "Classic White T-Shirt": "white_tee",
        "Blue Casual Shirt": "blue_shirt",
        "Slim Fit Blue Shirt": "blue_shirt",
        "Pro Running Shoes Red": "red_shoes",
        "Pro Running Shoes (Red)": "red_shoes",
        "Casual White Sneakers": "white_sneakers",
        "Everyday Sneakers White": "white_sneakers",
    }
    
    for base_idx, item in enumerate(all_items, start=1):
        name, cat, subcat, desc, price = item
        if name in seed_map:
            base_seed = seed_map[name]
        else:
            base_seed = f"prod_{base_idx}"
            
        # Variation 1: Base product
        products.append({
            "id": f"p_{pid:03d}",
            "name": name,
            "category": cat,
            "subcategory": subcat,
            "description": desc,
            "price": price,
            "image_url": f"https://picsum.photos/seed/{base_seed}/400/400"
        })
        pid += 1

        # Variation 2: Alternative style (same seed -> duplicate)
        if cat in ["Clothing", "Footwear"]:
            name_alt = f"{name} (Alternative Fit)"
        else:
            name_alt = f"{name} (Alternative Version)"
        products.append({
            "id": f"p_{pid:03d}",
            "name": name_alt,
            "category": cat,
            "subcategory": subcat,
            "description": f"An alternative style of {name}. {desc}",
            "price": price,
            "image_url": f"https://picsum.photos/seed/{base_seed}/400/400"
        })
        pid += 1

        # Variation 3: Premium edition (different seed -> unique)
        products.append({
            "id": f"p_{pid:03d}",
            "name": f"{name} - Premium Edition",
            "category": cat,
            "subcategory": subcat,
            "description": f"A premium high-quality edition of {name}. {desc}",
            "price": round(price * 1.3, 2),
            "image_url": f"https://picsum.photos/seed/{base_seed}_premium/400/400"
        })
        pid += 1

        # Variation 4: Special edition (same seed -> duplicate)
        products.append({
            "id": f"p_{pid:03d}",
            "name": f"Special Edition {name}",
            "category": cat,
            "subcategory": subcat,
            "description": f"Limited special edition of {name}. {desc}",
            "price": round(price * 1.1, 2),
            "image_url": f"https://picsum.photos/seed/{base_seed}/400/400"
        })
        pid += 1

    with open(output_path, 'w') as f:
        json.dump(products, f, indent=4)
        
    print(f"Generated {len(products)} synthetic fallback products and saved to {output_path}")

def generate_synthetic_data(output_path='data/synthetic_products.json'):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    images_dir = 'static/images'
    os.makedirs(images_dir, exist_ok=True)
    
    # Invalidate cache since we are switching datasets
    cache_path = 'data/embeddings_cache.json'
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            print("Removed old embeddings cache to force recomputation.")
        except Exception as e:
            print(f"Failed to remove cache: {e}")
            
    clothing_unique = []
    footwear_unique = []
    personal_care_unique = []
    accessories_unique = []
    sports_unique = []
    
    # 1. Try to load the HF dataset
    try:
        from datasets import load_dataset
        print("Loading ashraq/fashion-product-images-small from Hugging Face...")
        ds = load_dataset("ashraq/fashion-product-images-small", split="train")
        print("Dataset loaded successfully from Hugging Face. Scanning metadata...")
        
        # Optimize scanning by removing the image column during search (avoids decoding all images)
        metadata_ds = ds.remove_columns(["image"])
        
        clothing_indices = []
        footwear_indices = []
        personal_care_indices = []
        accessories_indices = []
        sports_indices = []
        
        for idx, item in enumerate(metadata_ds):
            cat = item.get('masterCategory')
            subcat = item.get('subCategory')
            usage = item.get('usage')
            name = item.get('productDisplayName')
            
            if not name or not cat:
                continue
                
            # 1. Clothing (Apparel)
            if cat == "Apparel" and len(clothing_indices) < 28:
                clothing_indices.append(idx)
            # 2. Footwear (Footwear)
            elif cat == "Footwear" and len(footwear_indices) < 24:
                footwear_indices.append(idx)
            # 3. Personal Care
            elif cat == "Personal Care" and len(personal_care_indices) < 48:
                personal_care_indices.append(idx)
            # 4. Accessories
            elif cat == "Accessories" and len(accessories_indices) < 40:
                accessories_indices.append(idx)
            # 5. Sports (any item where usage is Sports, or contains Sport/Active)
            elif (usage == "Sports" or "Sport" in name or "Active" in name) and len(sports_indices) < 40:
                sports_indices.append(idx)
                
            # Break if we have enough uniques
            if (len(clothing_indices) >= 28 and 
                len(footwear_indices) >= 24 and 
                len(personal_care_indices) >= 48 and 
                len(accessories_indices) >= 40 and 
                len(sports_indices) >= 40):
                break
                
        print(f"Indices found. Fetching full items with images...")
        clothing_unique = [ds[idx] for idx in clothing_indices]
        footwear_unique = [ds[idx] for idx in footwear_indices]
        personal_care_unique = [ds[idx] for idx in personal_care_indices]
        accessories_unique = [ds[idx] for idx in accessories_indices]
        sports_unique = [ds[idx] for idx in sports_indices]
        
    except Exception as e:
        print(f"HuggingFace dataset load failed ({e}). Trying Kaggle dataset...")
        
    # 2. Try to load the Kaggle dataset via kagglehub
    if not clothing_unique:
        try:
            try:
                import kagglehub
            except ImportError:
                print("kagglehub not installed. Installing via pip...")
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "kagglehub"])
                import kagglehub
                
            print("Downloading sahandakramipour/fashion-product-images-small from Kaggle via kagglehub...")
            path = kagglehub.dataset_download("sahandakramipour/fashion-product-images-small")
            print(f"Dataset downloaded/found at: {path}")
            
            import pandas as pd
            styles_path = os.path.join(path, "styles.csv")
            try:
                df = pd.read_csv(styles_path, on_bad_lines='skip')
            except TypeError:
                df = pd.read_csv(styles_path, error_bad_lines=False)
                
            print(f"Loaded styles.csv. Total rows: {len(df)}")
            
            # Map df rows to the dict format expected by our script
            metadata_list = df.to_dict(orient='records')
            cleaned_metadata = []
            for row in metadata_list:
                if pd.isna(row.get('id')) or pd.isna(row.get('productDisplayName')):
                    continue
                row_id = str(int(row['id']))
                item = {
                    'id': row_id,
                    'gender': str(row.get('gender', 'Unisex')),
                    'masterCategory': str(row.get('masterCategory', '')),
                    'subCategory': str(row.get('subCategory', '')),
                    'articleType': str(row.get('articleType', '')),
                    'baseColour': str(row.get('baseColour', 'neutral')),
                    'season': str(row.get('season', '')),
                    'year': row.get('year'),
                    'usage': str(row.get('usage', '')),
                    'productDisplayName': str(row.get('productDisplayName', '')),
                    'image': os.path.join(path, "images", f"{row_id}.jpg")
                }
                cleaned_metadata.append(item)
                
            clothing_indices = []
            footwear_indices = []
            personal_care_indices = []
            accessories_indices = []
            sports_indices = []
            
            for idx, item in enumerate(cleaned_metadata):
                cat = item.get('masterCategory')
                name = item.get('productDisplayName')
                usage = item.get('usage')
                
                # 1. Clothing (Apparel)
                if cat == "Apparel" and len(clothing_indices) < 28:
                    clothing_indices.append(idx)
                # 2. Footwear (Footwear)
                elif cat == "Footwear" and len(footwear_indices) < 24:
                    footwear_indices.append(idx)
                # 3. Personal Care
                elif cat == "Personal Care" and len(personal_care_indices) < 48:
                    personal_care_indices.append(idx)
                # 4. Accessories
                elif cat == "Accessories" and len(accessories_indices) < 40:
                    accessories_indices.append(idx)
                # 5. Sports (any item where usage is Sports, or contains Sport/Active)
                elif (usage == "Sports" or "Sport" in name or "Active" in name) and len(sports_indices) < 40:
                    sports_indices.append(idx)
                    
                # Break if we have enough uniques
                if (len(clothing_indices) >= 28 and 
                    len(footwear_indices) >= 24 and 
                    len(personal_care_indices) >= 48 and 
                    len(accessories_indices) >= 40 and 
                    len(sports_indices) >= 40):
                    break
                    
            clothing_unique = [cleaned_metadata[idx] for idx in clothing_indices]
            footwear_unique = [cleaned_metadata[idx] for idx in footwear_indices]
            personal_care_unique = [cleaned_metadata[idx] for idx in personal_care_indices]
            accessories_unique = [cleaned_metadata[idx] for idx in accessories_indices]
            sports_unique = [cleaned_metadata[idx] for idx in sports_indices]
            
        except Exception as ke:
            print(f"Kaggle dataset load failed ({ke}).")

    # 3. Build products if either method succeeded
    if clothing_unique:
        try:
            products = []
            pid = 1
            
            sports_ids = set(item['id'] for item in sports_unique)
            
            def add_product(item, name_override=None):
                nonlocal pid
                p_id = f"p_{pid:03d}"
                
                # Save PIL Image locally
                img = item['image']
                if not isinstance(img, Image.Image):
                    img = Image.open(img)
                    
                img_filename = f"{p_id}.jpg"
                img_path = os.path.join(images_dir, img_filename)
                img.convert('RGB').save(img_path, 'JPEG')
                
                # Determine Category
                cat_map = {
                    "Apparel": "Clothing",
                    "Footwear": "Footwear",
                    "Personal Care": "Personal Care",
                    "Accessories": "Accessories"
                }
                category = cat_map.get(item['masterCategory'], "Sports")
                if item['id'] in sports_ids:
                    category = "Sports"
                    
                desc = f"A stylish {item.get('baseColour', 'neutral')} {item.get('articleType', 'item')} designed for {item.get('gender', 'Unisex')}. Ideal for {item.get('usage', 'casual')} wear."
                name = name_override if name_override else item['productDisplayName']
                price = round(random.uniform(15.0, 150.0), 2)
                if category == "Personal Care":
                    price = round(random.uniform(10.0, 80.0), 2)
                elif category == "Footwear":
                    price = round(random.uniform(50.0, 200.0), 2)
                    
                products.append({
                    "id": p_id,
                    "name": name,
                    "category": category,
                    "subcategory": item.get('subCategory', item.get('articleType', 'General')),
                    "description": desc,
                    "price": price,
                    "image_url": f"/static/images/{img_filename}"
                })
                pid += 1

            # Add Clothing (28 unique + 12 duplicates)
            for item in clothing_unique:
                add_product(item)
            dup_clothing = clothing_unique[:12]
            dup_names = [
                f"{dup_clothing[0]['productDisplayName']} (Alternative Fit)",
                f"{dup_clothing[1]['productDisplayName']} - Premium Edition",
                f"Classic {dup_clothing[2]['productDisplayName']}",
                f"{dup_clothing[3]['productDisplayName']} (Slim Fit)",
                f"{dup_clothing[4]['productDisplayName']} - Athletic Cut",
                f"Urban {dup_clothing[5]['productDisplayName']}",
                f"{dup_clothing[6]['productDisplayName']} (Comfort Fit)",
                f"{dup_clothing[7]['productDisplayName']} - Limited Edition",
                f"Vintage {dup_clothing[8]['productDisplayName']}",
                f"{dup_clothing[9]['productDisplayName']} (Relaxed Fit)",
                f"{dup_clothing[10]['productDisplayName']} - Gold Edition",
                f"Eco-friendly {dup_clothing[11]['productDisplayName']}"
            ]
            for item, name in zip(dup_clothing, dup_names):
                add_product(item, name_override=name)
                
            # Add Footwear (24 unique + 8 duplicates)
            for item in footwear_unique:
                add_product(item)
            dup_footwear = footwear_unique[:8]
            dup_footwear_names = [
                f"{dup_footwear[0]['productDisplayName']} (Special Edition)",
                f"{dup_footwear[1]['productDisplayName']} - Blue Accent",
                f"{dup_footwear[2]['productDisplayName']} (Waterproof)",
                f"{dup_footwear[3]['productDisplayName']} - Lite Version",
                f"Premium {dup_footwear[4]['productDisplayName']}",
                f"{dup_footwear[5]['productDisplayName']} - Red Striped",
                f"{dup_footwear[6]['productDisplayName']} (Orthotic Support)",
                f"{dup_footwear[7]['productDisplayName']} - Breathable Mesh"
            ]
            for item, name in zip(dup_footwear, dup_footwear_names):
                add_product(item, name_override=name)
                
            # Add Personal Care (48 unique)
            for item in personal_care_unique:
                add_product(item)
                
            # Add Accessories (40 unique)
            for item in accessories_unique:
                add_product(item)
                
            # Add Sports (40 unique)
            for item in sports_unique:
                add_product(item)
                
            with open(output_path, 'w') as f:
                json.dump(products, f, indent=4)
            print(f"Generated {len(products)} products from fashion dataset and saved to {output_path}")
            
        except Exception as e:
            print(f"Failed to extract and save products ({e}). Falling back to synthetic mock generation...")
            fallback_synthetic_generation(output_path)
            
    else:
        print("No real dataset could be loaded. Falling back to synthetic mock generation...")
        fallback_synthetic_generation(output_path)

if __name__ == "__main__":
    generate_synthetic_data()
