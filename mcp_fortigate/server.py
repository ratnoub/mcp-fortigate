#!/usr/bin/env python3
"""FortiGate MCP Server (FastMCP, streamable HTTP).

The server is driven entirely by a YAML config file (``--config``) and serves the
MCP protocol over streamable HTTP so a client only needs to point at
``http://<ip>:5752/mcp``.

Usage::

    mcp-fortigate --config config.yaml                 # foreground, 0.0.0.0:5752
    mcp-fortigate --config config.yaml --daemon        # detached in the background
    mcp-fortigate --stop                               # stop a running daemon
    mcp-fortigate --config config.yaml --host 127.0.0.1 --port 9000
    python -m mcp_fortigate --config config.yaml

Configuration lives in the YAML file (see ``config.example.yaml``); the ``fortigate``
section maps to the ``FORTIGATE_*`` settings the REST client reads.
"""

from __future__ import annotations

import argparse
import json
import keyword
import sys
from contextlib import asynccontextmanager
from typing import Any

import jsonschema
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.function_tool import FunctionTool

from . import __version__
from . import config as config_mod
from . import daemon

# JSON-Schema type -> Python annotation used for the generated tool signature.
_TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def _py_type(prop: dict[str, Any]) -> str:
    t = prop.get("type")
    if isinstance(t, list):
        t = t[0] if t else None
    return _TYPE_MAP.get(t, "Any")


def _safe_param(name: str) -> str:
    return name if not keyword.iskeyword(name) else name + "_"


def build_tool_function(tool_name: str, schema: dict[str, Any], dispatch: Any) -> Any:
    """Build an async function whose signature matches ``schema``.

    FastMCP derives a tool's argument handling from the function signature, so we
    generate one parameter per schema property (required first, then optional with
    a ``None`` default). The body simply forwards the arguments to ``dispatch``.
    The *advertised* schema is set separately (see :func:`_make_tool`) so the rich
    per-property descriptions from the tool modules are preserved.
    """
    props = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    ordered = [n for n in props if n in required] + [n for n in props if n not in required]

    sig_parts: list[str] = []
    arg_parts: list[str] = []
    for n in ordered:
        py = _safe_param(n)
        t = _py_type(props.get(n, {}))
        if n in required:
            sig_parts.append(f"{py}: {t}")
        else:
            sig_parts.append(f"{py}: {t} | None = None")
        arg_parts.append(f"{n}={py}")

    src = (
        "async def _fn({sig}):\n"
        "    return await __dispatch__({args})\n"
    ).format(sig=", ".join(sig_parts), args=", ".join(arg_parts))
    ns: dict[str, Any] = {"__dispatch__": dispatch, "Any": Any}
    exec(compile(src, f"<tool:{tool_name}>", "exec"), ns)
    return ns["_fn"]


def _make_tool(tool_def: dict[str, Any], mod: Any, client: Any) -> FunctionTool:
    name = tool_def["name"]
    schema = tool_def["inputSchema"]

    async def dispatch(**kwargs: Any) -> str:
        # Drop None (unprovided optional args) so validation and dispatch see only
        # what the client actually sent, matching the original server's behaviour.
        args = {k: v for k, v in kwargs.items() if v is not None}
        try:
            jsonschema.validate(args, schema)
        except jsonschema.ValidationError as e:
            raise ToolError(f"Input validation error: {e.message}") from None
        try:
            result = await mod.handle(name, args, client)
        except Exception as e:  # surface the tool's error to the client
            raise ToolError(f"{name}: {e}") from e
        return json.dumps(result, indent=2)

    fn = build_tool_function(name, schema, dispatch)
    tool = FunctionTool.from_function(fn, name=name, description=tool_def.get("description") or "")
    tool.parameters = schema  # advertise the module's exact schema (with descriptions)
    return tool


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-fortigate",
        description="FortiGate MCP server (FastMCP, streamable HTTP).",
    )
    p.add_argument("--config", default="config.yaml",
                   help="Path to the YAML config file (default: config.yaml)")
    p.add_argument("--host", default=None,
                   help="Bind address (default: config 'server.host' or 0.0.0.0)")
    p.add_argument("--port", type=int, default=None,
                   help="Bind port (default: config 'server.port' or 5752)")
    p.add_argument("--daemon", action="store_true",
                   help="Run detached in the background; writes a PID and log file")
    p.add_argument("--stop", action="store_true",
                   help="Stop a daemon started with --daemon (kills its process tree)")
    p.add_argument("--pidfile", default="mcp_fortigate.pid",
                   help="PID file used with --daemon (default: mcp_fortigate.pid)")
    p.add_argument("--logfile", default="mcp_fortigate.log",
                   help="Log file used with --daemon (default: mcp_fortigate.log)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _serve(host: str, port: int) -> None:
    # Imported here (after the config has been loaded into the environment) because
    # client.py and the integrations read os.environ at import time.
    from .client import FORTIGATE_READ_ONLY, FortiGateClient, _validate_config
    from .integrations import kube as kube_integration
    from .integrations import pve as pve_integration
    from .tools import (
        appctrl,
        config,
        dns_dhcp,
        firewall,
        fortiguard,
        k8s,
        logs,
        nat,
        network,
        profiles,
        pve,
        raw,
        security,
        system,
        traffic,
    )

    _validate_config()

    modules = [
        system, fortiguard, firewall, nat, appctrl, profiles, security,
        traffic, logs, network, dns_dhcp, config, raw,
    ]
    if kube_integration.enabled():
        modules.append(k8s)
    if pve_integration.enabled():
        modules.append(pve)

    client = FortiGateClient()
    tool_count = sum(len(m.TOOLS) for m in modules)

    @asynccontextmanager
    async def lifespan(server: FastMCP):
        await client.authenticate()
        print("=" * 60, file=sys.stderr)
        print("FortiGate MCP Server (FastMCP)", file=sys.stderr)
        print(f"Tools: {tool_count}" + ("  (read-only)" if FORTIGATE_READ_ONLY else ""), file=sys.stderr)
        print(f"Endpoint: http://{host}:{port}/mcp", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        try:
            yield
        finally:
            await client.close()
            await k8s.aclose()
            await pve_integration.aclose()

    mcp = FastMCP(
        "fortigate-mcp-server",
        instructions="Tools to inspect and manage a FortiOS firewall over its REST API.",
        version=__version__,
        lifespan=lifespan,
    )
    for mod in modules:
        for tool_def in mod.TOOLS:
            mcp.add_tool(_make_tool(tool_def, mod, client))

    mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")


def run() -> None:
    args = _build_parser().parse_args()

    if args.stop:
        daemon.stop_daemon(args.pidfile)
        return

    cfg = config_mod.load_config(args.config)
    cfg_host, cfg_port = config_mod.server_settings(cfg)
    host = args.host or cfg_host
    port = args.port if args.port is not None else cfg_port

    if args.daemon:
        daemon.daemonize(args.config, host, port, args.pidfile, args.logfile)
        return  # parent exits; the detached child keeps serving

    try:
        _serve(host, port)
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)


if __name__ == "__main__":
    run()