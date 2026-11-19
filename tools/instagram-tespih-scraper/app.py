"""Tespih profilleri - adim adim kontrollu kazima arayuzu.
Calistir:  streamlit run app.py
"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

import apify_source
import instaloader_source
from apify_source import flatten
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
    kaynak = st.radio("Kaynak", ["Ücretsiz (Instaloader)", "Apify (ücretli)"])
    if kaynak.startswith("Ücretsiz"):
        ig_user = st.text_input("Instagram kullanıcı adınız (yedek hesap önerilir)")
        ready = bool(ig_user)
        st.caption("Önce terminalde bir kez: `py -m instaloader --login KULLANICI`")
    else:
        token = st.text_input("Apify API token", value=os.getenv("APIFY_TOKEN", ""), type="password")
        ready = bool(token)
    terms = st.text_area("Arama kelimeleri (satir satir)",
                         "tespih\ntesbih\nkehribar tespih\noltu tespih\nkuka tespih\ntespih atölyesi").split("\n")
    limit = st.number_input("Kelime basina max profil", 5, 200, 20)
    batch = st.number_input("Detay cekme parti boyutu", 5, 100, 10)
    only_contact = st.checkbox("Sadece iletisim bilgisi olanlari goster", True)

    def src():
        if kaynak.startswith("Ücretsiz"):
            if ss.get("L_user") != ig_user:
                ss.L = instaloader_source.get_loader(ig_user); ss.L_user = ig_user
            return (lambda t, l: instaloader_source.search_users(ss.L, t, l, log=ss.log.append),
                    lambda us: instaloader_source.profile_details(ss.L, us, log=ss.log.append))
        return (lambda t, l: apify_source.search_users(token, t, l),
                lambda us: apify_source.profile_details(token, us))

    if st.button("Profilleri ara", type="primary", disabled=not ready):
        with st.spinner("Kullanicilar aranıyor (ücretsiz modda yavaştır, bekleyin)..."):
            try:
                users = src()[0]([t.strip() for t in terms if t.strip()], int(limit))
            except FileNotFoundError:
                st.error("Oturum dosyası yok. Terminalde `py -m instaloader --login KULLANICI` çalıştırın.")
                users = []
        done = set(load_saved()["kullanici_adi"].astype(str))
        ss.pending_users = [u for u in users if u not in done]
        ss.found_users = users
        ss.log.append(f"{len(users)} profil bulundu, {len(ss.pending_users)} yeni.")
    pend = ss.get("pending_users", [])
    if Path("kuyruk.json").exists() and st.button("📂 Tarama sonuçlarını yükle (tara.py)"):
        import json
        done = set(load_saved()["kullanici_adi"].astype(str))
        rows = [build_row(p) for p in json.loads(Path("kuyruk.json").read_text("utf-8"))
                if p["username"] not in done]
        if only_contact:
            rows = [r for r in rows if r["telefon"] or r["whatsapp"] or r["email"] or r["adres"]]
        ss.queue, ss.idx = rows, 0
        ss.log.append(f"kuyruk.json: {len(rows)} profil kontrole eklendi.")
    st.write(f"Detayi cekilmemis: **{len(pend)}**")
    if pend and st.button(f"Sonraki {min(len(pend), int(batch))} profilin detayini cek"):
        part, ss.pending_users = pend[:int(batch)], pend[int(batch):]
        with st.spinner("Profil detaylari cekiliyor..."):
            rows = [build_row(p) for p in src()[1](part)]
        if only_contact:
            rows = [r for r in rows if r["telefon"] or r["whatsapp"] or r["email"] or r["adres"]]
        ss.queue.extend(rows)
        ss.log.append(f"{len(part)} profil cekildi, {len(rows)} kontrol kuyruguna eklendi.")
    st.divider()
    for l in ss.log[-8:]:
        st.caption(l)

# ---------- Ana alan: adim adim kontrol ----------
st.title("Tespih profilleri – adım adım kontrol")
tab1, tab2, tab3 = st.tabs(["Kontrol", f"Kaydedilenler ({EXCEL.name})", "Tarama kaydı"])

with tab3:
    st.subheader("Instagram'a yapılan istekler")
    st.caption("Durum 200 = başarılı. 401/404/429 = Instagram reddetti.")
    log_df = pd.DataFrame(instaloader_source.SCANNED[::-1])
    if log_df.empty:
        st.info("Henüz istek yapılmadı.")
    else:
        st.dataframe(log_df, width="stretch",
                     column_config={"adres": st.column_config.LinkColumn("adres")})
    st.subheader("Bulunan profiller")
    fu = ss.get("found_users", [])
    st.write(f"{len(fu)} profil")
    for u in fu:
        st.markdown(f"- [@{u}](https://www.instagram.com/{u}/)")

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
            st.dataframe(pd.DataFrame(q[ss.idx:]), width="stretch")

with tab2:
    df = load_saved()
    st.dataframe(df, width="stretch")
    if EXCEL.exists():
        st.download_button("Excel indir", EXCEL.read_bytes(), EXCEL.name)
