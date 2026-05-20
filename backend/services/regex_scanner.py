import re
import string
from bisect import bisect_right

from models.schemas import Finding

PATTERNS: list[tuple[str, str, str, str]] = [
    ("AWS Access Key", r"AKIA[0-9A-Z]{16}", "SECRET", "HIGH"),
    ("Private Key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "SECRET", "HIGH"),
    ("JWT Token", r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "SECRET", "HIGH"),
    ("Password", r"(?i)(password|passwd|pwd|secret)\s*[:=]\s*['\"]?[^\s'\"\n]{3,}", "SECRET", "HIGH"),
    ("API Key", r"(?i)(api[_-]?key|apikey|access[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?[^\s'\"\n]+", "SECRET", "HIGH"),
    ("Bearer Token", r"(?i)bearer\s+[A-Za-z0-9._-]{20,}", "SECRET", "HIGH"),
    ("DB URL", r"(?:jdbc:mysql|jdbc:postgresql|mongodb|redis|mysql|postgresql)://[^\s'\"\n]+", "INFRA_INFO", "HIGH"),
    ("Internal IP", r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b", "INFRA_INFO", "MEDIUM"),
    ("Email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "CUSTOMER_INFO", "MEDIUM"),
    ("Phone", r"(?:\+82|0)[\d\s-]{9,14}", "CUSTOMER_INFO", "MEDIUM"),
    ("Credit Card", r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "CUSTOMER_INFO", "HIGH"),
]

COMPILED_PATTERNS = [
    (name, re.compile(pattern), category, severity)
    for name, pattern, category, severity in PATTERNS
]

ACTION_BY_CATEGORY = {
    "SECRET": "실제 값을 제거하거나 [MASKED_SECRET] 형태로 치환하세요.",
    "INFRA_INFO": "내부 주소, DB URL, 서비스 식별자는 일반화해서 공유하세요.",
    "CUSTOMER_INFO": "개인정보나 고객 식별자는 마스킹한 뒤 공유하세요.",
}

INTERNAL_DOMAIN_SUFFIXES = (".internal", ".local", ".corp", ".company")
DOMAIN_CHARS = set(string.ascii_letters + string.digits + "-.")
INTERNAL_DOMAIN_FULL_RE = re.compile(
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+(?:internal|local|corp|company)",
    re.IGNORECASE,
)


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    offsets.extend(i + 1 for i, ch in enumerate(text) if ch == "\n")
    return offsets


def _line_number(offsets: list[int], pos: int) -> int:
    return bisect_right(offsets, pos)


def _short(value: str, limit: int = 160) -> str:
    return value[:limit] + ("..." if len(value) > limit else "")


def _iter_internal_domains(text: str) -> list[tuple[int, int, str]]:
    lower = text.lower()
    matches: list[tuple[int, int, str]] = []

    for suffix in INTERNAL_DOMAIN_SUFFIXES:
        search_from = 0
        while True:
            suffix_start = lower.find(suffix, search_from)
            if suffix_start == -1:
                break

            start = suffix_start - 1
            while start >= 0 and text[start] in DOMAIN_CHARS and suffix_start - start <= 255:
                start -= 1
            start += 1

            end = suffix_start + len(suffix)
            candidate = text[start:end]
            prev_ok = start == 0 or text[start - 1] not in DOMAIN_CHARS
            next_ok = end == len(text) or not (text[end].isalnum() or text[end] in "-_")
            if prev_ok and next_ok and INTERNAL_DOMAIN_FULL_RE.fullmatch(candidate):
                matches.append((start, end, candidate))

            search_from = end

    return matches


def _may_contain_pattern(name: str, text: str, lower: str) -> bool:
    if name == "AWS Access Key":
        return "AKIA" in text
    if name == "Private Key":
        return "-----BEGIN" in text
    if name == "JWT Token":
        return "eyJ" in text and "." in text
    if name == "Password":
        return any(key in lower for key in ("password", "passwd", "pwd", "secret"))
    if name == "API Key":
        return "key" in lower or "apikey" in lower or "secret" in lower
    if name == "Bearer Token":
        return "bearer" in lower
    if name == "DB URL":
        return "://" in text
    if name == "Internal IP":
        return "." in text and any(ch.isdigit() for ch in text)
    if name == "Email":
        return "@" in text
    if name in {"Phone", "Credit Card"}:
        return any(ch.isdigit() for ch in text)
    return True


def scan_by_regex(text: str) -> list[Finding]:
    findings: list[Finding] = []
    seen_spans: set[tuple[int, int]] = set()
    line_offsets = _line_offsets(text)
    lower = text.lower()

    for name, pattern, category, severity in COMPILED_PATTERNS:
        if not _may_contain_pattern(name, text, lower):
            continue
        for match in pattern.finditer(text):
            quote = match.group()
            span = (match.start(), match.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)

            findings.append(
                Finding(
                    type=name,
                    category=category,
                    value=_short(quote),
                    start=match.start(),
                    end=match.end(),
                    line=_line_number(line_offsets, match.start()),
                    severity=severity,
                    exact_quote=quote,
                    confidence=0.99,
                    reason=f"{name} 정규식 패턴과 일치하는 민감 값이 발견되었습니다.",
                    action=ACTION_BY_CATEGORY.get(category, "해당 값을 제거하거나 일반화해서 공유하세요."),
                    source="regex",
                )
            )

    for start, end, quote in _iter_internal_domains(text):
        span = (start, end)
        if span in seen_spans:
            continue
        seen_spans.add(span)
        findings.append(
            Finding(
                type="Internal Domain",
                category="INFRA_INFO",
                value=_short(quote),
                start=start,
                end=end,
                line=_line_number(line_offsets, start),
                severity="MEDIUM",
                exact_quote=quote,
                confidence=0.99,
                reason="Internal Domain 정규식 패턴과 일치하는 민감 값이 발견되었습니다.",
                action=ACTION_BY_CATEGORY["INFRA_INFO"],
                source="regex",
            )
        )

    return findings
