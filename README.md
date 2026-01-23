# 🌐 Proxy-Checker: 高质量代理自动检测与筛选

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white&style=flat-square" alt="Python">
  <img src="https://img.shields.io/github/license/wuyingzhishang/proxy-checker?style=flat-square" alt="License">
  <br>
  <img src="https://img.shields.io/github/actions/workflow/status/wuyingzhishang/proxy-checker/update-proxy-list.yml?label=代理列表更新&style=flat-square" alt="Proxy Update">
  <img src="https://img.shields.io/github/actions/workflow/status/wuyingzhishang/proxy-checker/check-proxy-quality.yml?label=质量深度检测&style=flat-square" alt="Quality Check">
</p>

> **🚀 自动抓取全球代理 • 深度质量评估 • 每小时实时更新**

本项目是一个全自动化的代理筛选工具，致力于提供**真正可用**的高质量代理列表。

### ✨ 核心亮点

- 🔄 **自动抓取**：每小时自动从公开源获取最新代理，拒绝陈旧数据。
- 🛡️ **深度检测**：集成 **IPPure 官方 API**，不仅检测连通性，更评估**IP纯净度**。
- 📊 **多维评分**：提供 **风险系数 (Fraud Score)**、**IP类型** (住宅/机房/广播) 及 **ASN归属** 详情。
- ⚡ **智能筛选**：自动过滤高延迟、高风险及透明代理，确保列表的高可用性。
- 🌍 **全球覆盖**：支持 HTTP/HTTPS/SOCKS4/SOCKS5 协议及全球地理位置解析。

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 抓取代理列表

```bash
python generate_proxy_list.py
```

### 检测代理质量

```bash
python ipcheck.py
```

## 📋 输出文件

### proxy.txt - 原始代理列表

```
# 代理列表 - 自动更新
# 更新时间: 2026-01-23 09:00:00
# 总计: 30 个代理

socks5://82.146.39.75:1080 [俄罗斯 莫斯科州 巴拉希哈]
http://123.143.162.221:6388 [韩国 首尔特别市]
socks5://35.183.59.99:5080 [加拿大 魁北克省 蒙特利尔]
```

### proxy_checked.txt - 质量检测报告

```
# 代理质量检测报告
# 检测时间: 2026-01-23 09:05:00

## 📊 统计摘要
# 总计: 30 | 成功: 15 | 失败: 15 | 成功率: 50.0%

## ✅ 可用代理列表 (按质量排序)
socks5://82.146.39.75:1080 [俄罗斯 莫斯科州]
  → 🌟 风险5% | 住宅IP | Russia Moscow Oblast Balashikha (JSC Datacenter)
```

## 📊 质量评分系统

| Emoji | 风险分数 | 质量等级 | 说明 |
|:-----:|:--------:|:--------:|------|
| 🌟 | 0-10 | 优秀 | 极低风险，高度可信 |
| 🟢 | 10-30 | 良好 | 低风险，适合一般使用 |
| 🟡 | 30-50 | 中等 | 中等风险，需谨慎使用 |
| 🟠 | 50-70 | 较差 | 较高风险，可能被部分网站阻止 |
| 🔴 | 70-90 | 差 | 高风险，大概率被阻止 |
| ⚫ | 90+ | 极差 | 极高风险，不建议使用 |

## 🔍 检测指标

| 指标 | 说明 |
|------|------|
| **风险分数** (fraudScore) | IPPure 评估的 IP 风险系数 (0-100) |
| **IP 类型** | 🏠 住宅IP / 📡 广播IP / 🏢 机房IP |
| **透明检测** | ⚠️ 标记 = 出口IP与代理IP不匹配（透明代理） |
| **地理位置** | 国家/地区/城市 + ASN 组织信息 |

## ⚙️ 配置说明

### ipcheck.py 配置

```python
class Config:
    API_URL = "https://my.ippure.com/v1/info"  # 检测 API
    CONNECT_TIMEOUT = 10   # 连接超时（秒）
    TOTAL_TIMEOUT = 30     # 总超时（秒）
    MAX_CONCURRENT = 5     # 最大并发数
    REQUEST_DELAY = 1.0    # 请求间隔（秒）
    MAX_RETRIES = 2        # 重试次数
```

### 支持的代理协议

- ✅ HTTP
- ✅ HTTPS
- ✅ SOCKS4
- ✅ SOCKS5

> ⚠️ **重要**: SOCKS 代理支持需要安装 `aiohttp_socks`

## 🤖 GitHub Actions 自动化

| 工作流 | 触发条件 | 说明 |
|--------|----------|------|
| **更新代理列表** | 每小时整点 | 抓取最新代理，更新 `proxy.txt` |
| **检测代理质量** | 代理列表更新后 | 检测质量，生成 `proxy_checked.txt` |

支持手动触发：Repository → Actions → 选择工作流 → Run workflow

## 📦 依赖项

| 包名 | 用途 |
|------|------|
| `requests` | HTTP 请求（抓取） |
| `beautifulsoup4` | HTML 解析 |
| `aiohttp` | 异步 HTTP 客户端（检测） |
| `aiohttp_socks` | SOCKS 代理支持 |
| `lxml` | 高性能 HTML 解析（可选） |

## 📄 许可证

MIT License

## ⚠️ 免责声明

本项目仅用于学习和研究目的。使用代理时请遵守：
- 当地法律法规
- 目标网站的使用条款
- 代理提供者的服务协议
