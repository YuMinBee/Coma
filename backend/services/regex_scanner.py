import re

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
    ("Internal Domain", r"\b[\w-]+\.(?:internal|local|corp|company)\b", "INFRA_INFO", "MEDIUM"),
]

ACTION_BY_CATEGORY = {
    "SECRET": "실제 값을 제거하거나 [MASKED_SECRET] 형태로 치환하세요.",
    "INFRA_INFO": "내부 주소, DB URL, 서비스 식별자는 일반화해서 공유하세요.",
    "CUSTOMER_INFO": "개인정보나 고객 식별자는 마스킹한 뒤 공유하세요.",
}


def _line_number(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def _short(value: str, limit: int = 160) -> str:
    return value[:limit] + ("..." if len(value) > limit else "")


def scan_by_regex(text: str) -> list[Finding]:
    findings: list[Finding] = []
    seen_spans: set[tuple[int, int]] = set()

    for name, pattern, category, severity in PATTERNS:
        for match in re.finditer(pattern, text):
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
                    line=_line_number(text, match.start()),
                    severity=severity,
                    exact_quote=quote,
                    confidence=0.99,
                    reason=f"{name} 정규식 패턴과 일치하는 민감 값이 발견되었습니다.",
                    action=ACTION_BY_CATEGORY.get(category, "해당 값을 제거하거나 일반화해서 공유하세요."),
                    source="regex",
                )
            )

    return findings
