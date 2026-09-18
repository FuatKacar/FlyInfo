"""FlyWire nöropil ağlarının kaynağı.

Ağlar FlyWire'ın herkese açık Neuroglancer deposundan (Google Cloud Storage) indirilir. Bu ağlar
JFRC2 şablon beynindeki nöropil yüzeylerinin (Jenett et al. 2012; adlandırma Ito et al. 2014)
FlyWire (FAFB14.1) uzayına dönüştürülmüş halidir. FlyWire, sinapsları nöropillere bu hacimlerle
atamıştır (Dorkenwald et al. 2024); dolayısıyla şemadaki bölgeler `neuropils.py` özetindeki
adlarla birebir aynıdır.

Depo adları içermez (bölümler 0–77 numaralıdır). Numara → ad eşlemesi, fafbseg-py
(navis-org/fafbseg-py @ d0da9512, `fafbseg/data/JFRC2NP.surf.fw.zip`) içindeki adlı PLY
dosyalarıyla KÖŞE KOORDİNATLARININ BİREBİR karşılaştırılmasıyla bir kez çıkarılmıştır: 78 adın
her biri tam olarak bir bölümle eşleşmiştir. Eşleme ayrıca geometrik testlerle doğrulanır
(sol/sağ ayna simetrisi, ön/arka ve üst/alt konumlar; bkz. tests/schematic).

SHA-256 değerleri her bölümün parça (fragment) dosyalarının sırayla birleştirilmiş içeriğidir.
"""

MESH_BASE_URL = "https://storage.googleapis.com/flywire_neuropil_meshes/"
NEUROPIL_PREFIX = "neuropils/neuropil_mesh_v141_v6"
BRAIN_PREFIX = "whole_neuropil/brain_mesh_v141.surf"

BRAIN_MESH: tuple[int, str] = (
    1,
    "12a484a4d254f4b328a6dc4e93027285d0b4b10a1309b8c167c67fe5a4336474",
)

