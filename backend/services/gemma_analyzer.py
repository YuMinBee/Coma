import json
import os
import re
from typing import Any

import httpx

from models.schemas import Finding

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("GEMMA_MODEL", "gemma2:2b")
MAX_ANALYSIS_CHARS = 12_000
MAX_SAFE_PROMPT_CHARS = 6_000

SUPPORTED_CATEGORIES = {
    "SECRET",
    "SOURCE_CODE",
    "TRADE_SECRET_CANDIDATE",
    "CUSTOMER_INFO",
    "INFRA_INFO",
    "SAFE",
}

CATEGORY_LABELS = {
    "SECRET": "인증/비밀정보",
    "SOURCE_CODE": "소스코드/내부 로직",
    "TRADE_SECRET_CANDIDATE": "영업비밀 후보",
    "CUSTOMER_INFO": "고객/개인정보",
    "INFRA_INFO": "인프라 정보",
}

CATEGORY_DEFAULT_SEVERITY = {
    "SECRET": "HIGH",
    "CUSTOMER_INFO": "HIGH",
    "SOURCE_CODE": "MEDIUM",
    "TRADE_SECRET_CANDIDATE": "MEDIUM",
    "INFRA_INFO": "MEDIUM",
}

SEVERITIES = {"HIGH", "MEDIUM", "LOW"}
SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

CATEGORY_DEFAULT_REASON = {
    "SECRET": "외부 AI에 입력하면 인증정보나 비밀값이 노출될 수 있습니다.",
    "SOURCE_CODE": "비공개 구현 방식이나 내부 로직이 노출될 수 있습니다.",
    "TRADE_SECRET_CANDIDATE": "영업비밀, 가격 정책, 알고리즘 또는 내부 노하우로 볼 수 있는 정보입니다.",
    "CUSTOMER_INFO": "고객명, 계약 조건, 연락처 또는 결제 관련 정보가 노출될 수 있습니다.",
    "INFRA_INFO": "운영 환경, 내부 서비스, 테이블명 또는 장애 맥락이 노출될 수 있습니다.",
}

CATEGORY_DEFAULT_ACTION = {
    "SECRET": "실제 값을 제거하거나 [MASKED_SECRET]으로 치환하세요.",
    "SOURCE_CODE": "구현 세부사항은 일반화하고 필요한 오류 증상만 공유하세요.",
    "TRADE_SECRET_CANDIDATE": "고객명, 단가, 알고리즘 세부 조건을 일반화해서 질문하세요.",
    "CUSTOMER_INFO": "고객 식별자와 계약/결제 정보를 마스킹하세요.",
    "INFRA_INFO": "내부 호스트명, 서비스명, 테이블명, 운영 식별자를 마스킹하세요.",
}

ANALYSIS_PROMPT = """You are SafePrompt Guard's context-risk scanner.
Scan the user text for anything that could be risky to paste into an external AI service.

Important behavior:
- Actively scan the whole text, not only obvious regex-style secrets.
- Find contextual leakage risks: internal architecture, proprietary code/logic, customer or contract details, business strategy, private infrastructure, credentials, tokens, and sensitive operational details.
- Return actual risk candidates only. Do not invent facts that are not present in the text.
- Avoid duplicate findings. Prefer the shortest exact quote that proves the risk.
- If a risk is represented by a specific value or phrase, exact_quote MUST be a verbatim substring from the text.
- If the whole line is risky but no short quote is enough, use the shortest sensitive phrase from that line as exact_quote.
- Do not include the line-number prefix in exact_quote.
- Every finding MUST include category, severity, line, exact_quote, reason, action, and confidence.
- line is 1-based. confidence is a number from 0.0 to 1.0.

Categories:
- SECRET: API keys, passwords, private keys, tokens, credentials, session cookies, auth headers.
- SOURCE_CODE: proprietary source code, private business logic, non-public implementation details.
- TRADE_SECRET_CANDIDATE: algorithms, ranking/recommendation logic, pricing logic, roadmap, internal know-how, sales or contract terms.
- CUSTOMER_INFO: customer names, personal data, contact info, contract details, payment/billing details.
- INFRA_INFO: internal domains, IPs, hostnames, database URLs, schema/table names, cloud/account/project identifiers, production incident details.
- SAFE: harmless general information.

Return JSON only, with this exact shape:
{{
  "risk_level": "HIGH|MEDIUM|LOW",
  "summary": "one short Korean summary",
  "findings": [
    {{
      "category": "SECRET|SOURCE_CODE|TRADE_SECRET_CANDIDATE|CUSTOMER_INFO|INFRA_INFO|SAFE",
      "severity": "HIGH|MEDIUM|LOW",
      "line": 1,
      "exact_quote": "verbatim substring from the text",
      "reason": "Korean reason",
      "action": "Korean mitigation advice",
      "confidence": 0.86
    }}
  ]
}}

User text with 1-based line numbers:
<TEXT>
{text}
</TEXT>
"""

