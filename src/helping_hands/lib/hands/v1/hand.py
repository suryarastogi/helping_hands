"""Unified Hand interface with LangGraph, Atomic Agents, and CLI backends.

A Hand is the AI agent that operates on a repo. This module defines:
  - ``Hand``: abstract protocol that all backends implement.
  - ``HandResponse``: common response container.
  - ``LangGraphHand``: backend powered by LangChain / LangGraph.
  - ``AtomicHand``: backend powered by atomic-agents.
  - ``BasicLangGraphHand``: iterative LangGraph backend with interruption.
  - ``BasicAtomicHand``: iterative Atomic backend with interruption.
  - ``E2EHand``: concrete end-to-end hand (clone/edit/commit/push/PR).
  - ``ClaudeCodeHand``: backend that invokes Claude Code via a terminal/bash call.
  - ``CodexCLIHand``: backend that invokes Codex CLI via a terminal/bash call.
  - ``GeminiCLIHand``: backend that invokes Gemini CLI via a terminal/bash call.
"""

from __future__ import annotations

import abc
import asyncio
import os
import re
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from helping_hands.lib.config import Config
    from helping_hands.lib.repo import RepoIndex


# ---------------------------------------------------------------------------
# Common types
# ---------------------------------------------------------------------------


@dataclass
class HandResponse:
    """Standardised response from any Hand backend."""

    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Hand protocol
# ---------------------------------------------------------------------------


