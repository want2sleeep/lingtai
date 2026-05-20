#!/usr/bin/env python3
"""
Lingtai Doctor — Self-diagnostic script for Lingtai agents.

Run from bash: python3 "${LINGTAI_SKILL_DIR}/scripts/doctor.py"
Or directly:   python3 /path/to/doctor.py

Checks:
  1. TUI version (installed vs latest GitHub release)
  2. Kernel version (Python lingtai package vs latest PyPI)
  3. Python runtime (venv status, version)
  4. Agent state (heartbeat freshness, molt count, stamina)
  5. LLM config (provider, model, base_url)
  6. MCP servers (registry entries)
  7. Disk usage (logs, knowledge, context)

Exit codes:
  0 — all checks passed (may have warnings)
  1 — one or more checks failed
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Helpers ──────────────────────────────────────────────────────────────────

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"

results = []
exit_code = 0


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")
    results.append(("ok", msg))


def fail(msg):
    global exit_code
    exit_code = 1
    print(f"  {RED}✗{RESET} {msg}")
    results.append(("fail", msg))


def warn(msg):
    print(f"  {YELLOW}!{RESET} {msg}")
    results.append(("warn", msg))


def info(msg):
    print(f"  {DIM}→{RESET} {msg}")
    results.append(("info", msg))


def section(title):
    print(f"\n{title}")


def run(cmd, timeout=10):
    """Run a command, return (stdout, stderr, returncode)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except FileNotFoundError:
        return "", f"command not found: {cmd[0]}", 1
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except Exception as e:
        return "", str(e), 1


