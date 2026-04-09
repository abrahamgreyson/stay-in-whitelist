# Phase 5: Operational Deployment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 05-operational-deployment
**Areas discussed:** 调度器配置, 日志轮转, systemd 服务模板, Python 路径

---

## 调度器配置

| Option | Description | Selected |
|--------|-------------|----------|
| 300 秒（5 分钟）— 推荐 | 对于 10 分钟检查间隔，5 分钟的宽限期是合理的安全边界。允许系统负载或短暂延迟而不跳过检查。 | ✓ |
| 600 秒（10 分钟） | 更宽容的设置，允许更多延迟但不跳过检查。适合网络不稳定的环境。 | |
| 60 秒（1 分钟） | 严格模式，如果检查延迟超过 1 分钟就跳过。适合对时间精度要求高的场景。 | |

**User's choice:** 300 秒（5 分钟）— 推荐
**Notes:** 对于 10 分钟（600 秒）的检查间隔，5 分钟宽限期提供合理的容错空间。

---

## 日志轮转

| Option | Description | Selected |
|--------|-------------|----------|
| 每日轮转，30 天备份 — 推荐 | 每天午夜轮转一次，保留 30 个备份文件（30 天）。简单清晰，日志文件大小可控，符合审计要求。 | ✓ |
| 保持小时轮转，30 个备份 | 保持当前每小时轮转（实际每 24 小时生成一个新文件），但保留 30 个备份。日志文件更小但数量更多。 | |
| 按大小轮转（如 10MB）+ 30 天 | 当单个日志文件达到指定大小时轮转，保留总大小约 30 天的日志。适合日志量波动大的场景。 | |

**User's choice:** 每日轮转，30 天备份 — 推荐
**Notes:** 需要更新 `logger.py` 中的两个函数：`get_logger()` 和 `reconfigure_logging()`，从 `when='H', interval=24, backupCount=7` 改为 `when='midnight', interval=1, backupCount=30`。

---

## systemd 服务模板

| Option | Description | Selected |
|--------|-------------|----------|
| 提供模板文件 — 推荐 | 创建 systemd 服务单元模板文件，使用标准 Linux 路径约定（/usr/local/bin/、/var/log/ 等）。用户可自定义路径。 | ✓ |
| 仅在 README 中说明 | 在文档中说明如何创建 systemd 服务，但不提供模板文件。用户自行决定路径和配置。 | |

**User's choice:** 提供模板文件 — 推荐
**Notes:** 创建 `stay-in-whitelist.service` 模板文件，包含 WorkingDirectory、ExecStart、StandardOutput、StandardError 路径。

---

## Python 路径

| Option | Description | Selected |
|--------|-------------|----------|
| 指向 venv 中的 Python — 推荐 | 使用虚拟环境的 Python 解释器（如 /opt/stay-in-whitelist/venv/bin/python）。确保依赖隔离，推荐用于生产环境。 | ✓ |
| 指向系统 Python | 使用系统级 Python（/usr/bin/python3）。需要系统级安装依赖，适合容器化部署。 | |

**User's choice:** 指向 venv 中的 Python — 推荐
**Notes:** ExecStart 应指向虚拟环境的 Python 解释器（如 `/opt/stay-in-whitelist/venv/bin/python`），确保依赖隔离。

---

## Claude's Discretion

- systemd 服务模板中是否包含网络依赖（`After=network.target`, `Wants=network-online.target`）
- 是否添加 `User=` 和 `Group=` 字段指定运行用户
- 服务模板文件是否使用占位符或直接提供示例路径
- 是否需要创建日志目录的说明

## Deferred Ideas

None — discussion stayed within phase scope
