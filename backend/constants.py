"""업로드 허용 확장자 — shared/allowed_extensions.json 단일 정의."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent


def _resolve_policy_path() -> Path:
    """로컬(repo/backend+shared) · Docker(/app+shared) 모두 지원."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "shared" / "allowed_extensions.json"
        if bundled.is_file():
            return bundled

    for root in (_BACKEND_DIR.parent, _BACKEND_DIR):
        path = root / "shared" / "allowed_extensions.json"
        if path.is_file():
            return path
    raise FileNotFoundError(
        "shared/allowed_extensions.json 을 찾을 수 없습니다. "
        f"확인 경로: {_BACKEND_DIR.parent / 'shared'}, {_BACKEND_DIR / 'shared'}"
    )


def _load_policy_file() -> dict:
    policy_path = _resolve_policy_path()
    if not policy_path.is_file():
        raise FileNotFoundError(f"shared/allowed_extensions.json 을 찾을 수 없습니다: {policy_path}")
    return json.loads(_resolve_policy_path().read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_file_upload_policy() -> dict:
    data = _load_policy_file()
    extensions = list(data["extensions"])
    notebook = list(data.get("notebook_extensions", [".ipynb"]))
    allowed = frozenset(extensions)
    notebook_set = frozenset(notebook)
    return {
        "extensions": extensions,
        "allowed_extensions": allowed,
        "notebook_extensions": notebook_set,
        "accept_attribute": ",".join(extensions),
        "extensions_sorted_display": ", ".join(sorted(allowed)),
    }


ALLOWED_EXTENSIONS = get_file_upload_policy()["allowed_extensions"]
NOTEBOOK_EXTENSIONS = get_file_upload_policy()["notebook_extensions"]

# 심사 정량 목표 기준: 1MiB 이하 텍스트를 스캔 대상으로 제한한다.
MAX_TEXT_CHARS = 1_048_576
MAX_UPLOAD_BYTES = 1 * 1024 * 1024
