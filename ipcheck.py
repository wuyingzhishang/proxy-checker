#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理质量检测脚本
使用 IPPure API (https://my.ippure.com/v1/info) 进行代理质量检测
支持 HTTP、HTTPS、SOCKS4、SOCKS5 代理协议
"""

import asyncio
import aiohttp
import re
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum
import sys

# SOCKS 代理支持
try:
    from aiohttp_socks import ProxyConnector, ProxyType
    SOCKS_SUPPORT = True
except ImportError:
    SOCKS_SUPPORT = False
    print("⚠️ aiohttp_socks 未安装，SOCKS 代理将无法使用")
    print("   安装命令: pip install aiohttp_socks")


# ================================
# 配置常量
# ================================
class Config:
    """配置常量"""
    API_URL = "https://my.ippure.com/v1/info"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # 超时配置（秒）
    CONNECT_TIMEOUT = 5
    TOTAL_TIMEOUT = 15
    
    # 并发配置
    MAX_CONCURRENT = 10  # 最大并发数
    REQUEST_DELAY = 0.5  # 请求间隔（秒）
    
    # 文件配置
    INPUT_FILE = "proxy.txt"
    OUTPUT_FILE = "proxy_checked.txt"
    
    # 重试配置
    MAX_RETRIES = 2


class ProxyQuality(Enum):
    """代理质量等级"""
    EXCELLENT = ("🌟", "优秀", 0, 10)
    GOOD = ("🟢", "良好", 10, 30)
    MEDIUM = ("🟡", "中等", 30, 50)
    POOR = ("🟠", "较差", 50, 70)
    BAD = ("🔴", "较差", 70, 90)
    TERRIBLE = ("⚫", "极差", 90, 100)
    UNKNOWN = ("❓", "未知", -1, -1)
    
    @classmethod
    def from_score(cls, score: int) -> 'ProxyQuality':
        """根据分数获取质量等级"""
        for quality in cls:
            if quality.value[2] <= score < quality.value[3]:
                return quality
        return cls.TERRIBLE if score >= 90 else cls.UNKNOWN


class IPType(Enum):
    """IP 类型"""
    RESIDENTIAL = ("🏠", "住宅IP")
    BROADCAST = ("📡", "广播IP")
    DATACENTER = ("🏢", "机房IP")
    UNKNOWN = ("❓", "未知")


@dataclass
class ProxyInfo:
    """代理信息"""
    original_line: str
    protocol: str = ""
    ip: str = ""
    port: str = ""
    location_hint: str = ""  # 原始行中的位置信息


@dataclass
class ProxyCheckResult:
    """代理检测结果"""
    proxy: ProxyInfo
    status: str = "pending"
    exit_ip: str = ""
    
    # IPPure API 返回的数据
    fraud_score: int = -1
    is_residential: bool = False
    is_broadcast: bool = False
    
    # 地理位置
    country: str = ""
    country_code: str = ""
    region: str = ""
    city: str = ""
    timezone: str = ""
    
    # ASN 信息
    asn: int = 0
    as_organization: str = ""
    
    # 计算字段
    response_time_ms: int = 0
    ip_match: bool = False  # 出口IP是否与代理IP匹配
    
    @property
    def quality(self) -> ProxyQuality:
        """获取代理质量等级"""
        return ProxyQuality.from_score(self.fraud_score)
    
    @property
    def ip_type(self) -> IPType:
        """获取 IP 类型"""
        if self.is_residential:
            return IPType.RESIDENTIAL
        elif self.is_broadcast:
            return IPType.BROADCAST
        elif self.status == "success":
            return IPType.DATACENTER
        return IPType.UNKNOWN
    
    @property
    def location_str(self) -> str:
        """格式化的地理位置"""
        parts = [p for p in [self.country, self.region, self.city] if p]
        return " ".join(parts) if parts else "未知"
    
    @property
    def summary(self) -> str:
        """生成检测结果摘要"""
        if self.status != "success":
            return f"❌ {self.status}"
        
        quality = self.quality
        ip_type = self.ip_type
        
        # 基本信息
        info = f"{quality.value[0]} 风险{self.fraud_score}% | {ip_type.value[1]}"
        
        # IP 匹配检查
        if not self.ip_match:
            info += " ⚠️透明"
        
        # 位置信息
        info += f" | {self.location_str}"
        
        # ASN 信息（简化显示）
        if self.as_organization:
            org_short = self.as_organization[:20] + "..." if len(self.as_organization) > 23 else self.as_organization
            info += f" ({org_short})"
        
        return info


# ================================
# 代理解析器
# ================================
class ProxyParser:
    """代理解析器"""
    
    # 支持的协议
    PROTOCOLS = {"http", "https", "socks4", "socks5"}
    
    # 正则表达式
    PROXY_PATTERN = re.compile(
        r'^(https?|socks[45])://'  # 协议
        r'(?:([^:@]+):([^@]+)@)?'  # 可选的用户名:密码
        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r':(\d+)'  # 端口
        r'(?:\s*\[([^\]]*)\])?',  # 可选的位置信息
        re.IGNORECASE
    )
    
    IP_PATTERN = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[ProxyInfo]:
        """解析代理行"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        match = cls.PROXY_PATTERN.match(line)
        if match:
            protocol = match.group(1).lower()
            ip = match.group(4)
            port = match.group(5)
            location_hint = match.group(6) or ""
            
            return ProxyInfo(
                original_line=line,
                protocol=protocol,
                ip=ip,
                port=port,
                location_hint=location_hint
            )
        
        return None
    
    @classmethod
    def parse_file(cls, filename: str) -> List[ProxyInfo]:
        """解析代理文件"""
        proxies = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    proxy = cls.parse_line(line)
                    if proxy:
                        proxies.append(proxy)
        except FileNotFoundError:
            print(f"❌ 文件不存在: {filename}")
        except Exception as e:
            print(f"❌ 读取文件错误: {e}")
        
        return proxies


# ================================
# 代理检测器
# ================================
class ProxyChecker:
    """代理检测器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT)
        self.results: List[ProxyCheckResult] = []
    
    def _get_proxy_connector(self, proxy: ProxyInfo):
        """获取代理连接器"""
        protocol = proxy.protocol.lower()
        
        if protocol in ('http', 'https'):
            # HTTP(S) 代理直接使用 aiohttp 的 proxy 参数
            return None, f"{protocol}://{proxy.ip}:{proxy.port}"
        
        elif protocol in ('socks4', 'socks5'):
            if not SOCKS_SUPPORT:
                raise RuntimeError("SOCKS 代理需要安装 aiohttp_socks")
            
            proxy_type = ProxyType.SOCKS4 if protocol == 'socks4' else ProxyType.SOCKS5
            connector = ProxyConnector(
                proxy_type=proxy_type,
                host=proxy.ip,
                port=int(proxy.port),
            )
            return connector, None
        
        raise ValueError(f"不支持的代理协议: {protocol}")
    
    async def check_single(self, proxy: ProxyInfo) -> ProxyCheckResult:
        """检测单个代理"""
        result = ProxyCheckResult(proxy=proxy)
        
        async with self.semaphore:
            for attempt in range(Config.MAX_RETRIES):
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    connector, proxy_url = self._get_proxy_connector(proxy)
                    
                    timeout = aiohttp.ClientTimeout(
                        connect=Config.CONNECT_TIMEOUT,
                        total=Config.TOTAL_TIMEOUT
                    )
                    
                    async with aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout
                    ) as session:
                        kwargs = {
                            "headers": {"User-Agent": Config.USER_AGENT}
                        }
                        if proxy_url:
                            kwargs["proxy"] = proxy_url
                        
                        async with session.get(Config.API_URL, **kwargs) as response:
                            result.response_time_ms = int(
                                (asyncio.get_event_loop().time() - start_time) * 1000
                            )
                            
                            if response.status != 200:
                                result.status = f"HTTP {response.status}"
                                continue
                            
                            data = await response.json()
                            
                            # 解析 API 响应
                            result.exit_ip = data.get('ip', '')
                            result.fraud_score = data.get('fraudScore', 0)
                            result.is_residential = data.get('isResidential', False)
                            result.is_broadcast = data.get('isBroadcast', False)
                            
                            result.country = data.get('country', '')
                            result.country_code = data.get('countryCode', '')
                            result.region = data.get('region', '')
                            result.city = data.get('city', '')
                            result.timezone = data.get('timezone', '')
                            
                            result.asn = data.get('asn', 0)
                            result.as_organization = data.get('asOrganization', '')
                            
                            # IP 匹配检查（判断是否透明代理）
                            result.ip_match = (result.exit_ip == proxy.ip)
                            
                            result.status = "success"
                            return result
                    
                except asyncio.TimeoutError:
                    result.status = "超时"
                except aiohttp.ClientProxyConnectionError as e:
                    result.status = "代理连接失败"
                except aiohttp.ClientError as e:
                    error_msg = str(e)[:50]
                    result.status = f"连接错误: {error_msg}"
                except RuntimeError as e:
                    result.status = str(e)
                    break  # 不重试配置错误
                except Exception as e:
                    error_msg = str(e)[:50]
                    result.status = f"错误: {error_msg}"
                
                # 重试延迟
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(1)
            
            return result
    
    async def check_all(self, proxies: List[ProxyInfo], 
                        progress_callback=None) -> List[ProxyCheckResult]:
        """批量检测代理"""
        self.results = []
        total = len(proxies)
        
        for i, proxy in enumerate(proxies, 1):
            result = await self.check_single(proxy)
            self.results.append(result)
            
            # 进度回调
            if progress_callback:
                progress_callback(i, total, result)
            
            # 请求间隔（避免 API 限流）
            if i < total:
                await asyncio.sleep(Config.REQUEST_DELAY)
        
        return self.results
    
    def get_statistics(self) -> dict:
        """获取检测统计"""
        total = len(self.results)
        success = sum(1 for r in self.results if r.status == "success")
        
        # 按质量等级统计
        quality_stats = {}
        for quality in ProxyQuality:
            count = sum(1 for r in self.results 
                       if r.status == "success" and r.quality == quality)
            if count > 0:
                quality_stats[quality.value[1]] = count
        
        # 按 IP 类型统计
        ip_type_stats = {}
        for ip_type in IPType:
            count = sum(1 for r in self.results 
                       if r.status == "success" and r.ip_type == ip_type)
            if count > 0:
                ip_type_stats[ip_type.value[1]] = count
        
        # 按地区统计
        country_stats = {}
        for r in self.results:
            if r.status == "success" and r.country:
                country_stats[r.country] = country_stats.get(r.country, 0) + 1
        
        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": f"{(success/total*100):.1f}%" if total > 0 else "0%",
            "quality_distribution": quality_stats,
            "ip_type_distribution": ip_type_stats,
            "country_distribution": country_stats
        }


# ================================
# 报告生成器
# ================================
class ReportGenerator:
    """报告生成器"""
    
    @staticmethod
    def generate_text_report(results: List[ProxyCheckResult], 
                             stats: dict) -> str:
        """生成文本报告"""
        lines = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 标题
        lines.append(f"# 代理质量检测报告")
        lines.append(f"# 检测时间: {timestamp}")
        lines.append(f"# API: IPPure (https://my.ippure.com/v1/info)")
        lines.append("")
        
        # 统计摘要
        lines.append("## 📊 统计摘要")
        lines.append(f"# 总计: {stats['total']} | 成功: {stats['success']} | 失败: {stats['failed']} | 成功率: {stats['success_rate']}")
        lines.append("")
        
        # 质量分布
        if stats['quality_distribution']:
            lines.append("## 质量分布")
            for quality, count in stats['quality_distribution'].items():
                lines.append(f"# {quality}: {count}")
            lines.append("")
        
        # IP 类型分布
        if stats['ip_type_distribution']:
            lines.append("## IP类型分布")
            for ip_type, count in stats['ip_type_distribution'].items():
                lines.append(f"# {ip_type}: {count}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("")
        
        # 成功的代理（按质量排序）
        success_results = [r for r in results if r.status == "success"]
        success_results.sort(key=lambda x: x.fraud_score)
        
        if success_results:
            lines.append("## ✅ 可用代理列表 (按质量排序)")
            lines.append("")
            for r in success_results:
                lines.append(f"{r.proxy.original_line}")
                lines.append(f"  → {r.summary}")
                if r.exit_ip and r.exit_ip != r.proxy.ip:
                    lines.append(f"  → 出口IP: {r.exit_ip}")
                lines.append("")
        
        # 失败的代理
        failed_results = [r for r in results if r.status != "success"]
        if failed_results:
            lines.append("## ❌ 失败代理列表")
            lines.append("")
            for r in failed_results:
                lines.append(f"{r.proxy.original_line}")
                lines.append(f"  → {r.status}")
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def save_report(content: str, filename: str):
        """保存报告到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 报告已保存到 {filename}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")


# ================================
# 主程序
# ================================
def print_progress(current: int, total: int, result: ProxyCheckResult):
    """打印检测进度"""
    progress = f"[{current}/{total}]"
    proxy_str = f"{result.proxy.protocol}://{result.proxy.ip}:{result.proxy.port}"
    
    if result.status == "success":
        print(f"{progress} ✅ {proxy_str}")
        print(f"       {result.summary}")
    else:
        print(f"{progress} ❌ {proxy_str}")
        print(f"       {result.status}")


async def main():
    """主函数"""
    print("=" * 60)
    print("🔍 代理质量检测工具 v2.0")
    print("   API: IPPure (https://my.ippure.com/v1/info)")
    print("=" * 60)
    print()
    
    # 检查 SOCKS 支持
    if not SOCKS_SUPPORT:
        print("⚠️ 警告: SOCKS 代理支持未启用")
        print("   请运行: pip install aiohttp_socks")
        print()
    
    # 解析代理文件
    proxies = ProxyParser.parse_file(Config.INPUT_FILE)
    
    if not proxies:
        print(f"❌ 未找到有效代理，请检查 {Config.INPUT_FILE}")
        return
    
    print(f"📋 发现 {len(proxies)} 个代理，开始检测...")
    print()
    
    # 开始检测
    checker = ProxyChecker()
    results = await checker.check_all(proxies, progress_callback=print_progress)
    
    print()
    print("=" * 60)
    
    # 获取统计
    stats = checker.get_statistics()
    
    # 打印统计摘要
    print()
    print("📊 检测统计:")
    print(f"   总计: {stats['total']} | 成功: {stats['success']} | 失败: {stats['failed']}")
    print(f"   成功率: {stats['success_rate']}")
    
    if stats['quality_distribution']:
        print()
        print("   质量分布:")
        for quality, count in stats['quality_distribution'].items():
            print(f"   - {quality}: {count}")
    
    if stats['ip_type_distribution']:
        print()
        print("   IP类型分布:")
        for ip_type, count in stats['ip_type_distribution'].items():
            print(f"   - {ip_type}: {count}")
    
    print()
    
    # 生成并保存报告
    report = ReportGenerator.generate_text_report(results, stats)
    ReportGenerator.save_report(report, Config.OUTPUT_FILE)
    
    print()
    print("✨ 检测完成!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 检测被用户中断")
        sys.exit(1)
