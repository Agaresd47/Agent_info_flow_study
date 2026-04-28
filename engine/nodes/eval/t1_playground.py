import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def materialize_workspace(task: dict) -> dict:
    try:
        descriptor_ref = _get_descriptor_ref(task)
        descriptor_path = _resolve_input_path(descriptor_ref) if isinstance(descriptor_ref, str) else None
        descriptor = _normalize_descriptor(_load_descriptor(descriptor_path)) if descriptor_path else _normalize_descriptor(descriptor_ref)
        fixture_id = str(
            descriptor.get("fixture_id")
            or (descriptor_path.stem if descriptor_path else "inline_fixture")
            or "fixture"
        )
        root = Path(tempfile.mkdtemp(prefix=f"t1_fixture_{fixture_id}_"))
        _populate_workspace(root, descriptor, descriptor_path)
        runtime_info = _build_workspace_runtime_info(root)
        return {
            "ok": True,
            "root": str(root),
            "fixture_id": fixture_id,
            "descriptor": descriptor,
            "cleanup": lambda: shutil.rmtree(root, ignore_errors=True),
            **runtime_info,
        }
    except Exception as exc:
        return {
            "ok": False,
            "root": "",
            "fixture_id": "",
            "descriptor": None,
            "cleanup": None,
            "error": {
                "code": "materialize_failed",
                "message": str(exc),
            },
        }


def _get_descriptor_ref(task: dict) -> Any:
    for key in ("workspace_fixture", "fixture", "workspace", "playground_fixture"):
        if key in task:
            return task[key]
    raise ValueError("task must include workspace_fixture, fixture, workspace, or playground_fixture")


def _resolve_input_path(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if not candidate.exists():
        raise ValueError(f"fixture input does not exist: {candidate}")
    return candidate.resolve()


def _load_descriptor(path: Path) -> Dict[str, Any]:
    if path.is_dir():
        return {
            "fixture_id": path.name,
            "copy_from": str(path),
        }
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _normalize_descriptor(json.loads(path.read_text(encoding="utf-8")))
    if suffix in {".yaml", ".yml"}:
        return _normalize_descriptor(yaml.safe_load(path.read_text(encoding="utf-8")))
    raise ValueError(f"unsupported fixture descriptor format: {path.suffix}")


def _normalize_descriptor(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("fixture descriptor must be a mapping")
    descriptor = dict(value)
    descriptor.setdefault("fixture_id", "fixture")
    descriptor.setdefault("directories", [])
    descriptor.setdefault("files", {})
    descriptor.setdefault("roots", [])
    descriptor.setdefault("entries", [])
    return descriptor


def _populate_workspace(root: Path, descriptor: Dict[str, Any], descriptor_path: Path | None) -> None:
    copy_from = descriptor.get("copy_from") or descriptor.get("static_tree") or descriptor.get("source")
    if copy_from:
        source = _resolve_descriptor_relative_path(copy_from, descriptor_path)
        if not source.is_dir():
            raise ValueError(f"copy source must be a directory: {source}")
        _copy_tree(source, root)

    for directory in _normalize_string_list(descriptor.get("directories")):
        target_dir = _safe_join(root, directory)
        target_dir.mkdir(parents=True, exist_ok=True)

    for item in descriptor.get("roots", []):
        if not isinstance(item, dict):
            continue
        target_dir = _safe_join(root, str(item.get("path") or ""))
        target_dir.mkdir(parents=True, exist_ok=True)

    files = descriptor.get("files")
    if isinstance(files, list):
        entries: List[Tuple[str, str]] = []
        for item in files:
            if not isinstance(item, dict) or "path" not in item:
                raise ValueError("list-based files entries require path/content mappings")
            entries.append((str(item["path"]), str(item.get("content", ""))))
    elif isinstance(files, dict):
        entries = [(str(path), str(content)) for path, content in files.items()]
    else:
        raise ValueError("files must be a mapping or list")

    for relative_path, content in sorted(entries):
        target = _safe_join(root, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    for entry in descriptor.get("entries", []):
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        target = _safe_join(root, str(entry["path"]))
        kind = str(entry.get("kind") or "file")
        if kind == "directory":
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = str(entry.get("content") or entry.get("excerpt") or "")
        if not content and "size_bytes" in entry:
            content = "x" * max(0, min(int(entry.get("size_bytes") or 0), 4096))
        target.write_text(content, encoding="utf-8")


def get_workspace_root(workspace_info: dict) -> Path:
    root_value = (
        workspace_info.get("execution_root")
        or workspace_info.get("workspace_root")
        or workspace_info.get("root")
    )
    if not root_value:
        raise ValueError("workspace root is required")
    return Path(str(root_value)).resolve()


def _build_workspace_runtime_info(root: Path) -> Dict[str, Any]:
    root_resolved = root.resolve()
    return {
        "workspace_root": str(root_resolved),
        "execution_root": str(root_resolved),
        "path_policy": {
            "workspace_root": str(root_resolved),
            "allow_outside_workspace": False,
        },
        "cli_runtime": {
            "workspace_root": str(root_resolved),
            "default_cwd": ".",
            "default_timeout_seconds": 15.0,
            "builtin_only": True,
            "max_output_chars": 4000,
            "allowed_commands": ["cat", "cp", "ln", "ls", "mkdir", "mv", "pwd", "touch"],
            "allowed_options": {
                "cat": [],
                "cp": ["-r", "-R", "--recursive"],
                "ln": ["-s", "--symbolic"],
                "ls": [],
                "mkdir": ["-p", "--parents"],
                "mv": [],
                "pwd": [],
                "touch": [],
            },
            "shell_mode": "argv_only",
        },
    }


def _resolve_descriptor_relative_path(value: str, descriptor_path: Path | None) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if descriptor_path is not None:
        return (descriptor_path.parent / path).resolve()
    return (Path.cwd() / path).resolve()


def _copy_tree(source: Path, destination: Path) -> None:
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _safe_join(root: Path, relative_path: str) -> Path:
    normalized = _normalize_virtual_path(relative_path)
    candidate = (root / normalized).resolve()
    root_resolved = root.resolve()
    if os.path.commonpath([str(root_resolved), str(candidate)]) != str(root_resolved):
        raise ValueError(f"path escapes workspace root: {relative_path}")
    return candidate


def _normalize_virtual_path(value: str) -> str:
    normalized = str(value).replace("\\", "/").strip()
    if normalized in {"", "."}:
        return "."
    if ":" in normalized:
        drive, remainder = normalized.split(":", 1)
        normalized = "{0}/{1}".format(drive, remainder.lstrip("/"))
    normalized = normalized.lstrip("/")
    return normalized


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ValueError("expected a list of strings")
