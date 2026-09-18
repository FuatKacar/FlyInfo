# Metin → Uyarım Sınıflandırması: Etiketleme Kılavuzu

> **Faz 4 hazırlığı** · Son güncelleme: 2026-09-17
> Veri: [`backend/sinek/stimulus/data/`](../backend/sinek/stimulus/data/)

Bu belge, Sohbet sekmesinde kullanıcının Türkçe mesajının hangi **duyusal uyarım kategorilerine** eşleneceğinin kurallarını tanımlar. Kurallar hem etiketli veri setlerinin hazırlanmasında hem de sınıflandırıcının değerlendirilmesinde tek ölçüttür.

> **Hatırlatma (yol haritası 1.3):** Metin → uyarım eşlemesi bilimsel bir bulgu değil, **tasarım kararıdır**. Bu kılavuz, kararın tutarlı ve şeffaf olmasını sağlar.

## 1. Temel kural

Etiket, mesajın **sineğe sunulan somut bir duyusal uyarıcıyı** tarif edip etmediğine göre verilir. Mesajın konusu değil, **uyarıcının kendisi** önemlidir.

| Mesaj | Etiket | Neden |
|---|---|---|
| "Sana biraz bal getirdim" | `sugar` | Tatlı uyarıcı sunuluyor |
| "Bal arıları çok çalışkan" | kapsam dışı | Uyarıcı sunulmuyor, sadece konu |
| "Sana bal vermeyeceğim" | kapsam dışı | Olumsuzlanmış: uyarıcı sunulmuyor |
| "Bal mı istersin su mu?" | kapsam dışı | Soru: sunulan somut uyarıcı yok |
| "Bal da var su da, ikisini de koydum" | `sugar`, `water` | İki uyarıcı birlikte sunuluyor |

## 2. Kategoriler

| Anahtar | Kategori | Kapsar | Kapsamaz |
|---|---|---|---|
| `sugar` | Tatlı / yiyecek | Bal, şeker, reçel, şurup, olgun/tatlı meyve, meyve suyu, nektar, pasta, çikolata, dondurma, tatlı yiyecek | Tuzlu yiyecek, "yemek" (tadı belirsizse) |
| `bitter` | Acı / zehir | Acı tat, zehir, böcek ilacı, kafein, kinin, acı ot, "tadı berbat/acı" | Acı biber (kapsaisin; ayrı bir duyu), duygusal "acı" |
| `water` | Su | Su, su damlası, ıslak pamuk, yağmur damlası | Nem, buhar, sis (higrosensör: kapsam dışı), maden suyu gazı |
| `johnston_organ` | Dokunma / anten uyarımı | Antene dokunma, antenlere üfleme, rüzgâr, hava akımı, antende toz/kir, anteni sallama | Ses ve müzik (farklı JO alt grupları), vücuda dokunma (antensiz) |
| `looming` | Tehdit / yaklaşan nesne | Yaklaşan el, gazete/terlik/sineklik ile vurma girişimi, üstüne gelen gölge, dalış yapan kuş, hızla yaklaşan nesne | Sabit görüntü, renk, ışık, sözlü tehdit (nesne yoksa) |
| `geosmin` | Kötü koku | Küf kokusu, toprak/rutubet kokusu, çürük/bozulmuş şey kokusu, "iğrenç koku" | Güzel koku, parfüm, sirke/meyve kokusu |
| `co2` | CO₂ | Nefes verme, "nefesim", karbondioksit, egzoz gazı, soda/maden suyu gazı | Üfleme (hava akımı → `johnston_organ`), oksijen |

### Sınır durumları
- **Nefes ve üfleme:** "Üstüne üfledim" hava akımıdır → `johnston_organ`. "Nefesimi verdim" solunum havasıdır → `co2`. İkisi açıkça birlikteyse ("antenlerine nefesimle üfledim") → `johnston_organ` + `co2`.
- **Gerçek ve mecaz:** Mecazi kullanımlar uyarıcı değildir ("hayat çok acı", "tatlı bir insansın", "başıma bela geldi").
- **Hayali/koşullu:** "Bal olsaydı…", "yarın getireceğim" → kapsam dışı (şu an sunulan bir uyarıcı yok).
- **Yazım hataları ve argo** etiketi değiştirmez ("baL getridim" → `sugar`). Veri setlerindeki yazım hataları (Türkçe karakter eksikliği "sekerli", konuşma dili "bi/kokuyo", harf eksikliği "bıraktm", yaygın yanlış yazım "karbondiyoksit") **kasıtlıdır** ve `yazim_hatasi` etiketiyle işaretlidir; sınıflandırıcının gerçek kullanıcı yazımına dayanıklılığını ölçer. Düzeltilmemelidir.
- **Belirsiz tat:** "yemek getirdim" tadı belirtilmediği için kapsam dışıdır. "Tatlı bir yemek" → `sugar`.

