import os
from transformers import CLIPTextModelWithProjection, CLIPProcessor

def main():
    model_name = "openai/clip-vit-base-patch32"
    save_path = "./text_model"
    
    if os.path.exists(save_path):
        print(f"Text model already exists at {save_path}")
        return
        
    print(f"Downloading and extracting text model from {model_name}...")
    model = CLIPTextModelWithProjection.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)
    
    print(f"Saving text model to {save_path}...")
    model.save_pretrained(save_path)
    processor.save_pretrained(save_path)
    print("Text model extraction complete!")

if __name__ == "__main__":
    main()
