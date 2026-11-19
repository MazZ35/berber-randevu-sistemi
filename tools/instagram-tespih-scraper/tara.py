"""Ucretsiz tarama: kendi Edge/Chrome tarayiciniz uzerinden, Instagram sayfalarini gercekten acarak.
Kullanim:  py tara.py tespih "kehribar tespih" "oltu tespih"
- Acilan pencerede giris yapin, ana sayfayi gorunce terminalde ENTER'a basin.
- Program arama sayfalarini acip kaydirir, sayfanin yukledigi verilerden profilleri toplar,
  sonra her profili acip bio/iletisim bilgisini alir. Her adim ekrana yazilir.
- Sonuclar kuyruk.json'a yazilir; uygulamada "Tarama sonuclarini yukle" ile kontrol edersiniz.
"""
import functools
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

print = functools.partial(print, flush=True)

from playwright.sync_api import sync_playwright

LIMIT = 100           # kelime basina hedef profil sayisi (--limit=N ile degisir)
SCROLL = 4            # arama sayfasinda kac kez asagi kaydirilsin
OUT = Path("kuyruk.json")
DURUM = Path("durum.json")   # kaldigi yerden devam icin
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


def main(terms, links=()):
    # uzun kelimeler once: "kehribar tespih" "tespih"ten once taranir
    terms = sorted(dict.fromkeys(terms), key=len, reverse=True)
    print(f"Kelime sirasi: {terms}  |  kelime basina hedef: {LIMIT} profil")
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
        if "--panel" in sys.argv:
            print(">>> Giris bekleniyor (kod isterse pencerede girin)...", flush=True)
            ok = 0
            for _ in range(600):
                logged = any(c["name"] == "sessionid" for c in ctx.cookies("https://www.instagram.com"))
                u = page.url
                ok = ok + 1 if logged and not any(x in u for x in ("challenge", "accounts/", "two_factor", "auth_platform")) else 0
                if ok >= 5:
                    break
                time.sleep(1)
            else:
                sys.exit("10 dakika icinde giris tamamlanmadi.")
        else:
            input(">>> Instagram ANA SAYFASINI (akisi) gorunce buraya donup ENTER'a basin... ")
        print("Giris tamam.\n")

        me = set()
        try:
            me = {c["value"] for c in ctx.cookies("https://www.instagram.com") if c["name"] == "ds_user_id"}
        except Exception:
            pass
        durum = {"found": [], "bing_done": [], "sayac": {}, "terim_done": []}
        if "--sifirla" in sys.argv:
            for f in (DURUM, OUT):
                f.unlink(missing_ok=True)
            print("Onceki tarama silindi, bastan basliyor.")
        elif DURUM.exists():
            durum.update(json.loads(DURUM.read_text("utf-8")))
            print(f"KALDIGI YERDEN DEVAM: {len(durum['found'])} profil daha once bulunmustu, "
                  f"{len(durum['bing_done'])} Bing sayfasi atlanacak.")

        def kaydet():
            DURUM.write_text(json.dumps(durum, ensure_ascii=False), "utf-8")

        found = durum["found"]
        bad = SKIP | {"popular", "about", "legal", "web", "developer", "explore", "tags", "locations", "tv", "api", "static", "accounts", "privacy", "terms", "help"}

        def ekle(us, kaynak):
            n = 0
            for u in us:
                if u and u not in found and u not in bad:
                    found.append(u); n += 1
                    print(f"   + https://www.instagram.com/{u}/   ({kaynak})")
            return n

        def capture(action):
            """action() sirasinda gelen JSON'lardaki kullanicilari dondurur."""
            local: dict = {}
            def h(resp):
                try:
                    if "json" in (resp.headers.get("content-type") or ""):
                        walk(resp.json(), local)
                except Exception:
                    pass
            page.on("response", h)
            try:
                action()
            finally:
                page.remove_listener("response", h)
            for u, d in local.items():
                if len(d) > len(seen.get(u, {})):
                    seen[u] = d
            return local

        for u in links:
            if u not in found:
                found.append(u); print(f"   + https://www.instagram.com/{u}/   (dogrudan link)")

        # 0) Arama motorlari: bio'sunda kelime gecen Instagram profilleri
        #    Bing hata verirse DuckDuckGo, o da olmazsa Google denenir.
        import re as _re
        MOTORLAR = {
            "bing": lambda q, s: f"https://www.bing.com/search?q={quote(q)}&first={s * 10 + 1}&setlang=tr",
            "duckduckgo": lambda q, s: f"https://html.duckduckgo.com/html/?q={quote(q)}&s={s * 30}&kl=tr-tr",
            "google": lambda q, s: f"https://www.google.com/search?q={quote(q)}&start={s * 10}&hl=tr",
        }
        hata_say = {m: 0 for m in MOTORLAR}
        sayac = durum["sayac"]

        def motor_ara(q, sayfa):
            """Calisan ilk motorla arar; (kullanici listesi, kullanilan url) dondurur."""
            for m, f in MOTORLAR.items():
                if hata_say[m] >= 3:
                    continue
                url = f(q, sayfa)
                if url in durum["bing_done"]:
                    return None, url
                print(f"[{m}] {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000); bekle(3, 6)
                    html = page.content()
                    if any(x in html.lower() for x in ("captcha", "unusual traffic", "olağandışı trafik")):
                        print(f"   {m} robot dogrulamasi istiyor - Edge penceresinde dogrulayin (60 sn bekleniyor)")
                        time.sleep(60); html = page.content()
                    hata_say[m] = 0
                    us = []
                    for u in _re.findall(r"instagram\.com(?:%2F|/)([A-Za-z0-9_.]{2,30})", html):
                        u = u.strip(".").lower()
                        if u not in us:
                            us.append(u)
                    return us, url
                except Exception as e:
                    hata_say[m] += 1
                    print(f"   {m} hata: {str(e)[:90]}")
                    if hata_say[m] >= 3:
                        print(f"   !!! {m} 3 kez hata verdi, artik kullanilmayacak.")
            return [], None

        for t in terms:
            sayac.setdefault(t, 0)
            for ek in ("", " whatsapp", " iletişim", " telefon", " sipariş"):
                if sayac[t] >= LIMIT or all(v >= 3 for v in hata_say.values()):
                    break
                q = f'site:instagram.com "{t}"{ek}'
                bos = 0
                for sayfa in range(15):
                    if sayac[t] >= LIMIT:
                        break
                    us, url = motor_ara(q, sayfa)
                    if us is None:
                        continue
                    if url is None:
                        break
                    n = ekle(us, f"arama: {t}")
                    sayac[t] += n
                    durum["bing_done"].append(url); kaydet()
                    print(f"   ({n} yeni profil | '{t}' toplam: {sayac[t]}/{LIMIT} | genel: {len(found)})")
                    bos = bos + 1 if n == 0 else 0
                    if bos >= 2:
                        break
        if all(v >= 3 for v in hata_say.values()):
            print("!!! Hicbir arama motoruna baglanilamadi. Internet/VPN/antivirus baglantiyi kesiyor olabilir.")
        print(f"\n== Arama motorlari bitti: {len(found)} profil listede. Simdi Instagram aramasi, sonra profiller tek tek okunacak. ==\n")

        for t in terms:
            if t in durum["terim_done"]:
                continue
            # 1) Arama kutusu (hesap sonuclari)
            print(f"[arama kutusu] '{t}'")
            def ara():
                page.goto("https://www.instagram.com/", wait_until="domcontentloaded"); bekle(3, 5)
                for name in ("Search", "Ara"):
                    loc = page.get_by_role("link", name=name)
                    if loc.count():
                        loc.first.click(); break
                bekle(1, 2)
                box = page.locator("input[placeholder='Search'], input[placeholder='Ara'], input[aria-label*='Search'], input[aria-label*='Ara']")
                box.first.fill(t)
                bekle(4, 6)
            try:
                res = capture(ara)
                users = [u for u, d in res.items() if "full_name" in d or "is_verified" in d]
                print(f"   ({ekle(users, 'arama')} yeni profil)")
            except Exception as e:
                print(f"   arama kutusu kullanilamadi: {str(e)[:100]}")

            # 2) Anahtar kelime sayfasindaki gonderiler -> sahipleri
            url = f"https://www.instagram.com/explore/search/keyword/?q={quote(t)}"
            print(f"[sayfa] {url}")
            posts = []
            try:
                page.goto(url, wait_until="domcontentloaded"); bekle()
                for _ in range(SCROLL):
                    page.mouse.wheel(0, 4000); bekle(2, 4)
                for href in page.eval_on_selector_all("a[href*='/p/'], a[href*='/reel/']",
                                                      "els => els.map(e => e.getAttribute('href'))"):
                    if href not in posts:
                        posts.append(href)
            except Exception as e:
                print(f"   hata: {str(e)[:100]}")
            print(f"   {len(posts)} gonderi bulundu, sahipleri aliniyor...")
            n = 0
            for href in posts[:LIMIT]:
                parts = [x for x in href.split("/") if x]
                owner = parts[0] if parts[0] not in ("p", "reel") else None   # /kullanici/p/KOD/ bicimi
                code = parts[parts.index("p" if "p" in parts else "reel") + 1]
                if not owner:
                    try:
                        local = capture(lambda: (page.goto("https://www.instagram.com" + href,
                                                           wait_until="domcontentloaded"), bekle(2, 4)))
                        cands = [u for u, d in local.items() if u not in me]
                        # once gonderinin kendi sahibini bul
                        og = page.eval_on_selector("meta[property='og:url']", "e => e.content") or ""
                        ogp = [x for x in og.replace("https://www.instagram.com/", "").split("/") if x]
                        if ogp and ogp[0] not in ("p", "reel"):
                            owner = ogp[0]
                        else:
                            desc = page.eval_on_selector("meta[property='og:title']", "e => e.content") or ""
                            owner = next((u for u in cands if u in desc), None) or (cands[0] if cands else None)
                    except Exception as e:
                        print(f"   {code}: {str(e)[:80]}")
                if owner:
                    n += ekle([owner], f"gonderi {code}")
            print(f"   ({n} yeni profil)")
            durum["terim_done"].append(t); kaydet()

        print(f"\nToplam {len(found)} profil. Profiller tek tek aciliyor...\n")
        old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
        have = {p["username"] for p in old}
        for u in found:
            if u in have:
                continue
            url = f"https://www.instagram.com/{u}/"
            print(f"[profil] {url}")
            try:
                local = capture(lambda: (page.goto(url, wait_until="domcontentloaded"), bekle()))
                p = dict(seen.get(u, {}))
                if len(local.get(u, {})) > len(p):
                    p = dict(local[u])
                # bio'daki "devamı / more" yazisina tikla
                for t in ("devamı", "more", "daha fazla"):
                    try:
                        loc = page.locator("header").get_by_text(t, exact=True)
                        if loc.count():
                            loc.first.click(timeout=2000); bekle(1, 2); break
                    except Exception:
                        pass
                header = page.inner_text("header") if page.query_selector("header") else ""
                linkler = []

                def topla_linkler(scope):
                    for h in page.eval_on_selector_all(scope + " a[href]", "els => els.map(e => e.href)"):
                        if "l.instagram.com" in h and "u=" in h:
                            from urllib.parse import parse_qs, urlparse, unquote
                            h = unquote(parse_qs(urlparse(h).query).get("u", [h])[0])
                        if "instagram.com" not in h and h not in linkler:
                            linkler.append(h)

                topla_linkler("header")
                # "ve 1 diger / and 1 more" -> Baglantilar penceresi
                try:
                    btn = page.locator("header").get_by_text(re.compile(r"(ve \d+ diğer|and \d+ more)"))
                    if btn.count():
                        btn.first.click(timeout=3000); bekle(1, 2)
                        dlg = "div[role='dialog']"
                        if page.query_selector(dlg):
                            topla_linkler(dlg)
                            header += "\n" + page.inner_text(dlg)
                            page.keyboard.press("Escape")
                except Exception as e:
                    print(f"   baglantilar acilamadi: {str(e)[:80]}")
                for bl in p.get("bio_links") or []:
                    if isinstance(bl, dict) and bl.get("url") and bl["url"] not in linkler:
                        linkler.append(bl["url"])
                bio = p.get("biography") or ""
                p["biography"] = (bio + "\n" + header).strip() if header not in bio else bio
                if linkler:
                    p["external_url"] = " ".join(linkler)
                    print(f"   linkler: {linkler}")
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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    import re as _r
    links = [_r.search(r"instagram\.com/([A-Za-z0-9_.]+)", a).group(1) if "instagram.com/" in a else a[1:]
             for a in args if "instagram.com/" in a or a.startswith("@")]
    terms = [a for a in args if not ("instagram.com/" in a or a.startswith("@"))]
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            LIMIT = int(a.split("=")[1])
    main(terms, links)
