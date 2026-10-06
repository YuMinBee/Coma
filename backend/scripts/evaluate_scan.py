"""
Run the SafePromptGuard eval set.

Usage from the repository root:
  python backend/scripts/evaluate_scan.py
  python backend/scripts/evaluate_scan.py --dataset backend/eval/dataset.jsonl
  python backend/scripts/evaluate_scan.py --use-gemma
  python backend/scripts/evaluate_scan.py --fail-on-mismatch   # CI gate (known failures excluded)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import statistics
import string
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import Finding
from services.gitleaks_scanner import gitleaks_available
from services.policy_engine import detector_for_finding
from services.scanner import run_scan

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "backend" / "eval" / "dataset.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "EVAL_REPORT.md"

CHECK_NAMES = (
    "detected",
    "masked",
    "blocked",
    "safe_prompt_null",
    "secret_leakage",
    "overall_action",
)

# 탐지기별 precision/recall은 값 단위 span을 내는 탐지기만 센다.
# 키워드 규칙은 줄 단위 신호라 span 정답과 비교할 수 없다.
SPAN_SOURCES = {"regex", "gitleaks"}

# 토큰 모양 문자열을 레포에 커밋하면 GitHub push protection·secret scanning이 막거나 경보를 낸다.
# 그래서 데이터셋에는 {{gen:이름}}만 두고 평가 시점에 결정적으로 생성한다.
_ALNUM = string.ascii_letters + string.digits
_URLSAFE = _ALNUM + "-_"
TOKEN_GENERATORS: dict[str, Any] = {
    "aws_key_id": lambda rng: "AKIA" + "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(16)),
    "github_token": lambda rng: "ghp_" + "".join(rng.choice(_ALNUM) for _ in range(36)),
    "openai_key": lambda rng: "sk-proj-" + "".join(rng.choice(_URLSAFE) for _ in range(48)),
    "anthropic_key": lambda rng: "sk-ant-api03-" + "".join(rng.choice(_URLSAFE) for _ in range(80)),
    "slack_token": lambda rng: "xoxb-"
    + "".join(rng.choice(string.digits) for _ in range(12))
    + "-"
    + "".join(rng.choice(string.digits) for _ in range(13))
    + "-"
    + "".join(rng.choice(_ALNUM) for _ in range(24)),
    "google_api_key": lambda rng: "AIza" + "".join(rng.choice(_URLSAFE) for _ in range(35)),
    "stripe_key": lambda rng: "sk_live_" + "".join(rng.choice(_ALNUM) for _ in range(24)),
    "hf_token": lambda rng: "hf_" + "".join(rng.choice(_ALNUM) for _ in range(34)),
    "bearer": lambda rng: "".join(rng.choice(_URLSAFE) for _ in range(40)),
}
TEMPLATE_RE = re.compile(r"\{\{gen:([a-z_]+)\}\}")


@dataclass
class ExpectedFinding:
    detector: str
    value: str


@dataclass
class EvalCase:
    case_id: str
    category: str
    text: str
    expected: dict[str, Any]
    sensitive_terms: list[str]
    expected_findings: list[ExpectedFinding] | None = None
    filename: str | None = None
    notes: str = ""
    known_failure: str | None = None


@dataclass
class DetectorTally:
    tp: int = 0
    fp: int = 0
    fn: int = 0


@dataclass
class CaseResult:
    case: EvalCase
    actual: dict[str, Any]
    checks: dict[str, bool]
    latency_ms: int
    findings_count: int
    tallies: dict[str, DetectorTally] = field(default_factory=dict)
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def expand_templates(value: str, case_id: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in TOKEN_GENERATORS:
            raise ValueError(f"{case_id}: unknown generator {name}")
        rng = random.Random(f"{case_id}:{name}")
        return TOKEN_GENERATORS[name](rng)

    return TEMPLATE_RE.sub(replace, value)


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            case_id = str(raw["id"])
            expected = raw.get("expected", {})
            if not isinstance(expected, dict):
                raise ValueError(f"{path}:{line_no} expected must be an object")

            expected_findings = None
            if "expected_findings" in raw:
                expected_findings = [
                    ExpectedFinding(
                        detector=str(item["detector"]),
                        value=expand_templates(str(item["value"]), case_id),
                    )
                    for item in raw["expected_findings"]
                ]

            cases.append(
                EvalCase(
                    case_id=case_id,
                    category=str(raw["category"]),
                    text=expand_templates(str(raw["text"]), case_id),
                    filename=raw.get("filename"),
                    sensitive_terms=[
                        expand_templates(str(term), case_id) for term in raw.get("sensitive_terms", [])
                    ],
                    expected=expected,
                    expected_findings=expected_findings,
                    notes=str(raw.get("notes", "")),
                    known_failure=raw.get("known_failure"),
                )
            )
    return cases


def redact(value: str, keep: int = 6) -> str:
    """리포트에 값 전체를 남기지 않는다(생성된 토큰이 커밋되면 secret scanning 경보가 난다)."""
    value = value.replace("\n", " ").replace("|", "/")
    if len(value) <= keep + 2:
        return value
    return f"{value[:keep]}…({len(value)})"


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def match_detectors(
    text: str,
    findings: list[Finding],
    expected: list[ExpectedFinding],
) -> tuple[dict[str, DetectorTally], list[str], list[str]]:
    """span이 겹치고 detector가 같으면 정답으로 센다. 값이 여러 번 나오면 모두 찾아야 한다.

    다른 정답 값 안에 들어 있는 위치(DB URL 안의 IP·비밀번호 등)는 채점하지 않는다. 겹치는 값은
    바깥 값 하나로 합쳐 가리는 설계라서다. 그 값이 출력에 남는지는 유출 검사(sensitive_terms)가 본다.
    """
    predicted = [
        (detector_for_finding(f), (f.start, f.end), f.exact_quote or f.value)
        for f in findings
        if f.source in SPAN_SOURCES and f.start is not None and f.end is not None
    ]
    occurrences: list[tuple[str, tuple[int, int], str]] = []
    for item in expected:
        start = text.find(item.value)
        if start == -1:
            raise ValueError(f"expected value not found in text: {item.value!r}")
        while start != -1:
            occurrences.append((item.detector, (start, start + len(item.value)), item.value))
            start = text.find(item.value, start + 1)
    targets = [
        target
        for target in occurrences
        if not any(
            other is not target
            and other[1][0] <= target[1][0]
            and target[1][1] <= other[1][1]
            and other[1][1] - other[1][0] > target[1][1] - target[1][0]
            for other in occurrences
        )
    ]

    tallies: dict[str, DetectorTally] = {}
    matched: set[int] = set()
    false_negatives: list[str] = []
    for detector, span, value in targets:
        tally = tallies.setdefault(detector, DetectorTally())
        hit = next(
            (
                index
                for index, (p_detector, p_span, _quote) in enumerate(predicted)
                if index not in matched and p_detector == detector and _overlaps(p_span, span)
            ),
            None,
        )
        if hit is None:
            tally.fn += 1
            false_negatives.append(f"{detector}:{redact(value)}")
        else:
            tally.tp += 1
            matched.add(hit)

    false_positives: list[str] = []
    for index, (detector, _span, quote) in enumerate(predicted):
        if index in matched:
            continue
        tallies.setdefault(detector, DetectorTally()).fp += 1
        false_positives.append(f"{detector}:{redact(quote)}")

    return tallies, false_positives, false_negatives


async def evaluate_case(
    case: EvalCase,
    *,
    use_gemma: bool,
    use_gitleaks: bool,
) -> CaseResult:
    started = time.perf_counter()
    result = await run_scan(
        case.text,
        use_gemma=use_gemma,
        use_gitleaks=use_gitleaks,
        filename=case.filename,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    safe_prompt = result.safe_prompt or ""
    leaked = has_secret_leakage(
        case.sensitive_terms,
        result.masked_text,
        safe_prompt,
    )
    actual = {
        "detected": len(result.findings) > 0,
        "masked": result.masked_text != case.text,
        "blocked": result.blocked,
        "safe_prompt_null": result.safe_prompt is None,
        "secret_leakage": leaked,
        "overall_action": result.overall_action,
    }

    checks = {}
    for name in CHECK_NAMES:
        if name in case.expected:
            checks[name] = actual[name] == case.expected[name]

    tallies: dict[str, DetectorTally] = {}
    false_positives: list[str] = []
    false_negatives: list[str] = []
    if case.expected_findings is not None:
        tallies, false_positives, false_negatives = match_detectors(
            case.text, result.findings, case.expected_findings
        )

    return CaseResult(
        case=case,
        actual=actual,
        checks=checks,
        latency_ms=latency_ms,
        findings_count=len(result.findings),
        tallies=tallies,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def has_secret_leakage(
    sensitive_terms: list[str],
    masked_text: str,
    safe_prompt: str,
) -> bool:
    haystack = f"{masked_text}\n{safe_prompt}"
    return any(term and term in haystack for term in sensitive_terms)


async def run_eval(
    cases: list[EvalCase],
    *,
    use_gemma: bool,
    use_gitleaks: bool,
) -> list[CaseResult]:
    results: list[CaseResult] = []
    for case in cases:
        results.append(
            await evaluate_case(
                case,
                use_gemma=use_gemma,
                use_gitleaks=use_gitleaks,
            )
        )
    return results


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    latencies = [result.latency_ms for result in results]
    checks_by_name: dict[str, list[bool]] = {name: [] for name in CHECK_NAMES}
    category_totals: dict[str, int] = {}
    category_passed: dict[str, int] = {}
    detector_totals: dict[str, DetectorTally] = {}

    for result in results:
        category_totals[result.case.category] = category_totals.get(result.case.category, 0) + 1
        if result.passed:
            category_passed[result.case.category] = category_passed.get(result.case.category, 0) + 1
        for name, passed in result.checks.items():
            checks_by_name[name].append(passed)
        for detector, tally in result.tallies.items():
            total = detector_totals.setdefault(detector, DetectorTally())
            total.tp += tally.tp
            total.fp += tally.fp
            total.fn += tally.fn

    gated = [result for result in results if not result.case.known_failure]
    micro = DetectorTally(
        tp=sum(t.tp for t in detector_totals.values()),
        fp=sum(t.fp for t in detector_totals.values()),
        fn=sum(t.fn for t in detector_totals.values()),
    )
    leaked_cases = [result for result in results if result.actual["secret_leakage"]]

    return {
        "total": len(results),
        "passed": sum(1 for result in results if result.passed),
        "gated_total": len(gated),
        "gated_passed": sum(1 for result in gated if result.passed),
        "leaked_cases": len(leaked_cases),
        "checks": {
            name: {
                "passed": sum(1 for passed in values if passed),
                "total": len(values),
            }
            for name, values in checks_by_name.items()
            if values
        },
        "categories": {
            category: {
                "passed": category_passed.get(category, 0),
                "total": total,
            }
            for category, total in sorted(category_totals.items())
        },
        "detectors": {
            detector: {"tp": t.tp, "fp": t.fp, "fn": t.fn, "prf": prf(t.tp, t.fp, t.fn)}
            for detector, t in sorted(detector_totals.items())
        },
        "micro": {"tp": micro.tp, "fp": micro.fp, "fn": micro.fn, "prf": prf(micro.tp, micro.fp, micro.fn)},
        "latency": {
            "avg_ms": statistics.mean(latencies) if latencies else 0,
            "p50_ms": percentile(latencies, 50),
            "p95_ms": percentile(latencies, 95),
            "max_ms": max(latencies) if latencies else 0,
        },
    }


def percentile(values: list[int], p: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * (p / 100))
    return ordered[index]


def ratio_text(passed: int, total: int) -> str:
    pct = (passed / total * 100) if total else 0
    return f"{passed}/{total} ({pct:.1f}%)"


def render_report(
    results: list[CaseResult],
    summary: dict[str, Any],
    *,
    dataset_path: Path,
    use_gemma: bool,
    use_gitleaks: bool,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    display_dataset_path = display_path(dataset_path)
    gitleaks_status = "ON" if use_gitleaks else "OFF"
    if use_gitleaks and not gitleaks_available():
        gitleaks_status = "ON (not installed, skipped)"
    micro_p, micro_r, micro_f1 = summary["micro"]["prf"]
    lines = [
        "# SafePromptGuard v5 Eval Report",
        "",
        f"> Generated: {generated_at}",
        f"> Dataset: `{display_dataset_path}` ({summary['total']} cases)",
        f"> Gemma: {'ON' if use_gemma else 'OFF'}",
        f"> Gitleaks: {gitleaks_status}",
        "",
        "## Summary",
        "",
        f"- Case pass rate: {ratio_text(summary['passed'], summary['total'])}",
        f"- Case pass rate excluding known failures: "
        f"{ratio_text(summary['gated_passed'], summary['gated_total'])}",
        f"- Span detectors (micro): precision {micro_p:.3f} / recall {micro_r:.3f} / F1 {micro_f1:.3f} "
        f"(TP {summary['micro']['tp']}, FP {summary['micro']['fp']}, FN {summary['micro']['fn']})",
        f"- Cases with a sensitive term left in the output: {summary['leaked_cases']}",
        f"- Latency avg/p50/p95/max: {summary['latency']['avg_ms']:.1f}ms / "
        f"{summary['latency']['p50_ms']}ms / {summary['latency']['p95_ms']}ms / "
        f"{summary['latency']['max_ms']}ms",
        "",
        "## Detector Precision / Recall",
        "",
        "Value-level spans from regex/gitleaks detectors. A prediction counts as correct when its",
        "detector matches and its span overlaps the expected value. Keyword rules are line-level",
        "signals and are measured only through the case checks below.",
        "",
        "| Detector | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for detector, item in summary["detectors"].items():
        precision, recall, f1 = item["prf"]
        lines.append(
            f"| {detector} | {item['tp']} | {item['fp']} | {item['fn']} | "
            f"{precision:.3f} | {recall:.3f} | {f1:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Check Accuracy",
            "",
            "| Check | Accuracy |",
            "|---|---:|",
        ]
    )
    for name, item in summary["checks"].items():
        lines.append(f"| {name} | {ratio_text(item['passed'], item['total'])} |")

    lines.extend(
        [
            "",
            "## Category Pass Rate",
            "",
            "| Category | Pass Rate |",
            "|---|---:|",
        ]
    )
    for category, item in summary["categories"].items():
        lines.append(f"| {category} | {ratio_text(item['passed'], item['total'])} |")

    known = [result for result in results if result.case.known_failure]
    if known:
        lines.extend(
            [
                "",
                "## Known Limitations",
                "",
                "These cases document behavior we have not fixed yet. They stay in the report but",
                "are excluded from the CI gate.",
                "",
                "| ID | Pass | Reason |",
                "|---|---:|---|",
            ]
        )
        for result in known:
            lines.append(
                f"| {result.case.case_id} | {'yes' if result.passed else 'no'} | {result.case.known_failure} |"
            )

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| ID | Category | Pass | Action | Findings | Latency | Failed Checks | Detector errors |",
            "|---|---|---:|---|---:|---:|---|---|",
        ]
    )
    for result in results:
        failed = ", ".join(name for name, passed in result.checks.items() if not passed)
        errors = [f"FN {item}" for item in result.false_negatives] + [
            f"FP {item}" for item in result.false_positives
        ]
        lines.append(
            f"| {result.case.case_id} | {result.case.category} | "
            f"{'yes' if result.passed else 'no'} | "
            f"{result.actual['overall_action']} | {result.findings_count} | "
            f"{result.latency_ms}ms | {failed or '-'} | {'; '.join(errors) or '-'} |"
        )

    return "\n".join(lines) + "\n"


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def print_console_summary(summary: dict[str, Any]) -> None:
    micro_p, micro_r, micro_f1 = summary["micro"]["prf"]
    print(f"Cases: {ratio_text(summary['passed'], summary['total'])}")
    print(f"Cases excluding known failures: {ratio_text(summary['gated_passed'], summary['gated_total'])}")
    print(f"Span detectors (micro): P {micro_p:.3f} / R {micro_r:.3f} / F1 {micro_f1:.3f}")
    print(f"Leaked cases: {summary['leaked_cases']}")
    print(
        "Latency avg/p50/p95/max: "
        f"{summary['latency']['avg_ms']:.1f}ms / "
        f"{summary['latency']['p50_ms']}ms / "
        f"{summary['latency']['p95_ms']}ms / "
        f"{summary['latency']['max_ms']}ms"
    )
    print()
    for name, item in summary["checks"].items():
        print(f"{name}: {ratio_text(item['passed'], item['total'])}")


async def async_main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SafePromptGuard scan behavior.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="JSONL eval dataset")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown report path")
    parser.add_argument("--use-gemma", action="store_true", help="Enable local Gemma analysis")
    parser.add_argument(
        "--no-gitleaks",
        action="store_true",
        help="Disable optional Gitleaks detector during evaluation",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Exit non-zero when a case outside the known-failure list fails",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)
    use_gitleaks = not args.no_gitleaks
    cases = load_cases(dataset_path)
    results = await run_eval(
        cases,
        use_gemma=args.use_gemma,
        use_gitleaks=use_gitleaks,
    )
    summary = summarize(results)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_report(
            results,
            summary,
            dataset_path=dataset_path,
            use_gemma=args.use_gemma,
            use_gitleaks=use_gitleaks,
        ),
        encoding="utf-8",
    )

    print_console_summary(summary)
    print(f"\nSaved: {output_path}")

    if args.fail_on_mismatch and summary["gated_passed"] != summary["gated_total"]:
        failed = [r.case.case_id for r in results if not r.case.known_failure and not r.passed]
        print(f"Failed cases: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
