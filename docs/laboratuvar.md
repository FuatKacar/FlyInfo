# Laboratuvar

> **Faz 6 çıktısı** · Son güncelleme: 2026-09-18
> Uygulama: [`backend/sinek/lab/`](../backend/sinek/lab/) · Arayüz: [`frontend/src/lab/`](../frontend/src/lab/)

Laboratuvar sekmesi simülasyonla doğrudan çalışır: metin sınıflandırıcı ve dil modeli katmanları devre dışıdır. Köşeli parantezli numaralar [yol haritası kaynakçasına](yol-haritasi.md#8-kaynakça-ve-ilgili-çalışmalar) karşılık gelir.

## 1. Nöron seçimi

| Tür | Tanım |
|---|---|
| Hazır grup | `neuron_groups.toml` içindeki uyarım ve okuma grupları |
| Hücre tipi | FlyWire anotasyonundaki `cell_type` (ör. `LB3` şeker tat nöronları, `DNp01` dev lif; reseptör geni adları — ör. Gr5a — hücre tipi değildir); arama yalnızca modeldeki nöronları sayar |
| Nörotransmitter | Anotasyondaki `top_nt` tahmini (ör. tüm GABA nöronları) |
| Beyin bölgesi | Çıkış sinapslarının çoğunluğu o nöropilde olan nöronlar |
| Nöron kimlikleri | Tek tek FlyWire kimlikleri (en fazla 500) |

Boş seçim hata sayılır; modelde bulunmayan kimlikler rapora uyarı olarak yazılır. FlyWire kimlikleri 2⁵³'ten büyük olduğu için API ve raporlarda **metin** olarak taşınır (JavaScript tam sayıları bu büyüklükte bozar).

## 2. Deney ve karşılaştırma

- **Uyarım:** seçilen nöronlara Poisson girdisi, 1–400 Hz.
- **Susturma:** seçilen nöronların çıkış sinapsları sıfırlanır (referans kodun yöntemi, [3]).
- Susturma varsa **kontrol** (susturmasız) ve **deney** koşulları **aynı tohumla** koşulur; iki sonuç arasındaki fark yalnızca susturmadan gelir.
- Her davranış için deneme başına okuma hızları **Welch t testiyle** karşılaştırılır (p < 0,05 anlamlı).
- Nöronların %5'inden fazlası susturulursa sonuçların fizyolojik olmayabileceği uyarısı eklenir.
- **Okuma nöronunun kendisi susturulursa** uyarı verilir: susturma yalnızca çıkış bağlantılarını kapattığı için nöronun kendi ateşlemesi ölçülmeye devam eder (ör. MN9 susturulunca MN9 okuması 82,5 → 80,0 Hz). Davranışı engellemek için ona girdi veren nöronlar susturulmalıdır.
- Deneyler arka plan işi olarak çalışır; arayüz ilerlemeyi gösterir. Aynı anda tek deney çalışır.

## 3. Sinyal yolu izleme

Kenar payı: `sinaps(u→v) × hız(u) / Σ_w sinaps(w→v) × hız(w)` — u'nun v'ye gelen sinaptik olaylar içindeki payı. Yol gücü kenar paylarının çarpımıdır; yolun işareti kenar işaretlerinin çarpımıdır. Arama, hedef okuma nöronundan geriye doğru ışın aramasıyla yapılır (en fazla 4 adım). Hiç ateşlemeyen nöronlar yola girmez.

**Sınırlılık:** Yollar yapısal ve korelasyonel bir özettir, nedensellik kanıtı değildir. Bu not arayüzde yolların yanında her zaman gösterilir; nedensellik için susturma deneyi önerilir.

## 4. Deney raporu

Tek JSON dosyası: istek (uyarımlar, susturmalar, parametreler, tohum), çözümlenmiş nöron kimlikleri, sonuçlar ve kaynak dosya / nöron grubu tanımları / kalibrasyon SHA-256 özetleri. Rapor geri yüklendiğinde deney aynı tohumla yeniden koşulur ve davranış okumaları karşılaştırılır:

- Aynı donanımda sonuçlar **birebir** aynıdır.
- Farklı donanımda (ekran kartı ↔ işlemci) toplama sırası farklı olabileceğinden kayan nokta düzeyinde küçük farklar oluşabilir; bu durumda en büyük fark bildirilir.
- Veri veya tanım özetleri rapordan farklıysa kullanıcı uyarılır.

## 5. Makaledeki susturma deneyinin yeniden üretimi (kabul ölçütü)

Shiu et al. (2024) şekil 1F [3]: şekere duyarlı GRN'ler 100 Hz ile uyarılırken tek bir ara nöron (v630 kimliği `720575940623211725`, hücre tipi **CB0553**) susturulur ve MN9 yanıtı ölçülür. Deney Laboratuvar arayüzünden, varsayılan parametrelerle (30 deneme × 1000 ms, tohum 0) koşuldu:

| | Kontrol (Hz) | Susturma (Hz) | Değişim | p |
|---|---|---|---|---|
| Makale (v630, arşivlenmiş sonuç) | 67,0 | 49,0 | −27 % | — |
| Doğrulama raporumuz (v783) | 67,7 | 48,7 | −28 % | — |
| **Laboratuvar (v783, arayüzden)** | **66,9** | **49,4** | **−26 %** | 1,5 × 10⁻²¹ |

Aynı deneyde sinyal yolu analizi, beslenme okuma nöronuna (MN9, CB0701) giden en güçlü üç yolun **üçünün de CB0553'ten geçtiğini** gösterdi (ör. LB3 → CB0616 → CB0553 → CB0701). Yol analizi (korelasyonel) ile susturma deneyi (nedensel) aynı nöronu işaret eder.

Deney süresi: ~160 sn (iki koşul, RTX 4060 Laptop).
