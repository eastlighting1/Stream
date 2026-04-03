import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "tmp-debug-store",
    "tmp_example_run",
    "dist",
    "build",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)\btoken\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)\bsecret\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*['\"][^'\"]+['\"]"),
]

DANGEROUS_API_PATTERNS = {
    "pickle": re.compile(r"\bpickle\b"),
    "marshal": re.compile(r"\bmarshal\b"),
    "eval(": re.compile(r"\beval\s*\("),
    "exec(": re.compile(r"\bexec\s*\("),
}

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".pyi",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
}


def iter_files(*roots: Path) -> list[Path]:
    files: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        if base.is_file():
            files.append(base)
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def file_exists_check() -> list[str]:
    failures: list[str] = []
    if not (ROOT / "SECURITY.md").exists():
        failures.append("missing SECURITY.md")
    if not (ROOT / "uv.lock").exists():
        failures.append("missing uv.lock")
    return failures


def dangerous_api_check() -> list[str]:
    failures: list[str] = []
    for path in iter_files(ROOT / "src", ROOT / "examples", ROOT / "tests"):
        if path.suffix not in {".py", ".pyi"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in DANGEROUS_API_PATTERNS.items():
            if pattern.search(text):
                relative = path.relative_to(ROOT)
                failures.append(f"dangerous api pattern '{label}' found in {relative}")
    return failures


def secret_scan_check() -> list[str]:
    failures: list[str] = []
    for path in iter_files(
        ROOT / "src",
        ROOT / "examples",
        ROOT / "tests",
        ROOT / "docs",
        ROOT / "README.md",
        ROOT / "README.ko.md",
    ):
        if path.suffix and path.suffix not in TEXT_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"secret-like pattern found in {path.relative_to(ROOT)}")
                break
    return failures


def test_presence_check() -> list[str]:
    failures: list[str] = []
    test_files = list((ROOT / "tests").rglob("test_*.py"))
    if not test_files:
        failures.append("missing pytest-style test files under tests/")
    names = [path.name for path in test_files]
    if not any("stream" in name for name in names):
        failures.append("tests/ exists but does not include stream-focused pytest files")
    return failures


def example_presence_check() -> list[str]:
    failures: list[str] = []
    example_path = ROOT / "examples" / "basic_usage.py"
    if not example_path.exists():
        failures.append("missing examples/basic_usage.py")
    return failures


def artifact_contents_check() -> list[str]:
    failures: list[str] = []
    dist = ROOT / "dist"
    if not dist.exists():
        failures.append("missing dist/; build step may not have run")
        return failures

    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if not wheels:
        failures.append("missing wheel artifact in dist/")
    if not sdists:
        failures.append("missing sdist artifact in dist/")

    banned_markers = (".venv/", "__pycache__/", ".pyc", "tmp_example_run/", "tmp-debug-store/")

    for wheel in wheels:
        with zipfile.ZipFile(wheel) as zf:
            names = zf.namelist()
        if not any(name.startswith("stream/") for name in names):
            failures.append(f"wheel missing stream package contents: {wheel.name}")
        for marker in banned_markers:
            if any(marker in name for name in names):
                failures.append(f"wheel contains banned artifact marker '{marker}': {wheel.name}")

    for sdist in sdists:
        with tarfile.open(sdist) as tf:
            names = tf.getnames()
        for marker in banned_markers:
            if any(marker in name for name in names):
                failures.append(f"sdist contains banned artifact marker '{marker}': {sdist.name}")

    return failures


def workflow_presence_check() -> list[str]:
    failures: list[str] = []
    workflow = ROOT / ".github" / "workflows" / "checks.yml"
    if not workflow.exists():
        failures.append("missing .github/workflows/checks.yml")
    return failures


def run() -> int:
    failures: list[str] = []
    failures.extend(file_exists_check())
    failures.extend(workflow_presence_check())
    failures.extend(test_presence_check())
    failures.extend(example_presence_check())
    failures.extend(dangerous_api_check())
    failures.extend(secret_scan_check())
    failures.extend(artifact_contents_check())

    if failures:
        print("policy checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("policy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
