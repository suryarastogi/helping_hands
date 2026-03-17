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
import logging
import os
import re
import shlex
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from helping_hands.lib.hands.v1.hand.base import (
    _META_BACKEND,
    _META_MODEL,
    _META_PR_STATUS,
    _META_PR_URL,
    _META_PROVIDER,
    _PR_STATUSES_SKIPPED,
    Hand,
    HandResponse,
)
from helping_hands.lib.hands.v1.hand.langgraph import (
    _LANGCHAIN_STREAM_EVENT,
    langchain_user_message,
)
from helping_hands.lib.hands.v1.hand.model_provider import (
    HandModel,
    build_atomic_client,
    build_langchain_chat_model,
    resolve_hand_model,
)
from helping_hands.lib.meta import skills as system_skills
from helping_hands.lib.meta.tools import (
    command as system_exec_tools,
    filesystem as system_tools,
    registry as tool_registry,
    web as system_web_tools,
)
from helping_hands.lib.meta.tools.registry import (
    _parse_optional_str,
    _parse_positive_int,
    _parse_str_list,
)

logger = logging.getLogger(__name__)

__all__ = ["DEFAULT_MAX_ITERATIONS", "BasicAtomicHand", "BasicLangGraphHand"]

DEFAULT_MAX_ITERATIONS: int = 6
"""Default maximum number of AI loop iterations for iterative hands."""

_README_CANDIDATES: tuple[str, ...] = ("README.md", "readme.md")
"""Candidate filenames for project README, checked in order during bootstrap."""

_AGENT_DOC_CANDIDATES: tuple[str, ...] = ("AGENT.md", "agent.md")
"""Candidate filenames for agent guidance doc, checked in order during bootstrap."""

_RUN_STATUS_INTERRUPTED: str = "interrupted"
"""Run status when the hand was interrupted by the user."""

_RUN_STATUS_SATISFIED: str = "satisfied"
"""Run status when the AI marked the task as satisfied."""

_RUN_STATUS_MAX_ITERATIONS: str = "max_iterations"
"""Run status when the iteration cap was reached without satisfaction."""

_TRUNCATION_MARKER: str = "\n[truncated]"
"""Marker appended to tool output that was truncated to fit size limits."""

_AUTH_PRESENT_LABEL: str = "set"
"""Label shown in stream output when the provider API key is present."""

_AUTH_ABSENT_LABEL: str = "not set"
"""Label shown in stream output when the provider API key is missing."""


