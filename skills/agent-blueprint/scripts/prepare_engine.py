#!/usr/bin/env python3
"""Materialize the bundled, pinned source archive into an explicit empty directory.

Uses only the Python 3.10+ standard library. This does not install dependencies,
configure credentials, run the engine, or make network requests. On success,
stdout contains only the absolute engine root, suitable for use by another tool.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath


EXPECTED_SHA256 = "56c89c7836fb396240fbf0d90e904a338b7f660124165776f449b218fc6b178b"
ARCHIVE = Path(__file__).resolve().parent.parent / "assets" / "agent-blueprint-source.zip"
ARCHIVE_ROOT = "agent-blueprint-main"
REQUIRED_FILES = {
    "BLUEPRINT.md",
    "使用引导.md",
    "blueprint/cli.py",
    "blueprint/rules.py",
    "blueprint/scanner.py",
}


def verify_digest(archive: Path) -> None:
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != EXPECTED_SHA256:
        raise ValueError("Bundled archive SHA-256 does not match the pinned source; no files were extracted.")


def inspect_archive(bundle: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, Path]]:
    """Validate every entry before writing anything; strip the one known root."""
    entries: list[tuple[zipfile.ZipInfo, Path]] = []
    seen: set[str] = set()
    files: set[str] = set()
    for info in bundle.infolist():
        name = info.filename
        if not name or "\\" in name or "\x00" in name:
            raise ValueError(f"Unsafe archive member name: {name!r}")
        pieces = name.rstrip("/").split("/")
        path = PurePosixPath(name)
        if path.is_absolute() or any(piece in ("", ".", "..") for piece in pieces):
            raise ValueError(f"Unsafe archive member path: {name!r}")
        if pieces[0] != ARCHIVE_ROOT:
            raise ValueError(f"Unexpected archive root: {name!r}")
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if stat.S_ISLNK(mode) or kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError(f"Links and special files are not allowed: {name!r}")
        if info.flag_bits & 1:
            raise ValueError(f"Encrypted archive entries are not supported: {name!r}")
        if len(pieces) == 1:
            if not info.is_dir():
                raise ValueError("The archive root must be a directory.")
            continue
        relative = Path(*pieces[1:])
        key = relative.as_posix()
        if key in seen:
            raise ValueError(f"Duplicate archive member: {name!r}")
        seen.add(key)
        if not info.is_dir():
            files.add(key)
        entries.append((info, relative))
    if not REQUIRED_FILES.issubset(files):
        missing = ", ".join(sorted(REQUIRED_FILES - files))
        raise ValueError(f"The archive is missing engine files: {missing}")
    for _info, relative in entries:
        if any(parent.as_posix() in files for parent in relative.parents if parent != Path(".")):
            raise ValueError(f"A file is also used as a directory: {relative}")
    return entries


def prepare_engine(destination: Path) -> Path:
    requested = destination.expanduser()
    if requested.is_symlink():
        raise ValueError("Destination must not be a symbolic link.")
    root = requested.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError(f"Destination must be absent or an empty directory; refusing to overwrite: {root}")
    verify_digest(ARCHIVE)
    with zipfile.ZipFile(ARCHIVE) as bundle:
        entries = inspect_archive(bundle)
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise ValueError(f"Destination is no longer empty; refusing to overwrite: {root}")
        for info, relative in entries:
            target = root / relative
            if not target.resolve().is_relative_to(root):
                raise ValueError(f"Archive member would escape the destination: {relative}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.parent.resolve().is_relative_to(root):
                raise ValueError(f"Archive parent would escape the destination: {relative}")
            with bundle.open(info) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                target.chmod(mode)
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path,
                        help="Explicit engine root to create; must be absent or empty.")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required.")
    try:
        root = prepare_engine(args.destination)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"prepare_engine: {exc}", file=sys.stderr)
        return 1
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
