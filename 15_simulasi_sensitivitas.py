"""
=============================================================================
PROGRAM SIMULASI BANYAK SEED DAN ANALISIS SENSITIVITAS ASUMSI DATA
File: 15_simulasi_sensitivitas.py

Hasil utama penelitian berasal dari SATU realisasi data sintetis (seed 42).
Script ini mengulang pembangkitan data dengan banyak seed dan beberapa
variasi asumsi, lalu mengukur akurasi peramalan multilangkah 9 bulan untuk:
- SARIMA final (spesifikasi tetap (1,0,0)x(1,1,0,12) pada log),
- seasonal naive dan Holt-Winters (pembanding terbaik non-SARIMA, script 14),
- ORAKEL: nilai harapan proses pembangkit (mu x faktor tren x faktor musim),
  yaitu ramalan terbaik yang mungkin; selisihnya dengan aktual hanya berasal
  dari keacakan buatan (variasi seragam +-k dan white noise). MAPE orakel =
  batas bawah galat yang dapat dicapai model mana pun pada data ini.

Agar tidak tumpang tindih:
- pembangkitan data memakai fungsi script 03 (dimuat, bukan disalin), dan
  hanya mengganti seed serta parameter k, sigma, S yang diuji;
- peramalan dan metrik memakai pembanding.py (fungsi yang sama dengan script
  14, terverifikasi mereproduksi output 08);
- tidak menulis ke data/hasil_generate maupun hasil script 04-13.

Pemeriksaan: skenario dasar dengan seed 42 harus mereproduksi
Volume_Akhir_Kg pada data/hasil_generate/volume_bulanan.csv.

Output : data/hasil_15/*.csv, data/hasil_15/grafik/15_boxplot_mape_simulasi.png,
         15_ringkasan_simulasi.md
Opsi   : --grafik-saja  -> hanya menggambar ulang grafik dari 15_hasil_per_seed.csv
                           (tanpa menjalankan ulang simulasi)
=============================================================================
"""

import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import keterangan_csv as kk
import pembanding as pb

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "data" / "hasil_15"
OUT.mkdir(parents=True, exist_ok=True)
GRAFIK = OUT / "grafik"
GRAFIK.mkdir(parents=True, exist_ok=True)
GRAFIK_PNG = GRAFIK / "15_boxplot_mape_simulasi.png"
RINGKASAN_MD = BASE_DIR / "15_ringkasan_simulasi.md"
VOLUME_CSV = BASE_DIR / "data" / "hasil_generate" / "volume_bulanan.csv"

S03 = pb.muat_skrip("03_generate_data.py")
N_LATIH = 27                       # sama dengan pembagian 75:25 script 06
N_SEED_DASAR = 100
N_SEED_SENSITIVITAS = 50

# (nama, k toleransi, sigma noise, pengali koefisien musiman S)
SKENARIO = [
    ("Dasar (k 10%, noise 5%, S 2,717)", S03.K_TOLERANSI, S03.SIGMA_NOISE, 1.0),
    ("k = 5%", 0.05, S03.SIGMA_NOISE, 1.0),
    ("k = 15%", 0.15, S03.SIGMA_NOISE, 1.0),
    ("Noise = 3%", S03.K_TOLERANSI, 0.03, 1.0),
    ("Noise = 10%", S03.K_TOLERANSI, 0.10, 1.0),
    ("S x 0,8", S03.K_TOLERANSI, S03.SIGMA_NOISE, 0.8),
    ("S x 1,2", S03.K_TOLERANSI, S03.SIGMA_NOISE, 1.2),
]

MODEL = {
    pb.LABEL_SARIMA: pb.ramal_sarima_final,
    pb.LABEL_NAIVE: pb.ramal_seasonal_naive,
    pb.LABEL_HW: pb.ramal_holt_winters,
}


# =============================================================================
# PEMBANGKITAN DATA (urutan langkah sama dengan main() script 03)
# =============================================================================

