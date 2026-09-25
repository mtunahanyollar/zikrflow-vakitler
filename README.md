# zikrflow-vakitler

ZikrFlow'un Türkiye'deki ilçe bazlı namaz vakitleri için statik JSON veri deposu.
Veri, Diyanet İşleri Başkanlığı'nın Namaz Vakitleri sayfasından haftalık otomasyonla (her pazartesi) alınır; Diyanet sayfasının yıllık tablosu bir sonraki takvim yılını verdiğinden aylık tablo (31 gün) kullanılır.

Uygulamalar bir ilçeyi şu URL'den okur:

`https://raw.githubusercontent.com/mtunahanyollar/zikrflow-vakitler/main/vakitler/<ilceId>.json`

Örnek şema:

```json
{
  "ilceId": "9206",
  "il": "Ankara",
  "ilce": "Ankara",
  "fetchedAt": "2026-09-25",
  "gunler": [{"t": "2026-09-25", "h": "13 Rebiülahir 1448", "imsak": "05:08", "gunes": "06:32", "ogle": "12:45", "ikindi": "16:09", "aksam": "18:49", "yatsi": "20:07"}]
}
```

`iller.json`, Diyanet ile aynı kimlikleri taşıyan il/ilçe kataloğudur. İlk üretiminde
kimlikler e-Mushaf listesinden alınır; çalışma zamanı ve GitHub Action yalnız Diyanet
sayfasına bağlıdır. İlçe koordinatları Wikidata'dan, eşleşmeyenler OSM Nominatim'den
tamamlanır.

## Kaynak ve lisans

Namaz vakti verisi **Diyanet İşleri Başkanlığı** kaynaklıdır. Koordinatlar Wikidata ve
OpenStreetMap katkıcılarından gelir; OSM koordinatları ODbL koşullarına tabidir.
Depodaki kod MIT lisanslıdır; veri üzerindeki haklar Diyanet'e aittir.

## Sunucu worker (Dokploy)

`Dockerfile` tek konteyner kurar: nginx `/data`'yı statik servis eder, arka planda `deploy/entrypoint.sh`
her saat kontrol edip `fetch_report.json` 7 günden eskiyse (ya da yoksa) tüm ilçeleri yeniden çeker
(869 istek, saniyede bir; ~15 dk). Konteyner yeniden başlarsa veri ilk çekime kadar boştur; uygulama bu
sürede önbelleğini ve aladhan yedeğini kullanır.

Uç noktalar: `/vakitler/<ilceId>.json`, `/iller.json`, `/fetch_report.json`, `/healthz`.
Prod: `https://vakitler.tunahanyollar.net`. GitHub Action (`.github/workflows/fetch.yml`) artık yalnız
yedek/manuel kullanım içindir; asıl üretim sunucudaki worker'dır.
