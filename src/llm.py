"""
Thin LLM wrapper — all LLM calls go through this file.

Uses AWS Bedrock with Claude via langchain-aws. To switch providers (e.g., back
to the Anthropic API, or to OpenAI), change this file only. No other file in
the project should import boto3, langchain_aws, or any LLM SDK directly.

Design choices:
- Synchronous, not async: Streamlit runs in a single thread and doesn't have a
  running event loop. Async calls require asyncio.run() wrappers that complicate
  every callsite. Sync is simpler and good enough for a demo tool.
- ChatBedrockConverse over boto3 directly: LangChain handles the Converse API
  message format, structured output (via tool use), and retry on rate limits.
- Factory function (_get_llm): creates a fresh client per call to avoid shared
  state across Streamlit reruns. The overhead is negligible.
- Bedrock over Anthropic API: IAM-authenticated (no key to rotate), usage tracked
  in AWS Cost Explorer, consistent with the App Runner deployment architecture.
- tenacity retry: handles Bedrock throttling and transient service errors with
  exponential backoff (2s → 30s, 3 attempts). The inner schema-retry in
  call_llm_structured handles LLM output validation failures separately.
"""

from __future__ import annotations

import os
from typing import TypeVar

from botocore.exceptions import ClientError
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# Claude Sonnet 4 via cross-region inference profile (required for Claude 4 models —
# on-demand throughput is not supported; must use the us. inference profile prefix).
# Override at runtime with the BEDROCK_MODEL_ID environment variable.
DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def _get_llm() -> ChatBedrockConverse:
    """Return a configured Bedrock LLM client."""
    return ChatBedrockConverse(
        model=os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        max_tokens=4096,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ClientError, TimeoutError)),
    reraise=True,
)
def call_llm(prompt: str, system: str = "") -> str:
    """
    Send a prompt to the LLM and return the text response.

    Used for unstructured calls where the output is plain text
    (e.g., generating a decision record narrative).

    Retries up to 3 times with exponential backoff on Bedrock throttling or
    transient service errors. Raises after 3 failed attempts.
    """
    messages: list[SystemMessage | HumanMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    response = _get_llm().invoke(messages)
    return str(response.content)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ClientError, TimeoutError)),
    reraise=True,
)
def call_llm_structured(prompt: str, response_model: type[T], system: str = "") -> T:
    """
    Send a prompt and parse the response into a Pydantic model.

    Uses Bedrock's tool-use feature (via LangChain's with_structured_output)
    to guarantee schema compliance. This means the LLM cannot return freeform
    JSON — it must call a tool whose schema matches the Pydantic model.

    Why structured output matters here: every LLM node in the graph produces
    data that downstream nodes depend on. Freeform JSON that doesn't match the
    expected schema would silently corrupt state. Tool-use enforces the contract.

    Two retry layers:
    - tenacity (@retry decorator): handles Bedrock infrastructure failures
      (throttling, transient errors) with exponential backoff.
    - Inner try/except: handles schema validation failures by retrying once
      with a stricter system message. After both retries fail, raises the error.
    """
    messages: list[SystemMessage | HumanMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    structured_llm = _get_llm().with_structured_output(response_model)

    try:
        result = structured_llm.invoke(messages)
        return result  # type: ignore[return-value]
    except Exception:
        # Retry with an explicit strictness reminder in the system message.
        strict_system = (
            (system + "\n\n" if system else "")
            + "IMPORTANT: Your response MUST strictly follow the required schema. "
            "Do not include any fields not defined in the schema."
        )
        retry_messages = [
            SystemMessage(content=strict_system),
            HumanMessage(content=prompt),
        ]
        return structured_llm.invoke(retry_messages)  # type: ignore[return-value]
