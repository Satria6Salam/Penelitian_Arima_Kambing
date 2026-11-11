"""
=============================================================================
PROGRAM ESTIMASI PARAMETER, VALIDASI DIAGNOSTIK, DAN EVALUASI KINERJA
File: 07_validasi_diagnostik_evaluasi.py

Ruang lingkup (mengikuti dokumen ALUR PENELITIAN FINAL):
1. Estimasi parameter model dengan SARIMAX statsmodels (konfigurasi sama
   dengan script 06): koefisien, std error, z, p-value, interval 95%,
   log-likelihood, AIC, BIC. Termasuk pengecekan optimum lokal dengan
   beberapa optimizer (hanya dicatat, output script 06 tidak diubah).
2. Diagnostik residual model shortlist pada data training:
   Ljung-Box (white noise), Shapiro-Wilk, dan Q-Q plot.
3. Time Series Cross-Validation rolling origin (walk-forward) pada 9 bulan
   testing: latih -> ramal 1 bulan -> tambah aktual -> latih ulang penuh.
4. Metrik akurasi rolling origin: MAPE, RMSE, MAE, MSE, R² vs target,
   dengan seasonal naive sebagai pembanding.
5. Rekomendasi model berdasarkan diagnostik + metrik rolling origin.

Peramalan multi-step pada data testing dikerjakan di script 08.

Estimasi memakai modul bersama estimasi_model.py (sama dengan script 06):
transformasi data (estimasi_model.TRANSFORMASI, versi final: log),
multi-optimizer + polish.
Prediksi dan metrik dikembalikan ke satuan kg.
Perbandingan dengan versi sebelumnya: perbandingan_versi_estimasi.md

Input  : data/hasil_06 (hanya dibaca)
Output : data/hasil_07/ dan 07_ringkasan_validasi.md
=============================================================================
"""

import ast
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels

from pathlib import Path
from scipy import stats
from statsmodels.graphics.gofplots import qqplot
from statsmodels.stats.diagnostic import acorr_ljungbox

import keterangan_csv as kk  # keterangan kolom pada setiap CSV hasil
import estimasi_model as em
import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/


# =============================================================================
# PENGATURAN PATH DIREKTORI
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_DIR = DATA_DIR / "hasil_06"
TRAIN_CSV = INPUT_DIR / "06_training_set.csv"
TEST_CSV = INPUT_DIR / "06_testing_set.csv"
AIC_BIC_CSV = INPUT_DIR / "06_perbandingan_aic_bic.csv"

OUTPUT_DIR = DATA_DIR / "hasil_07"
GRAFIK_DIR = OUTPUT_DIR / "grafik"

PARAMETER_CSV = OUTPUT_DIR / "07_parameter_estimasi.csv"
OPTIMUM_CSV = OUTPUT_DIR / "07_cek_optimum_lokal.csv"
SHORTLIST_CSV = OUTPUT_DIR / "07_shortlist.csv"
SUMMARY_TXT = OUTPUT_DIR / "07_summary_shortlist.txt"
DIAGNOSTIK_CSV = OUTPUT_DIR / "07_diagnostik_residual.csv"
ROLLING_CSV = OUTPUT_DIR / "07_rolling_origin_prediksi.csv"
METRIK_CSV = OUTPUT_DIR / "07_metrik_rolling_origin.csv"
RINGKASAN_MD = BASE_DIR / "07_ringkasan_validasi.md"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
GRAFIK_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# KONSTANTA PENELITIAN
# =============================================================================

TARGET_COL = "Total_Kuantitas_Kg"
M = 12

# Perbaikan LogL (multi-optimizer vs lbfgs default) yang dicatat sebagai optimum lokal
AMBANG_PERBAIKAN_LLF = 0.01

ALPHA = 0.05
LJUNG_BOX_LAGS = [6, 9, 12]

# Shortlist: model AIC terendah per skenario di dalam kelompok (d, D)-nya.
# (label, Skenario di CSV 06, kelompok differencing, isi kolom Eksogen)
VARIAN_SKENARIO = [
    ("ARIMA", "ARIMA", "d=0, D=0", "-"),
    ("SARIMA D=0", "SARIMA", "d=0, D=0", "-"),
    ("SARIMA D=1", "SARIMA", "d=0, D=1", "-"),
    ("ARIMAX Harga", "ARIMAX", "d=0, D=0", "Harga_Rata2_Per_Kg"),
    ("ARIMAX Harga+Iduladha", "ARIMAX", "d=0, D=0",
     "Harga_Rata2_Per_Kg, Koefisien_Musim"),
]

LABEL_NAIVE = "Seasonal naive"

# Target akurasi: RMSE/MAE/MSE relatif terhadap rata-rata aktual (estimasi_model.py)
METRIK_TARGET = ["MAPE_%", "RMSE", "MAE", "MSE", "R2"]

# Model yang membutuhkan nilai eksogen masa depan (harga, label Iduladha) tidak
# bisa dipakai untuk peramalan nyata ke depan, karena harga bulan depan belum
# diketahui. Model ini tetap dievaluasi sebagai pembanding, tetapi model final
# untuk peramalan dipilih dari model tanpa eksogen.
SYARAT_TANPA_EKSOGEN = True