_HORIZON = S03.buat_time_horizon(S03.TAHUN_DATA)
_BPS = S03.lengkapi_komponen_kosong({th: S03.baca_bps_wilayah(th, S03.WILAYAH) for th in S03.TAHUN_DATA})
_BASELINE = S03.hitung_baseline(_BPS)
_GRADIEN = S03.hitung_gradien_per_tahun(S03.TAHUN_DATA)
_S_DASAR = S03.hitung_koefisien_musiman(S03.PEMOTONGAN_MEI_2024, S03.PEMOTONGAN_JUNI_2024)
_IDX_IDULADHA = S03.tentukan_indeks_iduladha(_HORIZON)


def bangkitkan(seed, k, sigma, pengali_s):
    """Volume bulanan akhir + orakel untuk satu seed dan satu set asumsi."""
    S03.rng = np.random.default_rng(seed)
    S03.K_TOLERANSI = k
    vol = S03.buat_volume_bulanan(_HORIZON, _BASELINE)
    vol = S03.injeksi_tren(vol, _GRADIEN)
    vol = S03.sisipkan_musiman(vol, _S_DASAR * pengali_s, _IDX_IDULADHA)
    vol = S03.tambah_white_noise(vol, sigma)
    vol = vol.set_index(pd.DatetimeIndex(vol["Periode"], freq="MS"))
    orakel = vol["Mu_Lokal"] * vol["Faktor_Tren"] * vol["Koefisien_Musim"]
    return vol["Volume_Akhir_Kg"].astype(float), orakel.astype(float)


def cek_reproduksi():
    y, _ = bangkitkan(S03.SEED, S03.K_TOLERANSI, S03.SIGMA_NOISE, 1.0)
    ref = kk.baca_csv(VOLUME_CSV)["Volume_Akhir_Kg"].astype(float).values
    selisih = float(np.max(np.abs(y.values - ref)))
    if selisih > 0.011:
        raise RuntimeError(f"Seed {S03.SEED} tidak mereproduksi volume_bulanan.csv (selisih {selisih} kg)")
    return selisih


# =============================================================================
# SIMULASI
# =============================================================================

def simulasi():
    baris = []
    for nama, k, sigma, f_s in SKENARIO:
        n_seed = N_SEED_DASAR if nama.startswith("Dasar") else N_SEED_SENSITIVITAS
        t0 = time.time()
        for seed in range(1, n_seed + 1):
            y, orakel = bangkitkan(seed, k, sigma, f_s)
            aktual = y.iloc[N_LATIH:].values
            hasil = {"Skenario": nama, "k": k, "Sigma_Noise": sigma, "Koefisien_S": _S_DASAR * f_s, "Seed": seed,
                     "MAPE_Orakel_%": pb.hitung_metrik(aktual, orakel.iloc[N_LATIH:].values)["MAPE_%"]}
            for label, fungsi in MODEL.items():
                try:
                    pred = pb.prediksi_multilangkah(y, N_LATIH, fungsi)
                    hasil[f"MAPE_{label}_%"] = pb.hitung_metrik(aktual, pred)["MAPE_%"]
                except Exception:
                    hasil[f"MAPE_{label}_%"] = np.nan
            baris.append(hasil)
        print(f"- {nama:<34} {n_seed} seed  ({time.time() - t0:,.0f} detik)")
    return pd.DataFrame(baris)


def rangkum(df):
    s, n, h = (f"MAPE_{pb.LABEL_SARIMA}_%", f"MAPE_{pb.LABEL_NAIVE}_%", f"MAPE_{pb.LABEL_HW}_%")
    baris = []
    for nama, isi in df.groupby("Skenario", sort=False):
        r = {"Skenario": nama, "Jumlah_Seed": len(isi)}
        for kol, label in ((s, "SARIMA"), (h, "HoltWinters"), (n, "Naive"), ("MAPE_Orakel_%", "Orakel")):
            v = isi[kol].dropna()
            r.update({f"{label}_Median_%": v.median(), f"{label}_P5_%": v.quantile(0.05), f"{label}_P95_%": v.quantile(0.95)})
        r["Persen_SARIMA_Lebih_Baik_dari_Naive"] = float((isi[s] < isi[n]).mean() * 100)
        r["Persen_SARIMA_Lebih_Baik_dari_HoltWinters"] = float((isi[s] < isi[h]).mean() * 100)
        r["Persen_SARIMA_Di_Bawah_Target_15%"] = float((isi[s] < 15).mean() * 100)
        r["Median_Selisih_SARIMA_minus_Orakel_poin"] = float((isi[s] - isi["MAPE_Orakel_%"]).median())
        r["Seed_SARIMA_Gagal"] = int(isi[s].isna().sum())
        baris.append(r)
    return pd.DataFrame(baris)


