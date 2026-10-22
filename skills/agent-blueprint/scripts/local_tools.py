#!/usr/bin/env python3
"""Use the original engine's deterministic rules and static scanner locally.

Python 3.10+ standard library only. No API credentials, model calls, package
installation, or network access. Output files must be new; their parent
directory must already exist. Features may be a JSON file path or inline JSON.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
VALUES = {"yes", "no", "later", "unknown"}


def load_engine(engine: Path) -> tuple[Path, Any]:
    root = engine.expanduser().resolve(strict=True)
    for relative in ("BLUEPRINT.md", "blueprint/__init__.py", "blueprint/knowledge/__init__.py",
                     "blueprint/rules.py", "blueprint/scanner.py"):
        if not (root / relative).is_file():
            raise ValueError(f"Not an Agent Blueprint engine root; missing {relative}: {root}")
    sys.path.insert(0, str(root))
    knowledge = importlib.import_module("blueprint.knowledge")
    if not Path(knowledge.__file__).resolve().is_relative_to(root):
        raise ValueError("Another blueprint package is already loaded; run this helper in a fresh Python process.")
    return root, knowledge


def read_features(value: str) -> Any:
    if value.lstrip().startswith("{"):
        return json.loads(value)
    path = Path(value).expanduser()
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_features(raw: Any, knowledge: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        raise ValueError("Features JSON must be an object keyed by original feature IDs.")
    known = knowledge.FEATURE_BY_ID
    unknown_ids = sorted(set(raw) - set(known))
    if unknown_ids:
        raise ValueError("Unknown feature IDs: " + ", ".join(unknown_ids))
    normalized: dict[str, dict[str, str]] = {}
    for feature_id in known:
        item = raw.get(feature_id)
        if feature_id not in raw:
            normalized[feature_id] = {"value": "unknown", "evidence": "当前 AI 未提供判断，保留待确认。"}
            continue
        if not isinstance(item, dict):
            raise ValueError(f"{feature_id}: expected an object with value and evidence.")
        value = item.get("value")
        if not isinstance(value, str) or value not in VALUES:
            raise ValueError(f"{feature_id}: value must be yes, no, later, or unknown.")
        evidence = item.get("evidence", "")
        if not isinstance(evidence, str):
            raise ValueError(f"{feature_id}: evidence must be a string.")
        evidence = evidence.strip()
        if value != "unknown" and not evidence:
            raise ValueError(f"{feature_id}: yes/no/later requires nonempty evidence from the input.")
        normalized[feature_id] = {"value": value, "evidence": evidence or "当前 AI 标记为待确认。"}
    return normalized


def select(args: argparse.Namespace) -> dict[str, Any]:
    root, knowledge = load_engine(args.engine)
    features = normalize_features(read_features(args.features), knowledge)
    rules = importlib.import_module("blueprint.rules")
    return {
        "method": "当前 AI 特征判断 + 原引擎固定规则；未运行模型管线。",
        "model_pipeline_run": False,
        "engine": str(root),
        "features": features,
        "components": [decision.to_dict() for decision in rules.select_components(features)],
    }


def scan(args: argparse.Namespace) -> dict[str, Any]:
    root, _knowledge = load_engine(args.engine)
    project = args.project.expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError(f"Project is not a directory: {project}")
    scanner = importlib.import_module("blueprint.scanner")
    return {
        "method": "原引擎本地静态扫描；未运行目标项目、未调用模型，信号覆盖不等同功能完成或业务验收。",
        "static_only": True,
        "model_pipeline_run": False,
        "engine": str(root),
        "inventory": scanner.scan_project(project).to_dict(),
    }


def write_new_json(path: Path, data: dict[str, Any]) -> Path:
    requested = path.expanduser()
    if requested.exists() or requested.is_symlink():
        raise FileExistsError(f"Output already exists; choose a new file: {requested.absolute()}")
    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError(f"Output parent is not a directory: {parent}")
    output = parent / requested.name
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(text)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    select_parser = subparsers.add_parser("select", help="Apply fixed component rules to current-AI feature judgments.")
    select_parser.add_argument("--engine", required=True, type=Path)
    select_parser.add_argument("--features", required=True, help="JSON file path or inline JSON object.")
    select_parser.add_argument("--out", required=True, type=Path)
    select_parser.set_defaults(handler=select)
    scan_parser = subparsers.add_parser("scan", help="Save the complete original static inventory.")
    scan_parser.add_argument("--engine", required=True, type=Path)
    scan_parser.add_argument("--project", required=True, type=Path)
    scan_parser.add_argument("--out", required=True, type=Path)
    scan_parser.set_defaults(handler=scan)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required.")
    try:
        if args.out.expanduser().exists() or args.out.expanduser().is_symlink():
            raise FileExistsError(f"Output already exists; choose a new file: {args.out.expanduser().absolute()}")
        result = args.handler(args)
        output = write_new_json(args.out, result)
    except (OSError, ValueError, ImportError, AttributeError) as exc:
        print(f"local_tools: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
