"""Load server + FortiGate configuration from a YAML file into environment variables.

The config file (passed with ``--config``) is the single source of truth for the
server. Each top-level section maps to a group of settings whose keys are
environment-variable names, so the existing client and integrations (which read
``os.environ`` at import time) work unchanged.

Example ``config.yaml``::

    server:
      host: 0.0.0.0
      port: 5752
    fortigate:
      FORTIGATE_HOST: 172.18.7.14
      FORTIGATE_API_TOKEN: <token>
      FORTIGATE_READ_ONLY: true
    k8s:            # optional, enables the Kubernetes tools
      K8S_KUBECONFIG: ~/.kube/config
    proxmox:        # optional, enables the Proxmox tools
      PROXMOX_HOST: pve.example.com
      PROXMOX_USER: mcp
      PROXMOX_TOKEN_NAME: mcp
      PROXMOX_TOKEN_VALUE: <value>

``load_config`` must be called **before** importing :mod:`mcp_fortigate.client`
and the integrations, because those modules read the environment at import time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5752


def load_config(path: str | Path) -> dict[str, Any]:
    """Read the YAML config and export its values as environment variables.

    Returns the parsed config dict. Values already present in the environment
    are overridden by the config file, so the file is authoritative.
    """
    path = Path(path)
    if not path.is_file():
        print(f"Error: config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"Error: could not parse {path}: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(cfg, dict):
        print(f"Error: {path} must contain a mapping at the top level", file=sys.stderr)
        sys.exit(1)

    for section, values in cfg.items():
        if section == "server":
            continue  # handled by server_settings()
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if value is None:
                continue
            os.environ[str(key).strip()] = _to_env(value)
    return cfg


def _to_env(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def server_settings(cfg: dict[str, Any]) -> tuple[str, int]:
    """Return ``(host, port)`` from the optional ``server`` section, with defaults."""
    server = cfg.get("server") or {}
    if not isinstance(server, dict):
        server = {}
    host = server.get("host", DEFAULT_HOST)
    port = server.get("port", DEFAULT_PORT)
    try:
        return str(host), int(port)
    except (TypeError, ValueError) as e:
        print(f"Error: invalid 'server.host'/'server.port' in config: {e}", file=sys.stderr)
        sys.exit(1)