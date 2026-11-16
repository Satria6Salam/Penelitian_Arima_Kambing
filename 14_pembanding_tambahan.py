"""
=============================================================================
PROGRAM PEMBANDING TAMBAHAN DAN UJI DIEBOLD-MARIANO
File: 14_pembanding_tambahan.py

Menambah pembanding untuk model final SARIMA(1,0,0)x(1,1,0,12):
Holt-Winters (tren teredam + musiman), Theta, dan SARIMA airline
(0,1,1)x(0,1,1,12), dievaluasi dengan DUA skema yang sama persis dengan
script 07 (rolling origin 1 bulan, 9 putaran) dan script 08 (multilangkah
9 bulan). Lalu uji Diebold-Mariano model final vs setiap pembanding.

Agar tidak tumpang tindih:
- prediksi SARIMA final dan seasonal naive TIDAK dihitung ulang; dibaca dari
  07_rolling_origin_prediksi.csv dan 08_peramalan_testing.csv;
- metrik memakai hitung_metrik script 07 (lewat pembanding.py);
- model final dan hasil script 06-13 tidak diubah.
Satu-satunya hitung ulang SARIMA adalah PEMERIKSAAN KONSISTENSI: fungsi
pembanding.ramal_sarima_final harus mereproduksi output 08 (fungsi yang sama
dipakai simulasi script 15).

Input  : data/hasil_06 (latih/uji), data/hasil_07, data/hasil_08
Output : data/hasil_14/*.csv, 14_ringkasan_pembanding.md
=============================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd

import keterangan_csv as kk
import pembanding as pb

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "data" / "hasil_14"
OUT.mkdir(parents=True, exist_ok=True)
RINGKASAN_MD = BASE_DIR / "14_ringkasan_pembanding.md"

S07 = pb.muat_skrip("07_validasi_diagnostik_evaluasi.py")   # path input/output script 07
S08 = pb.muat_skrip("08_forecasting_data_testing.py")       # path output script 08

HORIZON_OPERASIONAL = 6     # 6 bulan pertama data uji = horizon peramalan operasional


def rp(v, d=2):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def muat():
    train = kk.baca_csv(S07.TRAIN_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    test = kk.baca_csv(S07.TEST_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    y_all = pd.concat([train, test])[pb.em.TARGET_COL].astype(float)

    roll = kk.baca_csv(S07.ROLLING_CSV)
    roll = roll[roll["Label"].isin([pb.LABEL_SARIMA, pb.LABEL_NAIVE])]
    roll = roll.rename(columns={"Periode_Target": "Periode", "Aktual": "Aktual_Kg", "Prediksi": "Prediksi_Kg"})
    roll["Skema"] = "Rolling origin"

    ms = kk.baca_csv(S08.PERAMALAN_CSV)
    ms = ms[ms["Label"].isin([pb.LABEL_SARIMA, pb.LABEL_NAIVE])]
    ms["Skema"] = "Multilangkah"
    kolom = ["Skema", "Label", "Periode", "Aktual_Kg", "Prediksi_Kg"]
    lama = pd.concat([roll[kolom], ms[kolom]], ignore_index=True)
    lama["Sumber"] = np.where(lama["Skema"] == "Rolling origin", "07_rolling_origin_prediksi.csv",
                              "08_peramalan_testing.csv")
    return y_all, len(train), lama


def cek_konsistensi(y_all, n_latih, lama):
    """Fungsi SARIMA bersama harus mereproduksi output 08 (dasar kepercayaan script 15)."""
    pred = pb.prediksi_multilangkah(y_all, n_latih, pb.ramal_sarima_final)
    ref = lama[(lama["Skema"] == "Multilangkah") & (lama["Label"] == pb.LABEL_SARIMA)]["Prediksi_Kg"].values
    selisih = float(np.max(np.abs(pred / ref - 1)) * 100)
    if selisih > 1e-3:
        raise RuntimeError(f"pembanding.ramal_sarima_final tidak mereproduksi output 08 (selisih {selisih:.5f}%)")
    return selisih


def hitung_pembanding_baru(y_all, n_latih):
    periode = y_all.index[n_latih:].strftime("%Y-%m")
    aktual = y_all.iloc[n_latih:].values
    baris = []
    for label, (spek, fungsi) in pb.PEMBANDING_BARU.items():
        for skema, f_skema in (("Rolling origin", pb.prediksi_rolling), ("Multilangkah", pb.prediksi_multilangkah)):
            pred = f_skema(y_all, n_latih, fungsi)
            for p_, a, x in zip(periode, aktual, pred):
                baris.append({"Skema": skema, "Label": label, "Spesifikasi": spek, "Periode": p_,
                              "Aktual_Kg": a, "Prediksi_Kg": x, "APE_%": abs(a - x) / a * 100})
        print(f"- {label:<16} selesai")
    return pd.DataFrame(baris)


def metrik(semua):
    baris = []
    for (skema, label), isi in semua.groupby(["Skema", "Label"], sort=False):
        m = pb.hitung_metrik(isi["Aktual_Kg"], isi["Prediksi_Kg"])
        ops = isi.head(HORIZON_OPERASIONAL)
        baris.append({"Skema": skema, "Label": label, **m,
                      "MAPE_6_Bulan_Pertama_%": pb.hitung_metrik(ops["Aktual_Kg"], ops["Prediksi_Kg"])["MAPE_%"]
                      if skema == "Multilangkah" else np.nan})
    df = pd.DataFrame(baris)
    df["Peringkat_MAPE"] = df.groupby("Skema")["MAPE_%"].rank(method="min").astype(int)
    return df.sort_values(["Skema", "Peringkat_MAPE"]).reset_index(drop=True)


def diebold_mariano(semua):
    """Galat 1 langkah (rolling origin): asumsi uji DM terpenuhi untuk h = 1."""
    r = semua[semua["Skema"] == "Rolling origin"]
    galat = {l: (isi["Aktual_Kg"] - isi["Prediksi_Kg"]).values for l, isi in r.groupby("Label")}
    baris = []
    for lawan in [l for l in galat if l != pb.LABEL_SARIMA]:
        for loss in ("kuadrat", "absolut"):
            dm, p, dbar = pb.uji_diebold_mariano(galat[pb.LABEL_SARIMA], galat[lawan], h=1, loss=loss)
            baris.append({"Model_A": pb.LABEL_SARIMA, "Model_B": lawan, "Loss": loss, "n": len(galat[lawan]),
                          "Rata2_Selisih_Loss": dbar, "Statistik_DM_HLN": dm, "P_value": p,
                          "Kesimpulan_5%": ("Berbeda signifikan; " + ("A lebih akurat" if dbar < 0 else "B lebih akurat"))
                          if p < 0.05 else "Tidak berbeda signifikan"})
    return pd.DataFrame(baris)


def tulis_ringkasan(df_m, df_dm, selisih_cek):
    def tabel(df, kolom, fmt):
        b = ["| " + " | ".join(kolom) + " |", "|" + "|".join(["---"] * len(kolom)) + "|"]
        for _, r in df.iterrows():
            b.append("| " + " | ".join(fmt.get(k, str)(r[k]) for k in kolom) + " |")
        return "\n".join(b)
    f2 = lambda v: "-" if pd.isna(v) else rp(v, 2)
    f0 = lambda v: rp(v, 0)
    L = ["# Ringkasan Script 14: Pembanding Tambahan dan Uji Diebold-Mariano\n",
         "Dibuat otomatis oleh `14_pembanding_tambahan.py`. Model final dan hasil script 06–13 tidak diubah.\n",
         "## Desain",
         "- Pembanding baru: " + "; ".join(f"**{k}** – {v[0]}" for k, v in pb.PEMBANDING_BARU.items()) + ".",
         "- Spesifikasi pembanding ditetapkan sebelum melihat data uji (tidak dipilih dari hasil uji).",
         "- Skema sama dengan script 07 (rolling origin 1 bulan, 9 putaran) dan script 08 (multilangkah 9 bulan).",
         f"- Prediksi {pb.LABEL_SARIMA} dan {pb.LABEL_NAIVE} dibaca dari output 07/08 (tidak dihitung ulang).",
         f"- Pemeriksaan konsistensi: fungsi SARIMA bersama mereproduksi output 08 dengan selisih maks {selisih_cek:.6f}%.\n"]
    for skema in ("Rolling origin", "Multilangkah"):
        isi = df_m[df_m["Skema"] == skema]
        kol = ["Peringkat_MAPE", "Label", "MAPE_%", "RMSE", "MAE", "R2"] + (["MAPE_6_Bulan_Pertama_%"] if skema == "Multilangkah" else [])
        L += [f"## Akurasi – {skema}", tabel(isi, kol, {"MAPE_%": f2, "RMSE": f0, "MAE": f0, "R2": lambda v: rp(v, 3),
                                                         "MAPE_6_Bulan_Pertama_%": f2}), ""]
    L += ["## Uji Diebold-Mariano (galat rolling origin, h = 1, koreksi Harvey dkk., n = 9)",
          tabel(df_dm, ["Model_A", "Model_B", "Loss", "Statistik_DM_HLN", "P_value", "Kesimpulan_5%"],
                {"Statistik_DM_HLN": lambda v: rp(v, 3), "P_value": lambda v: rp(v, 4)}),
          "", "Catatan: dengan hanya 9 titik uji, daya uji DM rendah; hasil tidak signifikan tidak berarti akurasinya sama."]
    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    print("=" * 75); print("SCRIPT 14: PEMBANDING TAMBAHAN DAN UJI DIEBOLD-MARIANO"); print("=" * 75)
    y_all, n_latih, lama = muat()
    selisih = cek_konsistensi(y_all, n_latih, lama)
    print(f"Konsistensi fungsi SARIMA vs output 08: selisih maks {selisih:.6f}%")
    baru = hitung_pembanding_baru(y_all, n_latih)
    semua = pd.concat([lama.drop(columns="Sumber"), baru[["Skema", "Label", "Periode", "Aktual_Kg", "Prediksi_Kg"]]],
                      ignore_index=True)
    df_m = metrik(semua)
    df_dm = diebold_mariano(semua)
    kk.simpan_csv(baru, OUT / "14_prediksi_pembanding_baru.csv", index=False)
    kk.simpan_csv(df_m, OUT / "14_metrik_pembanding.csv", index=False)
    kk.simpan_csv(df_dm, OUT / "14_uji_diebold_mariano.csv", index=False)
    tulis_ringkasan(df_m, df_dm, selisih)
    print(df_m[["Skema", "Label", "MAPE_%", "RMSE", "R2", "MAPE_6_Bulan_Pertama_%"]].round(3).to_string(index=False))
    print(df_dm[["Model_B", "Loss", "Statistik_DM_HLN", "P_value", "Kesimpulan_5%"]].round(4).to_string(index=False))
    print(f"Ringkasan: {RINGKASAN_MD}")


if __name__ == "__main__":
    main()
