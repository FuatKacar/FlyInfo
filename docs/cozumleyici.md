# Davranış Çözümleyicisi

> **Faz 3 çıktısı** · Son güncelleme: 2026-09-17
> Uygulama: [`backend/sinek/decoder/`](../backend/sinek/decoder/) · Kalibrasyon: [`calibration.json`](../backend/sinek/decoder/calibration.json)

Çözümleyici, simülasyonun nöron başına ateşleme hızlarından **deterministik** bir davranış okuması üretir. Bir LLM ya da öğrenilmiş model kullanmaz; kuralları bu belgede gerekçeleriyle yazılıdır. Köşeli parantezli numaralar [yol haritası kaynakçasına](yol-haritasi.md#8-kaynakça-ve-ilgili-çalışmalar) karşılık gelir.

## 1. Okuma nöronları

| Davranış | Okuma grubu (FlyWire tipi) | Kaynak |
|---|---|---|
| Beslenme (hortum uzatma) | MN9 (CB0701) | [6], [3] |
| Kaçış | Dev lif (DNp01) | [11], [12] |
| Anten temizleme | aDN1 (DNg62), aDN2 (DNge078) | [10], [3] |
| Geri yürüme | MDN | [16], [18] |
| İleri yürüme | P9 (DNp09) | [17] |

## 2. Kurallar

| Kural | Tanım | Gerekçe |
|---|---|---|
| **Okuma hızı** | Davranışın okuma grupları içindeki nöronların **en yüksek** ortalama ateşleme hızı | Tek taraflı uyarımlar (ör. tek yarıkürenin Johnston organı) yalnızca bir yarıküredeki komut nöronunu etkinleştirir; ortalama sinyali yapay olarak yarıya düşürür |
| **Etkin** | hız ≥ **5 Hz** ve hız − 2·SE > 0, SE = std / √(n − 1) | Hem anlamlı bir ateşleme düzeyi hem de 30 deneme boyunca sıfırdan istatistiksel olarak ayırt edilebilirlik |
| **Skor** | min(hız / referans hız, 1) | Farklı davranışların hızları farklı ölçeklerdedir (MN9 ≈ 90 Hz, dev lif ≈ 210 Hz); skor bunları karşılaştırılabilir kılar |
| **Referans hız** | Tek kategorili senaryolarda o davranışın okuma nöronlarında gözlenen en yüksek hız | Modelin doğal uyarımlara verdiği en güçlü yanıt, veriden ölçülür |
| **Kalibre edilemeyen davranış** | En yüksek gözlenen hız etkinlik eşiğini geçmiyorsa referans ve skor **tanımsız** (`null`) | Hiçbir uyarımın başlatmadığı bir davranış için ölçek uydurulmaz |
| **Yalnızca devre** | Tüm uyarım bileşenleri `circuit_only` gruplardansa (kötü koku, CO₂) davranış iddia edilmez | Bu uyarımların çözümleyicide literatürle doğrulanmış bir davranış karşılığı yoktur |
| **Bölge özeti** | Nöropil başına tahmini sinaptik çıkış olayı/sn; en yüksek 5 bölge ve toplam içindeki payları | [veri.md](veri.md) ve `neuropils.py` |

## 3. Kalibrasyon (paket sürümü 1)

| Davranış | Referans hız | Referans senaryo |
|---|---|---|
| Beslenme | 93,0 Hz (MN9) | tatlı, yoğunluk 1,0 |
| Kaçış | 211,7 Hz (dev lif) | yaklaşan nesne, 1,0 |
| Anten temizleme | 34,5 Hz (aDN2) | Johnston organı, 1,0 |
| Geri yürüme | 21,8 Hz (MDN) | yaklaşan nesne, 1,0 |
| İleri yürüme | **tanımsız** (en yüksek 1,1 Hz) | — |

Kalibrasyon `sinek.decoder.calibration_build` ile senaryo dosyalarından yeniden üretilebilir; dosya, kullanılan senaryo dosyalarının SHA-256 özetlerini içerir. `test_kalibrasyon_hazir_paketle_tutarli` testi saklı kalibrasyonun paketle tutarlılığını denetler.

## 4. Tek kategorili senaryolarda gözlenen yanıtlar

| Uyarım | Etkin davranışlar | Doz ilişkisi | Literatürle uyum |
|---|---|---|---|
| Tatlı | Beslenme | MN9: 0,2 → 4 Hz (etkin değil), 0,4 → 56 Hz, 1,0 → 93 Hz | ✅ [3] |
| Acı (tek başına) | — | Davranış yok | ✅ Acı, beslenmeyi baskılar; kendi başına başlatmaz [6] |
| Su | Beslenme (yalnızca yüksek yoğunlukta) | 0,8 → 11 Hz, 1,0 → 29 Hz | ✅ Su, şekerden yüksek uyarım ister [3] |
| Johnston organı | Anten temizleme | 0,6 → 9 Hz, 1,0 → 35 Hz; tek taraflı | ✅ [10], [3] |
| Yaklaşan nesne | Kaçış, geri yürüme | Dev lif 0,2'de bile > 100 Hz; MDN 0,6'dan itibaren | ✅ [11], [18] |
| Kötü koku, CO₂ | — (yalnızca devre) | Bkz. bölüm 5 | ⚠️ |

**Kombinasyonlarda (örnek):** tatlı 1,0 → beslenme %86; tatlı 1,0 + acı 1,0 → **%12** (acı baskılaması, [3] şekil 3A ile uyumlu); tatlı 0,6 + su 1,0 → %96 (toplamsal).

**Kendiliğinden ortaya çıkan bulgu:** Yaklaşan nesne uyarımı dev lifin yanında MDN'yi de etkinleştirir. Bu ilişki model kurulurken hedeflenmemiştir; Sen et al. (2017) [18] MDN'lerin görsel tehditle tetiklenen geri çekilmeye aracılık ettiğini deneysel olarak göstermiştir.

## 5. Bilinen sınırlılık: koku uyarımlarında geniş yayılma

Geosmin ve CO₂ uyarımları en düşük yoğunlukta bile 30 denemenin toplamında ~8.600–8.900 nöronda aktiviteye yol açar; bu sayı yoğunlukla neredeyse değişmez, ateşleme hızları ise yoğunlukla artar (geosmin 0,2: medyan 6,8 Hz; CO₂ 1,0: medyan 44,6 Hz). En yüksek hızlar anten lobu yerel ara nöronlarında (lLN1_bc, v2LN30) ve mantar cismi geri besleme nöronlarında (APL, DPM) görülür; yüzlerce başka koku alıcı nöronu da etkinleşir. Biyolojide geosmin sinyali DA2 glomerülüne özgü, dar bir kanaldan iletilir [14].

**İncelemeler (2026-09-17):**
1. Yayılma **olasılıksaldır**: tek bir 1000 ms denemede geosmin 40 Hz uyarımı yalnızca 50 nöronu etkinleştirmiş, CO₂ 40 Hz uyarımı ise 8.459 nörona yayılmıştır. Koku devreleri bazı denemelerde geniş bir aktivite durumuna "tutuşur".
2. Yayılmada öne çıkan ara nöronların nörotransmitter tahmini çoğunlukla dopamin veya serotonindir (ör. lLN1_bc: 12 dopamin, 11 asetilkolin, 7 serotonin); referans model bunları uyarıcı sayar ([veri.md](veri.md) bölüm 3.1).
3. Dopamin, serotonin ve oktopamin sinapsları **nötr** bırakıldığında CO₂ yayılması 8.459 → 3.513 nörona iner (%58); doğrulanmış devreler etkilenmez (tatlı → MN9, Johnston organı → aDN1).

**Sonuç:** Yayılma bir kod hatası değil, referans modelin koku yollarındaki bir sınırlılıktır; bu yollar makalede doğrulanmamıştır. Nöromodülatörlerin uyarıcı sayılması etkenlerden biridir ama tek başına açıklamaz. Kötü koku ve CO₂ uyarımları arayüzde "yalnızca devre aktivitesi" olarak ve bu uyarıyla gösterilir.

**Öneri (Faz 6):** Laboratuvar sekmesinde "nöromodülatör sinapsları nötr" işaret seçeneği sunulması; araştırmacılar etkiyi doğrudan inceleyebilir.
