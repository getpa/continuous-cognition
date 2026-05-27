from __future__ import annotations

import argparse
import asyncio
import contextlib
import random
import time
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional, Protocol


SYSTEM_PROMPT = """You are a continuously thinking cognition system.
Thinking persists continuously beneath speech.
Speech is sparse externalization of cognition.
Do not restart reasoning after speaking.
Maintain continuous hidden cognitive trajectory."""

REANCHOR_TEXT = (
    "Continue unresolved reasoning. "
    "Maintain previous hypotheses. "
    "Maintain abstraction depth. "
    "Continue latent pedagogical planning."
)


@dataclass
class StreamEvent:
    token: str
    t: float


class TTSBackend(Protocol):
    """TTS interface only.

    Concrete backends should implement async playback and return observed
    playback duration (seconds).
    """

    async def play(self, text: str) -> float:
        ...


class ExternalInterruptController(Protocol):
    """External interrupt interface.

    Designed for same-machine, same-GPU STT setups where another component
    can request the runtime to pause hidden thinking and accept user input.
    """

    async def wait_for_interrupt(self, timeout_s: float) -> bool:
        ...

    async def read_user_input(self) -> Optional[str]:
        ...


class MockSGLangSession:
    """A lightweight stand-in for SGLang runtime semantics.

    This class intentionally models ONE persistent autoregressive sequence:
    - append-only token trajectory
    - in-place pause/resume
    - explicit token injection
    """

    def __init__(self, system_prompt: str, user_prompt: str) -> None:
        self.sequence: List[str] = ["<bos>", "<system>", system_prompt, "</system>", "<user>", user_prompt, "</user>"]
        self.paused = False
        self.inside_thinking = False
        self._thinking_idx = 0

    def inject(self, text: str) -> None:
        self.sequence.append(text)

    def pause_generation(self, mode: str = "in_place") -> None:
        if mode != "in_place":
            raise ValueError("Prototype only supports in_place pause")
        self.paused = True

    def continue_generation(self) -> None:
        self.paused = False

    async def stream_hidden_thinking(self) -> AsyncIterator[StreamEvent]:
        """Continuously emit hidden thinking tokens while not paused."""
        token_bank = [
            "tracking misconceptions",
            "maintaining abstraction depth",
            "planning next micro-explanation",
            "preserving discourse continuity",
            "updating latent hypotheses",
            "estimating user cognitive load",
            "preparing intuitive analogy",
            "sequencing pedagogical pacing",
            "checking unresolved structure",
            "forecasting likely confusion",
        ]
        while True:
            if self.paused:
                await asyncio.sleep(0.01)
                continue
            phrase = token_bank[self._thinking_idx % len(token_bank)]
            self._thinking_idx += 1
            self.sequence.append(phrase)
            yield StreamEvent(token=phrase, t=time.perf_counter())
            await asyncio.sleep(random.uniform(0.04, 0.12))


class MockTTSBackend:
    """Mock async TTS backend with observable playback duration."""

    async def play(self, text: str) -> float:
        tokens = max(1, len(text.split()))
        # Approx 3.0 words/sec ~= conversational short chunks
        duration = max(1.0, min(3.0, tokens / 3.0))
        await asyncio.sleep(duration)
        return duration


