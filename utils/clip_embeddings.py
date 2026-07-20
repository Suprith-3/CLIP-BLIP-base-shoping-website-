import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
from io import BytesIO
import numpy as np

class CLIPWrapper:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        print(f"Loading CLIP model: {model_name}...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        print("CLIP model loaded.")

    def get_image_embedding(self, image_url):
        try:
            if image_url.startswith('http'):
                response = requests.get(image_url)
                image = Image.open(BytesIO(response.content)).convert("RGB")
            else:
                # Local path e.g. '/static/images/p_001.jpg'
                local_path = image_url.lstrip('/')
                image = Image.open(local_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Extract tensor from wrapper if necessary (transformers >= 5.0)
            if hasattr(image_features, "pooler_output"):
                image_features = image_features.pooler_output
            elif hasattr(image_features, "last_hidden_state"):
                image_features = image_features.last_hidden_state
                
            # Normalize embedding
            embedding = image_features.cpu().numpy()[0]
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.tolist()
        except Exception as e:
            print(f"Error processing image {image_url}: {e}")
            # Return a zero vector as fallback
            return np.zeros(512).tolist()

    def get_text_embedding(self, text):
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            
        # Extract tensor from wrapper if necessary (transformers >= 5.0)
        if hasattr(text_features, "pooler_output"):
            text_features = text_features.pooler_output
        elif hasattr(text_features, "last_hidden_state"):
            text_features = text_features.last_hidden_state
            
        # Normalize embedding
        embedding = text_features.cpu().numpy()[0]
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()
