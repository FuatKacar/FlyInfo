"""Uyarım sözlüğü ve dilbilgisi kuralları (katlanmış biçimde: ç→c, ş→s, ı→i ...).

KAYNAK KURALI: Terimler YALNIZCA docs/siniflandirma.md kategori tanımlarından (K), geliştirme
setinden (G) ve ikinci geliştirme setinden (G2) alınmıştır. Mühürlü test seti sözlük
oluşturulurken kullanılmaz.

Terim türleri:
    NOUNS       Tek başına uyarıcı sayılan maddeler/eylemler (bal, zehir, su, üflemek...)
    ADJECTIVES  Mecazla karışabilen sıfatlar (tatlı, acı); aynı yan cümlede bir sunum ipucu
                veya aynı kategoriden bir isim yoksa uyarıcı sayılmaz
    PHRASES     Öncelikli çok sözcüklü ifadeler; eşleşen sözcükler tekrar değerlendirilmez
"""

import re

# Kök + Türkçe çekim ekleri (katlanmış). Kökten sonra yalnızca bu ekler gelebilir;
# böylece "bal" → "bala/balı" eşleşir ama "balık", "balkon" eşleşmez.
SUFFIX = re.compile(
    r"^(y)?(l[iu])?(lar|ler)?"
    r"(imiz|iniz|umuz|unuz|im|in|um|un|i|u|si|su|m|n|yu|yi)?"
    r"(n)?"
    r"(nin|nun|in|un|da|de|ta|te|dan|den|tan|ten|a|e|ya|ye|la|le|yla|yle|i|u|yi|yu|ni|nu)?"
    r"(ki)?$"
)

CATEGORIES = ("sugar", "bitter", "water", "johnston_organ", "looming", "geosmin", "co2")

NOUNS: dict[str, tuple[str, ...]] = {
    "sugar": (
        "bal",  # K
        "seker",  # K
        "recel",  # K, G
        "surup",  # K, G
        "surub",  # G (şurubu)
        "nektar",  # K, G
        "pasta",  # K, G
        "cikolata",  # K, G
        "dondurma",  # K, G
        "kek",  # G
        "krema",  # G
        "muz",  # G
        "serbet",  # G
        "lokum",  # G2
        "pekmez",  # G2
        "baklava",  # G2
        "muhallebi",  # G2
        "kurabiye",  # G2
        "karamel",  # G2
        "komposto",  # G2
        "limonata",  # G2
        "glikoz",  # G2
        "hurma",  # G2
        "karpuz",  # G2
        "uzum",  # G2
        "seftali",  # G2
        "armut",  # G2
        "kiraz",  # G2
        "incir",  # G2
        "cilek",  # G2
        "elma",  # G2
    ),
    "bitter": (
        "zehir",  # K, G
        "zehr",  # G (zehri, ünlü düşmesi)
        "kafein",  # K, G
        "kinin",  # K, G
        "acimtirak",  # G
        "pestisit",  # G2
        "nikotin",  # G2
    ),
    "water": (
        "su",  # K
        "islak",  # K, G
        "yagmur",  # K, G
        "musluk",  # G
        "ciy",  # G2
        "islat",  # G2
        "sirilsiklam",  # G2
    ),
    "johnston_organ": (
        "ruzgar",  # K
        "esinti",  # G
        "vantilator",  # G
        "ufle",  # K (üfledim → "ufle" + ek aşağıda fiil olarak ele alınır)
        "meltem",  # G2
        "cereyan",  # G2
        "pervane",  # G2
        "yelpaze",  # G2
        "firtina",  # G2
    ),
    "looming": (),
    "geosmin": (
        "kuf",  # K, G
        "kufl",  # G (küflü, küflenmiş)
        "rutubet",  # K, G
        "les",  # G (leş)
        "lagim",  # G2
        "coplu",  # G2 (çöplük)
    ),
    "co2": (
        "nefes",  # K, G
        "karbondioksit",  # K, G
        "egzoz",  # K, G
        "co2",  # G
        "gaz",  # K (soda/maden suyu gazı)
        "soda",  # K, G
    ),
}

# Tehdit nesneleri: yalnızca mesajda bir eylem (sunum veya hareket ipucu) varsa sayılır
# ("Sineklik almayı unuttum" → kapsam dışı)
LOOMING_OBJECTS = (
    "sineklik",
    "terlik",
    "gazete",
    "golge",
    "raket",
    "karalti",
    "dergi",
    "avuc",
)  # K, G, G2

ADJECTIVES: dict[str, tuple[str, ...]] = {
    "sugar": ("tatli", "sekerli", "tatlandir"),  # K, G, G2
    "bitter": ("aci",),  # K, G
}

# Sıfatları ("tatlı", "acı") somut maddeye bağlayan isimler (mesaj düzeyinde)
SUBSTANCE_NOUNS = (
    "meyve",
    "yemek",
    "yiyecek",
    "sivi",
    "damla",
    "yudum",
    "kahve",
    "cay",
    "parca",
    "yaprak",
    "sey",
    "toz",
    "bitki",
)  # K, G, G2

