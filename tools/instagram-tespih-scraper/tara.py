"""Ucretsiz tarama: kendi Edge/Chrome tarayiciniz uzerinden.
Kullanim:  py tara.py tespih "kehribar tespih" "oltu tespih"
- Ilk calistirmada acilan pencerede Instagram'a giris yapin (bir kez; sonra hatirlanir).
- Her istek ve bulunan her profil linki ekrana yazilir.
- Sonuclar kuyruk.json dosyasina yazilir; uygulamada "Tarama sonuclarini yukle" ile kontrol edersiniz.
"""
import json
import random
import sys
import time
from urllib.parse import quote
from pathlib import Path

from playwright.sync_api import sync_playwright

LIMIT = 20          # kelime basina max profil
OUT = Path("kuyruk.json")

HDR = {"X-IG-App-ID": "936619743392459", "X-Requested-With": "XMLHttpRequest",
       "Referer": "https://www.instagram.com/"}


def bekle(a=4, b=9):
    time.sleep(random.uniform(a, b))


def usernames_in(obj, out):
    if isinstance(obj, dict):
        for k in ("owner", "user"):
            v = obj.get(k)
            if isinstance(v, dict) and v.get("username"):
                out.append(v["username"])
        for v in obj.values():
            usernames_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            usernames_in(v, out)


def main(terms):
    with sync_playwright() as pw:
        try:
            ctx = pw.chromium.launch_persistent_context("ig_tarayici_profili", channel="msedge", headless=False)
        except Exception:
            ctx = pw.chromium.launch_persistent_context("ig_tarayici_profili", channel="chrome", headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.instagram.com/")
        print("Instagram acildi. Giris yapili degilse acilan pencerede giris yapin...")
        for _ in range(300):
            if any(c["name"] == "sessionid" for c in ctx.cookies("https://www.instagram.com")):
                break
            time.sleep(1)
        else:
            sys.exit("5 dakika icinde giris yapilmadi.")
        print("Giris tamam.\n")
        time.sleep(5)  # giris sonrasi yonlendirmeler bitsin

        def api(path):
            url = "https://www.instagram.com/api/v1/" + path
            for deneme in range(3):
                try:
                    r = ctx.request.get(url, headers=HDR, timeout=30000)
                    break
                except Exception as e:
                    print(f"[hata] {url}: {e}"); time.sleep(5)
            else:
                return None
            print(f"[{r.status}] {r.url}")
            if r.status != 200:
                return None
            try:
                return r.json()
            except Exception:
                print("   (JSON degil - Instagram giris sayfasina yonlendirmis olabilir)")
                return None

        users = []
        def add(lst):
            n = 0
            for u in lst:
                if u not in users and n < LIMIT:
                    users.append(u); n += 1
                    print(f"   + https://www.instagram.com/{u}/")
            return n

        for t in terms:
            d = api(f"web/search/topsearch/?context=blended&query={quote(t)}")
            if d:
                add([x["user"]["username"] for x in d.get("users", [])])
            bekle()
            tag = t.replace(" ", "").lower()
            d = api(f"tags/web_info/?tag_name={tag}")
            if d:
                found = []; usernames_in(d, found); add(found)
            bekle()

        print(f"\nToplam {len(users)} profil bulundu. Detaylar cekiliyor...\n")
        old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
        have = {p["username"] for p in old}
        for u in users:
            if u in have:
                continue
            d = api(f"users/web_profile_info/?username={u}")
            if d:
                p = d["data"]["user"]
                addr = p.get("business_address_json") or {}
                if isinstance(addr, str):
                    try: addr = json.loads(addr)
                    except ValueError: addr = {"street_address": addr}
                old.append({
                    "username": p.get("username", u), "fullName": p.get("full_name", ""),
                    "followersCount": (p.get("edge_followed_by") or {}).get("count", ""),
                    "businessCategoryName": p.get("business_category_name") or p.get("category_name") or "",
                    "biography": p.get("biography", ""), "externalUrl": p.get("external_url") or "",
                    "businessPhoneNumber": p.get("business_phone_number") or "",
                    "businessEmail": p.get("business_email") or "", "businessAddress": addr,
                })
                OUT.write_text(json.dumps(old, ensure_ascii=False, indent=1), "utf-8")
                print(f"   bio: {p.get('biography','')[:80]!r}")
            bekle()
        ctx.close()
        print(f"\nBitti. {OUT} dosyasinda {len(old)} profil var. Uygulamada 'Tarama sonuclarini yukle' deyin.")


if __name__ == "__main__":
    main(sys.argv[1:] or ["tespih"])