# =============================================================================
# FUNGSI BANTUAN
# =============================================================================

def fit_model(y, exog, order, seasonal_order):
    """Estimasi multi-optimizer yang sama dengan script 06 (data transformasi)."""
    return em.fit_terbaik(y, exog, order, seasonal_order)


def hitung_metrik(aktual, prediksi):
    aktual = np.asarray(aktual, dtype=float)
    prediksi = np.asarray(prediksi, dtype=float)
    error = aktual - prediksi
    mse = float(np.mean(error ** 2))
    sst = float(np.sum((aktual - aktual.mean()) ** 2))
    return {
        "MAE": float(np.mean(np.abs(error))),
        "MSE": mse,
        "RMSE": float(np.sqrt(mse)),
        "MAPE_%": float(np.mean(np.abs(error / aktual)) * 100),
        "R2": float(1 - np.sum(error ** 2) / sst) if sst > 0 else np.nan,
    }


def teks_target(target, rata2):
    return (f"ȳ = {rata2:,.0f} kg → MAPE < {target['MAPE_%'][1]:g}%, "
            f"RMSE < {target['RMSE'][1]:,.0f} kg, MAE < {target['MAE'][1]:,.0f} kg, "
            f"MSE < {target['MSE'][1]:,.0f} kg², R² > {target['R2'][1]:g}")


def nama_file(teks):
    for a, b in [(" ", "_"), ("+", "plus"), ("=", ""), ("(", ""), (")", ""), (",", "")]:
        teks = teks.replace(a, b)
    return teks


# =============================================================================
# TAHAP 1: MEMUAT DATA
# =============================================================================

