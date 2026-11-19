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


def search_users(L, terms: list[str], limit_per_term: int = 30, hashtags: bool = True, log=print) -> list[str]:
    seen, out = set(), []

    def add(u):
        if u and u not in seen:
            seen.add(u); out.append(u)

    for t in terms:
        try:
            for i, p in enumerate(instaloader.TopSearchResults(L.context, t).get_profiles()):
                if i >= limit_per_term:
                    break
                add(p.username)
        except Exception as e:
            log(f"Arama hatasi ({t}): {e}")
        _pause()
        if hashtags:
            tag = t.replace(" ", "").lower()
            try:
                for i, post in enumerate(instaloader.Hashtag.from_name(L.context, tag).get_posts_resumable()):
                    if i >= limit_per_term:
                        break
                    add(post.owner_username)
                    if i % 10 == 9:
                        _pause(2, 5)
            except Exception as e:
                log(f"#{tag} hatasi: {e}")
            _pause()
    return out


def profile_details(L, usernames: list[str], log=print) -> list[dict]:
    res = []
    for u in usernames:
        try:
            p = instaloader.Profile.from_username(L.context, u)
            n = p._node
            addr = n.get("business_address_json") or {}
            if isinstance(addr, str):
                try:
                    addr = json.loads(addr)
                except ValueError:
                    addr = {"street_address": addr}
            res.append({
                "username": p.username, "fullName": p.full_name, "followersCount": p.followers,
                "businessCategoryName": p.business_category_name or "", "biography": p.biography,
                "externalUrl": p.external_url or "",
                "businessPhoneNumber": n.get("business_phone_number") or "",
                "businessEmail": n.get("business_email") or "",
                "businessAddress": addr,
            })
        except Exception as e:
            log(f"{u}: {e}")
        _pause()
    return res
