import os
import tempfile
import uuid
import requests
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from .qdrant_store import query_similar, query_with_vectors, LAST_QUERY_VECTORS, SareeMatch

# Map Content-Type header values to file extensions so the temp file has the
# correct extension and embed_image_gemini() infers the right MIME type.
_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class SareeSearchInput(BaseModel):
    image_url: Optional[str] = Field(None, description="Public URL of the query image")
    image_path: Optional[str] = Field(None, description="Local path of the uploaded image")
    top_k: int = Field(5, description="Number of similar sarees to return, default 5")
    min_price: Optional[float] = Field(None, description="Minimum price filter in INR")
    max_price: Optional[float] = Field(None, description="Maximum price filter in INR")


@tool("search_similar_sarees", args_schema=SareeSearchInput)
def search_similar_sarees(
    image_url: Optional[str] = None,
    image_path: Optional[str] = None,
    top_k: int = 5,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[dict]:
    """Find visually similar sarees in the catalogue given a query image.
    Use this whenever the user shares or references an image and asks for
    similar/matching/comparable items, styles, colours, or designs.
    If the user has uploaded an image, the path will be in your context, pass it to image_path."""

    # -----------------------------------------------------------------------
    # No image provided — re-use cached vectors from the last search so the
    # user can apply a price filter without re-embedding the query image.
    # -----------------------------------------------------------------------
    if not image_url and not image_path:
        if LAST_QUERY_VECTORS["gemini"] is not None:
            results = query_with_vectors(
                LAST_QUERY_VECTORS["gemini"],
                LAST_QUERY_VECTORS["color"],
                gemini_border_vec=LAST_QUERY_VECTORS.get("gemini_border"),
                top_k=top_k,
                min_price=min_price,
                max_price=max_price,
            )
            dict_results = [r.model_dump() for r in results]
            _push_to_session(dict_results)
            return dict_results
        raise ValueError("Must provide either image_url or image_path")

    # -----------------------------------------------------------------------
    # Download URL image with correct MIME-aware extension
    # -----------------------------------------------------------------------
    temp_path = None
    try:
        if image_url:
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()

            # Detect the real content type so the temp file extension is correct.
            # embed_image_gemini() infers the MIME type from the extension, so
            # saving a .webp as .jpg would send corrupted bytes to Gemini.
            content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            ext = _CONTENT_TYPE_TO_EXT.get(content_type, ".jpg")

            temp_path = os.path.join(tempfile.gettempdir(), f"query_{uuid.uuid4().hex}{ext}")
            with open(temp_path, "wb") as f:
                f.write(response.content)
            path_to_query = temp_path

        else:
            path_to_query = image_path

        results = query_similar(
            path_to_query,
            top_k=top_k,
            min_price=min_price,
            max_price=max_price,
        )
        dict_results = [r.model_dump() for r in results]
        _push_to_session(dict_results)
        return dict_results

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _push_to_session(results: List[dict]) -> None:
    """Store results in Streamlit session_state so the UI can render the grid."""
    try:
        import streamlit as st
        st.session_state["last_results"] = results
    except ImportError:
        pass