# nöropil adı → (depodaki bölüm numarası, SHA-256)
NEUROPIL_MESHES: dict[str, tuple[int, str]] = {
    "AL_L": (57, "200c64e740b82333af1eb019ba3cb45704d1bf41e930a7303c90ee99e8292591"),
    "AL_R": (27, "061b08a8f2f23ad69986bba4dd1451e8a6933871c1b5537b5b716c59a404f7ca"),
    "AME_L": (56, "c70a60364d0b7ffed3264151b8ebf407b55bc3b8219acb2bcecfc649c464856f"),
    "AME_R": (29, "aa75c16862f4b5d749c201551abed7ec2de57cb143ecdf4aa1883515cb0b38df"),
    "AMMC_L": (45, "32c45c91370a16369cac82632b5cb0013b412c2fc83e1ec83e03d2a272e1f4b7"),
    "AMMC_R": (71, "c3b5024d0d54569ec34166e423c8abe6f976badd657f540c436a224349d238fc"),
    "AOTU_L": (22, "819bc5784f970eb091eb19b1fb21a97a40a14eb695aa91fdc7be46ec1f53428e"),
    "AOTU_R": (24, "c3a2018afdaf06e24bed70f245e4ee58ef9959c6acd8f1684092d573793723b0"),
    "ATL_L": (18, "9d6a5e6dfae782c1dc81702bbd58b5161bc5ce149a5883db5d5243a3c1b1bdb6"),
    "ATL_R": (23, "7125a54f1d29449f4bab6aa0c3a6dcf4e030fe2714767495b76b8f1f3460ea85"),
    "AVLP_L": (69, "10c82f400cab499f8db626d2f0e75f6c6893e89c0cef31f3da836b559a904bc2"),
    "AVLP_R": (49, "4540d9bdd99c7ac1eb5734610d8ee68cadaa5aa513ca1dcb2071985d5da50c80"),
    "BU_L": (73, "20f82b2a39163de65dd7671d3a8b69f85c18ff714f5d0a8e64ffd5320e5626c5"),
    "BU_R": (11, "88560a48c4183b88b35555b274c30f4b95a285010ff7c431f2459361b02bacc7"),
    "CAN_L": (3, "dd20e8ad7a4b83b35e60e94537bbfeb95b008447a6d0a044d167d1169ee3c544"),
    "CAN_R": (61, "6df980464ff75bd226165cd44e265f69935709bcd316aa1279ca3edc7d027d53"),
    "CRE_L": (30, "c82e41267a97b6ef886eeeb26d720be7ecf3009b8eec491d10fd56a0324b1da4"),
    "CRE_R": (19, "8debaf65b383eccf1d0b65f8f3cf7d5258e5ec5379549c3df0ea4436403dfa0f"),
    "EB": (35, "b3841194265a7453ea54a5ed6e571a0ef7f853d025dc53bdb89ac3d912c5cc32"),
    "EPA_L": (8, "376fcc794723626a810e5c05a2dad3b04625fa587630cca75d7aabbd535cccd0"),
    "EPA_R": (52, "ae9e2776b2fb0981746c1c6e9d6fc3cfb1dd00e6117a6e13501483b28b1f516c"),
    "FB": (65, "9b63f3fa7d5e1b52e08bc923e277b3215daaac725a3d644f6bfd2422d80deb0a"),
    "FLA_L": (74, "bfc68aed9ed3418bbdc2006b86db7129720efeea83226343d26acd76347aaac9"),
    "FLA_R": (5, "bf0565967ff56f19d4fb629f4ac99af0d81bac8c8b4f0ef12ceb3ae88256ed11"),
    "GA_L": (34, "608561ab72f7d424582ba15a7e5c7dc5b0b6106df013e72843f8f5ec501d2a34"),
    "GA_R": (16, "d4b7ee180d2bfd8a6eade42ecb331828a6e39ea538e03c6ff5625e349d35f193"),
    "GNG": (26, "4699995c8ff20a3624636b42dd555f12f487f721b1371203faceb4825991d356"),
    "GOR_L": (12, "d76dc11db9ba836cc093da32f201e70ec9de2b82dab9be23ec405867dbc831ad"),
    "GOR_R": (32, "68a56f6fa2470588b9915865b3a7c60e40f599cf4c4ca16c8ab1a3435e423adf"),
    "IB_L": (67, "9c6831b813a3c55c69ae5689ba755dcc57d88ad5dc514f874e53c4ff85fd8e0f"),
    "IB_R": (17, "0080986093535c2451698f45de84f508943a0105c55d930bdc25b0c87c3fdc32"),
    "ICL_L": (31, "f4ae1490ae0ea4d2f17f9a27c1dc338b4982c7297ff60d69fb2545d337c66225"),
    "ICL_R": (33, "586e1a5fbe1425181392e5514fc2eff04d6ee4808183f944b442be555a70dcd9"),
    "IPS_L": (7, "dd453303c90da1823fd6b3a2df5e446d0213b69dbe72f694416faf323e7eed28"),
    "IPS_R": (38, "deac8b3ee784d1c262fdf2104dd249f846405d72aa2efa879cd8b433f37a6a51"),
    "LAL_L": (46, "ed26f0d9befceefab68d4c7c00b5fcbcd481f802fbfd92d56685396478b781bb"),
    "LAL_R": (25, "331797c5adf414805eaec7e7dac7784921a6d9e7eb14f900e7dbe5613bd5ba11"),
    "LA_L": (76, "ea1501c21582fccd0749d5c75229ea03dd10c79779f618bd935870696230415b"),
    "LA_R": (75, "84c64355b2f310504e3491d4d3c3cbdf5c5db32669b7570a5b9241a7e3913886"),
    "LH_L": (20, "fdaf6ebebcf06992f79e0b0978e7c96b693c8f3cbc330d49c6ac25b928b62d49"),
    "LH_R": (54, "447cadb8c0c4ef52af129085ba571050b3249f566e169ee081fbfd0d598e201f"),
    "LOP_L": (6, "68be4fd837bc53ba03f09eb8654817f7c9f7472a6fcc801ad7cf8be4e71899a1"),
    "LOP_R": (36, "be29f32b31c422097b75a565400e35937a9eb11924b1ff9e58c5fd4548f43a94"),
    "LO_L": (51, "0aea7a7d81a2cdd20e457d6c32b7099fb0c687ad372597a280ed7f929d15e54a"),
    "LO_R": (14, "428f641332e0a8c373e8507cfd16779a8dd5e4f37e4d7ecf91af1e44f38bbb8d"),
    "MB_CA_L": (66, "a34d815217922072a93744ba67fc8ca4a17c0282fef60fe0f707a2e155cadd3a"),
    "MB_CA_R": (21, "f1790c87581b880510b679537f2b339fbb146bdd56e26f4f3d008e481bca7ab3"),
    "MB_ML_L": (10, "5432e33b1c916bed42adf5d241b62d09c594190705e97863629666ce1f93c3e7"),
    "MB_ML_R": (41, "6737bcd3f83285151751f04188d9faf336f5c3b3870a644351580741192229d6"),
    "MB_PED_L": (48, "81c55038d63ad3e163bf72fc96d0a4fd6d9b7bdf76db80680fa8b1df7cba0c19"),
    "MB_PED_R": (28, "72b2e2120e6e701987f1f0b5d9b3ebd6218675f53051d325cda7230cb167ef66"),
    "MB_VL_L": (4, "05d069d03c91ef0dafbf84770aee7b2165c2b6af09927caa4dff316178f2cb69"),
    "MB_VL_R": (55, "24ba39dcb6ab0290dd709fff7916edfeddb4853968c093f43d75adfa3d1a20f4"),
    "ME_L": (43, "0a8d9e5e964de41b5a4705b8864c3e349a50021e9a92a28b709d2d82e9840c0e"),
    "ME_R": (2, "4d2c90beadeafe7548fd66a1105b58fa297d2ec4510c92ba0251291b80c9ea67"),
    "NO": (58, "f3f394cb71a1bb44846993a1b7bc1a7eaca5eee8e3094c5be902754bf0c80383"),
    "OCG": (77, "901de9829d477b24668ae4aa301b23356f5f388f4bd1cacc92c7faba66dc779c"),
    "PB": (68, "08761f791e1efbfa42bf21ba4a07ee8030bc38a94823700c0c6c4ab42551bad9"),
    "PLP_L": (59, "03349a6ed401fe35ef83ce7de9435686a1c8b39dfc9507f5706e1488356c23c6"),
    "PLP_R": (9, "3a979928bdebe8660c9e71337eb14115e21e2743c421f695a307e631c243cf65"),
    "PRW": (53, "dcf7857b0c0a611ffee51027ab9aed956385811b4084b088936c99adf7953174"),
    "PVLP_L": (39, "2c5bba09f547b2d2dbcf9344d9ed3a2ef56a81410ed016400808be1ce0a603eb"),
    "PVLP_R": (37, "a564de9bd10bf67ca749c964219106f50d8bde1b54e27c51effcd35827ac23b9"),
    "SAD": (70, "5999ff6ff46de28e5e4597cf518102cc8e612d437af22a3295c84b94a557ef69"),
    "SCL_L": (15, "f2b5d58053e7d12833480a0ef9aa353ba8251a23edab2cf962529181866bb522"),
    "SCL_R": (0, "15085b99a41426a75692f10e23bf0a950210d155dc40b6b7c751497c335d5fae"),
    "SIP_L": (72, "db8b7a3fda30391dffd6c5062d950e2149a442eb4eb5e7e5aa55c9f53448c3c4"),
    "SIP_R": (63, "07c3b9af4555b1f809970ca3bedbf8fabfc183d99d262b84c768356871fe182f"),
    "SLP_L": (62, "8c5642a2ecf97cbb9f9051a17aa59ba370cf013558fd5a048fb6ca4f77f3776a"),
    "SLP_R": (47, "8503ed48b5ad6d66c6cf91ad2264e19519fb6cf01bc65a88a0ce846b96268e28"),
    "SMP_L": (42, "cf57e2b6d9e91cb9eeb02f0bc8722b65fb8b0a93b74ee9f187155badf2996dfa"),
    "SMP_R": (1, "19848674e961008b83f7fd50bc4ee7bd82d505a9e7cb8bc401920693a55e4328"),
    "SPS_L": (13, "9c5915398b1bbad655ab5750780e6b40a967572498d8c0e9754e0249565c8730"),
    "SPS_R": (64, "1e06f4424900c7626f41961c3db9de31719bb8e0c808145bfa7502b6648ce0e3"),
    "VES_L": (44, "6b1adff158edf5824064a0d81ffffc408360aab55e3b99012ba5ee9da9c5592c"),
    "VES_R": (40, "ffb4f335a2c786eef48aa647119a751609512826bc589f12072c57e1ad706c83"),
    "WED_L": (50, "955bd87b51a7c7bbc58c55efa40612c15b090bde0dc831e7657e04199d411adf"),
    "WED_R": (60, "efff269665940391ddc3bc9058fe646618d81f20dba2629f5e6d697612fabc45"),
}
