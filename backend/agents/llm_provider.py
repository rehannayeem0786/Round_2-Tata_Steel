"""
LLM Provider — Unified LLM factory that supports OpenRouter
(OpenAI-compatible API) with quick retry and fallback model.
Uses free models from OpenRouter by default.
"""

import time
from langchain_openai import ChatOpenAI
from config import (
    NVIDIA_API_KEY, NVIDIA_BASE_URL,
    GROQ_API_KEY, GROQ_BASE_URL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE,
    API_PROVIDER
)

# Single fallback model if primary is rate-limited
FALLBACK_MODEL = "meta/llama-3.1-8b-instruct" if API_PROVIDER == "nvidia" else ("llama3-8b-8192" if API_PROVIDER == "groq" else "google/gemma-2-9b-it:free")


def get_llm(temperature: float = None, model: str = None):
    """
    Get the LLM instance based on configured provider.
    """
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    model_name = model or LLM_MODEL
    
    if API_PROVIDER == "nvidia":
        return ChatOpenAI(
            model=model_name,
            temperature=temp,
            openai_api_key=NVIDIA_API_KEY,
            openai_api_base=NVIDIA_BASE_URL,
            max_tokens=4096,
            max_retries=0,
            timeout=45,
        )
    
    if API_PROVIDER == "groq":
        return ChatOpenAI(
            model=model_name,
            temperature=temp,
            openai_api_key=GROQ_API_KEY,
            openai_api_base=GROQ_BASE_URL,
            max_tokens=4096,
            max_retries=0,
            timeout=45,
        )
        
    if API_PROVIDER == "openrouter":
        return ChatOpenAI(
            model=model_name,
            temperature=temp,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Intelligent Maintenance Wizard",
            },
            max_tokens=4096,
            max_retries=0,
            timeout=45,
        )
    
    elif API_PROVIDER == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temp,
                google_api_key=GOOGLE_API_KEY,
            )
        except ImportError:
            print("[WARN] langchain-google-genai not installed")
            return None
    
    return None


def invoke_with_retry(chain, **kwargs):
    """
    Invoke a LangChain chain with one retry on rate limit,
    then try a single fallback model for any errors.
    
    Returns:
        Response content string
    """
    # Try primary model
    try:
        response = chain.invoke(kwargs)
        return response.content
    except Exception as e:
        error_str = str(e)
        # If it is a rate limit, wait 5s and retry once
        if "429" in error_str or "rate" in error_str.lower():
            print(f"[RATE-LIMIT] Primary model rate-limited, waiting 5s...")
            time.sleep(5)
            try:
                response = chain.invoke(kwargs)
                return response.content
            except Exception as retry_err:
                error_str = str(retry_err)
                print(f"[RATE-LIMIT] Primary still limited: {retry_err}")
        else:
            print(f"[ERR] Primary model failed: {e}")
            
    # Try fallback model
    if (API_PROVIDER in ["openrouter", "groq", "nvidia"]) and FALLBACK_MODEL != LLM_MODEL:
        print(f"[FALLBACK] Trying fallback model: {FALLBACK_MODEL}")
        try:
            fallback_llm = get_llm(model=FALLBACK_MODEL)
            if hasattr(chain, 'first'):
                fallback_chain = chain.first | fallback_llm
                response = fallback_chain.invoke(kwargs)
                print(f"[FALLBACK] Success with {FALLBACK_MODEL}")
                return response.content
        except Exception as fb_err:
            print(f"[FALLBACK] {FALLBACK_MODEL} also failed: {fb_err}")
    
    # All failed — raise the original error
    raise Exception(f"All models failed or rate-limited. Please try again.")


def is_ai_enabled() -> bool:
    """Check if AI is enabled (any API key configured)."""
    return API_PROVIDER != "none"


def get_provider_info() -> dict:
    """Get current LLM provider information."""
    return {
        "provider": API_PROVIDER,
        "model": LLM_MODEL,
        "enabled": is_ai_enabled(),
    }
