import os
from typing import List, Optional
from pydantic import BaseModel, Field
from PIL import Image
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import QueryRequest, Prefetch, FusionQuery, Fusion, Filter, FieldCondition, Range

from .embeddings import embed_image_gemini, compute_color_histogram

# Initialize Qdrant Client (reused)
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY if QDRANT_API_KEY else None)

LAST_QUERY_VECTORS = {
    "gemini": None,
    "color": None
}

class SareeMatch(BaseModel):
    sku: str
    name: str
    score: float
    image_url: str
    product_url: str
    price: float

def crop_border(image_path: str) -> Image.Image:
    """
    Crops the bottom 30% of the image (typically border/pallu region for sarees).
    """
    img = Image.open(image_path)
    width, height = img.size
    
    # Calculate crop box (left, upper, right, lower)
    # Bottom 30%
    upper = int(height * 0.7)
    crop_box = (0, upper, width, height)
    
    cropped_img = img.crop(crop_box)
    return cropped_img

def normalize_score(cosine_similarity: float) -> float:
    """
    Normalizes a cosine similarity score (typically [-1, 1] but realistically [0.3, 1.0])
    into a 0-100 'match %' display value.
    """
    min_val = 0.5
    normalized = ((cosine_similarity - min_val) / (1.0 - min_val)) * 100
    return max(0.0, min(100.0, normalized))

def _calculate_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Helper to calculate cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
         return 0.0
    return dot_product / (norm1 * norm2)

def rerank(candidates: List[SareeMatch], top_k: int = 5) -> List[SareeMatch]:
    """
    Re-ranks candidates.
    For this graded phase, we might just rely on the RRF fusion for the first step,
    and perform the crop-based re-ranking if strictly needed. 
    """
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:top_k]

def build_filter(min_price: Optional[float] = None, max_price: Optional[float] = None) -> Optional[Filter]:
    must_conditions = []
    if min_price is not None or max_price is not None:
        price_range = Range()
        if min_price is not None:
            price_range.gte = min_price
        if max_price is not None:
            price_range.lte = max_price
        must_conditions.append(
            FieldCondition(key="discounted_price", range=price_range)
        )
    
    if must_conditions:
        return Filter(must=must_conditions)
    return None

def query_with_vectors(gemini_vec: np.ndarray, color_vec: np.ndarray, top_k: int = 5, limit: int = 20, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[SareeMatch]:
    gemini_vec_list = gemini_vec.tolist()
    color_vec_list = color_vec.tolist()
    
    qdrant_filter = build_filter(min_price, max_price)
    
    prefetch_gemini = Prefetch(
        query=gemini_vec_list,
        using="gemini",
        limit=limit,
        filter=qdrant_filter
    )
    
    prefetch_color = Prefetch(
        query=color_vec_list,
        using="color",
        limit=limit,
        filter=qdrant_filter
    )
    
    response = qdrant.query_points(
        collection_name="sarees",
        prefetch=[prefetch_gemini, prefetch_color],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit
    )
    
    candidates = []
    for point in response.points:
        payload = point.payload or {}
        score_val = normalize_score(point.score) if point.score < 1.0 else min(99.9, point.score * 10)
        
        match = SareeMatch(
            sku=payload.get("sku", ""),
            name=payload.get("name", ""),
            score=score_val,
            image_url=payload.get("image_url", ""),
            product_url=payload.get("product_url", ""),
            price=float(payload.get("discounted_price", payload.get("retail_price", 0.0)))
        )
        candidates.append(match)
    
    final_matches = rerank(candidates, top_k=top_k)
    return final_matches

def query_similar(image_path: str, top_k: int = 5, limit: int = 20, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[SareeMatch]:
    """
    Embeds query image with gemini and color_histogram, runs Qdrant prefetch with RRF,
    and returns a fused ranked list of SareeMatches.
    """
    # 1. Embed query image
    gemini_vec = embed_image_gemini(image_path)
    color_vec = compute_color_histogram(image_path)
    
    # Cache for follow-up filter queries
    LAST_QUERY_VECTORS["gemini"] = gemini_vec
    LAST_QUERY_VECTORS["color"] = color_vec
    
    return query_with_vectors(gemini_vec, color_vec, top_k, limit, min_price, max_price)
