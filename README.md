# Isaac Online Modded Linux

A standalone Linux/Nix CLI project for patching **The Binding of Isaac: Rebirth**
/ Repentance+ `isaac-ng.exe` so mods can be used in online co-op.

It also applies two Lua-side fixes by default:

- Installs a `resources/scripts/main.lua` runtime so Lua mod API entry points such
  as `RegisterMod`, `Game()`, and `_RunCallback` exist.
- Automatically detects **External Item Descriptions** when installed and patches
  its `main.lua` and `features/eid_api.lua` so it can work in online co-op. If
  EID is not installed, the default mode skips it without failing.

This project has been split out from the original Windows/WPF tool:

- No `.sln` / `.csproj`
- No WPF UI
- No Windows publish profile
- No Windows GitHub Actions packaging workflow
- Only a Linux CLI, Nix flake, Python package, bundled Lua runtime, and tests

By default, the tool applies two binary patches to `isaac-ng.exe`:

1. Allows entering online co-op while mods are enabled.
2. Disables the desync analytics sender.

It also installs the missing `resources/scripts/main.lua` runtime. This runtime is
required if the log contains `resources/scripts/main.lua: No such file or
directory`, or if mods fail with `attempt to call a nil value (global
'RegisterMod')`.

An experimental Repentance+ Lua Mod API binary patch was previously added to try
to fix `RegisterMod` being nil. Testing showed that it can stop the game during
early Lua initialization, so it is disabled by default and only available through
the explicit `--experimental-lua-api` flag.

## Default path

The tool checks common Steam install locations by default:

```text
$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe
```

It also reads Steam's `steamapps/libraryfolders.vdf`, so non-default library
folders can be detected automatically.

## Run with Nix

```bash
# From inside this project directory
nix run .#

# Explicitly use the default Steam game directory
nix run .# -- --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"

# Default action: patch the game, install the Lua runtime, and enable EID if installed
nix run .#

# Force patching the game, Lua runtime, and External Item Descriptions
nix run .# -- --all

# Preview only; do not write files
nix run .# -- --dry-run
```

## Install to the current user profile

```bash
nix profile install .#
isaac-online-modded --help
```

## Run directly with Python

```bash
python -m isaac_online_modded --help
```

When running from the development checkout:

```bash
PYTHONPATH=src python -m isaac_online_modded --help
```

## Common commands

```bash
# Default action: patch the game, install the Lua runtime, and auto-enable EID if installed
isaac-online-modded

# Patch the game and Lua runtime, but do not handle External Item Descriptions
isaac-online-modded --no-eid

# Print the detected isaac-ng.exe path
isaac-online-modded --print-path

# Specify the executable directly
isaac-online-modded --game-exe "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe"

# Specify the game directory
isaac-online-modded --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"

# Only patch the online mod gate and desync analytics logic
isaac-online-modded --patch-game

# Only install the Lua mod API runtime at resources/scripts/main.lua
isaac-online-modded --patch-lua-runtime

# Skip Lua runtime installation in the default mode
isaac-online-modded --no-lua-runtime

# Experimental Lua API binary patch. This candidate can prevent the game from starting.
isaac-online-modded --patch-game --experimental-lua-api

# Revert only the experimental Lua API patch while keeping the two stable online patches
isaac-online-modded --revert-experimental-lua-api

# Only patch External Item Descriptions. Fails if EID is not installed.
isaac-online-modded --patch-eid

# Force all supported stable patches. Fails if External Item Descriptions is not installed.
isaac-online-modded --all

# Restore isaac-ng.exe from its .bak backup
isaac-online-modded --restore
```

## Environment variables

```bash
ISAAC_GAME_EXE=/path/to/isaac-ng.exe isaac-online-modded
ISAAC_GAME_DIR="/path/to/The Binding of Isaac Rebirth" isaac-online-modded
STEAM_ROOT="$HOME/.local/share/Steam" isaac-online-modded
```

## Backups

Before writing, the tool creates one backup per target file:

```text
isaac-ng.exe.bak
main.lua.bak
eid_api.lua.bak
```

Existing backups are reused and are not overwritten.

## Troubleshooting: the game does not start

If you previously ran a build that applied the experimental Lua API binary patch,
the game may fail to start. Use the current tool to revert only that candidate
patch while keeping the two stable online patches:

```bash
isaac-online-modded --revert-experimental-lua-api
```

Current versions do not apply that candidate patch by default.

## Troubleshooting: online co-op starts, but mods do not work

If you can enter online co-op with mods enabled, but Lua mods such as EID have no
effect, rerun the current tool:

```bash
nix run .# -- --all
```

Steam game updates can overwrite `isaac-ng.exe`, so the binary patches may need
to be reapplied after updates. The usual Repentance+ log path is:

```text
$HOME/.local/share/Steam/steamapps/compatdata/250900/pfx/drive_c/users/steamuser/Documents/My Games/Binding of Isaac Repentance+/log.txt
```

If the log contains:

```text
attempt to call a nil value (global 'RegisterMod')
```

then the game detected the mod folders, but did not load the
`resources/scripts/main.lua` runtime during startup. Run the default command:

```bash
isaac-online-modded
```

Or install only the runtime:

```bash
isaac-online-modded --patch-lua-runtime
```

The old Lua API binary patch candidate is known to break startup, so it is not
used by default.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
nix flake check
```
