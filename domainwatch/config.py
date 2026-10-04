from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml

DEFAULT_CONFIG = Path.home() / ".domainwatch" / "config.yaml"

_env_re = re.compile(r"\$\{([^}^{]+)\}")


def _expand(obj):
    if isinstance(obj, str):
        return _env_re.sub(lambda m: os.environ.get(m.group(1), ""), obj)
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(v) for v in obj]
    return obj


def load_config(path: Optional[str | Path] = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.exists():
        return {}
    with p.open() as f:
        data = yaml.safe_load(f) or {}
    return _expand(data)


def get(cfg: dict, *keys, default=None):
    cur: Any = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
