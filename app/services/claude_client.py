import asyncio
import json
import time
from typing import AsyncGenerator, List, Dict, Any, Optional

import anthropic

from app.config import settings

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def stream_claude(
    system_prompt: str,
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_TOKENS,
) -> AsyncGenerator[str, None]:
    """Stream Claude response as SSE chunks. Yields text delta strings."""
    client = get_client()
    retries = 0
    max_retries = 3

    while retries <= max_retries:
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
            return
        except anthropic.RateLimitError:
            retries += 1
            if retries > max_retries:
                yield "\n\n[Rate limit exceeded. Please try again later.]"
                return
            wait = 2 ** retries
            await asyncio.sleep(wait)
        except anthropic.APIError as e:
            yield f"\n\n[API error: {str(e)}]"
            return


async def stream_sse(
    system_prompt: str,
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_TOKENS,
) -> AsyncGenerator[str, None]:
    """Wrap stream_claude output as SSE format for FastAPI StreamingResponse."""
    async for chunk in stream_claude(system_prompt, messages, max_tokens):
        safe_chunk = chunk.replace("\n", "\\n")
        yield f"data: {safe_chunk}\n\n"
    yield "data: [DONE]\n\n"


async def stream_sse_collecting(
    system_prompt: str,
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_TOKENS,
):
    """
    Generator that yields SSE-formatted strings for streaming to the browser,
    and after the stream ends, yields the full concatenated text as a final
    non-SSE item prefixed with '__FULL__:'.

    Usage in a router:
        collected = []
        async for item in stream_sse_collecting(sys, msgs):
            if item.startswith('__FULL__:'):
                full_text = item[9:]
            else:
                yield item   # SSE chunk to client
    """
    full_response = []
    async for chunk in stream_claude(system_prompt, messages, max_tokens):
        full_response.append(chunk)
        safe_chunk = chunk.replace("\n", "\\n")
        yield f"data: {safe_chunk}\n\n"
    yield "data: [DONE]\n\n"
    yield f"__FULL__:{''.join(full_response)}"


async def complete_claude(
    system_prompt: str,
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_TOKENS,
) -> str:
    """Non-streaming Claude call; returns full response text."""
    client = get_client()
    retries = 0
    max_retries = 3

    while retries <= max_retries:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            retries += 1
            if retries > max_retries:
                raise
            wait = 2 ** retries
            await asyncio.sleep(wait)
