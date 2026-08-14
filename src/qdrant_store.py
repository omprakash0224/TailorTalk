import os
import io
import tempfile
from typing import List, Optional
from PIL import Image
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion, Filter, FieldCondition, Range
from pydantic import BaseModel

from .embeddings import embed_image_gemini, compute_color_histogram

# ---------------------------------------------------------------------------
# Qdrant client (module-level singleton, reused across requests)
# ---------------------------------------------------------------------------
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")

qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None,
)

# NOTE: LAST_QUERY_VECTORS has been removed.
# Per-session vector caching is now handled by backend/session_store.py
# so that each user's query vectors are fully isolated.


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class SareeMatch(BaseModel):
    sku: str
    name: str
    score: float
    image_url: str
    product_url: str
    price: float


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def _save_crop_to_temp(img: Image.Image, suffix: str = ".jpg") -> str:
    """Saves a PIL Image to a temp file and returns the path."""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    img.convert("RGB").save(tmp.name, "JPEG")
    tmp.close()
    return tmp.name


def crop_border(image_path: str) -> Image.Image:
    """
    Crops the bottom 30 % of a saree image (the border/pallu region) and
    returns it as a PIL Image.  Used as a second embedding signal to improve
    recall for border-heavy queries.
    """
    img = Image.open(image_path)
    width, height = img.size
    upper = int(height * 0.70)              # keep bottom 30 %
    cropped = img.crop((0, upper, width, height))
    return cropped


def crop_body(image_path: str) -> Image.Image:
    """
    Crops the top 70 % of the saree (body region, excluding border/pallu).
    Used as the primary pattern/weave embedding signal.
    """
    img = Image.open(image_path)
    width, height = img.size
    lower = int(height * 0.70)              # keep top 70 %
    cropped = img.crop((0, 0, width, lower))
    return cropped


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def _rrf_to_pct(score: float, best_score: float) -> float:
    """
    Converts an RRF fusion score to a 0–100 'match %' by scaling relative to
    the best score in the result set.  The top result is pinned to ~95 % so
    there is always visible differentiation between results.
    """
    if best_score <= 0:
        return 0.0
    return round(min(99.9, (score / best_score) * 95.0), 1)


def _calculate_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Helper: cosine similarity between two L2-normalised vectors."""
    dot = np.dot(vec1, vec2)
    n1, n2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
    return float(dot / (n1 * n2)) if n1 > 0 and n2 > 0 else 0.0


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
def build_filter(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> Optional[Filter]:
    if min_price is None and max_price is None:
        return None
    return Filter(
        must=[
            FieldCondition(
                key="discounted_price",
                range=Range(gte=min_price, lte=max_price),
            )
        ]
    )


# ---------------------------------------------------------------------------
# Re-ranker
# ---------------------------------------------------------------------------
def rerank(candidates: List[SareeMatch], top_k: int = 5) -> List[SareeMatch]:
    """Sort by fused score descending and return top_k results."""
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:top_k]


# ---------------------------------------------------------------------------
# Core search
# ---------------------------------------------------------------------------
def query_with_vectors(
    gemini_vec: np.ndarray,
    color_vec: np.ndarray,
    gemini_border_vec: Optional[np.ndarray] = None,
    top_k: int = 5,
    prefetch_limit: int = 50,
    rrf_limit: int = 20,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[SareeMatch]:
    """
    Runs a multi-vector Qdrant search with RRF fusion and returns ranked results.

    Prefetch sources:
      1. gemini  — full-image semantic embedding (RETRIEVAL_QUERY)
      2. color   — HSV colour histogram
      3. gemini  — border/pallu crop embedding (RETRIEVAL_QUERY)  [optional]

    Having three independent ranking signals gives RRF more information to
    produce a better fused ranking than two signals alone.
    """
    qdrant_filter = build_filter(min_price, max_price)

    prefetches = [
        Prefetch(
            query=gemini_vec.tolist(),
            using="gemini",
            limit=prefetch_limit,
            filter=qdrant_filter,
        ),
        Prefetch(
            query=color_vec.tolist(),
            using="color",
            limit=prefetch_limit,
            filter=qdrant_filter,
        ),
    ]

    # Third prefetch: border-crop embedding (richer pallu/border signal)
    if gemini_border_vec is not None:
        prefetches.append(
            Prefetch(
                query=gemini_border_vec.tolist(),
                using="gemini",
                limit=prefetch_limit,
                filter=qdrant_filter,
            )
        )

    response = qdrant.query_points(
        collection_name="sarees",
        prefetch=prefetches,
        query=FusionQuery(fusion=Fusion.RRF),
        limit=rrf_limit,
    )

    raw_points = response.points
    best_score = raw_points[0].score if raw_points else 1.0

    candidates: List[SareeMatch] = []
    for point in raw_points:
        payload = point.payload or {}
        match = SareeMatch(
            sku=payload.get("sku", ""),
            name=payload.get("name", ""),
            score=_rrf_to_pct(point.score, best_score),
            image_url=payload.get("image_url", ""),
            product_url=payload.get("product_url", ""),
            price=float(payload.get("discounted_price", payload.get("retail_price", 0.0))),
        )
        candidates.append(match)

    return rerank(candidates, top_k=top_k)


class QueryVectors:
    """Container returned by query_similar() carrying the embedded vectors.

    The caller (backend router) is responsible for persisting these in the
    per-session store so that follow-up price-filter requests can re-use
    the same vectors without re-embedding the query image.
    """

    def __init__(
        self,
        gemini: np.ndarray,
        color: np.ndarray,
        gemini_border: Optional[np.ndarray],
    ) -> None:
        self.gemini = gemini
        self.color = color
        self.gemini_border = gemini_border


def query_similar(
    image_path: str,
    top_k: int = 5,
    prefetch_limit: int = 50,
    rrf_limit: int = 20,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> tuple[List[SareeMatch], "QueryVectors"]:
    """
    Embeds a query image and runs multi-vector RRF search against the Qdrant
    collection.  Uses three embedding signals:

    1. Full-image Gemini embedding  (RETRIEVAL_QUERY task type)
    2. HSV colour histogram
    3. Border/pallu-crop Gemini embedding  (RETRIEVAL_QUERY task type)

    Returns
    -------
    results : List[SareeMatch]
    vectors : QueryVectors
        The computed embedding vectors — callers should persist these in the
        session store for follow-up price-filter requests.
    """
    border_crop_path = None
    try:
        # 1. Full-image semantic embedding — RETRIEVAL_QUERY is critical here
        gemini_vec = embed_image_gemini(image_path, task_type="RETRIEVAL_QUERY")

        # 2. Colour histogram
        color_vec = compute_color_histogram(image_path)

        # 3. Border/pallu crop embedding — adds a third independent signal to RRF
        border_img = crop_border(image_path)
        border_crop_path = _save_crop_to_temp(border_img)
        gemini_border_vec = embed_image_gemini(border_crop_path, task_type="RETRIEVAL_QUERY")

    finally:
        if border_crop_path and os.path.exists(border_crop_path):
            try:
                os.remove(border_crop_path)
            except OSError:
                pass

    vectors = QueryVectors(gemini=gemini_vec, color=color_vec, gemini_border=gemini_border_vec)

    results = query_with_vectors(
        gemini_vec,
        color_vec,
        gemini_border_vec=gemini_border_vec,
        top_k=top_k,
        prefetch_limit=prefetch_limit,
        rrf_limit=rrf_limit,
        min_price=min_price,
        max_price=max_price,
    )
    return results, vectors
