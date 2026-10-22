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

- **92 tools** (88 always available, plus 4 more when the optional Kubernetes and
  Proxmox integrations are enabled) across system, firewall, NAT, network, DNS/DHCP,
  security profiles, application control, FortiGuard, traffic, logs, config and a raw
  API escape hatch. See [Tools](#tools) for the full list.
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

## Tools

92 tools in total: 88 are always available, and 4 more appear when the optional
Kubernetes and Proxmox integrations are enabled. In read-only mode
(`FORTIGATE_READ_ONLY: true`) every write tool is blocked.

### System, license & hardening (18)

| Tool | What it does |
|------|--------------|
| `get_system_status` | Model, serial, firmware version/build, hostname and uptime. |
| `get_license_status` | License and FortiGuard contract status (`all=true` for every entitlement). |
| `get_license_limits` | How much of the license's object limits (interfaces, policies, routes…) is used. |
| `get_license_features` | What the box is licensed for and which FortiGuard services are active or expiring. |
| `get_resource_usage` | Current CPU, memory, disk and session usage. |
| `list_interfaces` | Interface configuration (IP, mode, role, alias, allowaccess). |
| `get_interface` | One interface's full configuration. |
| `get_interface_status` | Live interface state: link, speed, IP and traffic counters. |
| `update_interface` | Update an interface (changing the API-facing interface can cut off access). |
| `list_admin_sessions` | Administrators currently logged in (GUI, SSH, API) and where from. |
| `audit_admin_access` | Read-only audit of admin exposure (no MFA, default admin, WAN admin access, weak password hashes) with graded findings and fixes. |
| `audit_hardening` | Full read-only hardening audit (admin access, crypto/TLS, SSL VPN, logging, NTP, FortiGuard, policy protection, HA) with an ordered fix plan. |
| `backup_config` | Back up the full running config (CLI text) to a local file; allowed in read-only mode. |
| `forticonverter_setup_prompt` | Show/hide the GUI's "Migrate Config with FortiConverter" setup step. |
| `activate_vm_eval_license` | Activate the free permanent evaluation license on an unlicensed FortiGate-VM via FortiCloud. |
| `get_ha_status` | HA mode, group, heartbeat/monitored interfaces, member roles and config sync. |
| `list_fortitokens` | FortiTokens on the box and which admins use two-factor auth. |
| `set_admin_mfa` | Enable/disable two-factor auth (FortiToken, email, SMS) for an administrator. |

### FortiGuard & firmware (3)

| Tool | What it does |
|------|--------------|
| `get_fortiguard_status` | Whether FortiGuard updates are reaching the box: server reachability, schedule, licensed services, signature age, plus findings. |
| `update_fortiguard` | Trigger a FortiGuard update now (the GUI's "Check update now"); `dry_run` by default. |
| `get_firmware_status` | Running firmware, newer images FortiGuard offers, the supported upgrade path and auto-upgrade settings. |

### Firewall policies, addresses & services (24)

| Tool | What it does |
|------|--------------|
| `list_firewall_policies` | List IPv4 firewall policies in evaluation order. |
| `get_firewall_policy` | Get one firewall policy. |
| `create_firewall_policy` | Create a firewall policy (added at the end; evaluation licenses allow only 3). |
| `update_firewall_policy` | Update a firewall policy (only the fields given change). |
| `delete_firewall_policy` | Delete a firewall policy. |
| `move_firewall_policy` | Move a policy before or after another one (policies match top-down). |
| `get_policy_stats` | Hit counts, bytes, packets and last-used time per policy. |
| `list_sessions` | Current sessions through the firewall, optionally filtered. |
| `list_addresses` | List firewall address objects. |
| `get_address` | Get one firewall address object. |
| `create_address` | Create a firewall address: a subnet/host, an IP range, or an FQDN. |
| `update_address` | Update a firewall address object. |
| `delete_address` | Delete a firewall address (fails while a policy or group still uses it). |
| `list_address_groups` | List firewall address groups and their members. |
| `create_address_group` | Create an address group. |
| `update_address_group` | Update an address group (`members` replaces the whole list). |
| `delete_address_group` | Delete an address group (fails while a policy still uses it). |
| `list_services` | List custom firewall services (port definitions). |
| `create_service` | Create a custom TCP/UDP service. |
| `list_service_groups` | List service groups and their members. |
| `create_service_group` | Create a service group, e.g. `K3S-MGMT = [SSH, K8S-API, PING]`. |
| `update_service_group` | Update a service group (`members` replaces the whole list). |
| `delete_service_group` | Delete a service group (fails while a policy still uses it). |
| `delete_service` | Delete a custom service (fails while a policy still uses it). |

### NAT & port forwarding (3)

| Tool | What it does |
|------|--------------|
| `list_port_forwards` | List virtual IPs (port forwards / static NAT) and the policies that use each. |
| `create_port_forward` | Create a port forward (VIP); can attach to an existing policy to save a policy slot. |
| `delete_port_forward` | Delete a VIP (`detach=true` first removes it from every policy). |

### Application control (5)

| Tool | What it does |
|------|--------------|
| `search_applications` | Search application-control signatures by name and/or category. |
| `list_app_categories` | Application-control categories (id and name). |
| `list_app_control_profiles` | App-control profiles with their rules (names instead of ids). |
| `add_app_control_rule` | Add a rule to an app-control profile (inserted at the top by default). |
| `delete_app_control_rule` | Remove a rule from an app-control profile by its id. |

### Security profiles (2)

| Tool | What it does |
|------|--------------|
| `list_security_profiles` | Security profiles by kind, the policies that use each, and whether the FortiGuard service is licensed. |
| `audit_policy_protection` | Check that accept policies are actually protected (IPS, HTTPS inspection, licensing, logging). Read-only. |

### SSL/SSH inspection & certificates (4)

| Tool | What it does |
|------|--------------|
| `list_ssl_ssh_profiles` | SSL/SSH inspection profiles with the CA each re-signs with. |
| `update_ssl_ssh_profile` | Update an SSL/SSH inspection profile (e.g. the deep-inspection CA). |
| `list_certificates` | Local and CA certificates with key type/size, validity and usage; flags weak RSA keys. |
| `download_certificate` | Download a certificate's PEM (public part) and its SHA-256 fingerprint. |

### Traffic & ARP (2)

| Tool | What it does |
|------|--------------|
| `get_top_traffic` | Live FortiView summary of current sessions, grouped by source/destination/app/country/interface/policy/protocol. |
| `get_arp_table` | IPv4 ARP table: which MAC answers for which IP on each interface. |

### Logs & log targets (3)

| Tool | What it does |
|------|--------------|
| `get_logs` | Read FortiGate logs, newest first (traffic, app-ctrl, event/system, ips, webfilter…). |
| `get_log_targets` | Where logs go (syslog, FortiAnalyzer, FortiGuard Cloud, disk, memory) with security flags. |
| `set_syslog_target` | Send logs to a syslog server (udp / reliable TCP / legacy-reliable, optional TLS). |

### Routing (4)

| Tool | What it does |
|------|--------------|
| `get_routing_table` | Active IPv4 routing table (connected, static, DHCP-learned and dynamic). |
| `list_static_routes` | List configured static routes. |
| `create_static_route` | Add a static route (evaluation licenses allow only 3). |
| `delete_static_route` | Delete a static route by its sequence number. |

### DNS & DHCP (14)

| Tool | What it does |
|------|--------------|
| `get_dns_settings` | System DNS settings: upstream resolvers the FortiGate uses and forwards to. |
| `list_dns_servers` | Interfaces where the FortiGate answers DNS queries, and in which mode. |
| `set_dns_server` | Serve DNS on an interface (recursive, non-recursive or forward-only). |
| `delete_dns_server` | Stop serving DNS on an interface. |
| `list_dns_zones` | List local DNS zones with their records. |
| `create_dns_zone` | Create a local DNS zone (`view=shadow` serves internal clients). |
| `delete_dns_zone` | Delete a local DNS zone and all its records. |
| `add_dns_record` | Add a record to a local DNS zone. |
| `delete_dns_record` | Delete a record from a local DNS zone by its id. |
| `list_dhcp_servers` | List DHCP servers with their ranges, options and reservations. |
| `list_dhcp_leases` | Current DHCP leases handed out by the FortiGate. |
| `update_dhcp_server` | Update a DHCP server. |
| `add_dhcp_reservation` | Reserve an IP for a MAC address on a DHCP server. |
| `delete_dhcp_reservation` | Remove a DHCP reservation by its id. |

### Generic config & API discovery (5)

Reach any setting no dedicated tool covers, using the FortiGate's own schema.

| Tool | What it does |
|------|--------------|
| `search_api` | Find FortiOS API endpoints by keyword (configuration and live state). |
| `describe_config` | Describe a config endpoint: table vs single object, and each field's type/values/range/default. |
| `get_config` | Read any configuration endpoint (secrets shown as `<set>`). |
| `set_config` | Change any configuration endpoint, schema-validated; `dry_run` by default. |
| `get_monitor` | Read any monitor (live state) endpoint. |

### Raw API (1)

| Tool | What it does |
|------|--------------|
| `fortigate_api` | Call any FortiOS REST endpoint directly (`/api/v2/...`); read-only mode still applies. |

### Kubernetes integration (optional, 3)

Enabled only when `K8S_KUBECONFIG` is set.

| Tool | What it does |
|------|--------------|
| `k8s_cluster_overview` | Read the cluster: nodes, LoadBalancer services and Ingress hostnames. Read-only. |
| `k8s_sync_ingress_dns` | Create FortiGate DNS records for Ingress hostnames that fall inside a local zone. |
| `k8s_sync_node_addresses` | Keep a FortiGate address object/group in step with the cluster's node IPs. |

### Proxmox VE integration (optional, 1)

Enabled only when Proxmox is configured.

| Tool | What it does |
|------|--------------|
| `identify_clients` | Match every client (DHCP leases and ARP) by MAC to the Proxmox VM/container that owns it. |

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