"""Check portable skill packaging and the design-derived case inventory."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "conduct-best-skills"


def main():
    errors = []
    entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if not entry.startswith("---\nname: conduct-best-skills\ndescription: "):
        errors.append("Missing or invalid entry metadata")
    if not (SKILL / "agents" / "openai.yaml").is_file():
        errors.append("Missing UI metadata")
    if len(list((SKILL / "references").glob("stage-*.md"))) != 7:
        errors.append("Expected seven stage references")
    documents = [*ROOT.glob("*.md"), *(ROOT / "evals").glob("*.md"),
                 *(ROOT / "skills").rglob("*.md"), *(ROOT / ".github").rglob("*.md")]
    names = set()
    for folder in sorted((ROOT / "skills").iterdir()):
        if not folder.is_dir():
            continue
        body = (folder / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---", body)
        if not match or match[1] != folder.name or match[1] in names:
            errors.append(f"Invalid or duplicate skill name: {folder.name}")
        names.add(folder.name)
        metadata = (folder / "agents/openai.yaml").read_text(encoding="utf-8")
        if "$" + folder.name not in metadata:
            errors.append(f"Default prompt does not name its skill: {folder.name}")
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).exists():
                errors.append(f"Broken link in {path.relative_to(ROOT)}: {target}")
        if re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/(?:Users|home)/", text):
            errors.append(f"Non-portable local path in {path.relative_to(ROOT)}")
    cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    expected = {"stage-1": 24, "stage-2": 42, "stage-3": 84, "stage-4-7": 54}
    if Counter(c["group"] for c in cases) != expected:
        errors.append("Case counts differ from design baseline")
    if len({c["id"] for c in cases}) != len(cases):
        errors.append("Duplicate case IDs")
    for case in cases:
        if not all(case.get(k) for k in ("id", "group", "scenario", "expected", "design_reference", "status")):
            errors.append("Incomplete case")
        if case["status"] != "NOT_RUN":
            errors.append("Catalog must not imply an unrecorded test run")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: portable package, local links, seven stages, {len(cases)} unexecuted design cases")


if __name__ == "__main__":
    main()
