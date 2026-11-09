# mcp-fortigate

Server [MCP](https://modelcontextprotocol.io) (Model Context Protocol) untuk
mengelola dan memeriksa firewall **FortiOS** melalui REST API. Dibangun di atas
[FastMCP](https://github.com/jlowin/fastmcp) dan menyajikan protokol melalui
**streamable HTTP**, sehingga client cukup menunjuk ke satu URL:

```
http://<ip>:5752/mcp
```

Server dikonfigurasi sepenuhnya dari file YAML (`--config config.yaml`) dan dapat
dijalankan di foreground atau detached di background (`--daemon`).

## Fitur

- **92 tool** (88 selalu tersedia, ditambah 4 lagi saat integrasi Kubernetes dan
  Proxmox opsional diaktifkan) mencakup system, firewall, NAT, network, DNS/DHCP,
  security profiles, application control, FortiGuard, traffic, logs, config, dan
  akses API mentah (raw API). Lihat [Tools](#tools) untuk daftar lengkap.
- **Mode read-only** (`FORTIGATE_READ_ONLY: true`) memblokir semua penulisan.
- Autentikasi **API token atau session (username/password)**, dengan
  re-login session otomatis saat kedaluwarsa.
- **Integrasi opsional** (aktif hanya jika dikonfigurasi):
  - **Kubernetes** — menjaga record DNS / address object FortiGate tetap selaras dengan cluster.
  - **Proxmox VE** — memberi label client berdasarkan VM/container yang memiliki MAC-nya.
- Transport **streamable HTTP** di `0.0.0.0:5752` secara default (endpoint `/mcp`).
- **`--daemon`** untuk berjalan detached di background (cross-platform, dengan file PID + log).

## Instalasi

### Dengan pipx (disarankan)

```bash
pipx install git+https://github.com/ratnoub/mcp-fortigate.git
# atau dari clone lokal / sdist:
pipx install .
```

Perintah `mcp-fortigate` akan tersedia di PATH dalam lingkungan terisolasi.

### Dengan pip

```bash
pip install .
```

### Dari source (pengembangan)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows   (Linux/macOS: .venv/bin/activate)
pip install -e .
```

## Konfigurasi

Salin contoh konfigurasi lalu edit:

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

Setiap key di bawah sebuah section diekspor sebagai environment variable dengan
nama yang sama, sehingga section `fortigate` langsung memetakan ke pengaturan
`FORTIGATE_*` yang dibaca client REST. `config.yaml` berisi secret dan
**git-ignored** — yang di-commit hanya `config.example.yaml`.

## Penggunaan

```bash
# Foreground (bind 0.0.0.0:5752, endpoint http://<ip>:5752/mcp)
mcp-fortigate --config config.yaml

# Detached di background (menulis mcp_fortigate.pid dan mcp_fortigate.log)
mcp-fortigate --config config.yaml --daemon

# Alamat / port bind kustom
mcp-fortigate --config config.yaml --host 127.0.0.1 --port 9000

# Jalankan sebagai modul (tanpa instalasi, dari root proyek)
python -m mcp_fortigate --config config.yaml
```

| Flag | Default | Keterangan |
|------|---------|------------|
| `--config` | `config.yaml` | Path file konfigurasi YAML |
| `--host` | config `server.host` atau `0.0.0.0` | Alamat bind |
| `--port` | config `server.port` atau `5752` | Port bind |
| `--daemon` | off | Jalankan detached di background |
| `--pidfile` | `mcp_fortigate.pid` | File PID yang dipakai bersama `--daemon` |
| `--logfile` | `mcp_fortigate.log` | File log yang dipakai bersama `--daemon` |
| `--version` | — | Tampilkan versi lalu keluar |

### Menghubungkan client

Arahkan client MCP apa pun ke endpoint streamable-HTTP:

```json
{
  "mcpServers": {
    "fortigate": {
      "url": "http://172.18.7.14:5752/mcp"
    }
  }
}
```

### Menghentikan daemon

```bash
# Windows
taskkill /PID <pid-dari-mcp_fortigate.pid> /F
# Linux/macOS
kill $(cat mcp_fortigate.pid)
```

## Tools

Total 92 tool: 88 selalu tersedia, dan 4 lagi muncul saat integrasi opsional
Kubernetes dan Proxmox diaktifkan. Dalam mode read-only
(`FORTIGATE_READ_ONLY: true`) semua tool penulisan diblokir.

### System, lisensi & hardening (18)

| Tool | Fungsi |
|------|--------|
| `get_system_status` | Model, serial, versi/build firmware, hostname, dan uptime. |
| `get_license_status` | Status lisensi dan kontrak FortiGuard (`all=true` untuk semua entitlement). |
| `get_license_limits` | Seberapa besar batas objek lisensi (interface, policy, route…) yang terpakai. |
| `get_license_features` | Apa saja yang dilisensikan pada perangkat dan layanan FortiGuard mana yang aktif atau segera kedaluwarsa. |
| `get_resource_usage` | Penggunaan CPU, memori, disk, dan session saat ini. |
| `list_interfaces` | Konfigurasi interface (IP, mode, role, alias, allowaccess). |
| `get_interface` | Konfigurasi lengkap satu interface. |
| `get_interface_status` | Status interface langsung: link, kecepatan, IP, dan counter trafik. |
| `update_interface` | Memperbarui interface (mengubah interface yang dipakai API dapat memutus akses). |
| `list_admin_sessions` | Administrator yang sedang login (GUI, SSH, API) dan dari mana. |
| `audit_admin_access` | Audit read-only terhadap paparan admin (tanpa MFA, admin default, akses admin di WAN, hash password lemah) beserta temuan berjenjang dan saran perbaikan. |
| `audit_hardening` | Audit hardening read-only lengkap (akses admin, crypto/TLS, SSL VPN, logging, NTP, FortiGuard, proteksi policy, HA) beserta rencana perbaikan berurutan. |
| `backup_config` | Backup konfigurasi berjalan penuh (teks CLI) ke file lokal; diizinkan dalam mode read-only. |
| `forticonverter_setup_prompt` | Menampilkan/menyembunyikan langkah setup "Migrate Config with FortiConverter" di GUI. |
| `activate_vm_eval_license` | Mengaktifkan lisensi evaluasi permanen gratis pada FortiGate-VM tanpa lisensi melalui FortiCloud. |
| `get_ha_status` | Mode HA, group, interface heartbeat/monitored, role anggota, dan sinkronisasi konfigurasi. |
| `list_fortitokens` | FortiToken di perangkat dan admin mana yang memakai autentikasi dua faktor. |
| `set_admin_mfa` | Mengaktifkan/menonaktifkan autentikasi dua faktor (FortiToken, email, SMS) untuk seorang administrator. |

### FortiGuard & firmware (3)

| Tool | Fungsi |
|------|--------|
| `get_fortiguard_status` | Apakah update FortiGuard benar-benar sampai ke perangkat: jangkauan server, jadwal, layanan berlisensi, umur signature, plus temuan. |
| `update_fortiguard` | Memicu update FortiGuard sekarang ("Check update now" di GUI); default `dry_run`. |
| `get_firmware_status` | Firmware berjalan, image versi baru yang ditawarkan FortiGuard, jalur upgrade yang didukung, dan pengaturan auto-upgrade. |

### Policy firewall, address & service (24)

| Tool | Fungsi |
|------|--------|
| `list_firewall_policies` | Daftar policy firewall IPv4 sesuai urutan evaluasi. |
| `get_firewall_policy` | Mengambil satu policy firewall. |
| `create_firewall_policy` | Membuat policy firewall (ditambahkan di akhir; lisensi evaluasi hanya mengizinkan 3). |
| `update_firewall_policy` | Memperbarui policy firewall (hanya field yang diberikan yang berubah). |
| `delete_firewall_policy` | Menghapus policy firewall. |
| `move_firewall_policy` | Memindahkan policy sebelum atau sesudah policy lain (policy dicocokkan dari atas ke bawah). |
| `get_policy_stats` | Jumlah hit, byte, packet, dan waktu pemakaian terakhir per policy. |
| `list_sessions` | Session saat ini yang melewati firewall, dapat difilter. |
| `list_addresses` | Daftar address object firewall. |
| `get_address` | Mengambil satu address object firewall. |
| `create_address` | Membuat address firewall: subnet/host, rentang IP, atau FQDN. |
| `update_address` | Memperbarui address object firewall. |
| `delete_address` | Menghapus address firewall (gagal selama masih dipakai policy atau group). |
| `list_address_groups` | Daftar address group firewall beserta anggotanya. |
| `create_address_group` | Membuat address group. |
| `update_address_group` | Memperbarui address group (`members` menggantikan seluruh daftar). |
| `delete_address_group` | Menghapus address group (gagal selama masih dipakai policy). |
| `list_services` | Daftar service firewall kustom (definisi port). |
| `create_service` | Membuat service TCP/UDP kustom. |
| `list_service_groups` | Daftar service group beserta anggotanya. |
| `create_service_group` | Membuat service group, mis. `K3S-MGMT = [SSH, K8S-API, PING]`. |
| `update_service_group` | Memperbarui service group (`members` menggantikan seluruh daftar). |
| `delete_service_group` | Menghapus service group (gagal selama masih dipakai policy). |
| `delete_service` | Menghapus service kustom (gagal selama masih dipakai policy). |

### NAT & port forwarding (3)

| Tool | Fungsi |
|------|--------|
| `list_port_forwards` | Daftar virtual IP (port forward / static NAT) dan policy yang memakai masing-masing. |
| `create_port_forward` | Membuat port forward (VIP); dapat menempel ke policy yang sudah ada agar hemat slot policy. |
| `delete_port_forward` | Menghapus VIP (`detach=true` dulu melepasnya dari semua policy). |

### Application control (5)

| Tool | Fungsi |
|------|--------|
| `search_applications` | Mencari signature application control berdasarkan nama dan/atau kategori. |
| `list_app_categories` | Kategori application control (id dan nama). |
| `list_app_control_profiles` | Profil app control beserta aturannya (menampilkan nama, bukan id). |
| `add_app_control_rule` | Menambahkan aturan ke profil app control (default disisipkan di bagian atas). |
| `delete_app_control_rule` | Menghapus aturan dari profil app control berdasarkan id-nya. |

### Security profiles (2)

| Tool | Fungsi |
|------|--------|
| `list_security_profiles` | Security profile per jenis, policy yang memakai masing-masing, dan apakah layanan FortiGuard-nya berlisensi. |
| `audit_policy_protection` | Memeriksa apakah policy accept benar-benar terlindungi (IPS, inspeksi HTTPS, lisensi, logging). Read-only. |

### Inspeksi SSL/SSH & sertifikat (4)

| Tool | Fungsi |
|------|--------|
| `list_ssl_ssh_profiles` | Profil inspeksi SSL/SSH beserta CA yang dipakai masing-masing untuk menandatangani ulang. |
| `update_ssl_ssh_profile` | Memperbarui profil inspeksi SSL/SSH (mis. CA untuk deep inspection). |
| `list_certificates` | Sertifikat lokal dan CA beserta tipe/ukuran key, masa berlaku, dan penggunaan; menandai key RSA yang lemah. |
| `download_certificate` | Mengunduh PEM sebuah sertifikat (bagian publik) beserta fingerprint SHA-256-nya. |

### Traffic & ARP (2)

| Tool | Fungsi |
|------|--------|
| `get_top_traffic` | Ringkasan FortiView langsung dari session saat ini, dikelompokkan per source/destination/aplikasi/negara/interface/policy/protokol. |
| `get_arp_table` | Tabel ARP IPv4: MAC mana yang menjawab untuk IP mana di tiap interface. |

### Logs & target log (3)

| Tool | Fungsi |
|------|--------|
| `get_logs` | Membaca log FortiGate, yang terbaru dulu (traffic, app-ctrl, event/system, ips, webfilter…). |
| `get_log_targets` | Ke mana log dikirim (syslog, FortiAnalyzer, FortiGuard Cloud, disk, memori) beserta penanda keamanan. |
| `set_syslog_target` | Mengirim log ke server syslog (udp / reliable TCP / legacy-reliable, TLS opsional). |

### Routing (4)

| Tool | Fungsi |
|------|--------|
| `get_routing_table` | Tabel routing IPv4 aktif (connected, static, hasil DHCP, dan dinamis). |
| `list_static_routes` | Daftar static route yang dikonfigurasi. |
| `create_static_route` | Menambahkan static route (lisensi evaluasi hanya mengizinkan 3). |
| `delete_static_route` | Menghapus static route berdasarkan nomor urutnya. |

### DNS & DHCP (14)

| Tool | Fungsi |
|------|--------|
| `get_dns_settings` | Pengaturan DNS sistem: resolver upstream yang dipakai dan diteruskan FortiGate. |
| `list_dns_servers` | Interface tempat FortiGate menjawab query DNS, dan dalam mode apa. |
| `set_dns_server` | Menyajikan DNS di sebuah interface (recursive, non-recursive, atau forward-only). |
| `delete_dns_server` | Menghentikan penyajian DNS di sebuah interface. |
| `list_dns_zones` | Daftar zona DNS lokal beserta record-nya. |
| `create_dns_zone` | Membuat zona DNS lokal (`view=shadow` untuk client internal). |
| `delete_dns_zone` | Menghapus zona DNS lokal beserta semua record-nya. |
| `add_dns_record` | Menambahkan record ke zona DNS lokal. |
| `delete_dns_record` | Menghapus record dari zona DNS lokal berdasarkan id-nya. |
| `list_dhcp_servers` | Daftar server DHCP beserta range, opsi, dan reservasinya. |
| `list_dhcp_leases` | Lease DHCP saat ini yang diberikan FortiGate. |
| `update_dhcp_server` | Memperbarui server DHCP. |
| `add_dhcp_reservation` | Mereservasi IP untuk sebuah alamat MAC di server DHCP. |
| `delete_dhcp_reservation` | Menghapus reservasi DHCP berdasarkan id-nya. |

### Konfigurasi generik & penelusuran API (5)

Mencapai pengaturan apa pun yang tidak dicakup tool khusus, memakai skema milik
FortiGate itu sendiri.

| Tool | Fungsi |
|------|--------|
| `search_api` | Mencari endpoint API FortiOS berdasarkan kata kunci (konfigurasi dan status langsung). |
| `describe_config` | Mendeskripsikan endpoint konfigurasi: tabel vs objek tunggal, serta tipe/nilai/rentang/default tiap field. |
| `get_config` | Membaca endpoint konfigurasi apa pun (secret ditampilkan sebagai `<set>`). |
| `set_config` | Mengubah endpoint konfigurasi apa pun, tervalidasi skema; default `dry_run`. |
| `get_monitor` | Membaca endpoint monitor (status langsung) apa pun. |

### API mentah (1)

| Tool | Fungsi |
|------|--------|
| `fortigate_api` | Memanggil endpoint REST FortiOS apa pun secara langsung (`/api/v2/...`); mode read-only tetap berlaku. |

### Integrasi Kubernetes (opsional, 3)

Aktif hanya jika `K8S_KUBECONFIG` diset.

| Tool | Fungsi |
|------|--------|
| `k8s_cluster_overview` | Membaca cluster: node, service LoadBalancer, dan hostname Ingress. Read-only. |
| `k8s_sync_ingress_dns` | Membuat record DNS FortiGate untuk hostname Ingress yang berada di dalam zona lokal. |
| `k8s_sync_node_addresses` | Menjaga address object/group FortiGate tetap selaras dengan IP node cluster. |

### Integrasi Proxmox VE (opsional, 1)

Aktif hanya jika Proxmox dikonfigurasi.

| Tool | Fungsi |
|------|--------|
| `identify_clients` | Mencocokkan setiap client (lease DHCP dan ARP) berdasarkan MAC dengan VM/container Proxmox yang memilikinya. |

## Struktur proyek

```
mcp-fortigate/
├── pyproject.toml            # packaging + entry point `mcp-fortigate`
├── config.example.yaml       # template konfigurasi (aman di-commit)
├── README.md
├── LICENSE
├── .gitignore
└── mcp_fortigate/
    ├── __init__.py           # __version__
    ├── __main__.py           # python -m mcp_fortigate
    ├── server.py             # server FastMCP, CLI, jembatan tool
    ├── config.py             # YAML -> environment
    ├── daemon.py             # --daemon cross-platform
    ├── client.py             # client REST FortiOS (auth token / session)
    ├── integrations/         # client k8s + proxmox opsional
    └── tools/                # modul tool (registry TOOLS + handle())
```

## Pengembangan

```bash
pip install -e .
python -m mcp_fortigate --config config.yaml
```

## Lisensi

[MIT](LICENSE).