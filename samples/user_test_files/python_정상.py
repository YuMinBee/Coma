# safe_example.py
from __future__ import annotations

import os
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = (BASE_DIR / "uploads").resolve()
REPORT_DIR = (BASE_DIR / "reports").resolve()

API_KEY = os.getenv("API_KEY")
DB_PASSWORD = os.getenv("DB_PASSWORD")


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    email: str


def open_database() -> sqlite3.Connection:
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_id(user_id: int) -> UserRecord | None:
    with open_database() as conn:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return UserRecord(
        id=int(row["id"]),
        username=str(row["username"]),
        email=str(row["email"]),
    )


def list_recent_users(limit: int = 20) -> list[UserRecord]:
    normalized_limit = max(1, min(limit, 100))
    with open_database() as conn:
        rows = conn.execute(
            "SELECT id, username, email FROM users ORDER BY id DESC LIMIT ?",
            (normalized_limit,),
        ).fetchall()

    return [
        UserRecord(
            id=int(row["id"]),
            username=str(row["username"]),
            email=str(row["email"]),
        )
        for row in rows
    ]


def safe_ping(host: str) -> str:
    allowed_hosts = {"localhost", "127.0.0.1"}

    if host not in allowed_hosts:
        raise ValueError("허용되지 않은 host입니다.")

    result = subprocess.run(
        ["ping", "-c", "1", host],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    return result.stdout


def resolve_inside(base_dir: Path, filename: str) -> Path:
    candidate = (base_dir / filename).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise ValueError("잘못된 파일 경로입니다.")
    return candidate


def read_uploaded_file(filename: str) -> str:
    file_path = resolve_inside(UPLOAD_DIR, filename)
    if not file_path.is_file():
        raise FileNotFoundError(filename)

    return file_path.read_text(encoding="utf-8")


def write_report(filename: str, lines: Iterable[str]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = resolve_inside(REPORT_DIR, filename)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def normalize_display_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    if len(cleaned) > 80:
        raise ValueError("이름이 너무 깁니다.")
    return cleaned


def render_user_summary(user: UserRecord | None) -> str:
    if user is None:
        return "사용자를 찾을 수 없습니다."

    return f"{user.id}: {normalize_display_name(user.username)}"


def build_daily_report() -> Path:
    users = list_recent_users(limit=10)
    lines = ["Daily user summary", "==================", ""]
    lines.extend(render_user_summary(user) for user in users)
    return write_report("daily_users.txt", lines)


if __name__ == "__main__":
    selected = get_user_by_id(1)
    print(render_user_summary(selected))
    print(build_daily_report())
