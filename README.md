# mcp-fortigate

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server for
managing and inspecting **FortiOS** firewalls over the REST API. It is built on
[FastMCP](https://github.com/jlowin/fastmcp) and serves the protocol over
**streamable HTTP**, so a client only needs to point at one URL:

```
http://<ip>:5752/mcp
```

The server is configured entirely from a YAML file (`--config config.yaml`) and can
run in the foreground or detached in the background (`--daemon`).

## Features

- **~60 tools** across system, firewall, NAT, network, DNS/DHCP, security profiles,
  application control, FortiGuard, traffic, logs, config and a raw API escape hatch.
- **Read-only mode** (`FORTIGATE_READ_ONLY: true`) blocks all writes.
- **API-token or session (username/password)** authentication, with automatic
  session re-login on expiry.
- **Optional integrations** (enabled only when configured):
  - **Kubernetes** — keep FortiGate DNS records / address objects in step with a cluster.
  - **Proxmox VE** — label clients with the VM/container that owns their MAC.
- **Streamable HTTP** transport on `0.0.0.0:5752` by default (endpoint `/mcp`).
- **`--daemon`** to run detached in the background (cross-platform, with PID + log files).

## Installation

### With pipx (recommended)

```bash
pipx install git+https://github.com/ratnoub/mcp-fortigate.git
# or from a local clone / sdist:
pipx install .
```

This puts a `mcp-fortigate` command on your PATH in an isolated environment.

### With pip

```bash
pip install .
```

### From source (development)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows   (.venv/bin/activate on Linux/macOS)
pip install -e .
```

## Configuration

Copy the example config and edit it:

```bash
copy config.example.yaml config.yaml     # Windows
cp config.example.yaml config.yaml       # Linux/macOS
```

```yaml
server:
  host: 0.0.0.0
  port: 5752

fortigate:
  FORTIGATE_HOST: 192.68.7.4
  FORTIGATE_API_TOKEN: <your-api-token>
  FORTIGATE_READ_ONLY: true
  FORTIGATE_VERIFY_SSL: false
```

Every key under a section is exported as an environment variable of the same name,
so the `fortigate` section maps directly to the `FORTIGATE_*` settings the REST
client reads. `config.yaml` holds secrets and is **git-ignored** — commit only
`config.example.yaml`.

## Usage

```bash
# Foreground (binds 0.0.0.0:5752, endpoint http://<ip>:5752/mcp)
mcp-fortigate --config config.yaml

# Detached in the background (writes mcp_fortigate.pid and mcp_fortigate.log)
mcp-fortigate --config config.yaml --daemon

# Custom bind address / port
mcp-fortigate --config config.yaml --host 127.0.0.1 --port 9000

# Run as a module (no install needed, from the project root)
python -m mcp_fortigate --config config.yaml
```

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `config.yaml` | Path to the YAML config file |
| `--host` | config `server.host` or `0.0.0.0` | Bind address |
| `--port` | config `server.port` or `5752` | Bind port |
| `--daemon` | off | Run detached in the background |
| `--pidfile` | `mcp_fortigate.pid` | PID file used with `--daemon` |
| `--logfile` | `mcp_fortigate.log` | Log file used with `--daemon` |
| `--version` | — | Print the version and exit |

### Connecting a client

Point any MCP client at the streamable-HTTP endpoint:

```json
{
  "mcpServers": {
    "fortigate": {
      "url": "http://172.18.7.14:5752/mcp"
    }
  }
}
```

### Stopping a daemon

```bash
# Windows
taskkill /PID <pid-from-mcp_fortigate.pid> /F
# Linux/macOS
kill $(cat mcp_fortigate.pid)
```

## Project layout

```
mcp-fortigate/
├── pyproject.toml            # packaging + `mcp-fortigate` entry point
├── config.example.yaml       # template configuration (safe to commit)
├── README.md
├── LICENSE
├── .gitignore
└── mcp_fortigate/
    ├── __init__.py           # __version__
    ├── __main__.py           # python -m mcp_fortigate
    ├── server.py             # FastMCP server, CLI, tool bridge
    ├── config.py             # YAML -> environment
    ├── daemon.py             # cross-platform --daemon
    ├── client.py             # FortiOS REST client (token / session auth)
    ├── integrations/         # optional k8s + proxmox clients
    └── tools/                # tool modules (TOOLS registry + handle())
```

## Development

```bash
pip install -e .
python -m mcp_fortigate --config config.yaml
```

## License

[MIT](LICENSE).