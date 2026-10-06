"""문서·테스트에서 널리 쓰이는 예제 값.

실제 유출이 아니므로 탐지 단계에서 제외한다(gitleaks allowlist와 같은 방식).
조직별 예외는 여기가 아니라 config/policy.yaml의 allow 규칙으로 표현한다.
"""

from __future__ import annotations

import re

KNOWN_EXAMPLE_SECRETS = frozenset(
    {
        "AKIAIOSFODNN7EXAMPLE",  # AWS 공식 문서 예제 Access Key ID
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # AWS 공식 문서 예제 Secret Access Key
    }
)

# RFC 2606 / RFC 6761 예약 도메인
RESERVED_EMAIL_DOMAINS = ("example.com", "example.net", "example.org")
RESERVED_TOP_LEVEL = (".example", ".test", ".invalid", ".localhost")

# 사람이 쓴 placeholder 단어는 소문자·대문자·첫 글자 대문자 형태로 들어온다. 무작위 키 안에
# "ExAmPLE"처럼 대소문자가 섞여 우연히 들어간 경우까지 예제 값으로 보면 실제 키를 놓친다.
PLACEHOLDER_WORDS = (
    "example",
    "sample",
    "dummy",
    "placeholder",
    "changeme",
    "change_me",
    "change-me",
    "your_",
    "your-",
    "fake",
    "redacted",
)
PLACEHOLDER_SYMBOLS = ("xxxx", "****", "<", ">", "${", "{{")

# 이미 마스킹된 결과를 다시 검사해도 placeholder를 탐지하지 않게 한다.
MASK_PLACEHOLDER_RE = re.compile(r"\[(?:MASKED_)?[A-Z][A-Z_]*(?:_\d+)?\]")


def is_reserved_email(address: str) -> bool:
    domain = address.rsplit("@", 1)[-1].lower().rstrip(".")
    if domain in RESERVED_EMAIL_DOMAINS:
        return True
    if any(domain.endswith("." + reserved) for reserved in RESERVED_EMAIL_DOMAINS):
        return True
    return domain.endswith(RESERVED_TOP_LEVEL)


def is_placeholder_secret(value: str) -> bool:
    stripped = value.strip().strip("'\"`")
    if not stripped:
        return True
    if stripped in KNOWN_EXAMPLE_SECRETS or stripped.endswith(("EXAMPLE", "EXAMPLEKEY")):
        return True
    if MASK_PLACEHOLDER_RE.fullmatch(stripped):
        return True
    for word in PLACEHOLDER_WORDS:
        if word in stripped or word.upper() in stripped or word.capitalize() in stripped:
            return True
    lower = stripped.lower()
    return any(symbol in lower for symbol in PLACEHOLDER_SYMBOLS)
