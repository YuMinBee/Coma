import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.regex_scanner import scan_by_regex
from services.rule_scanner import scan_by_rules
from services.masking import apply_masking, coalesce_span_findings


JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123"


def test_bearer_jwt_overlap_keeps_tail():
    text = f"Bearer {JWT} keep_this_tail"
    findings = scan_by_regex(text)

    # Bearer 값과 JWT가 같은 span이면 마스킹 우선순위가 높은 Bearer 하나만 남는다.
    types = {f.type for f in coalesce_span_findings(findings)}
    assert types == {"Bearer Token"}

    masked = apply_masking(text, findings)
    assert masked == "Bearer [MASKED_TOKEN] keep_this_tail"
    assert JWT not in masked


def test_coalesce_same_span_prefers_bearer():
    text = f"Bearer {JWT}"
    findings = scan_by_regex(text)
    coalesced = coalesce_span_findings(findings)
    assert len([f for f in coalesced if f.start is not None]) == 1
    assert coalesced[0].type == "Bearer Token"


def test_assignment_masks_value_and_keeps_key_name():
    text = "spring.datasource.password=Qwer1234!\nnext_line"
    masked = apply_masking(text, scan_by_regex(text))
    assert masked == "spring.datasource.password=[MASKED_PASSWORD]\nnext_line"


def test_private_key_body_is_masked():
    text = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEAsecretbody\n"
        "-----END RSA PRIVATE KEY-----\n"
        "after"
    )
    masked = apply_masking(text, scan_by_regex(text))
    assert "secretbody" not in masked
    assert masked == "[MASKED_PRIVATE_KEY]\nafter"


def test_truncated_private_key_is_masked_to_end():
    text = "config:\n-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA"
    masked = apply_masking(text, scan_by_regex(text))
    assert masked == "config:\n[MASKED_PRIVATE_KEY]"


if __name__ == "__main__":
    test_bearer_jwt_overlap_keeps_tail()
    test_coalesce_same_span_prefers_bearer()
    test_assignment_masks_value_and_keeps_key_name()
    test_private_key_body_is_masked()
    test_truncated_private_key_is_masked_to_end()
    print("all masking tests passed")


def test_line_masks_stay_on_the_right_line_after_a_multiline_key():
    # 키 블록(여러 줄)을 먼저 한 placeholder로 바꾸면 아래 줄 번호가 밀려 엉뚱한 줄이 가려졌다.
    text = (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAbody1\nbody2\n-----END RSA PRIVATE KEY-----\n"
        "정상 줄입니다\nprod deployment failed"
    )
    findings = scan_by_regex(text) + scan_by_rules(text)
    masked = apply_masking(text, findings)

    assert masked.split("\n") == ["[MASKED_PRIVATE_KEY]", "정상 줄입니다", "[MASKED_INFRA]"]
