"""Tarayicidaki Instagram oturumunu (sessionid cerezi) Instaloader oturum dosyasina cevirir.
Kullanim:  py oturum_olustur.py
"""
import getpass

import instaloader

user = input("Instagram kullanici adi: ").strip()
sid = getpass.getpass("sessionid cerezi (sag tik ile yapistirip Enter; ekranda gorunmez): ").strip()
if not sid:
    raise SystemExit("Hicbir sey yapistirilmadi. Tekrar calistirin.")
print(f"Alindi: {len(sid)} karakter, '{sid[:6]}...' ile basliyor.")

L = instaloader.Instaloader()
L.context._session.cookies.set("sessionid", sid, domain=".instagram.com")
L.context.username = user
ok = L.test_login()
if not ok:
    print("Oturum gecersiz gorunuyor. Tarayicida giris yapili oldugundan emin olup tekrar deneyin.")
else:
    L.save_session_to_file()
    print(f"Tamam! {ok} olarak oturum kaydedildi. Artik uygulamayi kullanabilirsiniz.")
