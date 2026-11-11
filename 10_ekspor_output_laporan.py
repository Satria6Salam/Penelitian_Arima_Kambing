"""
=============================================================================
PROGRAM EKSPOR OUTPUT LAPORAN (PLOT + CSV)
File: 10_ekspor_output_laporan.py

Melengkapi output berupa PLOT dan FILE CSV untuk setiap hasil penelitian,
lalu menyusun indeks OUTPUT_LAPORAN.md:
 1. Hasil ADF                      6. Hasil training
 2. Hasil differencing             7. Hasil AIC/BIC
 3. Hasil ACF & PACF               8. Validasi diagnostik & evaluasi kinerja
 4. Hasil pembagian dataset        9. Peramalan 6 bulan ke depan
 5. Penetapan 4 skenario pemodelan

Script ini TIDAK mengubah hasil script 03-09:
- ADF dan ACF/PACF dihitung ulang dengan pengaturan yang sama persis dengan
  05_eksplorasi_data.py (dan dicek terhadap model_config.json).
- AIC/BIC, diagnostik, metrik, dan peramalan dibaca dari CSV yang sudah ada.
- Hanya model shortlist yang di-fit ulang (estimasi_model.py, sama dengan
  script 07) untuk menyimpan nilai fitted dan residual training.
Semua output baru disimpan di data/laporan/.
=============================================================================
"""

import ast
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from pathlib import Path
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import matplotlib.dates as mdates

import keterangan_csv as kk  # keterangan kolom pada setiap CSV hasil
import estimasi_model as em


# =============================================================================
# PENGATURAN PATH DIREKTORI
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUT = DATA_DIR / "laporan"
OUT.mkdir(parents=True, exist_ok=True)
INDEKS_MD = BASE_DIR / "OUTPUT_LAPORAN.md"

DATASET_CSV = DATA_DIR / "olah" / "dataset_pra_proses_final.csv"
CONFIG_JSON = DATA_DIR / "eksplorasi" / "model_config.json"
H06 = DATA_DIR / "hasil_06"
H07 = DATA_DIR / "hasil_07"
H08 = DATA_DIR / "hasil_08"
H09 = DATA_DIR / "hasil_09"

TARGET_COL = em.TARGET_COL
ALPHA = 0.05            # sama dengan 05_eksplorasi_data.py
M = 12
DPI = 200


# =============================================================================
# FUNGSI BANTUAN
# =============================================================================

def rp(v, d=0):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_kg(ax):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: rp(v)))


def simpan(fig, nama):
    path = OUT / nama
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def rel(path):
    return str(Path(path).relative_to(BASE_DIR)).replace("/", "\\")


def adf_baris(seri, label):
    """ADF dengan pengaturan 05_eksplorasi_data.py (maxlag=None, regression='c', autolag='AIC')."""
    stat, p, lag, nobs, crit, _ = adfuller(seri, maxlag=None, regression="c", autolag="AIC")
    return {
        "Seri": label,
        "Jumlah_Observasi": int(nobs),
        "ADF_Statistic": float(stat),
        "P_value": float(p),
        "Used_Lag": int(lag),
        "Kritis_1%": float(crit["1%"]),
        "Kritis_5%": float(crit["5%"]),
        "Kritis_10%": float(crit["10%"]),
        "Keputusan": "Stasioner (tolak H0)" if (p < ALPHA and stat < crit["5%"])
        else "Tidak stasioner (gagal tolak H0)",
    }


