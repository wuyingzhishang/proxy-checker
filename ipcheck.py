import asyncio
import aiohttp
import re
from datetime import datetime

try:
    from aiohttp_socks import ProxyConnector
    SOCKS_SUPPORT = True
except ImportError:
    SOCKS_SUPPORT = False

def get_emoji(score):
    try:
        val = int(score)
        if val <= 10: return "⚪"
        if val <= 30: return "🟢"
        if val <= 50: return "🟡"
        if val <= 70: return "🟠"
        if val <= 90: return "🔴"
        return "⚫"
    except:
        return "❓"

def parse_proxy_file(filename='proxy.txt'):
    proxies = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
        return proxies
    except Exception as e:
        print(f"读取代理文件错误: {e}")
        return []

def extract_ip_from_line(line):
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
    if match:
        return match.group(1)
    return None

def extract_protocol_and_port(line):
    match = re.search(r'(https?|socks[45])://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)', line)
    if match:
        protocol = match.group(1)
        port = match.group(3)
        return protocol, port
    return None, None

async def check_proxy(ip, protocol, port):
    result = {
        'ip': ip,
        'protocol': protocol,
        'port': port,
        'status': 'error',
        'pure_score': '❓',
        'bot_ratio': '❓',
        'ip_attr': '❓',
        'ip_src': '❓'
    }
    
    try:
        proxy = f"{protocol}://{ip}:{port}"
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://my.ippure.com/v1/info",
                proxy=proxy,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
            ) as response:
                if response.status != 200:
                    result['status'] = f'HTTP {response.status}'
                    return result
                
                data = await response.json()
                
                fraud_score = data.get('fraudScore', 0)
                pure_score = f"{fraud_score}%"
                pure_emoji = get_emoji(fraud_score)
                
                bot_ratio = f"{min(fraud_score, 100)}%"
                bot_emoji = get_emoji(fraud_score)
                
                ip_attr = []
                if data.get('isResidential'):
                    ip_attr.append("住宅")
                elif data.get('isBroadcast'):
                    ip_attr.append("广播")
                else:
                    ip_attr.append("机房")
                
                if not data.get('isResidential') and not data.get('isBroadcast'):
                    ip_attr.append("数据中心")
                
                ip_attr_str = " ".join(ip_attr)
                
                country = data.get('country', '')
                region = data.get('region', '')
                city = data.get('city', '')
                ip_src = f"{country} {region} {city}".strip()
                
                result['status'] = 'success'
                result['pure_score'] = pure_score
                result['bot_ratio'] = bot_ratio
                result['ip_attr'] = ip_attr_str
                result['ip_src'] = ip_src
                result['summary'] = f"【{pure_emoji}{bot_emoji} {ip_attr_str} {ip_src}】"
                
    except asyncio.TimeoutError:
        result['status'] = 'timeout'
    except aiohttp.ClientProxyConnectionError:
        result['status'] = 'proxy connection error'
    except aiohttp.ClientError as e:
        result['status'] = f'error: {str(e)[:50]}'
    except Exception as e:
        result['status'] = f'error: {str(e)[:50]}'
    
    return result

async def main():
    proxy_lines = parse_proxy_file('proxy.txt')
    
    if not proxy_lines:
        print("未找到代理列表")
        return
    
    print(f"开始检测 {len(proxy_lines)} 个代理...")
    
    results = []
    
    for i, line in enumerate(proxy_lines, 1):
        ip = extract_ip_from_line(line)
        protocol, port = extract_protocol_and_port(line)
        
        if not ip or not protocol or not port:
            print(f"[{i}/{len(proxy_lines)}] 跳过无效行: {line[:50]}...")
            results.append({
                'original_line': line,
                'status': 'invalid format',
                'summary': '❓ 格式错误'
            })
            continue
        
        print(f"[{i}/{len(proxy_lines)}] 正在检测: {ip}:{port}")
        result = await check_proxy(ip, protocol, port)
        results.append({
            'original_line': line,
            'ip': ip,
            'protocol': protocol,
            'port': port,
            'status': result['status'],
            'summary': result.get('summary', '❓')
        })
        
        if result['status'] == 'success':
            print(f"  ✓ 检测成功: {result['summary']}")
        else:
            print(f"  ✗ 检测失败: {result['status']}")
        
        await asyncio.sleep(2)
    
    print(f"\n检测完成！")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open('proxy_checked.txt', 'w', encoding='utf-8') as f:
        f.write(f"# 代理质量检测结果 - {timestamp}\n")
        f.write(f"# 总计: {len(proxy_lines)} 个代理\n\n")
        
        for item in results:
            if item['status'] == 'success':
                f.write(f"{item['original_line']} {item['summary']}\n")
            else:
                f.write(f"{item['original_line']} ❌ {item['status']}\n")
    
    print(f"检测结果已保存到 proxy_checked.txt")

if __name__ == "__main__":
    asyncio.run(main())
