# Instagram Tespih Profil Tarayıcı

Tespih ile ilgili Instagram profillerini bulur; bio, işletme iletişim butonları ve linklerden
**telefon, WhatsApp, e-posta, il/ilçe, adres** bilgisini çıkarır. Her profil sizin onayınızdan
geçtikten sonra `tespih_profilleri.xlsx` dosyasına yazılır.

## Kurulum
```bash
pip install -r requirements.txt
export APIFY_TOKEN=apify_api_xxx      # https://console.apify.com/account/integrations
streamlit run app.py
```

## Akış
1. Sol menüde arama kelimelerini düzenleyip **Profilleri ara** (Apify `instagram-search-scraper`).
2. **Detay çek** ile profilleri parti parti çekin (Apify `instagram-profile-scraper`).
   Daha önce Excel'e kaydedilenler tekrar çekilmez.
3. Ana ekranda her profil için ham bio'yu ve otomatik çıkarılan alanları görürsünüz;
   düzeltip **Onayla & kaydet**, **Atla** veya **Geri** diyebilirsiniz.
4. "Kaydedilenler" sekmesinden Excel'i görüntüleyip indirebilirsiniz.

## Ücretsiz mod (Instaloader)
Kendi Instagram hesabınızla çalışır (ana hesabınız yerine **yedek bir hesap** kullanın).
Bir kez terminalde giriş yapın (oturum dosyası kaydedilir, şifre uygulamaya girilmez):
```powershell
py -m instaloader --login KULLANICI_ADINIZ
```
Sonra uygulamada "Ücretsiz (Instaloader)" seçip kullanıcı adınızı yazın. Engellenmemek için
her istek arasında 4-10 sn beklenir; az sayıda (günde birkaç yüz) profil tarayın.

## Neden Apify?
Kendi Instagram hesabınızla doğrudan kazıma yapmak hesabınızın kısıtlanmasına/kapatılmasına yol açar.
Meta'nın resmi Graph API'si anahtar kelimeyle kullanıcı aramaya izin vermez. Apify ücretli
(az miktar için ücretsiz kredi var) ama hesabınızı riske atmaz.

## Yasal not
Sadece profillerin herkese açık paylaştığı işletme iletişim bilgilerini toplayın. Toplanan verilerle
toplu/istenmeyen mesaj göndermek KVKK ve ETK (ticari elektronik ileti) kapsamında yaptırıma tabi
olabilir; ilk temasta izin alın ve ret talebine uyun.
