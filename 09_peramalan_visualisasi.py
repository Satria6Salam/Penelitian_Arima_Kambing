"""
=============================================================================
PROGRAM PERAMALAN DAN VISUALISASI MODEL FINAL
File: 09_peramalan_visualisasi.py

Mengikuti tahap "PERAMALAN & VISUALISASI (FORECASTING)" pada alur penelitian.
Model final: SARIMA(1,0,0)x(1,1,0,12) dengan transformasi log, model valid
(lulus Ljung-Box dan Shapiro-Wilk di script 07) yang tidak memerlukan data
masa depan. Estimasi memakai estimasi_model.py (sama dengan script 06-08).

Dua bagian:
A. VALIDASI (Apr-Sep 2025): parameter dikunci dari 27 bulan training, lalu
   diekstrapolasi HORIZON bulan dan dibandingkan dengan data aktual testing.
   Bukti akurasi ekstrapolasi sebelum dipakai ke masa depan.
B. PERAMALAN UTAMA (Jan-Jun 2026): model di-fit ulang pada 36 bulan penuh
   (Jan 2023-Des 2025), dicek ulang validitas residualnya, lalu diekstrapolasi
   HORIZON bulan ke depan.

Untuk setiap bulan h:
    Batas = Y_hat ± Z x SE   (Z = 1,96)
dihitung pada skala log lalu dikembalikan ke kg dengan exp(), sehingga
interval di kg tidak simetris. Fan chart menampilkan data historis, garis
peramalan, dan pita interval 95%.

Input  : data/hasil_06/06_training_set.csv, 06_testing_set.csv
Output : data/hasil_09/ (utama), data/hasil_09/validasi_apr_sep_2025/,
         09_ringkasan_peramalan.md
=============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels

from pathlib import Path
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

import keterangan_csv as kk  # keterangan kolom pada setiap CSV hasil
import estimasi_model as em
import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/


# =============================================================================
# PENGATURAN PATH DIREKTORI
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRAIN_CSV = DATA_DIR / "hasil_06" / "06_training_set.csv"
TEST_CSV = DATA_DIR / "hasil_06" / "06_testing_set.csv"

OUTPUT_DIR = DATA_DIR / "hasil_09"
VALIDASI_DIR = OUTPUT_DIR / "validasi_apr_sep_2025"
RINGKASAN_MD = BASE_DIR / "09_ringkasan_peramalan.md"

for d in [OUTPUT_DIR / "grafik", VALIDASI_DIR / "grafik"]:
    d.mkdir(parents=True, exist_ok=True)


# =============================================================================
# KONSTANTA PENELITIAN
# =============================================================================

TARGET_COL = em.TARGET_COL

NAMA_MODEL_FINAL = "SARIMA(1,0,0)x(1,1,0,12)"
ORDER = (1, 0, 0)
SEASONAL_ORDER = (1, 1, 0, 12)

HORIZON = 6                 # t+1 sampai t+6

ALPHA = 0.05
Z = float(stats.norm.ppf(1 - ALPHA / 2))   # 1,96
LJUNG_BOX_LAGS = [6, 9, 12]

# Tanggal Iduladha 2026 (perkiraan kalender Hijriah; dipakai hanya sebagai catatan)
IDULADHA_2026 = pd.Timestamp("2026-05-27")


# =============================================================================
# FUNGSI BANTUAN
# =============================================================================

def rp(nilai, desimal=0):
    """Format angka gaya Indonesia: titik ribuan, koma desimal."""
    teks = f"{nilai:,.{desimal}f}"
    return teks.replace(",", "X").replace(".", ",").replace("X", ".")


def tabel_markdown(df, kolom, fmt=None):
    fmt = fmt or {}
    def f(k, v):
        if isinstance(v, (float, np.floating)):
            return "-" if not np.isfinite(v) else fmt.get(k, lambda x: rp(x, 2))(v)
        return str(v)
    baris = ["| " + " | ".join(kolom) + " |", "|" + "|".join(["---"] * len(kolom)) + "|"]
    for _, r in df.iterrows():
        baris.append("| " + " | ".join(f(k, r[k]) for k in kolom) + " |")
    return "\n".join(baris)


def muat_data():
    for f in [TRAIN_CSV, TEST_CSV]:
        if not f.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {f}. Jalankan script 06 dulu.")
    train = kk.baca_csv(TRAIN_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    test = kk.baca_csv(TEST_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    if HORIZON > len(test):
        raise ValueError(f"HORIZON {HORIZON} melebihi panjang data testing ({len(test)} bulan).")
    return train, test


# =============================================================================
# ESTIMASI, DIAGNOSTIK, DAN EKSTRAPOLASI
# =============================================================================

def fit_model(data_kg):
    """Fit model final pada data (satuan kg) dan kembalikan hasil + tabel parameter."""
    data = em.skala_data(data_kg)
    result, info = em.fit_terbaik(data[TARGET_COL], None, ORDER, SEASONAL_ORDER)
    ci = result.conf_int(alpha=ALPHA)
    df_param = pd.DataFrame({
        "Parameter": result.params.index,
        "Koefisien": result.params.values,
        "Std_Error": result.bse.values,
        "P_value": result.pvalues.values,
        "CI95_Bawah": ci.iloc[:, 0].values,
        "CI95_Atas": ci.iloc[:, 1].values,
    })
    return result, info, df_param


def diagnostik(result):
    """Ljung-Box dan Shapiro-Wilk pada residual setelah burn-in."""
    resid = result.resid.iloc[int(result.loglikelihood_burn):]
    model_df = ORDER[0] + ORDER[2] + SEASONAL_ORDER[0] + SEASONAL_ORDER[2]
    baris = []
    for lag in LJUNG_BOX_LAGS:
        if lag - model_df <= 0 or lag >= len(resid):
            continue
        lb = acorr_ljungbox(resid, lags=[lag], model_df=model_df, return_df=True)
        p = float(lb["lb_pvalue"].iloc[0])
        baris.append({"Uji": f"Ljung-Box lag {lag}", "Statistik": float(lb["lb_stat"].iloc[0]),
                      "df": lag - model_df, "P_value": p,
                      "Keputusan": "Lulus (white noise)" if p > ALPHA else "Gagal"})
    w, p = stats.shapiro(resid)
    baris.append({"Uji": "Shapiro-Wilk", "Statistik": float(w), "df": np.nan, "P_value": float(p),
                  "Keputusan": "Lulus (normal)" if p > ALPHA else "Gagal"})
    df = pd.DataFrame(baris)
    df.insert(0, "Jumlah_Residual", len(resid))
    return df


def ekstrapolasi(result, data_kg, periode_ramal, aktual=None, iduladha=None):
    """Ramalan HORIZON langkah + interval 95% dihitung manual (Ŷlog ± Z×SE)."""
    fc = result.get_forecast(steps=HORIZON)
    mean_log = fc.predicted_mean.values
    se_log = fc.se_mean.values
    ci_sm = fc.conf_int(alpha=ALPHA).values

    baris = []
    for h in range(HORIZON):
        moe = Z * se_log[h]
        bawah_log, atas_log = mean_log[h] - moe, mean_log[h] + moe
        assert np.allclose([bawah_log, atas_log], ci_sm[h], atol=1e-8)
        y_hat = float(em.ke_kg(mean_log[h]))
        bawah, atas = float(em.ke_kg(bawah_log)), float(em.ke_kg(atas_log))
        info = {
            "h": h + 1,
            "t": len(data_kg) + h + 1,
            "Periode": periode_ramal[h].strftime("%Y-%m"),
            "Yhat_log": float(mean_log[h]),
            "SE_log": float(se_log[h]),
            "Z": Z,
            "MoE_log": float(moe),
            "Batas_Bawah_log": float(bawah_log),
            "Batas_Atas_log": float(atas_log),
            "Yhat_Kg": y_hat,
            "Batas_Bawah_95_Kg": bawah,
            "Batas_Atas_95_Kg": atas,
            "Lebar_Interval_Kg": atas - bawah,
            "Jarak_ke_Bawah_Kg": y_hat - bawah,
            "Jarak_ke_Atas_Kg": atas - y_hat,
        }
        if iduladha is not None:
            info["Bulan_Iduladha"] = iduladha[h]
        if aktual is not None:
            a = float(aktual[h])
            info.update({
                "Aktual_Kg": a,
                "Error_Kg": a - y_hat,
                "APE_%": abs(a - y_hat) / a * 100,
                "Aktual_dalam_Interval": "Ya" if bawah <= a <= atas else "Tidak",
            })
        baris.append(info)
    return pd.DataFrame(baris)


# =============================================================================
# FAN CHART
# =============================================================================

def fan_chart(historis, df, path, judul, label_historis, tanda_puncak, catatan_vline=None):
    idx = pd.to_datetime(df["Periode"])
    sambung_x = [historis.index[-1]] + list(idx)
    sambung_y = [float(historis[TARGET_COL].iloc[-1])] + list(df["Yhat_Kg"])

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(historis.index, historis[TARGET_COL], color="black", linewidth=1.8,
            label=label_historis)
    ax.fill_between(idx, df["Batas_Bawah_95_Kg"], df["Batas_Atas_95_Kg"],
                    color="#4a90d9", alpha=0.22, linewidth=0, label="Interval kepercayaan 95%")
    ax.plot(sambung_x, sambung_y, color="#1f5fbf", linestyle="--", linewidth=2,
            label=f"Peramalan {HORIZON} bulan ({NAMA_MODEL_FINAL}, log)")
    if "Aktual_Kg" in df:
        ax.scatter(idx, df["Aktual_Kg"], color="black", marker="o", s=30, zorder=5,
                   facecolors="white", label="Aktual testing (pembanding)")

    r = df.loc[df["Yhat_Kg"].idxmax()]
    x = pd.Timestamp(r["Periode"])
    teks = f"{tanda_puncak}\nramalan {rp(r['Yhat_Kg'])} kg\nbatas atas {rp(r['Batas_Atas_95_Kg'])} kg"
    if "Aktual_Kg" in df:
        teks += f"\naktual {rp(r['Aktual_Kg'])} kg"
    ax.annotate(teks, xy=(x, r["Yhat_Kg"]), xytext=(-20, -10), textcoords="offset points",
                fontsize=8, va="top", ha="right",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="none", alpha=0.85),
                arrowprops=dict(arrowstyle="-", color="grey", linewidth=0.8))

    if catatan_vline is not None:
        tgl, label = catatan_vline
        ax.axvline(tgl, color="#c0392b", linewidth=0.9, linestyle="-.")
        ax.text(tgl, ax.get_ylim()[1] * 0.97, f"{label} ", fontsize=8, color="#c0392b",
                ha="right", va="top")

    ax.axvline(historis.index[-1], color="grey", linewidth=0.8, linestyle=":")
    ax.set_title(judul)
    ax.set_xlabel("Periode (bulan)")
    ax.set_ylabel("Volume permintaan (kg)")
    ax.set_ylim(0, max(historis[TARGET_COL].max(), df["Batas_Atas_95_Kg"].max()) * 1.08)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: rp(v)))
    ax.text(historis.index[-1], ax.get_ylim()[1] * 0.02, " titik asal ramalan", fontsize=8,
            color="grey", va="bottom")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


# =============================================================================
# BAGIAN A: VALIDASI APR-SEP 2025
# =============================================================================

def bagian_validasi(train, test):
    print("\n" + "=" * 75)
    print("BAGIAN A: VALIDASI EKSTRAPOLASI (fit 27 bulan training -> Apr-Sep 2025)")
    print("=" * 75)

    result, info, df_param = fit_model(train)
    df = ekstrapolasi(result, train, test.index[:HORIZON],
                      aktual=test[TARGET_COL].values[:HORIZON],
                      iduladha=["Ya" if k > 1 else "Tidak"
                                for k in test["Koefisien_Musim"].values[:HORIZON]])
    kk.simpan_csv(df_param, VALIDASI_DIR / "09_parameter_model_validasi.csv", index=False)
    kk.simpan_csv(df, VALIDASI_DIR / "09_peramalan_validasi_apr_sep_2025.csv", index=False)
    fan_chart(train, df, VALIDASI_DIR / "grafik" / "09_fan_chart_validasi.png",
              "Validasi Peramalan Apr–Sep 2025 (parameter dari 27 bulan training)",
              "Data aktual historis (training)", "Iduladha Jun 2025")

    print(df[["h", "Periode", "Yhat_Kg", "Batas_Bawah_95_Kg", "Batas_Atas_95_Kg", "Aktual_Kg",
              "APE_%", "Aktual_dalam_Interval"]].to_string(
        index=False, float_format=lambda x: f"{x:,.1f}"))
    print(f"MAPE {HORIZON} bulan: {df['APE_%'].mean():.2f}% | dalam interval: "
          f"{(df['Aktual_dalam_Interval'] == 'Ya').sum()}/{HORIZON}")
    return df, df_param


# =============================================================================
# BAGIAN B: PERAMALAN UTAMA JAN-JUN 2026
# =============================================================================

def bagian_utama(train, test):
    print("\n" + "=" * 75)
    print("BAGIAN B: PERAMALAN UTAMA (fit 36 bulan penuh -> Jan-Jun 2026)")
    print("=" * 75)

    data_penuh = pd.concat([train, test])
    result, info, df_param = fit_model(data_penuh)
    df_diag = diagnostik(result)

    periode = pd.date_range(data_penuh.index[-1] + pd.offsets.MonthBegin(1),
                            periods=HORIZON, freq="MS")
    df = ekstrapolasi(result, data_penuh, periode)

    kk.simpan_csv(df_param, OUTPUT_DIR / "09_parameter_model_final.csv", index=False)
    kk.simpan_csv(df_diag, OUTPUT_DIR / "09_diagnostik_model_final.csv", index=False)
    kk.simpan_csv(df, OUTPUT_DIR / "09_peramalan_jan_jun_2026.csv", index=False)

    fan_chart(data_penuh, df, OUTPUT_DIR / "grafik" / "09_fan_chart.png",
              f"Fan Chart Peramalan Permintaan Daging Kambing {periode[0]:%b %Y}–{periode[-1]:%b %Y}",
              "Data aktual historis (Jan 2023–Des 2025)",
              "Puncak musiman (pola Iduladha Juni)",
              catatan_vline=(IDULADHA_2026, "Iduladha 2026 ±27 Mei"))

    print(df_param.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"LogL {result.llf:.4f} | AIC {result.aic:.4f} | BIC {result.bic:.4f} | "
          f"optimizer {info['Optimizer_Terpilih']} | konvergen {info['Konvergen']}")
    print(df_diag.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(df[["h", "Periode", "Yhat_Kg", "SE_log", "Batas_Bawah_95_Kg", "Batas_Atas_95_Kg",
              "Lebar_Interval_Kg"]].to_string(index=False, float_format=lambda x: f"{x:,.4f}"
                                                if x < 1 else f"{x:,.0f}"))
    return data_penuh, result, info, df_param, df_diag, df


# =============================================================================
# RINGKASAN MARKDOWN
# =============================================================================

def contoh_manual(r):
    baris = [
        f"- Ŷ (skala log) = {r['Yhat_log']:.4f} → Ŷ = exp({r['Yhat_log']:.4f}) = "
        f"**{rp(r['Yhat_Kg'])} kg**",
        f"- SE (skala log) = {r['SE_log']:.4f}",
        f"- Margin of Error = Z × SE = {Z:.2f} × {r['SE_log']:.4f} = {r['MoE_log']:.4f}",
        f"- Batas bawah = exp({r['Yhat_log']:.4f} − {r['MoE_log']:.4f}) = "
        f"exp({r['Batas_Bawah_log']:.4f}) = **{rp(r['Batas_Bawah_95_Kg'])} kg**",
        f"- Batas atas = exp({r['Yhat_log']:.4f} + {r['MoE_log']:.4f}) = "
        f"exp({r['Batas_Atas_log']:.4f}) = **{rp(r['Batas_Atas_95_Kg'])} kg**",
        f"- Interval tidak simetris di kg: Ŷ − bawah = {rp(r['Jarak_ke_Bawah_Kg'])} kg, "
        f"atas − Ŷ = {rp(r['Jarak_ke_Atas_Kg'])} kg (lebar {rp(r['Lebar_Interval_Kg'])} kg).",
        f"- Interpretasi bisnis: dengan keyakinan 95%, permintaan {r['Periode']} berada di kisaran "
        f"{rp(r['Batas_Bawah_95_Kg'])}–{rp(r['Batas_Atas_95_Kg'])} kg.",
    ]
    return baris


def tulis_ringkasan(train, df_val, data_penuh, result, info, df_param, df_diag, df):
    f0 = lambda x: rp(x)
    f4 = lambda x: f"{x:.4f}"
    L = []
    L.append("# Ringkasan Script 09: Peramalan dan Visualisasi Model Final\n")
    L.append(f"Dibuat otomatis oleh `09_peramalan_visualisasi.py` "
             f"(statsmodels {statsmodels.__version__}).\n")

    L.append("## Desain\n")
    L.append(f"- Model final: **{NAMA_MODEL_FINAL}** dengan transformasi log, model valid dari "
             "script 07 yang tidak memerlukan data masa depan.")
    L.append(f"- Interval 95%: Ŷ ± Z × SE dengan Z = {Z:.2f}, dihitung pada skala log lalu "
             "dikembalikan ke kg dengan exp(). Karena itu interval di kg tidak simetris (sisi atas "
             "lebih lebar). Ŷ = exp(ramalan log) adalah median ramalan.")
    L.append("- Bagian A memvalidasi ekstrapolasi pada data testing; Bagian B adalah peramalan "
             "utama Jan–Jun 2026.\n")

    # Bagian A
    n_val = int((df_val["Aktual_dalam_Interval"] == "Ya").sum())
    L.append("## A. Validasi ekstrapolasi Apr–Sep 2025\n")
    L.append(f"Parameter dikunci dari {len(train)} bulan training (Jan 2023–Mar 2025), lalu "
             f"diekstrapolasi {HORIZON} bulan dan dibandingkan dengan aktual testing. "
             f"MAPE **{rp(df_val['APE_%'].mean(), 2)}%**, aktual di dalam interval 95% pada "
             f"**{n_val} dari {HORIZON}** bulan. Fan chart: "
             "`data/hasil_09/validasi_apr_sep_2025/grafik/09_fan_chart_validasi.png`.\n")
    L.append(tabel_markdown(df_val, ["h", "Periode", "Yhat_Kg", "Batas_Bawah_95_Kg",
                                     "Batas_Atas_95_Kg", "Aktual_Kg", "APE_%",
                                     "Aktual_dalam_Interval"],
                            {"Yhat_Kg": f0, "Batas_Bawah_95_Kg": f0, "Batas_Atas_95_Kg": f0,
                             "Aktual_Kg": f0, "APE_%": lambda x: rp(x, 2)}))
    L.append("")

    # Bagian B
    L.append(f"## B. Model final untuk peramalan (fit {len(data_penuh)} bulan, "
             f"{data_penuh.index[0]:%b %Y}–{data_penuh.index[-1]:%b %Y})\n")
    L.append("### Parameter terkunci\n")
    L.append(tabel_markdown(df_param, list(df_param.columns),
                            {k: f4 for k in df_param.columns}))
    L.append(f"\nLogL {result.llf:.4f}; AIC {result.aic:.4f}; BIC {result.bic:.4f}; "
             f"optimizer {info['Optimizer_Terpilih']}; konvergen {info['Konvergen']}.\n")
    L.append("### Validitas residual\n")
    L.append(tabel_markdown(df_diag, list(df_diag.columns),
                            {"Statistik": f4, "P_value": f4, "df": lambda x: f"{x:.0f}"}))
    lulus = (df_diag["Keputusan"].str.startswith("Lulus")).all()
    L.append(f"\nModel {'tetap valid (lulus seluruh uji)' if lulus else 'TIDAK lulus seluruh uji'} "
             f"setelah di-fit ulang pada {len(data_penuh)} bulan.\n")

    L.append(f"### Peramalan Jan–Jun 2026\n")
    L.append(tabel_markdown(df, ["h", "t", "Periode", "Yhat_Kg", "SE_log", "Batas_Bawah_95_Kg",
                                 "Batas_Atas_95_Kg", "Lebar_Interval_Kg"],
                            {"Yhat_Kg": f0, "Batas_Bawah_95_Kg": f0, "Batas_Atas_95_Kg": f0,
                             "Lebar_Interval_Kg": f0, "SE_log": f4}))
    L.append("")
    L.append(f"Efek corong: SE skala log naik dari {df['SE_log'].iloc[0]:.4f} (h=1) menjadi "
             f"{df['SE_log'].iloc[-1]:.4f} (h={HORIZON}); lebar interval relatif terhadap Ŷ naik dari "
             f"{rp(df['Lebar_Interval_Kg'].iloc[0] / df['Yhat_Kg'].iloc[0] * 100, 1)}% menjadi "
             f"{rp(df['Lebar_Interval_Kg'].iloc[-1] / df['Yhat_Kg'].iloc[-1] * 100, 1)}%.\n")

    L.append("### Contoh perhitungan manual\n")
    for i, judul in [(0, "Kasus A"), (1, "Kasus B")]:
        r = df.iloc[i]
        L.append(f"#### {judul}: bulan ke-{int(r['t'])} ({r['Periode']}), meramal {int(r['h'])} "
                 "langkah ke depan\n")
        L.extend(contoh_manual(r))
        L.append("")
    puncak = df.loc[df["Yhat_Kg"].idxmax()]
    L.append(f"#### Bulan puncak: bulan ke-{int(puncak['t'])} ({puncak['Periode']}), "
             f"h = {int(puncak['h'])}\n")
    L.extend(contoh_manual(puncak))
    L.append("")

    L.append("### Fan chart\n")
    L.append("`data/hasil_09/grafik/09_fan_chart.png`: garis hitam = aktual historis Jan 2023–Des "
             "2025, garis biru putus-putus = peramalan Jan–Jun 2026 (tersambung dari Des 2025), pita "
             "biru muda = interval 95%, garis merah = perkiraan Iduladha 2026 (±27 Mei).\n")

    L.append("### Keterbatasan: pergeseran Iduladha 2026\n")
    L.append(f"Iduladha 2026 diperkirakan jatuh sekitar **{IDULADHA_2026:%d %B %Y}** (akhir Mei), "
             "bukan Juni. Model SARIMA musiman lag 12 meniru pola 2023–2025, ketika Iduladha selalu "
             f"jatuh di bulan Juni, sehingga lonjakan diramalkan di **{puncak['Periode']}**. Dalam "
             "kenyataan, lonjakan permintaan 2026 kemungkinan besar bergeser ke Mei (atau terbagi "
             "antara Mei dan Juni). Model tidak diubah dan tidak ditambahkan dummy baru; hasil Mei "
             "dan Juni 2026 perlu dibaca dengan catatan ini.\n")

    L.append("### Keterbatasan: level ramalan 2026 lebih rendah dari 2025\n")
    banding = []
    for _, r in df.iterrows():
        tahun_lalu = pd.Timestamp(r["Periode"]) - pd.DateOffset(years=1)
        if tahun_lalu in data_penuh.index:
            nilai = float(data_penuh.loc[tahun_lalu, TARGET_COL])
            banding.append({"Periode": r["Periode"], "Yhat_Kg": r["Yhat_Kg"],
                            "Aktual_Tahun_Lalu_Kg": nilai,
                            "Perubahan_%": (r["Yhat_Kg"] / nilai - 1) * 100})
    df_banding = pd.DataFrame(banding)
    if not df_banding.empty:
        L.append(tabel_markdown(df_banding, list(df_banding.columns),
                                {"Yhat_Kg": f0, "Aktual_Tahun_Lalu_Kg": f0,
                                 "Perubahan_%": lambda x: rp(x, 1)}))
        L.append("")
        L.append(f"Ramalan 2026 rata-rata **{rp(df_banding['Perubahan_%'].mean(), 1)}%** "
                 "dibanding bulan yang sama tahun 2025. Penurunan ini bukan tren yang terlihat di "
                 "2025 (Jul–Des 2025 justru lebih tinggi dari 2024), melainkan efek koefisien AR "
                 f"musiman ({result.params['ar.S.L12']:.2f}) yang ikut mengulang penurunan level "
                 "tajam dari 2023 ke 2024 (misalnya Desember 2023 → Desember 2024 turun sekitar "
                 "31%). Dengan data hanya 3 tahun, pola ini sebaiknya dibaca sebagai skenario "
                 "konservatif, bukan prediksi penurunan pasar yang pasti; ramalan perlu diperbarui "
                 "setelah data 2026 tersedia.\n")

    L.append("### Implikasi manajerial\n")
    normal = df.drop(index=puncak.name)
    L.append(f"- **Pemesanan stok bulan normal (garis tengah):** Ŷ berkisar "
             f"{rp(normal['Yhat_Kg'].min())}–{rp(normal['Yhat_Kg'].max())} kg per bulan "
             f"(rata-rata {rp(normal['Yhat_Kg'].mean())} kg).")
    L.append(f"- **Batas bawah bulan normal:** {rp(normal['Batas_Bawah_95_Kg'].min())}–"
             f"{rp(normal['Batas_Bawah_95_Kg'].max())} kg, volume minimum yang hampir pasti terserap.")
    L.append(f"- **Persiapan puncak Iduladha:** Ŷ puncak {rp(puncak['Yhat_Kg'])} kg "
             f"(±{rp(puncak['Yhat_Kg'] / normal['Yhat_Kg'].mean(), 2)} kali bulan normal) dengan "
             f"batas atas 95% **{rp(puncak['Batas_Atas_95_Kg'])} kg** sebagai acuan kapasitas cold "
             f"storage, pasokan ternak, dan modal cadangan (stok pengaman "
             f"{rp(puncak['Batas_Atas_95_Kg'] - puncak['Yhat_Kg'])} kg di atas Ŷ).")
    L.append("- Karena Iduladha 2026 jatuh ±27 Mei, persiapan kapasitas puncak sebaiknya sudah siap "
             "pada pertengahan Mei 2026, bukan menunggu Juni.")
    L.append("- Interval melebar untuk bulan yang lebih jauh; rencana April–Juni sebaiknya "
             "diperbarui setelah data aktual Januari–Maret 2026 tersedia.")

    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nRingkasan Markdown disimpan ke: {RINGKASAN_MD}")


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    penjelasan.mulai("09_peramalan_visualisasi")
    print("\n" + "=" * 75)
    print("PROGRAM PERAMALAN & VISUALISASI MODEL FINAL")
    print("=" * 75)

    train, test = muat_data()
    df_val, _ = bagian_validasi(train, test)
    data_penuh, result, info, df_param, df_diag, df = bagian_utama(train, test)
    penjelasan.jelaskan_09(data_penuh, result, df)   # contoh perhitungan rumus [9]
    tulis_ringkasan(train, df_val, data_penuh, result, info, df_param, df_diag, df)

    print("\n" + "=" * 75)
    print("TAHAP 09 SELESAI. Peramalan Jan-Jun 2026 dan fan chart selesai.")
    print("=" * 75)


if __name__ == "__main__":
    main()
