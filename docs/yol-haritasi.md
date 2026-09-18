# FlyInfo — Proje Yol Haritası

> **Durum:** Taslak v5 · **Güncelleme:** 2026-09-17
> **Kapsam:** MVP (araştırma odaklı, Türkçe, açık kaynak, yerelde çalıştırılabilir)

---

## 0. Dil Politikası ve Terimler Sözlüğü

### 0.1 Dil politikası
| Alan | Dil | Gerekçe |
|---|---|---|
| Kullanıcı arayüzü, sohbet yanıtları, hata mesajları | **%100 Türkçe** | Projenin temel hedefi |
| Belgeler (yol haritası, metodoloji, doğrulama raporu) | **Türkçe** | Hedef kitle |
| README | **Türkçe** + İngilizce özet bölümü | Uluslararası araştırmacıların projeyi bulabilmesi ve atıf yapabilmesi |
| Kod (değişken, fonksiyon, dosya adları), JSON anahtarları, API yolları | **İngilizce, ASCII** | Açık kaynak standardı; Türkçe karakterlerin platformlar arası sorun çıkarmaması; bilimsel kütüphanelerle tutarlılık |
| Kod yorumları ve commit mesajları | **Türkçe** | Katkıcı kitlesiyle tutarlılık |

Kullanıcıya görünen tüm metinler kodun içine gömülmez. Tek bir Türkçe metin dosyasında (`tr.json`) toplanır.

### 0.2 Terimler sözlüğü
Bilimsel literatürde yerleşik terimler İngilizce karşılıklarıyla birlikte kullanılır. Arayüzde de bu sözlük gösterilir.

| Türkçe terim | İngilizce karşılığı | Açıklama |
|---|---|---|
| Bağlantı haritası (konektom) | Connectome | Tüm nöronların ve aralarındaki sinapsların haritası |
| Sızıntılı birleştir-ateşle modeli | Leaky integrate-and-fire (LIF) | Nöronun zarda yük biriktirip eşikte ateşlediği basit model |
| İnen nöron | Descending neuron (DN) | Beyinden vücuda (sinir kordonuna) komut taşıyan nöron |
| Tat alıcı nöron | Gustatory receptor neuron (GRN) | Tat duyusunu algılayan duyusal nöron |
| Koku alıcı nöron | Olfactory receptor neuron (ORN) | Koku duyusunu algılayan duyusal nöron |
| Nöropil | Neuropil | Beyindeki sinaps yoğun anatomik bölge |
| Ateşleme hızı | Firing rate | Nöronun saniyedeki aksiyon potansiyeli sayısı (Hz) |
| Çözümleyici | Decoder | Nöral aktiviteden davranış okuyan katman |
| Vektör temsili | Embedding | Metnin anlamını sayısal vektöre dönüştürme |
| Susturma deneyi | Silencing / ablation | Bir nöron grubunun modelden çıkarılması |
| Sinyal yolu | Signaling pathway | Uyarının nöronlar arasında izlediği bağlantı zinciri |
| Kontrol deneyi | Control condition | Değişiklik yapılmamış, karşılaştırma için kullanılan koşul |
| Önceden hesaplanmış veri paketi | Precomputed artifact | Simülasyon çıktılarını içeren sürümlü dosya |

---

## 1. Amaç ve Kapsam

### 1.1 Problem tanımı
*Drosophila melanogaster*'ın (meyve sineği) tam beyin konektomu artık kamuya açık. Bu veri üzerinde çalışan simülasyonlar mevcut; ancak Türkçe, açık kaynak ve **bilimsel olarak şeffaf** bir etkileşimli arayüz bulunmuyor.

### 1.2 Hedef
Kullanıcının Türkçe yazdığı mesajı sineğin gerçek duyusal nöronlarına uygulanan bir **uyarım senaryosuna** çeviren, bu uyarımın konektom üzerinde nasıl yayıldığını simüle eden ve sonucu **davranışsal çıktı** (beslenme, kaçış, temizlenme vb.) olarak gösteren bir web uygulaması. Uygulama iki sekmeden oluşur:
- **Sohbet:** Meraklı kullanıcılar için metin tabanlı etkileşim.
- **Laboratuvar:** Araştırmacılar ve ileri kullanıcılar için doğrudan nöron uyarımı, susturma deneyleri, sinyal yolu izleme ve tekrarlanabilir deney raporları.

Uygulama GitHub üzerinden açık kaynak dağıtılır ve kullanıcının kendi bilgisayarında çalışır. Merkezi bir sunucu barındırılmaz.

### 1.3 Temel ilkeler
1. **Bilimsel şeffaflık.** Sinek dil anlamaz. Uygulama bir *sohbet* değil, **metin → duyusal uyarım → nöral simülasyon → davranış okuması** zinciridir. Her katmanın niteliği arayüzde açıkça etiketlenir:

   | Katman | Niteliği |
   |---|---|
   | Metin → uyarım eşlemesi | **Tasarım kararı** (bilimsel karşılığı sınırlı) |
   | Konektom simülasyonu | **Hesaplamalı model** (yayınlanmış yönteme dayalı, doğrulanmış) |
   | Davranış çözümleyicisi | **Deterministik okuma** (literatürde nedensel olarak gösterilmiş nöronlar) |
   | Doğal dil yanıtı | **Sunum katmanı** (LLM, yorum katmaz) |

2. **Kalite önceliklidir.** Dağıtım kolaylığı, indirme boyutu veya hesaplama maliyeti hiçbir koşulda bilimsel kaliteyi sınırlamaz.
3. **Tekrarlanabilirlik.** Aynı girdi, aynı sürüm ve aynı tohum (seed) her makinede aynı sonucu üretir.

### 1.4 Kapsam dışı (MVP)
- Biyofiziksel (Hodgkin-Huxley, kompartmanlı) nöron modelleri
- Plastisite / öğrenme
- Tam 3B beyin görselleştirmesi
- Ventral sinir kordonu (VNC) ve gerçek motor kinematiği

---

## 2. Veri Kaynakları

| Kaynak | İçerik | Kullanım |
|---|---|---|
| **FlyWire FAFB v783** [1] | Dişi yetişkin tam beyin (optik loblar dahil): 139.255 nöron, ~5×10⁷ kimyasal sinaps | Ana konektom |
| **FlyWire anotasyonları** [2], [5]: `flyconnectome/flywire_annotations` | Hücre tipleri, süper sınıflar, hemilineage; optik lob tipleri | Duyusal ve inen nöronların seçimi |
| **Nörotransmitter tahminleri** [4] | Nöron başına ACh / GABA / Glu / 5-HT / DA / OA olasılıkları | Sinaps işareti (uyarıcı / baskılayıcı) |
| **Tam beyin LIF modeli** [3]: `philshiu/Drosophila_brain_model` | Model, parametreler, v783 desteği, uyarım ve susturma kodu | Simülasyon modeli ve doğrulama referansı |
| MaleCNS v1.0 [7] (Janelia / Cambridge / MRC LMB / Google) | Erkek beyin + VNC, 166 binden fazla nöron | **Faz 8**: motor çıktı genişletmesi için değerlendirilecek |

**Yardımcı araçlar:** `fafbseg-py`, `navis`, FlyWire Codex (veri indirme), `sjcabs/fly_connectome_data_tutorial` (öğretici).

**Lisans:** FlyWire verileri CC-BY 4.0 lisanslıdır. İlgili makalelere atıf arayüzde, README'de ve `CITATION.cff` dosyasında yer alır.

> **Neden MaleCNS değil FlyWire?** Tam beyin konektomu, nörotransmitter tahminleri ve yayınlanıp doğrulanmış bir simülasyon modeli aynı veri setinde hazır. Bu, sonuçların literatürle karşılaştırılabilmesini sağlar.
>
> **Sürüm notu:** Referans model deposu FlyWire v783'ü destekler. Makaledeki sonuçlar önceki bir sürümle üretildiyse, sürüm farkının doğrulama sonuçlarına etkisi Faz 2'de raporlanır.

