from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from models.schemas import Finding, PolicyDecision

PolicyAction = Literal["allow", "mask", "block"]

ACTION_PRIORITY: dict[PolicyAction, int] = {
    "allow": 0,
    "mask": 1,
    "block": 2,
}

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "policy.yaml"

TYPE_DETECTOR_MAP = {
    "AWS Access Key": "api_key",
    "API Key": "api_key",
    "GitHub Token": "api_key",
    "OpenAI API Key": "api_key",
    "Anthropic API Key": "api_key",
    "Slack Token": "api_key",
    "Google API Key": "api_key",
    "Stripe Secret Key": "api_key",
    "Hugging Face Token": "api_key",
    "Private Key": "private_key",
    "JWT Token": "token",
    "Bearer Token": "token",
    "Password": "password",
    "DB URL": "db_url",
    "Internal IP": "internal_ip",
    "Internal Domain": "internal_domain",
    "Email": "email",
    "Phone": "phone",
    "Credit Card": "credit_card",
    "Resident Registration Number": "resident_registration_number",
    "Foreigner Registration Number": "foreigner_registration_number",
    "Corporate Registration Number": "corporate_registration_number",
    "Business Registration Number": "business_registration_number",
    "Bank Account": "bank_account",
    "Passport Number": "passport_number",
    "Driver License": "driver_license",
}

CATEGORY_DETECTOR_MAP = {
    "SECRET": "secret",
    "INFRA_INFO": "infra_info",
    "CUSTOMER_INFO": "customer_info",
    "SOURCE_CODE": "source_code",
    "TRADE_SECRET_CANDIDATE": "trade_secret_candidate",
}

SEVERITY_ALIASES = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


class PolicyCondition(BaseModel):
    # contains: 유형·값 어디든 부분 일치 / equals: 값 전체 일치 / matches: 값 전체 정규식 일치
    contains: str | None = None
    equals: str | None = None
    matches: str | None = None

    @field_validator("matches")
    @classmethod
    def validate_pattern(cls, value: str | None) -> str | None:
        if value is not None:
            re.compile(value)
        return value

    def is_empty(self) -> bool:
        return not (self.contains or self.equals or self.matches)


class PolicyRule(BaseModel):
    id: str
    detector: str
    severity: str | None = None
    action: PolicyAction
    condition: PolicyCondition | None = None
    priority: int = 0

    @field_validator("detector")
    @classmethod
    def normalize_detector(cls, value: str) -> str:
        detector = normalize_token(value)
        if not detector:
            raise ValueError("policy detector must not be empty")
        return detector

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: str | None) -> str | None:
        if value is None:
            return None
        severity = normalize_severity(value)
        if severity is None:
            raise ValueError("policy severity must be critical, high, medium, or low")
        return severity

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: Any) -> str:
        return str(value).strip().lower()


class PolicyConfig(BaseModel):
    policies: list[PolicyRule] = Field(default_factory=list)


class PolicyEvaluation(BaseModel):
    overall_action: PolicyAction
    blocked: bool
    blocked_reason: str | None = None
    policy_decisions: list[PolicyDecision] = Field(default_factory=list)


