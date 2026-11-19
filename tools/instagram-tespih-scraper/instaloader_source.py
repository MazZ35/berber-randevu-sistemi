"""Ucretsiz kaynak: Instaloader + kendi (yedek) Instagram hesabiniz.
Once terminalde bir kez giris yapin:  py -m instaloader --login KULLANICI_ADINIZ
(2 adimli dogrulama sorarsa orada cevaplayin; oturum dosyasi kaydedilir.)
"""
import json
import random
import time

import instaloader


def get_loader(username: str) -> instaloader.Instaloader:
    L = instaloader.Instaloader(download_pictures=False, download_videos=False,
                                download_comments=False, save_metadata=False, quiet=True,
                                max_connection_attempts=1)
    L.load_session_from_file(username)
    return L


def _pause(a=4, b=10):
    time.sleep(random.uniform(a, b))


HDR = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instagram.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}


SCANNED: list[dict] = []  # yapilan her istegin kaydi (arayuzde gosterilir)


def _get(L, path: str, params: dict) -> dict:
    r = L.context._session.get("https://www.instagram.com/api/v1/" + path, params=params,
                               headers=HDR, timeout=30)
    SCANNED.append({"saat": time.strftime("%H:%M:%S"), "durum": r.status_code, "adres": r.url})
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:120]}")
    return r.json()


def _usernames_in(obj, out: list):
    """JSON icindeki tum owner/user.username degerlerini toplar."""
    if isinstance(obj, dict):
        for k in ("owner", "user"):
            v = obj.get(k)
            if isinstance(v, dict) and v.get("username"):
                out.append(v["username"])
        for v in obj.values():
            _usernames_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _usernames_in(v, out)


def search_users(L, terms: list[str], limit_per_term: int = 30, hashtags: bool = True, log=print) -> list[str]:
    seen, out = set(), []

    def add(us):
        n = 0
        for u in us:
            if u and u not in seen:
                seen.add(u); out.append(u); n += 1
            if n >= limit_per_term:
                break
        return n

    for t in terms:
        try:
            d = _get(L, "web/search/topsearch/", {"query": t, "context": "blended"})
            n = add([x["user"]["username"] for x in d.get("users", [])])
            log(f"'{t}' aramasi: {n} profil")
        except Exception as e:
            log(f"Arama hatasi ({t}): {e}")
        _pause()
        if hashtags:
            tag = t.replace(" ", "").lower()
            try:
                found = []
                _usernames_in(_get(L, "tags/web_info/", {"tag_name": tag}), found)
                log(f"#{tag}: {add(found)} profil")
            except Exception as e:
                log(f"#{tag} hatasi: {e}")
            _pause()
    return out


def profile_details(L, usernames: list[str], log=print) -> list[dict]:
    res = []
    for u in usernames:
        try:
            p = _get(L, "users/web_profile_info/", {"username": u})["data"]["user"]
            addr = p.get("business_address_json") or {}
            if isinstance(addr, str):
                try:
                    addr = json.loads(addr)
                except ValueError:
                    addr = {"street_address": addr}
            res.append({
                "username": p.get("username", u), "fullName": p.get("full_name", ""),
                "followersCount": (p.get("edge_followed_by") or {}).get("count", ""),
                "businessCategoryName": p.get("business_category_name") or p.get("category_name") or "",
                "biography": p.get("biography", ""),
                "externalUrl": p.get("external_url") or "",
                "businessPhoneNumber": p.get("business_phone_number") or "",
                "businessEmail": p.get("business_email") or "",
                "businessAddress": addr,
            })
        except Exception as e:
            log(f"{u}: {e}")
        _pause()
    return res