# Hareket yönü: bu fiillerden biri ve bir yön sözcüğü aynı yan cümlede → yaklaşan nesne
MOTION_VERBS = (
    "gel",
    "yuvarlan",
    "indir",
    "in",
    "uc",
    "kos",
    "firlat",
    "suzul",
    "kapan",
    "kapat",
    "egil",
    "dal",
    "uzat",
)  # K, G, G2
DIRECTION_WORDS = (("sana", "dogru"), ("ustune",), ("uzerine",), ("arkandan",))  # K, G

# Fiil kökleri: sözcük bu kökle başlar (ek serbest). Kategori kanıtı sayılır.
VERB_STEMS: dict[str, tuple[str, ...]] = {
    "johnston_organ": ("ufle", "ufled", "gidikla", "durt", "esiyor", "es"),  # K, G
    "looming": (
        "yaklas",
        "savur",
        "atil",
        "dal",
        "ezice",
        "ezece",
        "ezeri",
        "pike",
        "vur",
    ),  # K, G, G2
    "geosmin": ("kokusmu", "kokmus", "curu", "curum", "kuflen"),  # K, G
    "co2": ("solu", "soludum", "soluk", "hohla"),  # G, G2
}
# "es" gibi kısa kökler yalnızca tam eşleşmede veya belirli çekimlerde kabul edilir.
SHORT_VERB_FORMS: dict[str, tuple[str, ...]] = {
    "es": ("esiyor", "esti", "esen", "esmeye"),  # G
    "dal": ("daliyor", "dalis", "dali", "dalarak"),  # G
    "durt": ("durttum", "durtuyorum", "durttu"),  # G
}

# Öncelikli çok sözcüklü ifadeler: (sözcükler) → kategoriler (boş = kapsam dışı)
PHRASES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("aci", "biber"), ()),  # K: kapsaisin ayrı bir duyu
    (("meyve", "suyu"), ("sugar",)),  # K
    (("portakal", "suyu"), ("sugar",)),  # G
    (("maden", "suyu"), ("co2",)),  # K, G (gazlı)
    (("maden", "suyunun"), ("co2",)),  # G
    (("sekerli", "su"), ("sugar", "water")),  # G
    (("seker", "kamisi"), ("sugar",)),  # K (şeker)
    (("olgun", "meyve"), ("sugar",)),  # K
    (("tatli", "meyve"), ("sugar",)),  # K
    (("bocek", "ilaci"), ("bitter",)),  # K, G
    (("tadi", "berbat"), ("bitter",)),  # K, G
    (("sac", "kurutma"), ("johnston_organ",)),  # G
    (("hava", "akimi"), ("johnston_organ",)),  # K
    (("kuru", "buz"), ("co2",)),  # G
    (("toprak", "kokusu"), ("geosmin",)),  # G
    (("toprak", "kokan"), ("geosmin",)),  # G
    (("pis", "kokusu"), ("geosmin",)),  # G
    (("pis", "koku"), ("geosmin",)),  # K
    (("igrenc", "kokuyor"), ("geosmin",)),  # G
    (("cop", "kutusunun"), ("geosmin",)),  # G
    (("bodrum", "gibi"), ("geosmin",)),  # G ("bodrum gibi kokuyor")
    (("gazli", "icecegin"), ("co2",)),  # G
    (("co", "2"), ("co2",)),  # G ("co2" sözcük bölünmesi)
    (("gazli", "su"), ("co2",)),  # G2
    (("ilac", "surub"), ("bitter",)),  # G2
    (("hasere", "ilac"), ("bitter",)),  # G2
    (("bocek", "oldurucu"), ("bitter",)),  # G2
    (("igrenc", "koku"), ("geosmin",)),  # K
    (("berbat", "koku"), ("geosmin",)),  # G2
    (("hava", "pompala"), ("johnston_organ",)),  # G2
    (("hava", "puskurt"), ("johnston_organ",)),  # G2
    (("hava", "gonder"), ("johnston_organ",)),  # K (hava akımı)
    (("kum", "tanesi"), ("johnston_organ",)),  # G2 (antende)
)

# Açık kapsam dışı ifadeler: eşleşirse yedek katman da uyarıcı üretemez
OUT_OF_SCOPE_PHRASES: tuple[tuple[str, ...], ...] = (
    ("aci", "biber"),  # K
    ("nefes", "tut"),  # G2 (nefesini tutmak)
)
# Kötü koku: bu sözcüklerden biri ve "kok..." ile başlayan bir sözcük aynı mesajda → kötü koku
BAD_SMELL_WORDS = (
    "pis",
    "igrenc",
    "kotu",
    "berbat",
    "bozuk",
    "toprak",
    "nemli",
    "mantar",
    "cop",
)  # K, G, G2

# Yokluk/tükenme bildiren sözcükler (olumsuzluk gibi davranır)
ABSENCE_WORDS = ("bitti", "bitmis", "tukendi", "tukenmis", "kalmadi")  # G2

