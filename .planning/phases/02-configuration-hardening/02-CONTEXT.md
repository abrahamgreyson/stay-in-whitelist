# Phase 2: Configuration Hardening - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

让 daemon 安全加载配置、在 systemd 下正确写入文件路径、消除 Pydantic 弃用警告。Phase 完成后：检查间隔可配置、文件路径基于绝对路径（兼容 systemd）、import config 不触发 I/O、无 Pydantic 弃用警告、Updater.client 为实例变量。

Requirements: CONF-01, CONF-02, CONF-03, CONF-04, QUAL-04

</domain>

<decisions>
## Implementation Decisions

### 配置初始化模式 (CONF-03)
- **D-01:** 使用显式 `load_config(path)` 函数加载配置。其他模块通过函数参数接收 config，不再直接 import 模块级单例
- **D-08:** `check_and_update_ip(config)` 直接接收 config 参数。APScheduler 使用 `functools.partial` 传递 config
- **D-12:** `ip_fetcher.py` 的公开函数（`get_current_ip(config)` 等）直接接收 config 参数，消除模块级 config import

### 文件路径策略 (CONF-02)
- **D-02:** 文件路径默认自动解析到项目根目录（config.yaml 所在位置），用户可通过 config.yaml 覆盖
- **D-11:** pathlib 仅用于 Phase 2 新增/修改的路径代码，已有 os.path 代码保持不动
- **D-15:** 配置键名：`paths.ip_cache` 和 `paths.log_file`，Pydantic `Paths` 模型持有这两个可选字段

### Logger-Config 初始化顺序
- **D-05:** Logger 先用默认路径（项目根目录）初始化。`load_config()` 成功后，按需调用 reconfigure 更新日志路径。无循环依赖

### 新增配置字段 (CONF-01)
- **D-03:** `check_interval` 和 `paths` 平铺在 Config 顶层，与 `timeouts` 结构对称
- **D-09:** check_interval 最小值 600 秒（10 分钟），无实质上限。Pydantic validator 校验

### Pydantic API 迁移 (CONF-04)
- config.dict() 全部替换为 config.model_dump()

### Updater.client 共享状态修复 (QUAL-04)
- **D-04:** 将 `client = None` 从类变量移到 `__init__` 中作为 `self.client = None`。最小改动

### Updater 遍历 config 的方式
- **D-10:** Updater 改为直接遍历 Pydantic 对象属性（`config.huawei`, `config.tencent` 等），获得类型提示和 IDE 补全

### 错误处理
- **D-07:** `load_config()` 快速失败：文件缺失/YAML 解析错误/Pydantic 校验失败都抛明确异常。调用方（main.py）捕获并退出。不自动生成配置
- **D-14:** 使用标准异常：FileNotFoundError（文件不存在）/ yaml.YAMLError（解析失败）/ pydantic.ValidationError（校验失败），不自定义异常

### 测试迁移
- **D-06:** 所有测试一次性迁移为显式 load_config() 或 pytest fixture，不保留旧 import 模式
- **D-13:** conftest.py 中定义 mock_config fixture，所有测试文件复用

### Scheduler 集成
- **D-16:** 使用 `functools.partial(check_and_update_ip, config=config)` 传参给 APScheduler

### Claude's Discretion
- load_config() 函数的具体实现细节（路径解析、YAML 读取、Pydantic 模型构建）
- Paths 模型的默认值计算逻辑（如何从项目根目录派生默认路径）
- reconfigure_logging() 的具体实现方式（替换 handler 还是重建 logger）
- conftest.py 中 mock_config fixture 的具体数据结构

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Configuration Layer
- `update_whitelist/config/config.py` — 当前 Pydantic Config 模型 + 模块级单例加载逻辑（需重构）
- `config.example.yaml` — 配置模板（需添加 check_interval 和 paths 字段）

### Entry Point
- `main.py` — 调度入口，硬编码 seconds=180（需改为从 config 读取），直接 import 模块级 config（需改为显式 load_config）

### IP Detection
- `update_whitelist/ip_fetcher.py` — 模块级 import config（需改为函数参数注入），IP_CACHE_FILE 相对路径（需改为绝对路径）

### Logging
- `update_whitelist/logger.py` — 硬编码相对路径日志文件（需改为可配置 + 按需重配）

### Updater
- `update_whitelist/updater.py` — client 类变量 bug（QUAL-04），config.dict() 弃用 API（CONF-04），dict 遍历改为对象属性（D-10）

### Prior Phase Context
- `.planning/phases/01-critical-reliability/01-CONTEXT.md` — Phase 1 决策，特别是 D-03（timeout 可配置）建立了 Config 扩展模式

### Codebase Analysis
- `.planning/codebase/CONCERNS.md` — 技术债务清单，包含本 phase 要解决的问题
- `.planning/codebase/ARCHITECTURE.md` — 模块级单例加载和相对路径问题的架构描述
- `.planning/codebase/CONVENTIONS.md` — 代码风格约定（Pydantic 模型命名、import 组织等）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Pydantic Config 模型框架: 已有完善的 BaseModel 层次结构（Config → CloudProvider → Region → Rule → Allow），Phase 1 已添加 TimeoutSettings 模型，Phase 2 的 Paths 模型可复用同一模式
- config.yaml 模板: config.example.yaml 已存在，新增字段只需追加

### Established Patterns
- 配置扩展模式: Phase 1 添加 timeouts 字段时建立了模式 — 新建 BaseModel 子类 + Config 顶层字段 + 默认值
- 错误处理: main.py 用 broad except Exception 包裹调度循环，load_config 的异常应在此层捕获
- 依赖链: main.py → ip_fetcher.py / updater.py / logger.py，所有模块都依赖 config

### Integration Points
- `main.py:9` — `from update_whitelist.config.config import config` — 需改为显式 load_config()
- `main.py:64` — `scheduler.add_job(..., seconds=180)` — 需改为从 config.check_interval 读取
- `ip_fetcher.py:9` — `from .config.config import config` — 需改为函数参数注入
- `ip_fetcher.py:11` — `IP_CACHE_FILE = 'ip_cache.txt'` — 需改为从 config 解析的绝对路径
- `logger.py:26` — `TimedRotatingFileHandler('update_whitelist.log', ...)` — 需改为从 config 解析的路径
- `updater.py:25` — `client = None` — 需从类变量移到 __init__
- `updater.py:33` — `config.dict()` — 需改为 model_dump() 或直接用对象属性

</code_context>

<specifics>
## Specific Ideas

- "千万不要用同一个备注的规则去处理开发/测试和生产环境" — 来自 Phase 1 讨论的隔离原则，config 路径解析也需注意此原则（开发环境的 ip_cache 和日志不应写入生产位置）
- 默认检查间隔 600 秒（10 分钟）— 用户从 3 分钟调整为 10 分钟，减少 API 调用频率
- config.yaml 中的 paths 部分应该是可选的，99% 用户不需要改

</specifics>

<deferred>
## Deferred Ideas

- 规则前缀可配置化 (IDENT-06) — 属于 Phase 4
- Health check / heartbeat 机制 — v2 需求
- 幂等规则管理 — v2 需求
- IP 变更通知 — v2 需求

</deferred>

---

*Phase: 02-configuration-hardening*
*Context gathered: 2026-04-06*
