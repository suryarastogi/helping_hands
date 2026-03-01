"""Iterative hand implementations shared by CLI basic backends.

This module defines:
- ``_BasicIterativeHand``: shared loop mechanics and prompt protocol.
- ``BasicLangGraphHand`` and ``BasicAtomicHand``: concrete iterative backends
  used by CLI ``--backend`` selection.

These classes implement the Hand interface while depending on
``helping_hands.lib.meta.tools.filesystem`` for system-level repo file operations
(read/write path resolution and safe filesystem access).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.model_provider import (
    build_atomic_client,
    build_langchain_chat_model,
    resolve_hand_model,
)
from helping_hands.lib.meta import skills as system_skills
from helping_hands.lib.meta.tools import command as system_exec_tools
from helping_hands.lib.meta.tools import filesystem as system_tools
from helping_hands.lib.meta.tools import web as system_web_tools


class _BasicIterativeHand(Hand):
    """Shared helpers for iterative hands."""

    _EDIT_PATTERN = re.compile(
        r"@@FILE:\s*(?P<path>[^\n]+)\n```(?:[A-Za-z0-9_+-]+)?\n(?P<content>.*?)\n```",
        flags=re.DOTALL,
    )
    _READ_PATTERN = re.compile(
        r"^@@READ:\s*(?P<path>[^\n]+)\s*$",
        flags=re.MULTILINE,
    )
    _READ_FALLBACK_PATTERN = re.compile(
        r"(?i)(?:content(?:s)? of(?: the)? file|read(?: the)? file)\s*[`\"]"
        r"(?P<path>[^`\"\n]+)[`\"]"
    )
    _TOOL_PATTERN = re.compile(
        r"@@TOOL:\s*(?P<name>[A-Za-z0-9_.-]+)\n"
        r"```(?:json)?\n(?P<payload>.*?)\n```",
        flags=re.DOTALL,
    )
    _MAX_READ_CHARS = 12000
    _MAX_TOOL_OUTPUT_CHARS = 4000
    _MAX_BOOTSTRAP_DOC_CHARS = 12000
    _BOOTSTRAP_TREE_MAX_DEPTH = 4
    _BOOTSTRAP_TREE_MAX_ENTRIES = 250

    def __init__(
        self,
        config: Any,
        repo_index: Any,
        *,
        max_iterations: int = 6,
    ) -> None:
        super().__init__(config, repo_index)
        self.max_iterations = max(1, max_iterations)
        selected = system_skills.normalize_skill_selection(
            getattr(self.config, "enabled_skills", ())
        )
        merged = system_skills.merge_with_legacy_tool_flags(
            selected,
            enable_execution=bool(getattr(self.config, "enable_execution", False)),
            enable_web=bool(getattr(self.config, "enable_web", False)),
        )
        self._selected_skills = system_skills.resolve_skills(merged)
        self._tool_runners = system_skills.build_tool_runner_map(self._selected_skills)

    def _execution_tools_enabled(self) -> bool:
        """Return whether execution skills (Python/Bash) are active."""
        return bool(getattr(self.config, "enable_execution", False))

    def _web_tools_enabled(self) -> bool:
        """Return whether web skills (search/browse) are active."""
        return bool(getattr(self.config, "enable_web", False))

    def _tool_instructions(self) -> str:
        """Build prompt-ready instructions for all enabled skills."""
        lines = [system_skills.format_skill_instructions(self._selected_skills)]
        lines.append(
            "Tool results are returned as @@TOOL_RESULT blocks "
            "in the next iteration summary."
        )
        return "\n".join(lines)

    def _build_iteration_prompt(
        self,
        *,
        prompt: str,
        iteration: int,
        max_iterations: int,
        previous_summary: str,
        bootstrap_context: str,
    ) -> str:
        """Assemble the full prompt for a single iteration of the loop."""
        previous = previous_summary.strip() or "none"
        bootstrap = (
            f"Bootstrap repository context:\n{bootstrap_context}\n\n"
            if bootstrap_context
            else ""
        )
        return (
            f"Task request: {prompt}\n\n"
            f"Iteration: {iteration}/{max_iterations}\n"
            f"Previous iteration summary: {previous}\n\n"
            f"{bootstrap}"
            "Work directly against the repository context and provide progress.\n"
            "When you need to inspect a file, request it using exactly:\n"
            "@@READ: relative/path.py\n"
            "Do not ask the user to provide file contents.\n"
            "When you need to update files, include complete file contents using:\n"
            "@@FILE: relative/path.py\n"
            "```python\n"
            "<full file content>\n"
            "```\n"
            "You may include multiple @@FILE blocks.\n"
            f"{self._tool_instructions()}\n"
            "Read results are returned as @@READ_RESULT blocks in the next "
            "iteration summary.\n"
            "At the end of your response include exactly one line in this form:\n"
            "SATISFIED: yes|no\n"
            "Use SATISFIED: yes only when the task is fully complete.\n"
        )

    @staticmethod
    def _is_satisfied(content: str) -> bool:
        """Check if the model response contains ``SATISFIED: yes``."""
        match = re.search(r"SATISFIED:\s*(yes|no)", content, flags=re.IGNORECASE)
        if match:
            return match.group(1).lower() == "yes"
        return False

    @classmethod
    def _extract_inline_edits(cls, content: str) -> list[tuple[str, str]]:
        """Extract ``@@FILE`` blocks from model output as (path, content) pairs."""
        return [
            (m.group("path").strip(), m.group("content"))
            for m in cls._EDIT_PATTERN.finditer(content)
        ]

    @classmethod
    def _extract_read_requests(cls, content: str) -> list[str]:
        """Extract ``@@READ`` file path requests from model output."""
        explicit = [
            m.group("path").strip() for m in cls._READ_PATTERN.finditer(content)
        ]
        if explicit:
            return explicit
        return [
            m.group("path").strip()
            for m in cls._READ_FALLBACK_PATTERN.finditer(content)
        ]

    @classmethod
    def _extract_tool_requests(
        cls,
        content: str,
    ) -> list[tuple[str, dict[str, Any], str | None]]:
        requests: list[tuple[str, dict[str, Any], str | None]] = []
        for match in cls._TOOL_PATTERN.finditer(content):
            tool_name = match.group("name").strip()
            payload_text = match.group("payload").strip()
            try:
                payload = json.loads(payload_text)
            except json.JSONDecodeError as exc:
                requests.append(
                    (
                        tool_name,
                        {},
                        f"invalid JSON payload ({exc.msg})",
                    )
                )
                continue
            if not isinstance(payload, dict):
                requests.append((tool_name, {}, "payload must be a JSON object"))
                continue
            requests.append((tool_name, payload, None))
        return requests

    @staticmethod
    def _merge_iteration_summary(content: str, tool_feedback: str) -> str:
        if not tool_feedback:
            return content
        return f"{content}\n\nTool results:\n{tool_feedback}"

    def _execute_read_requests(self, content: str) -> str:
        root = self.repo_index.root.resolve()
        requests = list(dict.fromkeys(self._extract_read_requests(content)))
        if not requests:
            return ""

        chunks: list[str] = []
        for rel_path in requests:
            try:
                text, truncated, display_path = system_tools.read_text_file(
                    root,
                    rel_path,
                    max_chars=self._MAX_READ_CHARS,
                )
            except ValueError:
                chunks.append(f"@@READ_RESULT: {rel_path}\nERROR: invalid path")
                continue
            except FileNotFoundError:
                chunks.append(f"@@READ_RESULT: {rel_path}\nERROR: file not found")
                continue
            except IsADirectoryError:
                chunks.append(f"@@READ_RESULT: {rel_path}\nERROR: path is a directory")
                continue
            except UnicodeError:
                chunks.append(
                    f"@@READ_RESULT: {rel_path}\nERROR: file is not UTF-8 text"
                )
                continue

            truncated_note = "\n[truncated]" if truncated else ""
            chunks.append(
                f"@@READ_RESULT: {display_path}\n```text\n{text}\n```{truncated_note}"
            )
        return "\n\n".join(chunks).strip()

    @staticmethod
    def _parse_str_list(
        payload: dict[str, Any],
        *,
        key: str,
    ) -> list[str]:
        raw = payload.get(key, [])
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ValueError(f"{key} must be a list of strings")
        values: list[str] = []
        for value in raw:
            if not isinstance(value, str):
                raise ValueError(f"{key} must contain only strings")
            values.append(value)
        return values

    @staticmethod
    def _parse_positive_int(
        payload: dict[str, Any],
        *,
        key: str,
        default: int,
    ) -> int:
        raw = payload.get(key, default)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ValueError(f"{key} must be an integer")
        if raw <= 0:
            raise ValueError(f"{key} must be > 0")
        return raw

    @staticmethod
    def _parse_optional_str(
        payload: dict[str, Any],
        *,
        key: str,
    ) -> str | None:
        raw = payload.get(key)
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError(f"{key} must be a string")
        text = raw.strip()
        return text or None

    @staticmethod
    def _format_command(command: list[str]) -> str:
        return " ".join(shlex.quote(token) for token in command)

    @classmethod
    def _truncate_tool_output(cls, text: str) -> tuple[str, bool]:
        if len(text) <= cls._MAX_TOOL_OUTPUT_CHARS:
            return text, False
        return text[: cls._MAX_TOOL_OUTPUT_CHARS], True

    @classmethod
    def _format_command_result(
        cls,
        *,
        tool_name: str,
        result: system_exec_tools.CommandResult,
    ) -> str:
        stdout, stdout_truncated = cls._truncate_tool_output(result.stdout)
        stderr, stderr_truncated = cls._truncate_tool_output(result.stderr)
        stdout_note = "\n[truncated]" if stdout_truncated else ""
        stderr_note = "\n[truncated]" if stderr_truncated else ""
        status = "success" if result.success else "failure"
        return (
            f"@@TOOL_RESULT: {tool_name}\n"
            f"status: {status}\n"
            f"exit_code: {result.exit_code}\n"
            f"timed_out: {str(result.timed_out).lower()}\n"
            f"cwd: {result.cwd}\n"
            f"command: {cls._format_command(result.command)}\n"
            f"stdout:\n```text\n{stdout}\n```{stdout_note}\n"
            f"stderr:\n```text\n{stderr}\n```{stderr_note}"
        )

    @classmethod
    def _format_web_search_result(
        cls,
        *,
        tool_name: str,
        result: system_web_tools.WebSearchResult,
    ) -> str:
        items = [
            {
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
            }
            for item in result.results
        ]
        payload = json.dumps(items, ensure_ascii=False, indent=2)
        payload_text, truncated = cls._truncate_tool_output(payload)
        truncated_note = "\n[truncated]" if truncated else ""
        return (
            f"@@TOOL_RESULT: {tool_name}\n"
            "status: success\n"
            f"query: {result.query}\n"
            f"result_count: {len(result.results)}\n"
            f"results:\n```json\n{payload_text}\n```{truncated_note}"
        )

    @classmethod
    def _format_web_browse_result(
        cls,
        *,
        tool_name: str,
        result: system_web_tools.WebBrowseResult,
    ) -> str:
        text, output_truncated = cls._truncate_tool_output(result.content)
        truncated_note = "\n[truncated]" if output_truncated else ""
        return (
            f"@@TOOL_RESULT: {tool_name}\n"
            "status: success\n"
            f"url: {result.url}\n"
            f"final_url: {result.final_url}\n"
            f"status_code: {result.status_code}\n"
            f"source_truncated: {str(result.truncated).lower()}\n"
            f"content:\n```text\n{text}\n```{truncated_note}"
        )

    @staticmethod
    def _tool_disabled_error(tool_name: str) -> ValueError:
        required_skill = system_skills.skill_name_for_tool(tool_name)
        if required_skill == "execution":
            return ValueError(
                f"{tool_name} is disabled; re-run with enable_execution=true"
            )
        if required_skill == "web":
            return ValueError(f"{tool_name} is disabled; re-run with enable_web=true")
        if required_skill:
            return ValueError(
                f"{tool_name} is disabled; re-run with --skills {required_skill}"
            )
        return ValueError(f"unsupported tool: {tool_name}")

    def _run_tool_request(
        self,
        *,
        root: Path,
        tool_name: str,
        payload: dict[str, Any],
    ) -> str:
        runner = self._tool_runners.get(tool_name)
        if runner is None:
            raise self._tool_disabled_error(tool_name)

        result = runner(root, payload)
        if isinstance(result, system_exec_tools.CommandResult):
            return self._format_command_result(tool_name=tool_name, result=result)
        if isinstance(result, system_web_tools.WebSearchResult):
            return self._format_web_search_result(tool_name=tool_name, result=result)
        if isinstance(result, system_web_tools.WebBrowseResult):
            return self._format_web_browse_result(tool_name=tool_name, result=result)
        raise TypeError(f"unsupported tool result type: {type(result)!r}")

    def _execute_tool_requests(self, content: str) -> str:
        root = self.repo_index.root.resolve()
        requests = self._extract_tool_requests(content)
        if not requests:
            return ""

        chunks: list[str] = []
        for tool_name, payload, error in requests:
            if error:
                chunks.append(f"@@TOOL_RESULT: {tool_name}\nERROR: {error}")
                continue
            try:
                result = self._run_tool_request(
                    root=root,
                    tool_name=tool_name,
                    payload=payload,
                )
            except (
                FileNotFoundError,
                IsADirectoryError,
                NotADirectoryError,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                chunks.append(f"@@TOOL_RESULT: {tool_name}\nERROR: {exc}")
                continue
            chunks.append(result)
        return "\n\n".join(chunks).strip()

    def _apply_inline_edits(self, content: str) -> list[str]:
        root = self.repo_index.root.resolve()
        changed: list[str] = []
        for rel_path, body in self._extract_inline_edits(content):
            try:
                display_path = system_tools.write_text_file(root, rel_path, body)
            except ValueError:
                continue
            changed.append(display_path)
        if changed:
            self.repo_index = self.repo_index.from_path(root)
        return changed

    def _read_bootstrap_doc(
        self,
        root: Path,
        candidates: tuple[str, ...],
    ) -> str:
        for rel_path in candidates:
            if not system_tools.path_exists(root, rel_path):
                continue
            try:
                text, truncated, display_path = system_tools.read_text_file(
                    root,
                    rel_path,
                    max_chars=self._MAX_BOOTSTRAP_DOC_CHARS,
                )
            except (FileNotFoundError, IsADirectoryError, UnicodeError, ValueError):
                continue

            truncated_note = "\n[truncated]" if truncated else ""
            return f"{display_path}:\n```text\n{text}\n```{truncated_note}"
        return ""

    def _build_tree_snapshot(self) -> str:
        entries: set[str] = set()
        for rel_path in sorted(self.repo_index.files):
            normalized = system_tools.normalize_relative_path(rel_path)
            if not normalized:
                continue
            parts = [part for part in normalized.split("/") if part]
            if not parts:
                continue

            max_depth = min(len(parts), self._BOOTSTRAP_TREE_MAX_DEPTH)
            for idx in range(1, max_depth):
                entries.add("/".join(parts[:idx]) + "/")
            if len(parts) <= self._BOOTSTRAP_TREE_MAX_DEPTH:
                entries.add("/".join(parts))
            else:
                entries.add("/".join(parts[: self._BOOTSTRAP_TREE_MAX_DEPTH]) + "/...")

        ordered = sorted(entries)
        if not ordered:
            return "- (empty)"

        shown = ordered[: self._BOOTSTRAP_TREE_MAX_ENTRIES]
        lines = [f"- {item}" for item in shown]
        hidden = len(ordered) - len(shown)
        if hidden > 0:
            lines.append(f"- ... ({hidden} more)")
        return "\n".join(lines)

    def _build_bootstrap_context(self) -> str:
        root = self.repo_index.root.resolve()
        sections: list[str] = []

        readme = self._read_bootstrap_doc(root, ("README.md", "readme.md"))
        if readme:
            sections.append(readme)

        agent = self._read_bootstrap_doc(root, ("AGENT.md", "agent.md"))
        if agent:
            sections.append(agent)

        sections.append(
            "Repository tree snapshot (depth <= "
            f"{self._BOOTSTRAP_TREE_MAX_DEPTH}):\n"
            f"{self._build_tree_snapshot()}"
        )
        return "\n\n".join(sections)


class BasicLangGraphHand(_BasicIterativeHand):
    """Iterative LangGraph-backed hand with streaming and interruption."""

    def __init__(
        self,
        config: Any,
        repo_index: Any,
        *,
        max_iterations: int = 6,
    ) -> None:
        super().__init__(config, repo_index, max_iterations=max_iterations)
        self._hand_model = resolve_hand_model(self.config.model)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from langgraph.prebuilt import create_react_agent

        llm = build_langchain_chat_model(
            self._hand_model,
            streaming=True,
        )
        system_prompt = (
            self._build_system_prompt()
            + "\n\nYou are running an iterative repository implementation loop."
            " Keep responses concise, implementation-focused, and deterministic."
        )
        return create_react_agent(
            model=llm,
            tools=[],
            prompt=system_prompt,
        )

    @staticmethod
    def _result_content(result: dict[str, Any]) -> str:
        messages = result.get("messages") or []
        if not messages:
            return ""
        last_msg = messages[-1]
        return last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    def run(self, prompt: str) -> HandResponse:
        self.reset_interrupt()
        prior = ""
        bootstrap_context = self._build_bootstrap_context()
        transcripts: list[str] = []
        completed = False
        iterations = 0

        for iteration in range(1, self.max_iterations + 1):
            if self._is_interrupted():
                break
            iterations = iteration
            step_prompt = self._build_iteration_prompt(
                prompt=prompt,
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_summary=prior,
                bootstrap_context=bootstrap_context if iteration == 1 else "",
            )
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": step_prompt}]}
            )
            content = self._result_content(result)
            changed = self._apply_inline_edits(content)
            read_feedback = self._execute_read_requests(content)
            tool_feedback = self._execute_tool_requests(content)
            combined_feedback = "\n\n".join(
                part for part in (read_feedback, tool_feedback) if part
            ).strip()
            transcripts.append(f"[iteration {iteration}]\n{content}")
            if changed:
                transcripts.append(f"[files updated] {', '.join(changed)}")
            if combined_feedback:
                transcripts.append(f"[tool results]\n{combined_feedback}")
            prior = self._merge_iteration_summary(content, combined_feedback)
            if self._is_satisfied(content):
                completed = True
                break

        interrupted = self._is_interrupted()
        if interrupted:
            status = "interrupted"
        elif completed:
            status = "satisfied"
        else:
            status = "max_iterations"

        pr_metadata = self._finalize_repo_pr(
            backend="basic-langgraph",
            prompt=prompt,
            summary=prior,
        )
        message = "\n\n".join(transcripts) if transcripts else "No output produced."
        return HandResponse(
            message=message,
            metadata={
                "backend": "basic-langgraph",
                "model": self._hand_model.model,
                "provider": self._hand_model.provider.name,
                "iterations": iterations,
                "status": status,
                "interrupted": str(interrupted).lower(),
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.reset_interrupt()
        prior = ""
        bootstrap_context = self._build_bootstrap_context()

        _env_name = self._hand_model.provider.api_key_env_var
        _present = "set" if os.environ.get(_env_name, "").strip() else "not set"
        yield (
            f"[basic-langgraph] provider={self._hand_model.provider.name}"
            f" | auth={_env_name} ({_present})\n"
        )

        for iteration in range(1, self.max_iterations + 1):
            if self._is_interrupted():
                yield "\n[interrupted]\n"
                return

            yield f"\n[iteration {iteration}/{self.max_iterations}]\n"
            step_prompt = self._build_iteration_prompt(
                prompt=prompt,
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_summary=prior,
                bootstrap_context=bootstrap_context if iteration == 1 else "",
            )
            parts: list[str] = []
            async for event in self._agent.astream_events(
                {"messages": [{"role": "user", "content": step_prompt}]},
                version="v2",
            ):
                if self._is_interrupted():
                    break
                if event["event"] == "on_chat_model_stream" and event["data"].get(
                    "chunk"
                ):
                    chunk = event["data"]["chunk"]
                    text = chunk.content if hasattr(chunk, "content") else ""
                    if text:
                        parts.append(str(text))
                        yield str(text)
            if self._is_interrupted():
                yield "\n[interrupted]\n"
                return

            content = "".join(parts)
            changed = self._apply_inline_edits(content)
            if changed:
                yield f"\n[files updated] {', '.join(changed)}\n"
            read_feedback = self._execute_read_requests(content)
            tool_feedback = self._execute_tool_requests(content)
            combined_feedback = "\n\n".join(
                part for part in (read_feedback, tool_feedback) if part
            ).strip()
            if combined_feedback:
                yield f"\n[tool results]\n{combined_feedback}\n"
            prior = self._merge_iteration_summary(content, combined_feedback)
            if self._is_satisfied(content):
                yield "\n\nTask marked satisfied.\n"
                pr_metadata = self._finalize_repo_pr(
                    backend="basic-langgraph",
                    prompt=prompt,
                    summary=content,
                )
                if pr_metadata.get("pr_url"):
                    yield f"\nPR created: {pr_metadata['pr_url']}\n"
                elif pr_metadata.get("pr_status") not in {"no_changes", "disabled"}:
                    yield f"\nPR status: {pr_metadata.get('pr_status')}\n"
                return
            yield "\n\nContinuing...\n"

        pr_metadata = self._finalize_repo_pr(
            backend="basic-langgraph",
            prompt=prompt,
            summary=prior,
        )
        if pr_metadata.get("pr_url"):
            yield f"\nPR created: {pr_metadata['pr_url']}\n"
        elif pr_metadata.get("pr_status") not in {"no_changes", "disabled"}:
            yield f"\nPR status: {pr_metadata.get('pr_status')}\n"
        yield "\n\nMax iterations reached.\n"


class BasicAtomicHand(_BasicIterativeHand):
    """Iterative Atomic-backed hand with streaming and interruption."""

    def __init__(
        self,
        config: Any,
        repo_index: Any,
        *,
        max_iterations: int = 6,
    ) -> None:
        super().__init__(config, repo_index, max_iterations=max_iterations)
        self._input_schema: type[Any] = None  # type: ignore[assignment]
        self._hand_model = resolve_hand_model(self.config.model)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from atomic_agents import AgentConfig, AtomicAgent, BasicChatInputSchema
        from atomic_agents.context import (
            ChatHistory,
            SystemPromptGenerator,
        )

        self._input_schema = BasicChatInputSchema

        client = build_atomic_client(self._hand_model)
        history = ChatHistory()
        prompt_gen = SystemPromptGenerator(
            background=[
                self._build_system_prompt()
                + "\n\nYou are running an iterative repository implementation loop."
                " Keep responses concise, implementation-focused, and deterministic."
            ],
        )
        return AtomicAgent(
            config=AgentConfig(
                client=client,
                model=self._hand_model.model,
                history=history,
                system_prompt_generator=prompt_gen,
            )
        )

    def _make_input(self, prompt: str) -> Any:
        return self._input_schema(chat_message=prompt)

    @staticmethod
    def _extract_message(response: Any) -> str:
        if hasattr(response, "chat_message") and response.chat_message:
            return str(response.chat_message)
        return str(response)

    def run(self, prompt: str) -> HandResponse:
        self.reset_interrupt()
        prior = ""
        bootstrap_context = self._build_bootstrap_context()
        transcripts: list[str] = []
        completed = False
        iterations = 0

        for iteration in range(1, self.max_iterations + 1):
            if self._is_interrupted():
                break
            iterations = iteration
            step_prompt = self._build_iteration_prompt(
                prompt=prompt,
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_summary=prior,
                bootstrap_context=bootstrap_context if iteration == 1 else "",
            )
            response = self._agent.run(self._make_input(step_prompt))
            content = self._extract_message(response)
            changed = self._apply_inline_edits(content)
            read_feedback = self._execute_read_requests(content)
            tool_feedback = self._execute_tool_requests(content)
            combined_feedback = "\n\n".join(
                part for part in (read_feedback, tool_feedback) if part
            ).strip()
            transcripts.append(f"[iteration {iteration}]\n{content}")
            if changed:
                transcripts.append(f"[files updated] {', '.join(changed)}")
            if combined_feedback:
                transcripts.append(f"[tool results]\n{combined_feedback}")
            prior = self._merge_iteration_summary(content, combined_feedback)
            if self._is_satisfied(content):
                completed = True
                break

        interrupted = self._is_interrupted()
        if interrupted:
            status = "interrupted"
        elif completed:
            status = "satisfied"
        else:
            status = "max_iterations"

        pr_metadata = self._finalize_repo_pr(
            backend="basic-atomic",
            prompt=prompt,
            summary=prior,
        )
        message = "\n\n".join(transcripts) if transcripts else "No output produced."
        return HandResponse(
            message=message,
            metadata={
                "backend": "basic-atomic",
                "model": self._hand_model.model,
                "provider": self._hand_model.provider.name,
                "iterations": iterations,
                "status": status,
                "interrupted": str(interrupted).lower(),
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.reset_interrupt()
        prior = ""
        bootstrap_context = self._build_bootstrap_context()

        _env_name = self._hand_model.provider.api_key_env_var
        _present = "set" if os.environ.get(_env_name, "").strip() else "not set"
        yield (
            f"[basic-atomic] provider={self._hand_model.provider.name}"
            f" | auth={_env_name} ({_present})\n"
        )

        for iteration in range(1, self.max_iterations + 1):
            if self._is_interrupted():
                yield "\n[interrupted]\n"
                return

            yield f"\n[iteration {iteration}/{self.max_iterations}]\n"
            step_prompt = self._build_iteration_prompt(
                prompt=prompt,
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_summary=prior,
                bootstrap_context=bootstrap_context if iteration == 1 else "",
            )
            stream_text = ""
            step_input = self._make_input(step_prompt)
            try:
                async_result = self._agent.run_async(step_input)
            except AssertionError:
                partial = await asyncio.to_thread(self._agent.run, step_input)
                current = self._extract_message(partial)
                if current.startswith(stream_text):
                    delta = current[len(stream_text) :]
                else:
                    delta = current
                stream_text = current
                if delta:
                    yield delta
                async_result = None
            except Exception:
                raise
            if async_result is not None and hasattr(async_result, "__aiter__"):
                async for partial in async_result:
                    if self._is_interrupted():
                        break
                    current = self._extract_message(partial)
                    if current.startswith(stream_text):
                        delta = current[len(stream_text) :]
                    else:
                        delta = current
                    stream_text = current
                    if delta:
                        yield delta
            elif async_result is not None:
                try:
                    partial = await async_result
                except AssertionError:
                    partial = await asyncio.to_thread(self._agent.run, step_input)
                current = self._extract_message(partial)
                if current.startswith(stream_text):
                    delta = current[len(stream_text) :]
                else:
                    delta = current
                stream_text = current
                if delta:
                    yield delta
            if self._is_interrupted():
                yield "\n[interrupted]\n"
                return

            changed = self._apply_inline_edits(stream_text)
            if changed:
                yield f"\n[files updated] {', '.join(changed)}\n"
            read_feedback = self._execute_read_requests(stream_text)
            tool_feedback = self._execute_tool_requests(stream_text)
            combined_feedback = "\n\n".join(
                part for part in (read_feedback, tool_feedback) if part
            ).strip()
            if combined_feedback:
                yield f"\n[tool results]\n{combined_feedback}\n"
            prior = self._merge_iteration_summary(stream_text, combined_feedback)
            if self._is_satisfied(stream_text):
                yield "\n\nTask marked satisfied.\n"
                pr_metadata = self._finalize_repo_pr(
                    backend="basic-atomic",
                    prompt=prompt,
                    summary=stream_text,
                )
                if pr_metadata.get("pr_url"):
                    yield f"\nPR created: {pr_metadata['pr_url']}\n"
                elif pr_metadata.get("pr_status") not in {"no_changes", "disabled"}:
                    yield f"\nPR status: {pr_metadata.get('pr_status')}\n"
                return
            yield "\n\nContinuing...\n"

        pr_metadata = self._finalize_repo_pr(
            backend="basic-atomic",
            prompt=prompt,
            summary=prior,
        )
        if pr_metadata.get("pr_url"):
            yield f"\nPR created: {pr_metadata['pr_url']}\n"
        elif pr_metadata.get("pr_status") not in {"no_changes", "disabled"}:
            yield f"\nPR status: {pr_metadata.get('pr_status')}\n"
        yield "\n\nMax iterations reached.\n"