---

## 3. Sistem Mimarisi

```
┌────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌───────────────┐
│ Türkçe     │ → │ 1. Girdi eşleme  │ → │ 2. Simülasyon    │ → │ 3. Çözümleyici   │ → │ 4. Sunum      │
│ mesaj      │   │ metin → uyarım   │   │ LIF, tam beyin   │   │ DN aktivitesi →  │   │ LLM: JSON →   │
│            │   │ vektörü          │   │ (hazır / canlı)  │   │ davranış skoru   │   │ Türkçe metin  │
└────────────┘   └──────────────────┘   └──────────────────┘   └──────────────────┘   └───────────────┘
                          │                      │                       │                    │
                          └──────────────────────┴───── Arayüzde her ara çıktı görünür ───────┘
```

### 3.1 Katman 1 — Girdi eşleme (metin → duyusal uyarım)
- Mesaj sabit bir **uyarım kategorisi** kümesine sınıflandırılır. Çoklu etiket ve yoğunluk (0–1) desteklenir.
- **Sınıflandırıcı (sürüm 2):** Türkçe dilbilgisine duyarlı, deterministik kural katmanı: karakter katlama, ek ve ünsüz yumuşaması eşleşmesi, yazım hatası toleransı, yan cümle bazında olumsuzluk, soru/gelecek/koşul algılama, mecaz ve konu filtreleri. Her karar kanıt kaydıyla açıklanır; LLM veya ek model kullanılmaz. Vektör temsili modelleri (bge-m3, multilingual-e5-large) değerlendirildi; tek başına makro F1 ≈ 0,70, yedek katman olarak da doğruluğu düşürdüğü için kullanılmadı. Mühürlü test setinde makro F1 **0,879** ([siniflandirma.md](siniflandirma.md)).
- **Kapsam dışı algılama:** Hiçbir kategoriye yeterince benzemeyen mesajlar (ör. "2+2 kaç?") "nötr" olarak işaretlenir ve kullanıcıya nedeni gösterilir.
- **Başlangıç eşlemesi.** Hücre tipleri anotasyon verisinden Faz 1'de doğrulanır. Çözümleyicide doğrudan karşılığı olmayan kategorilerde yalnızca devre ve bölge aktivasyonu gösterilir, davranış iddia edilmez.

| Kategori | Uyarılan nöron grubu | Literatürdeki davranış | Çözümleyici karşılığı | Kaynak |
|---|---|---|---|---|
| Tatlı / yiyecek | Şekere duyarlı GRN'ler (Gr5a+) | Hortum uzatma | MN9 ✅ | [8], [3] |
| Acı / zehir | Acıya duyarlı GRN'ler (Gr66a+) | Beslenmenin baskılanması | MN9 baskılanması ✅ | [8], [6], [3] |
| Su | Suya duyarlı GRN'ler (ppk28+) | Hortum uzatma | MN9 ✅ | [9], [3] |
| Dokunma / anten uyarımı | Johnston organı mekanosensörleri | Anten temizleme | aDN1, aDN2 ✅ | [10], [3] |
| Tehdit / yaklaşan nesne | Yaklaşma algılayan görsel projeksiyon nöronları (LC4, LPLC2) | Kaçış | Dev lif (DNp01) ✅ | [11], [12], [13] |
| Kötü koku | Geosmin ORN'leri (Or56a → DA2) | Kaçınma | Devre aktivitesi (lateral horn) ⚠️ | [14] |
| CO₂ | Gr21a/Gr63a nöronları (V glomerülü) | Kaçınma | Devre aktivitesi ⚠️ | [15] |
| Nötr / kapsam dışı | Uyarım yok (kontrol) | — | Aktivite yok | — |

Köşeli parantezli numaralar Bölüm 8'deki kaynakçaya karşılık gelir.

### 3.2 Katman 2 — Simülasyon
- **Model:** LIF, tam beyin, Shiu et al. 2024 parametreleri.
- **Bağlantı matrisi:** Sinaps sayısı × işaret (ACh → +, GABA/Glu → −). Seyrek (CSR) formatta tutulur.
- **Uyarım:** Seçilen nöronlara Poisson dağılımlı spike girdisi (frekans = yoğunluk × f_max; f_max referans çalışmadan alınır).
- **Çıktı:** Nöron başına ateşleme hızı (Hz). Senaryo başına çoklu deneme ortalaması ve standart sapma. Deneme sayısı ve süresi referans çalışmayla aynıdır.
- **Tekrarlanabilirlik:** Sabit rastgele tohum, deterministik hesaplama modu, sürümlü parametre dosyası.
- **İki çalışma modu:**
  1. **Hazır senaryolar:** Kategori × yoğunluk (ör. 8 × 5) ve tüm ikili kategori kombinasyonları önceden simüle edilir, Parquet formatında saklanır.
  2. **Canlı simülasyon:** Hazırda bulunmayan bir senaryo istendiğinde aynı LIF modeli kullanıcının bilgisayarında çalıştırılır (GPU varsa GPU, yoksa CPU; ilerleme çubuğuyla). Sonuç yerel önbelleğe yazılır.

  Yaklaşık veya basitleştirilmiş bir model **kullanılmaz**. Kullanıcıya her zaman gerçek LIF sonucu gösterilir.

### 3.3 Katman 3 — Deterministik çözümleyici
- Okuma, **inen nöronlar (DN)** ve seçili motor nöronlar üzerinden yapılır. Bunlar davranışla nedensel ilişkisi deneysel olarak gösterilmiş nöronlardır. Her satırın kaynağı arayüzde atıf olarak gösterilir:

| Davranış | Okunan nöron(lar) | Kaynak |
|---|---|---|
| Beslenme / hortum uzatma | MN9 (motor nöron; FlyWire tipi CB0701) | [6], [3] |
| Kaçış | Dev lif (giant fiber, DNp01) | [11], [12] |
| Anten temizleme | aDN1 (DNg62), aDN2 (DNge078) | [10], [3] |
| Geri yürüme | Moonwalker DN (MDN) | [16], [18] |
| İleri yürüme | P9 (DNp09). BPN v783 anotasyonlarında tanımlı olmadığından okunmaz | [17] |

FlyWire hücre tipi eşleşmeleri Faz 1'de doğrulanmıştır; ayrıntılar ve bilinen sınırlılıklar: [docs/veri.md](veri.md).

- **Skor:** Ham ateşleme hızı (Hz) her zaman gösterilir. Normalize skor (`0–1`) = ateşleme hızı / kalibrasyon senaryosundaki referans maksimum. Önceden tanımlı eşik aşılınca davranış etiketi atanır. Eşikler ve kalibrasyon [cozumleyici.md](cozumleyici.md)'de belgelenir.
- **Ek çıktılar:** En aktif 10 ara nöron tipi, nöropil bazında aktivasyon özeti.
- **Çıktı sözleşmesi (örnek):** JSON anahtarları İngilizce, kullanıcıya gösterilen etiketler `tr.json`'dan gelir.
  ```json
  {
    "stimulus": {"category": "sweet", "intensity": 0.75, "neuron_count": 42, "match_score": 0.91},
    "behaviors": {
      "feeding": {"rate_hz": 38.2, "score": 0.82, "active": true},
      "escape": {"rate_hz": 0.0, "score": 0.0, "active": false}
    },
    "top_neuropils": {"GNG": 0.71, "PRW": 0.52},
    "model": {"type": "LIF", "dataset": "FlyWire v783", "mode": "precomputed", "seed": 42, "version": "1.0.0"}
  }
  ```

