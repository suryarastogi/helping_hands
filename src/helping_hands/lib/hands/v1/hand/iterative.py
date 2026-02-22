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
import re
from collections.abc import AsyncIterator
from typing import Any

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.model_provider import (
    build_atomic_client,
    build_langchain_chat_model,
    resolve_hand_model,
)
from helping_hands.lib.meta.tools import filesystem as system_tools


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
        config: Any,
        repo_index: Any,
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
