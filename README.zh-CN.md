# 双系统 Linux / Windows 蓝牙配对同步

[English](README.md) | **简体中文**

让蓝牙设备在 Windows 与 Linux 双系统下共用，无需反复重新配对。
详见 [双系统蓝牙问题](#双系统蓝牙问题)。

> **[x2es/bt-dualboot](https://github.com/x2es/bt-dualboot) 的分支维护版** — 在 `dev` 分支以 Clean Architecture 重构（v2.0.0+）。
> PyPI 包名：`bt-dualboot-ng` · 命令行：`bt-dualboot`

### 亮点

- 无需重启三次
- 尽量少问配置细节
- 多蓝牙适配器支持（[#10](https://github.com/x2es/bt-dualboot/issues/10)）
- 保留 Windows 独有的 BLE 注册表字段（[#33](https://github.com/x2es/bt-dualboot/issues/33)）
- … [更多优势与替代方案](#优势与替代方案)

[安装](#安装) · [命令行参考](#命令行参考) · [开发指南](DEVELOPMENT.md)

---

## 用法：最快路径

假设设备已在 Windows 中配对，再启动到 Linux 并完成配对。
同步只需两步：

### 1. 挂载 Windows 分区

工具会自动探测并使用已挂载的 Windows 分区；也可使用 [`-w` / `--win`](#windows-挂载点) 指定路径。
分区须以[可写方式](#故障排查windows-分区写权限)挂载。

### 2. 同步所有可同步设备

```console
$ bt-dualboot -a -b

Elevating privileges via sudo...
Syncing...
==========
 [C2:9E:1D:E2:3D:A5] Keyboard K380
...done
```

**说明：**

- **自动 sudo** — 需要 root 时会通过 sudo 提权。可用 `--no-elevate` 关闭。
- [`--backup` / `--no-backup`](#备份选项) — 同步时必须显式指定其一（`-b` 或 `-n`）。
- 使用 `-d` / `--dry-run` 可预览命令效果而不实际写入。
- **短选项**：`-a`（全部同步）、`-s`（指定同步）、`-d`（演练）、`-w`（Windows 挂载点）、`-l`（列表）、`-b`（备份）、`-n`（不备份）。

---

## 用法：手动选择设备

### 1. 列出设备

```console
$ bt-dualboot -l

Works both in Linux and Windows
===============================
 [A4:BF:C6:D0:E5:FF] WH-1000XM4

Needs sync
==========

Following devices available for sync with `--sync-all` or `--sync MAC` options.

 [C2:9E:1D:E2:3D:A5] Keyboard K380

Have to be paired in Windows
============================

Following devices unavailable for sync unless you boot Windows and pair them

 [E9:1D:FE:2A:C3:C8] JBL GO

Missing pairing key
===================

Following devices do not have a pairing key and cannot be synced

 [AA:BB:CC:DD:EE:FF] Some Device
```

（无设备的分区段会省略；「Needs sync」在为空时仍会给出提示。）

### 2. 按 MAC 同步设备

```console
$ bt-dualboot -s C2:9E:1D:E2:3D:A5 -b

synced C2:9E:1D:E2:3D:A5 successfully
```

更多细节见 [`bt-dualboot -h`](#命令行参考) 及下文。

---

## 前置条件

- Python 3.13+
- 系统已安装 `chntpw`（提供 `reged`）：

```console
Ubuntu $ sudo apt install chntpw
```

参见 https://pogostick.net/~pnh/ntpasswd/

---

## 安装

```console
$ uv tool install bt-dualboot-ng
```

或使用 pipx：

```console
$ pipx install bt-dualboot-ng
```

需要时工具会通过 sudo 提权。可用 `--no-elevate` 关闭自动提权。

### 支持的系统

已在 Linux Mint 19.3、20.3（Ubuntu 18.04 bionic、20.04 focal）与 Windows 10 上测试。

支持范围：

- 理论上任何以类似 Ubuntu 方式保存蓝牙配置的 Linux 发行版
- Windows 10+

后续版本会扩充测试范围，也可能加入 macOS。若你在未列出的系统上成功或失败，欢迎在 https://github.com/awsl1414/bt-dualboot/issues 反馈。

---

## 进阶用法

### 备份选项

更新 Windows 注册表时使用 `chntpw/reged`，且不改变 Hive 文件大小（`reged -N -E`）。`chntpw` 为非官方工具，仍建议备份。必须显式选择备份策略（`-b` / `--backup` 或 `-n` / `--no-backup`）。

```console
$ bt-dualboot -a
usage: ....
bt-dualboot: error: Neither backup option given!

    Windows Registry Hive file will be updated!
    chntpw/reged tool is non-official and hackish Hive file editing tool.
    It is recommended to do backup prior writing into Hive file.

    Use:
      -b [path], --backup [path]    [default: /var/backup/bt-dualboot]
      -n, --no-backup               process without backup

    WARNING:
        Windows Registry Hive file may contain sensitive data. You shouldn't keep this file
        on a storage which may be accessed by others. Consider to remove backup files as soon
        as possible after ensure Windows boots and works correctly.
```

### 从备份恢复

若同步后 Windows 无法启动，可按如下步骤恢复：

**1. 进入 Linux，找到备份文件**

```console
$ ls /var/backup/bt-dualboot/
SYSTEM-2026-06-07--14-30-00
```

**2. 挂载 Windows 分区**

```console
$ sudo mount /dev/sdXn /mnt/windows
```

不确定分区时可用 `lsblk -f` 查看。

**3. 替换 Windows 注册表 Hive**

```console
$ sudo cp /mnt/windows/Windows/System32/config/SYSTEM /mnt/windows/Windows/System32/config/SYSTEM.broken
$ sudo cp /var/backup/bt-dualboot/SYSTEM-2026-06-07--14-30-00 /mnt/windows/Windows/System32/config/SYSTEM
```

**4. 重启进入 Windows**

若仍无法启动，可使用 Windows 自动修复 / 系统还原。

### Windows 挂载点

默认自动识别已挂载的 Windows 分区。若发现多个，会提示选择（支持单个、逗号分隔、区间或 `all`）。也可用 `-w` / `--win` 直接指定挂载点。

使用 `--list-win-mounts` 列出已识别的 Windows 分区：

```console
$ bt-dualboot --list-win-mounts

Windows locations:
==================
 /media/user/win_foo
 /media/user/win_bar

$ bt-dualboot -w /media/user/win_foo -l
```

多个 Windows 分区已挂载时：

```console
$ bt-dualboot -a -b

Multiple Windows locations found:
  [1] /media/user/win_foo
  [2] /media/user/win_bar

Select (e.g. 1 or 1,3 or all): 1
```

非交互或 `--bot` 模式下，存在多个挂载点时必须用 `-w MOUNT` 指定（工具会打印列表并退出）。

#### 故障排查：Windows 分区写权限

若 Windows 分区以只读方式挂载，需重新挂载为可写：

```console
$ sudo mount -o remount,rw /mnt/win/path
```

### 机器可读输出

`--bot` 会输出更易解析的格式，便于脚本使用（当前支持 `-l`）。

---

## 双系统蓝牙问题

在双系统中，设备在一侧配对后，另一侧往往会失效。两边共用同一块蓝牙适配器与 MAC；每次配对都会生成新密钥，另一侧已保存的密钥随即失效。

解决办法是同步两侧已保存的配对密钥。手动处理说明：https://unix.stackexchange.com/a/255510/411221

本工具采用[该评论](https://unix.stackexchange.com/questions/255509/bluetooth-pairing-on-dual-boot-of-windows-linux-mint-ubuntu-stop-having-to-p#comment545967_255510)中的思路：直接把 Linux 侧配对密钥写入 Windows 注册表，避免多次重启。

---

## 优势与替代方案

**bt-dualboot：**

- 无需多次重启
- [安装简单](#安装)
- 单一 [CLI](#命令行参考)，无需额外脚本
- 自动发现已挂载的 Windows 分区
- 安全更新注册表且不改变 Hive 文件大小（仅重写）
- 更新前可[备份](#备份选项)
- 无需导入/导出文件，也无编码问题
- 可用 `--dry-run` 先演练再正式写入

### 替代方案

**自动双向同步（后台服务 / EFI 共享）：**

- https://github.com/meowrch/BlueVein

**Linux → Windows 注册表**（与 bt-dualboot 同向）：

- https://github.com/KeyofBlueS/bt-keys-sync — 亦支持 Windows → Linux

**Windows → Linux：**

- https://github.com/vvoland/linkwinbt
- https://github.com/sermuns/dualboot-bt-link-keys — 只读挂载 Windows；不依赖 `chntpw`
- https://github.com/mos9527/bt-synckeys
- https://pypi.org/project/btkey-sync/
- [GUI] https://github.com/nagi1999a/BluetoothDualBootHelper
- https://github.com/ademlabs/synckeys
- https://github.com/Anuvind-ap/bluesync
- https://github.com/arunpandian7/DuoPair-Bluetooth
- https://github.com/Krakenus/bluetooth-dualboot-fixer
- https://github.com/LondonAppDev/dual-boot-bluetooth-pair
- https://github.com/heyzec/dual-boot-mouse
- https://github.com/luismaf/bluetooth-dual-boot
- https://github.com/aryklein/dualBootMouse

**macOS：**

- https://github.com/HenrySeed/macosDualBootingBluetoothKeys
- https://github.com/sarneeh/mac-win-dualboot-bt

---

## 命令行参考

```console
$ bt-dualboot -h
usage: bt-dualboot [-h] [--version] [-l] [--list-win-mounts] [--bot] [-d] [-w MOUNT] [-s MAC [MAC ...]] [-a] [-n] [-b [path]]
                   [--no-elevate]

Sync bluetooth keys from Linux to Windows (v2.1.1)

options:
  -h, --help            show this help message and exit
  --version             print version
  --no-elevate          do not auto-elevate to root via sudo

List resources:
  -l, --list            [root required] list bluetooth devices
  --list-win-mounts     list mounted Windows locations
  --bot                 parsable output for robots (supported: -l)

Sync keys:
  -d, --dry-run         print actions to do without invocation
  -w, --win MOUNT       Windows mount point (advanced usage)
  -s, --sync MAC [MAC ...]
                        [root required] sync specified device
  -a, --sync-all        [root required] sync all paired devices

Backup Windows Registry:
  -n, --no-backup       process without backup
  -b, --backup [path]   path to backup directory, default: /var/backup/bt-dualboot
```


