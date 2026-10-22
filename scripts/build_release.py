"""Build public-source and installable-skill ZIPs using an explicit allowlist."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from check_package import main as validate
from check_docs import main as validate_docs

ROOT = Path(__file__).resolve().parents[1]
SKILL_PREFIX = "skills/conduct-best-skills/"
SKILL_FILES = [
    "SKILL.md", "agents/openai.yaml",
    "references/commands.md", "references/command-scope.md", "references/preferences.md",
    "scripts/preferences.py", "scripts/activity.py", "scripts/workbench.py", "assets/preferences.html", "references/workbench.md",
    "references/stage-1-context.md", "references/stage-2-goals.md",
    "references/stage-3-planning.md", "references/stage-4-execution.md",
    "references/stage-5-verification.md", "references/stage-6-refinement.md",
    "references/stage-7-delivery.md", "references/contracts.md",
    "references/learning.md", "references/runtime.md", "scripts/conduct.py", "scripts/demo.py",
    "references/workflows.md", "templates/task-brief.md", "templates/workspace-agents.md",
    "references/discovery.md", "scripts/discovery.py", "scripts/discovery_core.py",
    "scripts/discovery_io.py", "scripts/discovery_sources.py",
]
COMMAND_NAMES = ("context", "goals", "plan", "discover", "build", "improve", "resume", "verify", "refine", "deliver", "preferences", "reflect", "workbench")
COMMAND_FILES = [f"skills/conduct-{name}/{file}" for name in COMMAND_NAMES
                 for file in ("SKILL.md", "agents/openai.yaml")]
PUBLIC_FILES = [
    "assets/workbench/workflow.png", "assets/workbench/preferences.png", "scripts/preview_workbench.py",
    "assets/illustrations/shared-route.png", "assets/illustrations/interaction-scenes.png",
    "assets/illustrations/generation-prompts.json",
    "assets/illustrations/intent-to-evidence.png",
    "assets/diagrams/context-memory.svg", "assets/diagrams/context-memory-cn.svg",
    "scripts/visuals_zh.json",
    "assets/branding/hero-cn.svg", "assets/diagrams/workflow-cn.svg",
    "assets/diagrams/before-after-cn.svg", "assets/diagrams/agent-interaction-cn.svg",
    "assets/diagrams/orchestration-cn.svg",
    "README_CN.md", "docs/architecture.md", "docs/audit.md", "docs/examples.md",
    "docs/commands-and-preferences.md", "tests/test_preferences.py", "tests/test_workbench.py",
    "docs/visual-design.md", "docs/validation.md", "docs/implementation-plan.md", "tests/test_runtime.py",
    "docs/reference-study.md", "docs/usability-evaluation.md", "tests/test_workflow.py",
    "docs/discovery-design.md", "docs/discovery-adapters.md", "docs/discovery-validation.md",
    "tests/test_discovery_core.py", "tests/test_discovery_io.py", "tests/test_discovery_sources.py",
    "tests/test_discovery_engine.py", "evals/discovery.json",
    "assets/branding/hero.svg", "assets/diagrams/workflow.svg",
    "assets/diagrams/workflow.mmd", "assets/diagrams/before-after.svg",
    "assets/diagrams/agent-interaction.svg", "assets/diagrams/orchestration.svg",
    "scripts/build_visuals.py", "scripts/check_docs.py",
    "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
    ".gitignore", ".gitattributes", "evals/README.md", "evals/cases.json",
    "evals/optimization.md",
    "scripts/check_package.py", "scripts/build_release.py", "scripts/check_release.py", "scripts/validate_runtime.py",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/PULL_REQUEST_TEMPLATE.md", ".github/workflows/ci.yml",
] + [SKILL_PREFIX + name for name in SKILL_FILES] + COMMAND_FILES


def suite_entries():
    return ([(SKILL_PREFIX + name, "conduct-best-skills/" + name) for name in SKILL_FILES]
            + [(name, name.removeprefix("skills/")) for name in COMMAND_FILES]
            + [("LICENSE", name + "/LICENSE") for name in ["conduct-best-skills", *["conduct-" + n for n in COMMAND_NAMES]]])


def write_archive(output, entries):
    # Preflight every input before opening the destination ZIP.
    for relative, _ in entries:
        source = ROOT / relative
        if not source.is_file() or source.is_symlink() or source.resolve() != source.absolute():
            raise ValueError(f"Missing or redirected release input: {relative}")
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for relative, member in entries:
            archive.write(ROOT / relative, member)
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive integrity check failed")
        if sorted(archive.namelist()) != sorted(member for _, member in entries):
            raise ValueError("Archive contents differ from release allowlist")


def main():
    validate()
    validate_docs()
    destination = ROOT / "dist"
    if destination.is_symlink() or destination.resolve() != destination.absolute():
        raise ValueError("Refusing redirected distribution directory")
    destination.mkdir(exist_ok=True)
    packages = {
        "conduct-best-skills-suite.zip": suite_entries(),
        "conduct-best-skills-source.zip": [
            (name, "conduct-best-skills/" + name) for name in PUBLIC_FILES
        ],
        "conduct-best-skills-skill.zip": [
            (SKILL_PREFIX + name, "conduct-best-skills/" + name) for name in SKILL_FILES
        ] + [("LICENSE", "conduct-best-skills/LICENSE")],
    }
    for filename, entries in packages.items():
        output = destination / filename
        if output.is_symlink() or output.resolve() != output.absolute():
            raise ValueError("Refusing redirected archive destination")
        write_archive(output, entries)
        print(f"Built dist/{filename}: {len(entries)} files; integrity verified")


if __name__ == "__main__":
    main()
