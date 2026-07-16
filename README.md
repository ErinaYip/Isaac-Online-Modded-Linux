# Isaac Online Modded Linux

[English](README.md) | [简体中文](README.zh-CN.md)

A small Linux/uv version of
[xADDBx/Isaac-Online-Modded](https://github.com/xADDBx/Isaac-Online-Modded).

This fork removes the Windows UI and rewrites the patcher as a Python CLI. It is
intended for **The Binding of Isaac: Rebirth / Repentance+** on Linux,
especially Steam/Proton installs.

## What it does

- Patches `isaac-ng.exe` so online co-op can be entered with mods enabled.
- Installs the Repentance+ Lua runtime shim at `resources/scripts/main.lua` so
  Lua mods can access APIs such as `RegisterMod`, `Game()`, and callbacks.
- Optionally patches **External Item Descriptions** for online co-op.
- Uses pure uv for environment management, running, and builds.

## Usage

```bash
# Run from the source tree with uv
uv run isaac-online-modded

# Specify the game directory if auto-detection is not enough
uv run isaac-online-modded --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"
```

Default Steam path:

```text
$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe
```

Useful commands:

```bash
uv run isaac-online-modded --dry-run
uv run isaac-online-modded --all
uv run isaac-online-modded --patch-lua-runtime
uv run isaac-online-modded --patch-eid
uv run isaac-online-modded --restore
```

Backups are created before writing, for example `isaac-ng.exe.bak`,
`main.lua.bak`, and `eid_api.lua.bak`.

## Development

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv lock --check
uv build
```