def normalize_token(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_severity(value: str | None) -> str | None:
    if value is None:
        return None
    return SEVERITY_ALIASES.get(str(value).strip().lower())


def detector_for_finding(finding: Finding) -> str:
    if finding.detector:
        return normalize_token(finding.detector)
    if finding.type in TYPE_DETECTOR_MAP:
        return TYPE_DETECTOR_MAP[finding.type]
    if finding.category in CATEGORY_DETECTOR_MAP:
        return CATEGORY_DETECTOR_MAP[finding.category]
    return normalize_token(finding.type or finding.category or finding.source)


def load_policy_config(path: str | Path | None = None) -> PolicyConfig:
    policy_path = Path(path) if path else DEFAULT_POLICY_PATH
    try:
        raw = policy_path.read_text(encoding="utf-8")
        data = _load_yaml(raw)
        return PolicyConfig.model_validate(data or {})
    except Exception:
        return PolicyConfig()


def evaluate_findings(
    findings: list[Finding],
    policy_config: PolicyConfig | None = None,
) -> PolicyEvaluation:
    if not findings:
        return PolicyEvaluation(overall_action="allow", blocked=False)

    config = policy_config if policy_config is not None else load_policy_config()
    decisions: list[PolicyDecision] = []

    for index, finding in enumerate(findings):
        detector = detector_for_finding(finding)
        policy = _select_policy(finding, detector, config.policies)
        if policy:
            decisions.append(
                PolicyDecision(
                    finding_index=index,
                    detector=detector,
                    policy_id=policy.id,
                    policy_action=policy.action,
                    decision_reason=f"Policy {policy.id} matched detector {detector}.",
                )
            )
        else:
            decisions.append(
                PolicyDecision(
                    finding_index=index,
                    detector=detector,
                    policy_id=None,
                    policy_action="mask",
                    decision_reason=(
                        f"No policy matched detector {detector}; defaulting to mask."
                    ),
                )
            )

    overall_action = max(
        (decision.policy_action for decision in decisions),
        key=lambda action: ACTION_PRIORITY[action],
    )
    blocked = overall_action == "block"
    return PolicyEvaluation(
        overall_action=overall_action,
        blocked=blocked,
        blocked_reason=_blocked_reason(decisions) if blocked else None,
        policy_decisions=decisions,
    )


def findings_for_actions(
    findings: list[Finding],
    decisions: list[PolicyDecision],
    actions: set[PolicyAction],
) -> list[Finding]:
    by_index = {decision.finding_index: decision for decision in decisions}
    return [
        finding
        for index, finding in enumerate(findings)
        if by_index.get(index) and by_index[index].policy_action in actions
    ]


def _select_policy(
    finding: Finding,
    detector: str,
    policies: list[PolicyRule],
) -> PolicyRule | None:
    matches = [
        policy
        for policy in policies
        if _policy_matches_finding(policy, finding, detector)
    ]
    if not matches:
        return None
    # 예외 규칙이 동작하도록 구체적인 규칙(조건·심각도 지정)이 일반 규칙보다 우선한다.
    # 같은 수준끼리는 더 강한 조치를 고른다.
    return max(
        matches,
        key=lambda policy: (
            policy.priority,
            _specificity(policy),
            ACTION_PRIORITY[policy.action],
        ),
    )


def _specificity(policy: PolicyRule) -> int:
    score = 0
    if policy.condition and not policy.condition.is_empty():
        score += 2
    if policy.severity is not None:
        score += 1
    return score


def _policy_matches_finding(
    policy: PolicyRule,
    finding: Finding,
    detector: str,
) -> bool:
    if policy.detector != detector:
        return False

    if policy.severity is not None:
        finding_severity = normalize_severity(finding.severity)
        if policy.severity != finding_severity:
            return False

    condition = policy.condition
    if condition is None:
        return True

    value = finding.exact_quote or finding.value
    if condition.equals is not None and value != condition.equals:
        return False

    if condition.matches is not None and not re.fullmatch(condition.matches, value):
        return False

    if condition.contains:
        needle = condition.contains.lower()
        haystack = "\n".join(
            part
            for part in (
                finding.type,
                finding.category,
                finding.value,
                finding.exact_quote,
            )
            if part
        ).lower()
        if needle not in haystack:
            return False

    return True


def _blocked_reason(decisions: list[PolicyDecision]) -> str | None:
    block_decision = next(
        (decision for decision in decisions if decision.policy_action == "block"),
        None,
    )
    if not block_decision:
        return None
    policy = block_decision.policy_id or "default"
    detector = block_decision.detector or "unknown"
    return f"Blocked by policy {policy} for detector {detector}."


def _load_yaml(raw: str) -> dict[str, Any]:
    try:
        import yaml

        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _load_simple_policy_yaml(raw)


def _load_simple_policy_yaml(raw: str) -> dict[str, Any]:
    policies: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_condition: dict[str, Any] | None = None

    for raw_line in raw.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip() or line.strip() == "policies:":
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                policies.append(current)
            current = {}
            current_condition = None
            key, value = _split_yaml_pair(stripped[2:])
            if key:
                current[key] = value
            continue

        if current is None:
            continue

        key, value = _split_yaml_pair(stripped)
        if not key:
            continue
        if key == "condition":
            current_condition = {}
            current["condition"] = current_condition
            continue
        if current_condition is not None and key in {"contains", "equals", "matches"}:
            current_condition[key] = value
        else:
            current[key] = value

    if current:
        policies.append(current)

    return {"policies": policies}


def _split_yaml_pair(text: str) -> tuple[str | None, str | None]:
    if ":" not in text:
        return None, None
    key, value = text.split(":", 1)
    value = value.strip().strip("\"'")
    return key.strip(), value or None
