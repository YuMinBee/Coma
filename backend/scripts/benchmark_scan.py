"""
SafePrompt Guard — 스캔 성능 벤치마크.

사용 (backend 디렉터리에서):
  python scripts/benchmark_scan.py
  python scripts/benchmark_scan.py --iterations 5 --sizes 10000,100000
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constants import MAX_TEXT_CHARS
from services import gemma_analyzer
from services.scanner import run_scan

API_MAX_CHARS = MAX_TEXT_CHARS
TARGET_1MB_CHARS = MAX_TEXT_CHARS

SAMPLE_BLOCK = """\
spring.datasource.url=jdbc:mysql://prod-db.company.internal:3306/payment
spring.datasource.password=Qwer1234!
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhbGciOiJIUzI1NiJ9.sig
customer_payment table timeout in production
"""
FILLER_BLOCK = """\
서비스 장애 재현 절차와 로그 일부를 외부 AI에 공유하기 전 점검합니다.
민감하지 않은 설명 문장과 일반 코드 조각을 함께 포함해 실제 문서 입력에 가깝게 만듭니다.
def sanitize_prompt(payload):
    return payload.strip()
"""


def make_sample_block() -> str:
    return SAMPLE_BLOCK + (FILLER_BLOCK * 20)


def make_payload(char_count: int) -> str:
    if char_count <= 0:
        return ""
    parts: list[str] = []
    total = 0
    block = make_sample_block()
    while total < char_count:
        parts.append(block)
        total += len(block)
    return "".join(parts)[:char_count]


@dataclass
class BenchResult:
    label: str
    char_count: int
    use_gemma: bool
    gemma_available: bool
    iterations: int
    times_ms: list[int]
    findings_count: int
    risk_level: str

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.times_ms) if self.times_ms else 0.0

    @property
    def max_ms(self) -> int:
        return max(self.times_ms) if self.times_ms else 0

    @property
    def min_ms(self) -> int:
        return min(self.times_ms) if self.times_ms else 0


async def bench_one(char_count: int, use_gemma: bool, iterations: int) -> BenchResult:
    text = make_payload(char_count)
    gemma_available = await gemma_analyzer.check_model_available() if use_gemma else False
    times_ms: list[int] = []
    last = None

    for _ in range(iterations):
        started = time.perf_counter()
        last = await run_scan(text, use_gemma=use_gemma and gemma_available)
        times_ms.append(int((time.perf_counter() - started) * 1000))

    assert last is not None
    size_label = f"{char_count // 1000}KB" if char_count < 1_000_000 else f"{char_count / 1_000_000:.2f}MB"
    return BenchResult(
        label=size_label,
        char_count=char_count,
        use_gemma=use_gemma and gemma_available,
        gemma_available=gemma_available,
        iterations=iterations,
        times_ms=times_ms,
        findings_count=len(last.findings),
        risk_level=last.risk_level,
    )


def format_table(results: list[BenchResult], goal_ms: int = 5000) -> str:
    lines = [
        "| 크기 | Gemma | 반복 | 평균(ms) | 최소 | 최대 | 탐지 | 위험도 | 5초 이내 |",
        "|------|-------|------|----------|------|------|------|--------|----------|",
    ]
    for r in results:
        gemma_col = "ON" if r.use_gemma else "OFF"
        if r.use_gemma is False and r.gemma_available is False:
            gemma_col = "OFF (미연결)"
        ok = "✅" if r.mean_ms <= goal_ms else "❌"
        lines.append(
            f"| {r.label} ({r.char_count:,}자) | {gemma_col} | {r.iterations} | "
            f"{r.mean_ms:.0f} | {r.min_ms} | {r.max_ms} | {r.findings_count} | "
            f"{r.risk_level} | {ok} |"
        )
    return "\n".join(lines)


def build_report(results: list[BenchResult], meta: dict) -> str:
    table = format_table(results)
    gemma_method = (
        "- Gemma 생략: `--regex-only` 모드"
        if meta.get("mode") == "regex-only"
        else f"- Gemma ON: **{GEMMA_BENCH_MAX_CHARS:,}자 이하**만 (대용량은 정규식+규칙만 측정)"
    )
    return f"""# SafePrompt Guard — 성능 측정 결과

> 자동 생성: {meta['generated_at']}  
> 환경: {meta['platform']} · Python {meta['python']}  
> Gemma: {'연결됨 (' + meta['gemma_model'] + ')' if meta['gemma_available'] else '미연결 (정규식+규칙만)'}  
> API 입력 상한: **{API_MAX_CHARS:,}자** (약 {API_MAX_CHARS / 1024 / 1024:.2f}MiB)

## 목표 (과제 정량 지표)

- **1MB 이하** 텍스트 기준 **평균 5초(5000ms) 이내** 분석 결과 출력
- 실제 API는 Pydantic `max_length={API_MAX_CHARS}` 로 **최대 {API_MAX_CHARS:,}자**까지 허용

## 측정 방법