def fetch_json(url, timeout=5):
    """Fetch JSON from URL. Returns (data, error)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "lingtai-doctor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)


# ── Determine working directory ─────────────────────────────────────────────

# The agent's working directory is typically the CWD or LINGTAI_AGENT_DIR
agent_dir = os.environ.get("LINGTAI_AGENT_DIR", os.getcwd())
agent_dir = Path(agent_dir)

# Global dir is typically ~/.lingtai-tui/
home = Path.home()
global_dir = Path(os.environ.get("LINGTAI_GLOBAL_DIR", home / ".lingtai-tui"))


# ── 1. TUI Version ──────────────────────────────────────────────────────────

section("── TUI ──")

stdout, _, rc = run(["lingtai-tui", "version"])
if rc == 0 and stdout:
    tui_version = stdout.split()[-1] if stdout else "unknown"
    ok(f"TUI version: {tui_version}")

    # Check latest release
    data, err = fetch_json(
        "https://api.github.com/repos/Lingtai-AI/lingtai/releases/latest"
    )
    if data and data.get("tag_name"):
        latest = data["tag_name"]
        if tui_version == latest.lstrip("v"):
            ok(f"TUI is up to date ({latest})")
        elif tui_version == "dev" or "-" in tui_version:
            warn(f"Dev build ({tui_version}), latest release: {latest}")
        else:
            warn(f"TUI update available: {tui_version} → {latest}")
            info("Update: brew update && brew upgrade lingtai-ai/lingtai/lingtai-tui")
    else:
        warn(f"Cannot check latest TUI release: {err}")
else:
    fail("lingtai-tui not found on PATH")
    info("Install: https://github.com/Lingtai-AI/lingtai/releases")

# ── 2. Kernel (Python lingtai) Version ──────────────────────────────────────

section("── Kernel (lingtai Python package) ──")

stdout, stderr, rc = run(
    [sys.executable, "-c", "import lingtai; print(lingtai.__version__)"]
)
if rc == 0 and stdout:
    kernel_version = stdout.strip()
    ok(f"Kernel version: {kernel_version}")

    # Check PyPI latest
    stdout2, _, rc2 = run([sys.executable, "-m", "pip", "index", "versions", "lingtai"])
    if rc2 == 0 and stdout2:
        # Parse "lingtai (X.Y.Z)" from output
        for part in stdout2.split():
            if part.startswith("(") and part.endswith(")"):
                latest_kernel = part[1:-1]
                if kernel_version == latest_kernel:
                    ok(f"Kernel is up to date ({latest_kernel})")
                else:
                    warn(f"Kernel update available: {kernel_version} → {latest_kernel}")
                    info(f"Update: {sys.executable} -m pip install --upgrade lingtai")
                break
    else:
        warn("Cannot check latest kernel version on PyPI")
else:
    fail(f"Cannot import lingtai: {stderr or 'unknown error'}")
    info(f"Install: {sys.executable} -m pip install lingtai")

# ── 3. Python Runtime ───────────────────────────────────────────────────────

section("── Python Runtime ──")

ok(f"Python: {sys.executable} ({sys.version.split()[0]})")

# Check if running in a managed venv
venv_dir = global_dir / "runtime" / "venv"
if str(sys.executable).startswith(str(venv_dir)):
    ok(f"Using managed venv: {venv_dir}")
elif "venv" in str(sys.executable) or ".virtualenvs" in str(sys.executable):
    info(f"Using custom venv: {sys.executable}")
else:
    warn(f"Using system Python (not managed venv)")
    info(f"Expected venv at: {venv_dir}/bin/python3")

# ── 4. Agent State ──────────────────────────────────────────────────────────

section("── Agent State ──")

agent_json = agent_dir / ".agent.json"
if agent_json.exists():
    try:
        with open(agent_json) as f:
            state = json.load(f)
        ok(f"Agent: {state.get('agent_name', '?')} (id: {state.get('agent_id', '?')})")
        ok(f"State: {state.get('state', '?')}")
        ok(f"Molt count: {state.get('molt_count', '?')}")
        ok(f"Stamina: {state.get('stamina', '?')}s")
        ok(f"LLM: {state.get('llm', {}).get('provider', '?')}/{state.get('llm', {}).get('model', '?')}")
    except Exception as e:
        fail(f"Cannot read .agent.json: {e}")
else:
    warn("No .agent.json found (not in agent working directory?)")

# Heartbeat
heartbeat_path = agent_dir / ".agent.heartbeat"
if heartbeat_path.exists():
    try:
        ts = float(heartbeat_path.read_text().strip())
        age = time.time() - ts
        if age < 3:
            ok(f"Heartbeat: fresh ({age:.1f}s)")
        elif age < 60:
            warn(f"Heartbeat: {age:.0f}s old")
        elif age < 3600:
            warn(f"Heartbeat: {int(age / 60)}m old — possibly stuck")
        else:
            fail(f"Heartbeat: {int(age / 3600)}h old — likely dead")
    except Exception as e:
        warn(f"Heartbeat parse error: {e}")
else:
    warn("No heartbeat file — agent may be suspended or not running")

# ── 5. LLM Config ───────────────────────────────────────────────────────────

section("── LLM ──")

init_json = agent_dir / "init.json"
if init_json.exists():
    try:
        with open(init_json) as f:
            cfg = json.load(f)
        llm = cfg.get("manifest", {}).get("llm", {})
        provider = llm.get("provider", "?")
        model = llm.get("model", "?")
        base_url = llm.get("base_url", "")
        api_key = llm.get("api_key", "")
        api_key_env = llm.get("api_key_env", "")

        ok(f"Provider: {provider}")
        ok(f"Model: {model}")
        if base_url:
            info(f"Base URL: {base_url}")
        if api_key:
            ok(f"API key: configured (direct)")
        elif api_key_env:
            key_val = os.environ.get(api_key_env, "")
            if key_val:
                ok(f"API key: resolved from ${api_key_env}")
            else:
                fail(f"API key: ${api_key_env} not set in environment")
        else:
            warn("No API key configured")
    except Exception as e:
        fail(f"Cannot read init.json: {e}")
else:
    warn("No init.json found")

# ── 6. MCP Servers ──────────────────────────────────────────────────────────

section("── MCP Servers ──")

mcp_registry = agent_dir / "mcp_registry.jsonl"
if mcp_registry.exists():
    try:
        servers = []
        with open(mcp_registry) as f:
            for line in f:
                line = line.strip()
                if line:
                    servers.append(json.loads(line))
        if servers:
            ok(f"{len(servers)} MCP server(s) registered:")
            for s in servers:
                name = s.get("name", "?")
                transport = s.get("transport", "?")
                info(f"  {name} ({transport})")
        else:
            info("No MCP servers registered")
    except Exception as e:
        warn(f"Cannot read mcp_registry.jsonl: {e}")
else:
    info("No mcp_registry.jsonl — no MCP servers configured")

# ── 7. Disk Usage ───────────────────────────────────────────────────────────

section("── Disk Usage ──")

# Log size
log_dir = agent_dir / "logs"
if log_dir.exists():
    log_size = sum(f.stat().st_size for f in log_dir.rglob("*") if f.is_file())
    if log_size > 100 * 1024 * 1024:
        warn(f"Logs: {log_size / 1024 / 1024:.1f} MB — consider archiving")
    else:
        ok(f"Logs: {log_size / 1024:.0f} KB")
else:
    info("No logs directory")

# Knowledge size
knowledge_dir = agent_dir / "knowledge"
if knowledge_dir.exists():
    k_size = sum(f.stat().st_size for f in knowledge_dir.rglob("*") if f.is_file())
    ok(f"Knowledge: {k_size / 1024:.0f} KB")
else:
    info("No knowledge directory")

# Chat history
history_dir = agent_dir / "history"
if history_dir.exists():
    h_size = sum(f.stat().st_size for f in history_dir.rglob("*") if f.is_file())
    if h_size > 500 * 1024 * 1024:
        warn(f"Chat history: {h_size / 1024 / 1024:.1f} MB — consider molting")
    else:
        ok(f"Chat history: {h_size / 1024 / 1024:.1f} MB")
else:
    info("No chat history")

# ── Summary ──────────────────────────────────────────────────────────────────

section("── Summary ──")

oks = sum(1 for r in results if r[0] == "ok")
warns = sum(1 for r in results if r[0] == "warn")
fails = sum(1 for r in results if r[0] == "fail")

print(f"  {GREEN}{oks} passed{RESET}, {YELLOW}{warns} warnings{RESET}, {RED}{fails} failures{RESET}")

if fails > 0:
    print(f"\n  {RED}Issues detected — review failures above.{RESET}")
    print(f"  Update commands:")
    print(f"    TUI:     brew update && brew upgrade lingtai-ai/lingtai/lingtai-tui")
    print(f"    Kernel:  {sys.executable} -m pip install --upgrade lingtai")
elif warns > 0:
    print(f"\n  {YELLOW}Warnings detected — review above. Agent is functional but may need attention.{RESET}")
else:
    print(f"\n  {GREEN}All systems healthy.{RESET}")

sys.exit(exit_code)
