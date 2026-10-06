import re

from models.schemas import Finding

MASK_LABELS: dict[str, str] = {
    "AWS Access Key": "MASKED_AWS_KEY",
    "Private Key": "MASKED_PRIVATE_KEY",
    "JWT Token": "MASKED_JWT",
    "Password": "MASKED_PASSWORD",
    "API Key": "MASKED_API_KEY",
    "Bearer Token": "MASKED_TOKEN",
    "DB URL": "MASKED_DB_URL",
    "Internal IP": "MASKED_INTERNAL_IP",
    "Email": "MASKED_EMAIL",
    "Phone": "MASKED_PHONE",
    "Credit Card": "MASKED_CARD",
    "Internal Domain": "MASKED_DOMAIN",
    "내부 테이블/엔티티명": "MASKED_TABLE",
    "GitHub Token": "MASKED_API_KEY",
    "OpenAI API Key": "MASKED_API_KEY",
    "Anthropic API Key": "MASKED_API_KEY",
    "Slack Token": "MASKED_API_KEY",
    "Google API Key": "MASKED_API_KEY",
    "Stripe Secret Key": "MASKED_API_KEY",
    "Hugging Face Token": "MASKED_API_KEY",
    "Resident Registration Number": "MASKED_RRN",
    "Foreigner Registration Number": "MASKED_FOREIGNER_ID",
    "Corporate Registration Number": "MASKED_CORP_ID",
    "Business Registration Number": "MASKED_BRN",
    "Bank Account": "MASKED_ACCOUNT",
    "Passport Number": "MASKED_PASSPORT",
    "Driver License": "MASKED_DRIVER_LICENSE",
}

CATEGORY_MASK: dict[str, str] = {
    "SECRET": "MASKED_SECRET",
    "SOURCE_CODE": "MASKED_SOURCE",
    "TRADE_SECRET_CANDIDATE": "MASKED_INTERNAL_LOGIC",
    "CUSTOMER_INFO": "MASKED_CUSTOMER_INFO",
    "INFRA_INFO": "MASKED_INFRA",
}

# 겹치는 span이 있을 때 마스킹·표시에 남길 finding 우선순위 (클수록 우선)
TYPE_MASK_PRIORITY: dict[str, int] = {
    # 서비스별 형식으로 확인된 키는 일반 Bearer보다 우선한다("Bearer sk-proj-…"는 OpenAI 키 → 차단).
    "AWS Access Key": 103,
    "GitHub Token": 102,
    "OpenAI API Key": 102,
    "Anthropic API Key": 102,
    "Slack Token": 102,
    "Google API Key": 102,
    "Stripe Secret Key": 102,
    "Hugging Face Token": 102,
    "Bearer Token": 100,
    "Private Key": 95,
    "JWT Token": 85,
    "API Key": 80,
    "Password": 75,
    "DB URL": 70,
    "Resident Registration Number": 65,
    "Foreigner Registration Number": 65,
    "Passport Number": 62,
    "Driver License": 62,
    "Credit Card": 60,
    "Bank Account": 55,
    "Corporate Registration Number": 52,
    "Business Registration Number": 50,
    "Phone": 40,
    "Email": 35,
    "Internal IP": 30,
    "Internal Domain": 25,
}


def placeholder_for_finding(finding: Finding) -> str:
    label = MASK_LABELS.get(finding.type) or CATEGORY_MASK.get(finding.category, "MASKED")
    return f"[{label}]"


def _placeholder(finding: Finding) -> str:
    return placeholder_for_finding(finding)


def _span_len(f: Finding) -> int:
    assert f.start is not None and f.end is not None
    return f.end - f.start


def _mask_rank(f: Finding) -> tuple[int, int]:
    return (TYPE_MASK_PRIORITY.get(f.type, 0), _span_len(f))


def _contains(outer: Finding, inner: Finding) -> bool:
    return outer.start <= inner.start and inner.end <= outer.end


def _pick_span_winner(a: Finding, b: Finding) -> Finding:
    # 한쪽이 다른 쪽을 완전히 포함하면 바깥쪽 라벨을 쓴다(키 블록 안의 줄, 키워드 줄 안의 IP).
    if _contains(a, b) and not _contains(b, a):
        return a
    if _contains(b, a) and not _contains(a, b):
        return b
    return a if _mask_rank(a) >= _mask_rank(b) else b


