# Update Procedures

Detailed instructions for updating each Lingtai component.

## TUI Binary

### Homebrew (macOS, recommended)

```bash
brew update
brew upgrade lingtai-ai/lingtai/lingtai-tui
```

Verify: `lingtai-tui version`

### Manual Download

1. Go to https://github.com/Lingtai-AI/lingtai/releases/latest
2. Download the binary for your platform
3. Replace the existing binary on PATH
4. Verify: `lingtai-tui version`

### After TUI Update

- **Restart the TUI** — the new binary picks up changes on restart
- **Run `/doctor`** — verify the update propagated
- **Run `lingtai-doctor` skill** — confirm agent sees new versions
- The TUI automatically re-extracts bundled skills and bootstrap assets on startup

## Kernel (Python `lingtai` package)

### pip

```bash
pip install --upgrade lingtai
```

Verify: `python3 -c "import lingtai; print(lingtai.__version__)"`

### Using the managed venv

If the agent is using the TUI's managed venv:

```bash
~/.lingtai-tui/runtime/venv/bin/python3 -m pip install --upgrade lingtai
```

### After Kernel Update

- **Restart the TUI** — agents inherit the new kernel on restart
- **No agent data is lost** — agent state, knowledge, and skills persist across updates

## MCP Addons

MCP addons (imap, telegram, feishu, wechat) are Python packages that the TUI manages:

```bash
pip install --upgrade lingtai-imap lingtai-telegram lingtai-feishu lingtai-wechat
```

Or via the TUI's managed venv:

```bash
~/.lingtai-tui/runtime/venv/bin/python3 -m pip install --upgrade lingtai-imap lingtai-telegram lingtai-feishu lingtai-wechat
```

The TUI runs `/doctor` to trigger addon updates automatically.

## Full Update Checklist

1. `brew update && brew upgrade lingtai-ai/lingtai/lingtai-tui`
2. `pip install --upgrade lingtai lingtai-imap lingtai-telegram lingtai-feishu lingtai-wechat`
3. Restart the TUI
4. Run `/doctor` in TUI
5. Run `python3 "${LINGTAI_SKILL_DIR}/scripts/doctor.py"` as agent
6. Verify all checks pass

## Troubleshooting Updates

### "Cannot import lingtai"

The Python kernel is not installed or the venv is broken:

```bash
# Check which Python the agent uses
~/.lingtai-tui/runtime/venv/bin/python3 -c "import lingtai; print(lingtai.__version__)"
```

If this fails, the venv needs repair. Run `/doctor` in the TUI, which will auto-repair.

### "Version didn't change after update"

The TUI binary may be a symlink to an older Cellar copy:

```bash
# Check where lingtai-tui actually points
ls -la $(which lingtai-tui)
```

If it's a manual symlink, update it to point to the new binary.

### "Kernel version mismatch between TUI and agent"

The TUI and kernel are separate packages with independent version numbers. They do not need to match. An older kernel with a newer TUI (or vice versa) is normal.
