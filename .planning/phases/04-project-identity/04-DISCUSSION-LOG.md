# Phase 4: Project Identity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 04-project-identity
**Areas discussed:** Rule Prefix, README, Log Filename, Config Keys

---

## Rule Prefix Default Value

| Option | Description | Selected |
|--------|-------------|----------|
| from Stay-in-Whitelist | 与当前 "from Wulihe" 格式一致，换了名字 | |
| Stay-in-Whitelist | 去掉 "from" 前缀，更简洁 | |
| stay_in_whitelist | 全小写蛇形命名，与 Python 包名一致 | |

**User's choice:** 保持 "from Wulihe" 不变 — Wulihe 是公司位置，不是项目名
**Notes:** 前缀标识的是"谁创建的规则"，不是"项目叫什么"。公司位置更有语义价值

## Rule Prefix Configuration Location

| Option | Description | Selected |
|--------|-------------|----------|
| Config 顶层 | 与 check_interval/paths 平级，所有 provider 共用一个前缀 | ✓ |
| Per-provider | 每个 CloudProvider 各配一个 | |
| Per-region | 每个 Region 配一个，粒度最细 | |

**User's choice:** Config 顶层
**Notes:** 配置键名 rule_prefix，默认值 "from Wulihe"

## Dev/Prod Environment Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| 不同配置文件 | config.dev.yaml（rule_prefix: "from Wulihe-dev"），systemd 指向不同文件 | ✓ |
| 同一文件，environment 字段 | 一个 config.yaml 里加 environment: dev/prod | |

**User's choice:** 不同配置文件
**Notes:** 代码不需要感知环境概念，运维层面通过 systemd 配置解决

## README Rewrite Style

| Option | Description | Selected |
|--------|-------------|----------|
| 纯中文，更新引用 | 只更新项目名、目录引用、badge URL | |
| 中英双语 | 英文为主 + 中文注释 | |
| 全面重写 | 可能改变结构和内容 | ✓ |

**User's choice:** 全面重写
**Notes:** 纯中文。当前 README 173 行，badge URL 指向旧的 abrahamgreyson/update-whitelist

## Log Filename Migration

| Option | Description | Selected |
|--------|-------------|----------|
| 改为 stay_in_whitelist.log | 默认名改为新项目名，已部署环境通过 paths.log_file 覆盖 | ✓ |
| 保持 update_whitelist.log | 不改默认名，避免部署风险 | |

**User's choice:** 改为 stay_in_whitelist.log
**Notes:** 已部署环境已通过 config.yaml 的 paths.log_file 指定路径，不受默认值变化影响

## Config Key Naming

| Option | Description | Selected |
|--------|-------------|----------|
| 保持现有键名 | huawei/tencent/ipinfo 等是云服务商标识不是项目标识 | ✓ |
| 部分重命名 | 去掉 update_whitelist 引用 | |

**User's choice:** 保持现有键名
**Notes:** 只更新注释中的旧项目名引用，添加 rule_prefix 字段文档

---

## Claude's Discretion

- 包重命名的执行顺序
- BaseCloudProvider 如何接收 rule_prefix
- README 具体内容结构
- _version.py gitignore 更新
- 是否需要迁移指南

## Deferred Ideas

None — discussion stayed within phase scope
