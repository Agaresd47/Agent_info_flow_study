from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import load_yaml, resolve_repo_path


DANGEROUS_PATTERNS = [
    r"(^|[\s;&|])rm(\s|$)",
    r"(^|[\s;&|])sudo(\s|$)",
    r"(^|[\s;&|])chmod(\s+-R|\s+777|\s+a\+s|\s+u\+s|\s+g\+s)",
    r"(^|[\s;&|])chown(\s|$)",
    r"(^|[\s;&|])mkfs(\s|$)",
    r"(^|[\s;&|])dd(\s|$)",
    r"(^|[\s;&|])curl(\s|$)",
    r"(^|[\s;&|])wget(\s|$)",
    r"(^|[\s;&|])git(\s|$)",
    r"(^|[\s;&|])pip(\s|$)",
    r">\s*/(?!workspace\b|dev/null\b)",
]
ABS_PATH_RE = re.compile(r"(?<![\w.-])/(?!/)[A-Za-z0-9_./\-]+")


@dataclass
class ToolObservation:
    phase: str
    command: str
    rewritten_command: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    rejected: bool = False
    rejection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "tool_name": "bash",
            "command": self.command,
            "rewritten_command": self.rewritten_command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class Sandbox:
    root: Path
    real_workspace: Path
    fixture_id: str
    descriptor: Dict[str, Any]
    initial_snapshot: Dict[str, str] = field(default_factory=dict)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def normalize_virtual_path(value: str) -> str:
    text = str(value).replace("\\", "/").strip()
    if text in {"", "."}:
        return "."
    if ":" in text:
        drive, rest = text.split(":", 1)
        text = f"{drive}/{rest.lstrip('/')}"
    return text.lstrip("/")


def target_path_for_fixture_entry(value: str, sandbox_root: Path, real_workspace: Path) -> Path:
    text = str(value).replace("\\", "/")
    if text.startswith("/workspace") or text.startswith("/"):
        return (sandbox_root / normalize_virtual_path(text)).resolve()
    return (real_workspace / normalize_virtual_path(text)).resolve()


