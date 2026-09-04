# Proxy Checker

自动聚合、清洗并检测公开代理的 GitHub Actions 项目。代理列表每 3 天更新一次，检测报告在代理列表更新成功后自动生成。

## 快速访问

以下链接始终指向仓库 `main` 分支的最新文件：

- **代理列表（原始池）**：[proxy.txt](https://raw.githubusercontent.com/wuyingzhishang/proxy-checker/main/proxy.txt)
- **质量检测报告**：[proxy_checked.txt](https://raw.githubusercontent.com/wuyingzhishang/proxy-checker/main/proxy_checked.txt)
- **GitHub Actions**：[查看更新与检测状态](https://github.com/wuyingzhishang/proxy-checker/actions)

> `proxy.txt` 是经过格式校验、去重后的代理池；`proxy_checked.txt` 只将实际检测成功的代理列为可用。免费代理可能随时失效，请在使用前再次验证。

## 数据概览

- **协议**：HTTP、HTTPS、SOCKS4、SOCKS5
- **聚合方式**：多源抓取、统一解析、IP/端口校验、重复项去除
- **质量检测**：通过 IPPure API 检查出口 IP、风险分数、IP 类型、地理位置和 ASN
- **并发检测**：受并发上限和请求间隔控制，保留输入顺序输出进度
- **多源聚合**：遍历全部来源并合并结果，跨来源统一去重；单个来源故障不会阻断其他来源
- **故障降级**：所有源暂时不可用时保留上一份有效列表
- **更新频率**：GitHub Actions 默认每 3 天运行一次，也支持手动触发


## 文件格式

### `proxy.txt`

每行一个代理，格式如下：

```text
socks5://1.2.3.4:1080 [位置或来源标记]
http://5.6.7.8:8080
```

### `proxy_checked.txt`

报告包含统计摘要、质量分布、IP 类型分布、地理位置、ASN、响应时间和失败原因。成功代理按风险分数从低到高排列。

## 快速开始

### 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 抓取代理列表

```bash
python generate_proxy_list.py
```

### 检测代理质量

```bash
python ipcheck.py
```

SOCKS4/SOCKS5 检测需要 `aiohttp_socks`，该依赖已包含在 `requirements.txt` 中。

## 质量评分

| 风险分数 | 等级 | 含义 |
|:--:|:--:|:--|
| 0-10 | 🌟 优秀 | 极低风险 |
| 10-30 | 🟢 良好 | 低风险 |
| 30-50 | 🟡 中等 | 需要谨慎使用 |
| 50-70 | 🟠 较差 | 可能被部分网站阻止 |
| 70-90 | 🔴 差 | 高风险 |
| 90-100 | ⚫ 极差 | 不建议使用 |

出口 IP 与代理地址不同时，报告会标记“出口 IP 不同”。这可能是负载均衡、IPv6 出口或代理链路造成的，不单独作为透明代理判定依据。

## 配置

主要配置位于 `generate_proxy_list.py` 和 `ipcheck.py` 的 `Config` 类：

```python
# 抓取
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# 检测
CONNECT_TIMEOUT = 5
TOTAL_TIMEOUT = 15
MAX_CONCURRENT = 10
REQUEST_DELAY = 0.5
MAX_RETRIES = 2
```

代理源可在 `generate_proxy_list.py` 的 `SOURCE_URLS` 中调整。源返回 HTML 表格、带协议的纯文本或普通 `IP:端口` 文本均可被解析。

## GitHub Actions

| 工作流 | 触发条件 | 输出 |
|---|---|---|
| 更新代理列表 | 每 3 天或手动触发 | `proxy.txt` |
| 检测代理质量 | 列表更新成功后或手动触发 | `proxy_checked.txt` |

工作流使用并发锁避免重复运行，并在在线源短时故障时保留已有有效数据。首次运行且所有源均不可用时会失败，以便及时发现配置问题。

## 代理来源（致谢）

本项目当前实际使用以下 5 个公开来源，不对任何单独来源做质量或安全背书：

- [tomcat1235 proxy_list](https://tomcat1235.nyc.mn/proxy_list)
- [HankNovic/ProxyClean SOCKS5](https://raw.githubusercontent.com/HankNovic/ProxyClean/refs/heads/main/SOCKS5.txt)
- [proxy.scdn.io API](https://proxy.scdn.io/api/get_proxy.php?protocol=all&count=10)
- [proxifly/free-proxy-list](https://github.com/proxifly/free-proxy-list)
- [TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List)

其中 `proxy.scdn.io` 返回未带协议的 `IP:端口`，项目按 HTTP 代理解析；实际协议请以源站信息和使用结果为准。

## 风险与免责声明

公开免费代理不保证稳定性、匿名性、真实性或安全性。请勿通过免费代理传输密码、令牌、个人信息或其他敏感数据，并遵守所在地法律法规、目标网站条款和代理来源的使用规则。本项目仅用于学习、测试和网络调试。

## 许可证

MIT License
