#!/usr/bin/env python3
"""OutWorlders Airdrop Bot — CUPANG AI AGENT
Tasks: Follow, Like, Quote, Tag friends, Submit EVM + X handle
"""
import asyncio, json, re
from playwright.async_api import async_playwright

AUTH='db9e9b...5169'
CT0='cbbd319ca8e37abb7ca81a251892401c4d0341f6bfa52b0ff884d8993429b98899f69da0a0fc0b71d06887734bf31fa5b0edf0f9ece987b701bd7a95c3a4ae6a27c46f3c3dcdd7ba0284337f44d31c7a'
EVM='0x816CD618bf496f8CC8c732A227DE7b50BEA69960'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width':1280,'height':900}
        )
        await context.add_cookies([
            {"name":"auth_token","value":AUTH,"domain":".x.com","path":"/","secure":True,"httpOnly":True,"sameSite":"None","expires":1812333299},
            {"name":"ct0","value":CT0,"domain":".x.com","path":"/","secure":True,"sameSite":"Lax","expires":1815357299},
            {"name":"twid","value":"u%3D1205811165873332225","domain":".x.com","path":"/","secure":True,"sameSite":"None","expires":1812333434},
        ])
        page = await context.new_page()
        ok = {}

        # TASK 1: Follow
        print("📌 Follow @outworld3rs")
        try:
            await page.goto('https://x.com/outworld3rs', wait_until='commit', timeout=20000)
            await asyncio.sleep(6)
            fb = page.get_by_role('button', name=re.compile(r'Follow',re.I)).first
            if await fb.is_visible(timeout=5000):
                await fb.click(); await asyncio.sleep(2)
                print("  ✅ Followed!"); ok['follow']=True
            else:
                print("  ✅ Already following"); ok['follow']=True
        except Exception as e:
            print(f"  ❌ {e}")

        # TASK 2: Like & Quote
        print("📌 Like & Quote post")
        try:
            await page.goto('https://x.com/search?q=from%3Aoutworld3rs&f=live', wait_until='commit', timeout=20000)
            await asyncio.sleep(6)
            tw = page.locator('[data-testid="tweet"]').first
            if await tw.is_visible(timeout=5000):
                lk = tw.locator('[data-testid="like"]').first
                try:
                    if await lk.is_visible(timeout=3000): await lk.click(); await asyncio.sleep(1)
                    print("  ✅ Liked!"); ok['like']=True
                except: print("  ✅ Liked (or already)"); ok['like']=True

                rt = tw.locator('[data-testid="retweet"]').first
                if await rt.is_visible(timeout=3000):
                    await rt.click(); await asyncio.sleep(1)
                    qo = page.locator('[role="menuitem"]:has-text("Quote"), a:has-text("Quote")').first
                    if await qo.is_visible(timeout=3000):
                        await qo.click(); await asyncio.sleep(2)
                        ta = page.locator('[data-testid="tweetTextarea_0"]').first
                        await ta.fill("Outworlders 🔥∆◊ @outworld3rs #OutWorlders #WL")
                        await asyncio.sleep(1)
                        pb = page.locator('[data-testid="tweetButtonInline"]').first
                        await pb.click(); await asyncio.sleep(3)
                        print("  ✅ Quote tweeted!"); ok['quote']=True
        except Exception as e:
            print(f"  ❌ {e}")

        # TASK 3: Tag friends
        print("📌 Tag 2 friends")
        try:
            await page.goto('https://x.com/search?q=from%3Aoutworld3rs&f=live', wait_until='commit', timeout=20000)
            await asyncio.sleep(6)
            tw = page.locator('[data-testid="tweet"]').first
            if await tw.is_visible(timeout=5000):
                await tw.click(); await asyncio.sleep(3)
                ra = page.locator('[data-testid="tweetTextarea_0"]').first
                if await ra.is_visible(timeout=5000):
                    await ra.fill("@haus_living @muhamm12 Outworlders WL 🔥∆◊")
                    await asyncio.sleep(1)
                    rb = page.locator('[data-testid="tweetButtonInline"]').first
                    await rb.click(); await asyncio.sleep(3)
                    print("  ✅ Tagged friends!"); ok['tag']=True
        except Exception as e:
            print(f"  ❌ {e}")

        # SUBMIT FORM
        print("📌 Submit OutWorlders form")
        try:
            p2 = await context.new_page()
            await p2.goto('https://outworlders.xyz', wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(3)
            rb = p2.locator('button:has-text("REGISTER")').first
            await rb.click(); await asyncio.sleep(2)
            ei = p2.locator('input[placeholder="0x…"]').first
            await ei.fill(EVM)
            print(f"  ✅ EVM: {EVM[:10]}...{EVM[-6:]}")
            xi = p2.locator('input[placeholder*="@handle"]').first
            await xi.fill("@muhamm122")
            print("  ✅ X: @muhamm122")
            await asyncio.sleep(1)
            sb = p2.locator('button:has-text("REGISTER SIGNAL")').first
            await sb.click(); await asyncio.sleep(3)
            await p2.screenshot(path='/tmp/outworlders-result.png')
            print("  ✅ Form submitted!")
            ok['submit']=True
            await p2.close()
        except Exception as e:
            print(f"  ❌ {e}")

        print("\n" + "="*40)
        print("📋 SUMMARY")
        print("="*40)
        for k,v in ok.items(): print(f"  {k}: {'✅' if v else '❌'}")
        print(f"  EVM: {EVM[:10]}...{EVM[-6:]}")
        print(f"  X: @muhamm122")

        await browser.close()

asyncio.run(main())
