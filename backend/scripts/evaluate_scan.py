"""
Run the SafePromptGuard v4.1 eval set.

Usage from the repository root:
  python backend/scripts/evaluate_scan.py
  python backend/scripts/evaluate_scan.py --dataset backend/eval/dataset.jsonl
  python backend/scripts/evaluate_scan.py --use-gemma
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.scanner import run_scan
from services.gitleaks_scanner import gitleaks_available

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


@dataclass
class EvalCase:
    case_id: str
    category: str
    text: str
    expected: dict[str, Any]
    sensitive_terms: list[str]
    filename: str | None = None
    notes: str = ""


@dataclass
class CaseResult:
    case: EvalCase
    actual: dict[str, Any]
    checks: dict[str, bool]
    latency_ms: int
    findings_count: int

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            expected = raw.get("expected", {})
            if not isinstance(expected, dict):
                raise ValueError(f"{path}:{line_no} expected must be an object")
            cases.append(
                EvalCase(
                    case_id=str(raw["id"]),
                    category=str(raw["category"]),
                    text=str(raw["text"]),
                    filename=raw.get("filename"),
                    sensitive_terms=list(raw.get("sensitive_terms", [])),
                    expected=expected,
                    notes=str(raw.get("notes", "")),
                )
            )
    return cases


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

    return CaseResult(
        case=case,
        actual=actual,
        checks=checks,
        latency_ms=latency_ms,
        findings_count=len(result.findings),
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


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    latencies = [result.latency_ms for result in results]
    checks_by_name: dict[str, list[bool]] = {name: [] for name in CHECK_NAMES}
    category_totals: dict[str, int] = {}
    category_passed: dict[str, int] = {}

    for result in results:
        category_totals[result.case.category] = category_totals.get(result.case.category, 0) + 1
        if result.passed:
            category_passed[result.case.category] = category_passed.get(result.case.category, 0) + 1
        for name, passed in result.checks.items():
            checks_by_name[name].append(passed)

    return {
        "total": len(results),
        "passed": sum(1 for result in results if result.passed),
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
    lines = [
        "# SafePromptGuard v4.2 Eval Report",
        "",
        f"> Generated: {generated_at}",
        f"> Dataset: `{display_dataset_path}`",
        f"> Gemma: {'ON' if use_gemma else 'OFF'}",
        f"> Gitleaks: {gitleaks_status}",
        "",
        "## Summary",
        "",
        f"- Case pass rate: {ratio_text(summary['passed'], summary['total'])}",
        f"- Latency avg/p50/p95/max: {summary['latency']['avg_ms']:.1f}ms / "
        f"{summary['latency']['p50_ms']}ms / {summary['latency']['p95_ms']}ms / "
        f"{summary['latency']['max_ms']}ms",
        "",
        "## Check Accuracy",
        "",
        "| Check | Accuracy |",
        "|---|---:|",
    ]
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

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| ID | Category | Pass | Action | Findings | Latency | Failed Checks |",
            "|---|---|---:|---|---:|---:|---|",
        ]
    )
    for result in results:
        failed = ", ".join(name for name, passed in result.checks.items() if not passed)
        lines.append(
            f"| {result.case.case_id} | {result.case.category} | "
            f"{'yes' if result.passed else 'no'} | "
            f"{result.actual['overall_action']} | {result.findings_count} | "
            f"{result.latency_ms}ms | {failed or '-'} |"
        )

    return "\n".join(lines) + "\n"


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def print_console_summary(summary: dict[str, Any]) -> None:
    print(f"Cases: {ratio_text(summary['passed'], summary['total'])}")
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
        help="Exit non-zero when any case has a failed expected check",
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

    if args.fail_on_mismatch and summary["passed"] != summary["total"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
