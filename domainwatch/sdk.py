"""DomainWatch Plugin SDK.

Third parties can ship:
  - a provider plugin (package domainwatch-provider-xyz) exposing
    entry point group "domainwatch.providers" -> callable returning a Provider
  - a notifier plugin (domainwatch-notifier-xyz) exposing
    entry point group "domainwatch.notifiers" -> callable returning a Notifier
"""
from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable, Protocol, runtime_checkable

from .core.models import DomainState, Event
from .providers.base import Provider


@runtime_checkable
class DomainWatchProvider(Protocol):
    name: str

    def check(self, domain: str) -> DomainState: ...


@runtime_checkable
class NotifierPlugin(Protocol):
    name: str

    def send(self, event: Event) -> None: ...


def load_provider_plugins() -> list[Provider]:
    out: list[Provider] = []
    try:
        eps = entry_points(group="domainwatch.providers")
    except TypeError:  # older python
        eps = entry_points().get("domainwatch.providers", [])
    for ep in eps:
        try:
            factory: Callable[[], Provider] = ep.load()
            out.append(factory())
        except Exception as e:
            print(f"[sdk] provider plugin {ep.name} failed: {e}")
    return out


def load_notifier_plugins() -> list[NotifierPlugin]:
    out: list[NotifierPlugin] = []
    try:
        eps = entry_points(group="domainwatch.notifiers")
    except TypeError:
        eps = entry_points().get("domainwatch.notifiers", [])
    for ep in eps:
        try:
            factory: Callable[[], NotifierPlugin] = ep.load()
            out.append(factory())
        except Exception as e:
            print(f"[sdk] notifier plugin {ep.name} failed: {e}")
    return out
