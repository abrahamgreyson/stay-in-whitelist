# Stay in Whitelist

[![License](https://img.shields.io/github/license/abrahamgreyson/stay-in-whitelist.svg?)](https://opensource.org/license/mit)
[![GitHub tag](https://img.shields.io/github/v/tag/abrahamgreyson/stay-in-whitelist?label=version)](https://github.com/abrahamgreyson/stay-in-whitelist/tags)
[![Test](https://github.com/abrahamgreyson/stay-in-whitelist/actions/workflows/test.yml/badge.svg)](https://github.com/abrahamgreyson/stay-in-whitelist/actions/workflows/test.yml)
[![Codecov](https://codecov.io/gh/abrahamgreyson/stay-in-whitelist/branch/main/graph/badge.svg?token=Fc4MbBmMpZ)](https://codecov.io/gh/abrahamgreyson/stay-in-whitelist?branch=main)
[![Python versions](https://img.shields.io/badge/python-3.9%7C3.10%7C3.11%7C3.12%7C3.13-blue)](https://github.com/abrahamgreyson/stay-in-whitelist/actions/workflows/test.yml)

定时检测本地公网 IP 变化，自动更新云服务安全组白名单。

在没有堡垒机的情况下，避免长期暴露数据库、应用端口等敏感端口。部署为 systemd 服务长期运行，IP 变了白名单自动跟上 -- 不漏更、不挂死、不锁死。

## 功能特性

- **多云支持** -- 华为云、腾讯云、阿里云（轻量服务器防火墙）
- **Per-provider 静态 IP** -- 每个 Provider 独立配置固定 IP 白名单，支持 `except_ports` 排除端口
- **幂等更新** -- 基于 `(IP, port)` 指纹比较，重复运行不产生副作用
- **多层级配置** -- 每个云支持多个 region，每个 region 支持多个安全组，每个安全组支持多个端口
- **IP 探测降级链** -- ipinfo -> icanhazip -> ipify -> ifconfig.me，自动切换可用源
- **先加后删更新策略** -- 避免规则清空导致用户被锁死
- **云 API 重试** -- 网络超时自动指数退避重试
- **systemd 长期运行** -- 开机自启，异常自动恢复

## 快速开始

### 1. 安装

```bash
git clone https://github.com/abrahamgreyson/stay-in-whitelist.git
cd stay-in-whitelist
pip install -e .
```

要求 Python 3.9+。

### 2. 配置

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入云服务凭证和需要放行的端口。详见下方[配置说明](#配置说明)。

### 3. 运行

```bash
# 安装后直接运行（推荐）
stay-in-whitelist

# 调试模式：跳过定时器，执行一次检查后退出
stay-in-whitelist --debug

# 强制更新：清空 IP 缓存，强制触发白名单更新
stay-in-whitelist --force

# 查看模式：打印所有安全组现有规则后退出
stay-in-whitelist --look
```

## 配置说明

配置文件为 `config.yaml`（模板见 `config.example.yaml`），使用 YAML 格式，Pydantic 校验。

### 云服务商

#### 华为云

在[统一身份认证服务 IAM](https://console.huaweicloud.com/iam) 中创建用户，获取 `Access Key` 和 `Secret Key`，赋予以下权限：

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "vpc:securityGroupRules:create",
                "vpc:securityGroupRules:delete",
                "vpc:securityGroupRules:get"
            ]
        }
    ]
}
```

#### 腾讯云

在[访问管理](https://console.cloud.tencent.com/cam/overview) 中创建用户，获取 `SecretId` 和 `SecretKey`，赋予以下权限：

```json
{
  "statement": [
    {
      "action": [
        "cvm:DescribeSecurityGroup*",
        "cvm:Create*",
        "cvm:DeleteSecurityGroupPolicy"
      ],
      "effect": "allow",
      "resource": ["*"]
    }
  ],
  "version": "2.0"
}
```

#### 阿里云（轻量服务器防火墙）

在 [RAM 访问控制](https://ram.console.aliyun.com/) 中创建用户，获取 `AccessKeyId` 和 `AccessKeySecret`，赋予 `AliyunSWASFullAccess` 权限。

`sg` 字段填写**轻量服务器实例 ID**（非安全组 ID），`region` 填写实例所在地域如 `cn-hongkong`。

使用的接口：`ListFirewallRules`、`CreateFirewallRules`、`DeleteFirewallRules`。

### 静态 IP 白名单

每个 Provider 可独立配置静态 IP，与动态 IP（from Wulihe）共存：

```yaml
tencent:
  access_key: ...
  secret_key: ...
  regions: [...]
  static_ips:
    ips:
      - 203.0.113.50
      - 203.0.113.51
    except_ports:    # 可选，排除不需要静态 IP 访问的端口
      - 22
```

- `ips`: 固定 IP 列表，以 `from Abe` 为前缀写入规则
- `except_ports`: 排除端口列表，仅影响静态 IP 规则，不影响动态 IP 规则
- 注释掉整段 `static_ips` 会自动清理残留的 `from Abe` 规则

### IP 探测

```yaml
ipinfo:
  tokens:
    - your_ipinfo_token
```

推荐在 [ipinfo.io](https://ipinfo.io) 申请 token 以获得更高的请求限额。未配置时自动使用其他免费源。

### 高级配置

```yaml
# 规则前缀（默认 "from Wulihe"，仅管理匹配此前缀的规则）
rule_prefix: "from Wulihe"

# 检查间隔（默认 600 秒，最小 600 秒）
check_interval: 600

# 文件路径
paths:
  ip_cache: /var/lib/stay-in-whitelist/ip_cache.txt
  log_file: /var/log/stay-in-whitelist/stay_in_whitelist.log

# 超时设置
timeouts:
  ip_detection:
    connect: 3
    read: 5
  cloud_api:
    connect: 3
    read: 10
```

## 部署 (Deployment)

### systemd 服务配置

```bash
# 复制服务模板
sudo cp stay-in-whitelist.service /etc/systemd/system/

# 编辑路径（修改 WorkingDirectory 和 ExecStart 为实际路径）
sudo nano /etc/systemd/system/stay-in-whitelist.service

# 启动
sudo systemctl daemon-reload
sudo systemctl enable --now stay-in-whitelist
```

**注意：** 不要设置 `StandardOutput`/`StandardError` 重定向到日志文件，脚本已通过 `TimedRotatingFileHandler` 直接写文件，重复重定向会导致日志双倍。

### 日志管理

- 日志文件：项目根目录 `stay_in_whitelist.log`
- 每日午夜轮转，保留 30 天
- 实时查看：`journalctl -u stay-in-whitelist -f` 或 `tail -f stay_in_whitelist.log`

## 架构

```
stay_in_whitelist/
  cli.py                     # CLI 入口（--debug / --force / --look）
  config/config.py           # Pydantic 配置模型 + load_config()
  ip_fetcher.py              # IP 探测（多 provider 降级链）
  updater.py                 # 编排层：遍历云/region/安全组，委托给 provider
  logger.py                  # 日志（控制台 + 轮转文件）
  cloud_providers/
    base_cloud_provider.py   # 抽象基类（策略模式）
    huawei_cloud.py          # 华为云
    tencent_cloud.py         # 腾讯云
    aliyun_swas_firewall.py  # 阿里云轻量服务器防火墙
```

### 核心流程

1. **定时轮询** -- APScheduler 每隔 `check_interval` 秒触发
2. **IP 探测** -- 按 ipinfo -> icanhazip -> ipify -> ifconfig.me 降级
3. **变化检测** -- 当前 IP 与缓存对比
4. **规则更新** -- 基于 `(IP, port)` 指纹比较，跳过未变化的规则；变化时先添加后删除旧规则

### 策略模式

云服务提供商继承 `BaseCloudProvider`，实现统一接口：

- `initialize_client()` -- 初始化 SDK 客户端
- `get_rules()` -- 获取安全组规则
- `add_rules()` -- 添加规则
- `delete_rules()` -- 删除规则
- `rule_fingerprint()` -- 提取 `(ip, port)` 用于幂等比较

扩展其他云服务时，在 `stay_in_whitelist/cloud_providers/` 目录下新增实现即可。

## 迁移指南

从 `update-whitelist` 升级到 `stay-in-whitelist` 需要注意以下变化：

| 项目 | 旧值 | 新值 |
|------|------|------|
| 包名 | `update_whitelist` | `stay_in_whitelist` |
| 日志文件 | `update_whitelist.log` | `stay_in_whitelist.log` |
| 项目名 | update-whitelist | Stay in Whitelist |

## 开发

```bash
pip install -e ".[dev]"
pytest
pytest --cov=stay_in_whitelist
```

Python 版本支持：3.9、3.10、3.11、3.12、3.13。

## 许可证

MIT
