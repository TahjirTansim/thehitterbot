# -*- coding: utf-8 -*-
"""
Fetch unique image URLs from nekos.best and save to gc_banners.txt
"""
import asyncio, aiohttp

TARGET = 1000

async def fetch_one(session):
    try:
        async with session.get("https://nekos.best/api/v2/neko") as r:
            if r.status != 200:
                return None
            data = await r.json()
            return data['results'][0]['url']
    except Exception:
        return None

async def main():
    urls = set()
    fails = 0
    async with aiohttp.ClientSession() as session:
        while len(urls) < TARGET and fails < 50:
            u = await fetch_one(session)
            if u:
                urls.add(u)
                fails = 0
                if len(urls) % 50 == 0:
                    print(f"[{len(urls)}/{TARGET}] collected")
            else:
                fails += 1
            await asyncio.sleep(0.3)

    with open('/root/thehitterbot/gc_banners.txt', 'w') as f:
        for u in sorted(urls):
            f.write(u + '\n')

    print()
    print(f"Total: {len(urls)} URLs saved to /root/thehitterbot/gc_banners.txt")

asyncio.run(main())
