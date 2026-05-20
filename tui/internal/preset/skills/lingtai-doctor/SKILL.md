---
name: lingtai-doctor
description: "Self-diagnostic skill for Lingtai agents — check current TUI/kernel/Python versions, detect outdated packages, verify MCP server health, inspect agent state, and get update instructions. Run the bundled doctor.py script for a quick health report, or follow the manual checklist. Reach for this when the human asks 'is everything up to date?', 'check my setup', or when something feels off and you want to rule out version/environment issues."
version: 1.0.0
tags: [lingtai, doctor, diagnostic, version, update, health, self-check]
---

# Lingtai Doctor

> **Self-diagnostic for Lingtai agents** — check versions, detect drift, verify health, get update instructions.

## When to Use

- Human asks "is everything up to date?" or "check my setup"
- Agent feels sluggish or errors seem version-related
- After a TUI upgrade, verify the agent picked up changes
- Debugging connectivity issues (LLM, MCP servers)
- Routine health check before starting a new task

## Quick Diagnosis

Run the bundled script for a full health report:

```bash
python3 "${LINGTAI_SKILL_DIR}/scripts/doctor.py"
```

The script checks:

1. **TUI version** — installed vs latest GitHub release
2. **Kernel version** — installed Python package vs latest on PyPI
3. **Python runtime** — venv status, Python version
4. **Agent state** — heartbeat freshness, molt count, stamina
5. **LLM connectivity** — provider, model, base URL
6. **MCP servers** — registered servers, registry health
7. **Disk health** — context usage, log size, knowledge size

Output is structured with ✓/✗/! indicators for quick scanning.

## Manual Checklist

If you prefer to run checks individually (or the script fails):

### Version Check

```bash
# TUI version
lingtai-tui version 2>/dev/null || echo "lingtai-tui not on PATH"

# Kernel (Python lingtai package) version
python3 -c "import lingtai; print(lingtai.__version__)" 2>/dev/null || echo "Cannot import lingtai"

# Latest releases (requires network)
python3 -c "
import urllib.request, json
# TUI
try:
    r = json.loads(urllib.request.urlopen('https://api.github.com/repos/Lingtai-AI/lingtai/releases/latest', timeout=5).read())
    print('TUI latest:', r.get('tag_name','?'))
except Exception as e:
    print('TUI latest: (failed)', e)

# Kernel
try:
    from importlib.metadata import metadata
    import subprocess
    result = subprocess.run(['pip', 'index', 'versions', 'lingtai'], capture_output=True, text=True, timeout=10)
    print('Kernel available:', result.stdout.split('(')[1].split(')')[0] if '(' in result.stdout else '?')
except Exception as e:
    print('Kernel latest: (failed)', e)
"
```

### Update Instructions

**TUI (Homebrew):**
```bash
brew update && brew upgrade lingtai-ai/lingtai/lingtai-tui
```

**TUI (Manual):**
Download latest from https://github.com/Lingtai-AI/lingtai/releases

**Kernel (Python package):**
```bash
pip install --upgrade lingtai
```

Then restart the TUI for changes to take effect.

### Agent Health

```bash
# Read your own state
cat .agent.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('state:', d.get('state')); print('molt_count:', d.get('molt_count')); print('stamina:', d.get('stamina'))"

# Check heartbeat freshness
python3 -c "
import time, os
try:
    ts = float(open('.agent.heartbeat').read().strip())
    age = time.time() - ts
    if age < 3: print('Heartbeat: fresh')
    elif age < 60: print(f'Heartbeat: {int(age)}s old')
    elif age < 3600: print(f'Heartbeat: {int(age/60)}m old')
    else: print(f'Heartbeat: {int(age/3600)}h old — STALE!')
except FileNotFoundError:
    print('Heartbeat: MISSING (agent not running or suspended)')
except Exception as e:
    print(f'Heartbeat: error ({e})')
"

# Context pressure — check logs for pressure warnings
grep "context_pressure" logs/events.jsonl 2>/dev/null | tail -3 | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(d.get('time','?'), d.get('type','?'), f\"usage={d.get('usage','?')}\")
    except: pass
"
```

### MCP Server Health

```bash
# Check MCP registry
cat mcp_registry.jsonl 2>/dev/null | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        name = d.get('name','?')
        transport = d.get('transport','?')
        print(f'  {name} ({transport})')
    except: pass
" || echo "No MCP registry found"
```

## Interpreting Results

| Check | ✓ (green) | ! (warn) | ✗ (fail) |
|-------|-----------|----------|----------|
| TUI version | Up to date | Dev build or version drift | Cannot determine |
| Kernel version | Up to date | Update available | Cannot import |
| Python runtime | Venv active, correct version | Using fallback Python | Venv missing |
| Agent state | Active, fresh heartbeat | Idle or stale heartbeat | Suspended or no heartbeat |
| LLM connectivity | Provider reachable | Rate limited or overloaded | Auth failure or network error |
| MCP servers | All registered | Registry issues | No registry |

## Update Procedure

After running updates:

1. **Restart the TUI** — `lingtai-tui` picks up new kernel on restart
2. **Run `/doctor` in TUI** — verify the TUI-level checks pass
3. **Run this skill's script again** — confirm versions match
4. **Tell the human** — "Updated to TUI vX.Y.Z / kernel vA.B.C. Restart complete."

## Reference Files

| File | Contents |
|------|----------|
| [scripts/doctor.py](scripts/doctor.py) | Full diagnostic script — run with `python3 doctor.py` |
| [reference/update-procedures.md](reference/update-procedures.md) | Detailed update procedures for each component |
