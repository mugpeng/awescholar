"""LiteLLM wrapper for multi-provider LLM calls with structured output."""

import litellm
from pydantic import BaseModel


def complete(
    model: str,
    system: str,
    user: str,
    response_format: type[BaseModel] | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.0,
) -> BaseModel | str:
    """Call LLM with optional structured output.

    If response_format is provided, returns validated Pydantic model.
    Otherwise returns raw string content.
    """
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["api_base"] = base_url
    if response_format:
        kwargs["response_format"] = response_format

    response = litellm.completion(**kwargs)
    content = response.choices[0].message.content

    if response_format:
        return response_format.model_validate_json(content)
    return content
