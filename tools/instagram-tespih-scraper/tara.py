"""Ucretsiz tarama: kendi Edge/Chrome tarayiciniz uzerinden, Instagram sayfalarini gercekten acarak.
Kullanim:  py tara.py tespih "kehribar tespih" "oltu tespih"
- Acilan pencerede giris yapin, ana sayfayi gorunce terminalde ENTER'a basin.
- Program arama sayfalarini acip kaydirir, sayfanin yukledigi verilerden profilleri toplar,
  sonra her profili acip bio/iletisim bilgisini alir. Her adim ekrana yazilir.
- Sonuclar kuyruk.json'a yazilir; uygulamada "Tarama sonuclarini yukle" ile kontrol edersiniz.
"""
import json
import random
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

LIMIT = 20            # kelime basina max profil
SCROLL = 4            # arama sayfasinda kac kez asagi kaydirilsin
OUT = Path("kuyruk.json")
SKIP = {"instagram", "explore", "accounts", "p", "reel", "reels", "stories", "direct"}


def bekle(a=3, b=7):
    time.sleep(random.uniform(a, b))


def walk(obj, users: dict):
    """JSON icindeki tum kullanici nesnelerini toplar (username -> en zengin dict)."""
    if isinstance(obj, dict):
        u = obj.get("username")
        if isinstance(u, str) and u:
            prev = users.get(u, {})
            if len(obj) > len(prev):
                users[u] = obj
        for v in obj.values():
            walk(v, users)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, users)


def to_record(p: dict, u: str) -> dict:
    addr = p.get("business_address_json") or {}
    if isinstance(addr, str):
        try:
            addr = json.loads(addr)
        except ValueError:
            addr = {"street_address": addr}
    fol = p.get("follower_count") or (p.get("edge_followed_by") or {}).get("count", "")
    return {
        "username": u, "fullName": p.get("full_name", ""), "followersCount": fol,
        "businessCategoryName": p.get("business_category_name") or p.get("category") or p.get("category_name") or "",
        "biography": p.get("biography", ""),
        "externalUrl": p.get("external_url") or "",
        "businessPhoneNumber": p.get("business_phone_number") or p.get("public_phone_number")
                               or p.get("contact_phone_number") or "",
        "businessEmail": p.get("business_email") or p.get("public_email") or "",
        "businessAddress": addr or {"street_address": p.get("address_street", ""),
                                    "city_name": p.get("city_name", "")},
    }


def main(terms):
    seen: dict = {}

    def on_response(resp):
        try:
            if "json" in (resp.headers.get("content-type") or ""):
                walk(resp.json(), seen)
        except Exception:
            pass

    with sync_playwright() as pw:
        try:
            ctx = pw.chromium.launch_persistent_context("ig_tarayici_profili", channel="msedge", headless=False)
        except Exception:
            ctx = pw.chromium.launch_persistent_context("ig_tarayici_profili", channel="chrome", headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_response)
        page.goto("https://www.instagram.com/")
        print("Instagram acildi. Acilan pencerede giris yapin; kod/dogrulama isterse tamamlayin.")
        input(">>> Instagram ANA SAYFASINI (akisi) gorunce buraya donup ENTER'a basin... ")
        print("Giris tamam.\n")

        found = []
        for t in terms:
            for url in (f"https://www.instagram.com/explore/search/keyword/?q={quote(t)}",
                        f"https://www.instagram.com/explore/search/keyword/?q={quote('#' + t.replace(' ', ''))}"):
                before = set(seen)
                print(f"[sayfa] {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    bekle()
                    for _ in range(SCROLL):
                        page.mouse.wheel(0, 4000); bekle(2, 4)
                    # sayfadaki profil linkleri de (JSON gelmezse yedek)
                    for href in page.eval_on_selector_all("a[href^='/']", "els => els.map(e => e.getAttribute('href'))"):
                        parts = [x for x in href.split("/") if x]
                        if len(parts) == 1 and parts[0] not in SKIP:
                            seen.setdefault(parts[0], {"username": parts[0]})
                except Exception as e:
                    print(f"   hata: {e}")
                new = [u for u in seen if u not in before and u not in found][:LIMIT]
                for u in new:
                    found.append(u)
                    print(f"   + https://www.instagram.com/{u}/")
                print(f"   ({len(new)} yeni profil)")

        print(f"\nToplam {len(found)} profil. Profiller tek tek aciliyor...\n")
        old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
        have = {p["username"] for p in old}
        for u in found:
            if u in have:
                continue
            url = f"https://www.instagram.com/{u}/"
            print(f"[profil] {url}")
            try:
                page.goto(url, wait_until="domcontentloaded")
                bekle()
                p = seen.get(u, {})
                if "biography" not in p:  # JSON'da yoksa sayfadan oku
                    desc = page.eval_on_selector("meta[name='description']", "e => e.content") or ""
                    body = page.inner_text("header") if page.query_selector("header") else ""
                    p = {**p, "biography": body or desc}
                rec = to_record(p, u)
                old.append(rec)
                OUT.write_text(json.dumps(old, ensure_ascii=False, indent=1), "utf-8")
                print(f"   bio: {rec['biography'][:90]!r}")
                if rec["businessPhoneNumber"]:
                    print(f"   tel: {rec['businessPhoneNumber']}")
            except Exception as e:
                print(f"   hata: {e}")
            bekle()
        ctx.close()
        print(f"\nBitti. {OUT} dosyasinda {len(old)} profil var. Uygulamada 'Tarama sonuclarini yukle' deyin.")


if __name__ == "__main__":
    main(sys.argv[1:] or ["tespih"])
