# 탐지기 설계

SafePrompt Guard는 세 단계로 값을 확정한다.

1. **패턴**: 정규식으로 후보를 찾는다. 모양만 본다.
2. **검증**: 체크섬·날짜·주소 범위·문맥 키워드로 후보를 확정하거나 버린다.
3. **예외**: 문서·테스트에서 널리 쓰는 예제 값(allowlist)은 탐지에서 제외하고, 조직별 예외는 정책(`config/policy.yaml`)으로 처리한다.

코드는 `backend/services/regex_scanner.py`(패턴·검증), `validators.py`(체크섬 등 순수 함수), `allowlist.py`(예제 값)에 있다.

## 한국 개인정보

| 유형 | detector | 확정 조건 | 마스킹 |
|---|---|---|---|
| 주민등록번호 | `resident_registration_number` | 생년월일·성별 자리(1–4)가 유효하면 확정. 체크섬이 맞으면 신뢰도 0.99, 안 맞으면 0.92(2020년 10월 이후 발급분은 뒷자리가 무작위). 구분자 없는 13자리는 "주민/등록번호" 문맥이 필요 | `[MASKED_RRN]` |
| 외국인등록번호 | `foreigner_registration_number` | 주민번호와 같고 성별 자리 5–8 | `[MASKED_FOREIGNER_ID]` |
| 법인등록번호 | `corporate_registration_number` | 6-7자리 + 앞쪽 30자 안에 "법인". 앞 6자리는 날짜가 아니라 등기소 코드라 날짜 검증을 하지 않는다 | `[MASKED_CORP_ID]` |
| 사업자등록번호 | `business_registration_number` | 국세청 검증 숫자가 맞으면 확정. 구분자가 없으면 "사업자" 문맥 필요 | `[MASKED_BRN]` |
| 계좌번호 | `bank_account` | 숫자 10–14자리 + 앞쪽 30자 안에 계좌·입금·은행 등 문맥. 전화번호·날짜·사업자번호·주민번호 모양은 제외 | `[MASKED_ACCOUNT]` |
| 여권번호 | `passport_number` | `M12345678` 또는 2021년 신형 `M123A4567` + "여권/passport" 문맥 | `[MASKED_PASSPORT]` |
| 운전면허번호 | `driver_license` | `11-23-456789-01`(지역 코드 11–28) 또는 `서울 12-345678-90` | `[MASKED_DRIVER_LICENSE]` |
| 전화번호 | `phone` | 휴대폰(010 등)·지역번호·070·+82. 앞뒤가 숫자면 제외해서 타임스탬프 안의 숫자를 잡지 않는다. 지역번호는 구분자가 있어야 한다 | `[MASKED_PHONE]` |
| 카드번호 | `credit_card` | Luhn 통과(구분자 없는 숫자열은 발급사 대역 2·3·4·5·6·9도 확인) 또는 "카드" 문맥 | `[MASKED_CARD]` |

**문맥은 세 곳에서 찾는다.** 값 바로 앞(같은 줄 30자), 값 바로 뒤(쉼표·괄호 등 구분자 전까지 6자: "국민 817201-01-224513 계좌"), 표의 열 이름(CSV/TSV 헤더 줄, `INSERT INTO t (name, brn) VALUES (...)`의 열 목록)이다. 계좌는 "국민 ", "우리은행: "처럼 은행 이름이 번호 바로 앞에 붙은 경우도 인정한다. 표 구조는 텍스트당 한 번만 분석해 캐시한다(1MB CSV 약 0.6초).

**문서가 직접 이름을 붙인 값은 검증에 실패해도 가린다.** "사업자등록번호 123-45-67891"처럼 앞에 유형 이름이 있으면 검증 숫자가 틀려도(오타 난 실제 번호일 수 있다) 신뢰도 0.75로 탐지한다. 검증은 문맥이 없을 때 주문번호 같은 숫자열을 걸러내는 용도다.

## 인증정보·인프라

