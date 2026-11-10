
"""
=============================================================================
PROGRAM EKSPLORASI DATA (EDA), UJI STASIONERITAS & IDENTIFIKASI MODEL
File: 05_eksplorasi_data.py

Metodologi:
1. Perhitungan dan ekspor tabel dekomposisi.
2. Visualisasi time series.
3. Visualisasi dekomposisi.
4. Uji stasioneritas menggunakan Augmented Dickey-Fuller (ADF).
5. Analisis ACF dan PACF.
6. Identifikasi kandidat ARIMA secara parsimonis.
7. Identifikasi indikasi musiman periode 12 bulan.
8. Ekspor konfigurasi model ke JSON.

CATATAN:
- Lag signifikan tidak otomatis menjadi orde AR atau MA.
- Identifikasi musiman tidak otomatis menetapkan D=1.
- Kandidat model harus dievaluasi pada tahap pemodelan.
=============================================================================
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/


# =============================================================================
# PENGATURAN PATH DAN PARAMETER
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

OUTPUT_DIR = DATA_DIR / "eksplorasi"

INPUT_FILE = DATA_DIR / "olah" / "dataset_pra_proses_final.csv"
OUTPUT_CSV = OUTPUT_DIR / "tabel_dekomposisi_hasil.csv"
OUTPUT_IMAGE_TS = OUTPUT_DIR / "time_series_plot.png"
OUTPUT_IMAGE_DEC = OUTPUT_DIR / "time_series_decomposition.png"
OUTPUT_IMAGE_ACF_PACF = OUTPUT_DIR / "acf_pacf_plot.png"
OUTPUT_CONFIG_JSON = OUTPUT_DIR / "model_config.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = "Total_Kuantitas_Kg"
SEASONAL_PERIOD = 12
ALPHA = 0.05


# =============================================================================
# FUNGSI VALIDASI DAN PEMUATAN DATA
# =============================================================================

def muat_data(filepath):
    """
    Membaca dan memvalidasi dataset bulanan.
    Frekuensi diatur menjadi Month Start (MS).
    """

    if not filepath.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {filepath}"
        )

    df = pd.read_csv(filepath)

    kolom_wajib = [
        "Periode",
        "Jumlah_Transaksi",
        "Total_Kuantitas_Kg",
        "Harga_Rata2_Per_Kg"
    ]

    kolom_hilang = [
        kolom for kolom in kolom_wajib
        if kolom not in df.columns
    ]

    if kolom_hilang:
        raise ValueError(
            f"Kolom dataset tidak lengkap: {kolom_hilang}"
        )

    df["Periode"] = pd.to_datetime(
        df["Periode"],
        errors="coerce"
    )

    if df["Periode"].isna().any():
        raise ValueError(
            "Terdapat tanggal Periode yang tidak valid."
        )

    df = df.sort_values("Periode")
    df = df.set_index("Periode")

    if df.index.has_duplicates:
        raise ValueError(
            "Terdapat tanggal duplikat pada dataset."
        )

    for kolom in [
        "Jumlah_Transaksi",
        "Total_Kuantitas_Kg",
        "Harga_Rata2_Per_Kg"
    ]:
        df[kolom] = pd.to_numeric(
            df[kolom],
            errors="coerce"
        )

    if df[TARGET_COLUMN].isna().any():
        raise ValueError(
            "Target mengandung nilai kosong atau nonnumerik."
        )

    # Frekuensi bulanan tanggal awal bulan.
    df = df.asfreq("MS")

    if df[TARGET_COLUMN].isna().any():
        raise ValueError(
            "Terdapat periode bulanan yang hilang. "
            "Periksa dataset sebelum melanjutkan."
        )

    if len(df) < 24:
        raise ValueError(
            "Dekomposisi musiman periode 12 membutuhkan "
            "minimal dua siklus atau 24 observasi."
        )

    print("\n[VALIDASI DATA]")
    print(f"Jumlah observasi : {len(df)}")
    print(f"Periode awal     : {df.index.min().date()}")
    print(f"Periode akhir    : {df.index.max().date()}")
    print(f"Frekuensi        : {df.index.freqstr}")

    return df


# =============================================================================
# FUNGSI 1: HITUNG DAN EKSPOR TABEL DEKOMPOSISI
# =============================================================================

def hitung_dan_ekspor_tabel(filepath, output_csv):

    print("\n-> Menghitung dekomposisi time series...")

    df = muat_data(filepath)

    y = df[TARGET_COLUMN]

    dekomposisi = seasonal_decompose(
        y,
        model="additive",
        period=SEASONAL_PERIOD,
        extrapolate_trend=0
    )

    df_hasil = df.copy()

    df_hasil["Trend_Kg"] = dekomposisi.trend
    df_hasil["Seasonal_Kg"] = dekomposisi.seasonal
    df_hasil["Residual_Kg"] = dekomposisi.resid

    df_hasil = df_hasil.round(2)

    df_hasil.to_csv(
        output_csv,
        index_label="Periode"
    )

    print(
        f"-> Tabel dekomposisi disimpan: "
        f"{output_csv.name}"
    )

    return output_csv


# =============================================================================
# FUNGSI 2: VISUALISASI TIME SERIES
# =============================================================================

def visualisasi_time_series_dari_tabel(
    file_csv,
    output_path
):

    print("\n-> Membuat visualisasi time series...")

    df = pd.read_csv(file_csv)

    df["Periode"] = pd.to_datetime(df["Periode"])
    df = df.set_index("Periode")

    plt.figure(figsize=(12, 5))

    plt.plot(
        df.index,
        df[TARGET_COLUMN],
        marker="o",
        linestyle="-",
        linewidth=2,
        markersize=5
    )

    max_val = df[TARGET_COLUMN].max()
    max_date = df[TARGET_COLUMN].idxmax()

    plt.annotate(
        f"Nilai maksimum\n{max_val:,.0f} kg",
        xy=(max_date, max_val),
        xytext=(max_date, max_val * 1.08),
        arrowprops=dict(
            facecolor="red",
            shrink=0.05
        ),
        fontsize=9,
        color="red",
        ha="center"
    )

    plt.title(
        "Time Series Plot: Total Permintaan Daging Kambing",
        fontsize=13,
        fontweight="bold"
    )

    plt.xlabel("Periode")
    plt.ylabel("Total Kuantitas (Kg)")

    plt.gca().xaxis.set_major_formatter(
        mdates.DateFormatter("%b %Y")
    )

    plt.gca().xaxis.set_major_locator(
        mdates.MonthLocator(interval=2)
    )

    plt.xticks(rotation=30, ha="right")
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"-> Grafik disimpan: {output_path.name}")


# =============================================================================
# FUNGSI 3: VISUALISASI DEKOMPOSISI
# =============================================================================

def visualisasi_dekomposisi_dari_tabel(
    file_csv,
    output_path
):

    print("\n-> Membuat visualisasi dekomposisi...")

    df = pd.read_csv(file_csv)

    df["Periode"] = pd.to_datetime(df["Periode"])
    df = df.set_index("Periode")

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(12, 11),
        sharex=True
    )

    komponen = [
        (TARGET_COLUMN, "Observed (Kg)"),
        ("Trend_Kg", "Trend (Kg)"),
        ("Seasonal_Kg", "Seasonal (Kg)"),
        ("Residual_Kg", "Residual (Kg)")
    ]

    for i, (kolom, label) in enumerate(komponen):

        axes[i].plot(
            df.index,
            df[kolom],
            marker="o",
            markersize=3,
            linewidth=1.5
        )

        axes[i].set_ylabel(
            label,
            fontweight="bold"
        )

        axes[i].grid(
            True,
            linestyle="--",
            alpha=0.6
        )

        if i >= 2:
            axes[i].axhline(
                0,
                linestyle="--",
                alpha=0.7
            )

    axes[3].xaxis.set_major_formatter(
        mdates.DateFormatter("%b %Y")
    )

    axes[3].xaxis.set_major_locator(
        mdates.MonthLocator(interval=2)
    )

    plt.xticks(rotation=30, ha="right")

    plt.suptitle(
        "Time Series Decomposition "
        "(Additive Model, m=12)",
        fontsize=14,
        fontweight="bold"
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"-> Grafik disimpan: {output_path.name}")


# =============================================================================
# FUNGSI 4: PERHITUNGAN REGRESI DICKY-FULLER SEDERHANA
# =============================================================================

def cetak_tabel_ols_manual(
    y_lag,
    delta_y,
    label="0"
):

    """
    Ilustrasi regresi Dickey-Fuller sederhana:

    Delta Y_t = alpha + gamma * Y_(t-1) + error

    Perhitungan ini BUKAN pengganti ADF resmi,
    karena tidak memasukkan lagged differences.
    """

    n = len(y_lag)

    mean_ylag = np.mean(y_lag)
    mean_dy = np.mean(delta_y)

    dev_ylag = y_lag - mean_ylag
    dev_dy = delta_y - mean_dy

    hasil_kali = dev_ylag * dev_dy
    kuadrat_dev = dev_ylag ** 2

    df_ols = pd.DataFrame({
        "Lag_1": y_lag,
        "Selisih_Diff": delta_y,
        "Dev_Lag1": dev_ylag,
        "Dev_Selisih": dev_dy,
        "Hasil_Kali": hasil_kali,
        "Kuadrat_Dev_Lag1": kuadrat_dev
    })

    print(
        f"\n[TABEL REGRESI DF SEDERHANA - ITERASI d={label}]"
    )

    print(df_ols.head(5).to_string(index=False))
    print("...")

    print(df_ols.tail(3).to_string(index=False))

    num = np.sum(hasil_kali)
    den = np.sum(kuadrat_dev)

    print(f"\nPembilang OLS : {num:.4f}")
    print(f"Penyebut OLS  : {den:.4f}")

    return num, den, mean_ylag, mean_dy, n


# =============================================================================
# FUNGSI 5: EVALUASI HASIL ADF
# =============================================================================

def evaluasi_stasioneritas_dinamis(
    adf_stat,
    p_value,
    crit_dict,
    alpha=0.05
):

    crit_5pct = crit_dict["5%"]

    is_p_valid = p_value < alpha
    is_stat_valid = adf_stat < crit_5pct

    print("\n-----------------------------------------------")
    print(f"EVALUASI UJI ADF (Alpha = {alpha})")
    print("-----------------------------------------------")

    print(
        f"ADF Statistic : {adf_stat:.4f}"
    )

    print(
        f"Critical 5%   : {crit_5pct:.4f}"
    )

    print(
        f"P-value       : {p_value:.6f}"
    )

    if is_p_valid and is_stat_valid:

        print("Keputusan: TOLAK H0.")
        print("Interpretasi: Seri stasioner menurut uji ADF.")

        return True

    else:

        print("Keputusan: GAGAL MENOLAK H0.")
        print("Interpretasi: Bukti stasioneritas belum cukup.")

        return False


# =============================================================================
# FUNGSI 6: UJI STASIONERITAS ADF DAN ITERASI DIFFERENCING
# =============================================================================

def uji_stasioneritas_dan_iterasi_differencing(
    file_csv,
    max_d=2
):

    print("\n================================================")
    print("UJI STASIONERITAS AUGMENTED DICKEY-FULLER")
    print("================================================")

    df = pd.read_csv(file_csv)

    y_original = df[TARGET_COLUMN].astype(float).values

    y_current = y_original.copy()

    for d in range(max_d + 1):

        print("\n-----------------------------------------------")
        print(f"PEMERIKSAAN DIFFERENCING d = {d}")
        print("-----------------------------------------------")

        if len(y_current) < 10:
            raise ValueError(
                "Observasi terlalu sedikit untuk uji ADF."
            )

        # Regresi DF sederhana hanya sebagai ilustrasi.
        y_lag = y_current[:-1]
        delta_y = np.diff(y_current)

        num, den, mean_ylag, mean_dy, n = (
            cetak_tabel_ols_manual(
                y_lag,
                delta_y,
                label=str(d)
            )
        )

        gamma_hat = num / den if den != 0 else 0

        alpha_hat = (
            mean_dy - gamma_hat * mean_ylag
        )

        delta_y_pred = (
            alpha_hat + gamma_hat * y_lag
        )

        residuals = delta_y - delta_y_pred

        ssr = np.sum(residuals ** 2)

        var_resid = (
            ssr / (n - 2)
            if n > 2 else 0
        )

        se_gamma = (
            np.sqrt(var_resid / den)
            if den > 0 else 0
        )

        t_stat_df = (
            gamma_hat / se_gamma
            if se_gamma > 0 else np.nan
        )

        print("\n[ILUSTRASI REGRESI DF SEDERHANA]")
        print(f"Gamma       : {gamma_hat:.6f}")
        print(f"Alpha       : {alpha_hat:.6f}")
        print(f"SSR         : {ssr:.6f}")
        print(f"SE Gamma    : {se_gamma:.6f}")
        print(f"t-stat DF   : {t_stat_df:.6f}")

        # Uji ADF resmi dari Statsmodels.
        adf_res = adfuller(
            y_current,
            maxlag=None,
            regression="c",
            autolag="AIC",
            result_object=False
        )

        adf_stat = adf_res[0]
        p_value = adf_res[1]
        used_lag = adf_res[2]
        n_obs = adf_res[3]
        crit_vals = adf_res[4]

        print("\n[HASIL RESMI AUGMENTED DICKEY-FULLER]")
        print(f"ADF Statistic : {adf_stat:.6f}")
        print(f"P-value       : {p_value:.6f}")
        print(f"Used Lag      : {used_lag}")
        print(f"Observations  : {n_obs}")

        for key, value in crit_vals.items():
            print(f"Critical {key}: {value:.6f}")

        is_stationary = evaluasi_stasioneritas_dinamis(
            adf_stat,
            p_value,
            crit_vals,
            alpha=ALPHA
        )

        if is_stationary:

            print(
                f"\nData dinyatakan stasioner pada d={d} "
                "berdasarkan uji ADF."
            )

            return d, y_current

        if d < max_d:

            print(
                f"\nData belum stasioner. "
                f"Melakukan differencing d={d + 1}."
            )

            y_current = np.diff(y_current)

        else:

            print(
                "\nPeringatan: Data belum stasioner "
                f"hingga d maksimum {max_d}."
            )

            return max_d, y_current


# =============================================================================
# FUNGSI 7: IDENTIFIKASI KANDIDAT ARIMA DAN SARIMA
# =============================================================================

def analisis_acf_pacf_dan_kandidat_model(
    y_stationary,
    d_locked,
    output_path
):

    print("\n================================================")
    print("ANALISIS ACF DAN PACF")
    print("================================================")

    y_stationary = np.asarray(
        y_stationary,
        dtype=float
    )

    n = len(y_stationary)

    if n < 10:
        raise ValueError(
            "Jumlah observasi terlalu sedikit untuk ACF/PACF."
        )

    # Menentukan batas lag secara aman.
    max_lag = min(
        max(4, int(n / 4)),
        15,
        n - 1
    )

    # Lag 12 hanya dianalisis jika observasi memadai.
    if n >= 24:
        max_lag = max(max_lag, 12)

    max_lag = min(max_lag, n - 1)

    mean_z = np.mean(y_stationary)

    dev_z = y_stationary - mean_z

    ss_tot = np.sum(dev_z ** 2)

    print(f"Jumlah observasi : {n}")
    print(f"Mean             : {mean_z:.4f}")
    print(f"Total variasi    : {ss_tot:.4f}")
    print(f"Maximum lag      : {max_lag}")

    # ---------------------------------------------------------
    # ACF DAN INTERVAL KEPERCAYAAN
    # ---------------------------------------------------------

    acf_vals, acf_confint = acf(
        y_stationary,
        nlags=max_lag,
        alpha=ALPHA,
        fft=False,
        bartlett_confint=True,
         result_object=False
    )

    # ---------------------------------------------------------
    # PACF DAN INTERVAL KEPERCAYAAN
    # ---------------------------------------------------------

    pacf_vals, pacf_confint = pacf(
        y_stationary,
        nlags=max_lag,
        alpha=ALPHA,
        method="yw"
    )

    # Interval dikembalikan dalam bentuk batas bawah dan atas
    # yang berpusat pada estimasi ACF/PACF.

    acf_significant = (
        (acf_confint[:, 0] > 0) |
        (acf_confint[:, 1] < 0)
    )

    pacf_significant = (
        (pacf_confint[:, 0] > 0) |
        (pacf_confint[:, 1] < 0)
    )

    # Lag 0 tidak digunakan untuk identifikasi model.
    acf_significant[0] = False
    pacf_significant[0] = False

    # ---------------------------------------------------------
    # TABEL ACF DAN PACF
    # ---------------------------------------------------------

    df_correlogram = pd.DataFrame({

        "Lag_k": np.arange(max_lag + 1),

        "Nilai_ACF": acf_vals,

        "ACF_CI_Bawah": acf_confint[:, 0],

        "ACF_CI_Atas": acf_confint[:, 1],

        "Status_ACF_Signifikan": acf_significant,

        "Nilai_PACF": pacf_vals,

        "PACF_CI_Bawah": pacf_confint[:, 0],

        "PACF_CI_Atas": pacf_confint[:, 1],

        "Status_PACF_Signifikan": pacf_significant

    })

    print("\n[TABEL HASIL ACF DAN PACF]")

    print(
        df_correlogram.to_string(index=False)
    )

    # ---------------------------------------------------------
    # PERHITUNGAN MANUAL ACF LAG 1-4
    # ---------------------------------------------------------

    print("\n[ILUSTRASI PERHITUNGAN ACF MANUAL LAG 1-4]")

    for k in range(1, min(4, max_lag) + 1):

        cov_k = np.sum(
            dev_z[k:] * dev_z[:-k]
        )

        r_k = (
            cov_k / ss_tot
            if ss_tot != 0 else 0
        )

        print(
            f"ACF lag {k}: "
            f"{cov_k:.4f} / {ss_tot:.4f} = {r_k:.4f}"
        )

    # ---------------------------------------------------------
    # PERHITUNGAN MANUAL PACF LAG 1-4
    # ---------------------------------------------------------

    print("\n[ILUSTRASI PERHITUNGAN PACF LAG 1-4]")

    for k in range(1, min(4, max_lag) + 1):

        print(
            f"PACF lag {k} dari Yule-Walker: "
            f"{pacf_vals[k]:.4f}"
        )

    print(
        "\nCatatan: PACF di atas menggunakan hasil "
        "perhitungan Yule-Walker Statsmodels."
    )

    # ---------------------------------------------------------
    # VISUALISASI ACF DAN PACF
    # ---------------------------------------------------------

    print("\n-> Membuat grafik ACF dan PACF...")

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14, 5)
    )

    plot_acf(
        y_stationary,
        ax=axes[0],
        lags=max_lag,
        alpha=ALPHA,
        bartlett_confint=True,
        title="Autocorrelation Function (ACF)"
    )

    plot_pacf(
        y_stationary,
        ax=axes[1],
        lags=max_lag,
        alpha=ALPHA,
        method="yw",
        title="Partial Autocorrelation Function (PACF)"
    )

    axes[0].set_xlabel("Lag")
    axes[1].set_xlabel("Lag")

    axes[0].set_ylabel("ACF")
    axes[1].set_ylabel("PACF")

    axes[0].grid(
        True,
        linestyle="--",
        alpha=0.6
    )

    axes[1].grid(
        True,
        linestyle="--",
        alpha=0.6
    )

    plt.suptitle(
        f"Analisis ACF dan PACF (d={d_locked})",
        fontsize=14,
        fontweight="bold"
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"-> Grafik disimpan: {output_path.name}")

    # ---------------------------------------------------------
    # IDENTIFIKASI LAG SIGNIFIKAN
    # ---------------------------------------------------------

    sig_acf_lags = [
        k for k in range(1, max_lag + 1)
        if acf_significant[k]
    ]

    sig_pacf_lags = [
        k for k in range(1, max_lag + 1)
        if pacf_significant[k]
    ]

    print("\n[IDENTIFIKASI LAG SIGNIFIKAN]")

    print(
        f"ACF signifikan  : {sig_acf_lags}"
    )

    print(
        f"PACF signifikan : {sig_pacf_lags}"
    )

    # ---------------------------------------------------------
    # IDENTIFIKASI POLA NONMUSIMAN
    # ---------------------------------------------------------

    # Orde p dan q tidak ditentukan dari nomor lag terbesar.
    # Kandidat dibuat berorde kecil untuk menghindari
    # kompleksitas parameter yang berlebihan.

    kandidat_pq = [
        (0, 0),
        (1, 0),
        (2, 0),
        (0, 1),
        (0, 2),
        (1, 1),
        (2, 1),
        (1, 2)
    ]

    kandidat_models = [
        (p, d_locked, q)
        for p, q in kandidat_pq
    ]

    print("\n[IDENTIFIKASI KANDIDAT ARIMA]")

    print(
        "ACF/PACF digunakan sebagai dasar "
        "penyaringan pola, bukan penetapan otomatis "
        "orde berdasarkan nomor lag terbesar."
    )

    for idx, model in enumerate(kandidat_models, 1):

        print(
            f"{idx}. ARIMA{model}"
        )

    # ---------------------------------------------------------
    # DETEKSI INDIKASI MUSIMAN LAG 12
    # ---------------------------------------------------------

    seasonal_D = 0
    seasonal_P = 0
    seasonal_Q = 0
    seasonal_m = SEASONAL_PERIOD

    seasonal_detected = False

    acf_12_sig = False
    pacf_12_sig = False

    if max_lag >= SEASONAL_PERIOD:

        acf_12_sig = bool(
            acf_significant[SEASONAL_PERIOD]
        )

        pacf_12_sig = bool(
            pacf_significant[SEASONAL_PERIOD]
        )

        print("\n[PEMERIKSAAN INDIKASI MUSIMAN]")

        print(
            f"ACF lag 12  : "
            f"{acf_vals[12]:.4f}, "
            f"signifikan={acf_12_sig}"
        )

        print(
            f"PACF lag 12 : "
            f"{pacf_vals[12]:.4f}, "
            f"signifikan={pacf_12_sig}"
        )

        seasonal_detected = (
            acf_12_sig or pacf_12_sig
        )

        if seasonal_detected:

            print(
                "Indikasi ketergantungan pada lag 12 "
                "ditemukan."
            )

            print(
                "Hal ini menjadi alasan untuk "
                "menguji kandidat model musiman."
            )

        else:

            print(
                "Tidak ditemukan indikasi signifikan "
                "pada lag 12 berdasarkan interval "
                "kepercayaan yang digunakan."
            )

    else:

        print(
            "\nObservasi belum cukup untuk "
            "pemeriksaan lag 12."
        )

    # ---------------------------------------------------------
    # KANDIDAT SARIMA
    # ---------------------------------------------------------

    # D=0 dan D=1 disiapkan sebagai alternatif pengujian.
    # Keputusan akhir D tidak ditetapkan hanya dari lag 12.

    kandidat_sarima = []

    if seasonal_detected:

        kandidat_sarima = [

            {
                "order": [0, d_locked, 1],
                "seasonal_order": [0, 0, 1, seasonal_m]
            },

            {
                "order": [1, d_locked, 0],
                "seasonal_order": [1, 0, 0, seasonal_m]
            },

            {
                "order": [0, d_locked, 1],
                "seasonal_order": [0, 1, 1, seasonal_m]
            },

            {
                "order": [1, d_locked, 0],
                "seasonal_order": [1, 1, 0, seasonal_m]
            }

        ]

        print("\n[KANDIDAT SARIMA UNTUK DIEVALUASI]")

        for idx, kandidat in enumerate(
            kandidat_sarima,
            1
        ):

            print(
                f"{idx}. SARIMA"
                f"{tuple(kandidat['order'])}"
                f"{tuple(kandidat['seasonal_order'])}"
            )

    else:

        print(
            "\nKandidat SARIMA tidak dibuat otomatis "
            "karena belum ditemukan indikasi lag 12."
        )

    # ---------------------------------------------------------
    # RINGKASAN HASIL
    # ---------------------------------------------------------

    print("\n================================================")
    print("RINGKASAN IDENTIFIKASI MODEL")
    print("================================================")

    print(f"Derajat differencing nonmusiman d : {d_locked}")
    print(f"Indikasi musiman                  : {seasonal_detected}")
    print(f"Periode musiman                   : {seasonal_m}")

    print(
        "D, P, Q belum dikunci secara otomatis. "
        "Nilainya perlu dievaluasi pada tahap pemodelan."
    )

    return (
        kandidat_models,
        seasonal_D,
        seasonal_P,
        seasonal_Q,
        seasonal_m,
        kandidat_sarima,
        seasonal_detected
    )


# =============================================================================
# FUNGSI 8: MENYIMPAN KONFIGURASI MODEL KE JSON
# =============================================================================

def simpan_konfigurasi_model(
    output_json,
    d_locked,
    seasonal_D,
    seasonal_P,
    seasonal_Q,
    seasonal_m,
    kandidat_models,
    kandidat_sarima=None,
    seasonal_detected=False
):

    print("\n-> Menyimpan konfigurasi model...")

    kandidat_list = [
        list(model)
        for model in kandidat_models
    ]

    config_data = {

        "derajat_pembedaan_non_musiman_d": int(
            d_locked
        ),

        "derajat_pembedaan_musiman_D": int(
            seasonal_D
        ),

        "parameter_ar_musiman_P": int(
            seasonal_P
        ),

        "parameter_ma_musiman_Q": int(
            seasonal_Q
        ),

        "periode_musiman_m": int(
            seasonal_m
        ),

        "indikasi_pola_musiman": bool(
            seasonal_detected
        ),

        "daftar_kandidat_p_d_q": kandidat_list,

        "daftar_kandidat_sarima": (
            kandidat_sarima or []
        ),

        "catatan_metodologi": (
            "Lag signifikan tidak otomatis "
            "menjadi orde p atau q. "
            "Keputusan differencing musiman D "
            "harus dievaluasi terpisah."
        )

    }

    with open(
        output_json,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            config_data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"-> Konfigurasi berhasil disimpan: "
        f"{output_json.name}"
    )


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    penjelasan.mulai("05_eksplorasi_data")

    print("================================================")
    print(" PROGRAM EKSPLORASI DATA DAN IDENTIFIKASI MODEL")
    print("================================================")

    try:

        # 1. Dekomposisi.
        tabel_csv = hitung_dan_ekspor_tabel(
            INPUT_FILE,
            OUTPUT_CSV
        )

        # 2. Visualisasi time series.
        visualisasi_time_series_dari_tabel(
            tabel_csv,
            OUTPUT_IMAGE_TS
        )

        # 3. Visualisasi dekomposisi.
        visualisasi_dekomposisi_dari_tabel(
            tabel_csv,
            OUTPUT_IMAGE_DEC
        )

        # 4. Uji ADF dan penentuan d.
        d_locked, y_stationary = (
            uji_stasioneritas_dan_iterasi_differencing(
                tabel_csv,
                max_d=2
            )
        )

        # 5. Analisis ACF/PACF dan identifikasi kandidat.
        (
            kandidat_models,
            seasonal_D,
            seasonal_P,
            seasonal_Q,
            seasonal_m,
            kandidat_sarima,
            seasonal_detected
        ) = analisis_acf_pacf_dan_kandidat_model(
            y_stationary,
            d_locked,
            OUTPUT_IMAGE_ACF_PACF
        )

        # Contoh perhitungan rumus [4] ADF/differencing dan [5] ACF/PACF.
        df_asli = pd.read_csv(INPUT_FILE, parse_dates=["Periode"])
        penjelasan.jelaskan_05(df_asli[TARGET_COLUMN].values, list(df_asli["Periode"]))

        # 6. Ekspor konfigurasi.
        simpan_konfigurasi_model(
            OUTPUT_CONFIG_JSON,
            d_locked,
            seasonal_D,
            seasonal_P,
            seasonal_Q,
            seasonal_m,
            kandidat_models,
            kandidat_sarima,
            seasonal_detected
        )

        print("\n================================================")
        print("EDA SELESAI")
        print("================================================")

        print(f"d                  : {d_locked}")
        print(f"D                  : {seasonal_D}")
        print(f"P                  : {seasonal_P}")
        print(f"Q                  : {seasonal_Q}")
        print(f"m                  : {seasonal_m}")

        print(
            f"Jumlah kandidat ARIMA : "
            f"{len(kandidat_models)}"
        )

        print(
            f"Jumlah kandidat SARIMA: "
            f"{len(kandidat_sarima)}"
        )

        print(
            "\nSeluruh hasil EDA dan konfigurasi "
            "berhasil dibuat."
        )

    except Exception as e:

        print(
            f"\n[ERROR] Terjadi kesalahan: {e}"
        )

        raise


if __name__ == "__main__":
    main()