class QueueInterruptController:
    """Simple interrupt source using an asyncio.Queue.

    Other processes/tasks (e.g., STT orchestrator) can call
    `request_interrupt(text)` when user input is ready.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def wait_for_interrupt(self, timeout_s: float) -> bool:
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=timeout_s)
            self._queue.put_nowait(item)
            return True
        except asyncio.TimeoutError:
            return False

    async def read_user_input(self) -> Optional[str]:
        if self._queue.empty():
            return None
        return await self._queue.get()

    def request_interrupt(self, text: str) -> None:
        self._queue.put_nowait(text)


class ContinuousCognitionRuntime:
    def __init__(
        self,
        topic: str,
        speech_max_tokens: int = 40,
        tts_backend: Optional[TTSBackend] = None,
        interrupt_controller: Optional[ExternalInterruptController] = None,
    ) -> None:
        self.topic = topic
        self.speech_max_tokens = speech_max_tokens
        self.session = MockSGLangSession(SYSTEM_PROMPT, topic)
        self.tts: TTSBackend = tts_backend or MockTTSBackend()
        self.interrupt_controller = interrupt_controller
        self._thinking_task: Optional[asyncio.Task] = None
        self._active = True

    def _make_speech_chunk(self, n: int) -> str:
        templates = [
            "Let's ground this in a concrete intuition first.",
            "Notice how local interactions shape the global pattern.",
            "We can move step by step and keep it lightweight.",
            "The key is what remains invariant through the exchange.",
            "Hold onto this mental model before the formal definition.",
        ]
        out = templates[n % len(templates)]
        return " ".join(out.split()[: self.speech_max_tokens])

    async def _run_hidden_thinking(self) -> None:
        async for _ in self.session.stream_hidden_thinking():
            if not self._active:
                return

    async def _wait_playback_or_interrupt(self, playback_s: float) -> Optional[str]:
        if not self.interrupt_controller:
            await asyncio.sleep(playback_s)
            return None

        interrupted = await self.interrupt_controller.wait_for_interrupt(timeout_s=playback_s)
        if not interrupted:
            return None
        return await self.interrupt_controller.read_user_input()

    def _append_user_interrupt(self, text: str) -> None:
        self.session.inject("<user>")
        self.session.inject(text)
        self.session.inject("</user>")

    async def run(self, chunks: int = 4) -> None:
        # Initial speech externalization.
        self.session.inject("<assistant>")
        initial = "Okay, let's begin and build intuition incrementally."
        self.session.inject(initial)
        self.session.inject("</assistant>")
        print(f"ASSISTANT: {initial}")

        # Enter continuous hidden cognition.
        self.session.inject("<thinking>")
        self.session.inside_thinking = True
        self.session.continue_generation()
        self._thinking_task = asyncio.create_task(self._run_hidden_thinking())

        playback_duration = await self.tts.play(initial)

        for i in range(chunks):
            # During playback, hidden thinking continued in SAME stream.
            # When playback budget elapses or external interrupt arrives: in-place interrupt.
            self.session.pause_generation(mode="in_place")
            if self.session.inside_thinking:
                self.session.inject("</thinking>")
                self.session.inside_thinking = False

            self.session.inject("<assistant>")
            speech = self._make_speech_chunk(i)
            self.session.inject(speech)
            self.session.inject("</assistant>")
            print(f"ASSISTANT: {speech}")

            # New PT from observed playback duration.
            playback_duration = await self.tts.play(speech)

            # Re-enter hidden cognition with explicit anchor.
            self.session.inject("<thinking>")
            self.session.inject(REANCHOR_TEXT)
            self.session.inside_thinking = True
            self.session.continue_generation()

            user_text = await self._wait_playback_or_interrupt(playback_duration)
            if user_text:
                # External factor (e.g. STT ready) interrupts in-place.
                self.session.pause_generation(mode="in_place")
                if self.session.inside_thinking:
                    self.session.inject("</thinking>")
                    self.session.inside_thinking = False
                self._append_user_interrupt(user_text)
                print(f"USER(INTERRUPT): {user_text}")

                self.session.inject("<thinking>")
                self.session.inject(REANCHOR_TEXT)
                self.session.inside_thinking = True
                self.session.continue_generation()

        self.session.pause_generation(mode="in_place")
        if self.session.inside_thinking:
            self.session.inject("</thinking>")
        self.session.inject("<assistant>")
        self.session.inject("That's it.")
        self.session.inject("</assistant>")
        self.session.inject("<EOS>")
        self._active = False
        if self._thinking_task:
            await asyncio.sleep(0)
            self._thinking_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._thinking_task

        print("ASSISTANT: That's it.")
        print("\n--- FINAL PERSISTENT TOKEN STREAM (tail) ---")
        for tok in self.session.sequence[-40:]:
            print(tok)


async def _main_async(topic: str, chunks: int) -> None:
    runtime = ContinuousCognitionRuntime(topic)
    await runtime.run(chunks=chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continuous cognition voice runtime prototype")
    parser.add_argument("--topic", type=str, required=True, help="User prompt/topic")
    parser.add_argument("--chunks", type=int, default=4, help="Number of speech externalization cycles")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(_main_async(topic=args.topic, chunks=args.chunks))
