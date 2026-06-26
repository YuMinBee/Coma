import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_scan import DEFAULT_DATASET, load_cases


def test_eval_dataset_shape():
    cases = load_cases(DEFAULT_DATASET)
    categories = {}
    for case in cases:
        categories[case.category] = categories.get(case.category, 0) + 1
        assert case.case_id
        assert case.text
        assert case.expected
        assert "overall_action" in case.expected

    assert len(cases) == 50
    assert categories == {
        "benign_prompt": 10,
        "edge_case": 10,
        "internal_info": 10,
        "pii": 10,
        "secrets": 10,
    }


if __name__ == "__main__":
    test_eval_dataset_shape()
    print("eval dataset tests passed")
