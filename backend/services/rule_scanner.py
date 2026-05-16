import re

from models.schemas import Finding

RISK_KEYWORDS: list[tuple[str, str, str, str]] = [
    (r"\b(?:prod|production)\b", "운영 환경 키워드", "INFRA_INFO", "운영 환경 정보가 포함된 줄입니다."),
    (r"\b(?:internal|company|corp)\b", "내부/회사 키워드", "INFRA_INFO", "내부 시스템 또는 회사 식별자가 포함된 줄입니다."),
    (r"\b(?:customer|client|vip)\b", "고객 관련 키워드", "CUSTOMER_INFO", "고객 또는 거래처 맥락이 포함된 줄입니다."),
    (r"\b(?:payment|salary|payroll|billing)\b", "결제/급여 키워드", "CUSTOMER_INFO", "결제, 급여, 청구 정보 맥락이 포함된 줄입니다."),
    (r"\b(?:admin|root|superuser)\b", "관리자 계정 키워드", "SECRET", "관리자 권한이나 계정 정보 맥락이 포함된 줄입니다."),
    (r"\b(?:credential|secret|private)\b", "인증정보 키워드", "SECRET", "인증정보 또는 비밀값 맥락이 포함된 줄입니다."),
    (r"\b(?:algorithm|recommendation|ranking)\b", "알고리즘/추천 키워드", "TRADE_SECRET_CANDIDATE", "추천, 랭킹, 알고리즘 등 내부 로직 맥락이 포함된 줄입니다."),
    (r"\b(?:contract|단가|계약)\b", "계약/영업 키워드", "TRADE_SECRET_CANDIDATE", "계약 조건이나 영업 정보 맥락이 포함된 줄입니다."),
]

SENSITIVE_FILES = {
    ".env",
    "application.yml",
    "application.properties",
    "config.py",
    "settings.py",
    "docker-compose.yml",
    "secrets.json",
    "credentials.json",
}

TABLE_PATTERN = re.compile(
    r"\b(?:tbl_|tb_|customer_|payment_|user_)[\w]+\b|"
    r"(?:고객|결제|주문|계약)[\s]*(?:테이블|table|Table)",
    re.IGNORECASE,
)

ACTION_BY_CATEGORY = {
    "SECRET": "인증정보, 관리자 계정, 비밀값은 실제 값 없이 설명하세요.",
    "INFRA_INFO": "운영 환경명, 내부 서비스명, 테이블명은 [MASKED_INFRA]처럼 치환하세요.",
    "CUSTOMER_INFO": "고객명, 계약 조건, 결제 맥락은 식별 불가능하게 일반화하세요.",
    "TRADE_SECRET_CANDIDATE": "알고리즘, 가격, 계약 조건은 세부 수치와 고유 명칭을 제거하세요.",
}


def _line_offsets(text: str) -> list[int]:
    offsets: list[int] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        offsets.append(offset)
        offset += len(line)
    if not offsets:
        offsets.append(0)
    return offsets


def _short(value: str, limit: int = 160) -> str:
    return value[:limit] + ("..." if len(value) > limit else "")


def _line_quote(line: str) -> str:
    return line.strip() or line


def scan_by_rules(text: str, filename: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.split("\n")
    offsets = _line_offsets(text)

    if filename:
        base = filename.lower().split("/")[-1].split("\\")[-1]
        if base in SENSITIVE_FILES or base.endswith((".env", ".pem", ".key")):
            findings.append(
                Finding(
                    type="민감 설정 파일",
                    category="SECRET",
                    value=filename,
                    line=1,
                    severity="HIGH",
                    exact_quote=filename,
                    confidence=0.95,
                    reason=f"민감 정보가 포함될 수 있는 파일 형식입니다: {base}",
                    action="설정 파일 전체를 공유하지 말고 필요한 오류 메시지만 발췌하세요.",
                    source="rule",
                )
            )

    for line_no, line in enumerate(lines, 1):
        line_start = offsets[line_no - 1] if line_no - 1 < len(offsets) else 0
        line_quote = _line_quote(line)

        for pattern, label, category, reason in RISK_KEYWORDS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(
                    Finding(
                        type=label,
                        category=category,
                        value=_short(line_quote),
                        line=line_no,
                        severity="MEDIUM",
                        exact_quote=line_quote,
                        confidence=0.78,
                        reason=reason,
                        action=ACTION_BY_CATEGORY.get(category, "해당 문맥을 일반화해서 설명하세요."),
                        source="rule",
                    )
                )
                break

        for match in TABLE_PATTERN.finditer(line):
            quote = match.group()
            findings.append(
                Finding(
                    type="내부 테이블/엔티티명",
                    category="INFRA_INFO",
                    value=quote,
                    start=line_start + match.start(),
                    end=line_start + match.end(),
                    line=line_no,
                    severity="MEDIUM",
                    exact_quote=quote,
                    confidence=0.9,
                    reason="업무 도메인 테이블명 또는 엔티티명이 포함되어 있습니다.",
                    action="테이블명은 [MASKED_TABLE] 등으로 치환하세요.",
                    source="rule",
                )
            )

    return findings
