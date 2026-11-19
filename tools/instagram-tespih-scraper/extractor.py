"""Profil metninden telefon / WhatsApp / il-ilce bilgisi cikarir."""
import re

ILLER = ["Adana","Adıyaman","Afyonkarahisar","Ağrı","Amasya","Ankara","Antalya","Artvin","Aydın","Balıkesir",
"Bilecik","Bingöl","Bitlis","Bolu","Burdur","Bursa","Çanakkale","Çankırı","Çorum","Denizli","Diyarbakır","Edirne",
"Elazığ","Erzincan","Erzurum","Eskişehir","Gaziantep","Giresun","Gümüşhane","Hakkari","Hatay","Isparta","Mersin",
"İstanbul","İzmir","Kars","Kastamonu","Kayseri","Kırklareli","Kırşehir","Kocaeli","Konya","Kütahya","Malatya",
"Manisa","Kahramanmaraş","Mardin","Muğla","Muş","Nevşehir","Niğde","Ordu","Rize","Sakarya","Samsun","Siirt",
"Sinop","Sivas","Tekirdağ","Tokat","Trabzon","Tunceli","Şanlıurfa","Uşak","Van","Yozgat","Zonguldak","Aksaray",
"Bayburt","Karaman","Kırıkkale","Batman","Şırnak","Bartın","Ardahan","Iğdır","Yalova","Karabük","Kilis",
"Osmaniye","Düzce"]

def _norm(s: str) -> str:
    tr = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
    return s.translate(tr).lower()

_IL_NORM = {_norm(i): i for i in ILLER}
_IL_NORM.update({"urfa": "Şanlıurfa", "maras": "Kahramanmaraş", "antep": "Gaziantep", "izmit": "Kocaeli", "adapazari": "Sakarya", "icel": "Mersin"})

PHONE_RE = re.compile(r"(?:\+?90[\s\-.]?|0)?\(?5\d{2}\)?[\s\-.]?\d{3}[\s\-.]?\d{2}[\s\-.]?\d{2}"
                      r"|(?:\+?90[\s\-.]?|0)\(?[2-4]\d{2}\)?[\s\-.]?\d{3}[\s\-.]?\d{2}[\s\-.]?\d{2}")
WA_LINK_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|whatsapp\.com/send\?phone=)\+?(\d{10,13})", re.I)
WA_WORD_RE = re.compile(r"(whatsapp|whatsap|wp|wa|watsap|📲|💬)[^\d+]{0,15}(\+?[\d\s\-().]{10,18})", re.I)
ILCE_IL_RE = re.compile(r"([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s*[/\-,]\s*([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)")


def normalize_phone(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    if d.startswith("90") and len(d) == 12:
        d = d[2:]
    if d.startswith("0") and len(d) == 11:
        d = d[1:]
    return "+90" + d if len(d) == 10 else ""


def extract(text: str, extra_phone: str = "") -> dict:
    text = text or ""
    phones = {normalize_phone(m.group()) for m in PHONE_RE.finditer(text)}
    if extra_phone:
        phones.add(normalize_phone(extra_phone) or extra_phone)
    phones.discard("")

    wa = {normalize_phone(m.group(1)) for m in WA_LINK_RE.finditer(text)}
    wa |= {normalize_phone(m.group(2)) for m in WA_WORD_RE.finditer(text)}
    wa.discard("")

    il, ilce = "", ""
    for m in ILCE_IL_RE.finditer(text):
        a, b = m.group(1), m.group(2)
        if _norm(b) in _IL_NORM and _norm(a) not in _IL_NORM:
            ilce, il = a, _IL_NORM[_norm(b)]
            break
    if not il:
        for w in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", text):
            if _norm(w) in _IL_NORM:
                il = _IL_NORM[_norm(w)]
                break

    adres = ""
    m = re.search(r"((?:adres|📍|🏠|mağaza|dükkan)[^\n]{5,150})", text, re.I)
    if m:
        adres = m.group(1).strip()

    return {"telefon": ", ".join(sorted(phones)), "whatsapp": ", ".join(sorted(wa)),
            "il": il, "ilce": ilce, "adres": adres}