## 3. Yoğunluk

Her etiketli kategori için kaba bir yoğunluk düzeyi verilir. Sınıflandırıcı bunu 0–1 aralığına eşler.

| Düzey | Anlam | Örnek ipuçları | Yoğunluk karşılığı |
|---|---|---|---|
| 1 | Hafif | "biraz", "bir damla", "hafifçe", "azıcık" | 0,2–0,4 |
| 2 | Orta | Niceleyici yok | 0,6 |
| 3 | Güçlü | "çok", "kocaman", "bir kavanoz", "hızla", "aniden", "her yer" | 0,8–1,0 |

## 4. Veri setleri

| Dosya | Amaç | Kural |
|---|---|---|
| `gelistirme.jsonl` | Kategori prototiplerini ve anahtar kelimeleri oluşturmak, eşikleri ayarlamak | Sınıflandırıcı geliştirilirken serbestçe kullanılabilir |
| `test.jsonl` | Nihai başarı ölçümü | Sınıflandırıcı tasarımında **görülmez**; yalnızca değerlendirmede kullanılır |

Satır biçimi:
```json
{"text": "Sana biraz bal getirdim", "labels": {"sugar": 1}, "tags": ["tekil"]}
```
- `labels`: kategori → yoğunluk düzeyi (1–3); boş `{}` kapsam dışı demektir.
- `tags`: değerlendirmede alt kırılımlar için (`tekil`, `coklu`, `kapsam_disi`, `olumsuz`, `mecaz`, `argo`, `yazim_hatasi`, `soru`, `sinir`).

## 5. Başarı ölçütü (yol haritası Faz 4)

- Kategori düzeyinde **makro F1 ≥ 0,85** (kapsam dışı ayrı bir sınıf olarak dahil).
- Sınıf bazında kesinlik, duyarlılık ve F1 raporlanır; ayrıca etiket (`tags`) alt kırılımları.
- Yoğunluk düzeyi doğruluğu ayrıca raporlanır (başarı ölçütü değildir).

## 6. Değerlendirme kaydı

Her test değerlendirmesi burada, sonucu ne olursa olsun kaydedilir. Bir test seti bir kez değerlendirildikten ve hataları incelendikten sonra artık "görülmemiş" sayılmaz.

### Sürüm 1 (2026-09-17) — kod özeti `fc712ef3fe25bf54`
- **Yöntem:** Kural katmanı (sözlük yalnızca kılavuz + geliştirme setinden) + bge-m3 kNN yedek katmanı (k = 5, eşik 0,55; eşik geliştirme setinde bir-dışarıda çapraz doğrulamayla seçildi). Yapılandırma test öncesi sabitlendi; test seti bir kez çalıştırıldı.
- **Sonuç:**

| Yapılandırma | Geliştirme makro F1 | Test makro F1 | Test tam eşleşme | Test yoğunluk doğruluğu |
|---|---|---|---|---|
| Kurallar + vektör yedeği (seçilen) | 0,982 | **0,836** | %77,7 | %75,3 |
| Yalnızca kurallar (ablasyon) | 0,982 | 0,816 | %74,8 | %74,4 |

- **Hedef (≥ 0,85) karşılanmadı.** Geliştirme–test farkı kuralların geliştirme setine aşırı uyduğunu gösterir.
- **Başlıca hata türleri:** (1) sunum olmadan yalnızca konu olarak geçen uyarıcı sözcükleri ("Arılar bal yapar") — kapsam dışı kesinliği 0,58; (2) tamlamalar ("elma suyu" → su); (3) yaklaşan nesne ve anten eylemlerinde dar sözcük dağarcığı (duyarlılık 0,62 ve 0,72); (4) yan cümleler arası olumsuzluk ("Şekerim bitti, getiremedim").
- **Sonraki adım:** Bu test seti artık ikinci geliştirme seti sayılır (`gelistirme2.jsonl`). İyileştirmeler yeni ve görülmemiş bir test setiyle ölçülecektir.

