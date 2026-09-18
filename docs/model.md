# Simülasyon Modeli

> **Faz 2 çıktısı** · Son güncelleme: 2026-09-17
> Uygulama: [`backend/sinek/simulation/lif.py`](../backend/sinek/simulation/lif.py) · Parametreler: [`params.py`](../backend/sinek/simulation/params.py)

Bu belge, projenin kullandığı tam beyin simülasyonunun matematiksel tanımını ve referans modelle birebir aynı davranması için gereken uygulama ayrıntılarını açıklar. Model, Shiu et al. (2024) [3] tarafından yayımlanan Brian2 modelinin PyTorch ile yeniden uygulamasıdır. Köşeli parantezli numaralar [yol haritası kaynakçasına](yol-haritasi.md#8-kaynakça-ve-ilgili-çalışmalar) karşılık gelir.

## 1. Nöron modeli

Her nöron bir **sızıntılı birleştir-ateşle (LIF)** birimidir. Zar potansiyeli `v` ve sinaptik iletkenlik benzeri girdi `g` şu denklemlerle değişir:

```
dv/dt = (v₀ − v + g) / τ_m
dg/dt = −g / τ_s
```

`v` eşiği (`v_th`) aştığında nöron spike atar, `v` sıfırlama potansiyeline (`v_rst`), `g` sıfıra döner ve nöron refrakter döneme girer.

### Parametreler

| Parametre | Değer | Anlam | Kaynak (referans kodundaki) |
|---|---|---|---|
| `v₀` | −52 mV | Dinlenim potansiyeli | Kakaria & de Bivort 2017 |
| `v_rst` | −52 mV | Sıfırlama potansiyeli | Kakaria & de Bivort 2017 |
| `v_th` | −45 mV | Ateşleme eşiği | Kakaria & de Bivort 2017 |
| `τ_m` | 20 ms | Zar zaman sabiti | Kakaria & de Bivort 2017 |
| `τ_s` | 5 ms | Sinaptik zaman sabiti | Jürgensen et al. 2021 |
| `t_rfc` | 2,2 ms | Refrakter dönem | Lazar et al. 2021 |
| `t_dly` | 1,8 ms | Sinaptik gecikme | Paul et al. 2015 |
| `w_syn` | 0,275 mV | Sinaps başına ağırlık (serbest parametre) | Shiu et al. 2024 [3] |
| `f_poi` | 250 | Poisson girdisi ağırlık çarpanı | Shiu et al. 2024 [3] |
| `dt` | 0,1 ms | Zaman adımı | Brian2 varsayılanı |
| Deneme | 30 × 1000 ms | Deney başına | Shiu et al. 2024 [3] |

### Sinaptik ağırlık
`i → j` bağlantısının ağırlığı `w = işaret(i) × sinaps_sayısı(i→j) × w_syn` değerindedir. İşaret, presinaptik nöronun nörotransmitterine göre belirlenir ([veri.md](veri.md) bölüm 3).

## 2. Sayısal çözüm

Denklemler doğrusaldır; her adımda **analitik (kesin) çözüm** kullanılır (Brian2 `method="linear"` ile aynı). `u = v − v₀` ve `a = g · τ_s / (τ_s − τ_m)` olmak üzere:

```
g(t + dt) = g · e^(−dt/τ_s)
u(t + dt) = (u − a) · e^(−dt/τ_m) + a · e^(−dt/τ_s)
```

Hesaplamalar varsayılan olarak **float64** hassasiyetinde yapılır.

## 3. Zaman adımı çizelgesi

Referansla birebir aynı spike zamanlarını elde etmek için, her zaman adımındaki işlemlerin sırası Brian2'nin çizelgesiyle (`groups → thresholds → synapses → resets`) aynı olmalıdır. Bu sıra Brian2 kaynak kodundan doğrulanmıştır.

| # | Aşama | İşlem |
|---|---|---|
| 1 | Durum güncellemesi | `not_refractory = (adım − son_spike_adımı) ≥ refrakter_adımı`; refrakter olmayanlarda `v` ve `g` analitik ilerletilir |
| 2 | Eşik | `spike = (v > v_th) ∧ not_refractory`; spike atanlar refrakter olur |
| 3 | Sinapslar | 18 adım (1,8 ms) önce atılan spike'lar `g += w` olarak iletilir; Poisson girdisi `v += w_syn × f_poi` olarak eklenir |
| 4 | Sıfırlama | Spike atanlarda `v = v_rst`, `g = 0` |

### Kritik ayrıntılar
Bu ayrıntılar belgelenmiş değildir; Brian2 kaynak kodundan çıkarılmış ve birebir denklik testleriyle doğrulanmıştır.

1. **Refrakter dönemde gelen girdiler yok sayılır.** Brian2, `(unless refractory)` işaretli değişkenlere yapılan tüm yazmaları (sinaptik `g += w` ve Poisson `v += …` dahil) nöron refrakterken uygulamaz ("conditional write"). Bu kural uygulanmazsa yoğun aktivitede spike zamanları referanstan ayrışır.
2. **Aynı adımda spike atan nöron girdiyi kaçırır.** Eşik aşamasında spike atan nöron refrakter olur; aynı adımın sinaps aşamasındaki girdiler ona uygulanmaz ve sıfırlama `g`'yi yine sıfırlar.
3. **Poisson hedeflerinin refrakter dönemi yoktur.** Referans kod, uyarılan nöronların refrakter süresini 0 yapar (frekans 0 Hz olsa bile).
4. **Adım yuvarlaması.** Süreler Brian2'nin `timestep(t, dt) = ⌊(t + 10⁻³·dt) / dt⌋` kuralıyla adıma çevrilir (1,8 ms → 18 adım, 2,2 ms → 22 adım).

## 4. Uyarım ve susturma

- **Uyarım (optogenetik aktivasyon modeli):** Seçilen her nörona bağımsız bir Poisson süreci eklenir. Her adımda `p = frekans × dt` olasılıkla `v`'ye 68,75 mV (`w_syn × f_poi`) eklenir; bu, nöronu bir sonraki adımda ateşlemeye yeterlidir. Uyarılan nöronun ateşleme hızı bu nedenle uyarım frekansına çok yakındır.
- **Susturma:** Susturulan nöronun **çıkış** sinapslarının ağırlığı sıfırlanır. Referans README'si susturmayı "giriş ve çıkış bağlantılarının sıfırlanması" olarak tanımlasa da referans kod (`syn.w['{i} == i'] = 0`) yalnızca çıkış bağlantılarını sıfırlar; bu proje **kodu** izler. Susturulan nöron hâlâ ateşleyebilir ama hiçbir nöronu etkilemez.

## 5. Çıktı

- **Ateşleme hızı:** Deneme başına spike sayısı / deneme süresi; 30 denemenin ortalaması.
- **Standart sapma:** Denemeler arası, `ddof = 0` (referansla aynı tanım).
- **Tekrarlanabilirlik:** Aynı tohum, aynı cihaz türü ve aynı yazılım sürümüyle sonuçlar birebir aynıdır.

## 6. Performans

Tüm denemeler tek bir toplu tensörde paralel çalışır. Spike iletimi olay tabanlıdır: yalnızca o adımda gecikmesi dolan spike'ların çıkış bağlantıları işlenir.

| Donanım | Deney (30 × 1000 ms, tam beyin) | Bellek |
|---|---|---|
| NVIDIA RTX 4060 Laptop (8 GB) | ≈ 80 sn | 0,63 GB |
| 16 iş parçacıklı dizüstü işlemci (ekran kartı yok) | ≈ 8,5 dk | — |

**Değerlendirilip reddedilen optimizasyon (2026-09-17).** Profil çıkarıldığında GPU süresinin çoğunun yoğun eleman bazlı işlemlerde (her adımda 30 × 138.639 değer üzerinde 7–8 ayrı çekirdek) geçtiği görüldü.
- `torch.compile`: Windows'ta ayrı bir C derleyicisi gerektirdiği için kullanıcı kurulumunu ağırlaştırır; elendi.
- PyTorch jiterator (NVRTC) ile tek çekirdekte birleştirme: yoğun kısmı 3,3×, toplam adımı ≈1,65× hızlandırır. Ancak NVRTC çarpma-toplamaları birleştirdiği (FMA) için zar potansiyeli değerlerinin %7,6'sı referans aritmetikten en fazla 1,4×10⁻¹⁴ mV sapar. Mevcut CPU ve GPU yolları Brian2/numpy aritmetiğiyle **bit düzeyinde aynıdır**; bu özelliği korumak için birleştirme uygulanmadı.

## 7. Doğrulama

- **Birebir denklik:** Rastgelelik içermeyen ağlarda spike zamanları Brian2 referans modeliyle birebir aynıdır (4 ağ rejimi + susturma); Poisson uyarımı istatistiksel olarak uyumludur. Testler: [`backend/tests/simulation/`](../backend/tests/simulation/).
- **Yayınlanmış sonuçlar:** [dogrulama.md](dogrulama.md).
