"""Tarayicidaki Instagram oturumunu (sessionid cerezi) Instaloader oturum dosyasina cevirir.
Kullanim:  py oturum_olustur.py
"""
import getpass

import instaloader

user = input("Instagram kullanici adi: ").strip()
sid = getpass.getpass("sessionid cerezi (yapistirin, ekranda gorunmez): ").strip()

L = instaloader.Instaloader()
L.context._session.cookies.set("sessionid", sid, domain=".instagram.com")
L.context.username = user
ok = L.test_login()
if not ok:
    print("Oturum gecersiz gorunuyor. Tarayicida giris yapili oldugundan emin olup tekrar deneyin.")
else:
    L.save_session_to_file()
    print(f"Tamam! {ok} olarak oturum kaydedildi. Artik uygulamayi kullanabilirsiniz.")
