import re
import string
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, NamedTuple

from models.schemas import Finding
from services import validators
from services.allowlist import is_placeholder_secret, is_reserved_email
from services.masking import TYPE_MASK_PRIORITY


class Verdict(NamedTuple):
    """검증을 통과한 후보. type/severity로 같은 패턴 안에서 세부 유형을 나눌 수 있다."""

    type: str
    confidence: float
    severity: str | None = None


Validator = Callable[[re.Match[str], str], Verdict | None]


@dataclass(frozen=True)
class Detector:
    name: str
    pattern: re.Pattern[str]
    category: str
    severity: str
    hint: Callable[[str, str], bool]
    validate: Validator | None = None
    # 민감 값이 들어 있는 그룹. 키 이름(password=)은 남기고 값만 마스킹한다.
    value_group: str | int = 0
    confidence: float = 0.99


ACTION_BY_CATEGORY = {
    "SECRET": "실제 값을 제거하거나 [MASKED_SECRET] 형태로 치환하세요.",
    "INFRA_INFO": "내부 주소, DB URL, 서비스 식별자는 일반화해서 공유하세요.",
    "CUSTOMER_INFO": "개인정보나 고객 식별자는 마스킹한 뒤 공유하세요.",
}

INTERNAL_DOMAIN_SUFFIXES = (".internal", ".local", ".corp", ".company")
DOMAIN_CHARS = set(string.ascii_letters + string.digits + "-.")
INTERNAL_DOMAIN_FULL_RE = re.compile(
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+(?:internal|local|corp|company)",
    re.IGNORECASE,
)

# 숫자만으로는 구분이 안 되는 식별자는 문맥 키워드로 확정한다. 문맥은 값 바로 앞(같은 줄 30자),
# 값 바로 뒤(구분자 전까지 6자: "국민 817201-01-224513 계좌"), 표의 열 이름(CSV 헤더, SQL INSERT 열 목록)이다.
CONTEXT_WINDOW = 30
CONTEXT_AFTER_WINDOW = 6
CONTEXT_STOP_RE = re.compile(r"[,;\n()\[\]{}|/'\"]")
RESIDENT_ID_CONTEXT = re.compile(r"주민|외국인|등록\s*번호|resident|(?<![a-z])rrn(?![a-z])|jumin|registration", re.I)
CORPORATE_ID_CONTEXT = re.compile(r"법인")
BUSINESS_NUMBER_CONTEXT = re.compile(r"사업자|business|(?<![a-z])brn(?![a-z])|biz_?(?:no|num|reg)", re.I)
ACCOUNT_CONTEXT = re.compile(
    r"계좌|입금|송금|이체|예금주|은행|뱅크|금고|우체국|농협|수협|신협|account|acct|\bbank\b",
    re.I,
)
# "국민 817201-01-224513"처럼 은행 약칭이 번호 바로 앞에 붙은 경우. "우리 팀"처럼 흔한 단어라 바로 앞일 때만 본다.
BANK_NAME_BEFORE_RE = re.compile(
    r"(?:국민|신한|우리|하나|농협|기업|카카오뱅크|토스뱅크|케이뱅크|새마을금고|우체국|수협|신협|SC제일|씨티|산업|부산|대구|경남|광주|전북|제주)"
    r"(?:은행)?\s*[:：]?\s*$"
)
PASSPORT_CONTEXT = re.compile(r"여권|passport", re.I)
CARD_CONTEXT = re.compile(r"카드|신용|결제\s*수단|card|credit|visa|master|amex", re.I)
SQL_INSERT_RE = re.compile(r"insert\s+into\s+[\w.\"`\[\]]+\s*\(([^)]*)\)\s*values\s*", re.I)

SECRET_REFERENCE_PREFIXES = (
    "os.getenv(",
    "os.environ",
    "getenv(",
    "process.env",
    "settings.",
    "config.",
    "env.",
    "environ.",
    "%(",
)
ENV_REFERENCE_RE = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?")
TYPE_HINT_VALUES = {"str", "string", "int", "float", "bool", "bytes", "dict", "list", "none", "null"}
BOOLEAN_VALUES = {"true", "false", "yes", "no", "on", "off"}
TRAILING_PUNCTUATION = ",;).}"
# Visa 4, Mastercard 2·5, Amex/JCB/Diners 3, Discover/UnionPay 6, 국내 전용 카드 9
CARD_ISSUER_FIRST_DIGITS = frozenset("234569")
SSH_REMOTE_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    offsets.extend(i + 1 for i, ch in enumerate(text) if ch == "\n")
    return offsets


