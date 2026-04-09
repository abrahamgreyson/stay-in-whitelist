# Phase 5: Operational Deployment - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

配置 APScheduler 和日志系统，确保守护进程在生产环境 systemd 服务中可靠运行。Phase 完成后：APScheduler 不会因 misfire 静默跳过检查、systemd 服务模板引用正确的路径、日志保留 30 天提供充足的审计跟踪。

Requirements: OPS-01, OPS-02, OPS-03

</domain>

<decisions>
## Implementation Decisions

### APScheduler Misfire 配置 (OPS-01)
- **D-01:** APScheduler 配置显式的 `misfire_grace_time = 300` 秒（5 分钟）
- **D-02:** 对于 10 分钟（600 秒）的检查间隔，5 分钟宽限期提供合理的容错空间
- **D-03:** 在 `main.py` 中，`scheduler.add_job()` 之前调用 `scheduler.configure(job_defaults={...})` 配置全局作业默认值
- **D-04:** job_defaults 应包含：`misfire_grace_time=300`, `coalesce=True`, `max_instances=1`

### 日志轮转策略 (OPS-03)
- **D-05:** 日志轮转从 7 天增加到 30 天保留期
- **D-06:** 轮转策略改为每日午夜轮转（`when='midnight', interval=1, backupCount=30`）
- **D-07:** 更新 `logger.py` 中的两个函数：
  - `get_logger()` line 26: 改为 `when='midnight', interval=1, backupCount=30`
  - `reconfigure_logging()` line 53: 改为 `when='midnight', interval=1, backupCount=30`
- **D-08:** 保留现有格式 `'%(asctime)s - %(levelname)s - %(message)s'` 不变

### systemd 服务模板 (OPS-02)
- **D-09:** 创建 `stay-in-whitelist.service` 模板文件在项目根目录
- **D-10:** 服务单元包含：
  - `Type=simple`
  - `WorkingDirectory=/opt/stay-in-whitelist`（示例路径，用户可自定义）
  - `ExecStart=/opt/stay-in-whitelist/venv/bin/python /opt/stay-in-whitelist/main.py`
  - `StandardOutput=append:/var/log/stay-in-whitelist/systemd-stdout.log`
  - `StandardError=append:/var/log/stay-in-whitelist/systemd-stderr.log`
  - `Restart=on-failure`
  - `RestartSec=5s`
- **D-11:** README 中添加部署说明：复制服务文件到 `/etc/systemd/system/`，自定义路径，启用服务

### Claude's Discretion
- systemd 服务模板中是否包含 `After=network.target` 和 `Wants=network-online.target`（网络依赖）
- 是否添加 `User=` 和 `Group=` 字段指定运行用户
- 服务模板文件是否使用占位符（如 `{{PROJECT_ROOT}}`）或直接提供示例路径
- 是否需要创建日志目录 `/var/log/stay-in-whitelist/` 的说明

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### APScheduler Configuration (OPS-01)
- `main.py` — 调度入口，line 79-81 需添加 `scheduler.configure(job_defaults={...})`
- `.planning/phases/05-operational-deployment/05-RESEARCH.md` — APScheduler misfire 处理最佳实践

### Log Rotation (OPS-03)
- `stay_in_whitelist/logger.py` — line 26, 53 需更新 TimedRotatingFileHandler 参数
- `.planning/phases/05-operational-deployment/05-RESEARCH.md` — Python logging TimedRotatingFileHandler 配置模式

### systemd Service (OPS-02)
- `main.py` — 程序入口，systemd ExecStart 指向此文件
- `.planning/phases/05-operational-deployment/05-RESEARCH.md` — systemd 服务单元配置最佳实践

### Prior Phase Context
- `.planning/phases/02-configuration-hardening/02-CONTEXT.md` — Phase 2 D-09: check_interval 最小值 600 秒
- `.planning/phases/04-project-identity/04-CONTEXT.md` — Phase 4 D-08: 日志文件名改为 stay_in_whitelist.log

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- APScheduler BlockingScheduler: 已在 `main.py` 中使用，只需添加 `configure()` 调用
- TimedRotatingFileHandler: 已在 `logger.py` 中使用，只需修改参数

### Established Patterns
- Logger 使用模式: `logger.py` 提供两个函数 — `get_logger()` 用于初始化，`reconfigure_logging()` 用于路径重配置
- APScheduler 集成: `main.py:79-81` 使用 `BlockingScheduler` + `add_job()` + `partial(check_and_update_ip, config=config)`

### Integration Points
- `main.py:79` — `scheduler = BlockingScheduler()` 之后需添加 `scheduler.configure(job_defaults={...})`
- `logger.py:26` — `TimedRotatingFileHandler('stay_in_whitelist.log', when='H', interval=24, backupCount=7)` 需改为 `when='midnight', interval=1, backupCount=30`
- `logger.py:53` — `reconfigure_logging()` 中的 TimedRotatingFileHandler 需同步修改

</code_context>

<specifics>
## Specific Ideas

- "日志文件名从 update_whitelist.log 改为 stay_in_whitelist.log" — Phase 4 已完成，本 phase 只需修改保留期
- "systemd 服务模板应该提供清晰的路径示例，用户可以根据实际部署位置修改" — 服务文件使用注释说明哪些路径需要自定义

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-operational-deployment*
*Context gathered: 2026-04-08*
