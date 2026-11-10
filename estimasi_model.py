"""
=============================================================================
MODUL BERSAMA ESTIMASI MODEL (dipakai script 06 dan 07)
File: estimasi_model.py

Isi:
1. Transformasi data di dalam script (file data TIDAK diubah), dipilih
   lewat konstanta TRANSFORMASI:
   - "log"        : target = ln(kg), harga = ln(Rp/kg)       [dipakai]
   - "level_ribu" : target = ribu kg, harga = ribu Rp/kg     [pembanding]
   Koefisien_Musim selalu dipakai apa adanya.
   Alasan:
   - Skala kg asli (±100.000 kg, sigma2 ±1e9) membuat optimizer L-BFGS sering
     berhenti di optimum lokal dan std error tidak stabil.
   - Lonjakan Iduladha bersifat perkalian (volume x 2,717). Pada skala level,
     residual bulan Juni sangat besar sehingga residual tidak normal
     (Shapiro-Wilk gagal). Transformasi log mengubah efek perkalian menjadi
     penjumlahan, sesuai saran dokumen alur penelitian bila uji normalitas gagal.
2. Estimasi multi-optimizer: lbfgs, bfgs, powell, nm, dan nm dari beberapa
   nilai awal; dipilih LogL tertinggi yang konvergen dengan std error valid,
   lalu di-"polish" dengan lbfgs dari titik terbaik.
=============================================================================
"""

import warnings
import numpy as np

from statsmodels.tsa.statespace.sarimax import SARIMAX


# =============================================================================
# KONSTANTA
# =============================================================================

TARGET_COL = "Total_Kuantitas_Kg"
PRICE_COL = "Harga_Rata2_Per_Kg"

TRANSFORMASI = "log"        # "log" atau "level_ribu"

DESKRIPSI_TRANSFORMASI = {
    "log": "target ln(kg), harga ln(Rp/kg), Koefisien_Musim apa adanya",
    "level_ribu": "target ribu kg, harga ribu Rp/kg, Koefisien_Musim apa adanya",
}[TRANSFORMASI]

ENFORCE_STATIONARITY = True
ENFORCE_INVERTIBILITY = True

# (metode, maxiter); lbfgs dengan maxiter 200 = pengaturan default statsmodels
OPTIMIZER = [
    ("lbfgs", 200),
    ("bfgs", 1000),
    ("powell", 5000),
    ("nm", 10000),
]
MAXITER_POLISH = 1000

# Batas std error dianggap tidak wajar (pada skala data yang ditransformasi)
SE_MAKS = 1e6


# =============================================================================
# TARGET AKURASI (RELATIF TERHADAP RATA-RATA PERMINTAAN)
# =============================================================================
# Target RMSE/MAE/MSE dibuat RELATIF terhadap rata-rata permintaan aktual pada
# periode yang dievaluasi (y_bar), sehingga tidak bergantung pada skala data
# (data penelitian = agregat Kabupaten Malang, tidak dibagi jumlah UMKM).
#   RMSE < 10% x y_bar
#   MAE  <  8% x y_bar      (rasio MAE/RMSE = 400/500 = 0,8 seperti dokumen alur)
#   MSE  < (10% x y_bar)^2  (konsisten dengan RMSE; dokumen alur: 250.000 = 500^2)
# MAPE dan R2 sudah tidak bergantung skala, jadi tetap absolut.

TARGET_MAPE_PERSEN = 15.0
TARGET_R2 = 0.70
PERSEN_TARGET_RMSE = 10.0
PERSEN_TARGET_MAE = 8.0

DESKRIPSI_TARGET = (f"MAPE < {TARGET_MAPE_PERSEN:g}%, RMSE < {PERSEN_TARGET_RMSE:g}% × ȳ, "
                    f"MAE < {PERSEN_TARGET_MAE:g}% × ȳ, MSE < ({PERSEN_TARGET_RMSE:g}% × ȳ)², "
                    f"R² > {TARGET_R2:g} (ȳ = rata-rata permintaan aktual periode evaluasi)")


