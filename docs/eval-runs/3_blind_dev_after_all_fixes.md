# SafePromptGuard v5 Eval Report

> Generated: 2026-10-06 09:45 UTC
> Dataset: `backend/eval/blind_dev.jsonl` (83 cases)
> Gemma: OFF
> Gitleaks: OFF

## Summary

- Case pass rate: 79/83 (95.2%)
- Case pass rate excluding known failures: 79/83 (95.2%)
- Span detectors (micro): precision 1.000 / recall 1.000 / F1 1.000 (TP 98, FP 0, FN 0)
- Cases with a sensitive term left in the output: 0
- Latency avg/p50/p95/max: 0.1ms / 0ms / 0ms / 11ms

## Detector Precision / Recall

Value-level spans from regex/gitleaks detectors. A prediction counts as correct when its
detector matches and its span overlaps the expected value. Keyword rules are line-level
signals and are measured only through the case checks below.

| Detector | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| api_key | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| bank_account | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| business_registration_number | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| credit_card | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| db_url | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| driver_license | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| email | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| foreigner_registration_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| internal_domain | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| internal_ip | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| passport_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| password | 9 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| phone | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| private_key | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| resident_registration_number | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| token | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Check Accuracy

| Check | Accuracy |
|---|---:|
| detected | 34/38 (89.5%) |
| masked | 79/83 (95.2%) |
| blocked | 83/83 (100.0%) |
| safe_prompt_null | 83/83 (100.0%) |
| secret_leakage | 83/83 (100.0%) |
| overall_action | 79/83 (95.2%) |

## Category Pass Rate

| Category | Pass Rate |
|---|---:|
| blind_dev | 79/83 (95.2%) |

## Cases

| ID | Category | Pass | Action | Findings | Latency | Failed Checks | Detector errors |
|---|---|---:|---|---:|---:|---|---|
| blind_001 | blind_dev | yes | mask | 2 | 11ms | - | - |
| blind_002 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_003 | blind_dev | yes | mask | 4 | 0ms | - | - |
| blind_004 | blind_dev | yes | mask | 5 | 0ms | - | - |
| blind_005 | blind_dev | yes | block | 3 | 0ms | - | - |
| blind_006 | blind_dev | yes | block | 1 | 0ms | - | - |
| blind_010 | blind_dev | yes | mask | 5 | 0ms | - | - |
| blind_013 | blind_dev | yes | mask | 3 | 0ms | - | - |
| blind_015 | blind_dev | yes | block | 4 | 0ms | - | - |
| blind_019 | blind_dev | yes | block | 2 | 0ms | - | - |
| blind_021 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_024 | blind_dev | yes | mask | 2 | 1ms | - | - |
| blind_025 | blind_dev | yes | mask | 4 | 0ms | - | - |
| blind_026 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_027 | blind_dev | yes | block | 3 | 0ms | - | - |
| blind_028 | blind_dev | yes | mask | 6 | 0ms | - | - |
| blind_032 | blind_dev | yes | mask | 4 | 0ms | - | - |
| blind_035 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_040 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_045 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_046 | blind_dev | yes | mask | 3 | 0ms | - | - |
| blind_047 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_048 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_049 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_050 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_051 | blind_dev | yes | block | 3 | 0ms | - | - |
| blind_052 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_053 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_054 | blind_dev | yes | block | 2 | 0ms | - | - |
| blind_058 | blind_dev | yes | mask | 3 | 0ms | - | - |
| blind_059 | blind_dev | yes | block | 4 | 0ms | - | - |
| blind_060 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_061 | blind_dev | yes | mask | 6 | 0ms | - | - |
| blind_062 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_066 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_071 | blind_dev | yes | mask | 4 | 0ms | - | - |
| blind_072 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_073 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_078 | blind_dev | yes | mask | 3 | 0ms | - | - |
| blind_079 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_080 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_081 | blind_dev | yes | mask | 1 | 0ms | - | - |
| blind_084 | blind_dev | yes | mask | 3 | 0ms | - | - |
| blind_087 | blind_dev | yes | block | 2 | 0ms | - | - |
| blind_089 | blind_dev | yes | mask | 2 | 0ms | - | - |
| blind_099 | blind_dev | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| blind_100 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_101 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_102 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_105 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_108 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_109 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_110 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_112 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_113 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_114 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_115 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_117 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_120 | blind_dev | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| blind_121 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_123 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_124 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_125 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_126 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_130 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_132 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_133 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_134 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_135 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_138 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_140 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_143 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_145 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_146 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_147 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_149 | blind_dev | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| blind_151 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_152 | blind_dev | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| blind_153 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_154 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_157 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_159 | blind_dev | yes | allow | 0 | 0ms | - | - |
| blind_160 | blind_dev | yes | allow | 0 | 0ms | - | - |
