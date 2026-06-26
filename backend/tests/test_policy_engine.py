import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import Finding
from services.policy_engine import (
    PolicyCondition,
    PolicyConfig,
    PolicyRule,
    evaluate_findings,
)
from services.scanner import run_scan


def make_finding(
    *,
    finding_type: str = "API Key",
    value: str = 'API_KEY = "real-secret-123"',
    severity: str = "HIGH",
) -> Finding:
    return Finding(
        type=finding_type,
        category="SECRET",
        value=value,
        start=0,
        end=len(value),
        line=1,
        severity=severity,
        exact_quote=value,
        source="regex",
    )


def test_policy_block_priority():
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="secret.api_key.mask",
                detector="api_key",
                severity="critical",
                action="mask",
            ),
            PolicyRule(
                id="secret.api_key.block",
                detector="api_key",
                severity="critical",
                action="block",
            ),
        ]
    )

    result = evaluate_findings([make_finding()], config)

    assert result.overall_action == "block"
    assert result.blocked is True
    assert result.policy_decisions[0].policy_action == "block"
    assert result.policy_decisions[0].policy_id == "secret.api_key.block"


def test_policy_mask_when_no_block():
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="secret.api_key.mask",
                detector="api_key",
                severity="critical",
                action="mask",
            )
        ]
    )

    result = evaluate_findings([make_finding()], config)

    assert result.overall_action == "mask"
    assert result.blocked is False
    assert result.policy_decisions[0].policy_action == "mask"


def test_policy_allow_excludes_masking():
    text = 'API_KEY = "example-token-123"'
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="dummy.secret.allow",
                detector="api_key",
                severity="critical",
                action="allow",
                condition=PolicyCondition(contains="example"),
            )
        ]
    )

    result = asyncio.run(run_scan(text, use_gemma=False, policy_config=config))

    assert result.overall_action == "allow"
    assert result.findings
    assert "[MASKED_API_KEY]" not in result.masked_text
    assert "example-token-123" in result.masked_text


def test_unmatched_finding_defaults_to_mask():
    text = 'API_KEY = "real-token-123"'
    result = asyncio.run(run_scan(text, use_gemma=False, policy_config=PolicyConfig()))

    assert result.overall_action == "mask"
    assert result.blocked is False
    assert "[MASKED_API_KEY]" in result.masked_text


def test_block_response_safe_prompt_is_none():
    text = 'API_KEY = "real-secret-123"'
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="secret.api_key.block",
                detector="api_key",
                severity="critical",
                action="block",
            )
        ]
    )

    result = asyncio.run(run_scan(text, use_gemma=False, policy_config=config))

    assert result.overall_action == "block"
    assert result.blocked is True
    assert result.safe_prompt is None
    assert result.blocked_reason is not None
    assert "real-secret-123" not in result.blocked_reason


def test_existing_response_fields_exist():
    result = asyncio.run(run_scan("hello", use_gemma=False, policy_config=PolicyConfig()))

    assert hasattr(result, "masked_text")
    assert hasattr(result, "safe_prompt")
    assert hasattr(result, "findings")
    assert result.masked_text == "hello"
    assert result.safe_prompt == ""
    assert result.findings == []


def test_default_policy_yaml_blocks_api_key():
    result = asyncio.run(run_scan('API_KEY = "real-token-123"', use_gemma=False))

    assert result.overall_action == "block"
    assert result.blocked is True
    assert result.safe_prompt is None
    assert any(
        decision.policy_id == "secret.api_key.block"
        and decision.policy_action == "block"
        for decision in result.policy_decisions
    )


if __name__ == "__main__":
    test_policy_block_priority()
    test_policy_mask_when_no_block()
    test_policy_allow_excludes_masking()
    test_unmatched_finding_defaults_to_mask()
    test_block_response_safe_prompt_is_none()
    test_existing_response_fields_exist()
    test_default_policy_yaml_blocks_api_key()
    print("policy engine tests passed")