def target_akurasi(rata2_aktual):
    """Kembalikan {metrik: (arah, batas)} dengan batas RMSE/MAE/MSE relatif terhadap ȳ."""
    batas_rmse = PERSEN_TARGET_RMSE / 100 * float(rata2_aktual)
    return {
        "MAPE_%": ("<", TARGET_MAPE_PERSEN),
        "RMSE": ("<", batas_rmse),
        "MAE": ("<", PERSEN_TARGET_MAE / 100 * float(rata2_aktual)),
        "MSE": ("<", batas_rmse ** 2),
        "R2": (">", TARGET_R2),
    }


def cek_target(target, nama, nilai):
    arah, batas = target[nama]
    if not np.isfinite(nilai):
        return "-"
    return "Lulus" if (nilai < batas if arah == "<" else nilai > batas) else "Gagal"


# =============================================================================
# TRANSFORMASI DATA
# =============================================================================

def skala_data(df):
    """Mengembalikan salinan DataFrame dengan target dan harga ditransformasi."""
    hasil = df.copy()
    if TRANSFORMASI == "log":
        hasil[TARGET_COL] = np.log(hasil[TARGET_COL].astype(float))
        if PRICE_COL in hasil.columns:
            hasil[PRICE_COL] = np.log(hasil[PRICE_COL].astype(float))
    else:
        hasil[TARGET_COL] = hasil[TARGET_COL].astype(float) / 1000.0
        if PRICE_COL in hasil.columns:
            hasil[PRICE_COL] = hasil[PRICE_COL].astype(float) / 1000.0
    return hasil


def ke_kg(nilai):
    """
    Mengembalikan prediksi target ke satuan kg.
    Untuk log: exp(prediksi), yaitu median ramalan pada skala kg.
    """
    nilai = np.asarray(nilai, dtype=float)
    return np.exp(nilai) if TRANSFORMASI == "log" else nilai * 1000.0


def _jacobian(result, y_kg):
    """
    Log-Jacobian transformasi pada observasi yang masuk likelihood
    (setelah burn-in): log|dg/dy| dijumlahkan.
    """
    burn = int(result.loglikelihood_burn)
    y = np.asarray(y_kg, dtype=float)[burn:]
    if TRANSFORMASI == "log":
        return -float(np.sum(np.log(y)))
    return -len(y) * np.log(1000.0)


def logl_setara_kg(result, y_kg):
    """
    LogL setara satuan kg = LogL(data transformasi) + log-Jacobian.
    Membuat model log dan level dapat dibandingkan pada data kg yang sama.
    Pendekatan untuk D=1 (inisialisasi approximate diffuse statsmodels).
    """
    return float(result.llf) + _jacobian(result, y_kg)


def aic_setara_kg(result, y_kg):
    return float(result.aic) - 2 * _jacobian(result, y_kg)


def bic_setara_kg(result, y_kg):
    return float(result.bic) - 2 * _jacobian(result, y_kg)


# =============================================================================
# ESTIMASI MULTI-OPTIMIZER
# =============================================================================

def tentukan_trend(d, D=0):
    # Konstanta hanya jika tidak ada differencing
    return "c" if d + D == 0 else "n"


def bangun_model(y, exog, order, seasonal_order):
    return SARIMAX(
        y,
        exog=exog,
        order=order,
        seasonal_order=seasonal_order,
        trend=tentukan_trend(order[1], seasonal_order[1]),
        enforce_stationarity=ENFORCE_STATIONARITY,
        enforce_invertibility=ENFORCE_INVERTIBILITY,
    )


def status_konvergen(result):
    retvals = getattr(result, "mle_retvals", None)
    if isinstance(retvals, dict) and retvals.get("converged") is not None:
        return bool(retvals["converged"])
    return None


