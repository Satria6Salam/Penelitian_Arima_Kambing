"""
=============================================================================
PROGRAM PERAMALAN DAN VISUALISASI PADA DATA TESTING
File: 08_forecasting_data_testing.py

Mengikuti tahap "PERAMALAN & VISUALISASI" pada alur penelitian, dengan
periode peramalan = data testing 25% (06_testing_set.csv, Apr-Des 2025):
1. Model valid dari script 07 (lulus Ljung-Box dan Shapiro-Wilk) dilatih
   pada seluruh training set (27 bulan), lalu mengekstrapolasi 9 bulan
   testing sekaligus (blind forecast, tanpa melihat data testing).
2. Menghitung batas bawah dan atas interval kepercayaan 95%.
3. Fan chart: data aktual historis, garis peramalan, dan pita CI 95%,
   serta data aktual testing sebagai pembanding.
4. Analisis: akurasi (MAPE, RMSE, MAE, MSE, R²), cakupan CI 95%, lebar CI,
   dan error per bulan; seasonal naive sebagai pembanding.
5. Perbandingan multi-step (script ini) vs one-step rolling origin (script 07)
   untuk melihat penurunan akurasi saat horizon makin jauh.

Estimasi memakai modul estimasi_model.py (sama dengan script 06 dan 07).
Ramalan log dikembalikan ke kg dengan exp(). exp(mean log) adalah MEDIAN
ramalan pada skala kg; kolom tambahan Prediksi_Mean_Lognormal_Kg memakai
koreksi bias lognormal exp(mu + var/2). Karena exp monoton, batas interval
95% pada skala log tetap menjadi batas interval 95% pada skala kg.


Input  : data/hasil_06 (training/testing), data/hasil_07 (model valid)
Output : data/hasil_08/ dan 08_ringkasan_forecasting.md
=============================================================================
"""

import ast
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels

from pathlib import Path
from scipy import stats

import estimasi_model as em
import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/


# =============================================================================
# PENGATURAN PATH DIREKTORI
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRAIN_CSV = DATA_DIR / "hasil_06" / "06_training_set.csv"
TEST_CSV = DATA_DIR / "hasil_06" / "06_testing_set.csv"
SHORTLIST_CSV = DATA_DIR / "hasil_07" / "07_shortlist.csv"
DIAGNOSTIK_CSV = DATA_DIR / "hasil_07" / "07_diagnostik_residual.csv"
METRIK_07_CSV = DATA_DIR / "hasil_07" / "07_metrik_rolling_origin.csv"
ROLLING_07_CSV = DATA_DIR / "hasil_07" / "07_rolling_origin_prediksi.csv"

OUTPUT_DIR = DATA_DIR / "hasil_08"
GRAFIK_DIR = OUTPUT_DIR / "grafik"

PERAMALAN_CSV = OUTPUT_DIR / "08_peramalan_testing.csv"
EVALUASI_CSV = OUTPUT_DIR / "08_evaluasi_peramalan.csv"
MODEL_CSV = OUTPUT_DIR / "08_model_peramalan.csv"
CEK_DATA_CSV = OUTPUT_DIR / "08_cek_data_testing.csv"
BANDING_07_CSV = OUTPUT_DIR / "08_multistep_vs_rolling.csv"
RINGKASAN_MD = BASE_DIR / "08_ringkasan_forecasting.md"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
GRAFIK_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# KONSTANTA PENELITIAN
# =============================================================================

TARGET_COL = em.TARGET_COL
M = 12
ALPHA_CI = 0.05            # interval kepercayaan 95%
LABEL_NAIVE = "Seasonal naive"

# Target akurasi: RMSE/MAE/MSE relatif terhadap rata-rata aktual (estimasi_model.py)
METRIK_TARGET = ["MAPE_%", "RMSE", "MAE", "MSE", "R2"]


