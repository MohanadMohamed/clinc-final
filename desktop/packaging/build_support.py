"""Allowlisted Windows test payload staging; never copies local configuration/data."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET_SUFFIXES = {
    ".html",
    ".js",
    ".css",
    ".svg",
    ".png",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
}


def verify_build_dependencies():
    for name in ("requirements-build-tools.txt", "requirements-windows.txt"):
        content = (ROOT / "desktop" / "packaging" / name).read_text()
        for package, version in re.findall(
            r"^([\w-]+)==([^\s]+)", content, re.MULTILINE
        ):
            if importlib.metadata.version(package) != version:
                raise ValueError(
                    "Build environment differs from pinned Windows requirements"
                )


def source_files(root: Path):
    files = [root / "backend" / name for name in ("requirements.txt", "alembic.ini")]
    for name in ("app", "migrations"):
        files.extend(
            path
            for path in (root / "backend" / name).rglob("*.py")
            if not any(
                part.startswith(".") or part == "__pycache__"
                for part in path.relative_to(root).parts
            )
        )
    dist = root / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        raise ValueError("Build React production assets first")
    files.extend(
        path
        for path in dist.rglob("*")
        if path.is_file()
        and path.suffix in ASSET_SUFFIXES
        and not any(part.startswith(".") for part in path.relative_to(dist).parts)
    )
    for path in sorted(files):
        # Reject symlinks, including symlinked source directories.
        if not path.is_file() or any(
            item.is_symlink() for item in (path, *path.parents)
        ):
            raise ValueError("Only regular allowlisted build inputs are permitted")
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Build input escapes repository")
    return sorted(files)


def stage_host(root: Path, output: Path):
    files = source_files(root)
    target = output / "doctor-host"
    target.mkdir(parents=True, exist_ok=False)
    for path in files:
        destination = target / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    profiles = output / "profiles"
    profiles.mkdir(exist_ok=False)
    for name in ("doctor-client.example.toml", "reception-client.example.toml"):
        shutil.copyfile(root / "desktop" / "packaging" / name, profiles / name)


def manifest(output: Path):
    result = {}
    for directory in ("doctor-host", "profiles", "client"):
        for path in sorted((output / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError("Artifact symlinks are forbidden")
            if path.is_file():
                result[path.relative_to(output).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    (output / "SHA256SUMS.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    # pip freeze can disclose direct-install URLs; retain names/versions only.
    inventory = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": sorted(
            [
                {"name": item.metadata["Name"], "version": item.version}
                for item in importlib.metadata.distributions()
            ],
            key=lambda item: item["name"].lower(),
        ),
    }
    (output / "BUILD-ENVIRONMENT.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage_host(ROOT, args.output)
    manifest(args.output)
    print("PASS: allowlisted doctor payload and artifact checksums prepared")
