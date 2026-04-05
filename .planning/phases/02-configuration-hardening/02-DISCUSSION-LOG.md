# Phase 2: Configuration Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 02-configuration-hardening
**Areas discussed:** 配置初始化模式, 文件路径策略, 新增配置字段, Updater.client, Logger-Config初始化顺序, 测试迁移, 错误处理, main.py函数签名, check_interval值域, updater遍历方式, pathlib迁移范围, ip_fetcher注入, 测试fixture, 异常类型, paths键名, Scheduler传参

---

## 配置初始化模式

| Option | Description | Selected |
|--------|-------------|----------|
| 显式函数 + 依赖注入 | load_config(path) 函数，其他模块通过参数接收 config | ✓ |
| Lazy Singleton | 首次使用时加载，模块级变量 | |
| 应用上下文对象 | AppState 类持有 config | |

**User's choice:** 显式函数 + 依赖注入
**Notes:** 最干净方案，import 不触发 I/O，测试可注入 mock

---

## 文件路径策略

| Option | Description | Selected |
|--------|-------------|----------|
| 默认自动检测 + 可配置 | 自动基于项目根目录解析，用户可配置覆盖 | ✓ |
| 基于可执行文件位置 | 基于 Python 可执行文件目录 | |
| 基于 cwd + 启动脚本保证 | 依赖调用者 cd 到正确目录 | |

**User's choice:** 默认自动检测 + 可配置
**Notes:** 自动解析 config.yaml 所在目录为项目根，99% 用户不需要配置

---

## 新增配置字段组织

| Option | Description | Selected |
|--------|-------------|----------|
| 平铺在 Config 顶层 | check_interval 和 paths 直接加在 Config，与 timeouts 对称 | ✓ |
| 分组为 Settings 子模型 | paths、check_interval、timeouts 放在 operational/settings 子模型下 | |

**User's choice:** 平铺在 Config 顶层
**Notes:** 与 Phase 1 的 timeouts 字段保持一致的扩展模式

---

## Updater.client 共享状态

| Option | Description | Selected |
|--------|-------------|----------|
| 直接移到 __init__ | client = None 从类变量移到 self.client = None | ✓ |
| 整体重构 Updater 构造 | Updater 构造时接收 config，全面重构 | |

**User's choice:** 直接移到 __init__
**Notes:** 最小改动，直接修复 bug

---

## Logger-Config 初始化顺序

| Option | Description | Selected |
|--------|-------------|----------|
| Logger 先用默认 + 按需重配 | Logger 始终先初始化，load_config 成功后 reconfigure | ✓ |
| Config 加载完全不用 Logger | load_config 内只输出到 stderr | |
| 集中初始化函数 init_app() | 提供统一初始化函数 | |

**User's choice:** Logger 先用默认 + 按需重配
**Notes:** 避免循环依赖，Logger 总是可用

---

## 测试迁移策略

| Option | Description | Selected |
|--------|-------------|----------|
| 一次性全部迁移 | 所有测试改为 load_config() 或 fixture | ✓ |
| 渐进式迁移 | 新代码用显式函数，旧测试暂时保持 | |

**User's choice:** 一次性全部迁移
**Notes:** 不保留旧模式，一步到位

---

## 错误处理

| Option | Description | Selected |
|--------|-------------|----------|
| 快速失败 + 明确错误信息 | 文件缺失/解析错误/校验失败都抛异常 | ✓ |
| 容错 + 自动生成默认配置 | 文件缺失时创建模板 | |

**User's choice:** 快速失败 + 明确错误信息
**Notes:** 不自动生成配置，明确告知用户问题

---

## main.py 函数签名变化

| Option | Description | Selected |
|--------|-------------|----------|
| 直接参数传入 | check_and_update_ip(config) 直接接收参数 | ✓ |
| 闭包捕获 config | check_and_update_ip 作为闭包 | |
| main() 内全局变量 | 通过全局变量传递 | |

**User's choice:** 直接参数传入
**Notes:** Scheduler 用 functools.partial 传递 config

---

## check_interval 值域限制

| Option | Description | Selected |
|--------|-------------|----------|
| 限制 60-86400 秒 | Pydantic validator 限制 | |
| 仅设下限 10 秒 | 不设上限 | |
| 600-99999999999 | 最小 10 分钟，无实质上限 | ✓ |

**User's choice:** 最小 600 秒，无实质上限
**Notes:** Pydantic validator 校验

---

## updater 遍历 config 的方式

| Option | Description | Selected |
|--------|-------------|----------|
| model_dump() 继续用 dict | 只换方法名 | |
| 改为 Pydantic 对象属性 | 直接用 config.huawei, config.tencent 等 | ✓ |

**User's choice:** 改为 Pydantic 对象属性
**Notes:** 获得类型提示和 IDE 补全

---

## pathlib 迁移范围

| Option | Description | Selected |
|--------|-------------|----------|
| 仅改新增代码 | Phase 2 新增/修改的路径代码用 pathlib | ✓ |
| 全部迁移到 pathlib | 所有 os.path 改为 pathlib | |

**User's choice:** 仅改新增代码
**Notes:** 最小改动原则

---

## ip_fetcher 的 config 注入方式

| Option | Description | Selected |
|--------|-------------|----------|
| 函数参数 | get_current_ip(config) 等函数直接接收 | ✓ |
| 模块级 configure() 函数 | 调用后缓存到模块级变量 | |

**User's choice:** 函数参数
**Notes:** 消除模块级 config import

---

## 测试 fixture 模式

| Option | Description | Selected |
|--------|-------------|----------|
| conftest.py 全局 fixture | mock_config fixture，所有测试文件复用 | ✓ |
| 每个测试文件自己构建 | 各自构建 config 对象 | |

**User's choice:** conftest.py 全局 fixture

---

## 异常类型选择

| Option | Description | Selected |
|--------|-------------|----------|
| 用标准异常 | FileNotFoundError / YAMLError / ValidationError | ✓ |
| 自定义 ConfigLoadError | 包装所有错误 | |

**User's choice:** 用标准异常

---

## paths 配置键名

| Option | Description | Selected |
|--------|-------------|----------|
| paths.ip_cache / paths.log_file | 简洁，与用途对应 | ✓ |
| files.cache / files.log | 更短但可能歧义 | |
| paths.ip_cache_path / paths.log_path | 显式但冗长 | |

**User's choice:** paths.ip_cache / paths.log_file

---

## Scheduler 传参方式

| Option | Description | Selected |
|--------|-------------|----------|
| functools.partial | 标准 Python 做法，可测试 | ✓ |
| lambda 包装 | 简单但 traceback 信息少 | |

**User's choice:** functools.partial

---

## Claude's Discretion

- load_config() 函数的具体实现细节
- Paths 模型的默认值计算逻辑
- reconfigure_logging() 的具体实现方式
- conftest.py 中 mock_config fixture 的具体数据结构

## Deferred Ideas

- 规则前缀可配置化 (IDENT-06) — Phase 4
- Health check / heartbeat — v2
- 幂等规则管理 — v2
- IP 变更通知 — v2