# =============================================================================
# FUNGSI BANTUAN
# =============================================================================

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
# TAHAP 1: MEMUAT DATA DAN MODEL VALID
# =============================================================================

def cek_data_testing(train, test):
    """Memeriksa kelengkapan dan pembagian data testing."""
    kolom_wajib = [TARGET_COL, em.PRICE_COL, "Koefisien_Musim"]
    total = len(train) + len(test)
    baris = [
        ("Jumlah baris testing", f"{len(test)}", len(test) == 9),
        ("Jumlah baris training", f"{len(train)}", len(train) == 27),
        ("Proporsi testing", f"{len(test) / total * 100:.1f}% dari {total} bulan",
         abs(len(test) / total - 0.25) < 1e-9),
        ("Periode testing", f"{test.index[0]:%Y-%m} s.d. {test.index[-1]:%Y-%m}", True),
        ("Tidak tumpang tindih dengan training",
         f"training berakhir {train.index[-1]:%Y-%m}",
         train.index.intersection(test.index).empty and test.index[0] > train.index[-1]),
        ("Testing berurutan bulanan tanpa celah", test.index.freqstr,
         test.index.freqstr == "MS" and len(pd.date_range(test.index[0], test.index[-1], freq="MS")) == len(test)),
        ("Testing tepat setelah training",
         f"{train.index[-1]:%Y-%m} -> {test.index[0]:%Y-%m}",
         test.index[0] == train.index[-1] + pd.offsets.MonthBegin(1)),
        ("Kolom tersedia", ", ".join(kolom_wajib), all(k in test.columns for k in kolom_wajib)),
        ("Tidak ada nilai kosong", "-",
         not test[[k for k in kolom_wajib if k in test.columns]].isna().any().any()),
        ("Bulan Iduladha di testing",
         ", ".join(test.index[test["Koefisien_Musim"] > 1].strftime("%Y-%m")), True),
    ]
    df = pd.DataFrame(baris, columns=["Pemeriksaan", "Hasil", "Lulus"])
    df["Lulus"] = df["Lulus"].map({True: "Ya", False: "Tidak"})
    df.to_csv(CEK_DATA_CSV, index=False)

    print("\n[PEMERIKSAAN DATA TESTING]")
    print(df.to_string(index=False))
    if (df["Lulus"] == "Tidak").any():
        raise ValueError("Data testing tidak lolos pemeriksaan; lihat tabel di atas.")
    return df