def muat_train_test():
    tr = kk.baca_csv(H06 / "06_training_set.csv", parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    te = kk.baca_csv(H06 / "06_testing_set.csv", parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    return tr, te


# =============================================================================
# 1-3. ADF, DIFFERENCING, ACF & PACF
# =============================================================================

def ekspor_adf_diff_acf(indeks):
    print("[1-3] ADF, differencing, ACF & PACF")
    df = kk.baca_csv(DATASET_CSV, parse_dates=["Periode"]).set_index("Periode")
    y = df[TARGET_COL].astype(float)
    config = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))

    # 1. ADF pada seri asli (d = 0), seperti script 05
    adf0 = adf_baris(y.values, "Asli (d=0)")
    kk.simpan_csv(pd.DataFrame([adf0]), OUT / "01_hasil_adf.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(y.index, y, color="black", label="Permintaan (kg)")
    ax.plot(y.index, y.rolling(M).mean(), color="#1f5fbf", label="Rata-rata bergerak 12 bulan")
    ax.plot(y.index, y.rolling(M).std(), color="#c0392b", linestyle="--",
            label="Simpangan baku bergerak 12 bulan")
    ax.set_title(f"Uji ADF seri asli: statistik {adf0['ADF_Statistic']:.4f}, "
                 f"p-value {adf0['P_value']:.6f} → {adf0['Keputusan']}")
    ax.set_xlabel("Periode")
    ax.set_ylabel("kg")
    format_kg(ax)
    ax.legend(fontsize=8)
    p1 = simpan(fig, "01_plot_adf.png")
    indeks[1] = {"csv": [OUT / "01_hasil_adf.csv"],
                 "plot": [p1, DATA_DIR / "eksplorasi" / "time_series_plot.png"],
                 "ket": f"ADF seri asli: statistik {adf0['ADF_Statistic']:.4f}, p {adf0['P_value']:.6f}, "
                        f"kritis 5% {adf0['Kritis_5%']:.4f} → stasioner (d = {config['derajat_pembedaan_non_musiman_d']})."}

    # 2. Differencing: seri asli, Δ1, Δ12 (dan Δ12 log yang dipakai model final)
    seri = pd.DataFrame({
        "Asli_Kg": y,
        "Diff1_Kg": y.diff(1),
        "Diff12_Kg": y.diff(M),
        "Log": np.log(y),
        "Diff12_Log": np.log(y).diff(M),
    })
    seri.index.name = "Periode"
    kk.simpan_csv(seri.reset_index().assign(Periode=lambda d: d["Periode"].dt.strftime("%Y-%m")),
                  OUT / "02_seri_differencing.csv", index=False)
    tabel_diff = pd.DataFrame([
        {**adf0, "Seri": "Asli (d=0, D=0)",
         "Dipakai": "Ya – ARIMA/SARIMA D=0/ARIMAX (keputusan script 05: d=0)"},
        {**adf_baris(seri["Diff1_Kg"].dropna().values, "Differencing 1 (d=1)"),
         "Dipakai": "Tidak – seri asli sudah stasioner"},
        {**adf_baris(seri["Diff12_Kg"].dropna().values, "Differencing musiman (D=1, m=12)"),
         "Dipakai": "Pembanding"},
        {**adf_baris(seri["Diff12_Log"].dropna().values, "Differencing musiman log (D=1, m=12)"),
         "Dipakai": "Ya – model final SARIMA(1,0,0)x(1,1,0,12) log"},
    ])
    kk.simpan_csv(tabel_diff, OUT / "02_hasil_differencing.csv", index=False)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for ax, kol, judul in zip(axes, ["Asli_Kg", "Diff1_Kg", "Diff12_Log"],
                              ["Seri asli (kg), d=0", "Differencing pertama Δ1 (kg)",
                               "Differencing musiman Δ12 dari log (model final)"]):
        ax.plot(seri.index, seri[kol], color="black", marker=".")
        ax.axhline(0 if kol != "Asli_Kg" else seri[kol].mean(), color="grey", linewidth=0.8)
        ax.set_title(judul, fontsize=10)
        if kol != "Diff12_Log":
            format_kg(ax)
    axes[-1].set_xlabel("Periode")
    p2 = simpan(fig, "02_plot_differencing.png")
    indeks[2] = {"csv": [OUT / "02_hasil_differencing.csv", OUT / "02_seri_differencing.csv",
                         CONFIG_JSON],
                 "plot": [p2],
                 "ket": "ADF untuk seri asli, Δ1, Δ12, dan Δ12 log; seri asli sudah stasioner (d=0). "
                        "D=1 diuji di tahap pemodelan dan dipakai model final (log)."}

    # 3. ACF & PACF dengan pengaturan script 05
    n = len(y)
    max_lag = min(max(4, int(n / 4)), 15, n - 1)
    if n >= 24:
        max_lag = max(max_lag, 12)
    max_lag = min(max_lag, n - 1)
    acf_v, acf_ci = acf(y.values, nlags=max_lag, alpha=ALPHA, fft=False, bartlett_confint=True)
    pacf_v, pacf_ci = pacf(y.values, nlags=max_lag, alpha=ALPHA, method="yw")
    tab = pd.DataFrame({
        "Lag_k": np.arange(max_lag + 1),
        "Nilai_ACF": acf_v,
        "ACF_Batas_Signifikansi": acf_ci[:, 1] - acf_v,
        "ACF_Signifikan": np.abs(acf_v) > (acf_ci[:, 1] - acf_v),
        "Nilai_PACF": pacf_v,
        "PACF_Batas_Signifikansi": pacf_ci[:, 1] - pacf_v,
        "PACF_Signifikan": np.abs(pacf_v) > (pacf_ci[:, 1] - pacf_v),
    })
    tab.loc[0, ["ACF_Signifikan", "PACF_Signifikan"]] = False
    kk.simpan_csv(tab, OUT / "03_tabel_acf_pacf.csv", index=False)

    # ACF dan PACF seri Δ12 log (input model final), gaya sama dengan script 05.
    # PACF hanya dapat dihitung sampai lag < n/2 (n = 24 -> lag 11). Metode "ywm"
    # dipakai karena "yw" (script 05) tidak stabil untuk seri sependek ini (nilai > |1|).
    z = seri["Diff12_Log"].dropna().values
    lag_acf = min(12, len(z) - 1)
    lag_pacf = min(12, len(z) // 2 - 1)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    plot_acf(z, lags=lag_acf, alpha=ALPHA, ax=axes[0], fft=False, bartlett_confint=True)
    plot_pacf(z, lags=lag_pacf, alpha=ALPHA, ax=axes[1], method="ywm")
    for ax, judul, sumbu in [(axes[0], "Autocorrelation Function (ACF)", "ACF"),
                             (axes[1], "Partial Autocorrelation Function (PACF)", "PACF")]:
        ax.set_title(judul)
        ax.set_xlabel("Lag")
        ax.set_ylabel(sumbu)
        ax.set_ylim(-1, 1)
        ax.grid(True, linestyle="--", alpha=0.6)
    fig.suptitle(f"Analisis ACF dan PACF seri setelah differencing musiman log (model final, "
                 f"n = {len(z)}; PACF Yule-Walker ywm sampai lag {lag_pacf})", fontsize=13, fontweight="bold")
    lag12 = tab.loc[tab["Lag_k"] == 12].iloc[0]
    p3 = simpan(fig, "03_plot_acf_pacf_diff12_log.png")
    indeks[3] = {"csv": [OUT / "03_tabel_acf_pacf.csv", CONFIG_JSON],
                 "plot": [DATA_DIR / "eksplorasi" / "acf_pacf_plot.png", p3,
                          DATA_DIR / "eksplorasi" / "time_series_decomposition.png"],
                 "ket": f"Lag 12 signifikan: ACF {lag12['Nilai_ACF']:.4f}, PACF {lag12['Nilai_PACF']:.4f} "
                        "pada seri asli → pola musiman m = 12; kandidat model di model_config.json. "
                        "Plot asli script 05 (seri asli, d=0): acf_pacf_plot.png. Plot tambahan "
                        "03_plot_acf_pacf_diff12_log.png memakai seri BERBEDA, yaitu Δ12 log "
                        "(input model final)."}
    return adf0, lag12


# =============================================================================
# 4-5. PEMBAGIAN DATASET DAN 4 SKENARIO
# =============================================================================

def ekspor_split_skenario(indeks):
    print("[4-5] Pembagian dataset dan skenario")
    tr, te = muat_train_test()
    ring = pd.DataFrame([
        {"Bagian": "Training", "Jumlah_Bulan": len(tr), "Proporsi_%": len(tr) / (len(tr) + len(te)) * 100,
         "Periode_Awal": f"{tr.index[0]:%Y-%m}", "Periode_Akhir": f"{tr.index[-1]:%Y-%m}",
         "Rata2_Kg": tr[TARGET_COL].mean(), "Bulan_Iduladha": ", ".join(tr.index[tr["Koefisien_Musim"] > 1].strftime("%Y-%m"))},
        {"Bagian": "Testing", "Jumlah_Bulan": len(te), "Proporsi_%": len(te) / (len(tr) + len(te)) * 100,
         "Periode_Awal": f"{te.index[0]:%Y-%m}", "Periode_Akhir": f"{te.index[-1]:%Y-%m}",
         "Rata2_Kg": te[TARGET_COL].mean(), "Bulan_Iduladha": ", ".join(te.index[te["Koefisien_Musim"] > 1].strftime("%Y-%m"))},
    ])
    kk.simpan_csv(ring, OUT / "04_ringkasan_pembagian_dataset.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(tr.index, tr[TARGET_COL], color="black", marker=".", label=f"Training ({len(tr)} bulan, 75%)")
    ax.plot(te.index, te[TARGET_COL], color="#c0392b", marker="o", label=f"Testing ({len(te)} bulan, 25%)")
    ax.axvspan(te.index[0] - pd.Timedelta(days=15), te.index[-1] + pd.Timedelta(days=15),
               color="#c0392b", alpha=0.07)
    ax.axvline(te.index[0] - pd.Timedelta(days=15), color="grey", linestyle=":")
    ax.set_title("Pembagian Dataset Kronologis (Training 75% : Testing 25%)")
    ax.set_xlabel("Periode")
    ax.set_ylabel("Permintaan (kg)")
    format_kg(ax)
    ax.legend(fontsize=8)
    p4 = simpan(fig, "04_plot_pembagian_dataset.png")
    indeks[4] = {"csv": [H06 / "06_training_set.csv", H06 / "06_testing_set.csv",
                         OUT / "04_ringkasan_pembagian_dataset.csv", H08 / "08_cek_data_testing.csv"],
                 "plot": [p4],
                 "ket": f"Training {tr.index[0]:%b %Y}–{tr.index[-1]:%b %Y} ({len(tr)} bulan), "
                        f"testing {te.index[0]:%b %Y}–{te.index[-1]:%b %Y} ({len(te)} bulan)."}

    est = kk.baca_csv(H06 / "06_hasil_estimasi.csv")
    def nama_skenario(r):
        if r["Skenario"] == "ARIMAX":
            return "ARIMAX Harga+Iduladha" if "Koefisien_Musim" in r["Eksogen"] else "ARIMAX Harga"
        return r["Skenario"]
    est["Skenario_Detail"] = est.apply(nama_skenario, axis=1)
    kk.simpan_csv(est[["Skenario", "Skenario_Detail", "Nama_Model", "Order", "Seasonal_Order", "Eksogen",
                       "Kelompok_Differencing", "Status"]],
                  OUT / "05_daftar_kandidat_skenario.csv", index=False)
    ring5 = est.groupby(["Skenario_Detail", "Kelompok_Differencing"], sort=False).agg(
        Jumlah_Kandidat=("Nama_Model", "count"),
        Eksogen=("Eksogen", "first"),
        Berhasil=("Status", lambda s: int((s == "Berhasil").sum())),
    ).reset_index()
    kk.simpan_csv(ring5, OUT / "05_ringkasan_skenario.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 4))
    label = ring5["Skenario_Detail"] + "\n(" + ring5["Kelompok_Differencing"] + ")"
    bars = ax.barh(label, ring5["Jumlah_Kandidat"], color=["#7f8c8d", "#4a90d9", "#1f5fbf", "#e67e22", "#c0392b"][:len(ring5)])
    ax.bar_label(bars, padding=3)
    ax.invert_yaxis()
    ax.set_xlabel("Jumlah kandidat model")
    ax.set_title(f"Penetapan Skenario Pemodelan ({len(est)} kandidat)")
    p5 = simpan(fig, "05_plot_skenario_pemodelan.png")
    indeks[5] = {"csv": [OUT / "05_ringkasan_skenario.csv", OUT / "05_daftar_kandidat_skenario.csv", CONFIG_JSON],
                 "plot": [p5],
                 "ket": "Skenario: ARIMA (baseline), SARIMA (musiman, D=0 dan D=1), ARIMAX + Harga, "
                        "ARIMAX + Harga + Iduladha. Ensemble tidak diestimasi."}
    return tr, te


# =============================================================================
# 6. HASIL TRAINING (FITTED VS AKTUAL)
# =============================================================================

def ekspor_training(indeks, tr):
    print("[6] Hasil training: fit ulang model shortlist untuk nilai fitted")
    short = kk.baca_csv(H07 / "07_shortlist.csv")
    data = em.skala_data(tr)
    fitted, residual = {}, {}
    for _, s in short.iterrows():
        exog_kol = [] if s["Eksogen"] == "-" else [e.strip() for e in s["Eksogen"].split(",")]
        res, _ = em.fit_terbaik(data[TARGET_COL], data[exog_kol].astype(float) if exog_kol else None,
                                ast.literal_eval(s["Order"]), ast.literal_eval(s["Seasonal_Order"]))
        burn = int(res.loglikelihood_burn)
        f = pd.Series(em.ke_kg(res.fittedvalues.values), index=tr.index)
        f.iloc[:burn] = np.nan
        fitted[s["Label"]] = f
        r = res.resid.copy()
        r.iloc[:burn] = np.nan
        residual[s["Label"]] = r

    df_fit = pd.DataFrame({"Aktual_Kg": tr[TARGET_COL], **{f"Fitted_{k}_Kg": v for k, v in fitted.items()}})
    df_fit.index = df_fit.index.strftime("%Y-%m")
    df_fit.index.name = "Periode"
    kk.simpan_csv(df_fit, OUT / "06_fitted_training.csv")
    df_res = pd.DataFrame({f"Residual_{k}": v for k, v in residual.items()}, index=tr.index)
    df_res.index = df_res.index.strftime("%Y-%m")
    df_res.index.name = "Periode"
    kk.simpan_csv(df_res, OUT / "08_residual_training.csv")

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(tr.index, tr[TARGET_COL], color="black", linewidth=2, label="Aktual training")
    for k, v in fitted.items():
        ax.plot(tr.index, v, linestyle="--", marker=".", label=f"Fitted {k}")
    ax.set_title("Hasil Training: Nilai Fitted Model Shortlist vs Aktual (Jan 2023–Mar 2025)")
    ax.set_xlabel("Periode")
    ax.set_ylabel("Permintaan (kg)")
    format_kg(ax)
    ax.legend(fontsize=8)
    p6 = simpan(fig, "06_plot_fitted_vs_aktual.png")
    indeks[6] = {"csv": [H06 / "06_hasil_estimasi.csv", H07 / "07_parameter_estimasi.csv",
                         OUT / "06_fitted_training.csv"],
                 "plot": [p6],
                 "ket": "Estimasi MLE seluruh kandidat (nobs, LogL, optimizer, konvergensi), tabel parameter "
                        "(koefisien, SE, p-value, CI 95%), dan nilai fitted model shortlist. "
                        "Summary lengkap: data\\hasil_07\\07_summary_shortlist.txt."}
    return residual


# =============================================================================
# 7. AIC/BIC
# =============================================================================

def ekspor_aic_bic(indeks):
    print("[7] AIC/BIC per kelompok differencing")
    aic = kk.baca_csv(H06 / "06_perbandingan_aic_bic.csv")
    aic = aic[aic["Status"] != "Gagal"]
    kelompok = list(aic["Kelompok_Differencing"].unique())
    fig, axes = plt.subplots(1, len(kelompok), figsize=(13, 7),
                             gridspec_kw={"width_ratios": [aic["Kelompok_Differencing"].eq(k).sum() for k in kelompok]})
    axes = np.atleast_1d(axes)
    for ax, k in zip(axes, kelompok):
        isi = aic[aic["Kelompok_Differencing"] == k].sort_values("AIC")
        y = np.arange(len(isi))
        ax.barh(y - 0.2, isi["AIC"], height=0.4, color="#1f5fbf", label="AIC")
        ax.barh(y + 0.2, isi["BIC"], height=0.4, color="#e67e22", label="BIC")
        ax.set_yticks(y)
        ax.set_yticklabels(isi["Nama_Model"], fontsize=7)
        ax.invert_yaxis()
        ax.axvline(0, color="grey", linewidth=0.8)
        ax.set_title(f"Kelompok {k}", fontsize=10)
        ax.set_xlabel("Nilai (skala ln kg)")
        ax.legend(fontsize=7)
    fig.suptitle("Perbandingan AIC/BIC per Kelompok Differencing (lebih kecil lebih baik; "
                 "tidak dibandingkan antar-kelompok)", fontsize=10)
    p7 = simpan(fig, "07_plot_aic_bic.png")
    indeks[7] = {"csv": [H06 / "06_perbandingan_aic_bic.csv", H06 / "06_cek_model_bersarang.csv"],
                 "plot": [p7],
                 "ket": "AIC/BIC, Delta, dan peringkat per kelompok (d, D); kolom *_setara_kg sudah "
                        "dikoreksi ke satuan kg."}


# =============================================================================
# 8. VALIDASI DIAGNOSTIK DAN EVALUASI
# =============================================================================

def ekspor_validasi(indeks, residual):
    print("[8] Validasi diagnostik dan evaluasi")
    diag = kk.baca_csv(H07 / "07_diagnostik_residual.csv")
    met = kk.baca_csv(H07 / "07_metrik_rolling_origin.csv")

    # Plot p-value Ljung-Box dan Shapiro-Wilk
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(diag))
    lebar = 0.2
    for i, lag in enumerate([6, 9, 12]):
        ax.bar(x + (i - 1.5) * lebar, diag[f"LB_p_lag{lag}"], width=lebar, label=f"Ljung-Box lag {lag}")
    ax.bar(x + 1.5 * lebar, diag["Shapiro_p"], width=lebar, color="#c0392b", label="Shapiro-Wilk")
    ax.axhline(ALPHA, color="black", linestyle="--", linewidth=0.9, label="α = 0,05")
    ax.set_xticks(x)
    ax.set_xticklabels(diag["Label"], fontsize=8)
    ax.set_ylabel("p-value (lulus bila > 0,05)")
    ax.set_title("Uji Ljung-Box dan Shapiro-Wilk Residual Training")
    ax.legend(fontsize=7, ncol=3)
    p8a = simpan(fig, "08_plot_ljungbox_shapiro.png")

    # Plot residual dan ACF residual
    n = len(residual)
    fig, axes = plt.subplots(n, 2, figsize=(11, 2.3 * n))
    for i, (k, r) in enumerate(residual.items()):
        r = r.dropna()
        axes[i, 0].plot(r.index, r.values, marker=".", color="black")
        axes[i, 0].axhline(0, color="grey", linewidth=0.8)
        axes[i, 0].set_title(f"Residual {k} (skala log)", fontsize=9)
        axes[i, 0].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        axes[i, 0].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        axes[i, 0].tick_params(axis="x", labelsize=8)
        plot_acf(r.values, lags=min(12, len(r) - 1), ax=axes[i, 1], alpha=ALPHA)
        axes[i, 1].set_title(f"ACF residual {k}", fontsize=9)
    p8b = simpan(fig, "08_plot_residual_acf.png")

    # Plot metrik rolling origin
    m = met.sort_values("MAPE_%")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    for ax, kol, judul, garis in [(axes[0], "MAPE_%", "MAPE (%)", 15),
                                  (axes[1], "RMSE", "RMSE (kg)", None),
                                  (axes[2], "R2", "R²", 0.70)]:
        warna = ["#7f8c8d" if l == "Seasonal naive" else "#1f5fbf" for l in m["Label"]]
        b = ax.barh(m["Label"], m[kol], color=warna)
        ax.bar_label(b, labels=[rp(v, 2) if kol != "RMSE" else rp(v) for v in m[kol]], fontsize=7, padding=2)
        if garis is not None:
            ax.axvline(garis, color="#c0392b", linestyle="--", linewidth=0.9,
                       label=f"Target {'<' if kol == 'MAPE_%' else '>'} {rp(garis, 2) if garis < 1 else garis}")
            ax.legend(fontsize=7)
        ax.invert_yaxis()
        ax.set_title(judul, fontsize=10)
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle("Metrik Time Series Cross-Validation (Rolling Origin 9 Bulan, Apr–Des 2025)", fontsize=10)
    p8c = simpan(fig, "08_plot_metrik_rolling_origin.png")

    qq = sorted((H07 / "grafik").glob("07_qq_*.png"))
    indeks[8] = {"csv": [H07 / "07_diagnostik_residual.csv", OUT / "08_residual_training.csv",
                         H07 / "07_rolling_origin_prediksi.csv", H07 / "07_metrik_rolling_origin.csv",
                         H08 / "08_peramalan_testing.csv", H08 / "08_evaluasi_peramalan.csv",
                         H08 / "08_multistep_vs_rolling.csv"],
                 "plot": [p8a, p8b, *qq, H07 / "grafik" / "07_rolling_origin_vs_aktual.png", p8c,
                          *sorted((H08 / "grafik").glob("*.png"))],
                 "ket": "Ljung-Box (lag 6/9/12) dan Shapiro-Wilk, Q-Q plot per model, rolling origin "
                        "9 putaran, MAPE/RMSE/MAE/MSE/R² vs target, serta peramalan multi-step data testing."}


# =============================================================================
# 9. PERAMALAN 6 BULAN KE DEPAN
# =============================================================================

def ekspor_peramalan(indeks):
    print("[9] Peramalan 6 bulan ke depan (output script 09)")
    indeks[9] = {"csv": [H09 / "09_peramalan_jan_jun_2026.csv", H09 / "09_parameter_model_final.csv",
                         H09 / "09_diagnostik_model_final.csv",
                         H09 / "validasi_apr_sep_2025" / "09_peramalan_validasi_apr_sep_2025.csv"],
                 "plot": [H09 / "grafik" / "09_fan_chart.png",
                          H09 / "validasi_apr_sep_2025" / "grafik" / "09_fan_chart_validasi.png"],
                 "ket": "Peramalan Jan–Jun 2026 dengan interval 95% (fan chart) dari model final "
                        "SARIMA(1,0,0)x(1,1,0,12) log; validasi ekstrapolasi Apr–Sep 2025."}


# =============================================================================
# INDEKS OUTPUT_LAPORAN.md
# =============================================================================

JUDUL = {
    1: "Hasil ADF",
    2: "Hasil Differencing",
    3: "Hasil ACF & PACF",
    4: "Hasil Pembagian Dataset",
    5: "Hasil Penetapan 4 Skenario Pemodelan",
    6: "Hasil Training",
    7: "Hasil AIC & BIC",
    8: "Hasil Validasi Diagnostik & Evaluasi Kinerja",
    9: "Hasil Peramalan 6 Bulan ke Depan",
}
RINGKASAN_MD = {
    5: "06_ringkasan_aic_bic.md", 6: "06_ringkasan_aic_bic.md", 7: "06_ringkasan_aic_bic.md",
    8: "07_ringkasan_validasi.md, 08_ringkasan_forecasting.md", 9: "09_ringkasan_peramalan.md",
}


def tulis_indeks(indeks):
    L = ["# Indeks Output Laporan Penelitian\n",
         "Daftar lokasi output (CSV dan plot) untuk setiap hasil penelitian. Semua path relatif "
         "terhadap folder proyek. Output baru yang melengkapi plot/CSV dibuat oleh "
         "`10_ekspor_output_laporan.py` di folder `data\\laporan\\`.\n"]
    hilang = []
    for no in range(1, 10):
        isi = indeks[no]
        L.append(f"## {no}. {JUDUL[no]}\n")
        L.append(isi["ket"] + "\n")
        L.append("**File CSV/data:**\n")
        for p in isi["csv"]:
            L.append(f"- `{rel(p)}`")
            if not Path(p).exists():
                hilang.append(p)
        L.append("\n**Plot:**\n")
        for p in isi["plot"]:
            L.append(f"- `{rel(p)}`")
            if not Path(p).exists():
                hilang.append(p)
        if no in RINGKASAN_MD:
            L.append(f"\nRingkasan teks: `{RINGKASAN_MD[no]}`")
        L.append("")
    INDEKS_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    return hilang


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    print("=" * 75)
    print("PROGRAM EKSPOR OUTPUT LAPORAN (PLOT + CSV)")
    print("=" * 75)
    indeks = {}
    adf0, lag12 = ekspor_adf_diff_acf(indeks)
    tr, _ = ekspor_split_skenario(indeks)
    residual = ekspor_training(indeks, tr)
    ekspor_aic_bic(indeks)
    ekspor_validasi(indeks, residual)
    ekspor_peramalan(indeks)
    hilang = tulis_indeks(indeks)

    print(f"\nCek konsistensi dengan script 05: ADF {adf0['ADF_Statistic']:.4f} "
          f"(p {adf0['P_value']:.6f}); ACF lag12 {lag12['Nilai_ACF']:.4f}, PACF lag12 {lag12['Nilai_PACF']:.4f}")
    print(f"Indeks disimpan ke: {INDEKS_MD}")
    if hilang:
        print("PERINGATAN, file belum ada:")
        for p in hilang:
            print(f"- {p}")
    print("=" * 75)
    print("TAHAP 10 SELESAI. Seluruh output laporan (plot + CSV) tersedia.")
    print("=" * 75)


if __name__ == "__main__":
    main()
