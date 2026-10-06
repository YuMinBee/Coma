"""정규식 후보를 실제 식별자로 확정하기 위한 검증 함수 모음.

정규식은 모양만 본다. 여기서는 체크섬·날짜·주소 범위처럼 모양으로는 알 수 없는
조건을 확인해서, 타임스탬프나 주문번호 같은 숫자열을 오탐하지 않게 한다.
"""

from __future__ import annotations

import calendar
import ipaddress

RESIDENT_ID_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
BUSINESS_NUMBER_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 5)

# 주민/외국인등록번호 7번째 자리 → 출생 세기. 1800년대(9, 0)는 실사용이 없어 제외한다.
CENTURY_BY_GENDER_DIGIT = {
    "1": 1900,
    "2": 1900,
    "5": 1900,
    "6": 1900,
    "3": 2000,
    "4": 2000,
    "7": 2000,
    "8": 2000,
}
FOREIGNER_GENDER_DIGITS = frozenset("5678")

# RFC 1918 사설 대역 + RFC 6598 공유 대역(CGNAT, Tailscale 등 사내 VPN이 사용)
INTERNAL_IPV4_NETWORKS = tuple(
    ipaddress.IPv4Network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")
)


def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def luhn_valid(number: str) -> bool:
    digits = digits_only(number)
    if len(digits) < 12:
        return False
    total = 0
    for index, ch in enumerate(reversed(digits)):
        digit = int(ch)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def resident_id_birth_valid(number: str) -> bool:
    """앞 7자리(생년월일 + 성별 자리)가 실제로 존재할 수 있는 값인지 확인한다."""
    digits = digits_only(number)
    if len(digits) != 13:
        return False
    century = CENTURY_BY_GENDER_DIGIT.get(digits[6])
    if century is None:
        return False
    year = century + int(digits[:2])
    month = int(digits[2:4])
    day = int(digits[4:6])
    if not 1 <= month <= 12:
        return False
    return 1 <= day <= calendar.monthrange(year, month)[1]


def resident_id_checksum_valid(number: str) -> bool:
    """2020년 10월 이전 발급 번호의 검증 숫자.

    이후 발급분은 뒷자리가 무작위라 체크섬이 맞지 않는다. 그래서 탐지 여부가 아니라
    신뢰도를 올리는 보조 신호로만 쓴다.
    """
    digits = digits_only(number)
    if len(digits) != 13:
        return False
    total = sum(int(d) * w for d, w in zip(digits[:12], RESIDENT_ID_WEIGHTS))
    modulus = 13 if digits[6] in FOREIGNER_GENDER_DIGITS else 11
    return (modulus - total % 11) % 10 == int(digits[12])


def is_foreigner_id(number: str) -> bool:
    digits = digits_only(number)
    return len(digits) == 13 and digits[6] in FOREIGNER_GENDER_DIGITS


def business_number_valid(number: str) -> bool:
    """국세청 사업자등록번호 검증 숫자 규칙."""
    digits = digits_only(number)
    if len(digits) != 10:
        return False
    values = [int(d) for d in digits]
    total = sum(v * w for v, w in zip(values[:9], BUSINESS_NUMBER_WEIGHTS))
    total += (values[8] * 5) // 10
    return (10 - total % 10) % 10 == values[9]


def is_internal_ipv4(value: str) -> bool:
    try:
        address = ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return any(address in network for network in INTERNAL_IPV4_NETWORKS)