- `run_scan()` 직접 호출 (HTTP 업로드·네트워크 오버헤드 제외)
- 샘플: 일반 설명 문장에 설정·API Key·JWT·DB URL을 섞은 합성 텍스트
- 각 크기·모드별 **{meta['iterations']}회** 반복 후 평균/최소/최대(ms)
{gemma_method}

## 결과

{table}

## 요약

{meta['summary']}

## 재현

```bash
cd backend
.\\venv\\Scripts\\activate   # Windows
python scripts/benchmark_scan.py --iterations {meta['iterations']}
```
"""


# Gemma는 입력 상한(MAX_ANALYSIS_CHARS)만 문맥 분석 — 대용량은 1·2차만 추가 측정
GEMMA_BENCH_MAX_CHARS = 100_000


async def run_benchmarks(sizes: list[int], iterations: int) -> tuple[list[BenchResult], dict]:
    import platform

    gemma_available = (
        await gemma_analyzer.check_model_available()
        if GEMMA_BENCH_MAX_CHARS > 0
        else False
    )
    all_results: list[BenchResult] = []

    for size in sizes:
        all_results.append(await bench_one(size, use_gemma=False, iterations=iterations))
        if size <= GEMMA_BENCH_MAX_CHARS:
            all_results.append(await bench_one(size, use_gemma=True, iterations=iterations))

    regex_only = [r for r in all_results if not r.use_gemma]
    under_5s = sum(1 for r in regex_only if r.mean_ms <= 5000)
    summary_lines = [
        f"- 정규식+규칙만: {under_5s}/{len(regex_only)} 구간이 평균 5초 이내",
    ]
    if gemma_available:
        gemma_on = [r for r in all_results if r.use_gemma]
        g_ok = sum(1 for r in gemma_on if r.mean_ms <= 5000)
        summary_lines.append(f"- Gemma 포함: {g_ok}/{len(gemma_on)} 구간이 평균 5초 이내")
    else:
        summary_lines.append("- Gemma 미연결 — 3차 문맥 분석 시간은 별도 측정 필요")

    max_size = max(sizes) if sizes else 0
    if max_size >= API_MAX_CHARS * 0.9:
        summary_lines.append(
            f"- 최대 측정 크기 {max_size:,}자 = API 상한 근처 (과제 1MB 목표에 대응)"
        )
    skipped = [s for s in sizes if s > GEMMA_BENCH_MAX_CHARS]
    if skipped and gemma_available:
        summary_lines.append(
            f"- Gemma ON은 {GEMMA_BENCH_MAX_CHARS:,}자 이하만 측정 "
            f"(그 이상은 1·2차만, 문맥 분석 입력 상한 {gemma_analyzer.MAX_ANALYSIS_CHARS:,}자)"
        )

    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "gemma_available": gemma_available,
        "gemma_model": gemma_analyzer.DEFAULT_MODEL,
        "iterations": iterations,
        "mode": "regex-only" if GEMMA_BENCH_MAX_CHARS == 0 else "default",
        "summary": "\n".join(summary_lines),
    }
    return all_results, meta


def parse_sizes(raw: str) -> list[int]:
    sizes = [int(x.strip()) for x in raw.split(",") if x.strip()]
    return [min(s, API_MAX_CHARS) for s in sizes]


def default_sizes() -> list[int]:
    return [10_000, 50_000, 100_000, 500_000, TARGET_1MB_CHARS]


async def main() -> None:
    parser = argparse.ArgumentParser(description="SafePrompt Guard scan benchmark")
    parser.add_argument("--iterations", type=int, default=3, help="반복 횟수 (기본 3)")
    parser.add_argument(
        "--sizes",
        type=str,
        default=",".join(str(s) for s in default_sizes()),
        help="쉼표 구분 문자 수 (예: 10000,100000,500000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Markdown 저장 경로 (기본: ../docs/PERFORMANCE.md)",
    )
    parser.add_argument(
        "--regex-only",
        action="store_true",
        help="정규식+규칙만 측정 (Gemma 생략, 빠름)",
    )
    parser.add_argument(
        "--gemma-only",
        action="store_true",
        help="Gemma ON만 측정 (100KB 이하 크기)",
    )
    args = parser.parse_args()

    sizes = parse_sizes(args.sizes)
    if args.regex_only:
        global GEMMA_BENCH_MAX_CHARS
        GEMMA_BENCH_MAX_CHARS = 0
    if args.gemma_only:
        sizes = [s for s in sizes if s <= GEMMA_BENCH_MAX_CHARS]
        results = []
        gemma_available = await gemma_analyzer.check_model_available()
        for size in sizes:
            results.append(await bench_one(size, use_gemma=True, iterations=args.iterations))
        import platform

        meta = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "gemma_available": gemma_available,
            "gemma_model": gemma_analyzer.DEFAULT_MODEL,
            "iterations": args.iterations,
            "mode": "gemma-only",
            "summary": "- Gemma ON 전용 측정",
        }
    else:
        results, meta = await run_benchmarks(sizes, args.iterations)

    print(build_report(results, meta))
    print()

    out = Path(args.output) if args.output else Path(__file__).resolve().parents[2] / "docs" / "PERFORMANCE.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(results, meta), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
