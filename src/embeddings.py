import os
import cv2
import numpy as np
from PIL import Image
import google.genai as genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted

import time

# The client reads GEMINI_API_KEY from the environment automatically.
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Returns a module-level cached genai.Client instance."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client


def embed_image_gemini(
    image_path: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
    max_retries: int = 5,
) -> np.ndarray:
    """
    Embeds an image using gemini-embedding-2-preview, returning a 3072-dim
    L2-normalized vector. Includes retry logic for rate limits.

    Args:
        image_path:  Path to the image file (jpg/jpeg/png/webp).
        task_type:   Gemini task type.  Use "RETRIEVAL_DOCUMENT" when building
                     the index and "RETRIEVAL_QUERY" when embedding a search
                     query.  The model uses different projection heads for each
                     role — mixing them collapses retrieval quality.
        max_retries: Number of retries on rate-limit errors.
    """
    client = _get_client()

    # Read image bytes and determine MIME type from the file extension
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    config = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=3072,
    )

    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model="models/gemini-embedding-2-preview",
                contents=[image_part],
                config=config,
            )
            vector = response.embeddings[0].values

            # L2 normalize
            vec_np = np.array(vector, dtype=np.float32)
            norm = np.linalg.norm(vec_np)
            if norm > 0:
                vec_np = vec_np / norm
            return vec_np

        except Exception as e:
            error_str = str(e)
            is_rate_limit = (
                "429" in error_str
                or "Quota exceeded" in error_str
                or "RESOURCE_EXHAUSTED" in error_str
                or isinstance(e, ResourceExhausted)
            )
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = 30 * (attempt + 1)
                print(
                    f"Rate limit hit for Gemini API. Waiting {wait_time}s "
                    f"before retry {attempt + 1}/{max_retries}..."
                )
                time.sleep(wait_time)
            else:
                raise ValueError(f"Failed to embed image via Gemini: {e}") from e

    raise ValueError("Failed to embed image via Gemini (max retries exceeded).")


def compute_color_histogram(image_path: str) -> np.ndarray:
    """
    HSV histogram (32 bins x 3 channels = 96-dim), L2-normalized.
    """
    # OpenCV loads images in BGR format
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Image not found or corrupt: {image_path}")

    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Calculate histograms for H, S, V channels — 32 bins per channel
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