def grafik(df, seed42):
    """(a) sebaran MAPE skenario dasar per model; (b) sebaran MAPE SARIMA final per skenario."""
    target, ket_s = 15, "MAPE_%s_%%"
    dasar = df[df["Skenario"].str.startswith("Dasar")]
    model = [(ket_s % pb.LABEL_SARIMA, "SARIMA\nfinal"), (ket_s % pb.LABEL_HW, "Holt-\nWinters"),
             (ket_s % pb.LABEL_NAIVE, "Seasonal\nnaive"), ("MAPE_Orakel_%", "Orakel")]
    skenario = list(dict.fromkeys(df["Skenario"]))
    label_sk = ["Dasar" if s.startswith("Dasar") else s.replace("k = ", "Variasi ±").replace("Noise = ", "Noise ")
                .replace("S x ", "S × ") for s in skenario]
    gaya = dict(showfliers=True, widths=0.55, patch_artist=True, medianprops=dict(color="black", lw=1.5),
                flierprops=dict(marker="o", ms=3, mfc="none", mec="gray"))

    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [4, 7]}, sharey=True)
    bx = a.boxplot([dasar[k].dropna() for k, _ in model], tick_labels=[l for _, l in model], **gaya)
    for kotak, warna in zip(bx["boxes"], ["tab:blue", "tab:orange", "tab:gray", "tab:green"]):
        kotak.set(facecolor=warna, alpha=0.35)
    a.plot(1, seed42, marker="*", color="tab:red", ms=11, ls="none", label=f"Seed 42 (data penelitian)")
    a.set_title(f"(a) Skenario dasar, {len(dasar)} replikasi", fontsize=10)
    a.set_ylabel("MAPE multilangkah 9 bulan (%)")
    a.legend(fontsize=8, loc="upper right")

    bx = b.boxplot([df.loc[df["Skenario"] == s, ket_s % pb.LABEL_SARIMA].dropna() for s in skenario],
                   tick_labels=label_sk, **gaya)
    for kotak in bx["boxes"]:
        kotak.set(facecolor="tab:blue", alpha=0.35)
    b.set_title("(b) SARIMA final per skenario sensitivitas", fontsize=10)
    b.tick_params(axis="x", labelsize=8)

    for ax in (a, b):
        ax.axhline(target, color="tab:red", ls="--", lw=1)
        ax.grid(axis="y", alpha=0.3)
    b.text(len(skenario) + 0.45, target, "Target 15%", color="tab:red", fontsize=8, va="bottom", ha="right")
    fig.tight_layout()
    fig.savefig(GRAFIK_PNG, dpi=150)
    plt.close(fig)


