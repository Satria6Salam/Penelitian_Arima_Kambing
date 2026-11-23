"""
=============================================================================
PROGRAM VALIDASI DI DALAM DATA LATIH (PEMILIHAN MODEL TANPA DATA UJI)
File: 17_validasi_data_latih.py

Script 07 menilai model shortlist dengan rolling origin pada data UJI
(Apr-Des 2025). Agar pemilihan model final tidak memakai data uji, script ini
mengulang aturan pemilihan dengan rolling origin di DALAM data latih:
latih awal Jan 2023 - Sep 2024 (21 bulan), ramal 1 bulan, tambah aktual,
latih ulang penuh; 6 putaran (target Okt 2024 - Mar 2025).

Aturan pemilihan (sama dengan script 07, tetapi MAPE dari validasi data latih):
  1. lulus Ljung-Box dan Shapiro-Wilk (07_diagnostik_residual.csv) DAN
     MAPE validasi lebih rendah dari seasonal naive;
  2. tidak membutuhkan nilai variabel eksogen pada bulan yang diramal;
  3. MAPE validasi terendah di antara model yang lolos aturan 1 dan 2.

Agar tidak tumpang tindih:
- shortlist, diagnostik, dan fungsi estimasi diambil dari script 06-07
  (estimasi_model.fit_terbaik, hitung_metrik script 07);
- data uji TIDAK dibaca sama sekali;
- hasil script 03-16 tidak diubah.

Bagian kedua mencatat ANGKA PENDUKUNG EVALUASI yang dikutip di artikel dan
diturunkan dari output program (tidak ada model baru):
  - selang bootstrap 95% MAPE multilangkah data uji (output 08, seed 42);
  - porsi Juni 2025 terhadap variasi total data uji (dasar tafsiran R²);
  - rata-rata pertumbuhan tahunan aktual Apr-Des 2024 dan rata-rata pertumbuhan
    yang diramal model untuk Apr-Des 2025 (penjelas bias ramalan terlalu rendah);
  - selisih maksimum MAPE skenario S x 0,8 dan S x 1,2 per seed (output 15).

Input  : data/hasil_06/06_training_set.csv, data/hasil_07/07_shortlist.csv,
         data/hasil_07/07_diagnostik_residual.csv, data/hasil_08/08_peramalan_testing.csv,
         data/hasil_15/15_hasil_per_seed.csv
Output : data/hasil_17/17_validasi_prediksi.csv, 17_validasi_metrik.csv,
         17_angka_pendukung_evaluasi.csv, 17_ringkasan_validasi_data_latih.md
=============================================================================
"""

import ast
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import keterangan_csv as kk
import pembanding as pb

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "data" / "hasil_17"
OUT.mkdir(parents=True, exist_ok=True)
PREDIKSI_CSV = OUT / "17_validasi_prediksi.csv"
METRIK_CSV = OUT / "17_validasi_metrik.csv"
PENDUKUNG_CSV = OUT / "17_angka_pendukung_evaluasi.csv"
RINGKASAN_MD = BASE_DIR / "17_ringkasan_validasi_data_latih.md"
PERAMALAN_08_CSV = BASE_DIR / "data" / "hasil_08" / "08_peramalan_testing.csv"
SEED_15_CSV = BASE_DIR / "data" / "hasil_15" / "15_hasil_per_seed.csv"
N_BOOTSTRAP = 10_000
SEED_BOOTSTRAP = 42

S07 = pb.muat_skrip("07_validasi_diagnostik_evaluasi.py")
em = pb.em
M = 12
N_LATIH_AWAL = 21          # Jan 2023 - Sep 2024; target validasi Okt 2024 - Mar 2025 (6 putaran)
LABEL_NAIVE = pb.LABEL_NAIVE


