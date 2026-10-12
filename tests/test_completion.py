from __future__ import annotations

from custom_components.samsung_local.completion import CompletionTracker


async def test_completion_is_emitted_once_and_rearms_on_new_cycle() -> None:
    saved: list[bool] = []

    async def save(value: bool) -> None:
        saved.append(value)

    tracker = CompletionTracker(save=save)
    assert not await tracker.async_update("active", "wash")
    assert await tracker.async_update("idle", "finish")
    assert not await tracker.async_update("idle", "finish")
    assert not await tracker.async_update("active", "wash")
    assert await tracker.async_update("idle", "finish")
    assert saved == [True, False, True]


async def test_restart_does_not_duplicate_finished_event() -> None:
    tracker = CompletionTracker(initial_finished=True)
    assert not await tracker.async_update("idle", "finish")
