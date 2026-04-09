# Phase 4: Project Identity - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

将项目全面重命名为 "Stay in Whitelist"：包目录 update_whitelist/ → stay_in_whitelist/、所有 import 路径、pyproject.toml、CI 配置、日志文件名、README 全面更新。规则描述前缀从硬编码提取为 Config 顶层可配置字段，支持通过不同 config 文件实现 dev/prod 环境隔离。

Requirements: IDENT-01, IDENT-02, IDENT-03, IDENT-04, IDENT-05, IDENT-06

</domain>

<decisions>
## Implementation Decisions

### Rule Prefix 可配置化 (IDENT-05, IDENT-06)
- **D-01:** 规则描述前缀提取为 Config 顶层字段 `rule_prefix`，默认值 `"from Wulihe"`（Wulihe 是公司位置，保持不变）
- **D-02:** dev/prod 环境隔离通过不同的 config 文件实现（如 config.dev.yaml 中 `rule_prefix: "from Wulihe-dev"`），代码不需要感知环境概念
- **D-03:** `rule_prefix` 放在 Config 顶层，与 `check_interval`/`paths` 平级，所有 cloud provider 共用一个前缀。配置键名：`rule_prefix`
- **D-04:** huawei_cloud.py 和 tencent_cloud.py 中硬编码的 `"from Wulihe"` 全部替换为读取 config 中的 `rule_prefix`
- **D-05:** `startswith("from Wulihe")` 的规则过滤逻辑改为 `startswith(rule_prefix)`，支持自定义前缀后仍能正确匹配

### README 重写 (IDENT-04)
- **D-06:** README.md 全面重写，纯中文，更新 badge URL、目录引用、项目名、架构描述
- **D-07:** badge URL 需更新为正确的 GitHub repo 路径（当前指向 abrahamgreyson/update-whitelist）

### 日志文件名 (IDENT-02)
- **D-08:** logger.py 中默认日志文件名从 `update_whitelist.log` 改为 `stay_in_whitelist.log`
- **D-09:** 已部署环境不受影响（通过 config.yaml 的 paths.log_file 覆盖默认值）

### Config 键名迁移 (IDENT-03)
- **D-10:** 现有 config.yaml 的 huawei/tencent/ipinfo/timeouts/paths/check_interval 等键名全部保持不变，它们是云服务商标识而非项目标识
- **D-11:** config.example.yaml 中只更新注释里的旧项目名引用（如 `update_whitelist.log` → `stay_in_whitelist.log`），并添加 `rule_prefix` 字段文档

### 包重命名 (IDENT-01)
- **D-12:** 目录 `update_whitelist/` 整体重命名为 `stay_in_whitelist/`
- **D-13:** pyproject.toml 中 `name` 改为 `"stay-in-whitelist"`，setuptools_scm 的 `write_to` 改为 `"stay_in_whitelist/_version.py"`
- **D-14:** CI 文件中的 `--cov=update_whitelist` 改为 `--cov=stay_in_whitelist`
- **D-15:** 所有 Python import 语句中的 `update_whitelist` 替换为 `stay_in_whitelist`
- **D-16:** 测试文件中的 mocker.patch 路径也需同步更新

### Claude's Discretion
- 包重命名的执行顺序（先改目录还是先改 import）
- BaseCloudProvider 如何接收 rule_prefix（构造函数参数 vs 类属性）
- README 具体的内容结构和详细程度
- _version.py gitignore 条目的更新
- 是否需要添加迁移指南（告知已部署用户需要注意的事项）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Package Rename (IDENT-01)
- `update_whitelist/` — 整个包目录需重命名为 `stay_in_whitelist/`
- `pyproject.toml` — 包名和 setuptools_scm write_to 路径（line 2, 44）
- `.github/workflows/test.yml` — CI 中 --cov 参数（line 43）
- `.gitlab-ci.yml` — CI 中 artifact path 和 --cov 参数（line 29, 40）

### Rule Prefix (IDENT-05, IDENT-06)
- `update_whitelist/cloud_providers/huawei_cloud.py` — 硬编码 "from Wulihe"（line 44, 84）
- `update_whitelist/cloud_providers/tencent_cloud.py` — 硬编码 "from Wulihe"（line 34, 53）
- `update_whitelist/config/config.py` — Config 模型，需添加 rule_prefix 字段（line 68）
- `config.example.yaml` — 需添加 rule_prefix 文档

### Log Filename (IDENT-02)
- `update_whitelist/logger.py` — 硬编码 'update_whitelist.log'（line 26）

### README (IDENT-04)
- `README.md` — 全面重写，当前 173 行纯中文

### Test Files Needing Import Update
- `tests/test_ip_fetcher.py` — import 和 mocker.patch 路径
- `tests/test_updater.py` — import 和 mocker.patch 路径
- `tests/test_huawei_cloud.py` — import 和 mocker.patch 路径
- `tests/test_tencent_cloud.py` — import、mocker.patch 和 "from Wulihe" 断言
- `tests/test_config.py` — import 和 docstring 引用
- `tests/test_base_cloud_provider.py` — import 路径
- `tests/conftest.py` — import 路径

### Prior Phase Context
- `.planning/phases/01-critical-reliability/01-CONTEXT.md` — Phase 1 D-18: dev/prod 必须用不同前缀隔离
- `.planning/phases/02-configuration-hardening/02-CONTEXT.md` — Phase 2 D-15: Config 键名模式

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Config 模型框架: Phase 1/2 已建立 BaseModel 扩展模式（TimeoutSettings, Paths），rule_prefix 只需加一个 `str` 字段到 Config 顶层
- BaseCloudProvider 构造函数: 已接收 `access_key, secret_key, region, **kwargs`，rule_prefix 可通过 kwargs 或新增参数传入

### Established Patterns
- Config 顶层字段模式: 新字段平铺在 Config 类（如 check_interval: int = 600, paths: Paths = Paths()），rule_prefix: str = "from Wulihe" 遵循同一模式
- 规则匹配模式: huawei_cloud 用 `description.startswith("from Wulihe")`，tencent_cloud 用 `PolicyDescription.startswith('from Wulihe')`，改为 startswith(rule_prefix) 即可

### Integration Points
- `huawei_cloud.py:44,84` — 规则描述前缀写入和过滤匹配
- `tencent_cloud.py:34,53` — 规则描述前缀写入和过滤匹配
- `updater.py` — set_client() 创建 cloud provider 实例时需传入 rule_prefix
- `config/config.py:68` — Config 模型需添加 rule_prefix 字段

</code_context>

<specifics>
## Specific Ideas

- "Wulihe 是我们公司的位置" — 用户确认保持 "from Wulihe" 作为默认前缀，不改为项目名
- dev/prod 隔离通过不同 config 文件是自然方案：systemd 服务指向不同 config 路径即可
- 已部署用户需注意日志文件名变化（从 update_whitelist.log 到 stay_in_whitelist.log），但 config.yaml 的 paths.log_file 配置优先级更高

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-project-identity*
*Context gathered: 2026-04-06*
