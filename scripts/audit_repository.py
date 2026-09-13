"""Audit public-release safeguards that can be checked automatically."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:password|api[_-]?key)\s*=\s*['\"][^'\"]+"),
]


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def relative_readme_targets(text: str) -> list[str]:
    targets = re.findall(r"\[[^]]*\]\(([^)]+)\)", text)
    return [target.split("#", 1)[0] for target in targets if not target.startswith(("http://", "https://", "#"))]


def main() -> None:
    tracked = tracked_files()
    relative = [path.relative_to(ROOT).as_posix() for path in tracked]
    prohibited = [
        path for path in relative
        if path.startswith(("data/restricted/", "data/cache/", "data/raw/regional/"))
        or (path.startswith("data/raw/") and path != "data/raw/README.md")
    ]
    if prohibited:
        raise RuntimeError(f"Raw, cache or restricted files are tracked: {prohibited}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = [target for target in relative_readme_targets(readme) if not (ROOT / target).exists()]
    if missing:
        raise RuntimeError(f"README links point to missing local files: {missing}")

    findings = []
    for path in tracked:
        if path.stat().st_size > 5_000_000:
            findings.append(f"large tracked file: {path.relative_to(ROOT)}")
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(f"possible credential in {path.relative_to(ROOT)}")
                break
    if findings:
        raise RuntimeError("; ".join(findings))
    print(f"Repository audit passed for {len(tracked)} tracked files.")


if __name__ == "__main__":
    main()
