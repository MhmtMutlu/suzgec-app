# suzgec-app

İçgör'ün web sitesi: tanıtım sayfası ve yasal metinler. GitHub Pages ile yayınlanır:
<https://mhmtmutlu.github.io/suzgec-app/>

| Sayfa | Adres |
|---|---|
| Tanıtım | `/` |
| Gizlilik politikası | `/gizlilik/` |
| Kullanım koşulları | `/kosullar/` |
| Katkı koşulları | `/katki/` |
| KVKK bilgilendirmesi | `/kvkk/` |
| Destek | `/destek/` |

## Düzenleme
- Yasal metinlerin kaynağı uygulama deposundaki `docs/legal/v2/*.md` dosyalarıdır (iki avukat görüşüyle yazıldı).
  Değişince: `python3 build.py --sync` (metinleri `src/legal/` altına kopyalar ve siteyi derler).
- Tanıtım metni, fiyatlar ve uygulama adı `build.py` başındaki sabitlerde. Ad tek yerde (`APP_NAME`); değişirse
  yalnız orayı değiştirip yeniden derle. Depo adı (`suzgec-app`) adres kırılmasın diye eski adla kalıyor.
- Yayın günü: `APP_STORE_LIVE = True` (rozetler gerçek App Store bağlantısı olur).
- Derleme: `python3 build.py`. Statik HTML depo köküne yazılır ve commit'lenir; bütün iç bağlantılar ve sayfa içi
  çapalar derlemede kontrol edilir. GitHub Pages ek bir derleme adımı çalıştırmaz.
- Stil: `assets/site.css`. Renkler uygulamanın token'larıyla aynı (`suzgec/tools/gen_colors.py`); yazı tipleri sistem
  yazı tipleri, dışarıdan hiçbir şey indirilmez.

## Gizlilik
Site çerez, analiz aracı veya üçüncü taraf isteği kullanmaz. Barındırma GitHub Pages'tedir: ziyaretçinin IP adresi
GitHub'a (ABD) ulaşır; bu, gizlilik politikasının 3.7 bölümünde açıkça yazılıdır.

## Yayına alma
Settings → Pages → Source: *Deploy from a branch* → Branch: `main` / `(root)`.
