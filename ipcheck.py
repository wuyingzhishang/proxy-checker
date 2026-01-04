import asyncio
import re
from playwright.async_api import async_playwright
from datetime import datetime

def get_emoji(percentage_str):
    try:
        val = float(percentage_str.replace('%', ''))
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            proxy={"server": proxy_url},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        result = {
            'proxy': proxy_url,
            'status': 'error',
            'pure_score': '❓',
            'bot_ratio': '❓',
            'ip_attr': '❓',
            'ip_src': '❓'
        }
        
        try:
            await page.goto("https://ippure.com/", wait_until="domcontentloaded", timeout=30000)
            
            try:
                await page.wait_for_selector("text=人机流量比", timeout=15000)
            except:
                result['status'] = 'timeout'
                return result

            await page.wait_for_timeout(2000)
            text = await page.inner_text("body")
            
            score_match = re.search(r"IPPure系数.*?(\d+%)", text, re.DOTALL)
            pure_score = score_match.group(1) if score_match else "❓"
            pure_emoji = get_emoji(pure_score)

            bot_match = re.search(r"bot\s*(\d+(\.\d+)?)%", text, re.IGNORECASE)
            bot_val = bot_match.group(0).replace('bot', '').strip() if bot_match else "❓"
            if bot_val != "❓" and not bot_val.endswith('%'):
                 bot_val += "%"
            bot_emoji = get_emoji(bot_val)

            attr_match = re.search(r"IP属性\s*\n\s*(.+)", text)
            if not attr_match:
                 attr_match = re.search(r"IP属性\s*(.+)", text)
            
            ip_attr = "❓"
            if attr_match:
                raw_attr = attr_match.group(1).strip()
                ip_attr = re.sub(r"IP$", "", raw_attr)

            src_match = re.search(r"IP来源\s*\n\s*(.+)", text)
            if not src_match:
                 src_match = re.search(r"IP来源\s*(.+)", text)
            
            ip_src = "❓"
            if src_match:
                raw_src = src_match.group(1).strip()
                ip_src = re.sub(r"IP$", "", raw_src)
            
            result['status'] = 'success'
            result['pure_score'] = pure_score
            result['bot_ratio'] = bot_val
            result['ip_attr'] = ip_attr
            result['ip_src'] = ip_src
            result['summary'] = f"【{pure_emoji}{bot_emoji} {ip_attr} {ip_src}】"
            
        except Exception as e:
            result['status'] = f'error: {str(e)[:50]}'
        finally:
            await browser.close()
        
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
