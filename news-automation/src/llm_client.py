"""
llm_client.py — Shared Gemini API client for text generation (Recap, Accuracy, Tagging).
Requires GEMINI_API_KEY environment variable.
"""
import logging
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY environment variable is not set. LLM features will fail.")
        return None
    
    genai.configure(api_key=api_key)
    
    # Use gemini-1.5-flash for fast, inexpensive text tasks
    model = genai.GenerativeModel('gemini-1.5-flash')
    return model

def generate_text(prompt: str, max_tokens: int = 2000) -> str:
    """Helper to generate text from a prompt."""
    model = get_gemini_client()
    if not model:
        return "LLM API Key missing."
        
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error("Error calling Gemini API: %s", e)
        return f"Error: {e}"
