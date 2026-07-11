# Isaac Online Modded Linux

[English](README.md) | [简体中文](README.zh-CN.md)

这是 [xADDBx/Isaac-Online-Modded](https://github.com/xADDBx/Isaac-Online-Modded)
的 Linux/Nix 修改版。

本分支去掉了原项目的 Windows UI，并将 patcher 改写为 Python CLI。目标是在
Linux，尤其是 Steam/Proton 环境下，为 **The Binding of Isaac: Rebirth /
Repentance+** 提供可直接运行的补丁工具。

## 功能

- patch `isaac-ng.exe`，允许开启 mod 时进入在线联机。
- 安装 Repentance+ Lua runtime shim 到 `resources/scripts/main.lua`，让 Lua mod
  可以使用 `RegisterMod`、`Game()` 和 callbacks 等 API。
- 可选 patch **External Item Descriptions**，使其能在在线联机中工作。
- 同时提供普通 Python 入口和 Nix flake 打包。

## 使用

```bash
# 使用 Nix 运行
nix run .#

# 或在源码目录中用 Python 运行
PYTHONPATH=src python -m isaac_online_modded

# 自动检测不够时，手动指定游戏目录
isaac-online-modded --game-dir "$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth"
```

默认 Steam 路径：

```text
$HOME/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng.exe
```

常用命令：

```bash
isaac-online-modded --dry-run
isaac-online-modded --all
isaac-online-modded --patch-lua-runtime
isaac-online-modded --patch-eid
isaac-online-modded --restore
```

写入前会自动创建备份，例如 `isaac-ng.exe.bak`、`main.lua.bak` 和
`eid_api.lua.bak`。

## 开发

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
nix flake check
```
