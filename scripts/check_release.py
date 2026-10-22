"""Verify allowlisted bytes and execute both archives outside the source checkout."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from build_release import PUBLIC_FILES, SKILL_FILES, SKILL_PREFIX

ROOT = Path(__file__).resolve().parents[1]


def run(argv, cwd):
    env = dict(os.environ, PYTHONUTF8="1")
    result = subprocess.run([sys.executable, *map(str, argv)], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stdout.decode("utf-8", errors="replace"))


def main():
    scratch = ROOT / "local" / "release-workspaces"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="archive-", dir=scratch) as name:
        destination = Path(name).resolve()
        assert destination.is_relative_to(scratch.resolve())
        for kind, expected in (
            ("skill", {"conduct-best-skills/" + f: SKILL_PREFIX + f for f in SKILL_FILES} | {"conduct-best-skills/LICENSE": "LICENSE"}),
            ("source", {"conduct-best-skills/" + f: f for f in PUBLIC_FILES}),
        ):
            with ZipFile(ROOT / "dist" / f"conduct-best-skills-{kind}.zip") as archive:
                assert sorted(archive.namelist()) == sorted(expected), "Archive differs from allowlist"
                for member, source in expected.items():
                    assert archive.read(member) == (ROOT / source).read_bytes(), f"Stale archive member: {member}"
                    target = (destination / kind / member).resolve()
                    assert target.is_relative_to(destination), "Unsafe archive member"
                archive.extractall(destination / kind)
        installed = destination / "skill" / "conduct-best-skills"
        run([installed / "scripts/demo.py", "--output", destination / "standalone-demo"], destination)
        run([installed / "scripts/conduct.py", "--workspace", destination / "standalone-demo", "status"], destination)
        # Exercise the newcomer path using only the installed Skill and a user project.
        starter = destination / "starter-project"
        starter.mkdir()
        for filename in ("total.py", "check.py"):
            (starter / filename).write_bytes((destination / "standalone-demo" / filename).read_bytes())
        run([installed / "scripts/conduct.py", "--workspace", starter, "start", "--goal", "Check scalar total",
             "--requirement", "Totals are correct", "--artifact", "total.py", "--input", "check.py",
             "--", "{python}", "-B", "check.py"], destination)
        run([installed / "scripts/conduct.py", "--workspace", starter, "verify-ready", "--execute"], destination)
        run([installed / "scripts/conduct.py", "--workspace", starter, "next"], destination)
        probe = starter / "skills" / "csv-reader"
        probe.mkdir(parents=True)
        (probe / "SKILL.md").write_text("---\nname: csv-reader\ndescription: Read CSV tables\n---\nCheck headers.\n", encoding="utf-8")
        run([installed / "scripts/conduct.py", "--workspace", starter, "discover", "--root", "skills",
             "--keyword", "csv", "--need", "csv", "--no-cache", "--output", "discovery.json"], destination)
        discovery = json.loads((starter / "discovery.json").read_text(encoding="utf-8"))
        assert discovery["composition"]["missing"] == [] and discovery["requests_used"] == 0
        assert discovery["candidates"][0]["name"] == "csv-reader"
        assert discovery["catalog"]["capabilities"][0]["available"] is False
        source = destination / "source" / "conduct-best-skills"
        run([source / "scripts/check_package.py"], source)
        run([source / "scripts/check_docs.py"], source)
        for path in source.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 10))
    print("PASS: archive allowlists and byte parity; installed demo, start/verify-ready/next and discovery; extracted source checks; Python 3.10 syntax")


if __name__ == "__main__":
    main()
