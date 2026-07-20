import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
from io import BytesIO
import numpy as np

class CLIPWrapper:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        import os
        import gc
        
        # Limit PyTorch threads to reduce memory overhead
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        
        print(f"Loading CLIP model: {model_name}...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_render = os.environ.get("RENDER") == "true"
        
        if self.is_render:
            from transformers import CLIPTextModelWithProjection
            print("Render environment detected. Loading ONLY the text model to save RAM...")
            
            # On Render, the buildCommand extracts the text model to ./text_model
            # Loading from here avoids downloading the 600MB safetensors file into memory
            render_model_path = "./text_model"
            if os.path.exists(render_model_path):
                self.model = CLIPTextModelWithProjection.from_pretrained(
                    render_model_path, 
                    local_files_only=True, 
                    low_cpu_mem_usage=True
                ).to(self.device)
                self.processor = CLIPProcessor.from_pretrained(
                    render_model_path, 
                    local_files_only=True
                )
            else:
                print("Warning: ./text_model not found. Falling back to downloading from Hugging Face...")
                self.model = CLIPTextModelWithProjection.from_pretrained(model_name).to(self.device)
                self.processor = CLIPProcessor.from_pretrained(model_name)
        else:
            # Load the model
            model = CLIPModel.from_pretrained(model_name)
            self.model = model.to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
        
        gc.collect()
        print("CLIP model loaded successfully.")

    def get_image_embedding(self, image_url):
        if self.is_render:
            print(f"Skipping image embedding for {image_url} on Render (vision disabled).")
            return np.zeros(512).tolist()
            
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
            if self.is_render:
                outputs = self.model(**inputs)
                text_features = outputs.text_embeds
            else:
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