def tulis_ringkasan(rk, selisih_cek, seed42):
    rp = lambda v, d=2: f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    L = ["# Ringkasan Script 15: Simulasi Banyak Seed dan Analisis Sensitivitas\n",
         "Dibuat otomatis oleh `15_simulasi_sensitivitas.py`. Hasil script 03–14 tidak diubah.\n",
         "## Desain",
         f"- Data dibangkitkan ulang dengan fungsi script 03 (seed 1–{N_SEED_DASAR} untuk skenario dasar, "
         f"1–{N_SEED_SENSITIVITAS} untuk skenario sensitivitas); latih {N_LATIH} bulan, uji 9 bulan multilangkah.",
         f"- Pemeriksaan: skenario dasar seed {S03.SEED} mereproduksi volume_bulanan.csv (selisih maks {selisih_cek:.2f} kg); "
         f"MAPE SARIMA seed 42 = {rp(seed42)}% (sama dengan Tabel 5 naskah).",
         "- Orakel = nilai harapan proses pembangkit (μ × faktor tren × faktor musim): batas bawah galat yang dapat dicapai.\n",
         "## Hasil per skenario (MAPE multilangkah 9 bulan, median [persentil 5–95])",
         "| Skenario | SARIMA | Holt-Winters | Seasonal naive | Orakel | SARIMA < naive | SARIMA < HW | SARIMA < 15% |",
         "|---|---|---|---|---|---|---|---|"]
    for _, r in rk.iterrows():
        sel = lambda p: f"{rp(r[p + '_Median_%'])} [{rp(r[p + '_P5_%'])}–{rp(r[p + '_P95_%'])}]"
        L.append(f"| {r['Skenario']} | {sel('SARIMA')} | {sel('HoltWinters')} | {sel('Naive')} | {sel('Orakel')} | "
                 f"{rp(r['Persen_SARIMA_Lebih_Baik_dari_Naive'], 0)}% | {rp(r['Persen_SARIMA_Lebih_Baik_dari_HoltWinters'], 0)}% | "
                 f"{rp(r['Persen_SARIMA_Di_Bawah_Target_15%'], 0)}% |")
    L += ["", "## Catatan skenario S",
          "- Skenario S × 0,8 dan S × 1,2 memberi MAPE yang (hampir) sama. Ini konsekuensi desain data, bukan galat: "
          "Iduladha selalu jatuh di bulan yang sama dan semua komponen bersifat perkalian, sehingga pada skala log "
          "pengali S hanya menambah konstanta di bulan Iduladha yang dihapus oleh pembedaan musiman; rasio seasonal "
          "naive dan orakel juga tidak berubah. Besar lonjakan S baru berpengaruh bila bulan Iduladha bergeser.",
          "", "## Cara membaca",
          "- Kolom persen = porsi seed tempat SARIMA lebih akurat dari pembanding / memenuhi target MAPE < 15%.",
          "- Bila MAPE SARIMA dekat dengan MAPE orakel, akurasi model terutama dibatasi oleh keacakan buatan pada data; "
          "akurasi tersebut menggambarkan kemampuan model menangkap pola pembangkit, bukan akurasi pada data permintaan riil."]
    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def mape_seed42(df):
    """MAPE SARIMA seed 42 skenario dasar (sama dengan hasil utama naskah, Tabel 5)."""
    dasar = df[df["Skenario"].str.startswith("Dasar") & (df["Seed"] == S03.SEED)]
    return float(dasar[f"MAPE_{pb.LABEL_SARIMA}_%"].iloc[0])


def main():
    if "--grafik-saja" in sys.argv:
        df = kk.baca_csv(OUT / "15_hasil_per_seed.csv")
        grafik(df, mape_seed42(df))
        print(f"Grafik: {GRAFIK_PNG}")
        return
    print("=" * 75); print("SCRIPT 15: SIMULASI BANYAK SEED DAN SENSITIVITAS"); print("=" * 75)
    selisih = cek_reproduksi()
    print(f"Reproduksi seed {S03.SEED}: selisih maks {selisih:.2f} kg terhadap volume_bulanan.csv")
    df = simulasi()
    y42, _ = bangkitkan(S03.SEED, S03.K_TOLERANSI, S03.SIGMA_NOISE, 1.0)
    seed42 = pb.hitung_metrik(y42.iloc[N_LATIH:].values,
                              pb.prediksi_multilangkah(y42, N_LATIH, pb.ramal_sarima_final))["MAPE_%"]
    rk = rangkum(df)
    kk.simpan_csv(df, OUT / "15_hasil_per_seed.csv", index=False)
    kk.simpan_csv(rk, OUT / "15_ringkasan_skenario.csv", index=False)
    tulis_ringkasan(rk, selisih, seed42)
    grafik(df, seed42)
    print(rk.round(2).to_string(index=False))
    print(f"MAPE SARIMA seed 42 (volume akhir): {seed42:.3f}%")
    print(f"Grafik   : {GRAFIK_PNG}")
    print(f"Ringkasan: {RINGKASAN_MD}")


if __name__ == "__main__":
    main()