def _line_number(offsets: list[int], pos: int) -> int:
    return bisect_right(offsets, pos)


def _short(value: str, limit: int = 160) -> str:
    return value[:limit] + ("..." if len(value) > limit else "")


def _line_text_for_pos(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end]


def _context_before(text: str, pos: int, width: int = CONTEXT_WINDOW) -> str:
    line_start = text.rfind("\n", 0, pos) + 1
    return text[max(line_start, pos - width) : pos]


def _context_after(text: str, end: int, width: int = CONTEXT_AFTER_WINDOW) -> str:
    window = text[end : end + width]
    stop = CONTEXT_STOP_RE.search(window)
    return window[: stop.start()] if stop else window


SQL_VALUES_MAX_SPAN = 4000


class _TableLayout:
    """표 형식 텍스트에서 값의 열 이름을 찾는다. 후보마다 다시 계산하지 않도록 텍스트당 한 번 만든다.

    - CSV/TSV: 같은 구분자를 쓰는 연속된 줄의 첫 줄을 헤더로 본다.
    - SQL: INSERT INTO t (a, b) VALUES ('x', 'y')의 열 목록.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.delimiters = tuple(delimiter for delimiter in (",", "\t") if delimiter in text)
        self.line_starts = _line_offsets(text) if self.delimiters else [0]
        self.lines = text.split("\n") if self.delimiters else [text]
        self.header_line: dict[str, list[int]] = {}
        for delimiter in self.delimiters:
            headers: list[int] = []
            block_header = -1
            for index, line in enumerate(self.lines):
                if delimiter not in line:
                    block_header = -1
                    headers.append(-1)
                elif block_header == -1:
                    block_header = index
                    headers.append(-1)
                else:
                    headers.append(block_header)
            self.header_line[delimiter] = headers
        self.sql_statements = [
            (match.end(), [column.strip().strip('`"[] ') for column in match.group(1).split(",")])
            for match in SQL_INSERT_RE.finditer(text)
        ]
        self.sql_value_starts = [start for start, _ in self.sql_statements]

    def column_name(self, pos: int) -> str:
        return self._sql_column(pos) or self._csv_column(pos)

    def _csv_column(self, pos: int) -> str:
        if not self.delimiters:
            return ""
        line_index = bisect_right(self.line_starts, pos) - 1
        line = self.lines[line_index]
        offset = pos - self.line_starts[line_index]
        for delimiter in self.delimiters:
            header_index = self.header_line[delimiter][line_index]
            if header_index < 0:
                continue
            column = line.count(delimiter, 0, offset)
            cells = self.lines[header_index].split(delimiter)
            return cells[column] if column < len(cells) else ""
        return ""

    def _sql_column(self, pos: int) -> str:
        statement_index = bisect_right(self.sql_value_starts, pos) - 1
        if statement_index < 0:
            return ""
        values_start, columns = self.sql_statements[statement_index]
        if pos - values_start > SQL_VALUES_MAX_SPAN:
            return ""
        depth = 0
        index = 0
        quote: str | None = None
        for char in self.text[values_start:pos]:
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in "'\"":
                quote = char
            elif char == "(":
                depth += 1
                index = 0
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 1:
                index += 1
        if depth != 1 or index >= len(columns):
            return ""
        return columns[index]


@lru_cache(maxsize=8)
def _table_layout(text: str) -> _TableLayout:
    return _TableLayout(text)


def _has_context(text: str, start: int, keywords: re.Pattern[str], end: int | None = None) -> bool:
    if keywords.search(_context_before(text, start)):
        return True
    if end is not None and keywords.search(_context_after(text, end)):
        return True
    # 텍스트 전체를 보는 판단(구분자 유무 등)은 캐시된 레이아웃 안에서 한 번만 한다.
    header = _table_layout(text).column_name(start)
    return bool(header and keywords.search(header))


# ---------------------------------------------------------------------------
# 검증 함수: None을 돌려주면 후보를 버린다.
# ---------------------------------------------------------------------------


def _reject_placeholder(name: str) -> Validator:
    def validate(match: re.Match[str], _text: str) -> Verdict | None:
        if is_placeholder_secret(match.group()):
            return None
        return Verdict(name, 0.99)

    return validate


def _assigned_secret(name: str) -> Validator:
    def validate(match: re.Match[str], text: str) -> Verdict | None:
        value = match.group("value").rstrip(TRAILING_PUNCTUATION)
        lower = value.lower()
        if lower.startswith(SECRET_REFERENCE_PREFIXES) or ENV_REFERENCE_RE.fullmatch(value):
            return None
        if lower.strip("[]|,") in TYPE_HINT_VALUES or lower in BOOLEAN_VALUES:
            return None
        line = _line_text_for_pos(text, match.start())
        if "def " in line and ":" in line and "=" not in line:
            return None
        if is_placeholder_secret(value):
            return None
        return Verdict(name, 0.95)

    return validate


SECRET_CALL_KEYWORDS = ("password", "passwd", "pwd", "secret", "apikey", "api_key", "accesskey", "access_key", "token")
# 값을 넣는 호출(setPassword)이 아니라 꺼내거나 지우는 호출(getPassword("user"))은 인자가 비밀값이 아니다.
SECRET_CALL_SKIP_PREFIXES = ("get", "is", "has", "remove", "delete", "clear", "find", "load", "read", "contains")


def _validate_secret_call(match: re.Match[str], text: str) -> Verdict | None:
    method = match.group("key").split(".")[-1].lower()
    if method.startswith(SECRET_CALL_SKIP_PREFIXES):
        return None
    compact = method.replace("_", "")
    if any(key in compact for key in ("password", "passwd", "pwd")):
        name = "Password"
    elif any(key in compact for key in ("apikey", "accesskey", "clientsecret", "apisecret", "appsecret", "token")):
        name = "API Key"
    elif "secret" in compact:
        name = "Password"
    else:
        return None
    return _assigned_secret(name)(match, text)


def _validate_bearer(match: re.Match[str], _text: str) -> Verdict | None:
    if is_placeholder_secret(match.group("value")):
        return None
    return Verdict("Bearer Token", 0.97)


def _validate_internal_ip(match: re.Match[str], _text: str) -> Verdict | None:
    if not validators.is_internal_ipv4(match.group()):
        return None
    return Verdict("Internal IP", 0.97)


def _validate_email(match: re.Match[str], _text: str) -> Verdict | None:
    address = match.group()
    if is_reserved_email(address):
        return None
    local, _, domain = address.partition("@")
    if local.lower() == "git" and domain.lower() in SSH_REMOTE_HOSTS:
        return None
    return Verdict("Email", 0.97)


def _validate_card(match: re.Match[str], text: str) -> Verdict | None:
    value = match.group()
    # 구분자 없는 긴 숫자열(주문번호 등)은 Luhn을 10% 확률로 우연히 통과한다. 발급사 대역도 본다.
    plausible_issuer = not value.isdigit() or value[0] in CARD_ISSUER_FIRST_DIGITS
    if plausible_issuer and validators.luhn_valid(value):
        return Verdict("Credit Card", 0.97)
    if _has_context(text, match.start(), CARD_CONTEXT, match.end()):
        return Verdict("Credit Card", 0.7)
    return None


# 검증 숫자·생년월일은 문맥이 없을 때 숫자열을 걸러내는 용도다. "사업자등록번호 …"처럼
# 문서가 직접 이름을 붙인 값은 오타가 난 실제 번호일 수 있으니 검증에 실패해도 가린다.


def _validate_corporate_id(match: re.Match[str], text: str) -> Verdict | None:
    # 법인등록번호 앞 6자리는 등기소·법인 종류 코드라 날짜 검증을 할 수 없다. 문맥으로만 확정한다.
    if not _has_context(text, match.start(), CORPORATE_ID_CONTEXT, match.end()):
        return None
    return Verdict("Corporate Registration Number", 0.85, "MEDIUM")


def _validate_resident_id(match: re.Match[str], text: str) -> Verdict | None:
    value = match.group()
    if _has_context(text, match.start(), CORPORATE_ID_CONTEXT, match.end()):
        return None
    labeled = _has_context(text, match.start(), RESIDENT_ID_CONTEXT, match.end())
    birth_valid = validators.resident_id_birth_valid(value)
    if not birth_valid and not labeled:
        return None
    if value.isdigit() and not labeled:
        return None
    if not birth_valid:
        confidence = 0.75
    elif validators.resident_id_checksum_valid(value):
        confidence = 0.99
    else:
        confidence = 0.92
    if validators.is_foreigner_id(value):
        return Verdict("Foreigner Registration Number", confidence)
    return Verdict("Resident Registration Number", confidence)


def _validate_business_number(match: re.Match[str], text: str) -> Verdict | None:
    value = match.group()
    labeled = _has_context(text, match.start(), BUSINESS_NUMBER_CONTEXT, match.end())
    if validators.business_number_valid(value):
        if value.isdigit() and not labeled:
            return None
        return Verdict("Business Registration Number", 0.95, "MEDIUM")
    if labeled:
        return Verdict("Business Registration Number", 0.75, "MEDIUM")
    return None


DATE_LIKE_RE = re.compile(r"(?:19|20)\d{2}-?(?:0[1-9]|1[0-2])-?(?:0[1-9]|[12]\d|3[01])")


def _validate_bank_account(match: re.Match[str], text: str) -> Verdict | None:
    # 후보 대부분은 문맥이 없어 탈락한다. 가장 싼 문맥 검사를 먼저 한다.
    bank_named = bool(BANK_NAME_BEFORE_RE.search(_context_before(text, match.start(), 12)))
    if not bank_named and not _has_context(text, match.start(), ACCOUNT_CONTEXT, match.end()):
        return None
    value = match.group()
    digits = validators.digits_only(value)
    if not 10 <= len(digits) <= 14:
        return None
    if PHONE_RE.fullmatch(value) or DATE_LIKE_RE.fullmatch(value):
        return None
    if validators.business_number_valid(value) and len(value.split("-")) == 3:
        return None
    if RESIDENT_ID_RE.fullmatch(value) and validators.resident_id_birth_valid(value):
        return None
    return Verdict("Bank Account", 0.85)


def _validate_passport(match: re.Match[str], text: str) -> Verdict | None:
    if not _has_context(text, match.start(), PASSPORT_CONTEXT, match.end()):
        return None
    return Verdict("Passport Number", 0.9)


# ---------------------------------------------------------------------------
# 패턴
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(
    r"(?<![\d\-+])"
    r"(?:"
    r"\+82[-. ]?(?:\(0\)[-. ]?)?(?:1[016789]|2|[3-6][1-5]|70)[-. ]?\d{3,4}[-. ]?\d{4}"
    r"|01[016789][-. ]?\d{3,4}[-. ]?\d{4}"
    r"|0(?:2|3[1-3]|4[1-4]|5[1-5]|6[1-4]|70|50[2-8]|80)[-. ]\d{3,4}[-. ]\d{4}"
    r")"
    r"(?!\d|-\d)"
)
RESIDENT_ID_RE = re.compile(r"(?<![\d-])\d{6}[- ]?[1-8]\d{6}(?![\d-])")

_ASSIGNMENT_VALUE = r"[\"']?\s*[:=]\s*[\"'`]?(?P<value>[^\s\"'`\n]{3,})"

DETECTORS: tuple[Detector, ...] = (
    Detector(
        name="AWS Access Key",
        pattern=re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}(?![A-Z0-9])"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: any(p in text for p in ("AKIA", "ASIA", "ABIA", "ACCA")),
        validate=_reject_placeholder("AWS Access Key"),
    ),
    Detector(
        # 헤더만 가리면 본문(base64)이 그대로 남는다. END까지 가린다. END가 없으면(잘린 붙여넣기)
        # 다음 줄이 base64일 때만 끝까지 가리고, 코드에서 헤더 문자열만 언급한 경우는 헤더만 가린다.
        name="Private Key",
        pattern=re.compile(
            r"-----BEGIN (?P<label>(?:[A-Z0-9]+ )*)PRIVATE KEY(?: BLOCK)?-----"
            r"(?:[\s\S]*?-----END (?P=label)PRIVATE KEY(?: BLOCK)?-----"
            r"|(?=[ \t]*\r?\n[ \t]*[A-Za-z0-9+/]{16,}={0,2}[ \t]*(?:\r?\n|\Z))[\s\S]*\Z)?"
        ),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "-----BEGIN" in text,
    ),
    Detector(
        name="JWT Token",
        pattern=re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "eyJ" in text and "." in text,
    ),
    Detector(
        name="GitHub Token",
        pattern=re.compile(
            r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{40,255})(?![A-Za-z0-9_])"
        ),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "gh" in text and "_" in text,
        validate=_reject_placeholder("GitHub Token"),
    ),
    Detector(
        name="Anthropic API Key",
        pattern=re.compile(r"(?<![A-Za-z0-9_-])sk-ant-[A-Za-z0-9_-]{32,}"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "sk-ant-" in text,
        validate=_reject_placeholder("Anthropic API Key"),
    ),
    Detector(
        name="OpenAI API Key",
        pattern=re.compile(
            r"(?<![A-Za-z0-9_-])sk-(?:(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}|[A-Za-z0-9]{48}(?![A-Za-z0-9_-]))"
        ),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "sk-" in text,
        validate=_reject_placeholder("OpenAI API Key"),
    ),
    Detector(
        name="Slack Token",
        pattern=re.compile(r"(?<![A-Za-z0-9-])xox[abposr]-[A-Za-z0-9-]{10,}"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "xox" in text,
        validate=_reject_placeholder("Slack Token"),
    ),
    Detector(
        name="Google API Key",
        pattern=re.compile(r"(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_-])"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "AIza" in text,
        validate=_reject_placeholder("Google API Key"),
    ),
    Detector(
        name="Stripe Secret Key",
        pattern=re.compile(r"(?<![A-Za-z0-9_])(?:sk|rk)_live_[0-9A-Za-z]{24,}"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "_live_" in text,
        validate=_reject_placeholder("Stripe Secret Key"),
    ),
    Detector(
        name="Hugging Face Token",
        pattern=re.compile(r"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{34,}(?![A-Za-z0-9_])"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, _lower: "hf_" in text,
        validate=_reject_placeholder("Hugging Face Token"),
    ),
    Detector(
        # 키 이름이 pass/pw로 끝나는 경우(smtp.pass, db_pw)도 본다. bypass·passport는 구분자가 없어 제외된다.
        name="Password",
        pattern=re.compile(
            r"(?i)(?:\b[\w.-]*(?:password|passwd|pwd|secret)[\w.-]*|\b(?:[\w.-]*[_.-])?(?:pass|pw))"
            + _ASSIGNMENT_VALUE
        ),
        category="SECRET",
        severity="HIGH",
        hint=lambda _text, lower: any(key in lower for key in ("pass", "pwd", "pw", "secret")),
        validate=_assigned_secret("Password"),
        value_group="value",
    ),
    Detector(
        # "비밀번호는 qwer1234입니다"처럼 조사로 이어지는 문장. 값은 ASCII까지만 잘라 조사를 뺀다.
        name="Password",
        pattern=re.compile(r"(?:비밀번호|패스워드|비번)\s*(?:은|는|:|=|->)\s*(?P<value>[!-~]{4,})"),
        category="SECRET",
        severity="HIGH",
        hint=lambda _text, lower: any(key in lower for key in ("비밀번호", "패스워드", "비번")),
        validate=_assigned_secret("Password"),
        value_group="value",
    ),
    Detector(
        name="API Key",
        # OAuth client secret·앱 시크릿은 비밀번호가 아니라 API 자격증명으로 분류한다(기본 정책: 차단).
        pattern=re.compile(
            r"(?i)\b[\w.-]*(?:api[_-]?key|apikey|access[_-]?key|secret[_-]?key|access[_-]?token"
            r"|auth[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?secret|app[_-]?secret)[\w.-]*"
            + _ASSIGNMENT_VALUE
        ),
        category="SECRET",
        severity="HIGH",
        hint=lambda _text, lower: "key" in lower or "token" in lower or "secret" in lower,
        validate=_assigned_secret("API Key"),
        value_group="value",
    ),
    Detector(
        name="Bearer Token",
        pattern=re.compile(r"(?i)\bbearer\s+(?P<value>[A-Za-z0-9._~+/-]{20,}=*)"),
        category="SECRET",
        severity="HIGH",
        hint=lambda _text, lower: "bearer" in lower,
        validate=_validate_bearer,
        value_group="value",
    ),
    Detector(
        # 설정 파일의 키 형태: "bearer: <token>", "BEARER_TOKEN=<token>"
        name="Bearer Token",
        pattern=re.compile(
            r"(?i)\b[\w.-]*bearer[\w.-]*[\"']?\s*[:=]\s*[\"'`]?(?P<value>[A-Za-z0-9._~+/-]{20,}=*)"
        ),
        category="SECRET",
        severity="HIGH",
        hint=lambda _text, lower: "bearer" in lower,
        validate=_validate_bearer,
        value_group="value",
    ),
    Detector(
        name="DB URL",
        pattern=re.compile(
            r"(?:jdbc:oracle:thin:@"
            r"|(?:jdbc:[a-z0-9]+|mongodb(?:\+srv)?|rediss?|mysql|mariadb|postgres(?:ql)?|amqps?|mssql|clickhouse)://)"
            r"[^\s'\"\n]+"
        ),
        category="INFRA_INFO",
        severity="HIGH",
        hint=lambda text, _lower: "://" in text or "jdbc:" in text,
    ),
    Detector(
        # cfg.setPassword("..."), builder.apiKey("...") 같은 코드 호출의 문자열 인자
        name="Password",
        pattern=re.compile(r"(?P<key>\b[A-Za-z_][\w.]*)\s*\(\s*[\"'](?P<value>[^\"'\n]{3,})[\"']\s*\)"),
        category="SECRET",
        severity="HIGH",
        hint=lambda text, lower: "(" in text and any(key in lower for key in SECRET_CALL_KEYWORDS),
        validate=_validate_secret_call,
        value_group="value",
    ),
    Detector(
        name="Internal IP",
        pattern=re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?!\d|\.\d)"),
        category="INFRA_INFO",
        severity="MEDIUM",
        hint=lambda text, _lower: "." in text and any(ch.isdigit() for ch in text),
        validate=_validate_internal_ip,
    ),
    Detector(
        name="Email",
        # 경계는 ASCII로만 본다. \w는 한글도 포함해서 "a@b.com으로" 같은 문장에서 놓친다.
        pattern=re.compile(
            r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"
            r"(?![A-Za-z0-9_-])"
        ),
        category="CUSTOMER_INFO",
        severity="MEDIUM",
        hint=lambda text, _lower: "@" in text,
        validate=_validate_email,
    ),
    Detector(
        name="Corporate Registration Number",
        pattern=re.compile(r"(?<![\d-])\d{6}-?\d{7}(?![\d-])"),
        category="CUSTOMER_INFO",
        severity="MEDIUM",
        hint=lambda _text, lower: "법인" in lower,
        validate=_validate_corporate_id,
    ),
    Detector(
        name="Resident Registration Number",
        pattern=RESIDENT_ID_RE,
        category="CUSTOMER_INFO",
        severity="HIGH",
        hint=lambda text, _lower: any(ch.isdigit() for ch in text),
        validate=_validate_resident_id,
    ),
    Detector(
        name="Driver License",
        pattern=re.compile(
            r"(?<![\d-])(?:(?:1[1-9]|2[0-8])-\d{2}"
            r"|(?:서울|부산|경기|강원|충북|충남|전북|전남|경북|경남|제주|대구|인천|광주|대전|울산)\s?\d{2})"
            r"-\d{6}-\d{2}(?![\d-])"
        ),
        category="CUSTOMER_INFO",
        severity="HIGH",
        hint=lambda text, _lower: "-" in text,
        confidence=0.9,
    ),
    Detector(
        name="Passport Number",
        pattern=re.compile(r"(?<![A-Za-z0-9])[MSRODG](?:\d{8}|\d{3}[A-Z]\d{4})(?![A-Za-z0-9])"),
        category="CUSTOMER_INFO",
        severity="HIGH",
        hint=lambda _text, lower: "여권" in lower or "passport" in lower,
        validate=_validate_passport,
    ),
    Detector(
        name="Credit Card",
        pattern=re.compile(
            r"(?<![\d-])(?:\d{4}(?P<s1>[ -]?)\d{4}(?P=s1)\d{4}(?P=s1)\d{4}(?:(?P=s1)\d{3})?"
            r"|\d{4}(?P<s2>[ -]?)\d{6}(?P=s2)\d{5}"
            r"|\d{13,19})(?![\d-])"
        ),
        category="CUSTOMER_INFO",
        severity="HIGH",
        hint=lambda text, _lower: any(ch.isdigit() for ch in text),
        validate=_validate_card,
    ),
    Detector(
        name="Business Registration Number",
        pattern=re.compile(r"(?<![\d-])\d{3}(?P<sep>-?)\d{2}(?P=sep)\d{5}(?![\d-])"),
        category="CUSTOMER_INFO",
        severity="MEDIUM",
        hint=lambda text, _lower: any(ch.isdigit() for ch in text),
        validate=_validate_business_number,
    ),
    Detector(
        name="Bank Account",
        pattern=re.compile(r"(?<![\d-])(?:\d{2,6}(?:-\d{2,7}){1,3}|\d{10,14})(?![\d-])"),
        category="CUSTOMER_INFO",
        severity="HIGH",
        hint=lambda text, lower: any(ch.isdigit() for ch in text) and bool(ACCOUNT_CONTEXT.search(lower)),
        validate=_validate_bank_account,
    ),
    Detector(
        name="Phone",
        pattern=PHONE_RE,
        category="CUSTOMER_INFO",
        severity="MEDIUM",
        hint=lambda text, _lower: "0" in text or "+82" in text,
        confidence=0.95,
    ),
)


def _iter_internal_domains(text: str) -> list[tuple[int, int, str]]:
    lower = text.lower()
    matches: list[tuple[int, int, str]] = []

    for suffix in INTERNAL_DOMAIN_SUFFIXES:
        search_from = 0
        while True:
            suffix_start = lower.find(suffix, search_from)
            if suffix_start == -1:
                break

            start = suffix_start - 1
            while start >= 0 and text[start] in DOMAIN_CHARS and suffix_start - start <= 255:
                start -= 1
            start += 1

            end = suffix_start + len(suffix)
            candidate = text[start:end]
            prev_ok = start == 0 or text[start - 1] not in DOMAIN_CHARS
            next_ok = end == len(text) or not (text[end].isalnum() or text[end] in "-_")
            if prev_ok and next_ok and INTERNAL_DOMAIN_FULL_RE.fullmatch(candidate):
                matches.append((start, end, candidate))

            search_from = end

    return matches


def scan_by_regex(text: str) -> list[Finding]:
    findings: list[Finding] = []
    # 같은 span을 여러 탐지기가 잡으면(예: Bearer 값 = JWT) 마스킹 우선순위가 높은 쪽만 남긴다.
    index_by_span: dict[tuple[int, int], int] = {}
    line_offsets = _line_offsets(text)
    lower = text.lower()

    for detector in DETECTORS:
        if not detector.hint(text, lower):
            continue
        for match in detector.pattern.finditer(text):
            if detector.validate is None:
                verdict = Verdict(detector.name, detector.confidence)
            else:
                verdict = detector.validate(match, text)
            if verdict is None:
                continue

            start, end = match.span(detector.value_group)
            quote = text[start:end]
            if detector.value_group:
                quote = quote.rstrip(TRAILING_PUNCTUATION)
            end = start + len(quote)
            span = (start, end)
            if not quote:
                continue
            existing = index_by_span.get(span)
            if existing is not None:
                current = findings[existing].type
                if TYPE_MASK_PRIORITY.get(verdict.type, 0) <= TYPE_MASK_PRIORITY.get(current, 0):
                    continue

            finding = Finding(
                type=verdict.type,
                category=detector.category,
                value=_short(quote),
                start=start,
                end=end,
                line=_line_number(line_offsets, start),
                severity=verdict.severity or detector.severity,
                exact_quote=quote,
                confidence=verdict.confidence,
                reason=f"{verdict.type} 패턴과 일치하는 민감 값이 발견되었습니다.",
                action=ACTION_BY_CATEGORY.get(
                    detector.category, "해당 값을 제거하거나 일반화해서 공유하세요."
                ),
                source="regex",
            )
            if existing is not None:
                findings[existing] = finding
            else:
                index_by_span[span] = len(findings)
                findings.append(finding)

    for start, end, quote in _iter_internal_domains(text):
        span = (start, end)
        if span in index_by_span:
            continue
        index_by_span[span] = len(findings)
        findings.append(
            Finding(
                type="Internal Domain",
                category="INFRA_INFO",
                value=_short(quote),
                start=start,
                end=end,
                line=_line_number(line_offsets, start),
                severity="MEDIUM",
                exact_quote=quote,
                confidence=0.99,
                reason="Internal Domain 패턴과 일치하는 민감 값이 발견되었습니다.",
                action=ACTION_BY_CATEGORY["INFRA_INFO"],
                source="regex",
            )
        )

    return findings
