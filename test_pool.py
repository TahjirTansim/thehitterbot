# -*- coding: utf-8 -*-
import asyncio, aiohttp, json, sys

TEST_CARD = "4111111111111111|12|2026|128"
TEST_SITE = "https://yarnfun.myshopify.com"
RAILWAY = "https://web-production-0919d.up.railway.app/shopify"

async def test(proxy):
    url = f"{RAILWAY}?site={TEST_SITE}&cc={TEST_CARD}&proxy={proxy}"
    try:
        timeout = aiohttp.ClientTimeout(total=45)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return proxy, "HTTP" + str(r.status)
                body = await r.text()
                try:
                    data = json.loads(body)
                except Exception:
                    return proxy, "BADJSON"
                response = str(data.get("Response", "")).upper()
                proxy_field = str(data.get("Proxy", "")).strip()
                if response in ("CONNECTION_ERROR", "TIMEOUT", "PROXY_ERROR", ""):
                    return proxy, response or "EMPTY"
                if "ERROR" in response or "ERROR" in proxy_field:
                    return proxy, response
                return proxy, "OK:" + response
    except asyncio.TimeoutError:
        return proxy, "TIMEOUT"
    except Exception as e:
        return proxy, type(e).__name__

async def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/root/thehitterbot/live_proxies (2).txt"
    proxies = [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]
    print("Testing " + str(len(proxies)) + " proxies from " + path)
    print("Saved to /root/thehitterbot/proxy_good.txt")
    print()

    ok = []
    bad = []

    BATCH = 20
    for i in range(0, len(proxies), BATCH):
        batch = proxies[i:i+BATCH]
        results = await asyncio.gather(*[test(p) for p in batch])
        for p, status in results:
            if status.startswith("OK:"):
                ok.append(p)
            else:
                bad.append((p, status))
        print("  Tested " + str(min(i+BATCH, len(proxies))) + "/" + str(len(proxies)) + " - ok: " + str(len(ok)) + ", bad: " + str(len(bad)))

    with open("/root/thehitterbot/proxy_good.txt", "w") as f:
        for p in ok:
            f.write(p + "\n")

    print()
    print("===========================================")
    print("  WORKING:  " + str(len(ok)))
    print("  DEAD:     " + str(len(bad)))
    print("  Saved:    /root/thehitterbot/proxy_good.txt")
    print("===========================================")

asyncio.run(main())
