"""
=============================================================================
PROGRAM PENYESUAIAN KALENDER IDULADHA (POST-PROCESSING RAMALAN)
File: 13_penyesuaian_iduladha.py

MASALAH
    Iduladha mengikuti kalender Hijriah sehingga maju ±11 hari per tahun
    Masehi. Pada data 2023-2025 Iduladha selalu jatuh di bulan Juni, sehingga
    SARIMA musiman (periode tetap 12 bulan) meramal lonjakan 2026 di Juni,
    padahal Iduladha 2026 jatuh ±27 Mei.

SOLUSI (TANPA MENGUBAH MODEL)
    Model, parameter, dan hasil script 03-12 TIDAK diubah. Script ini hanya
    membaca ramalan script 09 lalu memindahkan efek Iduladha ke bulan Iduladha
    yang sebenarnya.

    Asumsi: lonjakan pada "bulan Iduladha historis" (Juni) disebabkan oleh
    Iduladha, bukan oleh bulan Juni. Asumsi ini berbasis teori/pengetahuan
    lapangan; data 2023-2025 tidak dapat membuktikannya karena ketiga
    Iduladha jatuh di bulan yang sama.

RUMUS (pada skala log, konsisten dengan model log)
    S          = bulan lonjakan pada ramalan model (bulan Iduladha historis)
    Normal_S   = ramalan bulan sebelum S (perkiraan level S tanpa Iduladha)
    R          = Yhat_S / Normal_S                (pengali efek Iduladha)
    Dasar_m    = Yhat_m            untuk m != S
               = Yhat_S / R        untuk m  = S   (efek Iduladha dilepas)
    w_m        = porsi hari jendela Iduladha (H-7 s.d. H+3) yang jatuh di m
    Yhat_adj_m = Dasar_m x R^(w_m)
    Batas interval 95% dikalikan pengali yang sama, sehingga lebar interval
    pada skala log (yang ditentukan horizon h) tidak berubah.
    Untuk 2026 (Iduladha 27 Mei, jendela 20-30 Mei): w_Mei = 1, w_Jun = 0,
    sehingga hasilnya sama dengan menukar ramalan Mei dan Juni.

Input  : data/hasil_09/09_peramalan_jan_jun_2026.csv (hanya dibaca)
         data/hasil_generate/volume_bulanan.csv       (bulan Iduladha historis)
         data/olah/dataset_pra_proses_final.csv      (data historis untuk grafik)
Output : data/hasil_13/13_peramalan_disesuaikan_iduladha.csv
         data/hasil_13/13_bobot_jendela_iduladha.csv
         data/hasil_13/grafik/13_ramalan_disesuaikan.png
         13_ringkasan_penyesuaian_iduladha.md
=============================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import keterangan_csv as kk  # keterangan kolom pada setiap CSV hasil


# =============================================================================
# PENGATURAN
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RAMALAN_CSV = DATA_DIR / "hasil_09" / "09_peramalan_jan_jun_2026.csv"
VOLUME_CSV = DATA_DIR / "hasil_generate" / "volume_bulanan.csv"
DATASET_CSV = DATA_DIR / "olah" / "dataset_pra_proses_final.csv"

OUT = DATA_DIR / "hasil_13"
GRAFIK = OUT / "grafik"
GRAFIK.mkdir(parents=True, exist_ok=True)
HASIL_CSV = OUT / "13_peramalan_disesuaikan_iduladha.csv"
BOBOT_CSV = OUT / "13_bobot_jendela_iduladha.csv"
GRAFIK_PNG = GRAFIK / "13_ramalan_disesuaikan.png"
RINGKASAN_MD = BASE_DIR / "13_ringkasan_penyesuaian_iduladha.md"

# Tanggal Iduladha (perkiraan kalender Hijriah; tanggal resmi mengikuti
# ketetapan Kementerian Agama, perbarui tabel ini bila berbeda)
TANGGAL_IDULADHA = {
    2023: "2023-06-29",
    2024: "2024-06-17",
    2025: "2025-06-06",
    2026: "2026-05-27",
    2027: "2027-05-17",
    2028: "2028-05-05",
    2029: "2029-04-24",
    2030: "2030-04-13",
}

# Jendela permintaan Iduladha: belanja menjelang hari raya (H-7) sampai hari
# penyembelihan dan hari tasyrik (H+3)
HARI_SEBELUM = 7
HARI_SESUDAH = 3


NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
              "September", "Oktober", "November", "Desember"]


def tgl_id(t):
    return f"{t.day} {NAMA_BULAN[t.month - 1]} {t.year}"


def rp(v, d=0):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tabel_md(df, kolom, fmt):
    b = ["| " + " | ".join(kolom) + " |", "|" + "|".join(["---"] * len(kolom)) + "|"]
    for _, r in df.iterrows():
        b.append("| " + " | ".join(fmt.get(k, str)(r[k]) for k in kolom) + " |")
    return "\n".join(b)


# =============================================================================
# 1. BOBOT JENDELA IDULADHA PER BULAN
# =============================================================================

def bobot_jendela(tahun):
    """Porsi hari jendela Iduladha (H-7 s.d. H+3) yang jatuh di tiap bulan."""
    h = pd.Timestamp(TANGGAL_IDULADHA[tahun])
    hari = pd.date_range(h - pd.Timedelta(days=HARI_SEBELUM), h + pd.Timedelta(days=HARI_SESUDAH))
    porsi = hari.to_period("M").value_counts(normalize=True).sort_index()
    return h, {str(p): float(w) for p, w in porsi.items()}


# =============================================================================
# 2. PENYESUAIAN RAMALAN
# =============================================================================

def bulan_iduladha_historis():
    v = kk.baca_csv(VOLUME_CSV, parse_dates=["Periode"])
    bulan = v.loc[v["Koefisien_Musim"] > 1, "Periode"].dt.month
    return sorted(bulan.unique().tolist())


def sesuaikan(f, bulan_hist):
    f = f.copy()
    f["Bulan"] = pd.PeriodIndex(f["Periode"], freq="M").month
    f["Tahun"] = pd.PeriodIndex(f["Periode"], freq="M").year

    dasar = f["Yhat_Kg"].astype(float).copy()
    dasar_bawah = f["Batas_Bawah_95_Kg"].astype(float).copy()
    dasar_atas = f["Batas_Atas_95_Kg"].astype(float).copy()
    f["Pengali_R"] = 1.0
    f["Bobot_Iduladha"] = 0.0
    info_tahun, baris_bobot = [], []

    for tahun, idx_th in f.groupby("Tahun").groups.items():
        idx_th = list(idx_th)
        idx_s = [i for i in idx_th if f.at[i, "Bulan"] in bulan_hist]
        if not idx_s or tahun not in TANGGAL_IDULADHA:
            continue
        s = idx_s[0]                                   # bulan lonjakan pada ramalan model
        pos = f.index.get_loc(s)
        acuan = f.index[pos - 1] if pos > 0 else f.index[pos + 1]   # bulan normal terdekat
        R = float(f.at[s, "Yhat_Kg"] / f.at[acuan, "Yhat_Kg"])

        # Lepas efek Iduladha dari bulan lonjakan model
        dasar[s] = f.at[s, "Yhat_Kg"] / R
        dasar_bawah[s] = f.at[s, "Batas_Bawah_95_Kg"] / R
        dasar_atas[s] = f.at[s, "Batas_Atas_95_Kg"] / R

        tgl, bobot = bobot_jendela(tahun)
        di_luar = []
        for per, w in bobot.items():
            cocok = f.index[f["Periode"] == per]
            baris_bobot.append({"Tahun": tahun, "Tanggal_Iduladha": tgl.date(), "Periode": per,
                                "Bobot": w, "Dalam_Horizon": "Ya" if len(cocok) else "Tidak"})
            if len(cocok):
                f.at[cocok[0], "Bobot_Iduladha"] = w
                f.at[cocok[0], "Pengali_R"] = R ** w
            else:
                di_luar.append((per, w))
        info_tahun.append({"Tahun": tahun, "Tanggal": tgl, "Bulan_Model": f.at[s, "Periode"],
                           "Bulan_Acuan": f.at[acuan, "Periode"], "R": R, "Di_Luar": di_luar})

    f["Dasar_Kg"] = dasar
    f["Yhat_Disesuaikan_Kg"] = dasar * f["Pengali_R"]
    f["Batas_Bawah_95_Disesuaikan_Kg"] = dasar_bawah * f["Pengali_R"]
    f["Batas_Atas_95_Disesuaikan_Kg"] = dasar_atas * f["Pengali_R"]
    f["Selisih_vs_Model_Kg"] = f["Yhat_Disesuaikan_Kg"] - f["Yhat_Kg"]

    normal = f.loc[f["Bobot_Iduladha"] == 0, "Yhat_Disesuaikan_Kg"].mean()
    f["Indeks_vs_Bulan_Normal_Disesuaikan"] = f["Yhat_Disesuaikan_Kg"] / normal
    f["Faktor_Batas_Atas"] = f["Batas_Atas_95_Disesuaikan_Kg"] / f["Yhat_Disesuaikan_Kg"]
    return f, info_tahun, pd.DataFrame(baris_bobot), normal


# =============================================================================
# 3. GRAFIK
# =============================================================================

def grafik(f, info_tahun):
    d = kk.baca_csv(DATASET_CSV, parse_dates=["Periode"]).set_index("Periode")
    hist = d["Total_Kuantitas_Kg"].iloc[-12:]
    # Titik bulanan digambar di pertengahan bulan agar posisi tanggal Iduladha terbaca benar
    tengah = pd.Timedelta(days=14)
    t = pd.PeriodIndex(f["Periode"], freq="M").to_timestamp() + tengah

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hist.index + tengah, hist.values, color="black", lw=1.5, marker="o", ms=3,
            label="Aktual 2025")
    ax.plot(t, f["Yhat_Kg"], color="gray", ls="--", marker="o", ms=3,
            label="Ramalan model (puncak di Juni)")
    ax.fill_between(t, f["Batas_Bawah_95_Disesuaikan_Kg"], f["Batas_Atas_95_Disesuaikan_Kg"],
                    color="tab:blue", alpha=0.18, label="Interval 95% disesuaikan")
    ax.plot(t, f["Yhat_Disesuaikan_Kg"], color="tab:blue", marker="o", ms=4,
            label="Ramalan disesuaikan kalender Iduladha")
    for it in info_tahun:
        ax.axvline(it["Tanggal"], color="tab:red", lw=1)
        ax.text(it["Tanggal"], ax.get_ylim()[1] * 0.97, f"Iduladha {it['Tanggal']:%d-%m-%Y} ",
                color="tab:red", fontsize=8, va="top", ha="right")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: rp(x)))
    ax.set_ylabel("Permintaan (kg)")
    ax.set_title("Ramalan Jan–Jun 2026 Kabupaten Malang: penyesuaian kalender Iduladha")
    ax.legend(fontsize=8, loc="center left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(GRAFIK_PNG, dpi=150)
    plt.close(fig)


# =============================================================================
# 4. RINGKASAN
# =============================================================================

def tulis(f, info_tahun, df_bobot, normal, bulan_hist):
    f0 = lambda x: rp(x)
    L = ["# Ringkasan Script 13: Penyesuaian Kalender Iduladha\n",
         "Dibuat otomatis oleh `13_penyesuaian_iduladha.py`. Model, parameter, dan hasil script "
         "03–12 **tidak diubah**; script ini hanya menyesuaikan ramalan script 09 "
         "(*post-processing*).\n",
         "## Masalah\n",
         f"Pada data 2023–2025 Iduladha selalu jatuh di bulan "
         f"{', '.join(NAMA_BULAN[b - 1] for b in bulan_hist)}, sehingga SARIMA musiman "
         "(periode tetap 12 bulan) meramal lonjakan di bulan yang sama. Iduladha maju ±11 hari per "
         "tahun, sehingga lonjakan nyata bergeser.\n",
         "## Metode\n",
         "- Asumsi: lonjakan pada bulan Iduladha historis disebabkan oleh Iduladha, bukan oleh bulan "
         "kalendernya (berbasis teori; data 2023–2025 tidak dapat membedakan keduanya).",
         f"- Jendela permintaan Iduladha: H−{HARI_SEBELUM} sampai H+{HARI_SESUDAH} (belanja menjelang "
         "hari raya sampai hari penyembelihan dan tasyrik). Bobot bulan = porsi hari jendela di bulan tersebut.",
         "- Pengali efek Iduladha R = Ŷ bulan lonjakan model ÷ Ŷ bulan sebelumnya.",
         "- Ŷ disesuaikan = Ŷ dasar × R^bobot; bulan lonjakan model dilepas efeknya (Ŷ ÷ R).",
         "- Batas interval 95% dikalikan pengali yang sama, sehingga lebar interval pada skala log "
         "(ditentukan horizon h) tetap.\n",
         "## Perhitungan\n"]
    for it in info_tahun:
        L.append(f"- Iduladha {it['Tahun']}: **{tgl_id(it['Tanggal'])}**. Lonjakan model di "
                 f"{it['Bulan_Model']}, acuan bulan normal {it['Bulan_Acuan']}: "
                 f"R = {rp(f.loc[f['Periode'] == it['Bulan_Model'], 'Yhat_Kg'].iloc[0])} ÷ "
                 f"{rp(f.loc[f['Periode'] == it['Bulan_Acuan'], 'Yhat_Kg'].iloc[0])} = **{rp(it['R'], 3)}**.")
        for per, w in it["Di_Luar"]:
            L.append(f"  - Bobot {rp(w, 2)} jatuh di {per}, di luar horizon ramalan (tidak ditampilkan).")
    L.append("")
    L.append(tabel_md(df_bobot, ["Tahun", "Tanggal_Iduladha", "Periode", "Bobot", "Dalam_Horizon"],
                      {"Bobot": lambda x: rp(x, 2)}))
    L += ["", "## Hasil Jan–Jun 2026 (seluruh Kabupaten Malang)\n",
          tabel_md(f, ["Periode", "Yhat_Kg", "Bobot_Iduladha", "Yhat_Disesuaikan_Kg",
                       "Batas_Bawah_95_Disesuaikan_Kg", "Batas_Atas_95_Disesuaikan_Kg"],
                   {"Yhat_Kg": f0, "Yhat_Disesuaikan_Kg": f0, "Batas_Bawah_95_Disesuaikan_Kg": f0,
                    "Batas_Atas_95_Disesuaikan_Kg": f0, "Bobot_Iduladha": lambda x: rp(x, 2)}),
          "",
          f"Grafik: `{GRAFIK_PNG.relative_to(BASE_DIR).as_posix()}`.\n"]

    pk = f.loc[f["Yhat_Disesuaikan_Kg"].idxmax()]
    L += ["## Indeks untuk UMKM (disesuaikan)\n",
          tabel_md(f, ["Periode", "Indeks_vs_Bulan_Normal_Disesuaikan", "Faktor_Batas_Atas"],
                   {"Indeks_vs_Bulan_Normal_Disesuaikan": lambda x: rp(x, 2),
                    "Faktor_Batas_Atas": lambda x: rp(x, 2)}),
          "",
          f"Rata-rata bulan normal (disesuaikan): {rp(normal)} kg.\n",
          "## Implikasi\n",
          f"- Puncak permintaan 2026 berada di **{pk['Periode']}**: Ŷ {rp(pk['Yhat_Disesuaikan_Kg'])} kg, "
          f"batas atas 95% {rp(pk['Batas_Atas_95_Disesuaikan_Kg'])} kg (acuan kapasitas wilayah).",
          "- Bulan yang semula diramal sebagai puncak kembali ke level bulan normal.",
          "- Gunakan tabel ini untuk perencanaan; ramalan asli script 09 tetap dilaporkan sebagai "
          "hasil model.\n",
          "## Keterbatasan\n",
          "- Penyesuaian ini bukan bagian dari estimasi model statistik; besar lonjakan R diambil "
          "dari ramalan model dan diasumsikan sama walaupun bulannya bergeser.",
          "- Tanggal Iduladha adalah perkiraan; perbarui `TANGGAL_IDULADHA` sesuai ketetapan resmi.",
          "- Data historis sintetis menempatkan seluruh efek Iduladha di bulan Juni, sehingga "
          "penyesuaian tidak dapat divalidasi dengan data 2023–2025."]
    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    print("=" * 75)
    print("PENYESUAIAN KALENDER IDULADHA (POST-PROCESSING RAMALAN SCRIPT 09)")
    print("=" * 75)
    f = kk.baca_csv(RAMALAN_CSV)
    bulan_hist = bulan_iduladha_historis()
    print(f"Bulan Iduladha pada data historis: {bulan_hist}")

    f, info_tahun, df_bobot, normal = sesuaikan(f, bulan_hist)
    for it in info_tahun:
        print(f"Iduladha {it['Tahun']}: {it['Tanggal']:%d %b %Y} | lonjakan model {it['Bulan_Model']} | "
              f"acuan {it['Bulan_Acuan']} | R = {it['R']:.4f}")
    print(df_bobot.to_string(index=False))

    kolom = ["h", "Periode", "Yhat_Kg", "Bobot_Iduladha", "Pengali_R", "Dasar_Kg",
             "Yhat_Disesuaikan_Kg", "Batas_Bawah_95_Disesuaikan_Kg", "Batas_Atas_95_Disesuaikan_Kg",
             "Selisih_vs_Model_Kg", "Indeks_vs_Bulan_Normal_Disesuaikan", "Faktor_Batas_Atas"]
    kk.simpan_csv(f[kolom], HASIL_CSV, index=False)
    kk.simpan_csv(df_bobot, BOBOT_CSV, index=False)
    print()
    print(f[["Periode", "Yhat_Kg", "Bobot_Iduladha", "Yhat_Disesuaikan_Kg",
             "Batas_Bawah_95_Disesuaikan_Kg", "Batas_Atas_95_Disesuaikan_Kg"]].to_string(
        index=False, float_format=lambda x: f"{x:,.2f}"))

    grafik(f, info_tahun)
    tulis(f, info_tahun, df_bobot, normal, bulan_hist)
    print(f"\nCSV     : {HASIL_CSV}\nBobot   : {BOBOT_CSV}\nGrafik  : {GRAFIK_PNG}\nRingkasan: {RINGKASAN_MD}")
    print("PENYESUAIAN IDULADHA SELESAI.")


if __name__ == "__main__":
    main()