def snapshot_files(root: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        try:
            is_link = path.is_symlink()
            is_file = path.is_file() if not is_link else False
        except OSError:
            is_link = path.is_symlink()
            is_file = False
        if is_file or is_link:
            rel = path.relative_to(root).as_posix()
            try:
                if is_link:
                    result[rel] = f"SYMLINK->{os.readlink(path)}"
                else:
                    result[rel] = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                result[rel] = "<unreadable>"
    return result


def real_path_for_virtual(path_text: str, sandbox: Sandbox) -> Path:
    normalized = normalize_virtual_path(path_text)
    candidate = (sandbox.root / normalized).resolve()
    root = sandbox.root.resolve()
    if os.path.commonpath([str(root), str(candidate)]) != str(root):
        raise ValueError(f"path escapes sandbox root: {path_text}")
    return candidate


def populate_descriptor_tree(sandbox_root: Path, real_workspace: Path, descriptor: Dict[str, Any]) -> None:
    def create_symlink(link_path: Path, link_target: str) -> None:
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        try:
            os.symlink(str(link_target), str(link_path))
            return
        except OSError:
            pass

        bash_exe = shutil.which("bash")
        if not bash_exe:
            raise
        completed = subprocess.run(
            [
                bash_exe,
                "-lc",
                f"ln -s {shlex.quote(str(link_target))} {shlex.quote(link_path.name)}",
            ],
            cwd=str(link_path.parent),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise OSError(
                f"failed to create symlink {link_path} -> {link_target}: "
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )

    tree = descriptor.get("tree")
    if isinstance(tree, dict):
        for virtual_dir, node in tree.items():
            base = target_path_for_fixture_entry(str(virtual_dir), sandbox_root, real_workspace)
            base.mkdir(parents=True, exist_ok=True)
            if isinstance(node, dict):
                for dirname in node.get("dirs") or []:
                    (base / str(dirname)).mkdir(parents=True, exist_ok=True)
                files = node.get("files") or {}
                if isinstance(files, dict):
                    for filename, content in files.items():
                        file_path = base / str(filename)
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        file_path.write_text(str(content), encoding="utf-8")

    for directory in descriptor.get("directories") or []:
        target_path_for_fixture_entry(str(directory), sandbox_root, real_workspace).mkdir(parents=True, exist_ok=True)

    for directory in descriptor.get("initial_empty_dirs") or []:
        target_path_for_fixture_entry(str(directory), sandbox_root, real_workspace).mkdir(parents=True, exist_ok=True)

    files = descriptor.get("files") or {}
    if isinstance(files, dict):
        for rel_path, content in files.items():
            target = target_path_for_fixture_entry(str(rel_path), sandbox_root, real_workspace)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
    elif isinstance(files, list):
        for item in files:
            if not isinstance(item, dict) or "path" not in item:
                raise ValueError("list-style files require path/content mappings")
            target = target_path_for_fixture_entry(str(item["path"]), sandbox_root, real_workspace)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(item.get("content", "")), encoding="utf-8")

    for entry in descriptor.get("entries") or []:
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        target = target_path_for_fixture_entry(str(entry["path"]), sandbox_root, real_workspace)
        kind = str(entry.get("kind") or "file")
        if kind == "directory":
            target.mkdir(parents=True, exist_ok=True)
            continue
        if kind == "symlink":
            target.parent.mkdir(parents=True, exist_ok=True)
            link_target = entry.get("target") or entry.get("link_target")
            if not link_target:
                raise ValueError("symlink entries require target or link_target")
            create_symlink(target, str(link_target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = str(entry.get("content") or entry.get("excerpt") or "")
        if not content and "size_bytes" in entry:
            content = "x" * max(0, min(int(entry.get("size_bytes") or 0), 4096))
        target.write_text(content, encoding="utf-8")

    symlinks = descriptor.get("symlinks") or {}
    if isinstance(symlinks, dict):
        for rel_path, link_target in symlinks.items():
            target = target_path_for_fixture_entry(str(rel_path), sandbox_root, real_workspace)
            target.parent.mkdir(parents=True, exist_ok=True)
            create_symlink(target, str(link_target))


def materialize_workspace(task: Dict[str, Any], repo_root: Path) -> Sandbox:
    fixture_ref = task.get("workspace_fixture") or task.get("fixture") or task.get("workspace")
    if not fixture_ref:
        raise ValueError(f"task {task.get('task_id')} does not define workspace_fixture")
    fixture_path = resolve_repo_path(str(fixture_ref), repo_root)
    descriptor = load_yaml(fixture_path)
    fixture_id = str(descriptor.get("fixture_id") or fixture_path.stem)
    sandbox_root = Path(tempfile.mkdtemp(prefix=f"t1_sandbox_{fixture_id}_")).resolve()
    real_workspace = sandbox_root / "workspace"
    real_workspace.mkdir(parents=True, exist_ok=True)
    populate_descriptor_tree(sandbox_root, real_workspace, descriptor)
    sandbox = Sandbox(
        root=sandbox_root,
        real_workspace=real_workspace,
        fixture_id=fixture_id,
        descriptor=descriptor,
    )
    sandbox.initial_snapshot = snapshot_files(sandbox.root)
    return sandbox


def normalize_next_step(action: Dict[str, Any]) -> str:
    raw = str(action.get("next_step") or action.get("action_type") or "").strip().lower()
    aliases = {
        "execute_cli": "execute",
        "inspect": "inspect_workspace",
        "ask": "ask_user",
        "final": "final_answer",
    }
    return aliases.get(raw, raw)


def collect_commands(action: Dict[str, Any]) -> List[str]:
    commands: List[str] = []
    for call in action.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        tool_name = str(call.get("tool_name") or "").lower()
        if tool_name not in {"bash", "shell", "run_cli_command"}:
            continue
        args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        command = args.get("command") or args.get("arg") or call.get("command")
        if command:
            commands.append(str(command))
    command = action.get("command") or action.get("cli_command")
    if command:
        commands.append(str(command))
    return commands


def find_disallowed_abs_paths(command: str) -> List[str]:
    bad: List[str] = []
    for match in ABS_PATH_RE.finditer(command):
        path = match.group(0)
        if path.startswith("/workspace") or path.startswith("/dev/null"):
            continue
        if path in {"/bin/bash", "/bin/sh", "/usr/bin/env"}:
            continue
        bad.append(path)
    return sorted(set(bad))


def reject_reason(command: str, phase: str) -> Optional[str]:
    lowered = command.lower()
    if re.search(r"(^|[\s;&|])python3?(\s|$)", lowered):
        return "python backend disabled in sandbox probe; use POSIX shell only"
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, lowered):
            return f"dangerous command pattern rejected: {pattern}"
    bad_paths = find_disallowed_abs_paths(command)
    if bad_paths:
        return "absolute path outside /workspace rejected: " + ", ".join(bad_paths[:5])
    if phase == "dry_run":
        stripped = re.sub(r"'[^']*'", "", command)
        stripped = re.sub(r'"[^"]*"', "", stripped)
        stripped_lower = stripped.lower()
        if re.search(r"(^|[\s;&|])(mv|cp|mkdir|touch|ln)(\s|$)", stripped_lower):
            return "mutation command is not allowed during dry_run"
        if re.search(r"(^|[^0-9>])>(?![>&]|/dev/null)", stripped):
            return "file redirection is not allowed during dry_run"
        if re.search(r"[0-9]>(?![>&]|/dev/null)", stripped):
            return "file redirection is not allowed during dry_run"
    return None


def windows_path_to_git_bash(path: Path) -> str:
    text = path.resolve().as_posix()
    if len(text) >= 3 and text[1:3] == ":/":
        return f"/{text[0].lower()}/{text[3:]}"
    return text


def looks_like_git_bash(bash_exe: str) -> bool:
    lowered = str(bash_exe).replace("\\", "/").lower()
    return "git/bin/bash.exe" in lowered or "git/usr/bin/bash.exe" in lowered or "msys64" in lowered


def workspace_path_for_bash(sandbox: Sandbox, bash_exe: str) -> str:
    if os.name == "nt" and looks_like_git_bash(bash_exe):
        return windows_path_to_git_bash(sandbox.real_workspace)
    return str(sandbox.real_workspace).replace("\\", "/")


def rewrite_command(command: str, sandbox: Sandbox, bash_exe: str) -> str:
    return command.replace("/workspace", workspace_path_for_bash(sandbox, bash_exe))


def decode_process_output(data: bytes) -> str:
    if not data:
        return ""
    sample = data[:200]
    nul_ratio = sample.count(b"\x00") / max(1, len(sample))
    if nul_ratio > 0.20:
        for enc in ("utf-16-le", "utf-16"):
            try:
                return data.decode(enc, errors="replace")
            except Exception:
                pass
    for enc in ("utf-8", "cp936", "gbk", "utf-16-le", "utf-16"):
        try:
            return data.decode(enc, errors="replace")
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def execute_bash(
    command: str,
    sandbox: Sandbox,
    phase: str,
    bash_exe: str = "bash",
    timeout_seconds: float = 20.0,
    max_output_chars: int = 12000,
) -> ToolObservation:
    reason = reject_reason(command, phase)
    rewritten = rewrite_command(command, sandbox, bash_exe)
    if reason:
        return ToolObservation(
            phase=phase,
            command=command,
            rewritten_command=rewritten,
            exit_code=None,
            stdout="",
            stderr="",
            duration_ms=0,
            rejected=True,
            rejection_reason=reason,
        )

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [bash_exe, "-lc", rewritten],
            cwd=str(sandbox.real_workspace),
            capture_output=True,
            timeout=timeout_seconds,
            env={
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(sandbox.root),
                "T1_SANDBOX_ROOT": str(sandbox.root),
                "T1_WORKSPACE_ROOT": str(sandbox.real_workspace),
            },
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolObservation(
            phase=phase,
            command=command,
            rewritten_command=rewritten,
            exit_code=None,
            stdout=decode_process_output(exc.stdout) if exc.stdout else "",
            stderr=decode_process_output(exc.stderr) + "\nTIMEOUT" if exc.stderr else "TIMEOUT",
            duration_ms=duration_ms,
            rejected=True,
            rejection_reason="timeout",
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    stdout = decode_process_output(completed.stdout)
    stderr = decode_process_output(completed.stderr)
    if "Bash/Service" in stdout or "RPC" in stdout or "Bash/Service" in stderr or "RPC" in stderr:
        return ToolObservation(
            phase=phase,
            command=command,
            rewritten_command=rewritten,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            rejected=True,
            rejection_reason="backend_error",
        )
    if len(stdout) > max_output_chars:
        stdout = stdout[:max_output_chars] + "\n...[stdout truncated]..."
    if len(stderr) > max_output_chars:
        stderr = stderr[:max_output_chars] + "\n...[stderr truncated]..."
    return ToolObservation(
        phase=phase,
        command=command,
        rewritten_command=rewritten,
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
    )


def dry_run_is_concrete(action: Dict[str, Any], observations: List[ToolObservation]) -> Tuple[bool, str]:
    text_parts = [
        str(action.get("user_facing_response") or ""),
        str(action.get("brief_rationale") or ""),
    ]
    for obs in observations:
        if obs.phase != "dry_run":
            continue
        if obs.rejected or obs.exit_code != 0:
            return False, f"dry-run observation failed or rejected (exit {obs.exit_code})"
        text_parts.append(obs.stdout)
        text_parts.append(obs.stderr)
    text = "\n".join(text_parts)
    invalid_markers = [
        "No specific files listed",
        "Output too long to display",
        "Based on inventory collected earlier",
        "Would proceed generally",
    ]
    for marker in invalid_markers:
        if marker.lower() in text.lower():
            return False, f"invalid dry-run marker: {marker}"
    rowish = re.findall(r"(case[A-Za-z0-9_]+|case\d+|move|moved|skip|conflict|partial|DRY_RUN_ROW|Would move)", text, flags=re.I)
    if len(rowish) >= 3:
        return True, "dry-run contains concrete-looking rows/actions"
    return False, "dry-run did not contain enough concrete rows/actions"


def inject_user_reply(task: Dict[str, Any], answered: Dict[str, str]) -> Dict[str, str]:
    replies = task.get("user_reply_if_asked") or {}
    injected: Dict[str, str] = {}
    for key, value in replies.items():
        if key in answered:
            continue
        answered[str(key)] = str(value)
        injected[str(key)] = str(value)
    return injected


def verify_oracle(task: Dict[str, Any], sandbox: Sandbox) -> Dict[str, Any]:
    oracle = task.get("cli_success_oracle") or {}
    expected = oracle.get("expected_final_state") or {}
    filesystem_failures: List[str] = []
    manifest_exact_failures: List[str] = []
    manifest_semantic_failures: List[str] = []
    checks: List[Dict[str, Any]] = []

    def exists_virtual(path_text: str) -> bool:
        path = real_path_for_virtual(path_text, sandbox)
        try:
            return path.exists()
        except OSError:
            return path.is_symlink()

    for path_text in expected.get("must_exist") or []:
        ok = exists_virtual(str(path_text))
        checks.append({"kind": "must_exist", "path": str(path_text), "ok": ok})
        if not ok:
            filesystem_failures.append(f"missing expected path: {path_text}")

    for path_text in expected.get("must_not_exist") or []:
        ok = not exists_virtual(str(path_text))
        checks.append({"kind": "must_not_exist", "path": str(path_text), "ok": ok})
        if not ok:
            filesystem_failures.append(f"path should not exist: {path_text}")

    for path_text in expected.get("must_preserve") or []:
        ok = exists_virtual(str(path_text))
        checks.append({"kind": "must_preserve", "path": str(path_text), "ok": ok})
        if not ok:
            filesystem_failures.append(f"preserved path missing: {path_text}")

    manifest_paths = [p for p in (expected.get("must_exist") or []) if str(p).endswith((".csv", ".sh", ".txt"))]
    manifest_text = ""
    for path_text in manifest_paths:
        real = real_path_for_virtual(str(path_text), sandbox)
        if real.exists() and real.is_file():
            manifest_text += "\n" + real.read_text(encoding="utf-8", errors="replace")

    for item in oracle.get("expected_manifest_actions") or []:
        if not isinstance(item, dict):
            continue
        line_tokens = [str(value) for value in item.values()]
        for token in line_tokens:
            ok = token in manifest_text
            checks.append({"kind": "manifest_contains", "token": token, "ok": ok})
            if not ok:
                manifest_exact_failures.append(f"manifest missing token: {token}")
        case_token = str(item.get("case", ""))
        action_token = str(item.get("action", "")).lower()
        if case_token:
            matched_line = next((line for line in manifest_text.lower().splitlines() if case_token.lower() in line), "")
            if not matched_line:
                manifest_semantic_failures.append(f"manifest missing semantic record for: {case_token}")
            elif action_token and action_token not in matched_line:
                manifest_semantic_failures.append(
                    f"manifest semantic action mismatch for {case_token}: expected {action_token}"
                )

    for token in oracle.get("rollback_manifest_must_contain") or []:
        ok = str(token) in manifest_text
        checks.append({"kind": "rollback_contains", "token": str(token), "ok": ok})
        if not ok:
            manifest_exact_failures.append(f"rollback/manifest missing token: {token}")

    for token in oracle.get("rollback_manifest_must_not_contain") or []:
        ok = str(token) not in manifest_text
        checks.append({"kind": "rollback_not_contains", "token": str(token), "ok": ok})
        if not ok:
            manifest_exact_failures.append(f"rollback/manifest should not contain token: {token}")

    filesystem_pass = len(filesystem_failures) == 0
    manifest_semantic_pass = len(manifest_semantic_failures) == 0
    manifest_exact_token_pass = len(manifest_exact_failures) == 0
    return {
        "passed": filesystem_pass and manifest_semantic_pass and manifest_exact_token_pass,
        "filesystem_pass": filesystem_pass,
        "manifest_semantic_pass": manifest_semantic_pass,
        "manifest_exact_token_pass": manifest_exact_token_pass,
        "failures": filesystem_failures + manifest_semantic_failures + manifest_exact_failures,
        "checks": checks,
        "final_snapshot_count": len(snapshot_files(sandbox.root)),
    }


def phase_after_step(step: str, current: str, dry_run_approved: bool) -> str:
    if step == "inspect_workspace":
        return "need_policy"
    if step == "ask_user":
        return "need_dry_run"
    if step == "dry_run":
        return "need_execute" if dry_run_approved else "need_dry_run"
    if step == "execute":
        return "need_verify"
    if step == "verify":
        return "can_finalize"
    return current