def coalesce_span_findings(findings: list[Finding]) -> list[Finding]:
    """중첩·겹치는 span finding을 하나로 합쳐 마스킹 시 인덱스 깨짐을 방지한다."""
    span_findings = [
        f for f in findings if f.start is not None and f.end is not None and f.end > f.start
    ]
    span_ids = {id(f) for f in span_findings}
    other = [f for f in findings if id(f) not in span_ids]
    if not span_findings:
        return findings

    # 부분 겹침과 완전 포함을 한 번의 정렬 패스로 병합한다.
    span_findings.sort(key=lambda f: (f.start, f.end))
    merged: list[Finding] = []
    for f in span_findings:
        if merged and f.start < merged[-1].end:
            last = merged[-1]
            winner = _pick_span_winner(last, f)
            merged[-1] = winner.model_copy(
                update={"start": min(last.start, f.start), "end": max(last.end, f.end)}
            )
        else:
            merged.append(f)

    return other + merged


class PlaceholderMap:
    """같은 값에는 같은 번호를, 다른 값에는 새 번호를 붙인다([MASKED_PHONE_1], [MASKED_PHONE_2]).

    외부 AI가 답변에서 placeholder를 그대로 쓰면 어떤 값을 가리키는지 유지되고, entries로 원래 값을 되돌릴 수 있다.
    원래 값은 사용자가 보낸 원문에 이미 있던 것이며 검사 이력 DB에는 저장하지 않는다.
    """

    def __init__(self) -> None:
        self._by_value: dict[tuple[str, str], str] = {}
        self._counts: dict[str, int] = {}
        self.entries: list[dict[str, str]] = []

    def placeholder(self, finding: Finding, original: str) -> str:
        label = placeholder_for_finding(finding)[1:-1]
        key = (label, original)
        if key not in self._by_value:
            self._counts[label] = self._counts.get(label, 0) + 1
            placeholder = f"[{label}_{self._counts[label]}]"
            self._by_value[key] = placeholder
            self.entries.append({"placeholder": placeholder, "type": finding.type, "original": original})
        return self._by_value[key]

    def lookup(self, finding: Finding, original: str) -> str | None:
        return self._by_value.get((placeholder_for_finding(finding)[1:-1], original))


def mask_by_spans(text: str, findings: list[Finding], placeholders: PlaceholderMap | None = None) -> str:
    span_findings = sorted(
        (
            f
            for f in findings
            if f.start is not None and f.end is not None and 0 <= f.start < f.end <= len(text)
        ),
        key=lambda x: x.start,
    )
    if not span_findings:
        return text

    parts: list[str] = []
    cursor = 0
    for f in span_findings:
        if f.start < cursor:
            continue
        parts.append(text[cursor : f.start])
        original = text[f.start : f.end]
        parts.append(placeholders.placeholder(f, original) if placeholders is not None else _placeholder(f))
        cursor = f.end
    parts.append(text[cursor:])
    return "".join(parts)


def _line_findings_as_spans(text: str, findings: list[Finding]) -> list[Finding]:
    """줄 단위 finding을 원본 기준 span으로 바꾼다.

    span을 먼저 가린 뒤 원래 줄 번호로 줄을 가리면, 여러 줄짜리 키 블록이 한 placeholder가 된 아래부터
    줄 번호가 밀려 엉뚱한 줄이 가려졌다.
    """
    lines = text.split("\n")
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    spans: list[Finding] = []
    for f in findings:
        if f.start is not None or f.line is None or not 1 <= f.line <= len(lines):
            continue
        start = starts[f.line - 1]
        end = start + len(lines[f.line - 1])
        if end > start:
            spans.append(f.model_copy(update={"start": start, "end": end}))
    return spans


def apply_masking(text: str, findings: list[Finding], placeholders: PlaceholderMap | None = None) -> str:
    """placeholders를 주면 번호 붙은 placeholder를 쓰고 원래 값을 기록한다. 없으면 [MASKED_PHONE]처럼 라벨만 쓴다."""
    span_findings = [f for f in findings if f.start is not None and f.end is not None]
    coalesced = coalesce_span_findings(span_findings + _line_findings_as_spans(text, findings))
    return mask_by_spans(text, coalesced, placeholders)


def restore_placeholders(text: str, entries: list[dict[str, str]]) -> tuple[str, int]:
    """외부 AI 답변 속 placeholder를 원래 값으로 되돌린다. AI가 대괄호를 빼고 쓴 경우(MASKED_PHONE_1)도 처리한다."""
    mapping = {entry["placeholder"][1:-1]: entry["original"] for entry in entries if entry.get("placeholder")}
    if not mapping or not text:
        return text, 0
    names = "|".join(re.escape(name) for name in sorted(mapping, key=len, reverse=True))
    # 대괄호 없이 쓰면 영숫자 경계만 본다. \b는 한글도 단어 문자로 봐서 "MASKED_EMAIL_1로"를 놓친다.
    pattern = re.compile(rf"\[({names})\]|(?<![A-Za-z0-9_])({names})(?![A-Za-z0-9_])")
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return mapping[match.group(1) or match.group(2)]

    return pattern.sub(replace, text), count
