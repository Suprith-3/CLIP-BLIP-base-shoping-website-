import faiss
import numpy as np

class FAISSIndex:
    def __init__(self, dimension=512):
        self.dimension = dimension
        # Using IndexFlatIP since embeddings are normalized (Cosine Similarity = Inner Product)
        self.index = faiss.IndexFlatIP(dimension)
        self.id_map = [] # To map faiss integer indices back to string product IDs

    def build_index(self, products):
        """
        Builds the FAISS index from a list of product dictionaries containing 'id' and 'embedding'.
        """
        self.index.reset()
        self.id_map = []
        
        vectors = []
        for p in products:
            emb = np.array(p['embedding'], dtype=np.float32)
            vectors.append(emb)
            self.id_map.append(p['id'])
            
        if vectors:
            vectors_np = np.vstack(vectors)
            self.index.add(vectors_np)
            print(f"FAISS index built with {self.index.ntotal} vectors.")
        else:
            print("No vectors to build index.")

    def search(self, query_embedding, k=5):
        """
        Searches the index for the top k closest vectors to query_embedding.
        Returns a list of tuples: (product_id, similarity_score)
        """
        if self.index.ntotal == 0:
            return []
            
        q = np.array([query_embedding], dtype=np.float32)
        # distances for IndexFlatIP with normalized vectors are cosine similarities
        distances, indices = self.index.search(q, k)
        
        results = []
        for j in range(len(indices[0])):
            idx = indices[0][j]
            if idx != -1 and idx < len(self.id_map):
                score = float(distances[0][j])
                p_id = self.id_map[idx]
                results.append((p_id, score))
                
        return results
