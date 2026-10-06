import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import validators


def with_resident_checksum(first12: str) -> str:
    total = sum(int(d) * w for d, w in zip(first12, validators.RESIDENT_ID_WEIGHTS))
    modulus = 13 if first12[6] in validators.FOREIGNER_GENDER_DIGITS else 11
    return first12 + str((modulus - total % 11) % 10)


def with_business_checksum(first9: str) -> str:
    values = [int(d) for d in first9]
    total = sum(v * w for v, w in zip(values, validators.BUSINESS_NUMBER_WEIGHTS))
    total += (values[8] * 5) // 10
    return first9 + str((10 - total % 10) % 10)


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("4111 1111 1111 1111", True),
        ("4111-1111-1111-1112", False),
        ("378282246310005", True),
        ("1234", False),
    ],
)
def test_luhn(number, expected):
    assert validators.luhn_valid(number) is expected


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("900101-1234567", True),
        ("901301-1234567", False),  # 13월
        ("900230-2234567", False),  # 2월 30일
        ("000229-3234567", True),  # 2000년은 윤년
        ("010229-3234567", False),  # 2001년은 평년
        ("900101-9234567", False),  # 1800년대 성별 자리는 제외
        ("950505-5123456", True),  # 외국인
    ],
)
def test_resident_id_birth(number, expected):
    assert validators.resident_id_birth_valid(number) is expected


def test_resident_id_checksum_is_secondary_signal():
    valid = with_resident_checksum("850315" + "234567")
    broken = valid[:-1] + str((int(valid[-1]) + 1) % 10)
    assert validators.resident_id_checksum_valid(valid)
    assert not validators.resident_id_checksum_valid(broken)
    # 2020년 10월 이후 발급분처럼 체크섬이 안 맞아도 생년월일 검증은 통과한다.
    assert validators.resident_id_birth_valid(broken)


def test_foreigner_checksum_uses_its_own_modulus():
    valid = with_resident_checksum("950505" + "612345")
    assert validators.is_foreigner_id(valid)
    assert validators.resident_id_checksum_valid(valid)


def test_business_number():
    valid = with_business_checksum("123456789")
    broken = valid[:-1] + str((int(valid[-1]) + 1) % 10)
    assert validators.business_number_valid(f"{valid[:3]}-{valid[3:5]}-{valid[5:]}")
    assert not validators.business_number_valid(broken)


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("10.0.0.12", True),
        ("172.31.255.1", True),
        ("172.32.0.1", False),
        ("192.168.0.10", True),
        ("100.104.217.121", True),  # CGNAT / Tailscale
        ("192.168.999.999", False),
        ("8.8.8.8", False),
        ("010.0.0.1", False),
    ],
)
def test_internal_ipv4(address, expected):
    assert validators.is_internal_ipv4(address) is expected
