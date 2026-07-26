import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TUTORIAL_NOTEBOOKS = sorted(PROJECT_ROOT.joinpath("notebooks", "tutorial").rglob("*.ipynb"))


def test_tutorial_notebooks_are_valid_and_output_free():
    assert TUTORIAL_NOTEBOOKS

    for notebook_path in TUTORIAL_NOTEBOOKS:
        payload = json.loads(notebook_path.read_text(encoding="utf-8"))

        assert payload["nbformat"] == 4
        assert isinstance(payload["cells"], list)
        assert any(cell["cell_type"] == "markdown" for cell in payload["cells"])

        for cell in payload["cells"]:
            assert "source" in cell
            if cell["cell_type"] == "code":
                assert cell.get("execution_count") is None
                assert cell.get("outputs", []) == []
