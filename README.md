# CLIP-BLIP Shopping Website 🛍️

A modern, AI-powered e-commerce search and catalog curation system leveraging **OpenAI CLIP (Contrastive Language-Image Pretraining)** and **FAISS (Facebook AI Similarity Search)**. This application demonstrates advanced AI-driven features like semantic search, intelligent complementary product recommendations, t-SNE catalog visualization, and automated catalog deduplication.

---

## 🌟 Key Features

### 1. 🔍 AI-Powered Semantic Search (Text-to-Image / Image-to-Image)
Traditional keyword search fails when users describe "vibes" or abstract styles. By using **CLIP embeddings**, this website enables:
- **Natural Language Search**: Search using phrases like "cozy warm sweater for winter" or "shoes suitable for running in the rain".
- **Visual Similarity Search**: Find visually or stylistically similar items within the catalog.
- **Fast Vector Indexing**: Utilizes **FAISS** to perform nearest-neighbor lookup in milliseconds.

### 2. 👗 Intelligent Complementary Product Recommendations
Instead of recommending identical items, the recommendation engine targets category pairings (e.g., matching laptops with laptop bags and headphones, or shirts with jeans and belts) and ranks them using **CLIP embedding similarity** to ensure matching colors and style vibes.

### 3. 🗺️ Interactive t-SNE Catalog Visualization
Projecting high-dimensional embeddings into a 2D space allows interactive exploration of the catalog.
- Group similar clothing items visually.
- Plot search queries dynamically in relation to matching catalog items.

### 4. 📂 Catalog Deduplication & Curation
Manage catalog clutter with visual deduplication:
- Calculate pairwise cosine similarity across all product images.
- Cluster duplicate or near-duplicate items based on a adjustable similarity threshold.
- Preview a cleaned-up catalog dynamically.

---

## 🏗️ Architecture & Stack

- **Backend**: Flask (Python)
- **Vector Search**: FAISS (Facebook AI Similarity Search)
- **Deep Learning**: PyTorch & HuggingFace Transformers (CLIP model)
- **Dimensionality Reduction**: scikit-learn (t-SNE)
- **Frontend**: HTML5, CSS3 (Vanilla glassmorphism & modern UI), and JavaScript (dynamic API integration, Interactive Chart.js scatter plots)

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Git

### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Suprith-3/CLIP-BLIP-base-shoping-website-.git
   cd CLIP-BLIP-base-shoping-website-
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```
   The application will initialize the CLIP model, generate synthetic product data if not present, cache embeddings (`data/embeddings_cache.json`), and build the FAISS index. Once initialized, access the store at `http://localhost:5000`.

---

## 📂 Project Structure

```text
├── app.py                      # Flask main entrypoint and API routes
├── requirements.txt            # Python dependencies
├── logo.jpg                    # Store Logo
├── data/
│   ├── synthetic_products.json # Generated fashion catalog database (200 items)
│   └── embeddings_cache.json   # Cached CLIP embeddings for instant startup
├── templates/
│   └── index.html              # Main frontend UI
├── static/
│   ├── css/
│   │   └── styles.css          # Premium modern glassmorphic styling
│   ├── js/
│   │   └── app.js              # Frontend logic and API controller
│   └── images/                 # Product catalog images (p_001.jpg - p_200.jpg)
└── utils/
    ├── clip_embeddings.py      # CLIP feature extractor (image and text)
    ├── data_generator.py       # Fashion dataset download & generation helper
    ├── faiss_index.py          # FAISS vector database wrapper
    └── similarity.py           # Similarity matrix, clustering, and t-SNE utils
```

---

## 🛠️ Configuration & Customization
- **Adjust Recommendation Rules**: Modify the `COMPLEMENTARY_MAP` in `app.py` to change which categories recommend each other.
- **Tweak Clustering Threshold**: Change the default threshold inside `static/js/app.js` or directly via the deduplication dashboard slider.
