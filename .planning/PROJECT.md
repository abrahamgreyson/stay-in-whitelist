# Stay in Whitelist

## What This Is

一个定时检测本地公网 IP 变化并自动更新云服务安全组白名单的工具。解决动态 IP 环境下安全访问云服务（数据库、应用端口）的问题，避免长期暴露敏感端口。支持华为云、腾讯云，可扩展其他云服务。部署为 systemd 服务长期运行。

## Core Value

IP 变了，白名单自动跟上 — 不漏更、不挂死、不锁死。

## Requirements

### Validated

<!-- 从已有代码推断的已验证能力 -->

- ✓ 定时获取本地公网 IP（通过 ipinfo.io） — existing
- ✓ IP 变化时自动更新华为云安全组规则 — existing
- ✓ IP 变化时自动更新腾讯云安全组规则 — existing
- ✓ 支持多云、多 region、多安全组、多端口配置 — existing
- ✓ 文件缓存上次 IP 用于变化检测 — existing
- ✓ YAML 配置 + Pydantic 校验 — existing
- ✓ 日志轮转 — existing
- ✓ CI/CD 测试流水线（GitHub Actions + GitLab CI） — existing

### Active

<!-- 本次重构的目标 -->

- [ ] 修复 IP 检测遗漏 Bug — requests.get 无 timeout 导致挂起，APScheduler 跳过后续检查
- [ ] 所有网络请求加 timeout（IP 探测 + 云 API 调用）
- [ ] 云 API 调用加重试机制（指数退避），防止 rate limit 和瞬时故障
- [ ] 安全组规则更新改为"先加后删"，避免中间断档锁死
- [ ] 增加多个 IP 探测服务商（除 ipinfo 外增加备用提供商），支持降级容错
- [ ] IP 返回值格式验证（防止错误 HTML 写入安全组规则）
- [ ] 项目重命名为 "Stay in Whitelist"（包名、类名、配置键名、注释全面更新）
- [ ] 检查间隔改为可配置，默认 10 分钟
- [ ] 修复路径问题（ip_cache.txt、日志文件使用绝对路径，兼容 systemd）
- [ ] 修复 get_rules 失败返回 None 导致规则堆积的问题
- [ ] huawei_cloud.add_rules 加异常处理
- [ ] print() 调用替换为 logger

### Out of Scope

- 阿里云支持 — 当前用户不需要，保持 stub 或移除即可
- 异步/消息队列架构 — 当前规模不需要，保持线性执行
- Web UI 或 API 接口 — 自用工具不需要
- 容器化部署 — 暂无需求
- 密钥管理（Vault 等） — 本地自用，config.yaml + gitignore 足够

## Context

### 项目背景

用户的公司使用动态 IP，需要随时连接云服务中的数据库。该工具部署在本地机器上，每几分钟检查一次公网 IP，IP 变动时自动更新华为云和腾讯云的安全组规则。

### 使用中发现的痛点

1. **systemd 部署下 IP 变更遗漏**：本地 IP 已更新但脚本未检测到。根因是 `requests.get()` 无 timeout 导致请求挂起，APScheduler 的 `max_instances=1` 使后续检查被静默跳过
2. **云 API rate limit**：偶尔触发限制导致更新失败，无重试机制
3. **IPinfo 免费额度不足**：单一 IP 探测源，触达上限后返回错误信息
4. **先删后加的原子性问题**：如果添加规则失败，安全组为空，用户被锁死
5. **相对路径问题**：systemd 的 WorkingDirectory 可能与预期不同，导致缓存和日志文件写入错误位置

### 代码库现状

- Python 3.9-3.12，Pydantic v2，APScheduler 3.10
- 约 280 行核心代码（不含测试），19 个 Python 文件
- 单元测试覆盖较好（mock 方式），无集成测试
- 两个云服务提供商：华为云、腾讯云
- 策略模式的 cloud provider 抽象（BaseCloudProvider ABC）
- 代码质量问题：print() 混用、相对路径、模块级副作用、死代码

## Constraints

- **Python 版本**: 3.9+ — 兼容性要求
- **自用工具**: 不需要考虑多用户、权限控制、Web 界面
- **运行方式**: systemd 服务长期运行，需要健壮的错误恢复
- **无堡垒机**: 这是该工具存在的原因 — 在没有堡垒机的情况下保护端口访问
- **线性架构**: 保持简单，不需要引入异步或消息队列

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 保持线性执行架构 | 当前规模（2-3 云、几个安全组）不需要异步，timeout + 重试即可获得容错能力 | — Pending |
| 先加后删的规则更新顺序 | 避免中间断档导致用户被锁死 | — Pending |
| 默认检查间隔 10 分钟 | 用户从 3 分钟调整为 10 分钟，减少 API 调用频率，降低 rate limit 风险 | — Pending |
| 多 IP 探测服务商降级 | IPinfo 免费额度不足，需要备用提供商保证可用性 | — Pending |
| 项目重命名为 Stay in Whitelist | 与目录名对齐，更准确描述功能 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 after initialization*