class Hand(abc.ABC):
    """Abstract base for all Hand backends.

    Every backend receives the same repo context and config, and exposes
    ``run`` (sync) and ``stream`` (async generator) for interaction.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        self.config = config
        self.repo_index = repo_index
        self._interrupt_event = Event()
        self.auto_pr = True

    def _build_system_prompt(self) -> str:
        """Build a system prompt that includes repo context."""
        file_list = "\n".join(f"  - {f}" for f in self.repo_index.files[:200])
        return (
            "You are a helpful coding assistant working on a repository.\n"
            f"Repo root: {self.repo_index.root}\n"
            f"Files ({len(self.repo_index.files)} total):\n{file_list}\n\n"
            "Follow the repo's conventions. Propose focused, reviewable "
            "changes. Explain your reasoning."
        )

    @abc.abstractmethod
    def run(self, prompt: str) -> HandResponse:
        """Send a prompt and get a complete response."""

    @abc.abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Send a prompt and yield response chunks as they arrive."""

    def interrupt(self) -> None:
        """Request cooperative interruption for long-running runs/streams."""
        self._interrupt_event.set()

    def reset_interrupt(self) -> None:
        """Clear any pending interruption request."""
        self._interrupt_event.clear()

    def _is_interrupted(self) -> bool:
        return self._interrupt_event.is_set()

    @staticmethod
    def _default_base_branch() -> str:
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", "main")

    @staticmethod
    def _run_git_read(repo_dir: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    @classmethod
    def _github_repo_from_origin(cls, repo_dir: Path) -> str:
        remote = cls._run_git_read(repo_dir, "remote", "get-url", "origin")
        if not remote:
            return ""
        patterns = (
            r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
            r"^git@github\.com:(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
            r"^ssh://git@github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
        )
        for pattern in patterns:
            match = re.match(pattern, remote)
            if match:
                return match.group("repo")
        return ""

    @staticmethod
    def _build_generic_pr_body(
        *,
        backend: str,
        prompt: str,
        summary: str,
        commit_sha: str,
        stamp_utc: str,
    ) -> str:
        return (
            f"Automated update from `{backend}`.\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- prompt: {prompt}\n"
            f"- commit: `{commit_sha}`\n\n"
            "## Summary\n\n"
            f"{summary.strip() or 'No summary provided.'}\n"
        )

    @staticmethod
    def _configure_authenticated_push_remote(
        repo_dir: Path, repo: str, token: str
    ) -> None:
        push_url = f"https://x-access-token:{token}@github.com/{repo}.git"
        result = subprocess.run(
            ["git", "remote", "set-url", "--push", "origin", push_url],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown git error"
            msg = f"failed to configure authenticated push remote: {stderr}"
            raise RuntimeError(msg)

    def _finalize_repo_pr(
        self,
        *,
        backend: str,
        prompt: str,
        summary: str,
    ) -> dict[str, str]:
        metadata = {
            "auto_pr": str(self.auto_pr).lower(),
            "pr_status": "not_attempted",
            "pr_url": "",
            "pr_number": "",
            "pr_branch": "",
            "pr_commit": "",
        }
        if not self.auto_pr:
            metadata["pr_status"] = "disabled"
            return metadata

        repo_dir = self.repo_index.root.resolve()
        if not repo_dir.is_dir():
            metadata["pr_status"] = "no_repo"
            return metadata

        inside_work_tree = self._run_git_read(
            repo_dir, "rev-parse", "--is-inside-work-tree"
        )
        if inside_work_tree != "true":
            metadata["pr_status"] = "not_git_repo"
            return metadata

        has_changes = self._run_git_read(repo_dir, "status", "--porcelain")
        if not has_changes:
            metadata["pr_status"] = "no_changes"
            return metadata

        repo = self._github_repo_from_origin(repo_dir)
        if not repo:
            metadata["pr_status"] = "no_github_origin"
            return metadata

        from helping_hands.lib.github import GitHubClient

        try:
            with GitHubClient() as gh:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", "helping-hands[bot]"
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    "helping-hands-bot@users.noreply.github.com",
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)

                branch = f"helping-hands/{backend}-{uuid4().hex[:8]}"
                gh.create_branch(repo_dir, branch)
                commit_sha = gh.add_and_commit(
                    repo_dir,
                    f"feat({backend}): apply hand updates",
                )
                self._configure_authenticated_push_remote(repo_dir, repo, gh.token)
                prior_prompt = os.environ.get("GIT_TERMINAL_PROMPT")
                prior_gcm_interactive = os.environ.get("GCM_INTERACTIVE")
                os.environ["GIT_TERMINAL_PROMPT"] = "0"
                os.environ["GCM_INTERACTIVE"] = "never"
                try:
                    gh.push(repo_dir, branch=branch, set_upstream=True)
                finally:
                    if prior_prompt is None:
                        os.environ.pop("GIT_TERMINAL_PROMPT", None)
                    else:
                        os.environ["GIT_TERMINAL_PROMPT"] = prior_prompt
                    if prior_gcm_interactive is None:
                        os.environ.pop("GCM_INTERACTIVE", None)
                    else:
                        os.environ["GCM_INTERACTIVE"] = prior_gcm_interactive

                base_branch = self._default_base_branch()
                try:
                    repo_obj = gh.get_repo(repo)
                    if getattr(repo_obj, "default_branch", ""):
                        base_branch = str(repo_obj.default_branch)
                except Exception:
                    pass

                stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
                pr = gh.create_pr(
                    repo,
                    title=f"feat({backend}): automated hand update",
                    body=self._build_generic_pr_body(
                        backend=backend,
                        prompt=prompt,
                        summary=summary,
                        commit_sha=commit_sha,
                        stamp_utc=stamp,
                    ),
                    head=branch,
                    base=base_branch,
                )
                metadata.update(
                    {
                        "pr_status": "created",
                        "pr_url": pr.url,
                        "pr_number": str(pr.number),
                        "pr_branch": branch,
                        "pr_commit": commit_sha,
                    }
                )
                return metadata
        except ValueError as exc:
            metadata["pr_status"] = "missing_token"
            metadata["pr_error"] = str(exc)
            return metadata
        except RuntimeError as exc:
            metadata["pr_status"] = "git_error"
            metadata["pr_error"] = str(exc)
            return metadata
        except Exception as exc:
            metadata["pr_status"] = "error"
            metadata["pr_error"] = str(exc)
            return metadata


# ---------------------------------------------------------------------------
# LangGraph backend
# ---------------------------------------------------------------------------


class LangGraphHand(Hand):
    """Hand backed by LangChain / LangGraph ``create_react_agent``.

    Requires the ``langchain`` extra to be installed.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(
            model_name=self.config.model,
            streaming=True,
        )
        system_prompt = self._build_system_prompt()
        return create_react_agent(
            model=llm,
            tools=[],
            prompt=system_prompt,
        )

    def run(self, prompt: str) -> HandResponse:
        result = self._agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        last_msg = result["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        pr_metadata = self._finalize_repo_pr(
            backend="langgraph",
            prompt=prompt,
            summary=content,
        )
        return HandResponse(
            message=content,
            metadata={
                "backend": "langgraph",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        parts: list[str] = []
        async for event in self._agent.astream_events(
            {"messages": [{"role": "user", "content": prompt}]},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream" and event["data"].get("chunk"):
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    text = str(chunk.content)
                    parts.append(text)
                    yield text
        pr_metadata = self._finalize_repo_pr(
            backend="langgraph",
            prompt=prompt,
            summary="".join(parts),
        )
        if pr_metadata.get("pr_url"):
            yield f"\nPR created: {pr_metadata['pr_url']}\n"


# ---------------------------------------------------------------------------
# Atomic Agents backend
# ---------------------------------------------------------------------------


class AtomicHand(Hand):
    """Hand backed by the atomic-agents framework.

    Requires the ``atomic`` extra to be installed.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)
        self._input_schema: type[Any] = None  # type: ignore[assignment]
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        import instructor
        import openai
        from atomic_agents import AgentConfig, AtomicAgent, BasicChatInputSchema
        from atomic_agents.context import (
            ChatHistory,
            SystemPromptGenerator,
        )

        self._input_schema = BasicChatInputSchema

        client = instructor.from_openai(openai.OpenAI())
        history = ChatHistory()
        prompt_gen = SystemPromptGenerator(
            background=[self._build_system_prompt()],
        )
        return AtomicAgent(
            config=AgentConfig(
                client=client,
                model=self.config.model,
                history=history,
                system_prompt_generator=prompt_gen,
            )
        )

    def _make_input(self, prompt: str) -> Any:
        """Build an input schema instance. Uses mock-safe stored class."""
        return self._input_schema(chat_message=prompt)

    def run(self, prompt: str) -> HandResponse:
        response = self._agent.run(self._make_input(prompt))
        message = response.chat_message
        pr_metadata = self._finalize_repo_pr(
            backend="atomic",
            prompt=prompt,
            summary=message,
        )
        return HandResponse(
            message=message,
            metadata={
                "backend": "atomic",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        parts: list[str] = []
        user_input = self._make_input(prompt)
        try:
            async_result = self._agent.run_async(user_input)
        except AssertionError:
            partial = await asyncio.to_thread(self._agent.run, user_input)
            if hasattr(partial, "chat_message") and partial.chat_message:
                text = str(partial.chat_message)
                parts.append(text)
                yield text
            async_result = None
        except Exception:
            raise
        if async_result is None:
            pass
        elif hasattr(async_result, "__aiter__"):
            async for partial in async_result:
                if hasattr(partial, "chat_message") and partial.chat_message:
                    text = str(partial.chat_message)
                    parts.append(text)
                    yield text
        else:
            try:
                partial = await async_result
            except AssertionError:
                partial = await asyncio.to_thread(self._agent.run, user_input)
            if hasattr(partial, "chat_message") and partial.chat_message:
                text = str(partial.chat_message)
                parts.append(text)
                yield text
        pr_metadata = self._finalize_repo_pr(
            backend="atomic",
            prompt=prompt,
            summary="".join(parts),
        )
        if pr_metadata.get("pr_url"):
            yield f"\nPR created: {pr_metadata['pr_url']}\n"


# ---------------------------------------------------------------------------
# Basic iterative backends
# ---------------------------------------------------------------------------


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
    _MAX_READ_CHARS = 12000

    def __init__(
        self,
        config: Config,
        repo_index: RepoIndex,
        *,
        max_iterations: int = 6,
    ) -> None:
        super().__init__(config, repo_index)
        self.max_iterations = max(1, max_iterations)

    @staticmethod
    def _build_iteration_prompt(
        *,
        prompt: str,
        iteration: int,
        max_iterations: int,
        previous_summary: str,
    ) -> str:
        previous = previous_summary.strip() or "none"
        return (
            f"Task request: {prompt}\n\n"
            f"Iteration: {iteration}/{max_iterations}\n"
            f"Previous iteration summary: {previous}\n\n"
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
            "Read results are returned as @@READ_RESULT blocks in the next "
            "iteration summary.\n"
            "At the end of your response include exactly one line in this form:\n"
            "SATISFIED: yes|no\n"
            "Use SATISFIED: yes only when the task is fully complete.\n"
        )

    @staticmethod
    def _is_satisfied(content: str) -> bool:
        match = re.search(r"SATISFIED:\s*(yes|no)", content, flags=re.IGNORECASE)
        if match:
            return match.group(1).lower() == "yes"
        return False

    @classmethod
    def _extract_inline_edits(cls, content: str) -> list[tuple[str, str]]:
        return [
            (m.group("path").strip(), m.group("content"))
            for m in cls._EDIT_PATTERN.finditer(content)
        ]

    @classmethod
    def _extract_read_requests(cls, content: str) -> list[str]:
        explicit = [
            m.group("path").strip() for m in cls._READ_PATTERN.finditer(content)
        ]
        if explicit:
            return explicit
        return [
            m.group("path").strip()
            for m in cls._READ_FALLBACK_PATTERN.finditer(content)
        ]

    @staticmethod
    def _normalize_relative_path(rel_path: str) -> str:
        normalized = rel_path.strip().replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized

    def _resolve_repo_target(self, rel_path: str) -> Path | None:
        root = self.repo_index.root.resolve()
        normalized = self._normalize_relative_path(rel_path)
        if not normalized or normalized.startswith("/"):
            return None
        target = (root / normalized).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return None
        return target

    @staticmethod
    def _merge_iteration_summary(content: str, read_feedback: str) -> str:
        if not read_feedback:
            return content
        return f"{content}\n\nTool results:\n{read_feedback}"

    def _execute_read_requests(self, content: str) -> str:
        root = self.repo_index.root.resolve()
        requests = list(dict.fromkeys(self._extract_read_requests(content)))
        if not requests:
            return ""

        chunks: list[str] = []
        for rel_path in requests:
            target = self._resolve_repo_target(rel_path)
            if target is None:
                chunks.append(f"@@READ_RESULT: {rel_path}\nERROR: invalid path")
                continue
            if not target.exists():
                chunks.append(f"@@READ_RESULT: {rel_path}\nERROR: file not found")
                continue
            if target.is_dir():
                chunks.append(f"@@READ_RESULT: {rel_path}\nERROR: path is a directory")
                continue
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                chunks.append(
                    f"@@READ_RESULT: {rel_path}\nERROR: file is not UTF-8 text"
                )
                continue

            truncated = len(text) > self._MAX_READ_CHARS
            if truncated:
                text = text[: self._MAX_READ_CHARS]
            display_path = target.relative_to(root).as_posix()
            truncated_note = "\n[truncated]" if truncated else ""
            chunks.append(
                f"@@READ_RESULT: {display_path}\n```text\n{text}\n```{truncated_note}"
            )
        return "\n\n".join(chunks).strip()

    def _apply_inline_edits(self, content: str) -> list[str]:
        root = self.repo_index.root.resolve()
        changed: list[str] = []
        for rel_path, body in self._extract_inline_edits(content):
            target = self._resolve_repo_target(rel_path)
            if target is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            changed.append(str(target.relative_to(root)))
        if changed:
            self.repo_index = self.repo_index.from_path(root)
        return changed


class BasicLangGraphHand(_BasicIterativeHand):
    """Iterative LangGraph-backed hand with streaming and interruption."""

    def __init__(
        self,
        config: Config,
        repo_index: RepoIndex,
        *,
        max_iterations: int = 6,
    ) -> None:
        super().__init__(config, repo_index, max_iterations=max_iterations)
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(
            model_name=self.config.model,
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
            )
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": step_prompt}]}
            )
            content = self._result_content(result)
            changed = self._apply_inline_edits(content)
            read_feedback = self._execute_read_requests(content)
            transcripts.append(f"[iteration {iteration}]\n{content}")
            if changed:
                transcripts.append(f"[files updated] {', '.join(changed)}")
            if read_feedback:
                transcripts.append(f"[tool results]\n{read_feedback}")
            prior = self._merge_iteration_summary(content, read_feedback)
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
                "model": self.config.model,
                "iterations": iterations,
                "status": status,
                "interrupted": str(interrupted).lower(),
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.reset_interrupt()
        prior = ""

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
            if read_feedback:
                yield f"\n[tool results]\n{read_feedback}\n"
            prior = self._merge_iteration_summary(content, read_feedback)
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
        config: Config,
        repo_index: RepoIndex,
        *,
        max_iterations: int = 6,
    ) -> None:
        super().__init__(config, repo_index, max_iterations=max_iterations)
        self._input_schema: type[Any] = None  # type: ignore[assignment]
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        import instructor
        import openai
        from atomic_agents import AgentConfig, AtomicAgent, BasicChatInputSchema
        from atomic_agents.context import (
            ChatHistory,
            SystemPromptGenerator,
        )

        self._input_schema = BasicChatInputSchema

        client = instructor.from_openai(openai.OpenAI())
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
                model=self.config.model,
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
            )
            response = self._agent.run(self._make_input(step_prompt))
            content = self._extract_message(response)
            changed = self._apply_inline_edits(content)
            read_feedback = self._execute_read_requests(content)
            transcripts.append(f"[iteration {iteration}]\n{content}")
            if changed:
                transcripts.append(f"[files updated] {', '.join(changed)}")
            if read_feedback:
                transcripts.append(f"[tool results]\n{read_feedback}")
            prior = self._merge_iteration_summary(content, read_feedback)
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
                "model": self.config.model,
                "iterations": iterations,
                "status": status,
                "interrupted": str(interrupted).lower(),
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        self.reset_interrupt()
        prior = ""

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
            if read_feedback:
                yield f"\n[tool results]\n{read_feedback}\n"
            prior = self._merge_iteration_summary(stream_text, read_feedback)
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


