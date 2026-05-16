from models.schemas import Finding, ScanResponse
from services.regex_scanner import scan_by_regex
from services.rule_scanner import scan_by_rules
from services import gemma_analyzer
from services.masking import apply_masking

SOURCE_ORDER = {
    "gemma": 0,
    "regex": 1,
    "rule": 2,
}


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    seen_spans: set[tuple[int, int, str]] = set()
    result: list[Finding] = []
    for f in findings:
        if f.start is not None and f.end is not None:
            span_key = (f.start, f.end, f.category)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)

        key = f"{f.category}:{f.type}:{f.line}:{f.start}:{f.end}:{f.value[:60].lower()}"
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (
            SOURCE_ORDER.get(f.source, 99),
            f.line if f.line is not None else 999_999,
            f.start if f.start is not None else 999_999,
        ),
    )


def _compute_risk(findings: list[Finding], gemma_level: str) -> tuple[str, int]:
    score = 0
    for f in findings:
        if f.severity == "HIGH":
            score += 25
        elif f.severity == "MEDIUM":
            score += 12
        else:
            score += 5

    if gemma_level == "HIGH":
        score += 20
    elif gemma_level == "MEDIUM":
        score += 10

    score = min(score, 100)

    if score >= 50:
        level = "높음"
    elif score >= 25:
        level = "중간"
    else:
        level = "낮음"

    return level, score


def _detected_items(findings: list[Finding]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    type_map = {
        "AWS Access Key": "AWS Access Key",
        "Password": "DB/서비스 비밀번호",
        "API Key": "API Key / Secret",
        "DB URL": "DB 접속 URL",
        "Internal Domain": "내부 도메인",
        "내부 테이블/엔티티명": "내부 테이블명",
        "민감 설정 파일": "민감 설정 파일",
        "영업비밀 후보": "영업비밀 후보 문장",
        "고객/계약 정보": "고객·계약 정보",
    }
    for f in findings:
        label = type_map.get(f.type, f.type)
        if label not in seen:
            seen.add(label)
            items.append(label)
    return items


def _recommendations(risk_level: str, findings: list[Finding]) -> list[str]:
    recs: list[str] = []
    if risk_level == "높음":
        recs.append("외부 AI에 입력하기 전 반드시 민감정보를 제거해야 합니다.")
        recs.append("마스킹된 안전 프롬프트만 복사하여 사용하세요.")
    elif risk_level == "중간":
        recs.append("일부 민감 정보가 포함되어 있을 수 있습니다. 마스킹 결과를 확인하세요.")
    else:
        recs.append("상대적으로 안전하지만, 공유 전 한 번 더 검토하는 것을 권장합니다.")

    if any(f.category == "TRADE_SECRET_CANDIDATE" for f in findings):
        recs.append("내부 알고리즘·업무 로직 설명은 일반화하여 질문하세요.")
    if any(f.type == "민감 설정 파일" for f in findings):
        recs.append("설정 파일(.env 등) 전체 업로드는 피하고, 필요한 오류 메시지만 공유하세요.")

    return recs


async def run_scan(text: str, use_gemma: bool = True, filename: str | None = None) -> ScanResponse:
    regex_findings = scan_by_regex(text)
    rule_findings = scan_by_rules(text, filename)
    all_findings = _dedupe_findings(regex_findings + rule_findings)

    gemma_available = await gemma_analyzer.check_ollama_available()
    gemma_used = False
    gemma_level = "LOW"
    gemma_summary = ""

    if use_gemma and gemma_available:
        gemma_findings, gemma_level, gemma_summary = await gemma_analyzer.analyze_with_gemma(text)
        all_findings = _dedupe_findings(all_findings + gemma_findings)
        gemma_used = True

    all_findings = _sort_findings(all_findings)

    risk_level, risk_score = _compute_risk(all_findings, gemma_level)
    masked_text = apply_masking(text, all_findings)

    safe_prompt: str
    if gemma_used:
        generated = await gemma_analyzer.generate_safe_prompt(masked_text, gemma_summary)
        safe_prompt = generated or gemma_analyzer.fallback_safe_prompt(masked_text, all_findings)
    else:
        safe_prompt = gemma_analyzer.fallback_safe_prompt(masked_text, all_findings)

    return ScanResponse(
        risk_level=risk_level,
        risk_score=risk_score,
        findings=all_findings,
        detected_items=_detected_items(all_findings),
        recommendations=_recommendations(risk_level, all_findings),
        masked_text=masked_text,
        safe_prompt=safe_prompt,
        gemma_available=gemma_available,
        gemma_used=gemma_used,
    )
