# Isaac Online Modded Linux

独立的 Linux/Nix CLI 项目，用于 patch **The Binding of Isaac: Rebirth**
的 `isaac-ng.exe`，从而在在线联机模式中启用 mod。

同时支持两类 Lua 侧修复：

- 默认安装 `resources/scripts/main.lua` 运行时，让 `RegisterMod`、`Game()`、
  `_RunCallback` 等 Lua mod API 入口存在。
- 默认自动检测 **External Item Descriptions**，如果已安装就 patch
  `main.lua` 和 `features/eid_api.lua`，让它可以在联机模式中使用；如果没有
  安装则自动跳过。

这个项目已经从原 Windows/WPF 工具中拆出：

- 不包含 `.sln` / `.csproj`
- 不包含 WPF UI
- 不包含 Windows publish profile
- 不包含 GitHub Actions Windows 打包流程
- 只保留 Linux 可运行 CLI、Nix flake、Python 包和测试

当前默认只 patch 两处 `isaac-ng.exe` 逻辑：

1. 允许开启 mod 时进入在线联机。
2. 关闭 desync analytics sender。

另外会安装缺失的 `resources/scripts/main.lua`。如果日志里有
`resources/scripts/main.lua: No such file or directory`，或者各个 mod 报
`RegisterMod` 为 nil，就需要这个运行时文件。

曾经加入过一个 Repentance+ Lua Mod API 候选 patch，用来尝试修复
`RegisterMod` 为 nil；实际测试会导致游戏启动停在早期 Lua 初始化阶段，
因此现在默认禁用，只保留为显式实验参数 `--experimental-lua-api`。

## 默认路径

默认检测 Steam 常见安装位置：

```text
$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe
```

同时会读取 Steam 的 `steamapps/libraryfolders.vdf`，因此非默认库目录也可自动检测。

## 使用 Nix 运行

```bash
# 在本项目目录内
nix run .#

# 明确指定 Steam 默认游戏目录
nix run .# -- --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"

# 默认 patch 游戏本体；如果安装了 External Item Descriptions，也会自动启用
nix run .#

# 强制同时 patch 游戏本体和 External Item Descriptions
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

开发目录运行时：

```bash
PYTHONPATH=src python -m isaac_online_modded --help
```

## 常用命令

```bash
# 默认动作：patch game，并在已安装时自动允许 External Item Descriptions
isaac-online-modded

# 只 patch 游戏，不处理 External Item Descriptions
isaac-online-modded --no-eid

# 显示检测到的 isaac-ng.exe 路径
isaac-online-modded --print-path

# 指定 exe
isaac-online-modded --game-exe "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe"

# 指定游戏目录
isaac-online-modded --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"

# 只 patch 游戏联机 mod 检测和 desync analytics
isaac-online-modded --patch-game

# 只安装 Lua mod API 运行时 resources/scripts/main.lua
isaac-online-modded --patch-lua-runtime

# 默认动作中跳过 Lua runtime 安装
isaac-online-modded --no-lua-runtime

# 实验性 Lua API patch：当前候选可能导致游戏打不开，默认不要使用
isaac-online-modded --patch-game --experimental-lua-api

# 只回滚实验性 Lua API patch，保留前两项联机 patch
isaac-online-modded --revert-experimental-lua-api

# 只 patch External Item Descriptions；未安装时会报错
isaac-online-modded --patch-eid

# 强制两者都 patch；External Item Descriptions 未安装时会报错
isaac-online-modded --all

# 从 .bak 恢复 isaac-ng.exe
isaac-online-modded --restore
```

## 环境变量

```bash
ISAAC_GAME_EXE=/path/to/isaac-ng.exe isaac-online-modded
ISAAC_GAME_DIR="/path/to/The Binding of Isaac Rebirth" isaac-online-modded
STEAM_ROOT="$HOME/.local/share/Steam" isaac-online-modded
```

## 备份

写入前会自动创建一次备份：

```text
isaac-ng.exe.bak
main.lua.bak
eid_api.lua.bak
```

备份已存在时不会覆盖。

## 排查：游戏打不开

如果之前运行过带 Lua API 候选 patch 的版本，游戏可能会打不开。先用新版工具
只回滚该候选 patch，保留前两项联机 patch：

```bash
isaac-online-modded --revert-experimental-lua-api
```

当前新版默认不会再写入该候选 patch。

## 排查：能进联机但 mod 不生效

如果能在开启 mod 的情况下进入联机，但 EID 等 Lua mod 没有效果，先重新运行：

```bash
nix run .# -- --all
```

Steam 更新游戏后会覆盖 `isaac-ng.exe`，需要重新 patch。典型日志位置：

```text
$HOME/.local/share/Steam/steamapps/compatdata/250900/pfx/drive_c/users/steamuser/Documents/My Games/Binding of Isaac Repentance+/log.txt
```

如果日志里出现：

```text
attempt to call a nil value (global 'RegisterMod')
```

说明游戏扫描到了 mod，但启动阶段没有加载 `resources/scripts/main.lua`
运行时。重新运行新版默认命令：

```bash
isaac-online-modded
```

或只安装运行时：

```bash
isaac-online-modded --patch-lua-runtime
```

旧的二进制 Lua API 候选 patch 已确认会导致启动失败，所以不再默认使用。

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
nix flake check
```
