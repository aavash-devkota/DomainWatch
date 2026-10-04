from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ..core.models import Event

Handler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subs[event_type].append(handler)
        self._subs["*"]  # ensure wildcard list exists

    def subscribe_all(self, handler: Handler) -> None:
        self._subs["*"].append(handler)

    def emit(self, event: Event) -> None:
        for h in list(self._subs.get(event.type, [])):
            try:
                h(event)
            except Exception as exc:  # never let a notifier kill monitoring
                print(f"[eventbus] handler error: {exc}")
        for h in list(self._subs.get("*", [])):
            try:
                h(event)
            except Exception as exc:
                print(f"[eventbus] handler error: {exc}")
