import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from main import app
from scripts.evaluate_scan import load_cases
from services.masking import PlaceholderMap, apply_masking, restore_placeholders
from services.regex_scanner import scan_by_regex
from services.scanner import run_scan


EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


def scan(text: str):
    return asyncio.run(run_scan(text, use_gemma=False, use_gitleaks=False))


def test_same_value_gets_same_number_and_new_values_new_numbers():
    text = "담당 010-1234-5678, 대리 010-9876-5432, 다시 010-1234-5678 로 연락"
    result = scan(text)

    assert result.masked_text == "담당 [MASKED_PHONE_1], 대리 [MASKED_PHONE_2], 다시 [MASKED_PHONE_1] 로 연락"
    assert [(p.placeholder, p.original) for p in result.placeholders] == [
        ("[MASKED_PHONE_1]", "010-1234-5678"),
        ("[MASKED_PHONE_2]", "010-9876-5432"),
    ]
    assert [f.masked_value for f in result.findings] == ["[MASKED_PHONE_1]", "[MASKED_PHONE_2]", "[MASKED_PHONE_1]"]


def test_masked_text_restores_to_the_original():
    text = "spring.datasource.password=Qwer1234!\n문의: minji.kim@naver.com / 192.168.0.10"
    result = scan(text)
    restored, count = restore_placeholders(result.masked_text, [p.model_dump() for p in result.placeholders])

    assert restored == text
    assert count == 3


def test_restore_handles_ai_answers_that_drop_brackets():
    entries = [{"placeholder": "[MASKED_EMAIL_1]", "type": "Email", "original": "minji.kim@naver.com"}]
    restored, count = restore_placeholders("MASKED_EMAIL_1 주소로 다시 보내세요. [MASKED_EMAIL_1] 확인", entries)

    assert restored == "minji.kim@naver.com 주소로 다시 보내세요. minji.kim@naver.com 확인"
    assert count == 2


def test_restore_handles_korean_particles_after_bare_names():
    entries = [{"placeholder": "[MASKED_EMAIL_1]", "type": "Email", "original": "minji.kim@naver.com"}]
    restored, count = restore_placeholders("MASKED_EMAIL_1로 회신하고 `MASKED_EMAIL_1`은 참조에 넣으세요", entries)

    assert restored == "minji.kim@naver.com로 회신하고 `minji.kim@naver.com`은 참조에 넣으세요"
    assert count == 2


def test_restore_does_not_touch_longer_names():
    entries = [{"placeholder": "[MASKED_PHONE_1]", "type": "Phone", "original": "010-1111-2222"}]
    restored, count = restore_placeholders("[MASKED_PHONE_10], MASKED_PHONE_12 와 [MASKED_PHONE_1]", entries)

    assert restored == "[MASKED_PHONE_10], MASKED_PHONE_12 와 010-1111-2222"
    assert count == 1


def test_restore_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/restore",
        json={
            "text": "[MASKED_PHONE_1]로 연락하세요",
            "placeholders": [{"placeholder": "[MASKED_PHONE_1]", "type": "Phone", "original": "010-1234-5678"}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"restored_text": "010-1234-5678로 연락하세요", "replaced_count": 1}


def test_placeholder_map_without_numbering_keeps_legacy_labels():
    text = "연락처 010-1234-5678"
    assert apply_masking(text, scan_by_regex(text)) == "연락처 [MASKED_PHONE]"
    assert apply_masking(text, scan_by_regex(text), PlaceholderMap()) == "연락처 [MASKED_PHONE_1]"


def test_masked_output_is_clean_when_scanned_again():
    # 번호 placeholder도 allowlist에 걸려야 마스킹 결과를 다시 검사했을 때 새 탐지가 생기지 않는다.
    masked_cases = 0
    for name in ("dataset.jsonl", "blind_dev.jsonl", "blind_test.jsonl"):
        for case in load_cases(EVAL_DIR / name):
            first = scan(case.text)
            if not first.placeholders:
                continue
            masked_cases += 1
            assert scan(first.masked_text).findings == [], case.case_id
    assert masked_cases > 150