def muat_data_dan_model():
    print("\n" + "=" * 75)
    print("TAHAP 1: MEMUAT DATA DAN MODEL VALID DARI SCRIPT 07")
    print("=" * 75)

    for f in [TRAIN_CSV, TEST_CSV, SHORTLIST_CSV, DIAGNOSTIK_CSV]:
        if not f.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {f}. Jalankan script 06 dan 07 dulu.")

    train = pd.read_csv(TRAIN_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    test = pd.read_csv(TEST_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")

    cek = cek_data_testing(train, test)

    shortlist = pd.read_csv(SHORTLIST_CSV)
    diag = pd.read_csv(DIAGNOSTIK_CSV)
    df = shortlist.merge(diag[["Label", "Ljung_Box", "Shapiro_Wilk"]], on="Label")
    if METRIK_07_CSV.exists():
        met = pd.read_csv(METRIK_07_CSV)[["Label", "MAPE_%"]].rename(
            columns={"MAPE_%": "MAPE_rolling_07_%"})
        df = df.merge(met, on="Label", how="left")

    valid = df[(df["Ljung_Box"] == "Lulus") & (df["Shapiro_Wilk"] == "Lulus")].copy()
    if valid.empty:
        raise ValueError("Tidak ada model yang lulus Ljung-Box dan Shapiro-Wilk di script 07.")

    print(f"Training : {len(train)} obs ({train.index[0]:%b %Y} - {train.index[-1]:%b %Y})")
    print(f"Testing  : {len(test)} obs ({test.index[0]:%b %Y} - {test.index[-1]:%b %Y}) "
          "= periode peramalan")
    print(f"Transformasi estimasi: {em.TRANSFORMASI} ({em.DESKRIPSI_TRANSFORMASI})")
    print("\nModel valid (lulus Ljung-Box dan Shapiro-Wilk):")
    for _, r in valid.iterrows():
        print(f"- {r['Label']:<22} {r['Nama_Model']}")

    model = [{
        "Label": r["Label"],
        "Nama_Model": r["Nama_Model"],
        "order": ast.literal_eval(r["Order"]),
        "seasonal_order": ast.literal_eval(r["Seasonal_Order"]),
        "exog": [] if r["Eksogen"] == "-" else [e.strip() for e in r["Eksogen"].split(",")],
    } for _, r in valid.iterrows()]

    valid.to_csv(MODEL_CSV, index=False)
    return train, test, model, cek


# =============================================================================
# TAHAP 2: PERAMALAN 9 BULAN TESTING + CI 95%
# =============================================================================

def peramalan(train, test, model):
    print("\n" + "=" * 75)
    print(f"TAHAP 2: PERAMALAN {len(test)} BULAN TESTING (BLIND) + CI 95%")
    print("=" * 75)

    data_tr = em.skala_data(train)
    data_te = em.skala_data(test)
    y_tr = data_tr[TARGET_COL]

    baris = []
    for m in model:
        exog_tr = data_tr[m["exog"]].astype(float) if m["exog"] else None
        exog_te = data_te[m["exog"]].astype(float) if m["exog"] else None

        result, info = em.fit_terbaik(y_tr, exog_tr, m["order"], m["seasonal_order"])
        fc = result.get_forecast(steps=len(test), exog=exog_te)
        mean_t = fc.predicted_mean
        ci_t = fc.conf_int(alpha=ALPHA_CI)
        se_t = fc.se_mean
        var_t = fc.var_pred_mean

        for h, periode in enumerate(test.index):
            aktual = float(test[TARGET_COL].iloc[h])
            pred = float(em.ke_kg(mean_t.iloc[h]))
            pred_mean_ln = (float(np.exp(mean_t.iloc[h] + 0.5 * var_t.iloc[h]))
                            if em.TRANSFORMASI == "log" else pred)
            bawah = float(em.ke_kg(ci_t.iloc[h, 0]))
            atas = float(em.ke_kg(ci_t.iloc[h, 1]))
            baris.append({
                "Label": m["Label"],
                "Nama_Model": m["Nama_Model"],
                "Periode": periode.strftime("%Y-%m"),
                "Horizon": h + 1,
                "Aktual_Kg": aktual,
                "Prediksi_Kg": pred,
                "Prediksi_Mean_Lognormal_Kg": pred_mean_ln,
                "Batas_Bawah_95_Kg": bawah,
                "Batas_Atas_95_Kg": atas,
                "Lebar_CI_Kg": atas - bawah,
                "SE_Skala_Transformasi": float(se_t.iloc[h]),
                "Error_Kg": aktual - pred,
                "APE_%": abs(aktual - pred) / aktual * 100,
                "Dalam_CI_95": "Ya" if bawah <= aktual <= atas else "Tidak",
            })
        print(f"- {m['Label']:<22} {m['Nama_Model']:<36} optimizer {info['Optimizer_Terpilih']}, "
              f"konvergen {info['Konvergen']}")

    # Pembanding seasonal naive: y_hat(t) = y(t-12), tanpa CI
    y_all = pd.concat([train, test])[TARGET_COL].astype(float)
    n_train = len(train)
    for h, periode in enumerate(test.index):
        aktual = float(test[TARGET_COL].iloc[h])
        pred = float(y_all.iloc[n_train + h - M])
        baris.append({
            "Label": LABEL_NAIVE, "Nama_Model": "y[t-12]",
            "Periode": periode.strftime("%Y-%m"), "Horizon": h + 1,
            "Aktual_Kg": aktual, "Prediksi_Kg": pred,
            "Prediksi_Mean_Lognormal_Kg": np.nan,
            "Batas_Bawah_95_Kg": np.nan, "Batas_Atas_95_Kg": np.nan,
            "Lebar_CI_Kg": np.nan, "SE_Skala_Transformasi": np.nan,
            "Error_Kg": aktual - pred, "APE_%": abs(aktual - pred) / aktual * 100,
            "Dalam_CI_95": "-",
        })

    df = pd.DataFrame(baris)
    df.to_csv(PERAMALAN_CSV, index=False)
    print(f"\nPeramalan per bulan disimpan ke: {PERAMALAN_CSV}")
    return df


# =============================================================================
# TAHAP 3: EVALUASI DAN ANALISIS
# =============================================================================

def evaluasi(df):
    print("\n" + "=" * 75)
    print("TAHAP 3: EVALUASI PERAMALAN TERHADAP DATA AKTUAL TESTING")
    print("=" * 75)

    baris = []
    for label, isi in df.groupby("Label", sort=False):
        met = hitung_metrik(isi["Aktual_Kg"], isi["Prediksi_Kg"])
        info = {"Label": label, "Nama_Model": isi["Nama_Model"].iloc[0], **met,
                "APE_maks_%": float(isi["APE_%"].max()),
                "Bulan_APE_maks": isi.loc[isi["APE_%"].idxmax(), "Periode"],
                "Bias_rata2_Kg": float(isi["Error_Kg"].mean())}
        if label != LABEL_NAIVE:
            info["MAPE_mean_lognormal_%"] = hitung_metrik(
                isi["Aktual_Kg"], isi["Prediksi_Mean_Lognormal_Kg"])["MAPE_%"]
            n_dalam = int((isi["Dalam_CI_95"] == "Ya").sum())
            info["Cakupan_CI_95_%"] = n_dalam / len(isi) * 100
            info["Jumlah_Dalam_CI"] = f"{n_dalam}/{len(isi)}"
            info["Lebar_CI_rata2_Kg"] = float(isi["Lebar_CI_Kg"].mean())
            info["Lebar_CI_rata2_%_aktual"] = float((isi["Lebar_CI_Kg"] / isi["Aktual_Kg"]).mean() * 100)
        rata2 = float(isi["Aktual_Kg"].mean())
        target = em.target_akurasi(rata2)
        info["RMSE_%_rata2"] = met["RMSE"] / rata2 * 100
        info["MAE_%_rata2"] = met["MAE"] / rata2 * 100
        for nama in METRIK_TARGET:
            info[f"Target_{nama}"] = em.cek_target(target, nama, met[nama])
        baris.append(info)

    df_eval = pd.DataFrame(baris).sort_values("MAPE_%")
    df_eval.to_csv(EVALUASI_CSV, index=False)

    kolom = ["Label", "MAPE_%", "RMSE", "MAE", "R2", "Bias_rata2_Kg", "APE_maks_%",
             "Bulan_APE_maks", "Cakupan_CI_95_%", "Lebar_CI_rata2_%_aktual"]
    print(df_eval[kolom].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # Uji arah bias: apakah error rata-rata berbeda dari nol (t-test satu sampel)
    print("\nUji bias (H0: rata-rata error = 0, t-test satu sampel):")
    for label, isi in df.groupby("Label", sort=False):
        t, p = stats.ttest_1samp(isi["Error_Kg"], 0.0)
        print(f"- {label:<22} t = {t:6.2f}, p = {p:.4f} -> "
              f"{'bias signifikan' if p < 0.05 else 'tidak ada bias signifikan'}")

    print(f"\nEvaluasi disimpan ke: {EVALUASI_CSV}")
    return df_eval


def banding_rolling(df):
    """Multi-step (script 08) vs one-step rolling origin (script 07), APE per bulan."""
    print("\n" + "=" * 75)
    print("TAHAP 3B: MULTI-STEP (08) VS ROLLING ORIGIN 1 LANGKAH (07)")
    print("=" * 75)

    if not ROLLING_07_CSV.exists():
        print("File rolling origin script 07 tidak ditemukan; dilewati.")
        return pd.DataFrame()

    roll = pd.read_csv(ROLLING_07_CSV)[["Label", "Periode_Target", "Prediksi", "APE_%"]]
    roll = roll.rename(columns={"Periode_Target": "Periode", "Prediksi": "Prediksi_Rolling_Kg",
                                "APE_%": "APE_Rolling_%"})
    gabung = df.merge(roll, on=["Label", "Periode"], how="inner")
    gabung = gabung[["Label", "Periode", "Horizon", "Aktual_Kg", "Prediksi_Kg", "APE_%",
                     "Prediksi_Rolling_Kg", "APE_Rolling_%"]].rename(
        columns={"Prediksi_Kg": "Prediksi_MultiStep_Kg", "APE_%": "APE_MultiStep_%"})
    gabung["Selisih_APE_poin"] = gabung["APE_MultiStep_%"] - gabung["APE_Rolling_%"]
    gabung.to_csv(BANDING_07_CSV, index=False)

    ringkas = gabung.groupby("Label", sort=False).agg(
        MAPE_MultiStep=("APE_MultiStep_%", "mean"),
        MAPE_Rolling=("APE_Rolling_%", "mean"),
        MAPE_MultiStep_h1_3=("APE_MultiStep_%", lambda s: s.iloc[:3].mean()),
        MAPE_MultiStep_h4_6=("APE_MultiStep_%", lambda s: s.iloc[3:6].mean()),
        MAPE_MultiStep_h7_9=("APE_MultiStep_%", lambda s: s.iloc[6:9].mean()),
    ).reset_index()
    juni = gabung[gabung["Periode"] == "2025-06"][["Label", "Aktual_Kg", "Prediksi_MultiStep_Kg",
                                                     "APE_MultiStep_%", "Prediksi_Rolling_Kg",
                                                     "APE_Rolling_%"]]
    print(ringkas.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print("\nJuni 2025 (Iduladha):")
    print(juni.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print(f"\nDetail disimpan ke: {BANDING_07_CSV}")
    return gabung


# =============================================================================
# TAHAP 4: VISUALISASI (FAN CHART)
# =============================================================================

def visualisasi(train, test, df):
    print("\n" + "=" * 75)
    print("TAHAP 4: VISUALISASI FAN CHART")
    print("=" * 75)

    model_label = [l for l in df["Label"].unique() if l != LABEL_NAIVE]
    idx_test = test.index

    for label in model_label:
        isi = df[df["Label"] == label]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(train.index, train[TARGET_COL], color="black", linewidth=1.5,
                label="Aktual historis (training)")
        ax.plot(idx_test, test[TARGET_COL], color="black", marker="o", linewidth=1.5,
                linestyle=":", label="Aktual testing")
        ax.plot(idx_test, isi["Prediksi_Kg"], color="tab:blue", linestyle="--", marker=".",
                linewidth=1.8, label="Peramalan")
        ax.fill_between(idx_test, isi["Batas_Bawah_95_Kg"], isi["Batas_Atas_95_Kg"],
                        color="tab:blue", alpha=0.18, label="Interval kepercayaan 95%")
        ax.axvline(idx_test[0], color="grey", linewidth=0.8)
        ax.set_title(f"Peramalan Testing Apr–Des 2025: {isi['Nama_Model'].iloc[0]}")
        ax.set_xlabel("Periode")
        ax.set_ylabel("Permintaan daging kambing (kg)")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"{v:,.0f}".replace(",", ".")))
        ax.legend(fontsize=8, loc="upper left")
        fig.tight_layout()
        path = GRAFIK_DIR / f"08_fan_chart_{nama_file(label)}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"- {path.name}")

    # Grafik gabungan periode testing
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(idx_test, test[TARGET_COL], color="black", marker="o", linewidth=2, label="Aktual")
    for label in list(model_label) + [LABEL_NAIVE]:
        isi = df[df["Label"] == label]
        gaya = ":" if label == LABEL_NAIVE else "--"
        ax.plot(idx_test, isi["Prediksi_Kg"], linestyle=gaya, marker=".", label=label)
    ax.set_title("Perbandingan Peramalan Model Valid pada Testing Apr–Des 2025")
    ax.set_xlabel("Periode")
    ax.set_ylabel("Permintaan daging kambing (kg)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:,.0f}".replace(",", ".")))
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(GRAFIK_DIR / "08_perbandingan_peramalan.png", dpi=150)
    plt.close(fig)
    print("- 08_perbandingan_peramalan.png")


# =============================================================================
# RINGKASAN MARKDOWN
# =============================================================================

def tabel_markdown(df, kolom, fmt="{:,.2f}"):
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "-" if not np.isfinite(v) else fmt.format(v)
        return str(v)
    baris = ["| " + " | ".join(kolom) + " |", "|" + "|".join(["---"] * len(kolom)) + "|"]
    for _, r in df.iterrows():
        baris.append("| " + " | ".join(f(r[k]) for k in kolom) + " |")
    return "\n".join(baris)


def tulis_ringkasan(df, df_eval, cek, gabung):
    L = []
    L.append("# Ringkasan Script 08: Peramalan dan Visualisasi pada Data Testing\n")
    L.append(f"Dibuat otomatis oleh `08_peramalan_visualisasi.py` "
             f"(statsmodels {statsmodels.__version__}).\n")
    L.append("## Pemeriksaan data testing\n")
    L.append(tabel_markdown(cek, ["Pemeriksaan", "Hasil", "Lulus"]))
    L.append("")
    L.append("## Desain\n")
    L.append("- Periode peramalan = data testing 25% (`06_testing_set.csv`, Apr–Des 2025, 9 bulan).")
    L.append("- Model = model valid dari script 07 (lulus Ljung-Box dan Shapiro-Wilk), dilatih pada "
             "27 bulan training lalu meramal 9 bulan sekaligus tanpa melihat data testing "
             "(berbeda dengan rolling origin script 07 yang meramal 1 bulan lalu dilatih ulang).")
    L.append(f"- Transformasi estimasi: `{em.TRANSFORMASI}` ({em.DESKRIPSI_TRANSFORMASI}). "
             "Ramalan dan batas CI 95% dihitung pada skala log lalu dikembalikan ke kg dengan "
             "exp(); karena exp monoton, batasnya tetap CI 95% dan menjadi tidak simetris. "
             "exp(mean log) = median ramalan; kolom `Prediksi_Mean_Lognormal_Kg` di CSV memakai "
             "koreksi bias lognormal exp(μ + σ²/2).")
    L.append("- **ARIMAX memakai nilai eksogen aktual periode testing** (harga dan Koefisien_Musim "
             "dari `06_testing_set.csv`). Dalam peramalan nyata harga masa depan belum diketahui, "
             "sehingga akurasi ARIMAX di sini adalah batas atas (optimistis).\n")

    L.append("## Akurasi peramalan 9 bulan (kg)\n")
    L.append(tabel_markdown(df_eval, ["Label", "Nama_Model", "MAPE_%", "RMSE", "MAE", "MSE", "R2",
                                      "Bias_rata2_Kg", "APE_maks_%", "Bulan_APE_maks"]))
    L.append("")
    L.append("### Terhadap target akurasi\n")
    rata2 = float(df.drop_duplicates("Periode")["Aktual_Kg"].mean())
    L.append(f"Target: {em.DESKRIPSI_TARGET}. Pada data testing: "
             f"{teks_target(em.target_akurasi(rata2), rata2)}.\n")
    L.append(tabel_markdown(df_eval, ["Label", "RMSE_%_rata2", "MAE_%_rata2"]
                            + [f"Target_{n}" for n in METRIK_TARGET]))
    L.append("\n> Target RMSE/MAE/MSE relatif terhadap rata-rata permintaan aktual, karena data "
             "penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM).\n")

    L.append("## Interval kepercayaan 95%\n")
    ev = df_eval[df_eval["Label"] != LABEL_NAIVE]
    L.append(tabel_markdown(ev, ["Label", "Jumlah_Dalam_CI", "Cakupan_CI_95_%",
                                 "Lebar_CI_rata2_Kg", "Lebar_CI_rata2_%_aktual",
                                 "MAPE_mean_lognormal_%"]))
    L.append("")

    if not gabung.empty:
        L.append("## Multi-step (08) vs rolling origin 1 langkah (07)\n")
        rk = gabung.groupby("Label", sort=False).agg(
            MAPE_MultiStep=("APE_MultiStep_%", "mean"),
            MAPE_Rolling=("APE_Rolling_%", "mean"),
            MAPE_h1_3=("APE_MultiStep_%", lambda s: s.iloc[:3].mean()),
            MAPE_h4_6=("APE_MultiStep_%", lambda s: s.iloc[3:6].mean()),
            MAPE_h7_9=("APE_MultiStep_%", lambda s: s.iloc[6:9].mean()),
        ).reset_index()
        L.append(tabel_markdown(rk, list(rk.columns)))
        L.append("")
        L.append("### Juni 2025 (Iduladha, horizon 3)\n")
        juni = gabung[gabung["Periode"] == "2025-06"]
        L.append(tabel_markdown(juni, ["Label", "Aktual_Kg", "Prediksi_MultiStep_Kg", "APE_MultiStep_%",
                                       "Prediksi_Rolling_Kg", "APE_Rolling_%"], "{:,.1f}"))
        L.append("")

    L.append("## Peramalan per bulan\n")
    for label, isi in df[df["Label"] != LABEL_NAIVE].groupby("Label", sort=False):
        L.append(f"### {label}: {isi['Nama_Model'].iloc[0]}\n")
        L.append(tabel_markdown(isi, ["Periode", "Aktual_Kg", "Prediksi_Kg",
                                      "Prediksi_Mean_Lognormal_Kg", "Batas_Bawah_95_Kg",
                                      "Batas_Atas_95_Kg", "Error_Kg", "APE_%", "Dalam_CI_95"],
                                "{:,.0f}"))
        L.append("")

    L.append("## Grafik\n")
    L.append("- Fan chart per model: `data/hasil_08/grafik/08_fan_chart_*.png`")
    L.append("- Perbandingan semua model: `data/hasil_08/grafik/08_perbandingan_peramalan.png`")

    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nRingkasan Markdown disimpan ke: {RINGKASAN_MD}")


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    penjelasan.mulai("08_forecasting_data_testing")
    print("\n" + "=" * 75)
    print("PROGRAM PERAMALAN & VISUALISASI (DATA TESTING APR-DES 2025)")
    print("=" * 75)

    train, test, model, cek = muat_data_dan_model()
    df = peramalan(train, test, model)
    df_eval = evaluasi(df)
    penjelasan.jelaskan_08(train, test, df, df_eval)   # contoh perhitungan rumus [9]
    gabung = banding_rolling(df)
    visualisasi(train, test, df)
    tulis_ringkasan(df, df_eval, cek, gabung)

    print("\n" + "=" * 75)
    print("TAHAP 08 SELESAI. Peramalan data testing Apr-Des 2025 selesai.")
    print("=" * 75)


if __name__ == "__main__":
    main()
