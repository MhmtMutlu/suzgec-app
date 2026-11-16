# İçgör sitesi: SEO ve GEO

Zirve sitesindeki çalışmanın (zirve-app, zirve/docs/aso-geo) İçgör'e uyarlanmış hali. Kısa kural: sitede yalnızca
uygulamanın gerçekten yaptığı ve kural dosyalarında kaynağı olan bilgi yazılır.

## Hedeflenen aramalar ve sayfalar

| Arama niyeti | Sayfa |
|---|---|
| katkı maddesi tarayıcı, barkod okuyucu gıda, gıda içerik tarayıcı | `/` (başlık: "Katkı maddesi ve barkod tarayıcı, ailene göre") |
| gıda katkı maddeleri, E kodları listesi | `/katki-maddeleri/` (72 madde, türe göre) |
| "E471 nedir", "E102 zararlı mı", "tartrazin" | `/katki-maddeleri/e471/` … (72 sayfa; her biri kendi verisiyle) |
| beslenme skoru nedir, gıda skoru, nutri-score Türkiye | `/beslenme-skoru/` |
| 14 alerjen, etikette alerjen | `/alerjenler/` |
| içindekiler nasıl okunur, besin değerleri tablosu okuma | `/etiket-okuma/` |
| basın, uygulama hakkında kısa bilgi (AI yanıtları) | `/basin/` |

Sayfa başına tek konu; aynı metni farklı anahtar kelimeyle çoğaltan "kapı sayfası" yok.

## Teknik
- Her sayfa: canonical, açıklama, Open Graph + `og:locale tr_TR`, Twitter kartı, `apple-itunes-app` (Smart App Banner).
- JSON-LD tek `@graph`: Organization (mm-apps), WebSite, WebPage, BreadcrumbList; ana sayfada MobileApplication
  (puan/ödül yok); katkı listesinde CollectionPage + ItemList; rehberlerde Article; basında AboutPage.
- `sitemap.xml`: `lastmod` sayfanın içeriği gerçekten değişince ilerler (`data/lastmod.json`).
- `robots.txt`: arama ve yapay zekâ botlarına açık. `llms.txt`: aynı bilgiler, Türkçe (deneysel; Google kullanmıyor).
- IndexNow anahtarı derlemede `/<anahtar>.txt` olarak yazılır; `scripts/indexnow.sh` yayından sonra çalıştırılır.
- 404: `noindex`, canonical ve JSON-LD yok.

## Derleme denetimleri (`python3 build.py`)
- İç bağlantılar ve çapalar.
- JSON-LD yalnızca sayfada görünen şeyi söyler (ad = başlık, açıklama = meta, sayfa yolu adları sayfada).
- Yasak ifadeler (başlık, H1 ve metinde): "en iyi", "#1", "zararsız", "kanserojen", "tehlikeli", "resmî skor", "garanti" vb.
  Yasal sayfalar metin denetiminden muaf.
- `data/rules/*.json` uygulama deposundakiyle aynı olmalı; değilse `python3 build.py --sync-rules`.

## Sürüm anahtarları (`build.py` başı)
- `APP_RELEASE`: App Store'daki sürüm. "1.1" yayına girince değiştir ve `python3 build.py --sync` çalıştır
  (yasal metinler 1.1 için uygulama deposundan kopyalanır; 1.0 yayındayken `--sync` reddedilir).
- `PRICE_SET`: App Store'un bugün aldığı fiyat. 1.1 fiyatları (₺49,99 / ₺299,99) Apple'da başladığı gün "1.1" yap.
- İkisi farklı günlere düşebilir; site her zaman mağazayla aynı şeyi söylemeli.

## Senin yapacakların
1. **Search Console:** Alan adı mülkü (`icgor.mm-apps.com` ya da `mm-apps.com`), Cloudflare'de DNS TXT ile doğrula;
   `https://icgor.mm-apps.com/sitemap.xml` gönder; ana sayfa, `/katki-maddeleri/` ve `/beslenme-skoru/` için dizine ekleme iste.
2. **Bing Webmaster:** Search Console'dan içe aktar, sitemap'i onayla (ChatGPT ve Copilot aramaları Bing dizinini kullanır).
3. **GitHub Pages:** Settings > Pages > "Enforce HTTPS" açık mı kontrol et.
4. **Yayından sonra:** `./scripts/indexnow.sh` (değişen sayfaları Bing/Yandex'e bildirir).
5. **App Store açıklaması:** İlk cümle sitedeki tanımla aynı olsun (yapay zekâ yanıtları en çok App Store sayfasını kaynak gösteriyor).
6. **Yasal sayfalardaki yer tutucular:** `[YÜRÜRLÜK TARİHİ]`, `[POSTA ADRESİ]`, `[TEYİT EDİLECEK …]` canlı sayfalarda
   görünüyor. Metinler uygulama deposunda (`docs/legal/v2`); doldurulması senin kararın.

## Ölçüm (ayda bir)
Oturum kapalı, her soru yeni sohbette: ChatGPT, Perplexity, Google AI Modu, Gemini, Copilot. Sorular:
"katkı maddesi tarayan uygulama", "E471 nedir", "beslenme skoru nasıl hesaplanır", "alerjen tarayıcı uygulama",
"İçgör uygulaması nedir". İçgör anılıyor mu, bilgi doğru mu, hangi kaynak gösteriliyor; yanlışsa kaynağı düzelt.
Ek veri: Search Console sorguları, Bing Webmaster "AI Performance", App Analytics web yönlendirmeleri.
