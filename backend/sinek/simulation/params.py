"""LIF model parametreleri.

Varsayılanlar Shiu et al. (2024) referans kodundaki `default_params` ile birebir aynıdır
(philshiu/Drosophila_brain_model @ 91bdd1e7, model.py). Birimler: ms, mV, Hz.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LIFParams:
    # Deneme
    t_run_ms: float = 1000.0  # deneme süresi
    n_trials: int = 30  # deneme sayısı
    dt_ms: float = 0.1  # Brian2 varsayılan zaman adımı

    # Ağ sabitleri — Kakaria & de Bivort 2017
    v_0_mv: float = -52.0  # dinlenim potansiyeli
    v_rst_mv: float = -52.0  # spike sonrası sıfırlama potansiyeli
    v_th_mv: float = -45.0  # ateşleme eşiği
    t_mbr_ms: float = 20.0  # zar zaman sabiti
    # Jürgensen et al. 2021
    tau_ms: float = 5.0  # sinaptik iletkenlik zaman sabiti
    # Lazar et al. 2021
    t_rfc_ms: float = 2.2  # refrakter dönem
    # Paul et al. 2015
    t_dly_ms: float = 1.8  # sinaptik gecikme

    # Serbest parametre
    w_syn_mv: float = 0.275  # sinaps başına ağırlık
    f_poi: float = 250.0  # Poisson girdisinin ağırlık çarpanı (spike'a yol açmaya yeterli)

    def __post_init__(self) -> None:
        if self.n_trials < 1:
            raise ValueError("Deneme sayısı en az 1 olmalı")
        if min(self.t_run_ms, self.dt_ms, self.t_mbr_ms, self.tau_ms) <= 0:
            raise ValueError("Süreler ve zaman sabitleri pozitif olmalı")
        if self.t_mbr_ms == self.tau_ms:
            raise ValueError("Analitik çözüm için t_mbr_ms ve tau_ms farklı olmalı")
        if self.v_th_mv <= self.v_rst_mv:
            raise ValueError("Eşik sıfırlama potansiyelinden büyük olmalı")

    @property
    def n_steps(self) -> int:
        return _timestep(self.t_run_ms, self.dt_ms)

    @property
    def delay_steps(self) -> int:
        return _timestep(self.t_dly_ms, self.dt_ms)

    @property
    def refractory_steps(self) -> int:
        return _timestep(self.t_rfc_ms, self.dt_ms)

    @property
    def poisson_weight_mv(self) -> float:
        return self.w_syn_mv * self.f_poi

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _timestep(duration_ms: float, dt_ms: float) -> int:
    """Brian2'nin `timestep(t, dt)` fonksiyonu: kayan nokta hatasına karşı küçük pay ile taban."""
    return int((duration_ms + 1e-3 * dt_ms) / dt_ms)
