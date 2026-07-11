# Isaac Online Modded Linux

独立的 Linux/Nix CLI 项目，用于 patch **The Binding of Isaac: Rebirth**
的 `isaac-ng.exe`，从而在在线联机模式中启用 mod。

同时支持 **External Item Descriptions**：默认运行时会自动检测该 mod，
如果已安装就 patch `main.lua` 和 `features/eid_api.lua`，让它可以在联机
模式中使用；如果没有安装则自动跳过。

这个项目已经从原 Windows/WPF 工具中拆出：

- 不包含 `.sln` / `.csproj`
- 不包含 WPF UI
- 不包含 Windows publish profile
- 不包含 GitHub Actions Windows 打包流程
- 只保留 Linux 可运行 CLI、Nix flake、Python 包和测试

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

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
nix flake check
```
