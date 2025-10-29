# CCI İndikatörü (Kaynak Modları)

## Amaç
TradingView ile sinyal uyumluluğunu artırmak ve mevcut (typical price) yaklaşımı koruyarak esnek yapı sağlamak.

## Formül
Standart CCI:
```
CCI = (Source - SMA(Source, L)) / (0.015 * MeanDeviation(Source, L))
```
- Source (Mod):
  - `typical` = (High + Low + Close) / 3 (varsayılan eski davranış)
  - `close`   = Close fiyatı (TradingView `ta.cci(close, L)` uyumu)
- MeanDeviation: Mutlak sapmaların ortalaması

## Parametreler
| Ad | Değer | Açıklama |
|----|-------|----------|
| CCI_LENGTH | 13 | Periyot |
| CCI_THRESHOLD_HIGH | 100 | Üst eşik |
| CCI_THRESHOLD_LOW | -100 | Alt eşik |
| CCI_SOURCE_MODE | typical (varsayılan) | typical | close |

## Pattern Mantığı (Sinyal)
SELL:
```
not (CCI_curr > +100) and CCI_prev1 > +100 and CCI_prev2 > +100
```
BUY:
```
not (CCI_curr < -100) and CCI_prev1 < -100 and CCI_prev2 < -100
```
Bu üç mumluk teyit, tek kırılım sinyaline göre daha filtreli çalışır.

## Neden Kaynak Modu Ekledik?
- TradingView görsel doğrulama kolaylığı
- 4h / 1d timeframe uyumsuzluklarının temel kaynağı typical vs close farkı
- Strateji davranışını tek seferde kırmadan opsiyonel geçiş

## Rollout Önerisi
1. `CCI_SOURCE_MODE=typical` (varsayılan) ile devam
2. `cci_diff.py` çalıştır ve farkları incele:
   ```
   python cci_diff.py --interval 4h --show-signals
   ```
3. Eşik bölgesi ve sinyal ayrışmalarını değerlendir
4. Uygun görülürse `.env` içine:
   ```
   CCI_SOURCE_MODE=close
   ```
5. Değişiklik anını README değişiklik notuna ekle

## Log Örneği (Gelecekte Opsiyonel)
```
[CCI_DIFF] tf=4h idx=201 typical=108.4 close=112.7 delta=4.3 sigA=NEUTRAL sigB=SELL
```

## Dikkat Edilecekler
- Kaynak değişimi geçmiş sinyal serisini yeniden üretilemez kılar
- Sinyal frekansı eşik yakınlarında artabilir (false positive değerlendirmesi yapılmalı)
- Gerekirse threshold ince ayarı (+/- 110) test edilebilir

## Gelecek Çalışmalar
- Opsiyonel parallel hesap modunun loglanması
- Backtest harness entegrasyonu
- CCI jitter / smoothing varyantlarının parametrizasyonu
