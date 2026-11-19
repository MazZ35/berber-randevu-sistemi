"""Apify uzerinden Instagram arama + profil detaylari (resmi olmayan ama hesap riski olmayan yontem)."""
import requests

BASE = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


def _run(token: str, actor: str, payload: dict, timeout: int = 600) -> list:
    r = requests.post(BASE.format(actor=actor), params={"token": token}, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def search_users(token: str, terms: list[str], limit_per_term: int = 30) -> list[str]:
    items = _run(token, "apify~instagram-search-scraper",
                 {"search": ",".join(terms), "searchType": "user", "searchLimit": limit_per_term})
    seen, out = set(), []
    for it in items:
        u = it.get("username")
        if u and u not in seen:
            seen.add(u); out.append(u)
    return out


def profile_details(token: str, usernames: list[str]) -> list[dict]:
    return _run(token, "apify~instagram-profile-scraper", {"usernames": usernames})


def flatten(p: dict) -> dict:
    """Farkli actor surumlerindeki alan adlarini tek formata indirger."""
    addr = p.get("businessAddress") or {}
    if isinstance(addr, str):
        addr = {"street_address": addr}
    return {
        "kullanici_adi": p.get("username", ""),
        "ad": p.get("fullName", ""),
        "takipci": p.get("followersCount", ""),
        "kategori": p.get("businessCategoryName", ""),
        "bio": p.get("biography", ""),
        "web": p.get("externalUrl", "") or "",
        "is_telefon": p.get("businessPhoneNumber") or p.get("publicPhoneNumber") or "",
        "is_email": p.get("businessEmail") or p.get("publicEmail") or "",
        "is_adres": " ".join(str(v) for v in [addr.get("street_address"), addr.get("zip_code"), addr.get("city_name")] if v),
        "profil_url": f"https://www.instagram.com/{p.get('username', '')}/",
    }
