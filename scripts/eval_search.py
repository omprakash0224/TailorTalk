import os
import sys
from glob import glob

# Add src to python path so we can import from it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.qdrant_store import query_similar

def evaluate_search():
    eval_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'eval_queries')
    
    if not os.path.exists(eval_dir):
        print(f"Eval directory not found: {eval_dir}")
        return
        
    image_paths = glob(os.path.join(eval_dir, "*.jpg"))
    image_paths.extend(glob(os.path.join(eval_dir, "*.webp")))
    
    if not image_paths:
        print(f"No images found in {eval_dir} to evaluate.")
        return
        
    print(f"Found {len(image_paths)} images for evaluation. Starting...\n")
    
    for i, img_path in enumerate(image_paths, 1):
        filename = os.path.basename(img_path)
        print(f"--- Query {i}/{len(image_paths)}: {filename} ---")
        
        try:
            results = query_similar(img_path, top_k=5)
            
            for j, match in enumerate(results, 1):
                print(f"  {j}. [Score: {match.score:0.1f}%] {match.sku} - {match.name}")
        except Exception as e:
            print(f"  Error evaluating {filename}: {e}")
            
        print("\n")

if __name__ == "__main__":
    evaluate_search()
