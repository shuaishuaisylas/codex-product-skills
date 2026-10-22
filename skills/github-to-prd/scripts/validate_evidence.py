#!/usr/bin/env python3
"""Check snapshot drift, source locations, evidence status rules and runtime references.

This checks structure and evidence locations. A human/Codex review must still
decide whether cited sources support a requirement and whether cases are meaningful.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys


class EvidenceError(Exception):
    pass


def git(repo, *args):
    result = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
                             "--literal-pathspecs", "-C", str(repo), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise EvidenceError("Git could not read the repository (%s)." % args[0])
    return result.stdout


def positive_int(value):
    return type(value) is int and value > 0


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def relative_path(value, label, allow_dot=False):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise EvidenceError(label + " must be a nonempty POSIX relative path.")
    parts = value.split("/")
    if value.startswith("/") or ".." in parts or ("." in parts and not (allow_dot and value == ".")) or "" in parts:
        raise EvidenceError(label + " must not be absolute or contain dot/empty segments.")
    return PurePosixPath(value).as_posix()


def safe_file(root, relative, label):
    relative_path(relative, label)
    if root.is_symlink():
        raise EvidenceError(label + " root must not be a symlink.")
    path = root
    for component in PurePosixPath(relative).parts:
        path = path / component
        if path.is_symlink():
            raise EvidenceError(label + " has a symlink component: " + relative)
    if not path.resolve(strict=False).is_relative_to(root.resolve(strict=True)):
        raise EvidenceError(label + " escapes its root: " + relative)
    if not stat.S_ISREG(path.stat().st_mode):
        raise EvidenceError(label + " must be a regular file: " + relative)
    return path


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise EvidenceError("JSON document must be an object: " + path.name)
    return value


def validate(args, errors):
    requested_repo = Path(args.repo).expanduser().resolve(strict=True)
    root = Path(os.fsdecode(git(requested_repo, "rev-parse", "--show-toplevel")).strip()).resolve(strict=True)
    manifest = read_json(Path(args.manifest).expanduser())
    evidence = read_json(Path(args.evidence).expanduser())
    artifacts = Path(args.artifacts).expanduser().absolute()
    if not artifacts.is_dir() or artifacts.is_symlink():
        raise EvidenceError("Artifacts root must be an existing directory and must not be a symlink.")
    if any(parent.is_symlink() for parent in artifacts.parents):
        raise EvidenceError("Artifacts root must not have a symlink parent.")
    artifacts = artifacts.resolve(strict=True)
    if manifest.get("schema_version") != 1 or type(manifest.get("schema_version")) is not int:
        errors.append("Manifest schema_version must be 1.")
    if evidence.get("schema_version") != 1 or type(evidence.get("schema_version")) is not int:
        errors.append("Evidence schema_version must be 1.")
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise EvidenceError("Manifest repository must be an object.")
    commit = repository.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("Manifest commit must be a full 40-character lowercase Git SHA.")
    current_commit = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if current_commit != commit:
        errors.append("Repository HEAD differs from the manifest commit.")
    scope = relative_path(repository.get("scope"), "Manifest scope", allow_dot=True)
    tracked = {os.fsdecode(item) for item in git(root, "ls-files", "-z", "--", scope).split(b"\0") if item}
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list):
        raise EvidenceError("Manifest files must be an array.")
    file_index = {}
    for item in manifest_files:
        if not isinstance(item, dict):
            errors.append("Every manifest file must be an object.")
            continue
        try:
            relative = relative_path(item.get("path"), "Manifest source path")
            if scope != "." and not relative.startswith(scope + "/"):
                raise EvidenceError("Manifest source lies outside its declared scope: " + relative)
            if relative in file_index:
                raise EvidenceError("Duplicate manifest path: " + relative)
            file_index[relative] = item
            if relative not in tracked:
                errors.append("Manifest source is no longer tracked: " + relative)
            if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
                errors.append("Invalid manifest SHA-256: " + relative)
            for field in ("bytes", "lines"):
                if type(item.get(field)) is not int or item[field] < 0:
                    errors.append("Invalid manifest " + field + ": " + relative)
            raw = safe_file(root, relative, "Source").read_bytes()
            if hashlib.sha256(raw).hexdigest() != item.get("sha256"):
                errors.append("Source hash drift: " + relative)
            if len(raw) != item.get("bytes") or len(raw.splitlines()) != item.get("lines"):
                errors.append("Source size/line metadata drift: " + relative)
        except (EvidenceError, OSError, ValueError) as exc:
            errors.append(str(exc))
    skipped = manifest.get("skipped")
    if not isinstance(skipped, list):
        errors.append("Manifest skipped must be an array.")
        skipped = []
    skipped_paths = set()
    for item in skipped:
        try:
            if not isinstance(item, dict):
                raise EvidenceError("Every skipped entry must be an object.")
            relative = relative_path(item.get("path"), "Skipped source path")
            if scope != "." and not relative.startswith(scope + "/"):
                raise EvidenceError("Skipped source lies outside its declared scope: " + relative)
            if relative in skipped_paths or relative in file_index:
                errors.append("Duplicate manifest/skipped path: " + relative)
            skipped_paths.add(relative)
        except EvidenceError as exc:
            errors.append(str(exc))
    if tracked != set(file_index) | skipped_paths:
        errors.append("Tracked file inventory differs from the manifest (including skipped entries).")
    requirements = evidence.get("requirements")
    questions = evidence.get("questions")
    if not isinstance(requirements, list) or not requirements:
        raise EvidenceError("Evidence requirements must be a nonempty array.")
    if not isinstance(questions, list):
        raise EvidenceError("Evidence questions must be an array.")
    all_ids, question_ids, question_refs = set(), set(), set()

    def register(record, label):
        if not isinstance(record, dict):
            errors.append(label + " must be an object.")
            return None
        identifier = record.get("id")
        if not nonempty(identifier):
            errors.append(label + " id must be a nonempty string.")
            return None
        if identifier in all_ids:
            errors.append("Duplicate record id: " + identifier)
        all_ids.add(identifier)
        return identifier

    for question in questions:
        identifier = register(question, "Question")
        if identifier is None:
            continue
        question_ids.add(identifier)
        if not nonempty(question.get("question")) or not nonempty(question.get("reason")):
            errors.append(identifier + ": question and reason must be nonempty strings.")
    artifact_cache = {}
    statuses = {"runtime_verified", "source_supported", "documented_only", "conflict", "unknown"}
    status_counts = {status: 0 for status in sorted(statuses)}
    for requirement in requirements:
        identifier = register(requirement, "Requirement")
        if identifier is None:
            continue
        if not nonempty(requirement.get("statement")):
            errors.append(identifier + ": statement must be a nonempty string.")
        status = requirement.get("status")
        if status not in statuses:
            errors.append(identifier + ": invalid evidence status.")
        else:
            status_counts[status] += 1
        sources = requirement.get("sources")
        runtime = requirement.get("runtime")
        refs = requirement.get("open_question_ids")
        if not isinstance(sources, list):
            errors.append(identifier + ": sources must be an array.")
            sources = []
        if not isinstance(runtime, list):
            errors.append(identifier + ": runtime must be an array.")
            runtime = []
        if not isinstance(refs, list) or any(not nonempty(ref) for ref in refs):
            errors.append(identifier + ": open_question_ids must be an array of nonempty strings.")
            refs = []
        for ref in refs:
            question_refs.add(ref)
            if ref not in question_ids:
                errors.append(identifier + ": missing question reference " + ref)
        source_kinds, distinct_sources = set(), set()
        for source in sources:
            try:
                if not isinstance(source, dict):
                    raise EvidenceError(identifier + ": source must be an object.")
                relative = relative_path(source.get("path"), identifier + " source path")
                if relative not in file_index:
                    raise EvidenceError(identifier + ": source not present in manifest: " + relative)
                safe_file(root, relative, "Source")
                start, end = source.get("start_line"), source.get("end_line")
                lines = file_index[relative].get("lines")
                if not positive_int(start) or not positive_int(end) or start > end or type(lines) is not int or end > lines:
                    raise EvidenceError(identifier + ": invalid source line range: " + relative)
                kind = source.get("kind")
                if kind not in {"code", "documentation", "test"}:
                    raise EvidenceError(identifier + ": source kind must be code, documentation, or test.")
                source_kinds.add(kind)
                distinct_sources.add((relative, start, end))
            except (EvidenceError, OSError, ValueError) as exc:
                errors.append(str(exc))
        passed_runtime = bool(runtime)
        executed_runtime = False
        for reference in runtime:
            try:
                if not isinstance(reference, dict):
                    raise EvidenceError(identifier + ": runtime reference must be an object.")
                artifact_name = relative_path(reference.get("artifact"), identifier + " runtime artifact")
                case_id = reference.get("case_id")
                if not nonempty(case_id):
                    raise EvidenceError(identifier + ": runtime case_id must be a nonempty string.")
                if artifact_name not in artifact_cache:
                    artifact = read_json(safe_file(artifacts, artifact_name, "Runtime artifact"))
                    cases = artifact.get("cases")
                    if not isinstance(cases, list):
                        raise EvidenceError("Runtime artifact cases must be an array: " + artifact_name)
                    case_index = {}
                    for case in cases:
                        if not isinstance(case, dict) or not nonempty(case.get("id")):
                            raise EvidenceError("Runtime case must have a nonempty id: " + artifact_name)
                        if case["id"] in case_index:
                            raise EvidenceError("Duplicate runtime case id: " + case["id"])
                        if case.get("status") not in {"passed", "failed", "not_run"}:
                            raise EvidenceError("Invalid runtime case status: " + case["id"])
                        if not nonempty(case.get("expected")) or not nonempty(case.get("observed")):
                            raise EvidenceError("Runtime case needs nonempty expected/observed strings: " + case["id"])
                        case_index[case["id"]] = case
                    artifact_cache[artifact_name] = case_index
                case = artifact_cache[artifact_name].get(case_id)
                if case is None:
                    raise EvidenceError(identifier + ": runtime case does not exist: " + case_id)
                passed_runtime = passed_runtime and case["status"] == "passed"
                executed_runtime = executed_runtime or case["status"] in {"passed", "failed"}
            except (EvidenceError, OSError, ValueError, UnicodeError) as exc:
                errors.append(str(exc))
                passed_runtime = False
        has_implementation = bool(source_kinds & {"code", "test"})
        if status == "runtime_verified" and (not sources or not has_implementation or not runtime or not passed_runtime):
            errors.append(identifier + ": runtime_verified requires code/test sources and all referenced cases passed.")
        if status == "source_supported" and not has_implementation:
            errors.append(identifier + ": source_supported requires a code/test source.")
        if status == "documented_only" and "documentation" not in source_kinds:
            errors.append(identifier + ": documented_only requires a documentation source.")
        has_conflict_evidence = len(distinct_sources) >= 2 or (bool(distinct_sources) and executed_runtime)
        if status == "conflict" and (not has_conflict_evidence or not refs):
            errors.append(identifier + ": conflict requires a question and either two distinct source locations or a source plus an executed runtime case.")
        if status == "unknown" and not refs:
            errors.append(identifier + ": unknown requires a question.")
    return {"requirements": len(requirements), "questions": len(questions), "source_files": len(file_index),
            "unlinked_global_questions": len(question_ids - question_refs),
            "runtime_artifacts": len(artifact_cache), "statuses": status_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--out", required=True, help="New report file; parent directory must exist")
    args = parser.parse_args()
    errors, counts = [], {}
    out = Path(args.out).expanduser().absolute()
    # Reserve first, so existing reports are never replaced, even on invalid input.
    try:
        if not out.parent.is_dir():
            raise EvidenceError("Output parent directory must already exist.")
        if out.exists() or out.is_symlink():
            raise EvidenceError("Output already exists; choose a new file.")
        try:
            target_root = Path(os.fsdecode(git(Path(args.repo).expanduser(), "rev-parse", "--show-toplevel")).strip()).resolve(strict=True)
        except (EvidenceError, OSError, ValueError):
            target_root = None
        if target_root and out.resolve(strict=False).is_relative_to(target_root):
            raise EvidenceError("Validation report must be outside the target repository.")
        handle = out.open("x", encoding="utf-8")
    except (EvidenceError, OSError) as exc:
        print("validate_evidence: " + str(exc), file=sys.stderr)
        return 1
    try:
        counts = validate(args, errors)
    except (EvidenceError, OSError, ValueError, UnicodeError, TypeError) as exc:
        errors.append(str(exc))
    report = {"valid": not errors, "errors": errors, "counts": counts,
              "limitations": "structural and evidence location checks only; no semantic proof"}
    try:
        with handle:
            json.dump(report, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
    except OSError as exc:
        print("validate_evidence: Could not write report: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"valid": report["valid"], "errors": len(errors), "report": str(out)}))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
