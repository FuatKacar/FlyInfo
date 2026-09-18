# Veri Hattı ve Veri Kararları

> **Faz 1 çıktısı** · Son güncelleme: 2026-09-17
> Bu belgedeki tüm sayılar `backend/tests/connectome/test_real_data.py` tarafından otomatik olarak doğrulanır.

Bu belge, projenin kullandığı ham verinin nereden geldiğini, nasıl doğrulandığını ve veriyle ilgili alınan bilimsel kararları açıklar. Köşeli parantezli numaralar [yol haritası Bölüm 8](yol-haritasi.md#8-kaynakça-ve-ilgili-çalışmalar) kaynakçasına karşılık gelir.

## 1. Ham veri kaynakları

Tüm dosyalar belirli bir git commit'ine sabitlenmiştir ve SHA-256 özetiyle doğrulanır (`backend/sinek/connectome/sources.py`). Dosyalar `uv run sinek indir` komutuyla `data/raw/` dizinine indirilir; özet uyuşmazsa dosya kullanılmaz.

| Dosya | Kaynak | Boyut | İçerik |
|---|---|---|---|
| `Completeness_783.csv` | `philshiu/Drosophila_brain_model` @ `91bdd1e7` [3] | 3,3 MB | Modele dahil nöronlar; satır sırası = model indeksi |
| `Connectivity_783.parquet` | `philshiu/Drosophila_brain_model` @ `91bdd1e7` [3] | 100,8 MB | İşaretli sinaptik bağlantı tablosu |
| `Supplemental_file1_neuron_annotations.tsv` | `flyconnectome/flywire_annotations` @ `8587524c` [2], [7] | 31,7 MB | Hücre tipi, sınıf, taraf, nörotransmitter tahmini |

**Lisans:** Referans model kodu MIT, FlyWire verileri CC-BY 4.0. Anotasyon dosyası Schlegel et al. (2024) [2] ile yayımlanmış, Berg et al. (2025) [7] ile güncellenmiştir.

## 2. Konektom özeti

| Ölçüt | Değer | Karşılaştırma |
|---|---|---|
| Nöron sayısı (model) | 138.639 | FlyWire v783 toplamı 139.255 [1]; model yalnızca "tamamlanmış" nöronları içerir |
| Bağlantı (nöron çifti) sayısı | 15.091.983 | — |
| Kimyasal sinaps sayısı | 54.492.922 | ~5×10⁷ [1] ✅ |
| Uyarıcı / baskılayıcı bağlantı | 9.059.302 / 6.032.681 | — |

**Matris yönelimi:** `weights[post, pre]` = işaretli sinaps sayısı. Bir nörona gelen girdi `weights @ aktivite` ile hesaplanır.

**Bütünlük kontrolleri** (her yüklemede çalışır): kimlik ↔ indeks eşlemesinin nöron listesiyle birebir tutarlılığı, indekslerin sınır içinde olması, yinelenen bağlantı olmaması, sinaps sayılarının pozitif olması, işaret sütununun yalnızca ±1 içermesi.

## 3. Sinaps işareti

### 3.1 Referans kural
Referans bağlantı tablosunda işaret **presinaptik nöron başına** tanımlıdır. Anotasyonlarla karşılaştırıldığında kural şudur:

| Nörotransmitter | İşaret |
|---|---|
| Asetilkolin, dopamin, serotonin, oktopamin | + (uyarıcı) |
| GABA, glutamat | − (baskılayıcı) |

Dopamin, serotonin ve oktopamin nöromodülatördür; referans modelde basitleştirme olarak uyarıcı kabul edilmiştir. Bu bir **model sınırlılığıdır** ve sınırlılıklar sayfasında belirtilecektir.

### 3.2 Referans ve güncel anotasyon farkı
Referans modelin işaretleri, güncel anotasyon dosyasındaki `top_nt` tahminiyle **6.021 nöronda (%4,34)** uyuşmaz. Bu nöronların çıkış bağlantıları toplam bağlantıların **%1,23**'üdür. En olası neden referans modelin daha eski bir nörotransmitter tahmin sürümünü kullanmasıdır.

**Karar:** İşaret kaynağı seçilebilirdir (`SignSource`).
- `reference` (**varsayılan**): Makale sonuçlarıyla birebir karşılaştırma ve doğrulama için.
- `annotations`: Güncel tahminlerle çalışmak isteyen araştırmacılar için (Laboratuvar). Anotasyonda nörotransmitteri bilinmeyen nöronlar referans işaretini korur.

İki kaynak arasındaki davranış farkı Faz 2 doğrulama raporunda ayrıca raporlanacaktır.

## 4. Nöron grupları

Grupların tek doğruluk kaynağı [`backend/sinek/connectome/neuron_groups.toml`](../backend/sinek/connectome/neuron_groups.toml) dosyasıdır. Her grubun seçim yöntemi, kaynağı ve atfı dosyada yazılıdır.

### 4.1 Seçim ilkeleri
1. **Referans kimlikleri önceliklidir.** Shiu et al. (2024) [3] analiz kodunda kullanılan kimlik listeleri varsa bunlar kullanılır. Örneğin şekere ve suya duyarlı nöronlar anotasyonda aynı hücre tipindedir (LB3, `sugar/water`); ayrımları yalnızca referans listelerle yapılabilir.
2. **Referans yoksa hücre tipi anotasyonu** kullanılır.
3. **Tahminle tamamlama yapılmaz.** v783'te kimliği değişen referans nöronları yalnızca FlyWire CAVE servisiyle **doğrulanmış ardıllarıyla** değiştirilir (bölüm 4.3). Ardılı doğrulanamayan kimlik gruba eklenmez, "kayıp" olarak raporlanır.
4. **İsim benzerliğine güvenilmez.** Örnek: FlyWire'da eşanlamlısı "aDN" olan SMP029 nöronu çiftleşme davranışıyla ilgilidir ve anten temizleme komut nöronu aDN ile **ilgisizdir**. Okuma nöronları referans kodundaki kimliklerden hücre tipine eşlenmiştir.

### 4.2 Sonuç tablosu

| Grup | Rol | Seçim | Nöron | v783 ardılı | Not |
|---|---|---|---|---|---|
| `sugar` | uyarım | referans | 21 | 1 | |
| `bitter` | uyarım | referans | 21 | 1 | |
| `water` | uyarım | referans | 18 | 0 | |
| `ir94e` | uyarım | referans | 18 | 0 | Yalnızca Laboratuvar / doğrulama |
| `johnston_organ` | uyarım | referans | 146 | 1 | JO-CE + JO-F + JO-D/m |
| `looming` | uyarım | anotasyon | 314 | — | LC4 + LPLC2, iki yarıküre |
| `geosmin` | uyarım | anotasyon | 39 | — | ORN_DA2 |
| `co2` | uyarım | anotasyon | 67 | — | ORN_V |
| `mn9` | okuma | anotasyon | 2 | — | CB0701; beslenme |
| `giant_fiber` | okuma | anotasyon | 2 | — | DNp01; kaçış |
| `adn1` | okuma | anotasyon | 2 | — | DNg62; anten temizleme |
| `adn2` | okuma | anotasyon | 2 | — | DNge078; anten temizleme |
| `mdn` | okuma | anotasyon | 4 | — | Geri yürüme |
| `p9` | okuma | anotasyon | 2 | — | DNp09; ileri yürüme |
| `abn1` | okuma | anotasyon | 2 | — | SAD093; yalnızca doğrulama |

Referans gruplarının tamamı makaledeki boyutlardadır; kayıp nöron yoktur.

### 4.3 Kimlik değişimleri (v630 → v783)
Referans kod FlyWire **v630** kimliklerini kullanır. FlyWire'da bir nöron düzeltildiğinde kimliği değişir. Referans listelerdeki kimliklerin büyük çoğunluğu v783'te aynıdır. Değişenlerin v783 ardılları FlyWire CAVE servisiyle (`flywire_fafb_public`, 2026-09-17) belirlenmiştir:

1. `chunkedgraph.get_latest_roots(eski_kimlik, timestamp=v783)` ile ardıl adayları bulunur.
2. Birden fazla aday varsa, eski nöronun L2 hacim parçalarından hangisinin payını taşıdığı ölçülür.
3. Ardılın hücre tipi anotasyonla kontrol edilir.

| Grup | v630 kimliği | v783 ardılı | Kanıt |
|---|---|---|---|
| `sugar` | 720575940620900446 | 720575940639259967 | Örtüşme %100; LB3, sugar/water |
| `bitter` | 720575940618600651 | 720575940619072513 | Örtüşme %100; LB1c, bitter |
| `johnston_organ` | 720575940626307902 | 720575940625054647 | Nöron ikiye bölünmüş: bu parça eski hacmin %98,6'sını taşır ve tek atası eski kimliktir; diğer parça (720575940638571486) %0 taşır. JO-EV3 |
| MN9 (ikinci yarıküre) | 720575940645521262 | 720575940618238523 | Örtüşme %99,3; hücre tipi (CB0701) ile yapılan seçimi doğrular |
| Susturma deneyi (doğrulama) | 720575940615041430 | 720575940640589171 | Örtüşme %100; DNge031 |

Eşlemeler `neuron_groups.toml` içinde `successors` alanında kaynağıyla birlikte saklanır; v630 referans listeleri makale doğrulaması için değiştirilmeden korunur. Projeyi kullananların FlyWire hesabına ihtiyacı yoktur.

**Ardılların etkisi (Faz 2 ölçümü).** Aynı deneyler v783 verisiyle, ardıllar olmadan ve ardıllarla koşulup makale sonuçlarıyla karşılaştırıldı ([dogrulama.md](dogrulama.md) bölüm 5):

| Grup | Tüm beyin eğimi, ardılsız | Tüm beyin eğimi, ardıllı | MN9 (şeker 200 Hz), ardılsız → ardıllı (makale: 94,9 Hz) |
|---|---|---|---|
| Suya duyarlı (kimlik değişimi yok) | 0,996–1,003 | 0,996–1,003 | — |
| Johnston organı | 0,999–1,002 | 0,998–1,002 | — |
| Şekere duyarlı | **0,954–0,979** | **0,997–1,002** | **88,0 → 92,4 Hz** |

**Kontrol deneyi.** Ardılsız durumda şeker yolunda sistematik %5–9'luk düşüş vardı. Bunun sürüm farkından değil eksik nörondan kaynaklandığını göstermek için makalenin kendi v630 verisinden yalnızca o şeker nöronu çıkarılıp 120 Hz uyarım koşuldu: aynı sapma elde edildi (eğim 0,953; MN9 75,0 → 70,8 Hz). Ardıllar eklendikten sonra sapma ortadan kalktı. Kimlik değişimi olmayan su grubunun her iki durumda da birebir eşleşmesi, v630 → v783 bağlantı düzeltmelerinin bu devrelerde etkisiz olduğunu gösterir.

### 4.4 Taraf (yarıküre) notu
Referans kod bu nöronlara "sağ yarıküre" der; v783 anotasyonlarında aynı nöronlar `side = left` görünür. Bu fark, FlyWire'ın erken sürümlerindeki ayna yönelimi düzeltmesinden kaynaklanır. Arayüzde taraf bilgisi **v783 anotasyonuna göre** gösterilir.

### 4.5 Bilinen sınırlılıklar
- **BPN** (Bidaye et al. 2020 [17], ileri yürüme) v783 anotasyonlarında tanımlı değildir; ileri yürüme yalnızca P9 (DNp09) ile okunur.
- **Dev lif (DNp01):** Sağ taraftaki nöronun nörotransmitter tahmini glutamattır (baskılayıcı işaret). Literatürde dev lif kolinerjik ve elektriksel sinapslıdır [11]. Okuma, dev lifin *kendi* ateşleme hızına dayandığı ve hedefleri (VNC) modelde olmadığı için bu hatanın davranış okumasına etkisi sınırlıdır.
- **Kötü koku ve CO₂:** Bu uyarımların çözümleyicide doğrudan davranış karşılığı yoktur; yalnızca devre aktivitesi gösterilir (yol haritası 3.1).

## 5. Yeniden üretim

```bash
uv run sinek indir          # indir, SHA-256 ile doğrula, özet raporu yazdır
uv run pytest -m veri       # bu belgedeki tüm sayıları doğrula
```