# Bileşik "X suyu" (meyve suyu vb.): X bir yiyecek/içecek adıysa "su" SU sayılmaz
JUICE_MODIFIERS = ("meyve", "portakal", "tonik", "ot", "ozsu", "narenciye", "kamis")  # K, G, G2
WATER_MODIFIERS = (
    "icme",
    "kaynak",
    "musluk",
    "yagmur",
    "deniz",
    "temiz",
    "soguk",
    "sicak",
    "arit",
    "cesme",
    "saf",
    "tatli",
)  # K, G, G2

# Bozulma niteleyicileri: yiyecek adıyla birlikteyse kötü koku sayılır, tatlı sayılmaz
SPOILAGE = ("kuf", "curu", "bozu", "kokmus", "kokus", "bayat", "les")  # G2
# "ıslak"/"yağmur" koku bağlamında (ıslak toprak kokusu) ise su uyarımı sayılmaz
SMELL_CONTEXT = ("koku", "kokan", "kokus")  # G2

# Anten + ipucu → Johnston organı (anten tek başına yeterli değil: "anten tamircisi")
ANTENNA_STEM = "anten"  # K
ANTENNA_CUES = (
    "dokun",
    "ufle",
    "toz",
    "kir",
    "degd",
    "degi",
    "elle",
    "oksa",
    "temizle",
    "kil",
    "kum",
    "yag",
    "fiske",
    "un",
    "ag",
    "salla",
    "gidikla",
    "durt",
    "polen",
    "degd",
    "egil",
)  # K, G

# Sunum / varlık ipuçları (fiil kökleri, önek eşleşmesi) — sıfatların uyarıcı sayılması için
PRESENTATION_CUES = (
    "koy",
    "getir",
    "birak",
    "dok",
    "ver",
    "sur",
    "damlat",
    "serp",
    "sik",
    "puskurt",
    "akit",
    "akiy",
    "uzat",
    "doldur",
    "kat",
    "yaklas",
    "dokun",
    "tattir",
    "tadina",
    "var",
    "yayil",
    "dus",
    "bosalt",
    "pompala",
    "ayir",
    "kaplad",
    "cevir",
    "sikt",
    "sikiyor",
    "sal",
    "gel",
    "cik",
    "fiskir",
    "actim",
    "acip",
    "birik",
    "yukseli",
    "kaplad",
    "sinmis",
    "dol",
)  # K, G, G2
# Tam sözcük olarak sunum ipucu sayılan kısa emirler ("al", "ye")
EXACT_CUES = frozenset({"al", "ye", "buyur"})  # G2

# Konu fiilleri: uyarıcı sözcüğü sineğe sunulmuyor, yalnızca konu ediliyor
# ("Arılar bal yapar", "Kekimi kendim yedim", "listesini okuyorum", "belgesel izledim").
# Mesajda sunum ipucu yoksa ve bu fiillerden biri varsa isimler uyarıcı sayılmaz.
TOPIC_VERBS = (
    "yapar",
    "yedim",
    "yiyorum",
    "okuyor",
    "okudum",
    "izledim",
    "izliyor",
    "patladi",
)  # G2

# Olumsuzluk, soru, gelecek/koşul (kapsam dışı işaretleri)
NEGATION_WORDS = frozenset({"yok", "degil", "asla", "hic", "hicbir"})  # K
NEGATIVE_VERB = re.compile(
    r"(m[ae](d[i](m|n|k|niz|nuz|lar|ler)?"
    r"|y[ae]c[ae](k|g[i]m|g[i]n|g[i]z|kler|klar)"
    r"|z(sin|siniz|lar|ler)?"
    r"|m(iz)?"
    r"|m[i]s(tir|sin|lar|ler)?"
    r"|s[i]n(lar|ler)?"
    r"|yin)"
    r"|m[iu]yor(um|sun|uz|sunuz|lar)?)$"
)  # K: -madı, -mayacak, -maz, -mam, -mamış, -masın, -mıyor (sözcük sonunda)
NOT_NEGATIVE = frozenset({"tamam", "hamam", "madem"})
QUESTION_PARTICLES = re.compile(r"^m[iu](s[iu]n|y[iu]m|y[iu]z|s[iu]n[iu]z)?$")  # K
FUTURE = re.compile(r"(y)?[ae]c[ae][kg]")  # K: -acak/-ecek
FUTURE_EXCEPTIONS = ("yiyecek", "icecek", "icecegin")  # isimler (yiyecek, içecek)
CONDITIONAL = re.compile(r"s[ae]yd[i]")  # K: olsaydı
TIME_WORDS = frozenset({"yarin", "keske"})  # K

# Yoğunluk ipuçları
WEAK_CUES = frozenset(
    {"biraz", "azicik", "azcik", "hafif", "hafifce", "minik", "minicik", "yavasca", "yavas"}
)  # K, G
WEAK_PHRASES = (("bir", "damla"), ("birkac", "damla"))  # K, G
STRONG_CUES = frozenset(
    {
        "cok",
        "kocaman",
        "koca",
        "bol",
        "bolca",
        "hizla",
        "sert",
        "kuvvetli",
        "derin",
        "hepsi",
        "kavanoz",
        "kova",
    }
)  # K, G
STRONG_PHRASES = (("her", "yer"), ("her", "yere"), ("agzina", "kadar"), ("sonuna", "kadar"))  # K, G