| 유형 | detector | 비고 |
|---|---|---|
| AWS Access Key | `api_key` | `AKIA/ASIA…` 20자 |
| GitHub / OpenAI / Anthropic / Slack / Google / Stripe / Hugging Face 토큰 | `api_key` | 서비스별 접두어 형식. 문장 속에 그냥 붙여 넣은 토큰도 잡는다 |
| API Key 할당 | `api_key` | `api_key=`, `access_token:`, `CLIENT_SECRET =` 등 키 이름 뒤의 값. OAuth client secret은 API 자격증명으로 분류 |
| Password 할당 | `password` | `password=`, `"secret": …`, `smtp.pass:`, `DB_PW=`, "비밀번호는 abc123입니다". `true`/`false` 같은 값은 제외 |
| 코드 호출 인자 | `password` / `api_key` | `cfg.setPassword("…")`, `client.withApiKey("…")`. `getPassword("user")`처럼 값을 꺼내는 호출은 제외 |
| Bearer / JWT | `token` | `Authorization: Bearer …`와 설정 키 형태 `bearer: …` |
| Private Key | `private_key` | `BEGIN … PRIVATE KEY`부터 `END`까지 블록 전체. END가 없으면 다음 줄이 base64일 때만 끝까지 가리고(잘린 붙여넣기), 코드가 헤더 문자열만 언급하면 헤더만 가린다 |
| DB URL | `db_url` | postgresql, mysql, mariadb, `jdbc:*://`, `jdbc:oracle:thin:@`, mongodb, redis, amqp 등 |
| 내부 IP | `internal_ip` | RFC 1918 사설 대역 + RFC 6598 공유 대역(100.64.0.0/10, Tailscale 등 사내 VPN). 옥텟 범위를 검증한다 |
| 내부 도메인 | `internal_domain` | `.internal`, `.local`, `.corp`, `.company` |

할당형 탐지기(password, API key, bearer)는 **값만** 마스킹한다. `spring.datasource.password=[MASKED_PASSWORD]`처럼 키 이름이 남아서 외부 AI가 어떤 설정 문제인지 이해할 수 있다.

## 예제 값 allowlist

다음은 실제 유출이 아니므로 탐지하지 않는다.

- AWS 공식 문서 예제 키(`AKIAIOSFODNN7EXAMPLE` 등)와 `…EXAMPLE`로 끝나는 키
- RFC 2606/6761 예약 도메인 이메일(`example.com`, `*.test`, `*.invalid`, `*.localhost`)
- placeholder 값: `example`, `sample`, `dummy`, `placeholder`, `changeme`, `change-me`, `your_…`, `<…>`, `${…}`, `xxxx`, `****` 등을 포함한 값. 단어는 사람이 쓰는 형태(소문자·대문자·첫 글자 대문자)만 인정해서, 무작위 키에 `ExAmPLE`처럼 섞여 들어간 경우는 실제 키로 본다
- 환경변수 참조(`os.getenv(...)`, `os.environ[...]`, `$DB_PASS`, `${DB_PASS}`), 타입 힌트(`password: str`)
- 이미 마스킹된 placeholder(`[MASKED_EMAIL]`, `[MASKED_EMAIL_1]`, `[EMAIL_1]`). 마스킹 결과를 다시 검사해도 새 탐지가 생기지 않는다(평가셋 3종으로 테스트)

## 정책 우선순위

`config/policy.yaml`의 규칙이 여러 개 맞으면 **priority → 구체성 → 조치 강도** 순으로 하나를 고른다.

- 구체성: `condition`(contains / equals / matches)이 있으면 +2, `severity`가 있으면 +1
- 그래서 `condition`이 붙은 allow 규칙은 같은 detector의 일반 block 규칙보다 먼저 적용된다(조직 예외)
- 예외를 무시하고 무조건 막아야 하면 `priority`를 높인다

이전 버전은 항상 가장 강한 조치를 골라서 allow 예외가 절대 적용되지 않았다.

## 겹치는 탐지

같은 위치를 여러 탐지기가 잡으면 `masking.TYPE_MASK_PRIORITY`가 높은 쪽 하나만 남긴다. 예를 들어 `STRIPE_SECRET=sk_live_…`는 Password 할당과 Stripe 토큰에 모두 걸리지만 Stripe(`api_key`, 차단 대상)로 남는다. 서비스별 형식으로 확인된 키는 일반 Bearer보다 우선해서 `Authorization: Bearer sk-proj-…`는 OpenAI 키로 차단된다.

## 탐지기 추가 방법

1. `regex_scanner.DETECTORS`에 `Detector`를 추가한다. `hint`는 텍스트에 후보가 있을 수 없을 때 정규식을 건너뛰는 빠른 사전 검사다.
2. 모양만으로 부족하면 `validate`에서 검증하고, 실패하면 `None`을 돌려준다.
3. `policy_engine.TYPE_DETECTOR_MAP`, `masking.MASK_LABELS`, `masking.TYPE_MASK_PRIORITY`에 유형을 등록한다.
4. `tests/test_korean_pii.py`에 탐지 사례와 오탐 사례를 함께 추가하고, `backend/eval/dataset.jsonl`에 span 정답(`expected_findings`)이 있는 케이스를 추가한다.
