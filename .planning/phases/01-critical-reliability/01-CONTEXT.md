# Phase 1: Critical Reliability - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

修复导致 daemon 挂死、锁死用户、写垃圾数据到安全组的五个核心缺陷。Phase 完成后：daemon 永远不会因网络请求无限挂起、IP 探测有容错降级、无效 IP 不会写入安全组、云 API 瞬时故障自动重试、规则更新不会导致中间断档锁死用户。

Requirements: REL-01, REL-02, REL-03, REL-04, REL-05, REL-06, REL-07

</domain>

<decisions>
## Implementation Decisions

### Timeout 配置策略
- **D-01:** IP 探测和云 API 请求都加 connect timeout 和 read timeout，分开设置
- **D-02:** 默认值：IP 探测 connect=3s/read=5s，云 API connect=3s/read=10s
- **D-03:** timeout 值可在 config.yaml 中配置覆盖，99% 用户不需要改
- **D-04:** 使用 requests 的 timeout 元组参数 `(connect_timeout, read_timeout)`

### IP 探测降级逻辑
- **D-05:** 顺序尝试降级链：ipinfo → icanhazip → ipify → ifconfig.me，第一个成功就停
- **D-06:** ipinfo 排第一（保持现有 token 配置），降级到不需 token 的免费服务
- **D-07:** 每个 provider 有独立的 timeout，单个失败不影响后续 provider 的剩余时间
- **D-08:** 所有 provider 都失败时，记录错误日志，本轮检查跳过（不更新白名单），下次 scheduler tick 重试

### 重试策略
- **D-09:** 使用 tenacity 库实现重试，3 次重试 + 指数退避（初始 1 秒，倍增）
- **D-10:** 仅重试网络错误（requests.exceptions.ConnectionError, Timeout 等）和 5xx 服务端错误
- **D-11:** 4xx 客户端错误（配置错误、认证失败等）不重试，直接失败并记录日志
- **D-12:** 重试应用于所有云 API 调用：get_rules, add_rules, delete_rules

### 先加后删安全策略
- **D-13:** 安全组规则更新顺序改为：先 add_rules（新规则）→ 再 delete_rules（旧规则）
- **D-14:** 不做 add 后的 verify 步骤（多一次 API 调用的复杂度不值得，API 返回成功即视为规则生效）
- **D-15:** get_rules() 失败时返回空列表 `[]` 而非 `None`，防止规则堆积 bug
- **D-16:** huawei_cloud.add_rules() 必须包裹 try/except，与 delete_rules 保持一致的错误处理

### 测试安全约束
- **D-17:** Phase 1 的单元测试必须 mock 云 API 调用，不得实际操作生产安全组
- **D-18:** 开发/调试时如需实际测试，必须使用不同于生产环境的规则前缀（如 "from Wulihe-dev"）隔离
- **D-19:** 规则前缀可配置化（IDENT-06）属于 Phase 4 范围，但 Phase 1 测试时必须注意此隔离问题

### Claude's Discretion
- IP 探测 provider 的具体 URL 格式和响应解析
- tenacity 装饰器的具体参数配置（stop_after_attempt, wait_exponential）
- config.yaml 中 timeout 字段的命名和结构
- IP 验证失败时的具体日志格式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### IP Detection
- `update_whitelist/ip_fetcher.py` — 当前 IP 探测实现，需重构为多 provider 降级链
- `update_whitelist/config/config.py` — Config 模型，IPInfo 定义了 tokens 字段

### Cloud Provider Interface
- `update_whitelist/cloud_providers/base_cloud_provider.py` — ABC 定义了 get_rules/add_rules/delete_rules 接口
- `update_whitelist/cloud_providers/huawei_cloud.py` — 华为云实现，add_rules 缺少 try/except (REL-07)
- `update_whitelist/cloud_providers/tencent_cloud.py` — 腾讯云实现

### Update Orchestration
- `update_whitelist/updater.py` — 核心编排逻辑，先删后加需改为先加后删 (REL-05)
- `main.py` — 调度入口，has_ip_changed 和 check_and_update_ip 的错误处理

### Configuration
- `update_whitelist/config/config.py` — Pydantic Config 模型，timeout 配置需在此添加
- `config.example.yaml` — 配置模板

### Codebase Analysis
- `.planning/codebase/CONCERNS.md` — 完整的技术债务和安全问题清单，Phase 1 需求直接来源于此

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseCloudProvider` ABC: 已定义统一的 get_rules/add_rules/delete_rules 接口，timeout 和 retry 应在 Base 层或调用层添加
- `BaseCloudProvider.log(e)`: 已有云 SDK 异常格式化方法，重试日志可复用此模式
- Pydantic Config 模型: 已有完善的配置验证框架，添加 timeout 配置只需扩展模型

### Established Patterns
- 错误处理模式: cloud provider 方法用 try/except SDK异常 → log → return None/静默
- 当前先删后加: `updater.py:53-63` 按备注过滤规则 → 全删 → 全加
- IP 探测: 单函数 `get_current_ip()` 调 ipinfo.io，需重构为多 provider 降级

### Integration Points
- `main.py:has_ip_changed()` → `ip_fetcher.get_current_ip()` — IP 探测的调用入口
- `updater.py:update_security_group_rules()` → `client.add_rules()/delete_rules()` — 规则更新顺序
- `updater.py:fetch_security_group_rules()` → `client.get_rules()` — 获取现有规则的入口

</code_context>

<specifics>
## Specific Ideas

- "千万不要用同一个备注的规则去处理开发/测试和生产环境" — 用户特别强调，生产白名单被误删是灾难性的
- 降级链中的 icanhazip、ipify、ifconfig.me 都不需要 token，只需 GET 请求返回纯 IP 文本
- 华为云 SDK 的 `ClientRequestException` 和腾讯云 SDK 的 `TencentCloudSDKException` 需要分别判断是否属于重试范围

</specifics>

<deferred>
## Deferred Ideas

- 规则前缀可配置化 (IDENT-06) — 属于 Phase 4，但 Phase 1 测试需注意隔离
- Health check / heartbeat 机制 — v2 需求
- 幂等规则管理（跳过已存在的规则）— v2 需求
- IP 变更通知（webhook/email）— v2 需求

</deferred>

---

*Phase: 01-critical-reliability*
*Context gathered: 2026-04-05*