SAFE_PROMPT_TEMPLATE = """You are SafePrompt Guard's safe-prompt writer.
Rewrite the masked content into a safe Korean prompt that the user can paste into ChatGPT, Gemini, or another external AI.

Rules:
- Do not restore or guess anything hidden behind [MASKED_...] placeholders.
- Do not include company names, customer names, internal server names, table names, account identifiers, or secret values.
- Keep only the technical context needed for troubleshooting or explanation.
- Write in Korean.
- Return the safe prompt only. Do not add commentary outside the prompt.
- Structure it as: 문제 요약, 현재 상황, 마스킹된 내용, 요청할 질문.

Masked content:
---
{masked_text}
---

Detected risk summary:
{summary}
"""


async def fetch_ollama_tags() -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code != 200:
                return None
            data = r.json()
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def _tag_has_model(tag: dict[str, Any], model: str) -> bool:
    target = model.lower()
    for key in ("name", "model"):
        value = str(tag.get(key, "")).lower()
        if value == target:
            return True
    return False


async def check_ollama_available() -> bool:
    return await fetch_ollama_tags() is not None


async def check_model_available(model: str = DEFAULT_MODEL) -> bool:
    data = await fetch_ollama_tags()
    if not data:
        return False
    models = data.get("models", [])
    if not isinstance(models, list):
        return False
    return any(isinstance(item, dict) and _tag_has_model(item, model) for item in models)


async def local_gemma_status(model: str = DEFAULT_MODEL) -> dict[str, bool]:
    data = await fetch_ollama_tags()
    if not data:
        return {"ollama_available": False, "gemma_available": False}
    models = data.get("models", [])
    gemma_available = isinstance(models, list) and any(
        isinstance(item, dict) and _tag_has_model(item, model) for item in models
    )
    return {"ollama_available": True, "gemma_available": gemma_available}


async def _ollama_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    *,
    json_mode: bool = False,
    temperature: float = 0.1,
) -> str | None:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if json_mode:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(f"{OLLAMA_BASE}/api/generate", json=payload)
            if r.status_code != 200:
                return None
            return r.json().get("response", "")
    except Exception:
        return None


