import fnmatch
import os
import shlex
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .t1_playground import get_workspace_root


class WorkspaceToolExecutor:
    def __init__(self, workspace_info: dict):
        self.workspace_info = workspace_info or {}
        self.root = get_workspace_root(self.workspace_info)

    def _resolve_path(self, raw_path: Any, require_file: bool = False) -> Path:
        candidate = self._resolve_workspace_path(raw_path, cwd=self.root, require_exists=True)
        if require_file and not candidate.is_file():
            raise ValueError(f"path is not a file: {raw_path}")
        return candidate

    def _resolve_workspace_path(
        self,
        raw_path: Any,
        *,
        cwd: Path,
        require_exists: bool,
    ) -> Path:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("path must be a non-empty string")
        normalized = self._normalize_virtual_path(raw_path)
        if normalized == ".":
            candidate = cwd.resolve()
        elif str(raw_path).replace("\\", "/").startswith("/"):
            # Task prompts use virtual absolute paths; remap them into the fixture root.
            candidate = (self.root / normalized).resolve()
        else:
            candidate = (cwd / normalized).resolve()
        if os.path.commonpath([str(self.root), str(candidate)]) != str(self.root):
            raise ValueError(f"path is outside workspace root: {raw_path}")
        if require_exists and not candidate.exists():
            raise ValueError(f"path does not exist: {raw_path}")
        return candidate

    def _normalize_virtual_path(self, raw_path: str) -> str:
        normalized = raw_path.replace("\\", "/").strip()
        if normalized in {"", ".", "./"}:
            return "."
        if ":" in normalized:
            drive, remainder = normalized.split(":", 1)
            normalized = "{0}/{1}".format(drive, remainder.lstrip("/"))
        return normalized.lstrip("/")

    def _relative_path(self, path: Path) -> str:
        resolved = path.resolve()
        if resolved == self.root:
            return "."
        return resolved.relative_to(self.root).as_posix()

    def _relative_file_set(self, root: Path) -> set[str]:
        return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}

    def _basename_index(self, paths: Iterable[str]) -> Dict[str, List[str]]:
        index: Dict[str, List[str]] = {}
        for path in sorted(paths):
            basename = Path(path).name
            index.setdefault(basename, []).append(path)
        return index

    def _error(self, code: str, message: str, tool_name: str | None = None) -> dict:
        payload = {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if tool_name is not None:
            payload["tool"] = tool_name
        return payload


class ReadOnlyToolExecutor(WorkspaceToolExecutor):
    def run_tool(self, tool_name: str, arguments: dict) -> dict:
        handler = self._tool_map().get(str(tool_name))
        if handler is None:
            return self._error("unknown_tool", f"Unknown tool: {tool_name}")
        try:
            if not isinstance(arguments, dict):
                raise ValueError("arguments must be a mapping")
            return {
                "ok": True,
                "tool": tool_name,
                "result": handler(arguments),
            }
        except (ValueError, KeyError, TypeError) as exc:
            return self._error("invalid_arguments", str(exc), tool_name=tool_name)
        except OSError as exc:
            return self._error("io_error", str(exc), tool_name=tool_name)

    def _tool_map(self) -> Dict[str, Any]:
        return {
            "list_files": self._tool_list_files,
            "read_file_excerpt": self._tool_read_file_excerpt,
            "summarize_directory": self._tool_summarize_directory,
            "detect_conflicts": self._tool_detect_conflicts,
            "count_matched_files": self._tool_count_matched_files,
        }

    def _tool_list_files(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        root = self._resolve_path(arguments.get("path", "."))
        recursive = bool(arguments.get("recursive", False))
        max_entries = int(arguments.get("max_entries", 200))
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        iterator = root.rglob("*") if recursive else root.iterdir()
        entries = []
        for item in sorted(iterator):
            if len(entries) >= max_entries:
                break
            entries.append(
                {
                    "path": self._relative_path(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                }
            )
        return {
            "path": self._relative_path(root),
            "recursive": recursive,
            "entries": entries,
            "truncated": len(entries) == max_entries,
        }

    def _tool_read_file_excerpt(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve_path(arguments["path"], require_file=True)
        start_line = int(arguments.get("start_line", 1))
        max_lines = int(arguments.get("max_lines", 20))
        if start_line <= 0 or max_lines <= 0:
            raise ValueError("start_line and max_lines must be positive")
        lines = path.read_text(encoding="utf-8").splitlines()
        start_index = start_line - 1
        excerpt = lines[start_index : start_index + max_lines]
        return {
            "path": self._relative_path(path),
            "start_line": start_line,
            "end_line": start_line + len(excerpt) - 1 if excerpt else start_line - 1,
            "line_count": len(excerpt),
            "excerpt": "\n".join(excerpt),
        }

    def _tool_summarize_directory(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        root = self._resolve_path(arguments.get("path", "."))
        max_entries = int(arguments.get("max_entries", 20))
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        file_count = 0
        directory_count = 0
        total_bytes = 0
        extension_counts: Dict[str, int] = {}
        entries = []
        total_entries = 0
        for item in sorted(root.rglob("*")):
            total_entries += 1
            if item.is_dir():
                directory_count += 1
            else:
                file_count += 1
                total_bytes += item.stat().st_size
                suffix = item.suffix.lower() or "<none>"
                extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            if len(entries) < max_entries:
                entries.append(self._relative_path(item))
        return {
            "path": self._relative_path(root),
            "file_count": file_count,
            "directory_count": directory_count,
            "total_bytes": total_bytes,
            "extension_counts": dict(sorted(extension_counts.items())),
            "sample_entries": entries,
            "truncated": total_entries > max_entries,
        }

    def _tool_detect_conflicts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        source = self._resolve_path(arguments.get("source") or arguments.get("source_root"))
        target = self._resolve_path(arguments.get("target") or arguments.get("destination_root"))
        source_files = self._relative_file_set(source)
        target_files = self._relative_file_set(target)
        same_relative_paths = sorted(source_files & target_files)

        source_basenames = self._basename_index(source_files)
        target_basenames = self._basename_index(target_files)
        basename_conflicts = []
        for basename in sorted(source_basenames.keys() & target_basenames.keys()):
            if set(source_basenames[basename]) != set(target_basenames[basename]):
                basename_conflicts.append(
                    {
                        "basename": basename,
                        "source_paths": source_basenames[basename],
                        "target_paths": target_basenames[basename],
                    }
                )
        return {
            "source": self._relative_path(source),
            "target": self._relative_path(target),
            "same_relative_paths": same_relative_paths,
            "same_relative_path_count": len(same_relative_paths),
            "basename_conflicts": basename_conflicts,
            "basename_conflict_count": len(basename_conflicts),
        }

    def _tool_count_matched_files(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        root = self._resolve_path(arguments.get("root", "."))
        rule = arguments.get("rule")
        if not isinstance(rule, dict) or not rule:
            raise ValueError("rule must be a non-empty mapping")
        matches = []
        for item in sorted(root.rglob("*")):
            if item.is_file() and self._matches_rule(item, rule):
                matches.append(self._relative_path(item))
        return {
            "root": self._relative_path(root),
            "rule": rule,
            "count": len(matches),
            "matches": matches,
        }

    def _matches_rule(self, path: Path, rule: Dict[str, Any]) -> bool:
        relative = self._relative_path(path)
        name = path.name
        suffix = path.suffix.lower()
        if "glob" in rule and not fnmatch.fnmatch(relative, str(rule["glob"])):
            return False
        if "suffix" in rule and not name.endswith(str(rule["suffix"])):
            return False
        if "contains" in rule and str(rule["contains"]) not in name:
            return False
        if "extension" in rule and suffix != str(rule["extension"]).lower():
            return False
        return True


class CliToolExecutor(ReadOnlyToolExecutor):
    DEFAULT_ALLOWED_COMMANDS = ("cat", "cp", "ln", "ls", "mkdir", "mv", "pwd", "touch")
    DEFAULT_ALLOWED_OPTIONS = {
        "cat": frozenset(),
        "cp": frozenset({"-r", "-R", "--recursive"}),
        "ln": frozenset({"-s", "--symbolic"}),
        "ls": frozenset(),
        "mkdir": frozenset({"-p", "--parents"}),
        "mv": frozenset(),
        "pwd": frozenset(),
        "touch": frozenset(),
    }
    SHELL_META_TOKENS = ("&&", "||", "|", ";", ">", "<", "`", "$(")
    WRITE_COMMANDS = {"cp", "ln", "mkdir", "mv", "touch"}

    def __init__(
        self,
        workspace_info: dict,
        *,
        allowed_commands: Iterable[str] | None = None,
        default_timeout_seconds: float | None = None,
    ):
        super().__init__(workspace_info)
        runtime = workspace_info.get("cli_runtime") if isinstance(workspace_info, dict) else {}
        runtime_allowed = runtime.get("allowed_commands") if isinstance(runtime, dict) else None
        self.allowed_commands = {
            str(command).lower()
            for command in (
                allowed_commands
                or runtime_allowed
                or self.DEFAULT_ALLOWED_COMMANDS
            )
        }
        runtime_options = runtime.get("allowed_options") if isinstance(runtime, dict) else None
        self.allowed_options = self._normalize_allowed_options(runtime_options)
        timeout_value = default_timeout_seconds
        if timeout_value is None and isinstance(runtime, dict):
            timeout_value = runtime.get("default_timeout_seconds")
        self.default_timeout_seconds = float(timeout_value or 15.0)
        self.builtin_only = bool(runtime.get("builtin_only", True)) if isinstance(runtime, dict) else True
        max_output_chars = runtime.get("max_output_chars") if isinstance(runtime, dict) else None
        self.max_output_chars = max(1, int(max_output_chars or 4000))
        self._execution_events: List[Dict[str, Any]] = []
        self._execution_results: List[Dict[str, Any]] = []
        self._event_counter = 0

    def _tool_map(self) -> Dict[str, Any]:
        tool_map = super()._tool_map()
        tool_map["run_cli_command"] = self._tool_run_cli_command
        return tool_map

    def execute_cli_command(
        self,
        command: str | List[str],
        *,
        cwd: str = ".",
        timeout_seconds: float | None = None,
        env: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        cwd_path = self._resolve_path(cwd)
        if not cwd_path.is_dir():
            raise ValueError(f"cwd is not a directory: {cwd}")
        argv = self._normalize_command(command)
        plan = self._build_command_plan(argv, cwd_path)
        self._record_event(
            "command_started",
            command_id=plan["command_id"],
            raw_command=plan["raw_argv"],
            mapped_command=plan["mapped_argv"],
            cwd=self._relative_path(cwd_path),
            writes_attempted=plan["writes_attempted"],
            write_paths=plan["write_paths"],
        )
        started_at = time.monotonic()
        timeout_value = float(timeout_seconds or self.default_timeout_seconds)
        del timeout_value, env
        completed = self._execute_builtin_command(plan["executable"], plan["mapped_argv"], cwd_path)
        if completed is None:
            raise ValueError(f"builtin handler is not available for command: {plan['executable']}")
        duration_ms = int((time.monotonic() - started_at) * 1000)
        result = {
            "command_id": plan["command_id"],
            "status": "completed",
            "command": plan["raw_argv"],
            "mapped_command": plan["mapped_argv"],
            "cwd": self._relative_path(cwd_path),
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "duration_ms": duration_ms,
            "writes_attempted": plan["writes_attempted"],
            "write_paths": plan["write_paths"],
            "writes_outside_fixture_root": 0,
            "backend": completed.get("backend", "builtin") if isinstance(completed, dict) else "builtin",
            "error": None,
        }
        result["exit_code"] = int(completed["returncode"])
        result["stdout"] = str(completed.get("stdout", ""))
        result["stderr"] = str(completed.get("stderr", ""))
        self._apply_output_limits(result)
        self._execution_results.append(result)
        self._record_event("command_completed", **dict(result))
        return result

    def get_execution_events(self) -> List[Dict[str, Any]]:
        return [dict(event) for event in self._execution_events]

    def get_execution_summary(self) -> Dict[str, Any]:
        return {
            "commands_run": len(self._execution_results),
            "completed_commands": sum(1 for result in self._execution_results if result["status"] == "completed"),
            "rejected_commands": sum(1 for result in self._execution_results if result["status"] == "rejected"),
            "timed_out_commands": sum(1 for result in self._execution_results if result["status"] == "timeout"),
            "writes_attempted": sum(int(result["writes_attempted"]) for result in self._execution_results),
            "writes_outside_fixture_root": sum(
                int(result["writes_outside_fixture_root"]) for result in self._execution_results
            ),
            "exit_codes": [
                result["exit_code"]
                for result in self._execution_results
                if result["exit_code"] is not None
            ],
            "events": self.get_execution_events(),
        }

    def _tool_run_cli_command(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if "command" not in arguments:
            raise ValueError("command is required")
        try:
            result = self.execute_cli_command(
                arguments["command"],
                cwd=str(arguments.get("cwd") or "."),
                timeout_seconds=(
                    float(arguments["timeout_seconds"])
                    if "timeout_seconds" in arguments and arguments["timeout_seconds"] is not None
                    else None
                ),
                env=arguments.get("env"),
            )
        except (ValueError, OSError) as exc:
            command_value = arguments["command"]
            cwd_value = str(arguments.get("cwd") or ".")
            result = self._build_rejected_result(command_value, cwd_value, exc)
        return {
            **result,
            "execution_summary": self.get_execution_summary(),
        }

    def _normalize_command(self, command: str | List[str]) -> List[str]:
        if isinstance(command, str):
            for token in self.SHELL_META_TOKENS:
                if token in command:
                    raise ValueError("shell metacharacters are not supported in cli_test commands")
            argv = shlex.split(command, posix=True)
        elif isinstance(command, list) and all(isinstance(item, str) for item in command):
            argv = list(command)
        else:
            raise ValueError("command must be a shell-free string or list of strings")
        if not argv:
            raise ValueError("command must not be empty")
        return argv

    def _build_command_plan(self, argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        executable = Path(argv[0]).name.lower()
        if executable not in self.allowed_commands:
            raise ValueError(f"command is not allowed: {argv[0]}")
        self._validate_command_options(executable, argv)
        mapped_argv = list(argv)
        path_positions = self._path_positions_for_command(executable, argv)
        write_positions = self._write_positions_for_command(executable, path_positions)
        write_paths: List[str] = []
        for position in path_positions:
            raw_path = argv[position]
            resolved = self._resolve_workspace_path(
                raw_path,
                cwd=cwd_path,
                require_exists=position not in write_positions,
            )
            mapped_argv[position] = str(resolved)
            if position in write_positions:
                write_paths.append(self._relative_path(resolved))
        return {
            "command_id": self._next_command_id(),
            "raw_argv": list(argv),
            "mapped_argv": mapped_argv,
            "executable": executable,
            "writes_attempted": len(write_positions),
            "write_paths": write_paths,
        }

    def _path_positions_for_command(self, executable: str, argv: List[str]) -> List[int]:
        positions = self._non_option_positions(argv)
        if executable == "pwd":
            if len(argv) != 1:
                raise ValueError("pwd does not accept path arguments in cli_test")
            return []
        if executable in {"ls", "cat", "mkdir", "touch"}:
            if executable == "cat" and not positions:
                raise ValueError("cat requires at least one file path")
            return positions
        if executable in {"cp", "mv", "ln"}:
            if len(positions) < 2:
                raise ValueError(f"{executable} requires at least one source and one destination")
            return positions
        raise ValueError(f"unsupported command: {executable}")

    def _write_positions_for_command(self, executable: str, path_positions: List[int]) -> set[int]:
        if executable not in self.WRITE_COMMANDS:
            return set()
        if executable in {"cp", "mv", "ln"}:
            return {path_positions[-1]}
        return set(path_positions)

    def _non_option_positions(self, argv: List[str]) -> List[int]:
        positions: List[int] = []
        literal_mode = False
        for index, argument in enumerate(argv[1:], start=1):
            if literal_mode:
                positions.append(index)
                continue
            if argument == "--":
                literal_mode = True
                continue
            if argument.startswith("-") and argument != "-":
                continue
            positions.append(index)
        return positions

    def _build_command_env(self, extra_env: Dict[str, str] | None) -> Dict[str, str]:
        env = os.environ.copy()
        env["T1_WORKSPACE_ROOT"] = str(self.root)
        if extra_env:
            for key, value in extra_env.items():
                env[str(key)] = str(value)
        return env

    def _execute_builtin_command(
        self,
        executable: str,
        mapped_argv: List[str],
        cwd_path: Path,
    ) -> Dict[str, Any] | None:
        handlers = {
            "pwd": self._builtin_pwd,
            "ls": self._builtin_ls,
            "cat": self._builtin_cat,
            "mkdir": self._builtin_mkdir,
            "touch": self._builtin_touch,
            "cp": self._builtin_cp,
            "mv": self._builtin_mv,
            "ln": self._builtin_ln,
        }
        handler = handlers.get(executable)
        if handler is None:
            return None
        return handler(mapped_argv, cwd_path)

    def _builtin_pwd(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        return {"returncode": 0, "stdout": f"{cwd_path}\n", "stderr": "", "backend": "builtin"}

    def _builtin_ls(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        targets = self._builtin_non_option_args(mapped_argv) or [str(cwd_path)]
        output: List[str] = []
        for target in targets:
            path = Path(target)
            if path.is_dir():
                output.extend(sorted(item.name for item in path.iterdir()))
            else:
                output.append(path.name)
        return {"returncode": 0, "stdout": "\n".join(output) + ("\n" if output else ""), "stderr": "", "backend": "builtin"}

    def _builtin_cat(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        del cwd_path
        chunks = [Path(target).read_text(encoding="utf-8") for target in self._builtin_non_option_args(mapped_argv)]
        return {"returncode": 0, "stdout": "".join(chunks), "stderr": "", "backend": "builtin"}

    def _builtin_mkdir(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        del cwd_path
        parents = any(option in {"-p", "--parents"} for option in mapped_argv[1:])
        for target in self._builtin_non_option_args(mapped_argv):
            Path(target).mkdir(parents=parents, exist_ok=parents)
        return {"returncode": 0, "stdout": "", "stderr": "", "backend": "builtin"}

    def _builtin_touch(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        del cwd_path
        for target in self._builtin_non_option_args(mapped_argv):
            Path(target).touch(exist_ok=True)
        return {"returncode": 0, "stdout": "", "stderr": "", "backend": "builtin"}

    def _builtin_cp(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        del cwd_path
        recursive = any(option in {"-r", "-R", "--recursive"} for option in mapped_argv[1:])
        operands = [Path(target) for target in self._builtin_non_option_args(mapped_argv)]
        destination = operands[-1]
        sources = operands[:-1]
        if len(sources) > 1 and not destination.is_dir():
            raise ValueError("cp with multiple sources requires a destination directory")
        for source in sources:
            target = destination / source.name if destination.is_dir() else destination
            if source.is_dir():
                if not recursive:
                    raise ValueError("cp requires -r to copy directories")
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        return {"returncode": 0, "stdout": "", "stderr": "", "backend": "builtin"}

    def _builtin_mv(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        del cwd_path
        operands = [Path(target) for target in self._builtin_non_option_args(mapped_argv)]
        destination = operands[-1]
        sources = operands[:-1]
        if len(sources) > 1 and not destination.is_dir():
            raise ValueError("mv with multiple sources requires a destination directory")
        for source in sources:
            target = destination / source.name if destination.is_dir() else destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
        return {"returncode": 0, "stdout": "", "stderr": "", "backend": "builtin"}

    def _builtin_ln(self, mapped_argv: List[str], cwd_path: Path) -> Dict[str, Any]:
        del cwd_path
        symbolic = any(option in {"-s", "--symbolic"} for option in mapped_argv[1:])
        operands = [Path(target) for target in self._builtin_non_option_args(mapped_argv)]
        source, destination = operands[-2], operands[-1]
        if destination.is_dir():
            destination = destination / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if symbolic:
            os.symlink(source, destination)
        else:
            os.link(source, destination)
        return {"returncode": 0, "stdout": "", "stderr": "", "backend": "builtin"}

    def _builtin_non_option_args(self, mapped_argv: List[str]) -> List[str]:
        positions = self._non_option_positions(mapped_argv)
        return [mapped_argv[position] for position in positions]

    def _normalize_allowed_options(self, raw_options: Any) -> Dict[str, frozenset[str]]:
        normalized = {
            command: frozenset(options)
            for command, options in self.DEFAULT_ALLOWED_OPTIONS.items()
        }
        if not isinstance(raw_options, dict):
            return normalized
        for command, options in raw_options.items():
            if isinstance(options, list):
                normalized[str(command).lower()] = frozenset(str(option) for option in options)
        return normalized

    def _validate_command_options(self, executable: str, argv: List[str]) -> None:
        allowed = self.allowed_options.get(executable, frozenset())
        literal_mode = False
        for argument in argv[1:]:
            if literal_mode:
                continue
            if argument == "--":
                literal_mode = True
                continue
            if argument.startswith("-") and argument != "-":
                if argument not in allowed:
                    raise ValueError(f"unsupported option for {executable}: {argument}")

    def _next_command_id(self) -> str:
        return f"cmd-{len(self._execution_results) + 1}"

    def _apply_output_limits(self, result: Dict[str, Any]) -> None:
        stdout, stdout_truncated = self._truncate_output(str(result.get("stdout", "")))
        stderr, stderr_truncated = self._truncate_output(str(result.get("stderr", "")))
        result["stdout"] = stdout
        result["stderr"] = stderr
        result["stdout_truncated"] = stdout_truncated
        result["stderr_truncated"] = stderr_truncated

    def _truncate_output(self, value: str) -> tuple[str, bool]:
        if len(value) <= self.max_output_chars:
            return value, False
        return value[: self.max_output_chars], True

    def _build_rejected_result(self, command: str | List[str], cwd: str, exc: Exception) -> Dict[str, Any]:
        raw_command = self._coerce_command_repr(command)
        result = {
            "command_id": self._next_command_id(),
            "status": "rejected",
            "command": raw_command,
            "mapped_command": None,
            "cwd": cwd,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "timed_out": False,
            "duration_ms": 0,
            "writes_attempted": 0,
            "write_paths": [],
            "writes_outside_fixture_root": 0,
            "backend": "builtin" if self.builtin_only else "subprocess",
            "error": {
                "code": "command_rejected",
                "message": str(exc),
            },
        }
        self._execution_results.append(result)
        self._record_event(
            "command_rejected",
            command_id=result["command_id"],
            raw_command=result["command"],
            mapped_command=None,
            cwd=cwd,
            error=result["error"],
        )
        return result

    def _coerce_command_repr(self, command: str | List[str]) -> List[str]:
        if isinstance(command, str):
            stripped = command.strip()
            return [stripped] if stripped else []
        if isinstance(command, list) and all(isinstance(item, str) for item in command):
            return list(command)
        return [str(command)]

    def _record_event(self, event_type: str, **payload: Any) -> None:
        self._event_counter += 1
        event = {
            "sequence": self._event_counter,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self._execution_events.append(event)