def muat_data():
    print("\n" + "=" * 75)
    print("TAHAP 1: MEMUAT DATA DARI HASIL SCRIPT 06 (HANYA DIBACA)")
    print("=" * 75)

    for f in [TRAIN_CSV, TEST_CSV, AIC_BIC_CSV]:
        if not f.exists():
            raise FileNotFoundError(
                f"File tidak ditemukan: {f}. Jalankan 06_pemodelan_forecasting.py dulu."
            )

    train = kk.baca_csv(TRAIN_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    test = kk.baca_csv(TEST_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    df_aic = kk.baca_csv(AIC_BIC_CSV)

    kandidat = []
    for _, r in df_aic[df_aic["Status"] != "Gagal"].iterrows():
        kandidat.append({
            "Skenario": r["Skenario"],
            "Nama_Model": r["Nama_Model"],
            "order": ast.literal_eval(r["Order"]),
            "seasonal_order": ast.literal_eval(r["Seasonal_Order"]),
            "exog": [] if r["Eksogen"] == "-" else [e.strip() for e in r["Eksogen"].split(",")],
            "Eksogen": r["Eksogen"],
            "Kelompok": r["Kelompok_Differencing"],
            "LLF_06": float(r["Log_Likelihood"]),
            "AIC_06": float(r["AIC"]),
            "BIC_06": float(r["BIC"]),
        })

    print(f"Training : {len(train)} obs ({train.index[0]:%b %Y} - {train.index[-1]:%b %Y})")
    print(f"Testing  : {len(test)} obs ({test.index[0]:%b %Y} - {test.index[-1]:%b %Y})")
    print(f"Kandidat : {len(kandidat)} model dari {AIC_BIC_CSV.name}")
    return train, test, kandidat


# =============================================================================
# TAHAP 2: ESTIMASI PARAMETER DAN CEK OPTIMUM LOKAL
# =============================================================================

def estimasi_parameter(train, kandidat):
    print("\n" + "=" * 75)
    print("TAHAP 2: ESTIMASI PARAMETER (MLE SARIMAX, MULTI-OPTIMIZER)")
    print("=" * 75)
    print(f"Transformasi: {em.TRANSFORMASI} ({em.DESKRIPSI_TRANSFORMASI}).")

    data = em.skala_data(train)
    y = data[TARGET_COL]
    baris_param, baris_opt = [], []
    hasil_fit = {}

    for k in kandidat:
        exog = data[k["exog"]].astype(float) if k["exog"] else None
        result, info = fit_model(y, exog, k["order"], k["seasonal_order"])
        hasil_fit[k["Nama_Model"]] = result

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ci = result.conf_int(alpha=ALPHA)
            bse, zval, pval = result.bse, result.zvalues, result.pvalues

        for param in result.params.index:
            p = float(pval[param])
            baris_param.append({
                "Nama_Model": k["Nama_Model"],
                "Kelompok": k["Kelompok"],
                "Parameter": param,
                "Koefisien": float(result.params[param]),
                "Std_Error": float(bse[param]),
                "z": float(zval[param]),
                "P_value": p,
                "CI95_Bawah": float(ci.loc[param].iloc[0]),
                "CI95_Atas": float(ci.loc[param].iloc[1]),
                "Signifikan_5%": (
                    "-" if param == "sigma2" or not np.isfinite(p)
                    else ("Ya" if p < ALPHA else "Tidak")
                ),
                "LogL": float(result.llf),
                "AIC": float(result.aic),
                "BIC": float(result.bic),
            })

        llf_lbfgs = info.get("LogL_lbfgs", np.nan)
        perbaikan = float(result.llf) - llf_lbfgs
        baris_opt.append({
            "Nama_Model": k["Nama_Model"],
            "Kelompok": k["Kelompok"],
            "LogL_06": k["LLF_06"],
            "LogL_07": float(result.llf),
            **{kk: v for kk, v in info.items() if kk.startswith("LogL_")},
            "Optimizer_Terpilih": info["Optimizer_Terpilih"],
            "Dipoles_lbfgs": info["Dipoles_lbfgs"],
            "SE_Valid": info["SE_Valid"],
            "Konvergen": info["Konvergen"],
            "Perbaikan_vs_lbfgs_default": perbaikan,
            "Optimum_lokal_lbfgs": "Ya" if perbaikan > AMBANG_PERBAIKAN_LLF else "Tidak",
            "Warning_Fit": info["Warning"],
        })

    df_param = pd.DataFrame(baris_param)
    df_opt = pd.DataFrame(baris_opt)
    kk.simpan_csv(df_param, PARAMETER_CSV, index=False)
    kk.simpan_csv(df_opt, OPTIMUM_CSV, index=False)

    selisih_06 = (df_opt["LogL_07"] - df_opt["LogL_06"]).abs().max()
    print(f"Konsistensi dengan script 06   : selisih LogL maks {selisih_06:.2e}")
    print(f"Std error tidak valid          : {int((~df_opt['SE_Valid']).sum())} model")
    print(f"Tidak konvergen                : {int((df_opt['Konvergen'] == False).sum())} model")
    print(f"Parameter tidak signifikan (p >= {ALPHA}) : "
          f"{int((df_param['Signifikan_5%'] == 'Tidak').sum())} dari "
          f"{int((df_param['Signifikan_5%'] != '-').sum())}")
    lokal = df_opt[df_opt["Optimum_lokal_lbfgs"] == "Ya"]
    print(f"Model yang lbfgs default-nya masih di optimum lokal (diperbaiki): {len(lokal)}")
    if not lokal.empty:
        print(lokal[["Nama_Model", "LogL_lbfgs", "LogL_07", "Optimizer_Terpilih",
                     "Perbaikan_vs_lbfgs_default"]].to_string(
            index=False, float_format=lambda x: f"{x:.4f}"))

    print(f"\nTabel parameter disimpan ke : {PARAMETER_CSV}")
    print(f"Log optimizer disimpan ke   : {OPTIMUM_CSV}")
    return df_param, df_opt, hasil_fit


# =============================================================================
# TAHAP 3: SHORTLIST DAN DIAGNOSTIK RESIDUAL
# =============================================================================

def pilih_shortlist(kandidat):
    print("\n" + "=" * 75)
    print("TAHAP 3: SHORTLIST (AIC TERENDAH PER SKENARIO DALAM KELOMPOK d, D)")
    print("=" * 75)

    shortlist = []
    for label, skenario, kelompok, eksogen in VARIAN_SKENARIO:
        isi = [k for k in kandidat
               if k["Skenario"] == skenario and k["Kelompok"] == kelompok
               and k["Eksogen"] == eksogen]
        if not isi:
            print(f"- {label:<22}: tidak ada kandidat")
            continue
        terpilih = min(isi, key=lambda k: k["AIC_06"])
        shortlist.append({**terpilih, "Label": label})
        print(f"- {label:<22}: {terpilih['Nama_Model']:<36} AIC {terpilih['AIC_06']:.4f}")

    kk.simpan_csv(pd.DataFrame([{
        "Label": s["Label"], "Nama_Model": s["Nama_Model"], "Kelompok": s["Kelompok"],
        "Order": str(s["order"]), "Seasonal_Order": str(s["seasonal_order"]),
        "Eksogen": s["Eksogen"], "AIC_06": s["AIC_06"], "BIC_06": s["BIC_06"],
    } for s in shortlist]), SHORTLIST_CSV, index=False)
    return shortlist


def diagnostik_residual(shortlist, hasil_fit):
    print("\n" + "=" * 75)
    print("TAHAP 4: DIAGNOSTIK RESIDUAL (LJUNG-BOX, SHAPIRO-WILK, Q-Q PLOT)")
    print("=" * 75)

    baris = []
    teks_summary = []

    for s in shortlist:
        result = hasil_fit[s["Nama_Model"]]
        teks_summary.append("=" * 78 + f"\n{s['Label']}: {s['Nama_Model']}\n"
                            + "=" * 78 + "\n" + str(result.summary()) + "\n\n")

        # Buang residual burn-in (penting untuk D=1)
        burn = int(result.loglikelihood_burn)
        resid = result.resid.iloc[burn:]
        n_resid = len(resid)

        p, _, q = s["order"]
        P, _, Q, _ = s["seasonal_order"]
        model_df = p + q + P + Q

        info = {"Label": s["Label"], "Nama_Model": s["Nama_Model"],
                "Residual_Dibuang_Burn": burn, "Jumlah_Residual": n_resid,
                "model_df": model_df}

        lag_diuji, lag_dilewati, lulus_lb = [], [], True
        for lag in LJUNG_BOX_LAGS:
            df_uji = lag - model_df
            if df_uji <= 0 or lag >= n_resid:
                lag_dilewati.append(lag)
                info[f"LB_Q_lag{lag}"] = np.nan
                info[f"LB_df_lag{lag}"] = df_uji
                info[f"LB_p_lag{lag}"] = np.nan
                continue
            lb = acorr_ljungbox(resid, lags=[lag], model_df=model_df, return_df=True)
            q_stat = float(lb["lb_stat"].iloc[0])
            p_val = float(lb["lb_pvalue"].iloc[0])
            info[f"LB_Q_lag{lag}"] = q_stat
            info[f"LB_df_lag{lag}"] = df_uji
            info[f"LB_p_lag{lag}"] = p_val
            lag_diuji.append(lag)
            if p_val < ALPHA:
                lulus_lb = False

        info["LB_lag_diuji"] = ", ".join(map(str, lag_diuji)) or "-"
        info["LB_lag_dilewati"] = ", ".join(map(str, lag_dilewati)) or "-"
        info["Ljung_Box"] = ("Lulus" if lulus_lb else "Gagal") if lag_diuji else "-"

        sw_stat, sw_p = stats.shapiro(resid)
        info["Shapiro_W"] = float(sw_stat)
        info["Shapiro_p"] = float(sw_p)
        info["Shapiro_Wilk"] = "Lulus" if sw_p > ALPHA else "Gagal"
        baris.append(info)

        fig, ax = plt.subplots(figsize=(5, 5))
        qqplot(resid, line="s", ax=ax)
        ax.set_title(f"Q-Q Plot Residual\n{s['Nama_Model']}", fontsize=10)
        fig.tight_layout()
        fig.savefig(GRAFIK_DIR / f"07_qq_{nama_file(s['Label'])}.png", dpi=150)
        plt.close(fig)

        print(f"\n{s['Label']} - {s['Nama_Model']}")
        print(f"  Residual: {n_resid} (burn-in dibuang {burn}), model_df = {model_df}")
        for lag in LJUNG_BOX_LAGS:
            if lag in lag_diuji:
                print(f"  Ljung-Box lag {lag:<2}: Q = {info[f'LB_Q_lag{lag}']:.3f}, "
                      f"df = {info[f'LB_df_lag{lag}']}, p = {info[f'LB_p_lag{lag}']:.4f}")
            else:
                print(f"  Ljung-Box lag {lag:<2}: dilewati (df <= 0 atau lag >= n residual)")
        print(f"  Ljung-Box            : {info['Ljung_Box']}")
        print(f"  Shapiro-Wilk         : W = {sw_stat:.4f}, p = {sw_p:.4f} -> {info['Shapiro_Wilk']}")

    SUMMARY_TXT.write_text("".join(teks_summary), encoding="utf-8")
    df = pd.DataFrame(baris)
    kk.simpan_csv(df, DIAGNOSTIK_CSV, index=False)
    print(f"\nDiagnostik disimpan ke : {DIAGNOSTIK_CSV}")
    print(f"Q-Q plot disimpan ke   : {GRAFIK_DIR}")
    return df


# =============================================================================
# TAHAP 5: ROLLING ORIGIN DAN METRIK
# =============================================================================

def rolling_origin(train, test, shortlist):
    print("\n" + "=" * 75)
    print("TAHAP 5: TIME SERIES CROSS-VALIDATION (ROLLING ORIGIN)")
    print("=" * 75)
    print(f"Latih awal {len(train)} bulan, ramal 1 bulan, tambah aktual, "
          f"latih ulang penuh; {len(test)} putaran.")

    data_all = pd.concat([train, test])
    data_skala = em.skala_data(data_all)
    y_all = data_all[TARGET_COL].astype(float)          # kg (aktual dan naive)
    y_skala = data_skala[TARGET_COL]                     # data transformasi (estimasi)
    n_train = len(train)
    baris = []

    for s in shortlist:
        for i in range(len(test)):
            batas = n_train + i
            exog_latih = data_skala[s["exog"]].iloc[:batas].astype(float) if s["exog"] else None
            exog_next = data_skala[s["exog"]].iloc[batas:batas + 1].astype(float) if s["exog"] else None
            res_i, info_i = fit_model(y_skala.iloc[:batas], exog_latih,
                                      s["order"], s["seasonal_order"])
            pred_skala = float(res_i.get_forecast(steps=1, exog=exog_next).predicted_mean.iloc[0])
            pred = float(em.ke_kg(pred_skala))
            aktual = float(y_all.iloc[batas])
            baris.append({
                "Label": s["Label"], "Nama_Model": s["Nama_Model"], "Putaran": i + 1,
                "Panjang_Data_Latih": batas,
                "Periode_Target": y_all.index[batas].strftime("%Y-%m"),
                "Aktual": aktual, "Prediksi": pred, "Error": aktual - pred,
                "APE_%": abs(aktual - pred) / aktual * 100,
                "Optimizer": info_i["Optimizer_Terpilih"],
                "Konvergen": info_i["Konvergen"],
                "Warning": info_i["Warning"],
            })
        print(f"- {s['Label']:<22} selesai")

    # Pembanding seasonal naive: y_hat(t) = y(t - 12)
    for i in range(len(test)):
        batas = n_train + i
        aktual = float(y_all.iloc[batas])
        pred = float(y_all.iloc[batas - M])
        baris.append({
            "Label": LABEL_NAIVE, "Nama_Model": "y[t-12]", "Putaran": i + 1,
            "Panjang_Data_Latih": batas,
            "Periode_Target": y_all.index[batas].strftime("%Y-%m"),
            "Aktual": aktual, "Prediksi": pred, "Error": aktual - pred,
            "APE_%": abs(aktual - pred) / aktual * 100,
            "Optimizer": "-", "Konvergen": None, "Warning": "-",
        })
    print(f"- {LABEL_NAIVE:<22} selesai (pembanding)")

    df = pd.DataFrame(baris)
    kk.simpan_csv(df, ROLLING_CSV, index=False)
    print(f"\nPrediksi per putaran disimpan ke: {ROLLING_CSV}")
    return df


def hitung_metrik_rolling(df_roll):
    print("\n" + "=" * 75)
    print("TAHAP 6: METRIK AKURASI ROLLING ORIGIN VS TARGET")
    print("=" * 75)

    rata2 = float(df_roll.drop_duplicates("Periode_Target")["Aktual"].mean())
    target = em.target_akurasi(rata2)
    print(f"Target relatif: {teks_target(target, rata2)}")

    baris = []
    for label, isi in df_roll.groupby("Label", sort=False):
        met = hitung_metrik(isi["Aktual"], isi["Prediksi"])
        info = {"Label": label, "Nama_Model": isi["Nama_Model"].iloc[0], **met,
                "APE_maks_%": float(isi["APE_%"].max()),
                "APE_std_%": float(isi["APE_%"].std(ddof=1)),
                "RMSE_%_rata2": met["RMSE"] / rata2 * 100,
                "MAE_%_rata2": met["MAE"] / rata2 * 100}
        for nama in METRIK_TARGET:
            info[f"Target_{nama}"] = em.cek_target(target, nama, met[nama])
        baris.append(info)

    df = pd.DataFrame(baris)
    mape_naive = df.loc[df["Label"] == LABEL_NAIVE, "MAPE_%"]
    if mape_naive.empty:
        df["Lebih_baik_dari_naive"] = "-"
    else:
        df["Lebih_baik_dari_naive"] = np.where(
            df["MAPE_%"] < float(mape_naive.iloc[0]), "Ya", "Tidak")
    df.loc[df["Label"] == LABEL_NAIVE, "Lebih_baik_dari_naive"] = "-"
    df = df.sort_values("MAPE_%")
    kk.simpan_csv(df, METRIK_CSV, index=False)

    print(df[["Label", "MAPE_%", "RMSE", "MAE", "MSE", "R2", "APE_maks_%"]].to_string(
        index=False, float_format=lambda x: f"{x:,.3f}"))
    print("\nCATATAN: target RMSE/MAE/MSE relatif terhadap rata-rata permintaan aktual,")
    print("sehingga tidak bergantung skala data (agregat Kabupaten Malang).")
    print(f"\nMetrik disimpan ke: {METRIK_CSV}")
    return df


def grafik_rolling(train, df_roll):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(train.index, train[TARGET_COL], color="black", label="Aktual (training)")
    aktual = df_roll.drop_duplicates("Periode_Target")
    idx = pd.to_datetime(aktual["Periode_Target"])
    ax.plot(idx, aktual["Aktual"], color="black", marker="o", label="Aktual (testing)")
    for label, isi in df_roll.groupby("Label", sort=False):
        ax.plot(pd.to_datetime(isi["Periode_Target"]), isi["Prediksi"],
                linestyle="--", marker=".", label=label)
    ax.axvline(idx.iloc[0], color="grey", linewidth=0.8)
    ax.set_title("Prediksi Rolling Origin 1 Bulan ke Depan vs Aktual")
    ax.set_xlabel("Periode")
    ax.set_ylabel("Permintaan (kg)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(GRAFIK_DIR / "07_rolling_origin_vs_aktual.png", dpi=150)
    plt.close(fig)


# =============================================================================
# TAHAP 7: REKOMENDASI MODEL
# =============================================================================

def rekomendasi_model(df_diag, df_metrik):
    """
    Aturan:
    1. Layak statistik = lulus Ljung-Box (semua lag yang diuji) DAN Shapiro-Wilk,
       serta MAPE rolling origin lebih baik dari seasonal naive.
    2. Layak peramalan = layak statistik DAN tidak membutuhkan variabel eksogen
       masa depan (SYARAT_TANPA_EKSOGEN). Harga bulan depan belum diketahui saat
       meramal, sehingga ARIMAX hanya menjadi pembanding (akurasinya optimistis
       karena memakai harga aktual periode testing).
    3. Model final = layak peramalan dengan MAPE rolling origin terendah (RMSE
       sebagai pemecah seri).
    4. Jika tidak ada kandidat layak peramalan, pilih model tanpa eksogen dengan
       jumlah lulus diagnostik terbanyak lalu MAPE terendah (status bersyarat).
    AIC tidak dipakai lintas kelompok (d, D).
    """
    print("\n" + "=" * 75)
    print("TAHAP 7: REKOMENDASI MODEL")
    print("=" * 75)

    eksogen = {label: eks for label, _, _, eks in VARIAN_SKENARIO}
    df = df_diag[["Label", "Nama_Model", "Ljung_Box", "Shapiro_Wilk"]].merge(
        df_metrik[["Label", "MAPE_%", "RMSE", "R2", "Lebih_baik_dari_naive"]], on="Label")
    df["Butuh_Eksogen_Masa_Depan"] = np.where(df["Label"].map(eksogen) != "-", "Ya", "Tidak")
    df["Jumlah_Lulus_Diagnostik"] = (
        (df["Ljung_Box"] == "Lulus").astype(int) + (df["Shapiro_Wilk"] == "Lulus").astype(int)
    )
    df["Layak_Statistik"] = (df["Jumlah_Lulus_Diagnostik"] == 2) & (df["Lebih_baik_dari_naive"] == "Ya")
    bisa_ramal = (df["Butuh_Eksogen_Masa_Depan"] == "Tidak") if SYARAT_TANPA_EKSOGEN else True
    df["Layak_Peramalan"] = df["Layak_Statistik"] & bisa_ramal

    layak_stat = df[df["Layak_Statistik"]].sort_values(["MAPE_%", "RMSE"])
    terbaik_evaluasi = layak_stat.iloc[0] if not layak_stat.empty else None

    layak = df[df["Layak_Peramalan"]].sort_values(["MAPE_%", "RMSE"])
    if not layak.empty:
        pilih = layak.iloc[0]
        status = "Model final untuk peramalan"
        alasan = ("lulus Ljung-Box dan Shapiro-Wilk, lebih baik dari seasonal naive, tidak "
                  "membutuhkan nilai eksogen masa depan, dan memiliki MAPE rolling origin "
                  "terendah di antara model yang memenuhi syarat tersebut")
    else:
        calon = df[bisa_ramal] if SYARAT_TANPA_EKSOGEN else df
        pilih = calon.sort_values(["Jumlah_Lulus_Diagnostik", "MAPE_%"],
                                  ascending=[False, True]).iloc[0]
        status = "Model final bersyarat"
        alasan = ("tidak ada model tanpa eksogen yang lulus seluruh syarat; dipilih model "
                  "dengan diagnostik terbaik lalu MAPE rolling origin terendah")

    urutan = df.sort_values(["Layak_Peramalan", "Layak_Statistik", "Jumlah_Lulus_Diagnostik",
                             "MAPE_%"], ascending=[False, False, False, True]).reset_index(drop=True)
    urutan["Peringkat"] = range(1, len(urutan) + 1)

    print(urutan[["Peringkat", "Label", "Ljung_Box", "Shapiro_Wilk", "MAPE_%", "RMSE",
                  "Butuh_Eksogen_Masa_Depan", "Layak_Statistik", "Layak_Peramalan"]].to_string(
        index=False, float_format=lambda x: f"{x:,.3f}"))
    if terbaik_evaluasi is not None and terbaik_evaluasi["Label"] != pilih["Label"]:
        print(f"\nMAPE terendah (evaluasi): {terbaik_evaluasi['Label']} "
              f"({terbaik_evaluasi['MAPE_%']:.2f}%), tetapi membutuhkan eksogen masa depan.")
    print(f"\n{status}: {pilih['Label']} - {pilih['Nama_Model']}")
    print(f"Alasan: {alasan}.")

    return urutan, pilih, status, alasan, terbaik_evaluasi


# =============================================================================
# RINGKASAN MARKDOWN
# =============================================================================

def tabel_markdown(df, kolom, fmt="{:,.3f}"):
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "-" if not np.isfinite(v) else fmt.format(v)
        return str(v)
    baris = ["| " + " | ".join(kolom) + " |", "|" + "|".join(["---"] * len(kolom)) + "|"]
    for _, r in df.iterrows():
        baris.append("| " + " | ".join(f(r[k]) for k in kolom) + " |")
    return "\n".join(baris)


def tulis_ringkasan(df_param, df_opt, shortlist, df_diag, df_roll, df_metrik,
                    urutan, pilih, status, alasan, terbaik_evaluasi=None):
    L = []
    L.append("# Ringkasan Script 07: Estimasi Parameter, Validasi Diagnostik, dan Evaluasi Kinerja\n")
    L.append(f"Dibuat otomatis oleh `07_validasi_diagnostik_evaluasi.py` "
             f"(statsmodels {statsmodels.__version__}). Konfigurasi estimasi sama dengan "
             "script 06 (`enforce_stationarity=True`, `enforce_invertibility=True`, "
             "modul `estimasi_model.py`).\n")

    L.append("## Transformasi dan metode estimasi\n")
    L.append(f"- Transformasi: `{em.TRANSFORMASI}` ({em.DESKRIPSI_TRANSFORMASI}); dihitung di "
             "dalam script, file data tidak diubah.")
    L.append("- Alasan: (1) pada skala kg (permintaan ±100.000, varians residual ±1e9) optimizer "
             "L-BFGS sering berhenti di optimum lokal dan std error tidak stabil; (2) lonjakan "
             "Iduladha bersifat perkalian (×2,717), sehingga residual model level di bulan Juni "
             "sangat besar dan seluruh model level gagal Shapiro-Wilk. Transformasi log "
             "mengubah efek perkalian menjadi penjumlahan, sesuai saran dokumen alur. Hasil "
             "level dan versi lain dirangkum di `perbandingan_versi_estimasi.md`.")
    L.append(f"- Setiap model di-fit dengan {', '.join(m for m, _ in em.OPTIMIZER)} serta "
             "Nelder-Mead dari tiga nilai awal AR/MA (0; +0,3; −0,3). Dipilih LogL tertinggi "
             "yang konvergen dengan std error valid, lalu di-polish dengan lbfgs.")
    L.append("- Koefisien, std error, LogL, AIC, BIC, dan residual (bagian 1–3) berskala data "
             "transformasi. Prediksi rolling origin dikembalikan ke **kg** (exp dari ramalan "
             "log = median ramalan), dan seluruh metrik bagian 4 dalam **kg**.\n")

    L.append("## 1. Parameter model shortlist\n")
    L.append("Shortlist = AIC terendah per skenario di dalam kelompok (d, D)-nya. "
             "Tabel seluruh 28 kandidat: `data/hasil_07/07_parameter_estimasi.csv`; "
             "summary lengkap: `data/hasil_07/07_summary_shortlist.txt`. "
             f"Satuan: data transformasi `{em.TRANSFORMASI}` "
             "(pada model log, koefisien harga = elastisitas permintaan terhadap harga).\n")
    nama_short = [s["Nama_Model"] for s in shortlist]
    label_map = {s["Nama_Model"]: s["Label"] for s in shortlist}
    tp = df_param[df_param["Nama_Model"].isin(nama_short)].copy()
    tp.insert(0, "Label", tp["Nama_Model"].map(label_map))
    L.append(tabel_markdown(tp, ["Label", "Nama_Model", "Parameter", "Koefisien", "Std_Error",
                                 "z", "P_value", "CI95_Bawah", "CI95_Atas", "Signifikan_5%"],
                            "{:,.4f}"))
    L.append("")
    ic = tp.drop_duplicates("Nama_Model")[["Label", "Nama_Model", "LogL", "AIC", "BIC"]]
    L.append(tabel_markdown(ic, ["Label", "Nama_Model", "LogL", "AIC", "BIC"], "{:,.4f}"))
    L.append("")

    L.append("## 2. Validitas estimasi dan optimum lokal\n")
    L.append(f"- Konsistensi dengan script 06: selisih LogL maksimum "
             f"{(df_opt['LogL_07'] - df_opt['LogL_06']).abs().max():.2e}.")
    L.append(f"- Model dengan std error tidak valid: {int((~df_opt['SE_Valid']).sum())}; "
             f"tidak konvergen: {int((df_opt['Konvergen'] == False).sum())}.")
    lokal = df_opt[df_opt["Optimum_lokal_lbfgs"] == "Ya"]
    L.append(f"- Model yang dengan lbfgs default saja masih berhenti di optimum lokal "
             f"(diperbaiki oleh multi-optimizer, perbaikan LogL > {AMBANG_PERBAIKAN_LLF}): "
             f"{len(lokal)}. Log lengkap: `data/hasil_07/07_cek_optimum_lokal.csv`.\n")
    if not lokal.empty:
        L.append(tabel_markdown(lokal, ["Nama_Model", "Kelompok", "LogL_lbfgs", "LogL_07",
                                        "Optimizer_Terpilih", "Perbaikan_vs_lbfgs_default"],
                                "{:,.4f}"))
        L.append("")

    L.append("## 3. Diagnostik residual (training)\n")
    L.append(f"Residual burn-in (`loglikelihood_burn`) dibuang. Ljung-Box lag "
             f"{LJUNG_BOX_LAGS}, df = lag − (p+q+P+Q); lag dengan df ≤ 0 atau lag ≥ jumlah "
             f"residual dilewati. Keputusan α = {ALPHA}. Q-Q plot: "
             "`data/hasil_07/grafik/07_qq_*.png`.\n")
    kolom = ["Label", "Jumlah_Residual", "model_df"]
    for lag in LJUNG_BOX_LAGS:
        kolom += [f"LB_Q_lag{lag}", f"LB_p_lag{lag}"]
    kolom += ["LB_lag_dilewati", "Ljung_Box", "Shapiro_W", "Shapiro_p", "Shapiro_Wilk"]
    L.append(tabel_markdown(df_diag, kolom, "{:,.4f}"))
    L.append("")

    L.append("## 4. Rolling origin (9 putaran, latih ulang penuh)\n")
    rata2 = float(df_roll.drop_duplicates("Periode_Target")["Aktual"].mean())
    L.append(f"Target akurasi: {em.DESKRIPSI_TARGET}.\n")
    L.append(f"Pada periode testing: {teks_target(em.target_akurasi(rata2), rata2)}.\n")
    L.append("> Target RMSE/MAE/MSE dibuat **relatif terhadap rata-rata permintaan** karena data "
             "penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM yang tidak "
             "diketahui pasti). Proporsi target mengikuti dokumen alur: MAE/RMSE = 400/500 = 0,8 "
             "dan MSE = RMSE². MAPE dan R² tidak bergantung skala.\n")
    L.append(tabel_markdown(df_metrik, ["Label", "MAPE_%", "RMSE", "RMSE_%_rata2", "MAE",
                                        "MAE_%_rata2", "MSE", "R2", "APE_maks_%"]
                            + [f"Target_{n}" for n in METRIK_TARGET]
                            + ["Lebih_baik_dari_naive"]))
    L.append("")
    L.append("### Error per putaran (APE %)\n")
    pv = df_roll.pivot(index="Periode_Target", columns="Label", values="APE_%").reset_index()
    L.append(tabel_markdown(pv, list(pv.columns), "{:,.2f}"))
    L.append("")
    L.append("### Prediksi per putaran (kg)\n")
    pp = df_roll.pivot(index="Periode_Target", columns="Label", values="Prediksi")
    pp.insert(0, "Aktual", df_roll.drop_duplicates("Periode_Target").set_index("Periode_Target")["Aktual"])
    pp = pp.reset_index()
    L.append(tabel_markdown(pp, list(pp.columns), "{:,.0f}"))
    L.append("")

    L.append("## 5. Rekomendasi model\n")
    L.append("Aturan pemilihan:\n")
    L.append("1. **Layak statistik**: lulus Ljung-Box dan Shapiro-Wilk, serta MAPE rolling origin "
             "lebih baik dari seasonal naive.")
    L.append("2. **Layak peramalan**: layak statistik **dan tidak membutuhkan nilai eksogen masa "
             "depan**. Saat meramal Jan–Jun 2026, harga rata-rata per kg bulan-bulan tersebut belum "
             "diketahui, sehingga ARIMAX tidak dapat dipakai tanpa meramal harga terlebih dahulu "
             "(yang menambah ketidakpastian). Pada evaluasi ini ARIMAX memakai harga **aktual** "
             "periode testing, sehingga akurasinya merupakan batas atas yang optimistis.")
    L.append("3. **Model final** = layak peramalan dengan MAPE rolling origin terendah. AIC hanya "
             "dibandingkan di dalam kelompok (d, D).\n")
    L.append(tabel_markdown(urutan, ["Peringkat", "Label", "Nama_Model", "Ljung_Box",
                                     "Shapiro_Wilk", "MAPE_%", "RMSE", "R2",
                                     "Butuh_Eksogen_Masa_Depan", "Layak_Statistik",
                                     "Layak_Peramalan"]))
    L.append("")
    L.append(f"**{status}: {pilih['Label']} — {pilih['Nama_Model']}** ({alasan}).\n")
    if terbaik_evaluasi is not None and terbaik_evaluasi["Label"] != pilih["Label"]:
        L.append(f"Catatan: MAPE rolling origin terendah dimiliki **{terbaik_evaluasi['Label']}** "
                 f"({terbaik_evaluasi['MAPE_%']:.2f}% vs {pilih['MAPE_%']:.2f}%). Model ini valid "
                 "secara statistik dan dilaporkan sebagai pembanding, tetapi tidak dipilih sebagai "
                 "model final karena membutuhkan harga masa depan. Model final dipakai di script "
                 "09 (peramalan Jan–Jun 2026) dan script 11–12 (implementasi MS Access).\n")

    L.append("## Catatan\n")
    L.append("- ARIMAX memakai nilai eksogen aktual bulan yang diramal (Harga_Rata2_Per_Kg dan "
             "Koefisien_Musim) dari dataset. Dalam praktik, harga bulan depan belum diketahui "
             "dan harus diasumsikan, sehingga akurasi ARIMAX di sini cenderung optimistis.")
    L.append("- Koefisien_Musim adalah pengali yang dipakai untuk membangkitkan data sintetis, "
             "sehingga model dengan label ini diberi informasi persis tentang pola musiman data.")
    L.append("- Peramalan multi-step pada data testing (Apr–Des 2025) dikerjakan di script 08.")

    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nRingkasan Markdown disimpan ke: {RINGKASAN_MD}")


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    penjelasan.mulai("07_validasi_diagnostik_evaluasi")
    print("\n" + "=" * 75)
    print("PROGRAM ESTIMASI PARAMETER, VALIDASI DIAGNOSTIK & EVALUASI KINERJA")
    print("=" * 75)

    train, test, kandidat = muat_data()
    df_param, df_opt, hasil_fit = estimasi_parameter(train, kandidat)
    shortlist = pilih_shortlist(kandidat)
    df_diag = diagnostik_residual(shortlist, hasil_fit)
    df_roll = rolling_origin(train, test, shortlist)
    df_metrik = hitung_metrik_rolling(df_roll)
    grafik_rolling(train, df_roll)
    urutan, pilih, status, alasan, terbaik_evaluasi = rekomendasi_model(df_diag, df_metrik)
    # Contoh perhitungan rumus [9]: Ljung-Box, Shapiro-Wilk, Q-Q, rolling origin, metrik
    penjelasan.jelaskan_07(train, test, shortlist, hasil_fit, df_diag, df_roll, df_metrik)
    tulis_ringkasan(df_param, df_opt, shortlist, df_diag, df_roll, df_metrik,
                    urutan, pilih, status, alasan, terbaik_evaluasi)

    print("\n" + "=" * 75)
    print("TAHAP 07 SELESAI. Lanjut ke 08_forecasting_data_testing.py untuk peramalan data testing.")
    print("=" * 75)


if __name__ == "__main__":
    main()