### 3.4 Katman 4 — Sunum (LLM)
- LLM **yalnızca** Katman 3'ün JSON çıktısını Türkçe, okunabilir bir metne çevirir. Kullanıcının ham mesajı LLM'e gönderilmez.
- **Kısıtlar:** JSON'da olmayan bilgi eklenmez, duygu veya niyet atfedilmez ("sinek mutlu" gibi ifadeler yasak), sayısal değerler korunur.
- **Otomatik doğrulama:** Üretilen metindeki sayılar ve davranış adları JSON ile karşılaştırılır. Uyuşmazlık varsa metin reddedilir ve şablon metin gösterilir.
- Arayüzde "Bilimsel çıktı" (grafik ve ham JSON) ile "Sunum katmanı" (LLM metni) ayrı etiketlerle yan yana gösterilir.
- **API anahtarı zorunlu değildir.** Anahtar yoksa uygulama şablon metinle eksiksiz çalışır. Her kullanıcı kendi anahtarını kullanır.
- **Sağlayıcılar** soyut bir arayüz sınıfı üzerinden `.env` dosyasında seçilir:
  - **Birincil:** Google Gemini API, `gemini-3.8-flash` (`gemini-3.5-flash-lite` yalnızca kota yedeği; 2026-09-17'de resmi model listesinden güncellendi)
  - **Yedek:** Groq
  - **Çevrimdışı (opsiyonel):** Ollama
  - **Son çare:** Şablon tabanlı Türkçe metin
- **Önbellek:** LLM yanıtları senaryo anahtarına göre yerel olarak önbelleğe alınır.

### 3.5 Arayüz yapısı

İki sekme aynı simülasyon ve çözümleyici çekirdeğini kullanır. Aralarındaki fark yalnızca girdinin nasıl verildiği ve sonucun ne kadar ayrıntılı gösterildiğidir.

```
┌─────────────────────────────────────────────────────────────┐
│  [ Sohbet ]  [ Laboratuvar ]                     [ Sözlük ] │
├─────────────────────────────────────────────────────────────┤
│  Sohbet:      metin → Katman 1 → 2 → 3 → 4 → sohbet balonu  │
│  Laboratuvar: doğrudan seçim ────→ 2 → 3 → ayrıntılı panel  │
└─────────────────────────────────────────────────────────────┘
```

#### Sekme 1 — Sohbet
- Mesaj kutusu ve sohbet geçmişi. Her yanıtta LLM metni gösterilir.
- Her yanıtın altında açılır bir **"Bu yanıt nasıl üretildi?"** paneli bulunur: algılanan kategori, uyarılan nöron sayısı, davranış grafiği, beyin şeması, ham JSON.
- Panelden tek tıkla **"Laboratuvarda aç"** seçilebilir. Aynı senaryo Laboratuvar'a taşınır ve orada ayrıntılı incelenir.
- **Kapsam dışı mesajlar:** Uyarım uygulanmadığı açıkça söylenir ve altında örnek mesajlarla kısa bir yönlendirme gösterilir ("Sana biraz bal getirdim", "Antenlerine üfledim"…). Yönlendirme simülasyonun parçası değildir; `tr.json`'daki arayüz metnidir.

#### Canlı beyin şeması (Sohbet ekranı)
Sohbet ekranının yanında sineğin beyni sürekli görünür: varsayılan olarak döndürülebilir **3B** model, isteğe bağlı **2B** önden izdüşüm. Mesaj gönderildiğinde uyarımın sonucu şema üzerinde bölge parlaklıkları olarak gösterilir.

> **Karar (2026-09-17):** Yayılımın zaman içinde oynatıldığı animasyon fikrinden **vazgeçildi**. Gerekçe: animasyon için 225 senaryonun 10 ms'lik zaman profiliyle yeniden hesaplanması gerekiyordu (ölçüm: ~5 saat ekran kartı) ve projeyi indiren her kullanıcı ya bu hesaplamayı yapacak ya da ek bir veri paketi indirecekti. Şema, denemenin 1 saniyelik ortalamasını gösterir ve yayılım sırası **uydurulmaz**.

| Öğe | Tanım |
|---|---|
| Görünüm | Varsayılan **3B**: nöropil yüzeyleri üç boyutlu çizilir, fareyle döndürülür. **2B**: aynı ağların önden izdüşümü (hafif seçenek, WebGL gerekmez) |
| Geometri | 78 FlyWire nöropilinin 3B ağlarından (FlyWire herkese açık deposu; JFRC2 yüzeyleri [19], [20]) önden ortografik izdüşüm, silüet ve Douglas–Peucker sadeleştirmesiyle üretilen SVG yolları (`sinek.schematic.build`, ≈ 39 KB). Ağ dosyaları SHA-256 ile sabitlenmiştir; bölüm numarası → ad eşlemesi köşe koordinatlarının birebir karşılaştırılmasıyla çıkarılmış ve geometrik testlerle (sol/sağ simetri, ön/arka, üst/alt) doğrulanmıştır. Sineğin sağı ekranın solundadır ve bu şemada yazılıdır |
| Parlaklık | Her nöropilin **sinaps ağırlıklı ortalama ateşleme hızı** (Hz) = sinaptik olay hızı / bölgenin çıkış sinapsı sayısı. Ham olay hızı yerine bu değer kullanılır, çünkü ham değer bölge büyüklüğüyle ölçeklenir ve GNG gibi büyük bölgeler her uyarımda en parlak görünürdü. Ölçek tüm senaryolarda sabit ve logaritmiktir: parlaklık = log₁₀(1 + hız / 0,5 Hz) / log₁₀(1 + 200 Hz / 0,5 Hz). Hazır senaryolarda gözlenen aralık: şekerde GNG 5,8 Hz, yaklaşmada PVLP 24 Hz, CO₂'de MB kaliks 152 Hz. Renk körlüğüne uygun tek renk tonu rampası |
| Zaman | Gösterilen değer 1 saniyelik denemenin ortalamasıdır (30 deneme). Zaman içindeki yayılım oynatılmaz; bkz. yukarıdaki karar |
| Davranış nöronları | Okuma nöronları (MN9, dev lif, aDN, MDN, P9) şemada hücre gövdesi (soma) konumlarında işaretlenir (FlyWire anotasyonları); etkinleştikleri anda ayrıca vurgulanır |
| Şeffaflık | Şemanın altında "Parlaklık: simüle edilmiş sinaptik aktivite (30 deneme ortalaması)" açıklaması; kapsam dışı mesajda şema sönük kalır; koku uyarımlarında geniş yayılma uyarısı |
| Erişilebilirlik | Hareket azaltma tercihinde geçişler kapatılır; en aktif bölgeler metin olarak da listelenir; 3B desteklenmeyen cihazlarda 2B görünüm |

#### Sekme 2 — Laboratuvar
Metin katmanı (Katman 1) ve LLM katmanı (Katman 4) devre dışıdır. Kullanıcı doğrudan simülasyonla çalışır.

**L1. Doğrudan uyarım**
- Nöron grupları üç şekilde seçilebilir: hazır kategori listesinden, hücre tipi aramasıyla (ör. `LB3`, `DNp01`) veya tek tek nöron ID'si girerek.
- Her grup için yoğunluk (Hz) ayrı ayarlanır. Birden çok grup aynı anda uyarılabilir.
- Simülasyon süresi, deneme sayısı ve tohum ayarlanabilir. Varsayılanlar referans çalışmanın değerleridir.

**L2. Susturma deneyleri**
- Seçilen nöron grupları modelden çıkarılır (çıkış sinapsları sıfırlanır).
- Susturma seçenekleri: hücre tipi, nörotransmitter türü (ör. tüm GABAerjik nöronlar), nöropil ya da tek nöron.
- Sonuç **kontrol ve deney karşılaştırması** olarak gösterilir: her davranış için susturma öncesi ve sonrası ateşleme hızı, fark ve istatistiksel anlamlılık (denemeler arası).
- Susturma deneyleri her zaman canlı simülasyonla çalışır. Hazır senaryo kullanılmaz.

**L3. Sinyal yolu izleme**
- Uyarılan nörondan seçilen çözümleyici nöronuna giden en etkili yollar hesaplanır.
- **Yöntem:** Yol ağırlığı = yol üzerindeki bağlantıların (sinaps sayısı × işaret) ve simülasyondaki presinaptik ateşleme hızlarının birleşimi. Yalnızca simülasyonda gerçekten aktif olan nöronlar hesaba katılır. En güçlü k yol listelenir.
- Katmanlı akış diyagramıyla gösterilir: duyusal nöron → ara nöronlar → DN. Uyarıcı ve baskılayıcı bağlantılar ayrı renklerle ayrılır.
- **Sınırlılık notu:** Yollar yapısal ve korelasyonel bir özettir, nedensellik kanıtı değildir. Nedensellik için L2 (susturma) önerilir. Bu not arayüzde yolların yanında gösterilir.

**L4. Deney raporu**
- Her deney tek bir `.json` rapor dosyası olarak dışa aktarılır: girdiler, susturmalar, tüm parametreler, tohum, kod ve veri sürümü, SHA-256 özetleri, sonuçlar.
- Rapor dosyası Laboratuvar'a **geri yüklenebilir**. Deney birebir tekrar koşulur ve sonuçların eşleştiği doğrulanır.
- İsteğe bağlı olarak grafikler PNG/SVG ve sonuç tabloları CSV olarak indirilebilir.

---

## 4. Teknoloji Yığını

| Alan | Teknoloji |
|---|---|
| Dil / ortam | Python 3.12, `uv` (paket ve ortam yönetimi) |
| Kod kalitesi | Ruff (lint + biçimlendirme), mypy (tip denetimi), pre-commit |
| Veri işleme | pandas, pyarrow (Parquet), SciPy (seyrek matris) |
| Simülasyon | PyTorch (CPU/GPU), NumPy |
| Girdi sınıflandırma | Kural tabanlı Türkçe sınıflandırıcı (ek bağımlılık yok) |
| Backend API | FastAPI, Pydantic, Uvicorn |
| LLM | `google-genai` (Gemini), Groq SDK; sağlayıcı soyutlamalı |
| Frontend | React 19 + TypeScript 5.9 + Vite 8; three.js (3B beyin); Biome (lint/biçim) |
| Görselleştirme | 3B beyin (three.js, WebGL) ve 2B SVG şema; grafikler elle yazılmış HTML/SVG (ek kütüphane yok) |
| Test | pytest, Vitest, Playwright (uçtan uca) |
| Dağıtım | GitHub (kaynak kod + Releases), `uv` ile tek komut |
| CI | GitHub Actions (Windows / macOS / Linux test matrisi) |

### Dizin yapısı
```
FlyInfo/
├── data/                 # indirilen ham veri (git dışı)
├── artifacts/            # önceden hesaplanmış senaryo paketi (git dışı)
├── cache/                # dil modeli yanıtları, canlı simülasyon ve Laboratuvar önbelleği (git dışı)
├── backend/
│   ├── sinek/            # Python paketi
│   │   ├── connectome/   # veri indirme/doğrulama, matris kurma, nöron grupları, nöropiller
│   │   ├── simulation/   # LIF modeli, senaryolar, önceden hesaplama, paket/canlı sonuç deposu
│   │   ├── validation/   # Shiu et al. 2024 deneylerinin yeniden üretimi ve raporu
│   │   ├── stimulus/     # Türkçe metin → uyarım sınıflandırıcı ve veri setleri
│   │   ├── decoder/      # okuma nöronları, davranış skorları, kalibrasyon
│   │   ├── presentation/ # şablon metin, dil modeli sağlayıcıları, doğrulayıcı
│   │   ├── chat/         # sohbet hattı (sınıflandırıcı → senaryo → çözümleyici → sunum)
│   │   ├── lab/          # seçim, susturma deneyi, sinyal yolları, raporlar, arka plan işleri
│   │   ├── schematic/    # beyin şeması geometrisi (2B ve 3B) üretimi
│   │   ├── api/          # FastAPI uç noktaları
│   │   ├── locales/tr.json   # kullanıcıya görünen tüm metinler (arayüz de buradan okur)
│   │   ├── config.py     # ortam ayarları
│   │   └── cli.py        # `sinek` komutu
│   └── tests/
├── frontend/             # React + TypeScript (derlenmiş hali backend/sinek/web'e yazılır)
│   ├── src/              # sohbet, beyin (2B/3B), laboratuvar, "Nasıl çalışıyor?"
│   ├── e2e/              # Playwright uçtan uca testleri
│   └── public/beyin-3b.bin   # 3B beyin geometrisi
├── scripts/              # kaynakça ve API şeması aktarımı, DOI doğrulaması, ilerleme izleme
├── docs/                 # yol haritası, veri, model, doğrulama, çözümleyici, sınıflandırma, laboratuvar
├── .github/workflows/    # CI ve haftalık kaynakça denetimi
├── .env.example          # LLM ayarları şablonu (anahtarlar isteğe bağlı)
├── LICENSE               # MIT (kod); veri lisansları README'de
└── README.md             # Türkçe + İngilizce özet
```

---

## 5. Dağıtım ve Yerel Kurulum Modeli

Proje barındırılan bir servis değil, **indirilip yerelde çalıştırılan** açık kaynak bir araçtır.

### Kurulum modları
| Mod | Hedef kitle | İndirilen | Süre (tahmini) |
|---|---|---|---|
| **Hızlı deneme** | Meraklı kullanıcılar | Tam moddaki işlem hattının ürettiği veri paketlerinin **eksiksiz** hali (tüm nöronların ateşleme hızları dahil) + nöron meta verisi + bağlantı matrisi (canlı simülasyon için) | Boyuta bağlı |
| **Tam yeniden üretim** | Araştırmacılar | Ham FlyWire verisi (GB mertebesi) + tüm simülasyonların yeniden koşulması | Saatler |

### İlkeler
- **Kalite önceliklidir:** Senaryo sayısı, deneme sayısı ve saklanan veri miktarı indirme boyutuna göre kısılmaz. İki mod birebir aynı sonuçları verir.
- **Sıfır zorunlu hesap/anahtar:** Hızlı deneme modu API anahtarı olmadan çalışır.
- **Tek bağımlılık Python:** Frontend derlenmiş statik dosyalar olarak dağıtılır ve FastAPI tarafından sunulur. Son kullanıcı için Node.js gerekmez.
- **Tek komut:** `uv run sinek` komutu veri yoksa indirir, sunucuyu başlatır ve tarayıcıyı açar.
- **Platform desteği:** Windows, macOS, Linux. CI matrisiyle doğrulanır.
- **Sürümleme:** Veri paketleri, kod sürümüyle eşleşen Release etiketleriyle yayınlanır. Manifest dosyasında veri seti sürümü, model parametreleri, tohum ve SHA-256 özetleri bulunur.
- **Lisans uyumu:** Türetilmiş veriler CC-BY 4.0 atıflarıyla birlikte dağıtılır.

---

## 6. Uygulama Fazları

### Faz 0 — Kurulum ✅ Tamamlandı (2026-09-17)
- Depo yapısı, `uv` ortamı, Ruff / mypy / pre-commit, pytest, CI iskeleti
- `.gitignore`, `.env.example`, `LICENSE`, README iskeleti
- **Çıktı:** Üç platformda CI'dan geçen boş iskelet.

### Faz 1 — Veri hattı ✅ Tamamlandı (2026-09-17)
- FlyWire v783 bağlantı tablosu, nöron anotasyonları ve nörotransmitter tahminlerinin indirilmesi
- İşaretli seyrek bağlantı matrisinin kurulması, nöron ID ↔ indeks eşlemesi
- Kategori → nöron ID listelerinin anotasyondan çıkarılması; çözümleyici nöronlarının ID'lerinin belirlenmesi
- **Kabul kriteri:** Nöron sayısı ve toplam sinaps sayısı yayınlanan değerlerle tutarlı. Her kategori ve her çözümleyici nöronu için boş olmayan, literatürle eşleşen ID listesi. **Sonuç:** 138.639 nöron, 15.091.983 bağlantı, 54.492.922 sinaps; 15 grubun tamamı çözümlendi; ayrıntılar [docs/veri.md](veri.md).

### Faz 2 — Simülasyon ve bilimsel doğrulama ⭐ ✅ Tamamlandı (2026-09-17)
- LIF modelinin uygulanması (Shiu et al. parametreleri)
- **Referans koda karşı doğrulama:** Aynı girdi ve parametrelerle `philshiu/Drosophila_brain_model` çıktısıyla istatistiksel karşılaştırma
- **Yayınlanmış sonuçların yeniden üretimi:**
  - Şekere duyarlı GRN uyarımı → MN9 aktivasyonu
  - Acı GRN eşzamanlı uyarımı → MN9 aktivasyonunun baskılanması
  - Johnston organı uyarımı → anten temizleme devresi aktivasyonu
- **Kabul kriteri:** Referans kodla ateşleme hızları istatistiksel olarak uyumlu. Üç sonuç da referansla nitel olarak tutarlı. Tüm sonuçlar grafiklerle `docs/dogrulama.md`'de raporlanmış. **Sonuç:** Deterministik ağlarda Brian2 ile spike zamanları birebir aynı; makalenin v630 verisiyle 22 deneyin tamamı başarılı (tüm beyin r = 0,9989–0,9998, eğim 0,998–1,004; Şekil 1D, 3A, 4A, 5B ve 1F susturma deneyleri). v630 → v783 kimliği değişen 3 referans nöronunun ardılları FlyWire CAVE ile belirlenip eklendi; ardılsız durumda şeker yolunda ölçülen %5–9'luk sapma (nedeni kontrol deneyiyle doğrulandı) ortadan kalktı ve v783 uygulaması da makale sonuçlarını yeniden üretiyor. Belgeler: [model.md](model.md), [dogrulama.md](dogrulama.md). Laboratuvar susturma doğrulaması (Faz 6 kabul kriteri) bu fazda önceden karşılandı.

### Faz 3 — Önceden hesaplama ve çözümleyici ✅ Tamamlandı
> **Durum (2026-09-18):** Tamamlandı. 225 senaryoluk paket hesaplandı (manifest ve SHA-256 özetleriyle); çözümleyici ve kalibrasyon belgelendi ([cozumleyici.md](cozumleyici.md)). Kabul testleri (`tests/simulation/test_package_real.py`): paketteki **225 senaryonun hepsi** çözümleyici sözleşmesine uyuyor; aynı senaryo ekran kartında **canlı** koşulduğunda paketle **bit düzeyinde aynı** sonucu veriyor (spike sayıları ve kareleri, parmak izi).

- Senaryo matrisinin toplu simülasyonu, manifest ve özetlerle saklanması
- DN tabanlı davranış çözümleyicisi, kalibrasyon ve eşiklerin belgelenmesi
- Canlı simülasyon modunun hazır senaryolarla aynı sonucu verdiğinin testi
- **Kabul kriteri:** Her senaryo için çıktı sözleşmesine uygun JSON. Çözümleyici birim testleri geçiyor. Aynı tohumla canlı ve hazır sonuçlar eşleşiyor.

### Faz 4 — Girdi sınıflandırıcı, API ve sunum katmanı ✅ Tamamlandı
> **Durum (2026-09-17):** Tamamlandı. Sınıflandırıcı mühürlü test setinde makro F1 0,879 (hedef ≥ 0,85 ✅). API uç noktaları: `POST /api/chat`, `POST /api/stimulate`, `GET /api/scenarios`, `GET /api/neurons/{cell_type}`. Hazır senaryolarda uçtan uca yanıt 8–20 ms (LLM hariç).
>
> **Sağlayıcı denemesi (gerçek anahtarla, 7 mesaj):** Gemini yanıtlarının tamamı doğrulayıcıdan geçti. Bir önceki turda model uydurma bir sayı yazmış, doğrulayıcı yakalamış ve şablon metne düşülmüştü — mekanizma amaçlandığı gibi çalışıyor. Yanıt süresi 4–35 sn (tamamı LLM gecikmesi; ücretsiz katman).
>
> **Denemede bulunup düzeltilenler:**
> - Doğrulayıcı yuvarlama farkını hata sayıyordu (değer %32,35, model "%32,3" yazınca reddediliyordu). Artık yazılan ondalık basamak sayısına göre hem yuvarlama hem kesme kabul edilir; uydurulan sayılar yine yakalanır.
> - Yoğunluk değerleri (0,6 gibi) izinli sayılar arasında değildi; eklendi.
> - Model uyarıcıyı İngilizce adıyla ("looming") yazıyordu. Uyarım bileşenine `name_tr` alanı eklendi ve sistem istemi bu adı kullanmayı zorunlu kılıyor (istem sürümü 2).
> - `gemini-3.8-flash` ücretsiz katmanda sık sık 503 (meşgul) döndürüyor. Sağlayıcılara geçici hatalar için kısa aralıklı yeniden deneme eklendi (1 sn, 3 sn); kalıcı hatalarda (ör. 401) hemen yedeğe geçilir. Hata metinleri API anahtarını içermez (test edilir).

- Elle etiketlenmiş Türkçe test seti (≥300 örnek; günlük dil, argo, yazım hataları ve kapsam dışı mesajlar dahil)
- Vektör temsili modellerinin karşılaştırılması ve seçimi (sonuç: kural tabanlı sınıflandırıcı seçildi)
- FastAPI uç noktaları: `POST /api/chat`, `POST /api/stimulate`, `GET /api/scenarios`, `GET /api/neurons/{cell_type}` ✅
- LLM sağlayıcıları, çıktı doğrulayıcı, şablon metinler
- **Kabul kriteri:** Test setinde makro F1 ≥ 0,85, sınıf bazında sonuçlar raporlanmış. LLM doğrulayıcı test setinde uydurma içeriği yakalıyor. Hazır senaryolarda uçtan uca yanıt < 2 sn (LLM hariç).

### Faz 5 — Sohbet sekmesi (frontend) ✅ Tamamlandı
> **Düzeltilen ciddi hata (2026-09-17):** Proje adı değişikliğinde `neuron_groups.toml` dosyasındaki
> yorum satırı güncellenince hazır senaryo paketi geçersiz sayıldı (bütünlük denetimi dosyanın ham
> SHA-256'sını karşılaştırıyordu) ve **her mesaj sessizce canlı simülasyona düştü**: yanıtlar 13 ms
> yerine ~3 dakika sürdü. Alınan önlemler:
> - Bütünlük denetimi artık **ayrıştırılmış tanımların** özetini karşılaştırır; yorum ve biçim
>   değişiklikleri paketi geçersiz kılmaz, gerçek tanım değişiklikleri kılar (testlerle sabitlendi).
> - Paket kullanılamıyorsa arayüzde uyarı gösterilir; sessiz yavaşlama olmaz.
> - Sunum katmanına toplam süre bütçesi (45 sn) ve Gemini çağrılarına 25 sn zaman aşımı eklendi;
>   yeniden deneme yalnızca hızlı başarısızlıklarda yapılır (zaman aşımına uğrayan çağrı
>   tekrarlanmaz).
> - Bekleme kutusunda geçen süre saniye olarak gösterilir.
> **Durum (2026-09-17):** Tamamlananlar:
> - **Uygulama kabuğu:** sekmeler (klavyeyle gezinme), açık/koyu/sistem teması. Tüm arayüz metinleri arka uçtaki `tr.json` dosyasından gelir.
> - **Sohbet ekranı:** "Bu yanıt nasıl üretildi?" paneli (dört katman, davranış grafiği, ham JSON), kapsam dışı yönlendirmesi ve nedeni, hata ve tekrar deneme.
> - **Beyin şeması:** geometri üretim betiği, sabit logaritmik parlaklık ölçeği, en etkin bölgelerin metin listesi, davranış nöronu vurgusu, koku uyarımları için sınırlılık notu.
> - **3B görünüm (varsayılan):** aynı FlyWire nöropil ağlarının üç boyutlu hali (three.js, 1,7 MB ikili dosya: int16 köşeler + uint32 üçgenler). Fareyle döndürülür ve yakınlaştırılır; bölge üzerine gelince ad ve hız gösterilir. three.js yalnızca 3B açıldığında indirilir; sahne boşta çizim yapmaz (yalnızca kamera ya da veri değişince çizilir). WebGL yoksa 2B şemaya düşülür ve bu kullanıcıya söylenir. Seçim tarayıcıda saklanır.
> - **"Nasıl çalışıyor?" sayfası:** yöntem, sınırlılıklar, terimler; kaynakça `kaynakca.bib` dosyasından üretilir.
> - **Dağıtım:** Derlenmiş arayüz FastAPI tarafından sunulur; son kullanıcı Node.js kurmaz. API tipleri OpenAPI şemasından otomatik üretilir; CI şemanın ve tiplerin güncelliğini denetler.
> - **Testler:** Vitest bileşen testleri ve Playwright uçtan uca testleri (masaüstü + mobil; 3B görünüm dahil).
>
> **Zaman profili animasyonu (iptal, 2026-09-17):** Kayıt altyapısı yazıldı, ölçüldü (kayıt hız kaybı %0,1; spike sayıları birebir aynı) ve 68/225 senaryo hesaplandı. Animasyonun kullanıcı başına ~5 saatlik ekran kartı hesabı ya da ek veri paketi gerektirmesi nedeniyle **vazgeçildi**; ilgili kod ve komut depodan kaldırıldı (kullanılmayan kod bırakılmaz). Şema 1 saniyelik ortalamayı gösterir.
>
> **Tasarım kararları:**
> - Bölgeler arkadan öne, opak renklerle çizilir. Önden izdüşümde bölgeler üst üste biner; yarı saydam renkler toplanınca zayıf uyarımda bile tüm beyin parlak görünüyordu (ölçülmüş yanıltıcı görüntü).
> - Bulanık ışıma katmanı kullanılmaz; öndeki bölgelerin arkasında kalan bölgelerin parıltısını pus olarak sızdırıyordu.
> - TypeScript 5.9 kullanılır: 6/7 sürümleri OpenAPI tip üreticisinin (openapi-typescript 7) desteklediği sürüm aralığında değildir.

- Uygulama kabuğu: sekme yapısı, açık/koyu tema, `tr.json` altyapısı
- Sohbet arayüzü, "Bu yanıt nasıl üretildi?" paneli, kapsam dışı yönlendirmesi
- **Canlı beyin şeması:** nöropil ağlarından 2B (SVG) ve 3B geometri üretim betikleri; bölge parlaklığı ve davranış nöronu vurgusu
- Davranış grafiği
- "Bu nasıl çalışıyor?" metodoloji sayfası, terimler sözlüğü, atıflar, sınırlılıklar
- Erişilebilirlik: klavyeyle gezinme, renk körlüğüne uygun palet
- **Kabul kriteri:** Her yanıtta dört katmanın ara çıktısı görüntülenebiliyor. Playwright uçtan uca testleri geçiyor.

### Faz 6 — Laboratuvar sekmesi ✅ Tamamlandı
> **Durum (2026-09-17):** Arka uç tamamlandı (57 test).
> - **Nöron seçimi:** hazır grup, hücre tipi, nörotransmitter, nöropil (çıkış sinapslarının
>   çoğunluğuna göre) ve tek tek kimlik. Boş seçim hata sayılır; eksik kimlikler raporlanır.
> - **Deney:** uyarım + susturma. Susturma varsa kontrol ve deney **aynı tohumla** koşulur; fark
>   yalnızca susturmadan gelir. Davranış farkları deneme başına hızlarla Welch t testinden geçer.
>   Nöronların %5'inden fazlası susturulursa "fizyolojik olmayabilir" uyarısı eklenir.
> - **Sinyal yolu:** kenar payı = sinaps × presinaptik hız / hedefe gelen tüm olaylar; yol gücü
>   payların çarpımı, yol işareti kenar işaretlerinin çarpımı. Hedeften geriye ışın araması.
>   Yanıtta her zaman "nedensellik kanıtı değildir" notu döner.
> - **Rapor:** istek, çözümlenmiş kimlikler, sonuçlar ve kaynak/tanım/kalibrasyon SHA-256
>   özetleriyle tek JSON. Geri yüklenip yeniden koşulur; davranış okumaları birebir karşılaştırılır
>   ve fark varsa en büyük fark bildirilir.
> - **İlerleme:** deneyler arka plan işi olarak çalışır (`POST /api/lab/run` → iş kimliği,
>   `GET /api/lab/jobs/{id}` → durum, ilerleme, sonuç). Aynı anda tek deney çalışır.
>
> **Arayüz (2026-09-18):** seçiciler (hazır grup, hücre tipi araması, nörotransmitter, bölge,
> kimlik), parametreler, ilerleme çubuğu, kontrol/susturma karşılaştırma tablosu ve istatistik,
> koşullar arası geçişli davranış grafiği ve beyin şeması, hücre tipi adlı sinyal yolu diyagramı,
> rapor indirme / yükleme ve yeniden koşma sonucu. Testler: Vitest 6, uçtan uca 2 (masaüstü + mobil).
>
> **Kabul ölçütü:** Makalenin şekil 1F susturma deneyi arayüzden yeniden üretildi: MN9 kontrol
> 66,9 Hz → susturma 49,4 Hz (makale 67,0 → 49,0; p = 1,5 × 10⁻²¹). Sinyal yolu analizi, susturulan
> nöronun (CB0553) en güçlü yolların hepsinde yer aldığını gösterdi. Ayrıntı:
> [laboratuvar.md](laboratuvar.md).
>
> **Bulunup düzeltilen hata:** FlyWire kimlikleri (≈ 7 × 10¹⁷) JavaScript'in tam tuttuğu sınırı
> (2⁵³) aşıyor; arayüzde girilen kimlik bozuluyordu (…211725 → …211800). Kimlikler artık API ve
> raporlarda her yönde metin olarak taşınır; test edilir.

- **Backend:**
  - Susturma desteği (hücre tipi, nörotransmitter, nöropil, tek nöron)
  - Sinyal yolu analizi (aktiviteyle ağırlıklandırılmış en güçlü k yol)
  - Deney raporu şeması, dışa aktarma ve geri yükleyip yeniden koşma
  - Uç noktalar: `POST /api/lab/run`, `POST /api/lab/pathways`, `POST /api/lab/report`, `POST /api/lab/replay`, `GET /api/lab/options`, `GET /api/neurons/search` ✅
  - Uzun süren simülasyonlar için ilerleme bildirimi: arka plan işi + durum sorgulama (`GET /api/lab/jobs/{id}`) ✅
- **Frontend:**
  - Nöron grubu seçici (kategori / hücre tipi arama / ID), yoğunluk ve parametre kontrolleri
  - Susturma paneli, kontrol ve deney karşılaştırma grafikleri
  - Katmanlı sinyal yolu diyagramı
  - Rapor dışa aktarma / yükleme, PNG / SVG / CSV indirme
  - Sohbetten "Laboratuvarda aç" geçişi
- **Bilimsel doğrulama:** Shiu et al. makalesindeki en az bir susturma deneyinin Laboratuvar üzerinden yeniden üretilip `docs/dogrulama.md`'ye eklenmesi.
- **Kabul kriteri:** Referans susturma deneyi literatürle tutarlı. Dışa aktarılan bir rapor başka bir işletim sisteminde geri yüklendiğinde birebir aynı sonuçları veriyor. Sinyal yolu diyagramı Faz 2'deki doğrulama senaryolarında bilinen devreleri (ör. şekere duyarlı GRN → MN9) gösteriyor.

### Faz 7 — Açık kaynak yayın 🔄 Hazır, yayın onayı bekliyor
> **Durum (2026-09-18):** Yayın için gereken her şey hazır; depo henüz oluşturulmadı ve hiçbir şey yüklenmedi (kullanıcı kararı: önce hazırla, sonra onayla yükle).
> - **Tek komut:** `uv run sinek` eksik FlyWire verisini (~150 MB) ve hazır senaryo paketini (~8 MB) indirir, SHA-256 ile doğrular ve sunucuyu açar. Paket indirilemezse uygulama yine çalışır (canlı simülasyon) ve nedeni yazılır.
> - **Senaryo paketi dağıtımı:** deterministik zip arşivi (`sinek paketle`; aynı paket → aynı baytlar), GitHub Release `veri-v1` etiketinden indirme, arşiv özeti kodda sabit. Kurulum önce geçici dizine yapılır, tüm dosyalar manifestle doğrulanmadan mevcut paket değiştirilmez; dizin dışına yazmaya çalışan arşivler reddedilir.
> - **Derlenmiş arayüz depoda:** son kullanıcı Node.js kurmaz. Derleme deterministiktir (iki derleme birebir aynı); CI derlemenin güncelliğini denetler.
> - **Örnek deneyler:** makalenin şekil 1F (susturma) ve şekil 3A (acı baskılaması) deneyleri gerçek simülasyonla üretilip rapor olarak eklendi; Laboratuvar'da tek tıkla açılır.
> - **Belgeler:** yeniden yazılmış README (ekran görüntüleri, işletim sistemine göre kurulum, doğrulama tablosu, sınırlılıklar, SSS, yeniden üretim adımları), `CITATION.cff` (şema doğrulandı), yayın iş akışı (`.github/workflows/release.yml`).
> - **Zorunlu açıklama:** kimliği değişen 3 referans nöronu, yöntem ve ölçülen etkiyle README'nin "Sınırlılıklar ve açıklamalar" bölümünde ve doğrulama raporunun 6. bölümünde yer alıyor.
> - **Paket adı:** `flyinfo` (komut `sinek` olarak kaldı; kullanıcı kararı).
>
> Kalan (kullanıcı onayıyla): GitHub deposunun oluşturulması ve ilk yükleme, `veri-v1` Release'ine senaryo arşivinin yüklenmesi, CI'nın üç işletim sisteminde ilk koşusu. Kabul ölçütünün "temiz makinede çalışma" kısmı bu adımlardan sonra doğrulanabilir.

- Frontend'in statik derlenip backend ile paketlenmesi
- Veri paketi indirme komutu, Release iş akışı, `CITATION.cff`
- README: kurulum, iki sekmenin tanıtımı, ekran görüntüleri, SSS
- Laboratuvar için örnek deney raporları (doğrulama deneyleri hazır rapor olarak)
- **Zorunlu açıklama:** v630 → v783 geçişinde kimliği değişen 3 referans nöronunun (tatlı, acı, Johnston organı) FlyWire CAVE ile ardıllarının belirlendiği ve ardılsız durumda ölçülen etki (bkz. [docs/veri.md](veri.md) 4.3), doğrulama raporunda ve README'nin yöntem/sınırlılıklar bölümünde açıklanmış olmalı
- **Kabul kriteri:** Temiz bir Windows / macOS / Linux makinede README adımlarıyla API anahtarı olmadan çalışıyor. Hızlı deneme ve tam yeniden üretim modlarının özetleri eşleşiyor.

### Faz 8 — Genişletmeler (MVP sonrası)
- MaleCNS v1.0 ile VNC / motor çıktı ve 2B sinek davranış animasyonu
- Aktivasyon sonifikasyonu
- GitHub Pages üzerinde sunucusuz, salt okunur demo
- **İnternette yayın (2026-09-17: rafa kaldırıldı).** Değerlendirilen seçenekler: Sohbet sekmesi ucuz bir işlemci sunucusunda, Laboratuvar yerelde (hibrit); ya da simülasyonun WebGPU ile ziyaretçinin tarayıcısında çalıştırılması (modelin yeniden yazılması ve yeniden doğrulanması gerekir). Laboratuvar hesaplaması ekran kartı gerektirmez; ölçüm: RTX 4060 Laptop ~1,5 dk, 16 iş parçacıklı işlemci ~8,5 dk (tam kalite deney)
- Eğitilmiş nöral çözümleyici (PCA + lojistik regresyon) ile kural tabanlı çözümleyicinin karşılaştırılması

---

## 7. Riskler ve Önlemler

| Risk | Etki | Önlem |
|---|---|---|
| Metin → uyarım eşlemesinin bilimsel olarak keyfî olması | Güvenilirlik | Tasarım kararı olarak açıkça etiketlemek, eşleme tablosunu arayüzde yayınlamak |
| LLM'in yorum veya uydurma bilgi eklemesi | Şeffaflık | Katı istem, otomatik JSON doğrulayıcı, şablon yedeği, ham çıktının her zaman görünmesi |
| Nörotransmitter tahminlerindeki hata | Model doğruluğu | Güven skorlarını kullanmak, sınırlılıklar sayfasında belirtmek |
| Makale sonuçları ile v783 verisi arasındaki sürüm farkı | Doğrulama | Referans kodun v783 ile koşulması, farkların doğrulama raporunda belgelenmesi |
| Bazı kategorilerin çözümleyicide davranış karşılığının olmaması | Çıktı kapsamı | Davranış iddia etmeden yalnızca devre aktivitesi göstermek |
| Ücretsiz LLM kotalarının habersiz düşürülmesi / 429 hataları | Erişilebilirlik | Yanıt önbelleği, yedek sağlayıcı, şablon yedeği |
| Canlı simülasyonun zayıf donanımda yavaş olması | Kullanıcı deneyimi | Kapsamlı hazır senaryo seti, ilerleme göstergesi, GPU desteği |
| Sinyal yollarının nedensellik kanıtı gibi yorumlanması | Bilimsel doğruluk | Arayüzde sınırlılık notu, nedensellik için susturma deneyine yönlendirme |
| Geniş susturmaların (ör. tüm GABA) modeli fizyolojik olmayan duruma sokması | Yorumlama | Aşırı aktivite uyarısı, sonuçların "model davranışı" olarak etiketlenmesi |
| Laboratuvar sekmesinin karmaşık görünmesi | Kullanılabilirlik | Hazır örnek deneyler, varsayılan parametreler, alan içi yardım metinleri |
| Kurulumun karmaşık olması | Benimsenme | Tek komut, Node.js'siz dağıtım, platform CI testleri |
| Ham veri boyutu (GB mertebesi) | Altyapı | Gerekli tabloları Parquet'e dönüştürmek, ham veriyi depo dışında tutmak |

---

## 8. Kaynakça ve İlgili Çalışmalar

Tüm kaynaklar 2026-09-17 tarihinde Crossref ve bioRxiv kayıtlarıyla (başlık, dergi, cilt, sayfa, yazarlar) doğrulanmıştır.

### 8.1 Veri ve model
- **[1]** Dorkenwald, S., Matsliah, A., Sterling, A. R., Schlegel, P., Yu, S.-C., McKellar, C. E., et al. (2024). Neuronal wiring diagram of an adult brain. *Nature*, 634(8032), 124–138. https://doi.org/10.1038/s41586-024-07558-y
- **[2]** Schlegel, P., Yin, Y., Bates, A. S., Dorkenwald, S., Eichler, K., Brooks, P., et al. (2024). Whole-brain annotation and multi-connectome cell typing of *Drosophila*. *Nature*, 634(8032), 139–152. https://doi.org/10.1038/s41586-024-07686-5
- **[3]** Shiu, P. K., Sterne, G. R., Spiller, N., Franconville, R., Sandoval, A., Zhou, J., et al. (2024). A *Drosophila* computational brain model reveals sensorimotor processing. *Nature*, 634(8032), 210–219. https://doi.org/10.1038/s41586-024-07763-9
- **[4]** Eckstein, N., Bates, A. S., Champion, A., Du, M., Yin, Y., Schlegel, P., et al. (2024). Neurotransmitter classification from electron microscopy images at synaptic sites in *Drosophila melanogaster*. *Cell*, 187, 2574–2594.e23. https://doi.org/10.1016/j.cell.2024.03.016
- **[5]** Matsliah, A., Yu, S.-C., Kruk, K., et al. (2024). Neuronal parts list and wiring diagram for a visual system. *Nature*, 634, 166–180. https://doi.org/10.1038/s41586-024-07981-1
- **[7]** Berg, S., Beckett, I. R., Costa, M., Schlegel, P., Januszewski, M., Marin, E. C., Nern, A., et al. (2026). Sexual dimorphism in the complete connectome of the *Drosophila* male central nervous system. *Cell*. Ön baskı: https://doi.org/10.1101/2025.10.09.680999 *(Faz 8'de kullanılırsa)*

### 8.2 Nöron–davranış ilişkileri
- **[6]** Gordon, M. D., & Scott, K. (2009). Motor control in a *Drosophila* taste circuit. *Neuron*, 61(3), 373–384. https://doi.org/10.1016/j.neuron.2008.12.033
- **[8]** Thorne, N., Chromey, C., Bray, S., & Amrein, H. (2004). Taste perception and coding in *Drosophila*. *Current Biology*, 14(12), 1065–1079. https://doi.org/10.1016/j.cub.2004.05.019
- **[9]** Cameron, P., Hiroi, M., Ngai, J., & Scott, K. (2010). The molecular basis for water taste in *Drosophila*. *Nature*, 465, 91–95. https://doi.org/10.1038/nature09011
- **[10]** Hampel, S., Franconville, R., Simpson, J. H., & Seeds, A. M. (2015). A neural command circuit for grooming movement control. *eLife*, 4, e08758. https://doi.org/10.7554/eLife.08758
- **[11]** von Reyn, C. R., Breads, P., Peek, M. Y., Zheng, G. Z., Williamson, W. R., Yee, A. L., et al. (2014). A spike-timing mechanism for action selection. *Nature Neuroscience*, 17, 962–970. https://doi.org/10.1038/nn.3741
- **[12]** von Reyn, C. R., Nern, A., Williamson, W. R., Breads, P., Wu, M., Namiki, S., & Card, G. M. (2017). Feature integration drives probabilistic behavior in the *Drosophila* escape response. *Neuron*, 94(6), 1190–1204.e6. https://doi.org/10.1016/j.neuron.2017.05.036
- **[13]** Ache, J. M., Polsky, J., Alghailani, S., Parekh, R., Breads, P., Peek, M. Y., Bock, D. D., von Reyn, C. R., & Card, G. M. (2019). Neural basis for looming size and velocity encoding in the *Drosophila* giant fiber escape pathway. *Current Biology*, 29(6), 1073–1081.e4. https://doi.org/10.1016/j.cub.2019.01.079
- **[14]** Stensmyr, M. C., Dweck, H. K. M., Farhan, A., et al. (2012). A conserved dedicated olfactory circuit for detecting harmful microbes in *Drosophila*. *Cell*, 151(6), 1345–1357. https://doi.org/10.1016/j.cell.2012.09.046
- **[15]** Jones, W. D., Cayirlioglu, P., Grunwald Kadow, I., & Vosshall, L. B. (2007). Two chemosensory receptors together mediate carbon dioxide detection in *Drosophila*. *Nature*, 445, 86–90. https://doi.org/10.1038/nature05466
- **[16]** Bidaye, S. S., Machacek, C., Wu, Y., & Dickson, B. J. (2014). Neuronal control of *Drosophila* walking direction. *Science*, 344(6179), 97–101. https://doi.org/10.1126/science.1249964
- **[17]** Bidaye, S. S., Laturney, M., Chang, A. K., Liu, Y., Bockemühl, T., Büschges, A., & Scott, K. (2020). Two brain pathways initiate distinct forward walking programs in *Drosophila*. *Neuron*, 108(3), 469–485.e8. https://doi.org/10.1016/j.neuron.2020.07.032
- **[18]** Sen, R., Wu, M., Branson, K., Robie, A., Rubin, G. M., & Dickson, B. J. (2017). Moonwalker descending neurons mediate visually evoked retreat in *Drosophila*. *Current Biology*, 27(5), 766–771. https://doi.org/10.1016/j.cub.2017.02.008

### 8.3 Beyin şeması (nöropil geometrisi)
- **[19]** Ito, K., Shinomiya, K., Ito, M., Armstrong, J. D., Boyan, G., Hartenstein, V., et al. (2014). A systematic nomenclature for the insect brain. *Neuron*, 81(4), 755–765. https://doi.org/10.1016/j.neuron.2013.12.017
- **[20]** Jenett, A., Rubin, G. M., Ngo, T.-T. B., Shepherd, D., Murphy, C., Dionne, H., et al. (2012). A GAL4-driver line resource for *Drosophila* neurobiology. *Cell Reports*, 2(4), 991–1001. https://doi.org/10.1016/j.celrep.2012.09.011

> **Not:** Numaralar metin içi atıf sırasını korumak için sabittir. Uygulamada `CITATION.cff` ve arayüzdeki atıf listesi bu bölümden üretilir. Kaynakça Faz 0'da `docs/kaynakca.bib` dosyasına aktarılır; CI, DOI'leri Crossref üzerinden otomatik olarak yeniden doğrular.

### 8.3 Yardımcı kaynaklar
- `sjcabs/fly_connectome_data_tutorial`: FAFB, BANC, MANC, hemibrain ve MaleCNS verilerine erişim öğreticisi (A. S. Bates, SJCABS)
- `fafbseg-py`, `navis`: FlyWire verisine programatik erişim

### 8.4 Benzer projeler (doğrulanmış)
| Proje | Açıklama |
|---|---|
| DOOMFLY (Alex Wormuth): `nftechie/doomfly` | MaleCNS v1.0 konektomuyla Doom oynatma; görüntü → duyusal uyarım, aktivite → oyun kontrolü |
| Flyputer | Shiu tarzı LIF uygulaması ve sanal gövde arayüzü; `fly-mario` gibi projelerin temeli *(depo sahibi doğrulanamadı)* |
| `lixiang1076/fly-brain` | 138 bin nöronluk simülasyonla doğal dil arayüzü |
| `Felix471/ask-the-fly` | FlyWire v783 + Shiu modeliyle yemek seçimi |
| `vshapenko/flypoke` | Tek nöron uyarıp aktivitenin yayılımını izleme |
| `Pronexsteam/brainlab` | Çoklu konektom, referansa karşı doğrulanmış LIF, GPU |
| `cobanov/awesome-fly` | Sinek konektomu projelerinin derlenmiş listesi |
| @chetaslua'nın projesi | NumPy ile tam beyin simülasyonu ve ChatGPT bağlantısı *(yalnızca basında yer aldı, deposu doğrulanamadı)* |

**Farklılaşma:** Türkçe arayüz, sohbet ve laboratuvar olarak iki seviyeli kullanım, susturma deneyleri ve sinyal yolu izleme, katmanların ayrı etiketlendiği bilimsel şeffaflık, referans koda ve yayınlanmış sonuçlara karşı doğrulanmış model, tam tekrarlanabilirlik.
