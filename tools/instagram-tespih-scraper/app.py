"""Tespih profilleri - adim adim kontrollu kazima arayuzu.
Calistir:  streamlit run app.py
"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from apify_source import flatten, profile_details, search_users
from extractor import extract

EXCEL = Path(os.getenv("CIKTI_EXCEL", "tespih_profilleri.xlsx"))
COLS = ["kullanici_adi", "ad", "takipci", "kategori", "telefon", "whatsapp", "email",
        "il", "ilce", "adres", "web", "profil_url", "bio"]

st.set_page_config(page_title="Tespih Profil Tarayici", layout="wide")
ss = st.session_state
ss.setdefault("queue", []); ss.setdefault("idx", 0); ss.setdefault("log", [])


def load_saved() -> pd.DataFrame:
    return pd.read_excel(EXCEL) if EXCEL.exists() else pd.DataFrame(columns=COLS)


def save_row(row: dict):
    df = load_saved()
    df = df[df["kullanici_adi"] != row["kullanici_adi"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True)[COLS].to_excel(EXCEL, index=False)


def build_row(p: dict) -> dict:
    f = flatten(p)
    text = "\n".join([f["bio"], f["web"], f["is_adres"]])
    e = extract(text, extra_phone=f["is_telefon"])
    return {**{k: f[k] for k in ["kullanici_adi", "ad", "takipci", "kategori", "web", "profil_url", "bio"]},
            "telefon": e["telefon"], "whatsapp": e["whatsapp"], "email": f["is_email"],
            "il": e["il"], "ilce": e["ilce"], "adres": f["is_adres"] or e["adres"]}


# ---------- Kenar cubugu: arama ----------
with st.sidebar:
    st.header("1) Arama")
    token = st.text_input("Apify API token", value=os.getenv("APIFY_TOKEN", ""), type="password")
    terms = st.text_area("Arama kelimeleri (satir satir)",
                         "tespih\ntesbih\nkehribar tespih\noltu tespih\nkuka tespih\ntespih atölyesi").split("\n")
    limit = st.number_input("Kelime basina max profil", 5, 200, 30)
    batch = st.number_input("Detay cekme parti boyutu", 5, 100, 20)
    only_contact = st.checkbox("Sadece iletisim bilgisi olanlari goster", True)
    if st.button("Profilleri ara", type="primary", disabled=not token):
        with st.spinner("Kullanicilar aranıyor..."):
            users = search_users(token, [t.strip() for t in terms if t.strip()], int(limit))
        done = set(load_saved()["kullanici_adi"].astype(str))
        ss.pending_users = [u for u in users if u not in done]
        ss.log.append(f"{len(users)} profil bulundu, {len(ss.pending_users)} yeni.")
    pend = ss.get("pending_users", [])
    st.write(f"Detayi cekilmemis: **{len(pend)}**")
    if pend and st.button(f"Sonraki {min(len(pend), int(batch))} profilin detayini cek"):
        part, ss.pending_users = pend[:int(batch)], pend[int(batch):]
        with st.spinner("Profil detaylari cekiliyor..."):
            rows = [build_row(p) for p in profile_details(token, part)]
        if only_contact:
            rows = [r for r in rows if r["telefon"] or r["whatsapp"] or r["email"] or r["adres"]]
        ss.queue.extend(rows)
        ss.log.append(f"{len(part)} profil cekildi, {len(rows)} kontrol kuyruguna eklendi.")
    st.divider()
    for l in ss.log[-8:]:
        st.caption(l)

# ---------- Ana alan: adim adim kontrol ----------
st.title("Tespih profilleri – adım adım kontrol")
tab1, tab2 = st.tabs(["Kontrol", f"Kaydedilenler ({EXCEL.name})"])

with tab1:
    q = ss.queue
    if ss.idx >= len(q):
        st.info("Kontrol edilecek profil yok. Soldan arama yapıp detay çekin.")
    else:
        r = q[ss.idx]
        st.progress((ss.idx) / len(q), text=f"{ss.idx + 1} / {len(q)}")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader(f"@{r['kullanici_adi']}  ·  {r['ad']}")
            st.markdown(f"[Profili aç]({r['profil_url']})  ·  Takipçi: {r['takipci']}  ·  {r['kategori']}")
            st.text_area("Bio (ham veri)", r["bio"], height=220, disabled=True)
            if r["web"]:
                st.write("Link:", r["web"])
        with c2:
            with st.form(f"f{ss.idx}"):
                ed = {k: st.text_input(k, str(r[k] or "")) for k in
                      ["telefon", "whatsapp", "email", "il", "ilce", "adres"]}
                a, b, c = st.columns(3)
                ok = a.form_submit_button("✅ Onayla & kaydet", type="primary")
                skip = b.form_submit_button("⏭ Atla")
                back = c.form_submit_button("⏮ Geri")
            if ok:
                save_row({**r, **ed}); ss.log.append(f"Kaydedildi: {r['kullanici_adi']}")
                ss.idx += 1; st.rerun()
            if skip:
                ss.idx += 1; st.rerun()
            if back and ss.idx > 0:
                ss.idx -= 1; st.rerun()
        with st.expander("Kuyruktaki tüm veriler (tablo)"):
            st.dataframe(pd.DataFrame(q[ss.idx:]), use_container_width=True)

with tab2:
    df = load_saved()
    st.dataframe(df, use_container_width=True)
    if EXCEL.exists():
        st.download_button("Excel indir", EXCEL.read_bytes(), EXCEL.name)
