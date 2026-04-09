# Phase 1: Critical Reliability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 01-critical-reliability
**Areas discussed:** Timeout 配置策略, IP 探测降级逻辑, 重试策略细节, 先加后删安全策略

---

## Timeout 配置策略

| Option | Description | Selected |
|--------|-------------|----------|
| 硬编码合理值 | IP 探测 5s、云 API 10s，写死常量不改配置 | |
| config.yaml 可配置 | 默认 IP 探测 5s/云 API 10s，可在 config.yaml 覆盖 | ✓ |
| 分级可配置 | 每个云 provider/region 单独配 timeout | |

**Connect vs Read timeout:**

| Option | Description | Selected |
|--------|-------------|----------|
| 统一 timeout | connect 和 read 用同一个值 | |
| 分开 connect/read | connect 3s, read 10s，分别控制 | ✓ |

**User's choice:** config.yaml 可配置 + connect/read 分开设置
**Notes:** 默认值 IP 探测 connect=3s/read=5s, 云 API connect=3s/read=10s

---

## IP 探测降级逻辑

| Option | Description | Selected |
|--------|-------------|----------|
| 顺序尝试，第一个成功就停 | 快速、简单，timeout 控制单个 provider 耗时 | ✓ |
| 并发请求，取最快响应 | 最快但复杂度高，可能触发 rate limit | |
| 全试完取一致结果 | 防止错误 IP，但复杂度最高 | |

**Provider 顺序:**

| Option | Description | Selected |
|--------|-------------|----------|
| 按需求顺序 (ipinfo→icanhazip→ipify→ifconfig.me) | 保持 ipinfo token 配置，降级到免费服务 | ✓ |
| 免费探测源优先 | 减少 token 配置，但放弃 ipinfo 认证优势 | |

**User's choice:** 顺序尝试 + 按需求中的 provider 顺序
**Notes:** ipinfo 保持首选因为它已有 token 配置，其他三个不需要 token

---

## 重试策略细节

| Option | Description | Selected |
|--------|-------------|----------|
| 3 次，指数退避 | 初始 1s 倍增，总耗时最多 ~7s，对 10 分钟间隔足够 | ✓ |
| 5 次，更激进退避 | 初始 2s 倍增，总耗时最多 ~62s | |
| 完全可配置 | 重试次数和退避参数在 config.yaml 中可配 | |

**重试触发条件:**

| Option | Description | Selected |
|--------|-------------|----------|
| 仅网络 + 5xx | 网络错误和 5xx 重试，4xx 不重试 | ✓ |
| 所有异常 | 简单但可能重试不该重试的错误 | |

**User's choice:** 3 次指数退避 + 仅网络错误和 5xx
**Notes:** 使用 tenacity 库

---

## 先加后删安全策略

| Option | Description | Selected |
|--------|-------------|----------|
| 直接先加后删 | add API 返回成功即视为规则生效，然后删旧规则 | ✓ |
| 加后验证再删 | add 后再 get_rules 确认新规则存在再删旧规则 | |

**User's choice:** 直接先加后删
**Notes:** 用户特别强调开发和测试环境必须与生产环境隔离，不能用同一个备注前缀操作。生产白名单被误删是灾难性的。规则前缀可配置化属于 Phase 4 (IDENT-06)。

---

## Claude's Discretion

- IP 探测 provider 的具体 URL 格式和响应解析
- tenacity 装饰器的具体参数配置
- config.yaml 中 timeout 字段的命名和结构
- IP 验证失败时的具体日志格式

## Deferred Ideas

- 规则前缀可配置化 (IDENT-06) — Phase 4，但 Phase 1 测试需注意隔离
- Health check / heartbeat 机制 — v2
- 幂等规则管理 — v2
- IP 变更通知 — v2
