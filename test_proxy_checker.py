import asyncio
import unittest

from generate_proxy_list import ProxyScraper
from ipcheck import Config, ProxyChecker, ProxyParser, ProxyInfo, ProxyCheckResult


class TestProxyParser(unittest.TestCase):
    def test_parse_valid_proxy_and_credentials(self):
        proxy = ProxyParser.parse_line("HTTP://user%20name:p%40ss@1.2.3.4:8080 [test]")
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "http")
        self.assertEqual(proxy.username, "user name")
        self.assertEqual(proxy.password, "p@ss")
        self.assertEqual(proxy.location_hint, "test")

    def test_reject_invalid_ip_and_port(self):
        self.assertIsNone(ProxyParser.parse_line("http://999.2.3.4:8080"))
        self.assertIsNone(ProxyParser.parse_line("http://1.2.3.4:65536"))


class TestProxyChecker(unittest.TestCase):
    def test_proxy_url_contains_encoded_credentials(self):
        checker = ProxyChecker()
        _, url = checker._get_proxy_connector(
            ProxyInfo("", protocol="http", ip="1.2.3.4", port="8080", username="a b", password="p@ss")
        )
        self.assertEqual(url, "http://a%20b:p%40ss@1.2.3.4:8080")

    def test_check_all_runs_concurrently_and_preserves_order(self):
        class FastConfig(Config):
            MAX_CONCURRENT = 2
            REQUEST_DELAY = 0

        async def scenario():
            checker = ProxyChecker(FastConfig())
            active = 0
            peak = 0

            async def fake_check(proxy):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.01)
                active -= 1
                return ProxyCheckResult(proxy=proxy, status="success")

            checker.check_single = fake_check
            proxies = [ProxyInfo(str(i), ip=f"1.2.3.{i}", port="80") for i in range(1, 5)]
            results = await checker.check_all(proxies)
            return results, peak

        results, peak = asyncio.run(scenario())
        self.assertGreaterEqual(peak, 2)
        self.assertEqual([r.proxy.original_line for r in results], ["1", "2", "3", "4"])


class TestProxyScraper(unittest.TestCase):
    def test_parse_table_deduplicates_entries(self):
        html = """
        <table><tr><th>Protocol</th><th>IP</th><th>Port</th></tr>
        <tr><td>http</td><td>1.2.3.4</td><td>80</td></tr>
        <tr><td>http</td><td>1.2.3.4</td><td>80</td></tr>
        <tr><td>socks5</td><td>5.6.7.8</td><td>1080</td></tr></table>
        """
        scraper = ProxyScraper()
        entries = scraper._parse_table(html)
        self.assertEqual([(e.protocol, e.ip, e.port) for e in entries], [
            ("http", "1.2.3.4", "80"), ("socks5", "5.6.7.8", "1080")
        ])


if __name__ == "__main__":
    unittest.main()
