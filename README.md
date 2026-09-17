# Sync Bluetooth for dualboot Linux and Windows

**English** | [简体中文](README.zh-CN.md)

User-friendly tool that makes Bluetooth devices work on both Windows and Linux without re-pairing.
See [Dualboot Bluetooth issue](#dualboot-bluetooth-issue).

> **Fork of [x2es/bt-dualboot](https://github.com/x2es/bt-dualboot)** — maintained on the `dev` branch with Clean Architecture refactoring (v2.0.0+).
> PyPI package: `bt-dualboot-ng` · CLI command: `bt-dualboot`

### Highlights

- No need to reboot three times
- Asks for as few details as possible
- Multi-adapter support ([#10](https://github.com/x2es/bt-dualboot/issues/10))
- Preserves Windows-only BLE registry fields ([#33](https://github.com/x2es/bt-dualboot/issues/33))
- … [see all advantages and alternatives](#advantages-and-alternatives)

[Install](#install) · [CLI reference](#cli-reference) · [Developer guide](DEVELOPMENT.md)

---

## Usage: shortest way

Assuming devices are already paired in Windows, boot into Linux and pair them there too.
Syncing is two steps:

### 1. Mount Windows partition

The tool probes and uses a mounted Windows partition automatically. Otherwise use [`-w` / `--win`](#windows-mount-point).
The partition must be mounted with [write access](#troubleshooting-windows-partition-write-access).

### 2. Sync all devices available for sync

```console
$ bt-dualboot -a -b

Elevating privileges via sudo...
Syncing...
==========
 [C2:9E:1D:E2:3D:A5] Keyboard K380
...done
```

**Notes:**

- **Auto sudo** — elevates via sudo when root is needed. Use `--no-elevate` to disable.
- [`--backup` / `--no-backup`](#backup-options) — sync requires one of these explicitly (`-b` or `-n`).
- Use `-d` / `--dry-run` to preview any command’s effects.
- **Short options**: `-a` (sync-all), `-s` (sync), `-d` (dry-run), `-w` (win mount), `-l` (list), `-b` (backup), `-n` (no-backup).

---

## Usage: choose device manually

### 1. List devices

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

(Sections with no devices are omitted, except “Needs sync”, which shows a hint when empty.)

### 2. Sync devices by MAC

```console
$ bt-dualboot -s C2:9E:1D:E2:3D:A5 -b

synced C2:9E:1D:E2:3D:A5 successfully
```

See [`bt-dualboot -h`](#cli-reference) and the sections below for details.

---

## Prerequisites

- Python 3.13+
- `chntpw` package (provides `reged`):

```console
Ubuntu $ sudo apt install chntpw
```

See https://pogostick.net/~pnh/ntpasswd/

---

## Install

```console
$ uv tool install bt-dualboot-ng
```

or with pipx:

```console
$ pipx install bt-dualboot-ng
```

The tool elevates to root via sudo when needed. Use `--no-elevate` to disable auto-elevation.

### Supported OS

Tested with Linux Mint 19.3, 20.3 (Ubuntu 18.04 bionic, 20.04 focal), Windows 10.

Supported:

- Potentially any Linux-based system that keeps Bluetooth configuration in a format similar to Ubuntu
- Windows 10+

More OSes will be tested in later releases; macOS support may be added. If you succeed or fail on an OS not listed here, please share at https://github.com/awsl1414/bt-dualboot/issues.

---

## Advanced usage

### Backup options

Windows Registry updates use `chntpw/reged` without changing the hive file size (`reged -N -E`). `chntpw` is unofficial, so a backup is still recommended. You must choose a backup strategy explicitly (`-b` / `--backup` or `-n` / `--no-backup`).

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

### Restoring from backup

If Windows fails to boot after a sync, restore the backup:

**1. Boot into Linux and find your backup file**

```console
$ ls /var/backup/bt-dualboot/
SYSTEM-2026-06-07--14-30-00
```

**2. Mount your Windows partition**

```console
$ sudo mount /dev/sdXn /mnt/windows
```

Use `lsblk -f` to find the correct partition if unsure.

**3. Replace the Windows registry hive**

```console
$ sudo cp /mnt/windows/Windows/System32/config/SYSTEM /mnt/windows/Windows/System32/config/SYSTEM.broken
$ sudo cp /var/backup/bt-dualboot/SYSTEM-2026-06-07--14-30-00 /mnt/windows/Windows/System32/config/SYSTEM
```

**4. Reboot into Windows**

If Windows still does not boot, use Windows Automatic Repair / System Restore.

### Windows mount point

By default the tool finds and uses mounted Windows partitions. If several are found, you are prompted to select one or more (single, comma-separated, ranges, or `all`). Use `-w` / `--win` to set a mount point directly.

Use `--list-win-mounts` to list recognized Windows partitions.

```console
$ bt-dualboot --list-win-mounts

Windows locations:
==================
 /media/user/win_foo
 /media/user/win_bar

$ bt-dualboot -w /media/user/win_foo -l
```

When multiple Windows partitions are mounted:

```console
$ bt-dualboot -a -b

Multiple Windows locations found:
  [1] /media/user/win_foo
  [2] /media/user/win_bar

Select (e.g. 1 or 1,3 or all): 1
```

In non-interactive or `--bot` mode, multiple mounts require `-w MOUNT` (the tool prints the list and exits).

#### Troubleshooting: Windows partition write access

If the Windows partition is mounted read-only, remount it read-write:

```console
$ sudo mount -o remount,rw /mnt/win/path
```

### Machine processing

`--bot` enables more parsable output for scripts (currently supported for `-l`).

---

## Dualboot Bluetooth issue

Every time a Bluetooth device is paired in one dual-boot OS, it stops working in the other. Both OSes use the same adapter MAC; each pairing generates new keys, so the key stored in the other OS becomes obsolete.

The solution is to sync saved pairing keys. Manual approaches: https://unix.stackexchange.com/a/255510/411221

This tool follows the approach from [this comment](https://unix.stackexchange.com/questions/255509/bluetooth-pairing-on-dual-boot-of-windows-linux-mint-ubuntu-stop-having-to-p#comment545967_255510): copy pairing keys from Linux into the Windows registry, avoiding multiple reboots.

---

## Advantages and alternatives

**bt-dualboot:**

- Does not require multiple reboots
- [Simple install](#install)
- Single [CLI](#cli-reference); no extra scripts
- Discovers mounted Windows partitions automatically
- Safe registry update without changing hive file size (rewrite only)
- [Backup](#backup-options) before update
- No import/export files or encoding hassles
- `--dry-run` before real changes

### Alternatives

**Automatic bidirectional sync (service / EFI share):**

- https://github.com/meowrch/BlueVein

**Linux → Windows registry** (same direction as bt-dualboot):

- https://github.com/KeyofBlueS/bt-keys-sync — also supports Windows → Linux

**Windows → Linux:**

- https://github.com/vvoland/linkwinbt
- https://github.com/sermuns/dualboot-bt-link-keys — read-only Windows mount; no `chntpw`
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

**macOS:**

- https://github.com/HenrySeed/macosDualBootingBluetoothKeys
- https://github.com/sarneeh/mac-win-dualboot-bt

---

## CLI reference

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


