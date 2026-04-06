# Phase 3: Code Quality - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

所有运行时输出通过结构化日志，死代码清除，构建工具链修复。Phase 完成后：无 print() 残留、日志不含 credential、无注释死代码、无未使用模块、pip install 无错误。

Requirements: QUAL-01, QUAL-02, QUAL-03, QUAL-05, QUAL-06

</domain>

<decisions>
## Implementation Decisions

### print → logger 转换策略 (QUAL-01)
- **D-01:** main.py 启动时的配置加载错误 print() 改为 logger.error() — logger 在模块导入时已有 StreamHandler，即使文件路径未配好，console 输出仍然可用
- **D-02:** 云 provider 的 API response print() 改为 logger.debug() — 调试信息只在 DEBUG 级别输出，生产环境（默认 INFO）不会看到

### 日志敏感信息 (QUAL-02)
- **D-03:** 审核确认当前代码不泄露 credential 即可，不额外添加日志过滤器。当前代码已满足要求：ip_fetcher 不 log 含 token 的 URL，无 access_key/secret_key 被 log

### 死代码清理 (QUAL-03, QUAL-05)
- **D-04:** 删除 `update_whitelist/config/config_loader.py` — 从未被 import 的废弃模块
- **D-05:** 验证 updater.py 中无注释死代码残留（Phase 1/2 可能已清除）

### 构建工具链修复 (QUAL-06)
- **D-06:** 修复 `requirements.dev.txt` 第 4 行的尾部多余引号：`pytest-cov~=5.0.0"` → `pytest-cov~=5.0.0`

### Claude's Discretion
- logger.debug() 中的具体日志消息格式
- config_loader.py 删除后是否需要清理 __init__.py 中的相关 import
- 其他代码风格微调

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Print → Logger (QUAL-01)
- `main.py` — 启动入口，line 69, 72 有 print() 需替换为 logger.error()
- `update_whitelist/cloud_providers/huawei_cloud.py` — line 32 有 print(response) 需替换为 logger.debug()
- `update_whitelist/cloud_providers/tencent_cloud.py` — line 56, 78 有 print(resp.to_json_string()) 需替换为 logger.debug()

### Credential Audit (QUAL-02)
- `update_whitelist/ip_fetcher.py` — 确认不 log 含 token 的 URL（当前已满足）
- `update_whitelist/cloud_providers/huawei_cloud.py` — 确认 logger.debug(response) 不含 credential
- `update_whitelist/cloud_providers/tencent_cloud.py` — 确认 logger.debug(resp.to_json_string()) 不含 credential

### Dead Code (QUAL-03, QUAL-05)
- `update_whitelist/updater.py` — 验证无注释死代码
- `update_whitelist/config/config_loader.py` — 待删除的未使用模块

### Build Fix (QUAL-06)
- `requirements.dev.txt` — line 4 有尾部引号需修复

### Prior Phase Context
- `.planning/phases/01-critical-reliability/01-CONTEXT.md` — Phase 1 决策
- `.planning/phases/02-configuration-hardening/02-CONTEXT.md` — Phase 2 决策，特别是 D-12（main() 使用 print() 输出 config 错误）将被本 phase 覆盖

### Codebase Analysis
- `.planning/codebase/CONCERNS.md` — 技术债务清单，本 phase 解决其中 Code Quality 和 Tech Debt 相关条目

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `update_whitelist/logger.py` — get_logger() 工厂函数，已在所有模块中使用，添加 logger 调用无需额外 setup
- `update_whitelist/cloud_providers/base_cloud_provider.py` — 已有 logger import 模式

### Established Patterns
- Logger 使用模式: 每个模块 `logger = get_logger()` 在文件顶部，然后 `logger.info/debug/warning/error`
- 华为云 logger 已存在: `huawei_cloud.py:17` 有 `logger = get_logger()`
- 腾讯云无 logger import: `tencent_cloud.py` 目前没有 import logger，需添加

### Integration Points
- `main.py:69,72` — 配置加载失败的 print() → logger.error()
- `huawei_cloud.py:32` — delete response print → logger.debug()
- `tencent_cloud.py:56,78` — add/delete response print → logger.debug()
- `update_whitelist/config/config_loader.py` — 整个文件删除
- `update_whitelist/config/__init__.py` — 可能需要移除对 config_loader 的引用（如有）

</code_context>

<specifics>
## Specific Ideas

- API response 的 debug 日志在生产环境（systemd + INFO 级别）不会输出，只在需要排查问题时手动调整日志级别查看
- config_loader.py 是最初实现的配置加载函数，已被 Phase 2 的 load_config() 完全取代

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-code-quality*
*Context gathered: 2026-04-06*
