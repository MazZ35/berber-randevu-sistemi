"""Tespih profilleri - tarama + adim adim kontrol paneli.
Calistir:  py -m streamlit run app.py --server.port 8600
"""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from apify_source import flatten
from extractor import extract

HERE = Path(__file__).parent
EXCEL = HERE / "tespih_profilleri.xlsx"
KUYRUK = HERE / "kuyruk.json"
COLS = ["kullanici_adi", "ad", "takipci", "kategori", "telefon", "whatsapp", "email",
        "il", "ilce", "adres", "web", "profil_url", "bio"]

st.set_page_config(page_title="Tespih Profil Tarayici", layout="wide")
ss = st.session_state
ss.setdefault("queue", []); ss.setdefault("idx", 0); ss.setdefault("tarama_log", "")


def load_saved() -> pd.DataFrame:
    return pd.read_excel(EXCEL) if EXCEL.exists() else pd.DataFrame(columns=COLS)


def save_row(row: dict):
    df = load_saved()
    df = df[df["kullanici_adi"].astype(str) != row["kullanici_adi"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True)[COLS].to_excel(EXCEL, index=False)


def build_row(p: dict) -> dict:
    f = flatten(p)
    e = extract("\n".join([f["bio"], f["web"], f["is_adres"]]), extra_phone=f["is_telefon"])
    return {**{k: f[k] for k in ["kullanici_adi", "ad", "takipci", "kategori", "web", "profil_url", "bio"]},
            "telefon": e["telefon"], "whatsapp": e["whatsapp"], "email": f["is_email"],
            "il": e["il"], "ilce": e["ilce"], "adres": f["is_adres"] or e["adres"]}


def kuyrugu_yukle(only_contact: bool) -> int:
    if not KUYRUK.exists():
        return 0
    done = set(load_saved()["kullanici_adi"].astype(str))
    rows = [build_row(p) for p in json.loads(KUYRUK.read_text("utf-8")) if p["username"] not in done]
    if only_contact:
        rows = [r for r in rows if r["telefon"] or r["whatsapp"] or r["email"] or r["adres"]]
    ss.queue, ss.idx = rows, 0
    return len(rows)


# ---------- Kenar cubugu ----------
with st.sidebar:
    st.header("1) Tarama")
    terms = [t.strip() for t in st.text_area("Arama kelimeleri (satır satır)",
             "tespih\nkehribar tespih\noltu tespih").split("\n") if t.strip()]
    only_contact = st.checkbox("Sadece iletişim bilgisi olanları göster", False)
    start = st.button("🔍 Taramayı başlat", type="primary")
    st.caption("Edge penceresi açılır. Giriş isterse orada giriş yapın; tarama kendiliğinden başlar.")
    st.divider()
    st.header("2) Kontrol")
    st.write(f"kuyruk.json: **{len(json.loads(KUYRUK.read_text('utf-8'))) if KUYRUK.exists() else 0}** profil")
    if st.button("📂 Tarama sonuçlarını yükle", disabled=not KUYRUK.exists()):
        st.toast(f"{kuyrugu_yukle(only_contact)} profil kontrole eklendi")

st.title("Tespih profilleri – tarama ve kontrol")
tab0, tab1, tab2 = st.tabs(["Tarama (canlı)", "Kontrol", "Kaydedilenler"])

with tab0:
    out = st.empty()
    if start:
        log = ""
        proc = subprocess.Popen([sys.executable, "-u", str(HERE / "tara.py"), *terms, "--panel"],
                                cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            log += line
            out.code(log[-6000:], language=None)
        proc.wait()
        ss.tarama_log = log
        n = kuyrugu_yukle(only_contact)
        st.success(f"Tarama bitti. {n} profil 'Kontrol' sekmesine eklendi.")
    elif ss.tarama_log:
        out.code(ss.tarama_log[-6000:], language=None)
    else:
        out.info("Soldan 'Taramayı başlat' deyin. Taranan her sayfa ve bulunan her profil burada görünür.")

with tab1:
    q = ss.queue
    if ss.idx >= len(q):
        st.info("Kontrol edilecek profil yok. Önce tarama yapın ya da 'Tarama sonuçlarını yükle' deyin.")
    else:
        r = q[ss.idx]
        st.progress(ss.idx / len(q), text=f"{ss.idx + 1} / {len(q)}")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"@{r['kullanici_adi']}  ·  {r['ad']}")
            st.markdown(f"[Profili aç]({r['profil_url']})  ·  Takipçi: {r['takipci']}  ·  {r['kategori']}")
            st.text_area("Bio (ham veri)", r["bio"], height=240, disabled=True)
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
                save_row({**r, **ed}); ss.idx += 1; st.rerun()
            if skip:
                ss.idx += 1; st.rerun()
            if back and ss.idx > 0:
                ss.idx -= 1; st.rerun()

with tab2:
    df = load_saved()
    st.write(f"{len(df)} kayıt")
    st.dataframe(df, width="stretch")
    if EXCEL.exists():
        st.download_button("Excel indir", EXCEL.read_bytes(), EXCEL.name)
