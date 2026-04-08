# Stay in Whitelist

[![License](https://img.shields.io/github/license/abrahamgreyson/update-whitelist.svg?)](https://opensource.org/license/mit)
[![CodeFactor](https://www.codefactor.io/repository/github/abrahamgreyson/update-whitelist/badge)](https://www.codefactor.io/repository/github/abrahamgreyson/update-whitelist)
[![Test](https://github.com/abrahamgreyson/update-whitelist/actions/workflows/test.yml/badge.svg)](https://github.com/abrahamgreyson/update-whitelist/actions/workflows/test.yml)
[![Codecov](https://codecov.io/gh/abrahamgreyson/update-whitelist/branch/main/graph/badge.svg?token=Fc4MbBmMpZ)](https://codecov.io/gh/abrahamgreyson/update-whitelist?branch=main)
[![Python versions](https://img.shields.io/badge/python-3.9%7C3.10%7C3.11%7C3.12-blue)](https://github.com/abrahamgreyson/update-whitelist/actions/workflows/test.yml)

定时检测本地公网 IP 变化，自动更新云服务安全组白名单。

在没有堡垒机的情况下，避免长期暴露数据库、应用端口等敏感端口。部署为 systemd 服务长期运行，IP 变了白名单自动跟上 -- 不漏更、不挂死、不锁死。

## 功能特性

- **多云支持** -- 华为云、腾讯云，可扩展其他云服务
- **多层级配置** -- 每个云支持多个 region，每个 region 支持多个安全组，每个安全组支持多个端口
- **IP 探测降级链** -- ipinfo -> icanhazip -> ipify -> ifconfig.me，自动切换可用源
- **可配置规则前缀** -- 支持 dev/prod 环境隔离，默认 `from Wulihe`
- **先加后删更新策略** -- 避免规则清空导致用户被锁死
- **云 API 重试** -- 网络超时自动指数退避重试
- **systemd 长期运行** -- 开机自启，异常自动恢复

## 快速开始

### 1. 安装

```bash
git clone https://github.com/abrahamgreyson/update-whitelist.git
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
# 前台运行（调试用，带控制台输出）
python main.py

# 后台运行
nohup python main.py > /dev/null 2>&1 &
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

使用的 VPC 接口：`ListSecurityGroupRule`、`DeleteSecurityGroupRule`、`BatchCreateSecurityGroupRules`。

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

使用的接口：`DescribeSecurityGroupPolicies`、`DeleteSecurityGroupPolicies`、`CreateSecurityGroupPolicies`。

### IP 探测

```yaml
ipinfo:
  tokens:
    - your_ipinfo_token
```

推荐在 [ipinfo.io](https://ipinfo.io) 申请 token 以获得更高的请求限额。如果未配置 token，工具会自动跳过 ipinfo，使用其他免费 IP 探测源（icanhazip、ipify、ifconfig.me）。

### 高级配置

#### 检查间隔

```yaml
check_interval: 600  # 默认 600 秒（10 分钟），最小 600 秒
```

#### 规则前缀（dev/prod 隔离）

```yaml
rule_prefix: "from Wulihe"  # 默认值
```

安全组规则的描述前缀。工具只管理匹配此前缀的规则。

**dev/prod 隔离示例：** 如果开发环境和生产环境共用同一个安全组，可以设置不同的前缀（如 `from Wulihe-dev` 和 `from Wulihe-prod`），各自管理各自的规则，互不干扰。

注意：更换前缀后，旧前缀的规则会变成孤儿规则，需要手动清理。

#### 文件路径

```yaml
paths:
  ip_cache: /var/lib/stay-in-whitelist/ip_cache.txt   # IP 缓存文件路径
  log_file: /var/log/stay-in-whitelist/stay_in_whitelist.log  # 日志文件路径
```

默认情况下，缓存文件和日志文件存放在项目目录下。systemd 部署建议使用绝对路径。

#### 超时设置

```yaml
timeouts:
  ip_detection:
    connect: 3   # 连接超时（秒）
    read: 5      # 读取超时（秒）
  cloud_api:
    connect: 3   # 连接超时（秒）
    read: 10     # 读取超时（秒）
```

大多数情况下不需要调整。

## 部署 (Deployment)

### systemd 服务配置

Stay in Whitelist 可以作为 systemd 服务长期运行，实现开机自启动和故障自动恢复。

#### 1. 安装服务

```bash
# 复制服务模板到 systemd 目录
sudo cp stay-in-whitelist.service /etc/systemd/system/

# 编辑服务文件，自定义路径（重要！）
sudo nano /etc/systemd/system/stay-in-whitelist.service
```

#### 2. 自定义路径

在服务文件中修改以下路径为实际部署位置：

```ini
[Service]
# 修改为项目实际路径
WorkingDirectory=/home/yourusername/stay-in-whitelist
ExecStart=/home/yourusername/stay-in-whitelist/venv/bin/python /home/yourusername/stay-in-whitelist/main.py

# 修改日志路径（可选，默认使用项目内的 stay_in_whitelist.log）
StandardOutput=append:/home/yourusername/stay-in-whitelist/stay_in_whitelist.log
StandardError=append:/home/yourusername/stay-in-whitelist/stay_in_whitelist.log
```

**路径说明：**
- `WorkingDirectory`: 项目根目录，包含 main.py 和 config.yaml
- `ExecStart`: Python 解释器路径（venv/bin/python）和 main.py 完整路径
- `StandardOutput`/`StandardError`: 日志文件路径，需确保有写入权限

#### 3. 启动服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启动
sudo systemctl enable stay-in-whitelist

# 启动服务
sudo systemctl start stay-in-whitelist

# 查看服务状态
sudo systemctl status stay-in-whitelist
```

#### 4. 服务管理

```bash
# 查看实时日志
sudo journalctl -u stay-in-whitelist -f

# 查看最近 100 行日志
sudo journalctl -u stay-in-whitelist -n 100

# 停止服务
sudo systemctl stop stay-in-whitelist

# 重启服务
sudo systemctl restart stay-in-whitelist

# 禁用开机自启动
sudo systemctl disable stay-in-whitelist
```

### 日志管理

服务运行后，日志文件位于项目根目录的 `stay_in_whitelist.log`。

**日志轮转配置：**
- 每日午夜自动轮转
- 保留最近 30 天的日志文件
- 旧日志自动删除，避免磁盘占用过多

**查看日志文件：**
```bash
# 查看当前日志
tail -f stay_in_whitelist.log

# 查看历史日志（轮转后的备份）
ls -lh stay_in_whitelist.log*
```

### 故障排查

**服务无法启动：**
1. 检查路径配置是否正确（WorkingDirectory、ExecStart）
2. 检查 Python 虚拟环境是否存在：`ls venv/bin/python`
3. 检查 config.yaml 是否存在且格式正确
4. 查看详细错误日志：`sudo journalctl -u stay-in-whitelist -n 50`

**IP 检测失败：**
1. 检查网络连接：`ping ipinfo.io`
2. 检查 config.yaml 中的 IP 检测服务配置
3. 查看日志中的错误信息

**云服务白名单未更新：**
1. 检查 config.yaml 中的云服务凭证是否正确
2. 检查安全组 ID 和区域配置
3. 确认 rule_prefix 配置正确（默认 "from Wulihe"）
4. 查看日志中的 API 调用结果

**日志文件过大：**
- 日志会自动轮转，保留最近 30 天
- 如果需要手动清理：`rm stay_in_whitelist.log.[N]`（N > 30）
- 检查日志轮转是否正常：`ls -lh stay_in_whitelist.log*`

## 架构

```
main.py                     # 入口：APScheduler 定时调度
stay_in_whitelist/
  config/config.py          # Pydantic 配置模型 + load_config()
  ip_fetcher.py             # IP 探测（多 provider 降级链）
  updater.py                # 编排层：遍历云/region/安全组，委托给 provider
  logger.py                 # 日志（控制台 + 轮转文件）
  cloud_providers/
    base_cloud_provider.py  # 抽象基类（策略模式）
    huawei_cloud.py         # 华为云实现
    tencent_cloud.py        # 腾讯云实现
```

### 核心流程

1. **定时轮询** -- APScheduler 每隔 `check_interval` 秒触发一次检查
2. **IP 探测** -- 按 ipinfo -> icanhazip -> ipify -> ifconfig.me 顺序尝试，返回第一个有效 IP
3. **变化检测** -- 将当前 IP 与 `ip_cache.txt` 中的缓存 IP 对比
4. **规则更新** -- IP 变化时，遍历配置的云服务商/region/安全组，**先添加新规则再删除旧规则**，避免中间断档

### 策略模式

云服务提供商继承 `BaseCloudProvider`，实现统一接口：

- `initialize_client()` -- 初始化 SDK 客户端
- `get_rules()` -- 获取安全组规则（失败返回空列表）
- `add_rules()` -- 添加安全组规则
- `delete_rules()` -- 删除安全组规则

扩展其他云服务时，在 `stay_in_whitelist/cloud_providers/` 目录下新增实现即可。

## 迁移指南

从 `update-whitelist` 升级到 `stay-in-whitelist` 需要注意以下变化：

| 项目 | 旧值 | 新值 |
|------|------|------|
| 包名 | `update_whitelist` | `stay_in_whitelist` |
| 日志文件 | `update_whitelist.log` | `stay_in_whitelist.log` |
| 项目名 | update-whitelist | Stay in Whitelist |

**注意事项：**

- `config.yaml` 的字段名没有变化，现有配置文件可以直接使用
- 旧的 `ip_cache.txt` 格式不变，可以继续使用
- 旧日志文件 `update_whitelist.log` 不会自动迁移，可手动删除或归档
- 安全组中的旧规则描述前缀（如 `from Wulihe`）不受影响，工具会继续管理匹配的规则

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 带覆盖率报告
pytest --cov=stay_in_whitelist
```

Python 版本支持：3.9、3.10、3.11、3.12。

## 许可证

MIT
