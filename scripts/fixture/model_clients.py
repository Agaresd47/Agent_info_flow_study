from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import load_yaml

try:
    import boto3  # type: ignore
except Exception:  # noqa: BLE001
    boto3 = None


def load_runner_profiles(config_path: Path) -> List[Dict[str, Any]]:
    payload = load_yaml(config_path)
    runners = payload.get("runners")
    if not isinstance(runners, list):
        raise ValueError(f"runners must be a list in {config_path}")
    return runners


def get_bedrock_client() -> tuple[Any, str, Optional[str]]:
    if boto3 is None:
        raise RuntimeError("boto3 is required for Bedrock model calls")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"
    profile = os.environ.get("AWS_PROFILE")
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("bedrock-runtime"), region, profile


def call_bedrock_model(
    client: Any,
    model_id: str,
    system_text: str,
    user_text: str,
    max_tokens: int,
) -> Dict[str, Any]:
    response = client.converse(
        modelId=model_id,
        system=[{"text": system_text}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(item.get("text", "") for item in content if "text" in item).strip()
    return {
        "text": text,
        "usage": response.get("usage", {}),
        "stop_reason": response.get("stopReason"),
    }


def call_openai_responses(model: str, system_text: str, user_text: str, max_tokens: int) -> Dict[str, Any]:
    key = os.environ["OPENAI_API_KEY"]
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
        ],
        "max_output_tokens": max_tokens,
        "reasoning": {"effort": "low"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = data.get("output_text") or ""
    if not text:
        parts: List[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(str(content["text"]))
        text = "".join(parts)
    return {
        "text": text.strip(),
        "usage": data.get("usage", {}),
        "id": data.get("id"),
        "status": data.get("status"),
    }
