from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from models.schemas import Finding

DEFAULT_TIMEOUT_SECONDS = 20


def gitleaks_available(command: str = "gitleaks") -> bool:
    return shutil.which(command) is not None


def scan_with_gitleaks(
    text: str,
    *,
    filename: str | None = None,
    command: str = "gitleaks",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[Finding]:
    if not text.strip() or not gitleaks_available(command):
        return []

    safe_name = _safe_filename(filename)
    try:
        with tempfile.TemporaryDirectory(prefix="safeprompt-gitleaks-") as tmp:
            root = Path(tmp)
            source_file = root / safe_name
            source_file.write_text(text, encoding="utf-8")
            report_file = root / "gitleaks-report.json"

            report = _run_gitleaks(
                root,
                report_file,
                command=command,
                timeout_seconds=timeout_seconds,
            )
            return findings_from_gitleaks_report(report, text)
    except Exception:
        return []


def findings_from_gitleaks_report(
    report: list[dict[str, Any]],
    text: str,
) -> list[Finding]:
    findings: list[Finding] = []
    for item in report:
        if not isinstance(item, dict):
            continue

        rule_id = _text_value(item, "RuleID", "RuleId", "rule_id", "ruleID")
        description = _text_value(item, "Description", "description")
        match = _text_value(item, "Match", "match")
        secret = _text_value(item, "Secret", "secret")
        quote = _best_quote(secret, match)
        start, end = _find_span(text, item, quote)
        line = _line_number(text, start) if start is not None else _safe_int(item.get("StartLine"))

        finding_type = _finding_type(rule_id, description)
        findings.append(
            Finding(
                type=finding_type,
                category="SECRET",
                value=_short(quote or finding_type),
                start=start,
                end=end,
                line=line,
                severity="HIGH",
                detector=_detector_for_rule(rule_id, description),
                exact_quote=quote,
                confidence=0.98,
                reason=f"Gitleaks matched secret rule {_safe_rule_label(rule_id, description)}.",
                action="Remove the secret value or replace it with a safe placeholder before sharing.",
                source="gitleaks",
            )
        )
    return findings


def _run_gitleaks(
    source_dir: Path,
    report_file: Path,
    *,
    command: str,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    commands = [
        [
            command,
            "detect",
            "--no-git",
            "--source",
            str(source_dir),
            "--report-format",
            "json",
            "--report-path",
            str(report_file),
            "--no-banner",
        ],
        [
            command,
            "dir",
            str(source_dir),
            "--report-format",
            "json",
            "--report-path",
            str(report_file),
            "--no-banner",
        ],
    ]

    for args in commands:
        if report_file.exists():
            report_file.unlink()
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if report_file.exists():
            return _read_report(report_file)
        if proc.returncode in (0, 1):
            return []
    return []


def _read_report(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _text_value(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _best_quote(secret: str | None, match: str | None) -> str | None:
    if secret and not _is_redacted(secret):
        return secret
    if match and not _is_redacted(match):
        return match
    return secret or match


def _is_redacted(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and set(stripped) <= {"*", "x", "X"}


def _find_span(
    text: str,
    item: dict[str, Any],
    quote: str | None,
) -> tuple[int | None, int | None]:
    if quote:
        idx = text.find(quote)
        if idx >= 0:
            return idx, idx + len(quote)

    line = _safe_int(item.get("StartLine"))
    column = _safe_int(item.get("StartColumn"))
    end_line = _safe_int(item.get("EndLine"))
    end_column = _safe_int(item.get("EndColumn"))
    if not line or not column:
        return None, None

    start = _offset_for_line_column(text, line, column)
    end = None
    if end_line and end_column:
        end = _offset_for_line_column(text, end_line, end_column)
    if start is None:
        return None, None
    if end is None or end <= start:
        end = start + len(quote or "")
    return start, min(end, len(text))


def _offset_for_line_column(text: str, line: int, column: int) -> int | None:
    if line < 1 or column < 1:
        return None
    offset = 0
    for current_line, content in enumerate(text.splitlines(keepends=True), 1):
        if current_line == line:
            return min(offset + column - 1, offset + len(content.rstrip("\r\n")))
        offset += len(content)
    return None


def _line_number(text: str, offset: int | None) -> int | None:
    if offset is None:
        return None
    return text[:offset].count("\n") + 1


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _detector_for_rule(rule_id: str | None, description: str | None) -> str:
    label = f"{rule_id or ''} {description or ''}".lower()
    if "api" in label and "key" in label:
        return "api_key"
    if "access" in label and "key" in label:
        return "api_key"
    if "private" in label and "key" in label:
        return "private_key"
    if "token" in label or "jwt" in label:
        return "token"
    if "password" in label or "passwd" in label:
        return "password"
    return "secret"


def _finding_type(rule_id: str | None, description: str | None) -> str:
    detector = _detector_for_rule(rule_id, description)
    if detector == "api_key":
        return "API Key"
    if detector == "private_key":
        return "Private Key"
    if detector == "token":
        return "Bearer Token"
    if detector == "password":
        return "Password"
    return "Gitleaks Secret"


def _safe_rule_label(rule_id: str | None, description: str | None) -> str:
    return rule_id or description or "unknown"


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "scan.txt").name
    return name or "scan.txt"


def _short(value: str, limit: int = 160) -> str:
    return value[:limit] + ("..." if len(value) > limit else "")
