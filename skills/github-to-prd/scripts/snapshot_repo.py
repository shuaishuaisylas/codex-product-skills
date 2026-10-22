#!/usr/bin/env python3
"""Create a read-only, commit-pinned inventory of tracked repository text files.

Uses only Python's standard library and Git. It never executes repository code.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from urllib.parse import quote, urlsplit


class SnapshotError(Exception):
    pass


class SourceSymlink(SnapshotError):
    pass


def git(repo, *args):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
         "--literal-pathspecs", "-C", str(repo), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise SnapshotError("Git could not read the repository (%s)." % args[0])
    return result.stdout


def relative_path(value, label, allow_dot=False):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise SnapshotError(label + " must be a nonempty POSIX relative path.")
    parts = value.split("/")
    if value.startswith("/") or ".." in parts or ("." in parts and not (allow_dot and value == ".")):
        raise SnapshotError(label + " must not be absolute or contain dot segments.")
    if any(part == "" for part in parts):
        raise SnapshotError(label + " must not contain empty path segments.")
    return PurePosixPath(value).as_posix()


def checked_source(root, relative):
    path = root
    for component in PurePosixPath(relative).parts:
        path = path / component
        if path.is_symlink():
            raise SourceSymlink("Symlink scope/source is not followed: " + relative)
    if not path.resolve(strict=False).is_relative_to(root):
        raise SnapshotError("Source escapes the repository: " + relative)
    return path


def github_url(value, explicit=False):
    value = value.strip()
    if value.startswith("git@github.com:") and not explicit:
        path = value[len("git@github.com:"):]
    else:
        parsed = urlsplit(value)
        allowed_schemes = ("https",) if explicit else ("https", "ssh")
        if (parsed.scheme not in allowed_schemes or parsed.hostname != "github.com"
                or parsed.port is not None or parsed.query or parsed.fragment
                or parsed.password or (parsed.scheme == "https" and parsed.username)
                or (parsed.scheme == "ssh" and parsed.username not in (None, "git"))):
            raise SnapshotError("Use a GitHub origin or --repo-url https://github.com/OWNER/REPO.")
        path = parsed.path.lstrip("/")
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
        raise SnapshotError("GitHub URL must name exactly one owner and one repository.")
    if any(part in (".", "..") for part in path.split("/")):
        raise SnapshotError("Invalid GitHub repository URL.")
    return "https://github.com/" + path


def new_output_path(value, root):
    path = Path(value).expanduser().absolute()
    if not path.parent.is_dir():
        raise SnapshotError("Output parent directory must already exist.")
    if path.exists() or path.is_symlink():
        raise SnapshotError("Output already exists; choose a new file.")
    if path.resolve(strict=False).is_relative_to(root):
        raise SnapshotError("Snapshot output must be outside the target repository.")
    return path


def capture(args):
    requested_repo = Path(args.repo).expanduser().resolve(strict=True)
    root = Path(os.fsdecode(git(requested_repo, "rev-parse", "--show-toplevel")).strip()).resolve(strict=True)
    scope = relative_path(args.scope, "Scope", allow_dot=True)
    scoped_path = checked_source(root, scope)
    if not scoped_path.is_dir():
        raise SnapshotError("Scope must be an existing directory inside the Git root.")
    out = new_output_path(args.out, root)
    commit = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SnapshotError("A full 40-character Git commit is required.")
    dirty = bool(git(root, "status", "--porcelain=v1", "-z", "--untracked-files=no"))
    if dirty and not args.allow_dirty:
        raise SnapshotError("Tracked changes exist. Commit them or explicitly use --allow-dirty.")
    if args.repo_url:
        url = github_url(args.repo_url, explicit=True)
    else:
        try:
            origin = git(root, "config", "--get", "remote.origin.url").decode("utf-8").strip()
        except SnapshotError:
            raise SnapshotError("No origin URL found; supply --repo-url https://github.com/OWNER/REPO.")
        url = github_url(origin)
    tracked_raw = git(root, "ls-files", "-z", "--", scope).split(b"\0")
    tracked = sorted({os.fsdecode(item) for item in tracked_raw if item})
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    files, skipped = [], []
    for relative in tracked:
        relative_path(relative, "Tracked source path")
        try:
            source = checked_source(root, relative)
        except SourceSymlink:
            skipped.append({"path": relative, "reason": "symlink_not_followed"})
            continue
        try:
            mode = source.stat().st_mode
            if not stat.S_ISREG(mode):
                skipped.append({"path": relative, "reason": "not_regular_file"})
                continue
            raw = source.read_bytes()
        except OSError:
            skipped.append({"path": relative, "reason": "unreadable_or_missing"})
            continue
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped.append({"path": relative, "reason": "binary_or_non_utf8"})
            continue
        if b"\0" in raw:
            skipped.append({"path": relative, "reason": "binary_or_non_utf8"})
            continue
        files.append({
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "lines": len(raw.splitlines()),
            "github_url": None if dirty else "%s/blob/%s/%s" % (url, commit, quote(relative, safe="/")),
        })
    # Catch an editor or Git process changing the checkout during the inventory.
    if git(root, "rev-parse", "HEAD").decode("ascii").strip() != commit:
        raise SnapshotError("HEAD changed during capture; repeat the snapshot.")
    if bool(git(root, "status", "--porcelain=v1", "-z", "--untracked-files=no")) != dirty:
        raise SnapshotError("Tracked working-tree state changed during capture; repeat the snapshot.")
    result = {
        "schema_version": 1,
        "repository": {
            "url": url, "commit": commit, "scope": scope, "dirty": dirty,
            "untracked_count": sum(bool(item) for item in untracked),
            "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "files": files,
        "skipped": skipped,
    }
    with out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=True, indent=2)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--scope", default=".", help="Directory relative to the Git root (default: .)")
    parser.add_argument("--repo-url", help="Explicit HTTPS GitHub URL when the origin is unavailable")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow tracked changes; all GitHub file URLs become null")
    args = parser.parse_args()
    try:
        result = capture(args)
    except (SnapshotError, OSError, ValueError, UnicodeError) as exc:
        print("snapshot_repo: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"created": str(Path(args.out).absolute()), "files": len(result["files"]),
                      "skipped": len(result["skipped"]), "dirty": result["repository"]["dirty"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
