"""
=============================================================================
MODUL BERSAMA: MODEL PEMBANDING DAN UJI DIEBOLD-MARIANO
File: pembanding.py   (dipakai oleh 14_pembanding_tambahan.py dan
                       15_simulasi_sensitivitas.py; tidak dijalankan sendiri)

Isi modul ini sengaja dibatasi pada hal yang BELUM ada di script 03-13:
- fungsi peramalan untuk model pembanding baru (Holt-Winters, Theta,
  SARIMA airline) dan pembungkus SARIMA final / seasonal naive dengan
  antarmuka yang sama;
- skema evaluasi rolling origin dan multilangkah untuk fungsi tersebut;
- uji Diebold-Mariano (dengan koreksi sampel kecil Harvey dkk., 1997).

Yang DIPAKAI ULANG dari modul lain (tidak disalin):
- estimasi multi-optimizer, transformasi log, dan pengembalian ke kg
  -> estimasi_model.py (fit_terbaik, skala_data, ke_kg);
- rumus metrik MAE/MSE/RMSE/MAPE/R2 -> hitung_metrik di script 07;
- pembacaan CSV berketerangan -> keterangan_csv.py.
=============================================================================
"""

import importlib.util
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.forecasting.theta import ThetaModel
from statsmodels.tsa.holtwinters import ExponentialSmoothing

import estimasi_model as em

BASE_DIR = Path(__file__).resolve().parent
M = 12

# Spesifikasi model (ditetapkan sebelum melihat hasil data uji)
SPEK_SARIMA_FINAL = ((1, 0, 0), (1, 1, 0, M))   # model final penelitian (script 07)
SPEK_SARIMA_AIRLINE = ((0, 1, 1), (0, 1, 1, M))  # model "airline" Box-Jenkins

LABEL_SARIMA = "SARIMA D=1"          # sama dengan label di output 07/08
LABEL_NAIVE = "Seasonal naive"       # sama dengan label di output 07/08
LABEL_HW = "Holt-Winters"
LABEL_THETA = "Theta"
LABEL_AIRLINE = "SARIMA airline"


@lru_cache(maxsize=None)
def muat_skrip(nama_file):
    """Memuat script bernomor (mis. 07_...py) sebagai modul tanpa menjalankan main()."""
    path = BASE_DIR / nama_file
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def hitung_metrik(aktual, prediksi):
    """Metrik akurasi yang SAMA dengan script 07 (dipanggil, bukan disalin)."""
    return muat_skrip("07_validasi_diagnostik_evaluasi.py").hitung_metrik(aktual, prediksi)


# =============================================================================
# FUNGSI PERAMALAN (antarmuka sama: y dalam kg, horizon h -> array kg)
# =============================================================================

def _log(y):
    """Transformasi yang sama dengan model penelitian (estimasi_model.TRANSFORMASI)."""
    return em.skala_data(y.to_frame(em.TARGET_COL))[em.TARGET_COL]


def ramal_sarima(y, h, spek=SPEK_SARIMA_FINAL):
    order, seasonal_order = spek
    res, info = em.fit_terbaik(_log(y), None, order, seasonal_order)
    return em.ke_kg(res.get_forecast(steps=h).predicted_mean.values), info


def ramal_sarima_final(y, h):
    return ramal_sarima(y, h, SPEK_SARIMA_FINAL)[0]


def ramal_seasonal_naive(y, h):
    akhir = np.asarray(y, dtype=float)[-M:]
    return np.array([akhir[i % M] for i in range(h)])


def ramal_holt_winters(y, h):
    """Holt-Winters tren teredam + musiman aditif pada skala log (= musiman perkalian)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(_log(y), trend="add", damped_trend=True, seasonal="add",
                                   seasonal_periods=M, initialization_method="estimated").fit()
    return em.ke_kg(np.asarray(fit.forecast(h), dtype=float))


def ramal_theta(y, h):
    """Metode Theta dengan dekomposisi musiman aditif pada skala log."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ThetaModel(_log(y), period=M, deseasonalize=True, method="additive").fit()
    return em.ke_kg(np.asarray(fit.forecast(h), dtype=float))


def ramal_airline(y, h):
    return ramal_sarima(y, h, SPEK_SARIMA_AIRLINE)[0]


# Model pembanding BARU (belum dievaluasi di script 07/08)
PEMBANDING_BARU = {
    LABEL_HW: ("ExponentialSmoothing(log y): tren aditif teredam + musiman aditif, m = 12", ramal_holt_winters),
    LABEL_THETA: ("ThetaModel(log y): deseasonalize aditif, m = 12", ramal_theta),
    LABEL_AIRLINE: ("SARIMA(0, 1, 1)x(0, 1, 1, 12) pada log y", ramal_airline),
}


# =============================================================================
# SKEMA EVALUASI (sama dengan script 07 dan 08)
# =============================================================================

def prediksi_rolling(y_all, n_latih, fungsi):
    """Rolling origin script 07: latih ulang penuh, ramal 1 bulan, tambah aktual."""
    return np.array([float(fungsi(y_all.iloc[:n_latih + i], 1)[0])
                     for i in range(len(y_all) - n_latih)])


def prediksi_multilangkah(y_all, n_latih, fungsi):
    """Skema script 08: latih sekali, ramal seluruh periode uji sekaligus."""
    return np.asarray(fungsi(y_all.iloc[:n_latih], len(y_all) - n_latih), dtype=float)


# =============================================================================
# UJI DIEBOLD-MARIANO
# =============================================================================

def uji_diebold_mariano(galat_a, galat_b, h=1, loss="kuadrat"):
    """
    H0: akurasi model A = model B. d_t = L(e_a) - L(e_b); d < 0 berarti A lebih akurat.
    Statistik DM dengan varians jangka panjang (autokovarians sampai lag h-1),
    dikoreksi sampel kecil Harvey, Leybourne & Newbold (1997), p dari t(n-1) dua sisi.
    """
    ea, eb = np.asarray(galat_a, float), np.asarray(galat_b, float)
    fungsi_loss = (lambda e: e ** 2) if loss == "kuadrat" else np.abs
    d = fungsi_loss(ea) - fungsi_loss(eb)
    n = len(d)
    d_bar = d.mean()
    gamma = [np.mean((d[k:] - d_bar) * (d[:n - k] - d_bar)) for k in range(h)]
    var_lr = gamma[0] + 2 * sum(gamma[1:])
    if var_lr <= 0:
        return np.nan, np.nan, d_bar
    dm = d_bar / np.sqrt(var_lr / n)
    koreksi = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    dm_hln = dm * koreksi
    p = 2 * stats.t.sf(abs(dm_hln), df=n - 1)
    return float(dm_hln), float(p), float(d_bar)
