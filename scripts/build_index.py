import os
import sys
import time
import uuid
import pandas as pd
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from tqdm import tqdm

# Add src to python path so we can import embeddings
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.embeddings import embed_image_gemini, compute_color_histogram
import google.generativeai as genai

# Load environment variables
load_dotenv()

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    print("Warning: QDRANT_URL or QDRANT_API_KEY not found in environment.")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

def main():
    if not QDRANT_URL:
        # Default to local in-memory or a local docker if no URL provided
        # But Qdrant Cloud is requested in Plan
        print("Using local memory Qdrant since QDRANT_URL is not set.")
        client = QdrantClient(":memory:")
    else:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    collection_name = "sarees"
    
    # Create collection if it doesn't exist
    if not client.collection_exists(collection_name):
        print(f"Creating collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "gemini": VectorParams(size=3072, distance=Distance.COSINE),
                "color":  VectorParams(size=96,   distance=Distance.COSINE),
            },
        )
    else:
        print(f"Collection '{collection_name}' already exists.")

    csv_path = "data/byrappa_tejas_31july.csv"
    images_dir = "data/images"
    progress_file = "data/index_progress.log"
    
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df.dropna(subset=['image_url', 'SKU'], inplace=True)
    df.drop_duplicates(subset=['image_url'], inplace=True)
    
    # Read processed SKUs
    processed_skus = set()
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            for line in f:
                processed_skus.add(line.strip())
                
    points = []
    chunk_size = 100
    
    print(f"Total rows: {len(df)}. Processed already: {len(processed_skus)}")
    
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        sku = str(row['SKU']).strip()
        if sku in processed_skus:
            continue
            
        image_path = os.path.join(images_dir, f"{sku}.jpg")
        if not os.path.exists(image_path):
            continue
            
        try:
            # Respect rate limit (1500 RPM for Gemini free tier)
            # A 0.05s delay gives at most 20 requests/sec = 1200 RPM
            time.sleep(0.05)
            
            vec_gemini = embed_image_gemini(image_path)
            vec_color = compute_color_histogram(image_path)
            
            in_stock = True
            if 'Stock' in row and pd.notna(row['Stock']):
                stock_val = str(row['Stock']).strip().lower()
                in_stock = stock_val not in ['0', 'out of stock', 'false', 'no']
            
            payload = {
                "sku": sku,
                "name": str(row.get('Name', '')).strip(),
                "retail_price": float(row.get('Retail Price', 0) if pd.notna(row.get('Retail Price')) else 0),
                "discounted_price": float(row.get('Discounted Price', 0) if pd.notna(row.get('Discounted Price')) else 0),
                "image_url": str(row.get('image_url', '')).strip(),
                "product_url": str(row.get('Website Link', '')).strip(),
                "in_stock": in_stock
            }
            
            # Using deterministic UUID from SKU since Qdrant IDs must be Int or UUID
            point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, sku))
            
            point = PointStruct(
                id=point_id,
                vector={
                    "gemini": vec_gemini.tolist(),
                    "color": vec_color.tolist()
                },
                payload=payload
            )
            points.append((point, sku))
            
            if len(points) >= chunk_size:
                point_structs = [p[0] for p in points]
                skus = [p[1] for p in points]
                client.upsert(
                    collection_name=collection_name,
                    points=point_structs,
                    wait=True
                )
                
                with open(progress_file, "a") as f:
                    for s in skus:
                        f.write(s + "\n")
                
                points = []
                
        except Exception as e:
            print(f"Error processing SKU {sku}: {e}")
            
    # Process remaining points
    if points:
        point_structs = [p[0] for p in points]
        skus = [p[1] for p in points]
        client.upsert(
            collection_name=collection_name,
            points=point_structs,
            wait=True
        )
        with open(progress_file, "a") as f:
            for s in skus:
                f.write(s + "\n")

    if QDRANT_URL:
        count = client.get_collection(collection_name).points_count
        print(f"Index building complete. Total vectors in collection: {count}")
    else:
        print("Finished local in-memory index run.")

if __name__ == "__main__":
    main()
