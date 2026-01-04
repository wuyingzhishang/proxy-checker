import asyncio
import aiohttp
from datetime import datetime

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

async def check_proxy(proxy_url):
    result = {
        'proxy': proxy_url,
        'status': 'error',
        'pure_score': '❓',
        'bot_ratio': '❓',
        'ip_attr': '❓',
        'ip_src': '❓'
    }
    
    try:
        proxy = None
        if proxy_url.startswith('http://'):
            proxy = f"http://{proxy_url[7:]}"
        elif proxy_url.startswith('https://'):
            proxy = f"https://{proxy_url[8:]}"
        elif proxy_url.startswith('socks5://'):
            proxy = f"socks5://{proxy_url[8:]}"
        elif proxy_url.startswith('socks4://'):
            proxy = f"socks4://{proxy_url[8:]}"
        
        if not proxy:
            result['status'] = 'invalid proxy format'
            return result
        
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
    proxies = parse_proxy_file('proxy.txt')
    
    if not proxies:
        print("未找到代理列表")
        return
    
    print(f"开始检测 {len(proxies)} 个代理...")
    
    results = []
    checked_proxies = []
    
    for i, proxy in enumerate(proxies, 1):
        print(f"[{i}/{len(proxies)}] 正在检测: {proxy}")
        result = await check_proxy(proxy)
        results.append(result)
        
        if result['status'] == 'success':
            checked_proxies.append({
                'proxy': proxy,
                'summary': result['summary']
            })
            print(f"  ✓ 检测成功: {result['summary']}")
        else:
            print(f"  ✗ 检测失败: {result['status']}")
        
        await asyncio.sleep(2)
    
    print(f"\n检测完成！成功: {len(checked_proxies)}/{len(proxies)}")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open('proxy_checked.txt', 'w', encoding='utf-8') as f:
        f.write(f"# 代理质量检测结果 - {timestamp}\n")
        f.write(f"# 总计: {len(proxies)} 个代理 | 成功检测: {len(checked_proxies)} 个\n\n")
        
        if checked_proxies:
            f.write("# 可用代理列表\n")
            for item in checked_proxies:
                f.write(f"{item['proxy']} {item['summary']}\n")
        else:
            f.write("# 没有可用的代理\n")
        
        f.write(f"\n# 检测详情\n")
        for i, result in enumerate(results, 1):
            status_icon = "✓" if result['status'] == 'success' else "✗"
            f.write(f"{status_icon} {result['proxy']}\n")
            if result['status'] == 'success':
                f.write(f"  {result['summary']}\n")
            else:
                f.write(f"  状态: {result['status']}\n")
    
    print(f"检测结果已保存到 proxy_checked.txt")

if __name__ == "__main__":
    asyncio.run(main())
