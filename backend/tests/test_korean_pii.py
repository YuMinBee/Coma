import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.regex_scanner import scan_by_regex
from tests.test_validators import with_business_checksum, with_resident_checksum

BUSINESS_NUMBER = with_business_checksum("123456789")
BUSINESS_NUMBER_DASHED = f"{BUSINESS_NUMBER[:3]}-{BUSINESS_NUMBER[3:5]}-{BUSINESS_NUMBER[5:]}"
BROKEN_BUSINESS_NUMBER = BUSINESS_NUMBER_DASHED[:-1] + str((int(BUSINESS_NUMBER_DASHED[-1]) + 1) % 10)
RESIDENT_ID = with_resident_checksum("850315" + "234567")
RESIDENT_ID_DASHED = f"{RESIDENT_ID[:6]}-{RESIDENT_ID[6:]}"


def detected(text: str) -> list[tuple[str, str]]:
    return [(f.type, f.exact_quote) for f in scan_by_regex(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("고객 연락처 010-1234-5678입니다", [("Phone", "010-1234-5678")]),
        ("휴대폰 01012345678로 연락", [("Phone", "01012345678")]),
        ("Callback number is +82 10 1234 5678.", [("Phone", "+82 10 1234 5678")]),
        ("대표 02-123-4567 / 지사 031.987.6543", [("Phone", "02-123-4567"), ("Phone", "031.987.6543")]),
        (f"주민등록번호 {RESIDENT_ID_DASHED}", [("Resident Registration Number", RESIDENT_ID_DASHED)]),
        (f"주민번호: {RESIDENT_ID}", [("Resident Registration Number", RESIDENT_ID)]),
        ("외국인등록번호: 950505-5123456", [("Foreigner Registration Number", "950505-5123456")]),
        ("법인등록번호 110111-1234567", [("Corporate Registration Number", "110111-1234567")]),
        (f"사업자등록번호 {BUSINESS_NUMBER_DASHED}", [("Business Registration Number", BUSINESS_NUMBER_DASHED)]),
        (f"사업자번호 {BUSINESS_NUMBER}", [("Business Registration Number", BUSINESS_NUMBER)]),
        ("환불 계좌: 국민 123456-78-901234 (예금주 홍길동)", [("Bank Account", "123456-78-901234")]),
        ("카카오뱅크 3333012345678로 입금", [("Bank Account", "3333012345678")]),
        ("여권번호 M123A4567", [("Passport Number", "M123A4567")]),
        ("Passport No. M12345678", [("Passport Number", "M12345678")]),
        ("운전면허번호 11-23-456789-01", [("Driver License", "11-23-456789-01")]),
        ("면허 서울 12-345678-90", [("Driver License", "서울 12-345678-90")]),
        ("카드 4111 1111 1111 1111", [("Credit Card", "4111 1111 1111 1111")]),
        ("Card number: 5555-4444-3333-2222", [("Credit Card", "5555-4444-3333-2222")]),
        ("메일은 minji.kim@naver.com으로 보내주세요", [("Email", "minji.kim@naver.com")]),
        ("비밀번호는 qwer1234입니다", [("Password", "qwer1234")]),
    ],
)
def test_korean_identifiers_are_detected(text, expected):
    assert detected(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "로그: 2026-06-26 10:00:00 INFO started",
        "배포 버전 2.10.3, 빌드 20240612",
        "주문번호 2024-0612-0001 처리 완료",
        "order 1234567890123456 shipped",
        "192.168.999.999 is not a valid private address.",
        "Use user@example.com as a placeholder in docs.",
        "git remote add origin git@github.com:YuMinBee/Coma.git",
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        "This example API_KEY=example-token is documentation only.",
        "DB_PASSWORD=$DB_PASS",
        "password = ${DB_PASSWORD}",
        "비밀번호는 바꿨어요",
        # 사업자번호 모양이지만 검증 숫자가 틀리고 문맥도 없음
        f"참조번호 {BROKEN_BUSINESS_NUMBER}",
        # 구분자 없는 13자리는 문맥 없이 주민번호로 보지 않는다
        f"tracking id {RESIDENT_ID}",
        # 여권 모양이어도 문맥이 없으면 부품 번호일 수 있다
        "부품 코드 M12345678 재고 3개",
        # 계좌 모양이어도 은행 문맥이 없으면 주문번호다
        "송장 123456-78-901234 출고",
    ],
)
def test_hard_negatives_are_not_detected(text):
    assert detected(text) == []


def test_labeled_identifiers_are_masked_even_when_validation_fails():
    # 문서가 직접 "사업자등록번호"라고 부른 값은 오타가 난 실제 번호일 수 있다.
    findings = scan_by_regex(f"사업자등록번호 {BROKEN_BUSINESS_NUMBER}")
    assert [(f.type, f.exact_quote) for f in findings] == [
        ("Business Registration Number", BROKEN_BUSINESS_NUMBER)
    ]
    assert findings[0].confidence < 0.9

    findings = scan_by_regex("주민등록번호 991332-1234567")  # 13월: 오타
    assert [(f.type, f.exact_quote) for f in findings] == [
        ("Resident Registration Number", "991332-1234567")
    ]


def test_corporate_number_allows_zero_type_digit():
    # 법인등록번호 7번째 자리는 0일 수 있어 주민번호 패턴으로는 잡히지 않는다.
    assert detected("법인등록번호: 134511-0004321") == [("Corporate Registration Number", "134511-0004321")]


def test_account_context_must_be_near_the_number():
    text = "주문번호 2024-0612-0001, 환불 계좌: 신한 110-123-456789"
    assert detected(text) == [("Bank Account", "110-123-456789")]


def test_masked_output_is_not_rescanned():
    assert detected("password=[MASKED_PASSWORD] email [EMAIL_1]") == []