# ---------------------------------------------------------------------------
# End-to-end backend (minimal working flow)
# ---------------------------------------------------------------------------


class E2EHand(Hand):
    """Minimal end-to-end hand for validating clone/edit/PR workflow."""

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    @staticmethod
    def _safe_repo_dir(repo: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", repo.strip("/"))

    @staticmethod
    def _work_base() -> Path:
        root = os.environ.get("HELPING_HANDS_WORK_ROOT", ".")
        return Path(root).expanduser()

    @staticmethod
    def _default_base_branch() -> str:
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", "main")

    @staticmethod
    def _build_e2e_pr_comment(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        # E2E is deterministic; production hands should provide AI-authored
        # PR summaries/comments when they own the PR workflow.
        return (
            "## helping_hands E2E update\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- commit: `{commit_sha}`\n"
            f"- prompt: {prompt}\n"
        )

    @staticmethod
    def _build_e2e_pr_body(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        return (
            "Automated E2E validation PR.\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- prompt: {prompt}\n"
            f"- commit: `{commit_sha}`\n"
        )

    def run(
        self,
        prompt: str,
        hand_uuid: str | None = None,
        pr_number: int | None = None,
        dry_run: bool = False,
    ) -> HandResponse:
        from helping_hands.lib.github import GitHubClient

        repo = self.config.repo.strip()
        if not repo:
            raise ValueError("E2EHand requires config.repo set to a GitHub owner/repo.")

        hand_uuid = hand_uuid or str(uuid4())
        safe_repo = self._safe_repo_dir(self.config.repo)
        hand_root = self._work_base() / hand_uuid
        repo_dir = hand_root / "git" / safe_repo
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        base_branch = self._default_base_branch()
        branch = f"helping-hands/e2e-{hand_uuid[:8]}"
        e2e_file = "HELPING_HANDS_E2E.md"
        e2e_path = repo_dir / e2e_file

        with GitHubClient() as gh:
            pr_url = ""
            resumed_pr = False
            pr_info: dict[str, Any] | None = None
            if pr_number is not None:
                pr_info = gh.get_pr(repo, pr_number)
                base_branch = str(pr_info["base"])
                pr_url = str(pr_info["url"])
                if not dry_run:
                    branch = str(pr_info["head"])
                    resumed_pr = True

            gh.clone(repo, repo_dir, branch=base_branch, depth=1)
            repo_dir.mkdir(parents=True, exist_ok=True)
            if resumed_pr:
                gh.fetch_branch(repo_dir, branch)
                gh.switch_branch(repo_dir, branch)
            else:
                gh.create_branch(repo_dir, branch)

            stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
            e2e_path.write_text(
                (
                    "# helping_hands E2E marker\n\n"
                    f"- hand_uuid: `{hand_uuid}`\n"
                    f"- prompt: {prompt}\n"
                    f"- timestamp_utc: {stamp}\n"
                ),
                encoding="utf-8",
            )
            commit_sha = ""
            final_pr_number = pr_number
            if not dry_run:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", "helping-hands[bot]"
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    "helping-hands-bot@users.noreply.github.com",
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)
                commit_sha = gh.add_and_commit(
                    repo_dir,
                    "test(e2e): minimal change from E2EHand",
                    paths=[e2e_file],
                )
                gh.push(repo_dir, branch=branch, set_upstream=True)
                pr_body = self._build_e2e_pr_body(
                    hand_uuid=hand_uuid,
                    prompt=prompt,
                    stamp_utc=stamp,
                    commit_sha=commit_sha,
                )
                if resumed_pr:
                    final_pr_number = pr_number
                else:
                    pr = gh.create_pr(
                        repo,
                        title="test(e2e): minimal edit by helping_hands",
                        body=pr_body,
                        head=branch,
                        base=base_branch,
                    )
                    pr_url = pr.url
                    final_pr_number = pr.number
                if final_pr_number is not None:
                    gh.update_pr_body(repo, final_pr_number, body=pr_body)
                    gh.upsert_pr_comment(
                        repo,
                        final_pr_number,
                        body=self._build_e2e_pr_comment(
                            hand_uuid=hand_uuid,
                            prompt=prompt,
                            stamp_utc=stamp,
                            commit_sha=commit_sha,
                        ),
                        marker="<!-- helping_hands:e2e-status -->",
                    )

        if dry_run:
            message = "E2EHand dry run complete. No push/PR performed."
        else:
            message = f"E2EHand complete. PR: {pr_url}"
        return HandResponse(
            message=message,
            metadata={
                "backend": "e2e",
                "model": self.config.model,
                "hand_uuid": hand_uuid,
                "hand_root": str(hand_root),
                "repo": repo,
                "workspace": str(repo_dir),
                "branch": branch,
                "base_branch": base_branch,
                "commit": commit_sha,
                "pr_number": "" if final_pr_number is None else str(final_pr_number),
                "pr_url": pr_url,
                "resumed_pr": str(resumed_pr).lower(),
                "dry_run": str(dry_run).lower(),
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield self.run(prompt).message


# ---------------------------------------------------------------------------
# Claude Code backend (scaffolding)
# ---------------------------------------------------------------------------


class ClaudeCodeHand(Hand):
    """Hand backed by Claude Code via a terminal/bash invocation.

    This backend would run the Claude Code CLI (or equivalent) as a
    subprocess: e.g. a terminal/bash call that passes the repo path and
    user prompt, then captures stdout/stderr. Not yet implemented; this
    class is scaffolding for future integration.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="claudecode",
            prompt=prompt,
            summary="ClaudeCode hand not yet implemented.",
        )
        return HandResponse(
            message="ClaudeCode hand not yet implemented.",
            metadata={
                "backend": "claudecode",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "ClaudeCode hand not yet implemented."


# ---------------------------------------------------------------------------
# Codex CLI backend (scaffolding)
# ---------------------------------------------------------------------------


class CodexCLIHand(Hand):
    """Hand backed by Codex CLI via a terminal/bash invocation.

    This backend would run the Codex CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="codexcli",
            prompt=prompt,
            summary="CodexCLI hand not yet implemented.",
        )
        return HandResponse(
            message="CodexCLI hand not yet implemented.",
            metadata={
                "backend": "codexcli",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "CodexCLI hand not yet implemented."


# ---------------------------------------------------------------------------
# Gemini CLI backend (scaffolding)
# ---------------------------------------------------------------------------


class GeminiCLIHand(Hand):
    """Hand backed by Gemini CLI via a terminal/bash invocation.

    This backend would run the Gemini CLI as a subprocess with repo context
    and the user prompt, then capture stdout/stderr. Not yet implemented;
    this class is scaffolding for future integration.
    """

    def __init__(self, config: Config, repo_index: RepoIndex) -> None:
        super().__init__(config, repo_index)

    def run(self, prompt: str) -> HandResponse:
        pr_metadata = self._finalize_repo_pr(
            backend="geminicli",
            prompt=prompt,
            summary="GeminiCLI hand not yet implemented.",
        )
        return HandResponse(
            message="GeminiCLI hand not yet implemented.",
            metadata={
                "backend": "geminicli",
                "model": self.config.model,
                **pr_metadata,
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield "GeminiCLI hand not yet implemented."
