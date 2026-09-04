#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理列表抓取脚本
从指定源网站抓取代理列表并保存到本地文件
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ================================
# 配置
# ================================
class Config:
    """配置常量"""
    # 数据源
    SOURCE_URL = "https://tomcat1235.nyc.mn/proxy_list"
    
    # 请求配置
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # 秒
    
    # 请求头
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # 输出配置
    OUTPUT_FILE = "proxy.txt"
    
    # 有效协议
    VALID_PROTOCOLS = {"http", "https", "socks4", "socks5"}


@dataclass
class ProxyEntry:
    """代理条目"""
    protocol: str
    ip: str
    port: str
    location: str = ""
    
    def __post_init__(self):
        """数据清理"""
        self.protocol = self.protocol.lower().strip()
        self.ip = self.ip.strip()
        self.port = self.port.strip()
        self.location = self._clean_location(self.location)
    
    def _clean_location(self, location: str) -> str:
        """清理位置信息"""
        if not location:
            return ""
        # 移除常见的无用文本
        location = location.replace('复制', '').replace('已复制', '').replace('已', '')
        # 规范化空白
        location = ' '.join(location.split())
        return location
    
    @property
    def is_valid(self) -> bool:
        """验证代理是否有效"""
        if self.protocol not in Config.VALID_PROTOCOLS:
            return False
        if not self._is_valid_ip(self.ip):
            return False
        if not self._is_valid_port(self.port):
            return False
        return True
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """验证 IP 地址格式"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(p) <= 255 for p in parts)
    
    @staticmethod
    def _is_valid_port(port: str) -> bool:
        """验证端口格式"""
        try:
            p = int(port)
            return 1 <= p <= 65535
        except ValueError:
            return False
    
    def to_line(self) -> str:
        """转换为输出行格式"""
        base = f"{self.protocol}://{self.ip}:{self.port}"
        if self.location:
            return f"{base} [{self.location}]"
        return base


# ================================
# 抓取器
# ================================
class ProxyScraper:
    """代理列表抓取器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.session = None
    
    def _get_session(self) -> requests.Session:
        """获取请求会话"""
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': self.config.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            })
        return self.session
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """抓取页面内容，带重试机制"""
        session = self._get_session()
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                logger.info(f"正在抓取: {url} (尝试 {attempt + 1}/{self.config.MAX_RETRIES})")
                
                response = session.get(url, timeout=self.config.REQUEST_TIMEOUT)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                return response.text
                
            except requests.RequestException as e:
                logger.warning(f"请求失败: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    logger.info(f"等待 {self.config.RETRY_DELAY} 秒后重试...")
                    time.sleep(self.config.RETRY_DELAY)
        
        return None
    
    def _parse_table(self, html: str) -> List[ProxyEntry]:
        """解析 HTML 表格提取代理"""
        proxies = []
        soup = BeautifulSoup(html, 'html.parser')
        
        rows = soup.find_all('tr')
        if not rows:
            logger.error("未找到代理数据表格")
            return proxies

        seen = set()
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            
            try:
                protocol = cells[0].get_text(strip=True)
                ip = cells[1].get_text(strip=True)
                port = cells[2].get_text(strip=True)
                location = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                
                entry = ProxyEntry(
                    protocol=protocol,
                    ip=ip,
                    port=port,
                    location=location
                )
                
                if entry.is_valid:
                    key = (entry.protocol, entry.ip, entry.port)
                    if key not in seen:
                        seen.add(key)
                        proxies.append(entry)
                else:
                    logger.debug(f"跳过无效代理: {protocol}://{ip}:{port}")
                    
            except Exception as e:
                logger.debug(f"解析行失败: {e}")
                continue
        
        return proxies
    
    def scrape(self) -> List[ProxyEntry]:
        """执行抓取"""
        html = self._fetch_page(self.config.SOURCE_URL)
        if not html:
            logger.error("无法获取页面内容")
            return []
        
        proxies = self._parse_table(html)
        logger.info(f"成功解析 {len(proxies)} 个有效代理")
        
        return proxies
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
            self.session = None


# ================================
# 文件写入器
# ================================
class ProxyFileWriter:
    """代理文件写入器"""
    
    @staticmethod
    def save(proxies: List[ProxyEntry], filename: str) -> bool:
        """保存代理列表到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # 写入文件头
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"# 代理列表 - 自动更新\n")
                f.write(f"# 更新时间: {timestamp}\n")
                f.write(f"# 总计: {len(proxies)} 个代理\n")
                f.write(f"# 来源: {Config.SOURCE_URL}\n")
                f.write(f"# 格式: 协议://IP:端口 [位置]\n")
                f.write("\n")
                
                # 按协议分组排序
                proxies_sorted = sorted(proxies, key=lambda x: (x.protocol, x.ip))
                
                # 写入代理列表
                for proxy in proxies_sorted:
                    f.write(f"{proxy.to_line()}\n")
            
            logger.info(f"已保存 {len(proxies)} 个代理到 {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False


# ================================
# 统计
# ================================
def print_statistics(proxies: List[ProxyEntry]):
    """打印统计信息"""
    if not proxies:
        return
    
    print("\n📊 代理统计:")
    
    # 按协议统计
    protocol_count = {}
    for p in proxies:
        protocol_count[p.protocol] = protocol_count.get(p.protocol, 0) + 1
    
    print("   协议分布:")
    for proto, count in sorted(protocol_count.items()):
        print(f"   - {proto.upper()}: {count}")
    
    # 按位置统计（提取国家）
    country_count = {}
    for p in proxies:
        if p.location:
            # 尝试提取第一个词作为国家
            country = p.location.split()[0] if p.location else "未知"
            country_count[country] = country_count.get(country, 0) + 1
    
    if country_count:
        print("\n   位置分布 (Top 5):")
        for country, count in sorted(country_count.items(), key=lambda x: -x[1])[:5]:
            print(f"   - {country}: {count}")


# ================================
# 主程序
# ================================
def main():
    """主函数"""
    print("=" * 60)
    print("🌐 代理列表抓取工具 v2.0")
    print(f"   数据源: {Config.SOURCE_URL}")
    print("=" * 60)
    print()
    
    scraper = ProxyScraper()
    
    try:
        # 抓取代理
        proxies = scraper.scrape()
        
        if not proxies:
            logger.error("未能获取任何有效代理")
            return 1
        
        # 打印统计
        print_statistics(proxies)
        
        # 保存到文件
        success = ProxyFileWriter.save(proxies, Config.OUTPUT_FILE)
        
        if success:
            print()
            print("✨ 抓取完成!")
            return 0
        else:
            return 1
            
    finally:
        scraper.close()


if __name__ == "__main__":
    exit(main())