def rp(v, d=2):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def muat():
    train = kk.baca_csv(S07.TRAIN_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    shortlist = kk.baca_csv(S07.SHORTLIST_CSV)
    diag = kk.baca_csv(S07.DIAGNOSTIK_CSV).set_index("Label")
    return train, shortlist, diag


def rolling_latih(train, shortlist):
    skala = em.skala_data(train)
    y_kg = train[em.TARGET_COL].astype(float)
    y_s = skala[em.TARGET_COL]
    baris = []
    for _, s in shortlist.iterrows():
        order, sorder = ast.literal_eval(s["Order"]), ast.literal_eval(s["Seasonal_Order"])
        eks = [] if s["Eksogen"] == "-" else [e.strip() for e in s["Eksogen"].split(",")]
        for i, batas in enumerate(range(N_LATIH_AWAL, len(train)), start=1):
            x_latih = skala[eks].iloc[:batas].astype(float) if eks else None
            x_next = skala[eks].iloc[batas:batas + 1].astype(float) if eks else None
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res, info = em.fit_terbaik(y_s.iloc[:batas], x_latih, order, sorder)
            pred = float(em.ke_kg(float(res.get_forecast(steps=1, exog=x_next).predicted_mean.iloc[0])))
            aktual = float(y_kg.iloc[batas])
            baris.append({"Label": s["Label"], "Nama_Model": s["Nama_Model"], "Putaran": i,
                          "Panjang_Data_Latih": batas, "Periode_Target": y_kg.index[batas].strftime("%Y-%m"),
                          "Aktual": aktual, "Prediksi": pred, "Error": aktual - pred,
                          "APE_%": abs(aktual - pred) / aktual * 100,
                          "Optimizer": info["Optimizer_Terpilih"], "Konvergen": info["Konvergen"]})
        print(f"- {s['Label']:<22} selesai")
    for i, batas in enumerate(range(N_LATIH_AWAL, len(train)), start=1):
        aktual, pred = float(y_kg.iloc[batas]), float(y_kg.iloc[batas - M])
        baris.append({"Label": LABEL_NAIVE, "Nama_Model": "y[t-12]", "Putaran": i, "Panjang_Data_Latih": batas,
                      "Periode_Target": y_kg.index[batas].strftime("%Y-%m"), "Aktual": aktual, "Prediksi": pred,
                      "Error": aktual - pred, "APE_%": abs(aktual - pred) / aktual * 100,
                      "Optimizer": "-", "Konvergen": None})
    return pd.DataFrame(baris)


def pilih_model(df, shortlist, diag):
    eksogen = dict(zip(shortlist["Label"], shortlist["Eksogen"]))
    baris = []
    for label, isi in df.groupby("Label", sort=False):
        m = S07.hitung_metrik(isi["Aktual"], isi["Prediksi"])
        baris.append({"Label": label, "Nama_Model": isi["Nama_Model"].iloc[0], "Jumlah_Putaran": len(isi),
                      "MAPE_%": m["MAPE_%"], "RMSE": m["RMSE"], "MAE": m["MAE"]})
    met = pd.DataFrame(baris)
    naive = met.loc[met["Label"] == LABEL_NAIVE, "MAPE_%"].iloc[0]
    met["Ljung_Box"] = met["Label"].map(lambda l: diag.loc[l, "Ljung_Box"] if l in diag.index else "-")
    met["Shapiro_Wilk"] = met["Label"].map(lambda l: diag.loc[l, "Shapiro_Wilk"] if l in diag.index else "-")
    met["Lebih_baik_dari_naive"] = ["-" if l == LABEL_NAIVE else ("Ya" if v < naive else "Tidak")
                                    for l, v in zip(met["Label"], met["MAPE_%"])]
    met["Aturan_1"] = ["-" if l == LABEL_NAIVE else
                       ("Lolos" if (lb == "Lulus" and sw == "Lulus" and nb == "Ya") else "Gagal")
                       for l, lb, sw, nb in zip(met["Label"], met["Ljung_Box"], met["Shapiro_Wilk"],
                                                met["Lebih_baik_dari_naive"])]
    met["Butuh_Eksogen_Masa_Depan"] = met["Label"].map(
        lambda l: "-" if l == LABEL_NAIVE else ("Tidak" if eksogen.get(l, "-") == "-" else "Ya"))
    lolos = met[(met["Aturan_1"] == "Lolos") & (met["Butuh_Eksogen_Masa_Depan"] == "Tidak")]
    final = lolos.loc[lolos["MAPE_%"].idxmin(), "Label"] if not lolos.empty else None
    met["Model_Final"] = ["Ya" if l == final else "Tidak" for l in met["Label"]]
    return met, final


def angka_pendukung(train):
    """Angka turunan output program yang dikutip artikel (deterministik; bootstrap memakai seed tetap)."""
    test = kk.baca_csv(S07.TEST_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    y = pd.concat([train, test])[em.TARGET_COL].astype(float)
    p8 = kk.baca_csv(PERAMALAN_08_CSV)
    p8 = p8[p8["Label"] == pb.LABEL_SARIMA].sort_values("Horizon")
    ape = p8["APE_%"].to_numpy(float)
    rng = np.random.default_rng(SEED_BOOTSTRAP)
    boot = rng.choice(ape, size=(N_BOOTSTRAP, len(ape)), replace=True).mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])

    akt = test[em.TARGET_COL].astype(float)
    porsi_juni = float((akt.loc["2025-06-01"] - akt.mean()) ** 2 / ((akt - akt.mean()) ** 2).sum())

    ln = np.log(y)
    w = (ln - ln.shift(12)).dropna()
    tumbuh_2024 = float(w.loc["2024-04-01":"2024-12-01"].mean())
    w_ramal = np.log(p8["Prediksi_Kg"].to_numpy(float)) - ln.loc["2024-04-01":"2024-12-01"].to_numpy()
    turun = int((w_ramal < 0).sum())

    s15 = kk.baca_csv(SEED_15_CSV)
    kol = f"MAPE_{pb.LABEL_SARIMA}_%"
    a = s15[s15["Skenario"] == "S x 0,8"].set_index("Seed")[kol]
    b = s15[s15["Skenario"] == "S x 1,2"].set_index("Seed")[kol]
    selisih_s = float((a - b).abs().max())

    return pd.DataFrame([
        {"Besaran": "MAPE multilangkah data uji (%)", "Nilai": float(ape.mean()),
         "Cara_Hitung": "Rata-rata APE_% SARIMA D=1 di 08_peramalan_testing.csv"},
        {"Besaran": "Bootstrap 95% MAPE uji - batas bawah (%)", "Nilai": float(lo),
         "Cara_Hitung": f"Persentil 2,5 dari {N_BOOTSTRAP} rata-rata 9 APE yang diambil ulang (seed {SEED_BOOTSTRAP})"},
        {"Besaran": "Bootstrap 95% MAPE uji - batas atas (%)", "Nilai": float(hi),
         "Cara_Hitung": f"Persentil 97,5 dari {N_BOOTSTRAP} rata-rata 9 APE yang diambil ulang (seed {SEED_BOOTSTRAP})"},
        {"Besaran": "Porsi Juni 2025 terhadap variasi total data uji (%)", "Nilai": porsi_juni * 100,
         "Cara_Hitung": "(y Juni - rata-rata uji)^2 / jumlah (y - rata-rata uji)^2"},
        {"Besaran": "Rata-rata pertumbuhan tahunan aktual Apr-Des 2024 (%)", "Nilai": tumbuh_2024 * 100,
         "Cara_Hitung": "Rata-rata ln y_t - ln y_(t-12), Apr-Des 2024"},
        {"Besaran": "Bulan uji yang diramal tumbuh negatif dibanding tahun lalu", "Nilai": float(turun),
         "Cara_Hitung": "Jumlah bulan Apr-Des 2025 dengan ln ramalan - ln aktual 12 bulan sebelumnya < 0"},
        {"Besaran": "Selisih maksimum MAPE SARIMA skenario S x 0,8 vs S x 1,2 per seed (poin)", "Nilai": selisih_s,
         "Cara_Hitung": "Maks |MAPE S x 0,8 - MAPE S x 1,2| per seed di 15_hasil_per_seed.csv"},
    ])


