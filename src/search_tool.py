import os
import base64
import tempfile
import uuid
import requests
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from .qdrant_store import query_similar, SareeMatch

class SareeSearchInput(BaseModel):
    image_url: Optional[str] = Field(None, description="Public URL of the query image")
    image_path: Optional[str] = Field(None, description="Local path of the uploaded image")
    top_k: int = Field(5, description="Number of similar sarees to return, default 5")
    min_price: Optional[float] = Field(None, description="Minimum price filter")
    max_price: Optional[float] = Field(None, description="Maximum price filter")

@tool("search_similar_sarees", args_schema=SareeSearchInput)
def search_similar_sarees(image_url: Optional[str] = None, image_path: Optional[str] = None, top_k: int = 5, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[dict]:
    """Find visually similar sarees in the catalogue given a query image.
    Use this whenever the user shares or references an image and asks for
    similar/matching/comparable items, styles, colours, or designs.
    If the user has uploaded an image, the path will be in your context, pass it to image_path."""
    if not image_url and not image_path:
        # If user is trying to filter a previous search, we can use the cached vectors.
        # We will handle this by returning a special signal or directly calling qdrant_store.filter_last_search
        from .qdrant_store import LAST_QUERY_VECTORS
        if LAST_QUERY_VECTORS["gemini"] is not None:
             from .qdrant_store import query_with_vectors
             results = query_with_vectors(LAST_QUERY_VECTORS["gemini"], LAST_QUERY_VECTORS["color"], top_k=top_k, min_price=min_price, max_price=max_price)
             dict_results = [r.dict() for r in results]
             try:
                 import streamlit as st
                 st.session_state["last_results"] = dict_results
             except ImportError:
                 pass
             return dict_results
        else:
             raise ValueError("Must provide either image_url or image_path")
    
    temp_path = None
    try:
        if image_url:
            temp_path = os.path.join(tempfile.gettempdir(), f"query_{uuid.uuid4().hex}.jpg")
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            with open(temp_path, "wb") as f:
                f.write(response.content)
            path_to_query = temp_path
        elif image_path:
            path_to_query = image_path
                
        # Call the qdrant store
        from .qdrant_store import query_similar
        results = query_similar(path_to_query, top_k=top_k, min_price=min_price, max_price=max_price)
        dict_results = [r.dict() for r in results]
        
        # Store in session state for Streamlit to render the grid
        try:
            import streamlit as st
            st.session_state["last_results"] = dict_results
        except ImportError:
            pass
            
        return dict_results
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
