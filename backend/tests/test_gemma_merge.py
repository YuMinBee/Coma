import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import Finding
from services import gemma_analyzer, scanner
from services.policy_engine import PolicyConfig, PolicyRule

# 키 모양 문자열을 그대로 커밋하면 secret scanning 경보가 날 수 있어 실행 시점에 합친다.
AWS_KEY = "AKIA" + "VW3Q7R2T9YK4MZ8P"


def _fake_gemma(monkeypatch, quote_of):
    async def available(*_args, **_kwargs):
        return True

    async def analyze(text):
        quote = quote_of(text)
        start = text.index(quote)
        return [
            Finding(
                type="비밀정보",
                category="SECRET",
                value=quote,
                start=start,
                end=start + len(quote),
                line=1,
                severity="HIGH",
                exact_quote=quote,
                confidence=0.7,
                source="gemma",
            )
        ], "HIGH", ""

    async def safe_prompt(*_args, **_kwargs):
        return None

    monkeypatch.setattr(gemma_analyzer, "check_model_available", available)
    monkeypatch.setattr(gemma_analyzer, "analyze_with_gemma", analyze)
    monkeypatch.setattr(gemma_analyzer, "generate_safe_prompt", safe_prompt)


def test_gemma_line_finding_does_not_hide_a_verified_key(monkeypatch):
    # Gemma가 줄 전체를 짚었을 때 정규식이 찾은 AWS 키가 사라져 block 정책이 적용되지 않았다.
    text = f"aws_access_key_id = {AWS_KEY}  # prod 계정"
    _fake_gemma(monkeypatch, lambda t: t)
    config = PolicyConfig(policies=[PolicyRule(id="api_key.block", detector="api_key", severity="critical", action="block")])

    result = asyncio.run(scanner.run_scan(text, use_gemma=True, use_gitleaks=False, policy_config=config))

    assert any(f.type == "AWS Access Key" for f in result.findings)
    assert result.blocked is True
    assert AWS_KEY not in result.masked_text
