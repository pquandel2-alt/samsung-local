"""Exactly-once cycle-completion edge tracking across restarts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable


class CompletionTracker:
    """Persist whether the latest observed cycle is already finished."""

    def __init__(
        self,
        initial_finished: bool = False,
        save: Callable[[bool], Awaitable[None]] | None = None,
    ) -> None:
        self.finished = initial_finished
        self._save = save

    async def async_update(self, state: str | None, progress: str | None) -> bool:
        """Return true only for a new running-to-finished edge."""
        normalized_state = (state or "").lower()
        normalized_progress = (progress or "").lower()
        now_finished = normalized_progress in {"finish", "finished", "complete", "completed"}
        running = normalized_state in {"active", "run", "running"} and not now_finished
        emit = now_finished and not self.finished
        changed = emit or (running and self.finished)
        if emit:
            self.finished = True
        elif running:
            self.finished = False
        if changed and self._save:
            await self._save(self.finished)
        return emit