def _parse_json_response(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if not raw:
        return None

    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", raw):
        try:
            data, _ = decoder.raw_decode(raw[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        line = int(value)
    except (TypeError, ValueError):
        return None
    return line if line > 0 else None


def _normalize_category(value: Any) -> str:
    cat = str(value or "").strip().upper()
    return cat if cat in SUPPORTED_CATEGORIES else "TRADE_SECRET_CANDIDATE"


def _normalize_severity(value: Any, category: str) -> str:
    severity = str(value or "").strip().upper()
    if severity not in SEVERITIES:
        severity = CATEGORY_DEFAULT_SEVERITY.get(category, "MEDIUM")

    minimum = CATEGORY_DEFAULT_SEVERITY.get(category, "MEDIUM")
    if SEVERITY_RANK[severity] < SEVERITY_RANK[minimum]:
        return minimum
    return severity


def _normalize_risk_level(value: Any) -> str:
    risk = str(value or "").strip().upper()
    if risk in SEVERITIES:
        return risk
    return "LOW"


def _normalize_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence > 1.0 and confidence <= 100.0:
        confidence = confidence / 100.0
    return max(0.0, min(1.0, confidence))


def _clean_quote(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    quote = value.strip().strip("`")
    quote = re.sub(r"^\s*\d+\s*[:.)-]\s*", "", quote)
    if not quote or quote.lower() in {"none", "null", "n/a", "safe"}:
        return None
    return quote[:500]


def _clean_model_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in {"none", "null", "n/a", "safe"}:
        return None
    return text


def _line_number(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def _line_region(text: str, line: int | None) -> tuple[int, str] | None:
    if line is None:
        return None

    offset = 0
    for idx, content in enumerate(text.splitlines(keepends=True), 1):
        if idx == line:
            return offset, content.rstrip("\r\n")
        offset += len(content)
    return None


def _line_text(text: str, line: int | None) -> str | None:
    region = _line_region(text, line)
    if not region:
        return None
    content = region[1].strip()
    return content or None


def _numbered_text(text: str) -> str:
    return "\n".join(f"{idx}: {line}" for idx, line in enumerate(text.splitlines(), 1))


def _search_region(region: str, quote: str) -> tuple[int, int] | None:
    idx = region.find(quote)
    if idx >= 0:
        return idx, idx + len(quote)

    lower_idx = region.lower().find(quote.lower())
    if lower_idx >= 0:
        return lower_idx, lower_idx + len(quote)

    parts = [part for part in re.split(r"\s+", quote.strip()) if part]
    if len(parts) >= 2:
        pattern = r"\s+".join(re.escape(part) for part in parts)
        match = re.search(pattern, region, flags=re.IGNORECASE)
        if match:
            return match.start(), match.end()

    return None


def _find_quote_span(text: str, quote: str | None, line: int | None) -> tuple[int | None, int | None]:
    if not quote or len(quote.strip()) < 4:
        return None, None

    regions: list[tuple[int, str]] = []
    line_region = _line_region(text, line)
    if line_region:
        regions.append(line_region)
    regions.append((0, text))

    for region_start, region in regions:
        span = _search_region(region, quote)
        if span:
            return region_start + span[0], region_start + span[1]

    return None, None


def _finding_value(text: str, start: int | None, end: int | None, quote: str | None, line: int | None) -> str:
    if start is not None and end is not None:
        value = text[start:end]
    elif quote:
        value = quote
    elif line:
        value = f"줄 {line}"
    else:
        value = "문맥 기반 위험"

    return value[:160] + ("..." if len(value) > 160 else "")


async def analyze_with_gemma(text: str) -> tuple[list[Finding], str, str]:
    analysis_text = text[:MAX_ANALYSIS_CHARS]
    prompt = ANALYSIS_PROMPT.format(text=_numbered_text(analysis_text))
    raw = await _ollama_generate(prompt, json_mode=True, temperature=0.0)
    if not raw:
        return [], "LOW", ""

    data = _parse_json_response(raw)
    if not data:
        return [], "LOW", ""

    findings: list[Finding] = []
    for item in data.get("findings", []):
        if not isinstance(item, dict):
            continue

        category = _normalize_category(item.get("category"))
        if category == "SAFE":
            continue

        line = _safe_int(item.get("line"))
        quote = _clean_quote(item.get("exact_quote") or item.get("quote") or item.get("value"))
        if not quote:
            quote = _line_text(text, line)
        start, end = _find_quote_span(text, quote, line)
        if start is not None:
            line = _line_number(text, start)

        severity = _normalize_severity(item.get("severity"), category)
        confidence = _normalize_confidence(item.get("confidence"))
        if confidence is None:
            confidence = 0.65 if quote else 0.5
        findings.append(
            Finding(
                type=CATEGORY_LABELS.get(category, "문맥 기반 위험"),
                category=category,
                value=_finding_value(text, start, end, quote, line),
                start=start,
                end=end,
                line=line,
                severity=severity,
                exact_quote=quote,
                confidence=confidence,
                reason=_clean_model_text(item.get("reason")) or CATEGORY_DEFAULT_REASON.get(category),
                action=_clean_model_text(item.get("action")) or CATEGORY_DEFAULT_ACTION.get(category),
                source="gemma",
            )
        )

    return findings, _normalize_risk_level(data.get("risk_level")), str(data.get("summary") or "")


async def generate_safe_prompt(masked_text: str, summary: str) -> str | None:
    prompt = SAFE_PROMPT_TEMPLATE.format(
        masked_text=masked_text[:MAX_SAFE_PROMPT_CHARS],
        summary=summary or "민감정보가 마스킹되었습니다.",
    )
    return await _ollama_generate(prompt, temperature=0.2)


def fallback_safe_prompt(masked_text: str, findings: list[Finding]) -> str:
    types = list({f.type for f in findings[:8]})
    detected = ", ".join(types) if types else "민감정보"

    lines = masked_text.strip().split("\n")
    context_lines = [line for line in lines if line.strip()][:12]
    context_block = "\n".join(context_lines)

    return f"""다음 내용은 외부 AI에 질문하기 전 보안 검사를 거쳤습니다.
{detected} 등 민감한 정보는 마스킹 처리했습니다.

## 문제 상황
아래 마스킹된 로그/설정/문서를 기준으로 원인 분석과 해결 방법을 알려주세요.

## 현재 상황
- 애플리케이션 또는 시스템에서 오류/이슈가 발생한 상태
- 운영 환경과 유사한 조건에서 재현 가능
- 민감한 접속 정보·고객 정보·내부 식별자는 제거됨

## 마스킹된 내용
```
{context_block}
```

## 요청
1. 가능한 원인을 우선순위별로 정리해 주세요.
2. 점검해야 할 설정 항목과 순서를 알려주세요.
3. 재발 방지를 위한 보안·운영 권장사항을 제안해 주세요."""
