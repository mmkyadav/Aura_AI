"""
aura/core/llm_factory.py
------------------------
Model factory providing automatic multi-provider fallback resiliency via OpenRouter.
All models (PRIMARY_MODEL, FALLBACK_MODEL, RETRY_MODEL) are routed exclusively through OpenRouter API.
"""

import logging
from langchain_openai import ChatOpenAI
from aura.config import settings

logger = logging.getLogger(__name__)


def _create_openrouter_model(model_name: str, temp: float = 0.1) -> ChatOpenAI:
    """
    Instantiate a chat model via OpenRouter API gateway.
    All models (e.g. 'openai/gpt-4o-mini', 'google/gemini-2.5-flash', 'deepseek/deepseek-chat')
    are passed to OpenRouter with base_url='https://openrouter.ai/api/v1'.
    """
    api_key = settings.OPENROUTER_API_KEY or "dummy_key"
    base_url = settings.OPENROUTER_BASE_URL

    logger.info("Initializing model '%s' via OpenRouter", model_name)

    return ChatOpenAI(
        model=model_name,
        temperature=temp,
        api_key=api_key,
        base_url=base_url,
        timeout=45.0,
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Aura AI Assistant",
        }
    )


def get_resilient_llm(temperature: float = 0.1):
    """
    Return an LLM instance backed by OpenRouter fallback models.
    Primary (openai/gpt-4o-mini) -> Fallback (google/gemini-2.5-flash) -> Retry (deepseek/deepseek-chat)
    """
    primary_name = settings.PRIMARY_MODEL
    fallback_1_name = settings.fallback_1
    fallback_2_name = settings.fallback_2

    primary = _create_openrouter_model(primary_name, temp=temperature)

    fallbacks = []
    if fallback_1_name and fallback_1_name != primary_name:
        fallbacks.append(_create_openrouter_model(fallback_1_name, temp=temperature))
    if fallback_2_name and fallback_2_name != primary_name and fallback_2_name != fallback_1_name:
        fallbacks.append(_create_openrouter_model(fallback_2_name, temp=temperature))

    if fallbacks:
        logger.info(
            "Configured OpenRouter LLM Resiliency: Primary (%s) -> Fallback 1 (%s) -> Fallback 2 (%s)",
            primary_name,
            fallback_1_name,
            fallback_2_name,
        )
        return primary.with_fallbacks(fallbacks)

    return primary