class _BasicIterativeHand(Hand):
    """Shared helpers for iterative hands."""

    _BACKEND_NAME: str
    _hand_model: HandModel

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
    _MAX_ITERATIONS = 1000

    def __init__(
        self,
        config: Any,
        repo_index: Any,
        *,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        """Initialize the iterative hand with iteration cap and tool dispatch.

        Args:
            config: Hand configuration object (model, tools, skills, etc.).
            repo_index: Repository index providing file listing and root path.
            max_iterations: Maximum number of AI loop iterations (clamped to
                ``[1, _MAX_ITERATIONS]``).
        """
        super().__init__(config, repo_index)
        clamped = max(1, max_iterations)
        if clamped > self._MAX_ITERATIONS:
            logger.warning(
                "max_iterations %d exceeds cap %d, clamping",
                clamped,
                self._MAX_ITERATIONS,
            )
            clamped = self._MAX_ITERATIONS
        self.max_iterations = clamped
        # _selected_tool_categories is resolved by Hand.__init__(); build dispatch map.
        self._tool_runners = tool_registry.build_tool_runner_map(
            self._selected_tool_categories
        )

    def _execution_tools_enabled(self) -> bool:
        """Check whether execution tools (python, bash) are enabled in config."""
        return self.config.enable_execution

    def _web_tools_enabled(self) -> bool:
        """Check whether web tools (search, browse) are enabled in config."""
        return self.config.enable_web

    def _tool_instructions(self) -> str:
        """Build tool usage instructions for the iteration prompt.

        Returns:
            Formatted instruction text describing available tools and skills.
        """
        lines = [tool_registry.format_tool_instructions(self._selected_tool_categories)]
        lines.append(
            "Tool results are returned as @@TOOL_RESULT blocks "
            "in the next iteration summary."
        )
        skill_knowledge = system_skills.format_skill_knowledge(self._selected_skills)
        if skill_knowledge:
            lines.append(skill_knowledge)
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
        """Build the full prompt string for a single iteration step.

        Combines the task request, iteration counter, previous summary,
        optional bootstrap context (first iteration only), and inline
        tool/read/file instructions.

        Args:
            prompt: Original user task description.
            iteration: Current iteration number (1-based).
            max_iterations: Total allowed iterations.
            previous_summary: Summary text from the prior iteration.
            bootstrap_context: Repo bootstrap context (README, AGENT, tree).

        Returns:
            Formatted prompt string ready for the AI model.
        """
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
        """Check whether the AI response contains a ``SATISFIED: yes`` marker.

        Args:
            content: Raw AI response text.

        Returns:
            ``True`` if the response contains ``SATISFIED: yes`` (case-insensitive),
            ``False`` otherwise.
        """
        match = re.search(r"SATISFIED:\s*(yes|no)", content, flags=re.IGNORECASE)
        if match:
            return match.group(1).lower() == "yes"
        return False

    @classmethod
    def _extract_inline_edits(cls, content: str) -> list[tuple[str, str]]:
        """Extract ``@@FILE`` inline edit blocks from the AI response.

        Args:
            content: Raw AI response text.

        Returns:
            List of ``(relative_path, file_content)`` tuples parsed from
            ``@@FILE:`` fenced code blocks.
        """
        return [
            (m.group("path").strip(), m.group("content"))
            for m in cls._EDIT_PATTERN.finditer(content)
        ]

    @classmethod
    def _extract_read_requests(cls, content: str) -> list[str]:
        """Extract ``@@READ`` file-read requests from the AI response.

        Falls back to a natural-language pattern (e.g. ``read the file "x"``)
        when no explicit ``@@READ:`` directives are found.

        Args:
            content: Raw AI response text.

        Returns:
            Deduplicated list of relative file paths requested for reading.
        """
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
        """Extract ``@@TOOL`` invocation requests from the AI response.

        Each match is parsed as a tool name plus a JSON payload. Invalid
        JSON or non-dict payloads are returned with an error string in the
        third tuple element.

        Args:
            content: Raw AI response text.

        Returns:
            List of ``(tool_name, payload_dict, error_or_none)`` tuples.
        """
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
        """Merge AI response content with tool feedback for the next iteration.

        Args:
            content: AI response text from the current iteration.
            tool_feedback: Concatenated tool/read result blocks (may be empty).

        Returns:
            Combined summary string; returns *content* unchanged when
            *tool_feedback* is empty.
        """
        if not tool_feedback:
            return content
        return f"{content}\n\nTool results:\n{tool_feedback}"

    def _collect_tool_feedback(self, content: str) -> str:
        """Execute read and tool requests, returning combined feedback.

        Runs ``_execute_read_requests`` and ``_execute_tool_requests`` on
        *content*, then joins non-empty results with a double newline.

        Args:
            content: AI response text to scan for ``@@READ`` / ``@@TOOL``
                requests.

        Returns:
            Combined feedback string (stripped), or ``""`` if neither
            read nor tool requests produced output.
        """
        read_feedback = self._execute_read_requests(content)
        tool_feedback = self._execute_tool_requests(content)
        return "\n\n".join(
            part for part in (read_feedback, tool_feedback) if part
        ).strip()

    def _process_stream_iteration(
        self, content: str, prompt: str
    ) -> tuple[list[str], str, bool]:
        """Apply edits, collect feedback, and check satisfaction for a stream iteration.

        Encapsulates the post-response processing shared by
        ``BasicLangGraphHand.stream()`` and ``BasicAtomicHand.stream()``:
        apply inline edits, collect tool feedback, merge iteration summary,
        and check whether the task is satisfied.

        Args:
            content: AI response text for the current iteration.
            prompt: Original user prompt (passed to ``_finalize_repo_pr`` on
                satisfaction).

        Returns:
            Tuple of ``(messages, prior, satisfied)`` where *messages* is a
            list of strings to yield, *prior* is the merged iteration summary,
            and *satisfied* is ``True`` when the task should stop.
        """
        messages: list[str] = []
        changed = self._apply_inline_edits(content)
        if changed:
            messages.append(f"\n[files updated] {', '.join(changed)}\n")
        combined_feedback = self._collect_tool_feedback(content)
        if combined_feedback:
            messages.append(f"\n[tool results]\n{combined_feedback}\n")
        prior = self._merge_iteration_summary(content, combined_feedback)
        if self._is_satisfied(content):
            messages.append("\n\nTask marked satisfied.\n")
            pr_metadata = self._finalize_repo_pr(
                backend=self._BACKEND_NAME,
                prompt=prompt,
                summary=content,
            )
            status_line = self._pr_status_line(pr_metadata)
            if status_line:
                messages.append(status_line)
            return messages, prior, True
        messages.append("\n\nContinuing...\n")
        return messages, prior, False

    def _stream_max_iterations_tail(self, prompt: str, prior: str) -> list[str]:
        """Finalize stream when max iterations are reached.

        Called at the end of both ``BasicLangGraphHand.stream()`` and
        ``BasicAtomicHand.stream()`` when the iteration loop exhausts
        without satisfaction.

        Args:
            prompt: Original user prompt for PR finalization.
            prior: Last merged iteration summary.

        Returns:
            List of strings to yield (PR status line + max-iterations
            message).
        """
        messages: list[str] = []
        pr_metadata = self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary=prior,
        )
        status_line = self._pr_status_line(pr_metadata)
        if status_line:
            messages.append(status_line)
        messages.append("\n\nMax iterations reached.\n")
        return messages

    @staticmethod
    def _append_iteration_transcript(
        transcripts: list[str],
        iteration: int,
        content: str,
        changed: list[str],
        combined_feedback: str,
    ) -> None:
        """Append iteration summary lines to *transcripts*.

        Builds a consistent transcript block used by ``run()`` methods of
        both ``BasicLangGraphHand`` and ``BasicAtomicHand``.

        Args:
            transcripts: Mutable transcript list to extend.
            iteration: Current 1-based iteration number.
            content: AI response text for this iteration.
            changed: List of filenames updated by inline edits (may be empty).
            combined_feedback: Combined tool/read feedback (may be empty).
        """
        transcripts.append(f"[iteration {iteration}]\n{content}")
        if changed:
            transcripts.append(f"[files updated] {', '.join(changed)}")
        if combined_feedback:
            transcripts.append(f"[tool results]\n{combined_feedback}")

    def _execute_read_requests(self, content: str) -> str:
        """Execute all ``@@READ`` requests found in the AI response.

        Reads each requested file from the repo root (deduplicated, capped at
        ``_MAX_READ_CHARS``), returning formatted ``@@READ_RESULT`` blocks.

        Args:
            content: Raw AI response text containing ``@@READ:`` directives.

        Returns:
            Concatenated ``@@READ_RESULT`` blocks, or empty string if no
            read requests were found.
        """
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
            except UnicodeError:
                chunks.append(
                    self._format_error_result(
                        "READ", rel_path, "file is not UTF-8 text"
                    )
                )
                continue
            except ValueError as exc:
                chunks.append(self._format_error_result("READ", rel_path, str(exc)))
                continue
            except FileNotFoundError:
                chunks.append(
                    self._format_error_result("READ", rel_path, "file not found")
                )
                continue
            except IsADirectoryError:
                chunks.append(
                    self._format_error_result("READ", rel_path, "path is a directory")
                )
                continue

            truncated_note = _TRUNCATION_MARKER if truncated else ""
            chunks.append(
                f"@@READ_RESULT: {display_path}\n```text\n{text}\n```{truncated_note}"
            )
        return "\n\n".join(chunks).strip()

    # Payload validators delegated to registry module:
    _parse_str_list = staticmethod(_parse_str_list)
    _parse_positive_int = staticmethod(_parse_positive_int)
    _parse_optional_str = staticmethod(_parse_optional_str)

    @staticmethod
    def _format_error_result(tag: str, name: str, message: str) -> str:
        """Format an error as a ``@@<TAG>_RESULT`` block.

        Args:
            tag: Result tag prefix (e.g. ``"READ"`` or ``"TOOL"``).
            name: Identifier for the request that failed (path or tool name).
            message: Human-readable error description.

        Returns:
            Formatted error string like ``@@READ_RESULT: foo\\nERROR: msg``.
        """
        return f"@@{tag}_RESULT: {name}\nERROR: {message}"

    @staticmethod
    def _format_command(command: list[str]) -> str:
        """Format a command list as a shell-safe string for display.

        Args:
            command: List of command tokens to format.

        Returns:
            Shell-quoted string representation of the command.
        """
        return " ".join(shlex.quote(token) for token in command)

    @classmethod
    def _truncate_tool_output(cls, text: str) -> tuple[str, bool]:
        """Truncate tool output text to ``_MAX_TOOL_OUTPUT_CHARS``.

        Args:
            text: Raw tool output string.

        Returns:
            Tuple of ``(possibly_truncated_text, was_truncated)``.
        """
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
        """Format a ``CommandResult`` as a ``@@TOOL_RESULT`` block.

        Args:
            tool_name: Name of the invoked tool.
            result: Command execution result to format.

        Returns:
            Formatted multi-line string with status, exit code, stdout,
            and stderr sections.
        """
        stdout, stdout_truncated = cls._truncate_tool_output(result.stdout)
        stderr, stderr_truncated = cls._truncate_tool_output(result.stderr)
        stdout_note = _TRUNCATION_MARKER if stdout_truncated else ""
        stderr_note = _TRUNCATION_MARKER if stderr_truncated else ""
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
        """Format a ``WebSearchResult`` as a ``@@TOOL_RESULT`` block.

        Args:
            tool_name: Name of the invoked tool.
            result: Web search result containing query and result items.

        Returns:
            Formatted multi-line string with query, result count, and
            JSON-serialized search results.
        """
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
        truncated_note = _TRUNCATION_MARKER if truncated else ""
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
        """Format a ``WebBrowseResult`` as a ``@@TOOL_RESULT`` block.

        Args:
            tool_name: Name of the invoked tool.
            result: Web browse result containing URL, status, and content.

        Returns:
            Formatted multi-line string with URL, status code, and
            page content.
        """
        text, output_truncated = cls._truncate_tool_output(result.content)
        truncated_note = _TRUNCATION_MARKER if output_truncated else ""
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
        """Build a ValueError for a tool that is not enabled.

        Args:
            tool_name: Name of the requested tool.

        Returns:
            ValueError with a message indicating which ``--tools`` category
            must be enabled, or that the tool is unsupported.
        """
        required_category = tool_registry.category_name_for_tool(tool_name)
        if required_category:
            return ValueError(
                f"{tool_name} is disabled; re-run with --tools {required_category}"
            )
        return ValueError(f"unsupported tool: {tool_name}")

    @staticmethod
    def _pr_status_line(pr_metadata: dict[str, Any]) -> str:
        """Return a human-readable PR status line from finalization metadata.

        Args:
            pr_metadata: Dict returned by ``_finalize_repo_pr()``.

        Returns:
            A newline-wrapped status string, or empty string if the PR was
            skipped or no meaningful status is available.
        """
        pr_url = pr_metadata.get(_META_PR_URL)
        if pr_url:
            return f"\nPR created: {pr_url}\n"
        status = pr_metadata.get(_META_PR_STATUS)
        if status and status not in _PR_STATUSES_SKIPPED:
            return f"\nPR status: {status}\n"
        return ""

    def _auth_status_line(self) -> str:
        """Return a one-line auth status banner for the current provider.

        Checks whether the provider's API key environment variable is set
        and returns a formatted string like::

            [backend] provider=openai | auth=OPENAI_API_KEY (set)

        Returns:
            A single-line status string (newline-terminated).
        """
        env_name = self._hand_model.provider.api_key_env_var
        label = (
            _AUTH_PRESENT_LABEL
            if os.environ.get(env_name, "").strip()
            else _AUTH_ABSENT_LABEL
        )
        return (
            f"[{self._BACKEND_NAME}] provider={self._hand_model.provider.name}"
            f" | auth={env_name} ({label})\n"
        )

    def _run_tool_request(
        self,
        *,
        root: Path,
        tool_name: str,
        payload: dict[str, Any],
    ) -> str:
        """Dispatch a single tool request and return its formatted result.

        Args:
            root: Resolved repo root path.
            tool_name: Name of the tool to invoke.
            payload: JSON-decoded arguments for the tool.

        Returns:
            Formatted ``@@TOOL_RESULT`` block string.

        Raises:
            ValueError: If the tool is not enabled or unsupported.
            TypeError: If the tool returns an unrecognized result type.
        """
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
        """Execute all ``@@TOOL`` requests found in the AI response.

        Parses tool invocations, dispatches each through
        ``_run_tool_request``, and collects formatted ``@@TOOL_RESULT``
        blocks. Errors are caught and reported inline.

        Args:
            content: Raw AI response text containing ``@@TOOL:`` directives.

        Returns:
            Concatenated ``@@TOOL_RESULT`` blocks, or empty string if no
            tool requests were found.
        """
        root = self.repo_index.root.resolve()
        requests = self._extract_tool_requests(content)
        if not requests:
            return ""

        chunks: list[str] = []
        for tool_name, payload, error in requests:
            if error:
                chunks.append(self._format_error_result("TOOL", tool_name, error))
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
                chunks.append(self._format_error_result("TOOL", tool_name, str(exc)))
                continue
            chunks.append(result)
        return "\n\n".join(chunks).strip()

    def _apply_inline_edits(self, content: str) -> list[str]:
        """Apply ``@@FILE`` inline edits from the AI response to disk.

        Writes each extracted file block to the repo and refreshes the
        repo index when any files were changed.

        Args:
            content: Raw AI response text containing ``@@FILE:`` blocks.

        Returns:
            List of display paths for files that were successfully written.
        """
        root = self.repo_index.root.resolve()
        changed: list[str] = []
        for rel_path, body in self._extract_inline_edits(content):
            try:
                display_path = system_tools.write_text_file(root, rel_path, body)
            except ValueError:
                logger.debug("Skipping inline edit for %r: invalid path", rel_path)
                continue
            except OSError as exc:
                logger.warning("Failed to write inline edit for %r: %s", rel_path, exc)
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
        """Read the first matching bootstrap document from candidate filenames.

        Args:
            root: Resolved repo root path.
            candidates: Ordered tuple of filenames to try.

        Returns:
            Formatted document content, or empty string if none found.
        """
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

            truncated_note = _TRUNCATION_MARKER if truncated else ""
            return f"{display_path}:\n```text\n{text}\n```{truncated_note}"
        return ""

    def _build_tree_snapshot(self) -> str:
        """Build a bounded directory tree snapshot from the repo index.

        Returns:
            Formatted tree listing, capped at ``_BOOTSTRAP_TREE_MAX_ENTRIES``
            entries and ``_BOOTSTRAP_TREE_MAX_DEPTH`` levels deep.
        """
        entries: set[str] = set()
        for rel_path in sorted(self.repo_index.files):
            try:
                normalized = system_tools.normalize_relative_path(rel_path)
            except ValueError:
                logger.debug("skipping invalid path in tree snapshot: %s", rel_path)
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
        """Build the bootstrap context for the first iteration.

        Reads README and AGENT docs (from ``_README_CANDIDATES`` and
        ``_AGENT_DOC_CANDIDATES``) and appends a bounded tree snapshot.

        Returns:
            Combined bootstrap context string.
        """
        root = self.repo_index.root.resolve()
        sections: list[str] = []

        readme = self._read_bootstrap_doc(root, _README_CANDIDATES)
        if readme:
            sections.append(readme)

        agent = self._read_bootstrap_doc(root, _AGENT_DOC_CANDIDATES)
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

    _BACKEND_NAME = "basic-langgraph"

    def __init__(
        self,
        config: Any,
        repo_index: Any,
        *,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
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
        """Extract the text content from a LangGraph agent result dict.

        Args:
            result: LangGraph ``invoke`` return value containing a
                ``messages`` list.

        Returns:
            Content string from the last message, or empty string if
            no messages are present.
        """
        messages = result.get("messages") or []
        if not messages:
            return ""
        last_msg = messages[-1]
        return last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    def run(self, prompt: str) -> HandResponse:
        """Execute the LangGraph agent loop synchronously.

        Iterates up to ``max_iterations`` times, building an iteration
        prompt, invoking the LangGraph agent, applying inline edits,
        executing tool and read requests, and checking for early
        satisfaction.

        Args:
            prompt: The user task prompt.

        Returns:
            A ``HandResponse`` with concatenated iteration transcripts and
            metadata including status (``satisfied``, ``max_iterations``,
            or ``interrupted``), iteration count, and PR metadata.
        """
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
            result = self._agent.invoke(langchain_user_message(step_prompt))
            content = self._result_content(result)
            changed = self._apply_inline_edits(content)
            combined_feedback = self._collect_tool_feedback(content)
            self._append_iteration_transcript(
                transcripts,
                iteration,
                content,
                changed,
                combined_feedback,
            )
            prior = self._merge_iteration_summary(content, combined_feedback)
            if self._is_satisfied(content):
                completed = True
                break

        interrupted = self._is_interrupted()
        if interrupted:
            status = _RUN_STATUS_INTERRUPTED
        elif completed:
            status = _RUN_STATUS_SATISFIED
        else:
            status = _RUN_STATUS_MAX_ITERATIONS

        pr_metadata = self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary=prior,
        )
        message = "\n\n".join(transcripts) if transcripts else "No output produced."
        return HandResponse(
            message=message,
            metadata={
                _META_BACKEND: self._BACKEND_NAME,
                _META_MODEL: self._hand_model.model,
                _META_PROVIDER: self._hand_model.provider.name,
                "iterations": iterations,
                "status": status,
                "interrupted": str(interrupted).lower(),
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream LangGraph agent output as an async iterator.

        Yields progress lines for each iteration including auth info,
        iteration markers, file-change notifications, tool results,
        and PR status. Supports interruption between iterations.

        Args:
            prompt: The user task prompt.

        Yields:
            Progress strings suitable for incremental display.
        """
        self.reset_interrupt()
        prior = ""
        bootstrap_context = self._build_bootstrap_context()

        yield self._auth_status_line()

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
                langchain_user_message(step_prompt),
                version="v2",
            ):
                if self._is_interrupted():
                    break
                if event["event"] == _LANGCHAIN_STREAM_EVENT and event["data"].get(
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
            messages, prior, satisfied = self._process_stream_iteration(content, prompt)
            for msg in messages:
                yield msg
            if satisfied:
                return

        for msg in self._stream_max_iterations_tail(prompt, prior):
            yield msg


class BasicAtomicHand(_BasicIterativeHand):
    """Iterative Atomic-backed hand with streaming and interruption."""

    _BACKEND_NAME = "basic-atomic"

    def __init__(
        self,
        config: Any,
        repo_index: Any,
        *,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        super().__init__(config, repo_index, max_iterations=max_iterations)
        self._input_schema: type[Any] | None = None
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
        """Wrap a prompt string into the Atomic Agents input schema.

        Args:
            prompt: Text prompt for the current iteration step.

        Returns:
            ``BasicChatInputSchema`` instance with the prompt as
            ``chat_message``.
        """
        if self._input_schema is None:
            raise RuntimeError("_input_schema not initialised; call _build_agent first")
        return self._input_schema(chat_message=prompt)

    @staticmethod
    def _extract_message(response: Any) -> str:
        """Extract the text message from an Atomic Agents response.

        Args:
            response: Atomic Agents agent response object.

        Returns:
            String content from ``chat_message`` attribute if present,
            otherwise ``str(response)``.
        """
        if hasattr(response, "chat_message") and response.chat_message:
            return str(response.chat_message)
        return str(response)

    def run(self, prompt: str) -> HandResponse:
        """Execute the Atomic Agents loop synchronously.

        Iterates up to ``max_iterations`` times, building an iteration
        prompt, running the Atomic agent, applying inline edits,
        executing tool and read requests, and checking for early
        satisfaction.

        Args:
            prompt: The user task prompt.

        Returns:
            A ``HandResponse`` with concatenated iteration transcripts and
            metadata including status (``satisfied``, ``max_iterations``,
            or ``interrupted``), iteration count, and PR metadata.
        """
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
            combined_feedback = self._collect_tool_feedback(content)
            self._append_iteration_transcript(
                transcripts,
                iteration,
                content,
                changed,
                combined_feedback,
            )
            prior = self._merge_iteration_summary(content, combined_feedback)
            if self._is_satisfied(content):
                completed = True
                break

        interrupted = self._is_interrupted()
        if interrupted:
            status = _RUN_STATUS_INTERRUPTED
        elif completed:
            status = _RUN_STATUS_SATISFIED
        else:
            status = _RUN_STATUS_MAX_ITERATIONS

        pr_metadata = self._finalize_repo_pr(
            backend=self._BACKEND_NAME,
            prompt=prompt,
            summary=prior,
        )
        message = "\n\n".join(transcripts) if transcripts else "No output produced."
        return HandResponse(
            message=message,
            metadata={
                _META_BACKEND: self._BACKEND_NAME,
                _META_MODEL: self._hand_model.model,
                _META_PROVIDER: self._hand_model.provider.name,
                "iterations": iterations,
                "status": status,
                "interrupted": str(interrupted).lower(),
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream Atomic Agents output as an async iterator.

        Yields progress lines for each iteration including auth info,
        iteration markers, file-change notifications, tool results,
        and PR status. Falls back to synchronous execution via
        ``asyncio.to_thread`` when the agent raises ``AssertionError``.

        Args:
            prompt: The user task prompt.

        Yields:
            Progress strings suitable for incremental display.
        """
        self.reset_interrupt()
        prior = ""
        bootstrap_context = self._build_bootstrap_context()

        yield self._auth_status_line()

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
                delta = current[len(stream_text) :]
                stream_text = current
                if delta:
                    yield delta
                async_result = None
            except (RuntimeError, TypeError, ValueError, AttributeError, OSError):
                logger.debug("run_async raised non-AssertionError", exc_info=True)
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
                delta = current[len(stream_text) :]
                stream_text = current
                if delta:
                    yield delta
            if self._is_interrupted():
                yield "\n[interrupted]\n"
                return

            messages, prior, satisfied = self._process_stream_iteration(
                stream_text, prompt
            )
            for msg in messages:
                yield msg
            if satisfied:
                return

        for msg in self._stream_max_iterations_tail(prompt, prior):
            yield msg
