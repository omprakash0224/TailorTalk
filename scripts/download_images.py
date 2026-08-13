import os
import time
import requests
import pandas as pd
from PIL import Image
from io import BytesIO
import logging

# Setup logging
log_file = "data/download_errors.log"
logging.basicConfig(
    filename=log_file,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def download_image(url, retries=3, timeout=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 TailorTalk-Bot/1.0'
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 404:
                return None, 404
            response.raise_for_status()
            return response.content, response.status_code
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                logging.error(f"Failed to download {url}: {e}")
                return None, str(e)
            time.sleep(1 * (attempt + 1))
    return None, "Max retries exceeded"

def main():
    csv_path = "data/byrappa_tejas_31july.csv"
    output_dir = "data/images"
    
    os.makedirs(output_dir, exist_ok=True)
    
    df = pd.read_csv(csv_path, skipinitialspace=True)
    # Strip whitespace from column names just in case
    df.columns = df.columns.str.strip()
    
    # Drop missing
    initial_count = len(df)
    df.dropna(subset=['image_url', 'SKU'], inplace=True)
    
    # Deduplicate on image_url
    df.drop_duplicates(subset=['image_url'], inplace=True)
    final_count = len(df)
    
    print(f"Loaded CSV. Kept {final_count}/{initial_count} rows after deduplication.")
    
    success_count = 0
    for idx, row in df.iterrows():
        sku = str(row['SKU']).strip()
        url = str(row['image_url']).strip()
        
        output_path = os.path.join(output_dir, f"{sku}.jpg")
        
        if os.path.exists(output_path):
            success_count += 1
            continue
            
        content, status = download_image(url)
        
        if content is None:
            logging.error(f"SKU: {sku} | URL: {url} | Status: {status}")
            continue
            
        try:
            # Convert WEBP to RGB JPEG
            img = Image.open(BytesIO(content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Verify dimensions
            width, height = img.size
            if width == 0 or height == 0:
                logging.error(f"SKU: {sku} | URL: {url} | Status: Invalid dimensions {width}x{height}")
                continue
                
            img.save(output_path, "JPEG")
            
            # Verify file size > 1 KB
            file_size = os.path.getsize(output_path)
            if file_size <= 1024:
                logging.error(f"SKU: {sku} | URL: {url} | Status: File size too small ({file_size} bytes)")
                os.remove(output_path)
                continue
                
            # Verify it opens cleanly
            img_verify = Image.open(output_path)
            img_verify.verify()
            
            success_count += 1
            
        except Exception as e:
            logging.error(f"SKU: {sku} | URL: {url} | Status: Image processing error: {e}")
            
        time.sleep(0.2)
        
        if success_count > 0 and success_count % 100 == 0:
            print(f"Downloaded {success_count}/{final_count} images...")

    print(f"Finished downloading. Successfully saved {success_count}/{final_count} images.")

if __name__ == "__main__":
    main()
