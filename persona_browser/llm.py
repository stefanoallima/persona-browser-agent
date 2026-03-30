"""LLM provider factory — creates the right LangChain chat model from config."""

from .config import LLMConfig, get_api_key


def create_llm(config: LLMConfig):
    """Create a LangChain chat model from config.

    All providers use OpenAI-compatible interface (langchain-openai).
    Z.AI, OpenRouter, and custom endpoints all speak the OpenAI protocol.
    """
    api_key = get_api_key(config)

    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": config.model,
        "api_key": api_key,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    # Set base_url for non-OpenAI providers
    if config.provider == "zai" or config.provider == "zai-coding-plan":
        kwargs["base_url"] = config.endpoint or "https://api.z.ai/api/coding/paas/v4"
    elif config.provider == "openrouter":
        kwargs["base_url"] = config.endpoint or "https://openrouter.ai/api/v1"
    elif config.provider == "custom":
        if not config.endpoint:
            raise ValueError("Custom provider requires an endpoint URL")
        kwargs["base_url"] = config.endpoint
    elif config.provider == "openai":
        # Native OpenAI — no base_url override needed
        pass
    else:
        # Unknown provider — treat as OpenAI-compatible with endpoint
        if config.endpoint:
            kwargs["base_url"] = config.endpoint

    return ChatOpenAI(**kwargs)