### Test seti 2 (mühürlendi: 2026-09-17)
- **Dosya:** `test.jsonl`, 304 örnek (kategori başına 36–40, kapsam dışı 68, çoklu etiket 26)
- **SHA-256:** `bf8ebdb7be9c4dfad92db90afe8a9d531afb9eea3d7ccd7aef6352d984c8ab78`
- **Yöntem:** Sınıflandırıcıda herhangi bir değişiklik yapılmadan önce yazıldı ve mühürlendi. Sürüm 2 iyileştirmeleri yalnızca `gelistirme.jsonl` ve `gelistirme2.jsonl` ile yapılır; test seti yalnızca son değerlendirmede bir kez kullanılır.
- **Bilinen sınırlılık:** Test seti, sınıflandırıcıyı geliştiren aynı yazar tarafından hazırlanmıştır (yazar yanlılığı). Bağımsız kullanıcı cümleleriyle ek değerlendirme önerilir.

### Sürüm 2 (2026-09-17) — kod özeti `5af726bfaf964132`
- **Değişiklikler (yalnızca iki geliştirme setine dayanarak):** Türkçe ek dizilimi (iyelik + belirtme/tamlayan), ünsüz yumuşaması (toprak → toprağın), ifadelerde çekim eşleşmesi, sözlük terimlerinin metinle aynı normalleştirilmesi, olumsuzluk kalıbının sözcük sonuna bağlanması, yokluk sözcükleri ("bitti"), açık kapsam dışı ifadeler ("acı biber", "nefesini tutmak"), konu fiilleri ("okuyorum", "izledim"), tamlama ve bozulma filtreleri ("elma suyu", "küflü kek"), "kötü sözcük + koku" birlikteliği, kısa hareket fiillerinin çekimleri, yazım hatası toleransında ilk harf koşulu, sözcük dağarcığı genişletmesi (G2).
- **Yedek katman kaldırıldı:** İki geliştirme setinin birleşiminde (434 örnek) bir-dışarıda çapraz doğrulamada yalnızca kurallar makro F1 0,978; yedek katman her eşikte daha düşük (0,963–0,973). Yedek katmana düşen 14 örneğin 2'si doğru, 9'u yanlış uyarıcıydı.
- **Sonuç (mühürlü test seti 2, tek değerlendirme):**

| Ölçüt | Geliştirme | Geliştirme 2 | **Test 2** |
|---|---|---|---|
| Makro F1 | 0,989 | 0,974 | **0,879** |
| Tam eşleşme | %98,3 | %96,2 | %84,2 |
| Yoğunluk doğruluğu | — | — | %77,3 |

| Sınıf (test 2) | Kesinlik | Duyarlılık | F1 |
|---|---|---|---|
| Tatlı | 0,87 | 0,82 | 0,85 |
| Acı | 0,91 | 0,84 | 0,87 |
| Su | 0,84 | 0,97 | 0,90 |
| Anten | 1,00 | 0,82 | 0,90 |
| Yaklaşan nesne | 0,97 | 0,78 | 0,86 |
| Kötü koku | 0,97 | 0,94 | 0,96 |
| CO₂ | 0,95 | 0,95 | 0,95 |
| Kapsam dışı | 0,67 | 0,85 | 0,75 |

- **Hedef (≥ 0,85) karşılandı.**
- **Bilinen zayıflıklar:** mecaz (tam eşleşme %50: "sözleri acı geldi", "dilinden bal damlıyor"); konu olarak geçen sözcükler ("su faturası", "nefes egzersizi"); yaklaşan nesne ve anten eylemlerinde sınırlı fiil dağarcığı ("alçalıyor", "uzanıyor", "antenini çektim").
- **Test sonrası fark edilen kusur (bu sürümde düzeltilmedi):** Yazım hatası toleransı "çiçek" sözcüğünü "çilek" ile eşleştirir. Aynı test setiyle yeniden ölçmek geçersiz olacağından düzeltme, yeni bir test setiyle değerlendirilecek sonraki sürüme bırakılmıştır.
- **Durum:** Test seti 2 artık görülmüştür; sonraki sürümlerin değerlendirmesi için yeni bir test seti gerekir.

## 7. İnceleme

Veri setleri ilk olarak proje geliştirici asistanı tarafından bu kılavuza göre hazırlanmıştır. Anadili Türkçe olan bir kişinin **test setini gözden geçirmesi** önerilir; değişiklikler bu belgedeki kurallara göre yapılmalıdır.
