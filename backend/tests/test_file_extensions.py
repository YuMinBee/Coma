import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constants import ALLOWED_EXTENSIONS, get_file_upload_policy

ROOT = Path(__file__).resolve().parents[2]
SHARED_JSON = ROOT / "shared" / "allowed_extensions.json"


def test_shared_json_matches_backend():
    data = json.loads(SHARED_JSON.read_text(encoding="utf-8"))
    policy = get_file_upload_policy()
    assert set(data["extensions"]) == set(policy["extensions"])
    assert policy["accept_attribute"] == ",".join(data["extensions"])
    assert ".ipynb" in ALLOWED_EXTENSIONS
    assert ".python" in ALLOWED_EXTENSIONS
    assert ".c" in ALLOWED_EXTENSIONS
    assert ".cpp" in ALLOWED_EXTENSIONS
    assert ".sql" in ALLOWED_EXTENSIONS


if __name__ == "__main__":
    test_shared_json_matches_backend()
    print("file extension policy ok")
