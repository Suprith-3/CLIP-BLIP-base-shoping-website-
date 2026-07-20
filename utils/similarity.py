import numpy as np
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity_matrix(embeddings):
    """
    Calculates the pairwise cosine similarity matrix for a list of embeddings.
    """
    if not embeddings:
        return np.array([])
    X = np.array(embeddings, dtype=np.float32)
    return cosine_similarity(X)

def cluster_duplicates(similarity_matrix, ids, threshold=0.90):
    """
    Clusters products based on the similarity matrix and threshold.
    Returns:
    - clusters: list of lists of IDs.
    - unique_ids: one representative ID from each cluster.
    """
    n = len(ids)
    visited = set()
    clusters = []
    
    for i in range(n):
        if ids[i] in visited:
            continue
            
        # Find all items similar to item i
        current_cluster = []
        for j in range(n):
            if similarity_matrix[i][j] >= threshold:
                current_cluster.append(ids[j])
                visited.add(ids[j])
                
        clusters.append(current_cluster)
        
    unique_ids = [c[0] for c in clusters if len(c) > 0]
    return clusters, unique_ids

def compute_tsne(embeddings, n_components=2, perplexity=10):
    """
    Computes t-SNE projection for the embeddings.
    """
    if not embeddings or len(embeddings) < perplexity:
        # Fallback if too few embeddings (though we should have 200)
        return [[0.0, 0.0] for _ in embeddings]
        
    X = np.array(embeddings, dtype=np.float32)
    tsne = TSNE(n_components=n_components, perplexity=perplexity, random_state=42, init='pca')
    X_embedded = tsne.fit_transform(X)
    return X_embedded.tolist()
