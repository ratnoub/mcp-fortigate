"""Cross-platform daemon support: re-exec the server detached in the background.

On POSIX this uses the classic double-fork + ``setsid``. On Windows it re-launches
the same command as a detached process. Both redirect stdout/stderr to a log file,
write a PID file, and let the parent exit so the calling shell returns immediately.

The re-executed command is ``<python> -m mcp_fortigate --config ... --host ... --port ...``
(without ``--daemon``), so it works both when installed (pipx) and when run from source.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Windows process-creation flags for a fully detached background process.
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def daemonize(config: str, host: str, port: int, pidfile: str, logfile: str) -> None:
    """Re-exec the server in the background and exit the parent process."""
    cmd = [
        sys.executable,
        "-m",
        "mcp_fortigate",
        "--config",
        config,
        "--host",
        host,
        "--port",
        str(port),
    ]
    pid_path = Path(pidfile)
    log_path = Path(logfile)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "posix":
        _daemonize_posix(cmd, pid_path, log_path)
    else:
        _daemonize_windows(cmd, pid_path, log_path)


def _write_pid(path: Path, pid: int) -> None:
    path.write_text(str(pid), encoding="utf-8")


def _daemonize_posix(cmd: list[str], pid_path: Path, log_path: Path) -> None:
    # First fork: let the parent (the shell) return at once.
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    # Second fork: the daemon can never reacquire a controlling terminal.
    if os.fork() > 0:
        os._exit(0)

    sys.stdout.flush()
    sys.stderr.flush()
    log = open(log_path, "ab")
    os.dup2(log.fileno(), sys.stdout.fileno())
    os.dup2(log.fileno(), sys.stderr.fileno())
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, sys.stdin.fileno())
    os.chdir("/")

    _write_pid(pid_path, os.getpid())
    os.execv(cmd[0], cmd)


def _daemonize_windows(cmd: list[str], pid_path: Path, log_path: Path) -> None:
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    _write_pid(pid_path, proc.pid)
    port = _port_from_cmd(cmd)
    print(f"mcp-fortigate started in the background (pid {proc.pid}).")
    print(f"  endpoint: http://<ip>:{port}/mcp")
    print(f"  log:      {log_path}")
    print(f"  pidfile:  {pid_path}")
    os._exit(0)


def _port_from_cmd(cmd: list[str]) -> str:
    try:
        return cmd[cmd.index("--port") + 1]
    except (ValueError, IndexError):
        return "?"


def stop_daemon(pidfile: str) -> None:
    """Stop a daemon started with ``--daemon`` by killing its whole process tree.

    On Windows the venv ``python.exe`` is a launcher that re-execs the real
    interpreter as a child, so we must kill the tree (not just the recorded PID).
    On POSIX the daemon is a session/process-group leader, so we signal the group.
    """
    pid_path = Path(pidfile)
    if not pid_path.is_file():
        print(f"No PID file at {pidfile}; is the daemon running?", file=sys.stderr)
        sys.exit(1)
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        print(f"PID file {pidfile} is corrupt.", file=sys.stderr)
        sys.exit(1)

    if os.name == "posix":
        import signal

        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass  # already gone
    else:
        # /T kills the process and all its descendants; /F forces it.
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)

    try:
        pid_path.unlink()
    except OSError:
        pass
    print(f"Stopped mcp-fortigate (pid {pid}).")