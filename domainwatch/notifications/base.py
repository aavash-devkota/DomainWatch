from __future__ import annotations

import abc
import json
import urllib.request

from ..core.models import Event


class Notifier(abc.ABC):
    name = "base"

    @abc.abstractmethod
    def send(self, event: Event) -> None: ...


class ConsoleNotifier(Notifier):
    name = "console"

    def send(self, event: Event) -> None:
        print(f"🔔 {event.pretty()}")


def _post(url: str, payload: dict, headers=None) -> None:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    urllib.request.urlopen(req, timeout=10).read()


class WebhookNotifier(Notifier):
    name = "webhook"

    def __init__(self, url: str):
        self.url = url

    def send(self, event: Event) -> None:
        _post(self.url, {"type": event.type, "domain": event.domain, "message": event.message})


class DiscordNotifier(WebhookNotifier):
    name = "discord"

    def send(self, event: Event) -> None:
        _post(self.url, {"content": f"**{event.type}** — {event.message}"})


class NtfyNotifier(Notifier):
    name = "ntfy"

    def __init__(self, topic_url: str):
        self.topic_url = topic_url

    def send(self, event: Event) -> None:
        req = urllib.request.Request(self.topic_url, data=event.message.encode(),
                                     headers={"Title": event.type})
        urllib.request.urlopen(req, timeout=10).read()


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, token: str, chat_id: str):
        self.token, self.chat_id = token, chat_id

    def send(self, event: Event) -> None:
        _post(f"https://api.telegram.org/bot{self.token}/sendMessage",
              {"chat_id": self.chat_id, "text": f"{event.type}: {event.message}"})


def build_notifiers(cfg: dict) -> list[Notifier]:
    out: list[Notifier] = [ConsoleNotifier()]
    n = cfg.get("notifications", {}) or {}
    try:
        if n.get("webhook", {}).get("enabled") and n["webhook"].get("url"):
            out.append(WebhookNotifier(n["webhook"]["url"]))
        if n.get("discord", {}).get("enabled") and n["discord"].get("webhook"):
            out.append(DiscordNotifier(n["discord"]["webhook"]))
        if n.get("ntfy", {}).get("enabled") and n["ntfy"].get("topic"):
            out.append(NtfyNotifier(n["ntfy"]["topic"]))
        if n.get("telegram", {}).get("enabled") and n["telegram"].get("token"):
            out.append(TelegramNotifier(n["telegram"]["token"], str(n["telegram"].get("chat_id", ""))))
    except Exception as e:
        print(f"[notifications] config error: {e}")
    return out