def se_valid(result):
    """Std error harus terhingga, > 0, dan tidak sangat besar."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bse = np.asarray(result.bse, dtype=float)
    return bool(np.all(np.isfinite(bse)) and np.all(bse > 0) and np.all(bse < SE_MAKS))


def _variasi_nilai_awal(model):
    """
    Nilai awal alternatif: start_params default statsmodels dengan koefisien
    AR/MA (termasuk musiman) diganti 0, +0,3, dan -0,3. Dipakai untuk
    menghindari optimum lokal.
    """
    dasar = np.asarray(model.start_params, dtype=float)
    idx = [i for i, n in enumerate(model.param_names)
           if n.startswith(("ar.", "ma."))]
    if not idx:
        return []
    variasi = []
    for nilai in (0.0, 0.3, -0.3):
        sp = dasar.copy()
        sp[idx] = nilai
        variasi.append((f"nm_awal{nilai:+.1f}", sp))
    return variasi


def fit_terbaik(y, exog, order, seasonal_order):
    """
    Fit satu model dengan beberapa optimizer dan beberapa nilai awal, lalu
    pilih hasil terbaik yang valid.

    Aturan pemilihan (berurutan dari LogL tertinggi):
    1. Hasil di-polish dengan lbfgs dari titik tersebut; hasil polish dipakai
       bila LogL tidak turun dan konvergen, jika tidak dipakai hasil aslinya.
    2. Hasil harus memiliki std error valid (terhingga, > 0, tidak sangat besar).
    3. Hasil yang konvergen diutamakan; bila tidak ada yang konvergen,
       dipakai hasil valid dengan LogL tertinggi dan diberi status tidak konvergen.

    Returns
    -------
    result : hasil estimasi terpilih
    info   : dict berisi LogL tiap optimizer, optimizer terpilih, status
             polish, validitas std error, konvergensi, dan warning.
    """
    kandidat = []
    info = {}

    def _pesan(daftar):
        return {f"{x.category.__name__}: {str(x.message).splitlines()[0]}" for x in daftar}

    model = bangun_model(y, exog, order, seasonal_order)

    percobaan = [(m, mi, None) for m, mi in OPTIMIZER]
    percobaan += [(nama, 10000, sp) for nama, sp in _variasi_nilai_awal(model)]

    for nama, maxiter, start in percobaan:
        metode = "nm" if nama.startswith("nm_awal") else nama
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                if metode == "lbfgs" and start is None:
                    res = model.fit(disp=False, maxiter=maxiter)
                else:
                    res = model.fit(disp=False, method=metode, maxiter=maxiter,
                                    start_params=start)
                llf = float(res.llf)
            except Exception:
                res, llf = None, np.nan
        info[f"LogL_{nama}"] = llf
        if res is not None and np.isfinite(llf):
            kandidat.append((llf, nama, res, _pesan(w)))

    if not kandidat:
        raise ValueError("Semua optimizer gagal menghasilkan log-likelihood terhingga.")

    kandidat.sort(key=lambda x: x[0], reverse=True)

    valid_konvergen, valid_lain = None, None
    for llf, nama, res, pesan_fit in kandidat:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                res_pol = model.fit(disp=False, start_params=res.params,
                                    maxiter=MAXITER_POLISH)
            except Exception:
                res_pol = None
        if (res_pol is not None and np.isfinite(res_pol.llf)
                and res_pol.llf >= llf - 1e-6 and status_konvergen(res_pol)):
            pilihan = (nama, res_pol, True, pesan_fit | _pesan(w))
        else:
            pilihan = (nama, res, False, pesan_fit)

        if not se_valid(pilihan[1]):
            continue
        if status_konvergen(pilihan[1]) is not False:
            valid_konvergen = pilihan
            break
        if valid_lain is None:
            valid_lain = pilihan

    if valid_konvergen is not None:
        nama, result, dipoles, pesan = valid_konvergen
    elif valid_lain is not None:
        nama, result, dipoles, pesan = valid_lain
    else:
        _, nama, result, pesan = kandidat[0]
        dipoles = False

    # Warning konvergensi dari optimizer yang tidak terpilih tidak relevan
    if status_konvergen(result) is not False:
        pesan = {x for x in pesan if not x.startswith("ConvergenceWarning")}

    info.update({
        "Optimizer_Terpilih": nama,
        "Dipoles_lbfgs": dipoles,
        "SE_Valid": se_valid(result),
        "Konvergen": status_konvergen(result),
        "Warning": " | ".join(sorted(pesan)) if pesan else "-",
    })
    return result, info