def tulis_ringkasan(met, final, final_07, pendukung=None):
    def f2(v):
        return rp(v, 2)
    L = ["# Ringkasan Validasi di Dalam Data Latih (Script 17)", "",
         "Pemilihan model final diulang tanpa data uji: rolling origin 1 bulan di dalam data latih, "
         "latih awal Jan 2023 - Sep 2024, 6 putaran (target Okt 2024 - Mar 2025).", "",
         "| Model | MAPE validasi (%) | RMSE (kg) | Ljung-Box | Shapiro-Wilk | Lebih baik dari naive | Aturan 1 | Butuh eksogen | Model final |",
         "|---|---:|---:|---|---|---|---|---|---|"]
    for r in met.to_dict("records"):
        L.append(f"| {r['Label']}: {r['Nama_Model']} | {f2(r['MAPE_%'])} | {rp(r['RMSE'], 0)} | {r['Ljung_Box']} | "
                 f"{r['Shapiro_Wilk']} | {r['Lebih_baik_dari_naive']} | {r['Aturan_1']} | "
                 f"{r['Butuh_Eksogen_Masa_Depan']} | {r['Model_Final']} |")
    L += ["", f"**Model final (tanpa data uji): {final}.** Model final script 07 (MAPE rolling origin data uji): {final_07}.",
          "Hasil " + ("SAMA" if final == final_07 else "BERBEDA") + ": pemilihan model "
          + ("tidak bergantung pada data uji." if final == final_07 else "berubah bila data uji tidak dipakai."),
          "", "Catatan: jendela validasi Okt 2024 - Mar 2025 tidak memuat bulan Iduladha."]
    if pendukung is not None:
        L += ["", "## Angka pendukung evaluasi (dikutip di artikel)", "", "| Besaran | Nilai | Cara hitung |", "|---|---:|---|"]
        L += [f"| {r['Besaran']} | {rp(r['Nilai'], 3)} | {r['Cara_Hitung']} |" for r in pendukung.to_dict("records")]
    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    print("=" * 75); print("SCRIPT 17: VALIDASI DI DALAM DATA LATIH (PEMILIHAN MODEL TANPA DATA UJI)"); print("=" * 75)
    train, shortlist, diag = muat()
    print(f"Data latih {len(train)} bulan; latih awal {N_LATIH_AWAL} bulan; {len(train) - N_LATIH_AWAL} putaran validasi.")
    df = rolling_latih(train, shortlist)
    met, final = pilih_model(df, shortlist, diag)
    final_07 = kk.baca_csv(S07.METRIK_CSV)
    diag07 = diag.reset_index()
    layak = diag07[(diag07["Ljung_Box"] == "Lulus") & (diag07["Shapiro_Wilk"] == "Lulus")]["Label"]
    m07 = final_07[final_07["Label"].isin(layak) & final_07["Label"].isin(
        shortlist.loc[shortlist["Eksogen"] == "-", "Label"])]
    naive07 = final_07.loc[final_07["Label"] == LABEL_NAIVE, "MAPE_%"].iloc[0]
    m07 = m07[m07["MAPE_%"] < naive07]
    final_07 = m07.loc[m07["MAPE_%"].idxmin(), "Label"] if not m07.empty else None
    pendukung = angka_pendukung(train)
    kk.simpan_csv(df, PREDIKSI_CSV, index=False)
    kk.simpan_csv(met, METRIK_CSV, index=False)
    kk.simpan_csv(pendukung, PENDUKUNG_CSV, index=False)
    tulis_ringkasan(met, final, final_07, pendukung)
    print("\nAngka pendukung evaluasi:")
    print(pendukung[["Besaran", "Nilai"]].round(4).to_string(index=False))
    print(met[["Label", "MAPE_%", "RMSE", "Ljung_Box", "Shapiro_Wilk", "Aturan_1", "Butuh_Eksogen_Masa_Depan",
               "Model_Final"]].round(3).to_string(index=False))
    print(f"\nModel final tanpa data uji : {final}")
    print(f"Model final script 07      : {final_07}  -> {'SAMA' if final == final_07 else 'BERBEDA'}")
    print(f"Output: {PREDIKSI_CSV.name}, {METRIK_CSV.name}, {PENDUKUNG_CSV.name}, {RINGKASAN_MD.name}")


if __name__ == "__main__":
    main()
