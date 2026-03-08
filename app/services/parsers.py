import json
import re
from typing import Any, Dict, List, Optional, Tuple


def extract_json_block(text: str) -> Optional[Any]:
    """Extract the first ```json ... ``` block from text and parse it."""
    pattern = r"```json\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    # Try bare JSON object/array
    try:
        # Find first { or [
        start = min(
            (text.find("{") if text.find("{") != -1 else len(text)),
            (text.find("[") if text.find("[") != -1 else len(text)),
        )
        if start < len(text):
            return json.loads(text[start:])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def extract_all_json_blocks(text: str) -> List[Any]:
    """Extract all ```json ... ``` blocks from text."""
    pattern = r"```json\s*([\s\S]*?)\s*```"
    results = []
    for match in re.finditer(pattern, text):
        try:
            results.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return results


def extract_mermaid_block(text: str) -> Optional[str]:
    """Extract the first mermaid fenced block from text."""
    pattern = r"```mermaid\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return None


def extract_code_block(text: str, lang: str) -> Optional[str]:
    """Extract a fenced code block by language name. Handles unclosed final block."""
    pattern = rf"```{re.escape(lang)}\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try unclosed block at end of text
    pattern_open = rf"```{re.escape(lang)}\s*([\s\S]+)$"
    match = re.search(pattern_open, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_workflow_data(text: str) -> Dict[str, Any]:
    """
    Extract Mermaid diagram + JSON flags from workflow mapping response.
    Returns dict with keys: mermaid, handoffs, redundancies, triggers
    """
    mermaid = extract_mermaid_block(text) or ""
    json_data = extract_json_block(text) or {}

    return {
        "mermaid": mermaid,
        "handoffs": json_data.get("handoffs", []),
        "redundancies": json_data.get("redundancies", []),
        "triggers": json_data.get("triggers", []),
    }


def extract_architecture_data(text: str) -> Dict[str, Any]:
    """Extract Mermaid diagram + agents + linear_flows from architecture response."""
    mermaid = extract_mermaid_block(text) or ""
    json_data = extract_json_block(text) or {}

    return {
        "mermaid": mermaid,
        "agents": json_data.get("agents", []),
        "linear_flows": json_data.get("linear_flows", []),
        "description": json_data.get("description", ""),
    }


def extract_build_data(text: str) -> Dict[str, str]:
    """Extract per-platform code blocks from build response."""
    return {
        "n8n": extract_code_block(text, "n8n") or extract_code_block(text, "json") or "",
        "zapier": extract_code_block(text, "zapier") or "",
        "make": extract_code_block(text, "make") or "",
        "python": extract_code_block(text, "python") or "",
    }


_COMPLEXITY_MULTIPLIERS = {"low": 1.0, "medium": 2.0, "high": 4.0}


def calculate_roi_score(annual_hours_saved: float, build_time_days: float, complexity: str) -> float:
    """
    roi_score = (annual_hours_saved * 100) / (build_time_days * complexity_multiplier)
    normalized to 0-100 scale
    """
    if build_time_days <= 0:
        build_time_days = 1
    multiplier = _COMPLEXITY_MULTIPLIERS.get(complexity.lower(), 2.0)
    raw = (annual_hours_saved * 100) / (build_time_days * multiplier)
    # Normalize: cap at 100
    return min(round(raw, 1), 100.0)


def parse_opportunities(json_data: Any) -> List[Dict[str, Any]]:
    """Parse and normalize opportunities list from Claude response."""
    if isinstance(json_data, dict):
        opportunities = json_data.get("opportunities", [])
    elif isinstance(json_data, list):
        opportunities = json_data
    else:
        return []

    result = []
    for i, opp in enumerate(opportunities):
        complexity = opp.get("complexity", "medium").lower()
        annual_hours = float(opp.get("annual_hours_saved", 0))
        build_days = float(opp.get("build_time_days", 5))
        roi = opp.get("roi_score")
        if roi is None:
            roi = calculate_roi_score(annual_hours, build_days, complexity)

        result.append({
            "rank": opp.get("rank", i + 1),
            "title": opp.get("title", f"Opportunity {i+1}"),
            "description": opp.get("description", ""),
            "roi_score": float(roi),
            "complexity": complexity,
            "build_time_days": build_days,
            "annual_hours_saved": annual_hours,
            "platform_recommendation": opp.get("platform_recommendation", "n8n"),
        })

    # Re-sort by roi_score descending and re-rank
    result.sort(key=lambda x: x["roi_score"], reverse=True)
    for i, opp in enumerate(result):
        opp["rank"] = i + 1
    return result
