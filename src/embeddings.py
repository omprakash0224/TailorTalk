import os
import cv2
import numpy as np
from PIL import Image
import google.generativeai as genai

# Note: GEMINI_API_KEY must be set in the environment before calling this.
# You can use genai.configure(api_key=...) if you prefer explicit configuration.
# The SDK automatically picks up GEMINI_API_KEY from os.environ.

import time
from google.api_core.exceptions import ResourceExhausted

def embed_image_gemini(image_path: str, max_retries=5) -> np.ndarray:
    """
    Calls gemini-embedding-2-preview with task type RETRIEVAL_DOCUMENT, 
    returns 3072-dim L2-normalized vector. Includes retry logic for rate limits.
    """
    img = Image.open(image_path)
    
    for attempt in range(max_retries):
        try:
            response = genai.embed_content(
                model="models/gemini-embedding-2-preview",
                content=img,
                task_type="RETRIEVAL_DOCUMENT"
            )
            vector = response['embedding']
            
            # Ensure L2 normalization
            vec_np = np.array(vector, dtype=np.float32)
            norm = np.linalg.norm(vec_np)
            if norm > 0:
                vec_np = vec_np / norm
            return vec_np
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota exceeded" in error_str or isinstance(e, ResourceExhausted):
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    print(f"Rate limit hit for Gemini API. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    raise ValueError(f"Failed to embed image via Gemini (Rate Limit Max Retries Reached): {e}")
            else:
                raise ValueError(f"Failed to embed image via Gemini: {e}")

def compute_color_histogram(image_path: str) -> np.ndarray:
    """
    HSV histogram (32 bins x 3 channels = 96-dim), L2-normalized.
    """
    # OpenCV loads images in BGR format
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Image not found or corrupt: {image_path}")
        
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Calculate histograms for H, S, V channels
    # 32 bins per channel
    hist_h = cv2.calcHist([img_hsv], [0], None, [32], [0, 180])
    hist_s = cv2.calcHist([img_hsv], [1], None, [32], [0, 256])
    hist_v = cv2.calcHist([img_hsv], [2], None, [32], [0, 256])
    
    # Concatenate to a 96-dim vector
    hist_concat = np.concatenate((hist_h, hist_s, hist_v)).flatten()
    
    # L2 normalize
    norm = np.linalg.norm(hist_concat)
    if norm > 0:
        hist_concat = hist_concat / norm
        
    return hist_concat.astype(np.float32)
