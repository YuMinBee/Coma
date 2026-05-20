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
    "Bearer Token": 100,
    "Private Key": 95,
    "AWS Access Key": 90,
    "JWT Token": 85,
    "API Key": 80,
    "Password": 75,
    "DB URL": 70,
}


def _placeholder(finding: Finding) -> str:
    label = MASK_LABELS.get(finding.type) or CATEGORY_MASK.get(finding.category, "MASKED")
    return f"[{label}]"


def _span_len(f: Finding) -> int:
    assert f.start is not None and f.end is not None
    return f.end - f.start


def _mask_rank(f: Finding) -> tuple[int, int]:
    return (TYPE_MASK_PRIORITY.get(f.type, 0), _span_len(f))


def _pick_span_winner(a: Finding, b: Finding) -> Finding:
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


def mask_by_spans(text: str, findings: list[Finding]) -> str:
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
        parts.append(_placeholder(f))
        cursor = f.end
    parts.append(text[cursor:])
    return "".join(parts)


def mask_by_lines(text: str, findings: list[Finding]) -> str:
    lines = text.split("\n")
    lines_to_mask: dict[int, str] = {}

    for f in findings:
        if f.line is None or f.start is not None:
            continue
        if f.line not in lines_to_mask:
            lines_to_mask[f.line] = _placeholder(f)

    for line_no, placeholder in lines_to_mask.items():
        idx = line_no - 1
        if 0 <= idx < len(lines):
            lines[idx] = placeholder

    return "\n".join(lines)


def apply_masking(text: str, findings: list[Finding]) -> str:
    coalesced = coalesce_span_findings(findings)
    masked = mask_by_spans(text, coalesced)
    return mask_by_lines(masked, coalesced)
