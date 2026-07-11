# Isaac Online Modded Linux

[English](README.md) | [简体中文](README.zh-CN.md)

一个独立的 Linux/Nix CLI 项目，用于 patch **The Binding of Isaac: Rebirth**
/ Repentance+ 的 `isaac-ng.exe`，从而在在线联机模式中使用 mod。

默认还会应用两类 Lua 侧修复：

- 安装 `resources/scripts/main.lua` 运行时，让 `RegisterMod`、`Game()`、
  `_RunCallback` 等 Lua mod API 入口存在。
- 自动检测 **External Item Descriptions**；如果已安装，就 patch 它的
  `main.lua` 和 `features/eid_api.lua`，使其可以在在线联机中工作。如果没有
  安装 EID，默认模式会自动跳过，不会报错退出。

本项目已经从原 Windows/WPF 工具中拆出：

- 不包含 `.sln` / `.csproj`
- 不包含 WPF UI
- 不包含 Windows publish profile
- 不包含 Windows GitHub Actions 打包流程
- 只保留 Linux CLI、Nix flake、Python 包、内置 Lua 运行时和测试

默认会对 `isaac-ng.exe` 应用两处稳定二进制 patch：

1. 允许开启 mod 时进入在线联机。
2. 禁用 desync analytics sender。

同时会安装缺失的 `resources/scripts/main.lua` 运行时。如果日志中出现
`resources/scripts/main.lua: No such file or directory`，或者 mod 报
`attempt to call a nil value (global 'RegisterMod')`，就需要这个运行时文件。

之前曾加入过一个实验性的 Repentance+ Lua Mod API 二进制 patch，用于尝试修复
`RegisterMod` 为 nil。实际测试发现它可能让游戏停在早期 Lua 初始化阶段，因此
现在默认禁用，只能通过显式参数 `--experimental-lua-api` 使用。

## 默认路径

工具默认检查常见 Steam 安装位置：

```text
$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe
```

同时会读取 Steam 的 `steamapps/libraryfolders.vdf`，因此非默认库目录也可以自动检测。

## 使用 Nix 运行

```bash
# 在本项目目录中运行
nix run .#

# 显式指定默认 Steam 游戏目录
nix run .# -- --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"

# 默认动作：patch 游戏、安装 Lua runtime，并在已安装时启用 EID
nix run .#

# 强制 patch 游戏、Lua runtime 和 External Item Descriptions
nix run .# -- --all

# 仅预览，不写入文件
nix run .# -- --dry-run
```

## 安装到当前用户 profile

```bash
nix profile install .#
isaac-online-modded --help
```

## 直接用 Python 运行

```bash
python -m isaac_online_modded --help
```

在开发目录中运行：

```bash
PYTHONPATH=src python -m isaac_online_modded --help
```

## 常用命令

```bash
# 默认动作：patch 游戏、安装 Lua runtime，并在已安装时自动启用 EID
isaac-online-modded

# patch 游戏和 Lua runtime，但不处理 External Item Descriptions
isaac-online-modded --no-eid

# 打印检测到的 isaac-ng.exe 路径
isaac-online-modded --print-path

# 直接指定可执行文件
isaac-online-modded --game-exe "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe"

# 指定游戏目录
isaac-online-modded --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"

# 只 patch 联机 mod gate 和 desync analytics 逻辑
isaac-online-modded --patch-game

# 只安装 Lua mod API 运行时 resources/scripts/main.lua
isaac-online-modded --patch-lua-runtime

# 默认模式中跳过 Lua runtime 安装
isaac-online-modded --no-lua-runtime

# 实验性 Lua API 二进制 patch。当前候选可能导致游戏无法启动。
isaac-online-modded --patch-game --experimental-lua-api

# 只回滚实验性 Lua API patch，保留两处稳定联机 patch
isaac-online-modded --revert-experimental-lua-api

# 只 patch External Item Descriptions。未安装 EID 时会失败。
isaac-online-modded --patch-eid

# 强制应用所有稳定 patch。未安装 External Item Descriptions 时会失败。
isaac-online-modded --all

# 从 .bak 备份恢复 isaac-ng.exe
isaac-online-modded --restore
```

## 环境变量

```bash
ISAAC_GAME_EXE=/path/to/isaac-ng.exe isaac-online-modded
ISAAC_GAME_DIR="/path/to/The Binding of Isaac Rebirth" isaac-online-modded
STEAM_ROOT="$HOME/.local/share/Steam" isaac-online-modded
```

## 备份

写入前，工具会为每个目标文件创建一次备份：

```text
isaac-ng.exe.bak
main.lua.bak
eid_api.lua.bak
```

已有备份会被复用，不会覆盖。

## 排查：游戏无法启动

如果之前运行过应用了实验性 Lua API 二进制 patch 的版本，游戏可能无法启动。
使用当前工具只回滚该候选 patch，同时保留两处稳定联机 patch：

```bash
isaac-online-modded --revert-experimental-lua-api
```

当前版本默认不会应用该候选 patch。

## 排查：能进入在线联机，但 mod 不生效

如果可以在开启 mod 时进入在线联机，但 EID 等 Lua mod 没有效果，重新运行当前工具：

```bash
nix run .# -- --all
```

Steam 游戏更新可能会覆盖 `isaac-ng.exe`，因此更新后可能需要重新应用二进制
patch。常见 Repentance+ 日志路径：

```text
$HOME/.local/share/Steam/steamapps/compatdata/250900/pfx/drive_c/users/steamuser/Documents/My Games/Binding of Isaac Repentance+/log.txt
```

如果日志包含：

```text
attempt to call a nil value (global 'RegisterMod')
```

说明游戏检测到了 mod 目录，但启动时没有加载 `resources/scripts/main.lua` 运行时。
运行默认命令：

```bash
isaac-online-modded
```

或者只安装运行时：

```bash
isaac-online-modded --patch-lua-runtime
```

旧的 Lua API 二进制 patch 候选已确认会破坏启动，因此默认不使用。

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
nix flake check
```
