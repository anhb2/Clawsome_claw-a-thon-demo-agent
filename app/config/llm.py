import os

from openai import OpenAI

REQUIRED_LLM_VARS = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")


def get_llm_config() -> tuple[str, str, str]:
    """Return LLM credentials from environment. Raises ValueError if any are missing."""
    missing = [name for name in REQUIRED_LLM_VARS if not os.environ.get(name)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in .env or use /agentbase-llm to configure LLM access."
        )
    return (
        os.environ["LLM_API_KEY"],
        os.environ["LLM_BASE_URL"],
        os.environ["LLM_MODEL"],
    )


def get_llm_client() -> tuple[OpenAI, str]:
    """Create an OpenAI-compatible client for GreenNode MAAS."""
    api_key, base_url, model = get_llm_config()
    return OpenAI(api_key=api_key, base_url=base_url), model
