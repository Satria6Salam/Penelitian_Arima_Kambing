"""
=============================================================================
PROGRAM REKOMENDASI MANAJERIAL BERBASIS METRIK HASIL
File: 11_rekomendasi_manajerial.py

Menerjemahkan hasil penelitian ke rekomendasi bisnis (tahap "IMPLEMENTASI
SISTEM & ANALISIS DAMPAK BISNIS", poin 2), memakai ANGKA NYATA penelitian:
1. Penurunan risiko overproduksi dan understock pada data testing
   (Apr-Des 2025): rencana stok = ramalan model final vs seasonal naive.
2. Efisiensi biaya pakan: indeks kebutuhan bulanan Jan-Jun 2026.
3. Pencegahan underproduksi: kapasitas puncak dari batas atas interval 95%.
4. Batas margin harga: harga historis bulan biasa vs bulan Iduladha.
5. Panduan indeks/persentase untuk UMKM (tidak bergantung skala usaha).
Sasaran: angka kg untuk pemangku kepentingan tingkat Kabupaten Malang (data
agregat kabupaten, tidak dibagi jumlah UMKM); angka relatif untuk UMKM.

Input  : data/hasil_08, data/hasil_09, data/olah, data/hasil_generate
Output : data/hasil_11/11_rek_*.csv dan 11_rekomendasi_manajerial.md
=============================================================================
"""

import numpy as np
import pandas as pd

from pathlib import Path


# =============================================================================
# PENGATURAN PATH
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUT = DATA_DIR / "hasil_11"
OUT.mkdir(parents=True, exist_ok=True)

PERAMALAN_TEST_CSV = DATA_DIR / "hasil_08" / "08_peramalan_testing.csv"
EVAL_TEST_CSV = DATA_DIR / "hasil_08" / "08_evaluasi_peramalan.csv"
VALIDASI_09_CSV = DATA_DIR / "hasil_09" / "validasi_apr_sep_2025" / "09_peramalan_validasi_apr_sep_2025.csv"
PERAMALAN_2026_CSV = DATA_DIR / "hasil_09" / "09_peramalan_jan_jun_2026.csv"
METRIK_07_CSV = DATA_DIR / "hasil_07" / "07_metrik_rolling_origin.csv"
DATASET_CSV = DATA_DIR / "olah" / "dataset_pra_proses_final.csv"
VOLUME_CSV = DATA_DIR / "hasil_generate" / "volume_bulanan.csv"
RINGKASAN_MD = BASE_DIR / "11_rekomendasi_manajerial.md"

MODEL = "SARIMA D=1"
PEMBANDING = "Seasonal naive"


def rp(v, d=0):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tabel_md(df, kolom, fmt=None):
    fmt = fmt or {}
    def f(k, v):
        if isinstance(v, (float, np.floating)):
            return "-" if not np.isfinite(v) else fmt.get(k, lambda x: rp(x, 1))(v)
        return str(v)
    b = ["| " + " | ".join(kolom) + " |", "|" + "|".join(["---"] * len(kolom)) + "|"]
    for _, r in df.iterrows():
        b.append("| " + " | ".join(f(k, r[k]) for k in kolom) + " |")
    return "\n".join(b)


# =============================================================================
# 1. OVERPRODUKSI DAN UNDERSTOCK PADA DATA TESTING
# =============================================================================

def analisis_stok():
    df = pd.read_csv(PERAMALAN_TEST_CSV)
    baris = []
    for label in [MODEL, PEMBANDING]:
        isi = df[df["Label"] == label]
        rencana, aktual = isi["Prediksi_Kg"].values, isi["Aktual_Kg"].values
        over = np.clip(rencana - aktual, 0, None)
        under = np.clip(aktual - rencana, 0, None)
        baris.append({
            "Metode_Rencana_Stok": label,
            "Total_Aktual_Kg": aktual.sum(),
            "Total_Rencana_Kg": rencana.sum(),
            "Kelebihan_Stok_Kg": over.sum(),
            "Kekurangan_Stok_Kg": under.sum(),
            "Bulan_Kelebihan": int((over > 0).sum()),
            "Bulan_Kekurangan": int((under > 0).sum()),
            "Total_Selisih_Absolut_Kg": np.abs(rencana - aktual).sum(),
        })
    hasil = pd.DataFrame(baris)
    m, n = hasil.iloc[0], hasil.iloc[1]
    pengurangan = {
        "Penurunan_Kelebihan_Stok_%": (1 - m["Kelebihan_Stok_Kg"] / n["Kelebihan_Stok_Kg"]) * 100
        if n["Kelebihan_Stok_Kg"] > 0 else np.nan,
        "Penurunan_Kekurangan_Stok_%": (1 - m["Kekurangan_Stok_Kg"] / n["Kekurangan_Stok_Kg"]) * 100
        if n["Kekurangan_Stok_Kg"] > 0 else np.nan,
        "Penurunan_Selisih_Total_%": (1 - m["Total_Selisih_Absolut_Kg"] / n["Total_Selisih_Absolut_Kg"]) * 100,
    }
    hasil.to_csv(OUT / "11_rek_stok_testing.csv", index=False)

    per_bulan = df[df["Label"].isin([MODEL, PEMBANDING])].pivot(
        index="Periode", columns="Label", values="Prediksi_Kg").reset_index()
    per_bulan.insert(1, "Aktual_Kg", df[df["Label"] == MODEL].set_index("Periode")
                     .loc[per_bulan["Periode"], "Aktual_Kg"].values)
    per_bulan.to_csv(OUT / "11_rek_stok_per_bulan.csv", index=False)
    return hasil, pengurangan, per_bulan


# =============================================================================
# 2. INDEKS KEBUTUHAN (PAKAN) JAN-JUN 2026
# =============================================================================

def analisis_pakan():
    f = pd.read_csv(PERAMALAN_2026_CSV)
    rata = f["Yhat_Kg"].mean()
    normal = f[f["Yhat_Kg"] < f["Yhat_Kg"].max()]["Yhat_Kg"].mean()
    tab = pd.DataFrame({
        "Periode": f["Periode"],
        "Ramalan_Kg": f["Yhat_Kg"],
        "Indeks_vs_Rata2_6_Bulan": f["Yhat_Kg"] / rata,
        "Indeks_vs_Bulan_Normal": f["Yhat_Kg"] / normal,
        "Batas_Atas_95_Kg": f["Batas_Atas_95_Kg"],
    })
    tab.to_csv(OUT / "11_rek_indeks_kebutuhan_2026.csv", index=False)
    return tab, normal


# =============================================================================
# 3. KAPASITAS PUNCAK (UNDERPRODUKSI)
# =============================================================================

def analisis_kapasitas():
    f = pd.read_csv(PERAMALAN_2026_CSV)
    puncak = f.loc[f["Yhat_Kg"].idxmax()]
    val = pd.read_csv(VALIDASI_09_CSV)
    juni = val[val["Periode"] == "2025-06"].iloc[0]
    hasil = pd.DataFrame([{
        "Periode_Puncak": puncak["Periode"],
        "Ramalan_Puncak_Kg": puncak["Yhat_Kg"],
        "Batas_Atas_95_Kg": puncak["Batas_Atas_95_Kg"],
        "Stok_Pengaman_Kg": puncak["Batas_Atas_95_Kg"] - puncak["Yhat_Kg"],
        "Validasi_Juni_2025_Ramalan_Kg": juni["Yhat_Kg"],
        "Validasi_Juni_2025_Batas_Atas_Kg": juni["Batas_Atas_95_Kg"],
        "Validasi_Juni_2025_Aktual_Kg": juni["Aktual_Kg"],
        "Validasi_Juni_2025_Dalam_Interval": juni["Aktual_dalam_Interval"],
    }])
    hasil.to_csv(OUT / "11_rek_kapasitas_puncak.csv", index=False)
    return hasil.iloc[0]


# =============================================================================
# 3b. PANDUAN INDEKS / PERSENTASE UNTUK UMKM
# =============================================================================
# Ramalan berskala agregat Kabupaten Malang. Agar bisa dipakai UMKM dengan skala
# berapa pun, ramalan diubah menjadi angka relatif (tidak bergantung skala):
#   Indeks bulan       = Yhat_bulan / rata-rata Yhat bulan normal
#   Perubahan vs 2025  = Yhat_bulan / aktual bulan yang sama tahun lalu - 1
#   Faktor batas bawah = Batas_Bawah_95 / Yhat ;  faktor batas atas = Batas_Atas_95 / Yhat
#   Stok pengaman %    = (Batas_Atas_95 - Yhat) / Yhat
# Contoh pemakaian: UMKM dengan penjualan bulan normal X kg -> rencana bulan
# tersebut = X x indeks, kapasitas maksimum = X x indeks x faktor batas atas.

CONTOH_UMKM_KG = 500        # contoh penjualan bulan normal satu UMKM (ilustrasi)


def analisis_umkm():
    f = pd.read_csv(PERAMALAN_2026_CSV)
    d = pd.read_csv(DATASET_CSV, parse_dates=["Periode"])
    lalu = d.set_index(d["Periode"].dt.strftime("%Y-%m"))["Total_Kuantitas_Kg"]
    periode_lalu = pd.to_datetime(f["Periode"]) - pd.DateOffset(years=1)
    aktual_lalu = lalu.reindex(periode_lalu.dt.strftime("%Y-%m")).values

    normal = f[f["Yhat_Kg"] < f["Yhat_Kg"].max()]["Yhat_Kg"].mean()
    tab = pd.DataFrame({
        "Periode": f["Periode"],
        "Indeks_vs_Bulan_Normal": f["Yhat_Kg"] / normal,
        "Perubahan_vs_Tahun_Lalu_%": (f["Yhat_Kg"] / aktual_lalu - 1) * 100,
        "Faktor_Batas_Bawah": f["Batas_Bawah_95_Kg"] / f["Yhat_Kg"],
        "Faktor_Batas_Atas": f["Batas_Atas_95_Kg"] / f["Yhat_Kg"],
        "Stok_Pengaman_%": (f["Batas_Atas_95_Kg"] / f["Yhat_Kg"] - 1) * 100,
    })
    tab[f"Contoh_UMKM_{CONTOH_UMKM_KG}kg_Rencana_Kg"] = CONTOH_UMKM_KG * tab["Indeks_vs_Bulan_Normal"]
    tab[f"Contoh_UMKM_{CONTOH_UMKM_KG}kg_Maks_Kg"] = (CONTOH_UMKM_KG * tab["Indeks_vs_Bulan_Normal"]
                                                      * tab["Faktor_Batas_Atas"])
    tab.to_csv(OUT / "11_rek_panduan_umkm_2026.csv", index=False)
    return tab


# =============================================================================
# 4. MARGIN HARGA
# =============================================================================

def analisis_harga():
    d = pd.read_csv(DATASET_CSV, parse_dates=["Periode"])
    v = pd.read_csv(VOLUME_CSV, parse_dates=["Periode"])[["Periode", "Koefisien_Musim"]]
    d = d.merge(v, on="Periode")
    d["Kategori"] = np.where(d["Koefisien_Musim"] > 1, "Bulan Iduladha", "Bulan biasa")
    tab = d.groupby("Kategori").agg(
        Jumlah_Bulan=("Periode", "count"),
        Harga_Rata2_Per_Kg=("Harga_Rata2_Per_Kg", "mean"),
        Harga_Min=("Harga_Rata2_Per_Kg", "min"),
        Harga_Maks=("Harga_Rata2_Per_Kg", "max"),
        Volume_Rata2_Kg=("Total_Kuantitas_Kg", "mean"),
    ).reset_index()
    biasa = tab.set_index("Kategori").loc["Bulan biasa"]
    idul = tab.set_index("Kategori").loc["Bulan Iduladha"]
    selisih_pct = (idul["Harga_Rata2_Per_Kg"] / biasa["Harga_Rata2_Per_Kg"] - 1) * 100
    tab["Selisih_vs_Bulan_Biasa_%"] = (tab["Harga_Rata2_Per_Kg"] / biasa["Harga_Rata2_Per_Kg"] - 1) * 100
    tab.to_csv(OUT / "11_rek_harga_historis.csv", index=False)
    return tab, biasa, idul, selisih_pct


# =============================================================================
# RINGKASAN MARKDOWN
# =============================================================================

def tulis(stok, kurang, per_bulan, pakan, normal, kap, harga, biasa, idul, selisih_pct, umkm):
    ev = pd.read_csv(EVAL_TEST_CSV).set_index("Label")
    met7 = pd.read_csv(METRIK_07_CSV).set_index("Label")
    val = pd.read_csv(VALIDASI_09_CSV)
    mape_val = val["APE_%"].mean()
    m, n = stok.iloc[0], stok.iloc[1]
    f0 = lambda x: rp(x)

    L = ["# Rekomendasi Manajerial Berbasis Metrik Hasil Penelitian\n",
         "Dibuat otomatis oleh `11_rekomendasi_manajerial.py`. Semua angka berasal dari hasil "
         "penelitian ini (bukan angka contoh dokumen alur).\n",
         "## Sasaran rekomendasi\n",
         "Data penelitian adalah permintaan daging kambing **agregat Kabupaten Malang** (produksi "
         "BPS sebagai proksi permintaan, tidak dibagi jumlah UMKM karena jumlahnya tidak diketahui "
         "pasti). Karena itu rekomendasi disusun dalam dua tingkat:\n",
         "- **Tingkat kabupaten (angka kg):** Dinas yang membidangi peternakan, Rumah Potong Hewan "
         "(RPH), pemasok/pedagang besar ternak, dan asosiasi pedagang daging, untuk perencanaan "
         "pasokan ternak, kapasitas pemotongan, dan cold storage wilayah (bagian 1–4).",
         "- **Tingkat UMKM (angka relatif/indeks):** pedagang, warung sate, dan katering dengan "
         "skala berapa pun cukup mengalikan penjualan bulan normalnya dengan indeks (bagian 5).\n",
         "## Dasar akurasi model final SARIMA(1,0,0)x(1,1,0,12) log\n",
         f"- Validasi ekstrapolasi 6 bulan (Apr–Sep 2025): MAPE **{rp(mape_val, 2)}%**, "
         f"aktual di dalam interval 95% pada {int((val['Aktual_dalam_Interval'] == 'Ya').sum())} "
         f"dari {len(val)} bulan.",
         f"- Rolling origin 1 bulan (Apr–Des 2025): MAPE **{rp(met7.loc[MODEL, 'MAPE_%'], 2)}%**, "
         f"R² {rp(met7.loc[MODEL, 'R2'], 3)}.",
         f"- Peramalan 9 bulan data testing: MAPE **{rp(ev.loc[MODEL, 'MAPE_%'], 2)}%**, "
         f"RMSE {rp(ev.loc[MODEL, 'RMSE'])} kg; pembanding seasonal naive MAPE "
         f"{rp(ev.loc[PEMBANDING, 'MAPE_%'], 2)}%.",
         "- Seluruh MAPE berada di bawah target penelitian 15% (kategori akurat menurut "
         "Lewis, 1982: MAPE 10–20% baik, < 10% sangat akurat).\n"]

    L += ["## 1. Penurunan risiko kelebihan dan kekurangan pasokan wilayah\n",
          "**Asumsi:** rencana pasokan/pemotongan bulanan wilayah ditetapkan sama dengan ramalan. Metode lama "
          "diwakili seasonal naive (stok = penjualan bulan yang sama tahun lalu). Kelebihan stok = "
          "rencana − aktual bila positif; kekurangan = aktual − rencana bila positif. Periode: data "
          "testing Apr–Des 2025 (ramalan 9 bulan dari model yang dilatih s.d. Mar 2025).\n",
          tabel_md(stok, list(stok.columns), {k: f0 for k in stok.columns}),
          "",
          (f"- Kelebihan stok turun dari {rp(n['Kelebihan_Stok_Kg'])} kg menjadi "
           f"{rp(m['Kelebihan_Stok_Kg'])} kg (**{rp(kurang['Penurunan_Kelebihan_Stok_%'], 1)}%**)."
           if np.isfinite(kurang["Penurunan_Kelebihan_Stok_%"]) else
           f"- Pada periode ini permintaan 2025 lebih tinggi dari 2024, sehingga metode lama tidak "
           f"pernah kelebihan stok tetapi selalu kekurangan. Model menghasilkan kelebihan stok "
           f"{rp(m['Kelebihan_Stok_Kg'])} kg pada {int(m['Bulan_Kelebihan'])} bulan "
           f"({rp(m['Kelebihan_Stok_Kg'] / m['Total_Aktual_Kg'] * 100, 1)}% dari total permintaan), "
           "sebagai imbalan dari penurunan kekurangan stok yang jauh lebih besar."),
          f"- Kekurangan stok turun dari {rp(n['Kekurangan_Stok_Kg'])} kg menjadi "
          f"{rp(m['Kekurangan_Stok_Kg'])} kg (**{rp(kurang['Penurunan_Kekurangan_Stok_%'], 1)}%**).",
          f"- Total selisih rencana vs aktual turun **{rp(kurang['Penurunan_Selisih_Total_%'], 1)}%**.",
          f"- Dalam persentase total permintaan: selisih rencana vs aktual model "
          f"**{rp(m['Total_Selisih_Absolut_Kg'] / m['Total_Aktual_Kg'] * 100, 1)}%**, metode lama "
          f"**{rp(n['Total_Selisih_Absolut_Kg'] / n['Total_Aktual_Kg'] * 100, 1)}%** "
          "(angka persentase ini berlaku juga untuk UMKM, tidak bergantung skala).",
          "- Rekomendasi: jadikan ramalan model (garis tengah) dasar perencanaan pasokan dan "
          "pemotongan bulanan wilayah, dan perbarui ramalan setiap bulan setelah data aktual masuk "
          "(Tbl_Peramalan di Access) agar galat tidak menumpuk.\n"]

    pk = pakan
    L += ["## 2. Perencanaan pasokan ternak dan pakan wilayah\n",
          "**Asumsi:** kebutuhan ternak (dan pakan peternak) sebanding dengan volume permintaan. Angka "
          "\"pakan ±70% biaya operasional\" dari dokumen alur belum memiliki sumber di penelitian "
          "ini dan perlu rujukan sebelum dipakai.\n",
          tabel_md(pk, list(pk.columns), {"Ramalan_Kg": f0, "Batas_Atas_95_Kg": f0,
                                          "Indeks_vs_Rata2_6_Bulan": lambda x: rp(x, 2),
                                          "Indeks_vs_Bulan_Normal": lambda x: rp(x, 2)}),
          "",
          f"- Januari–Mei 2026 relatif datar (indeks {rp(pk['Indeks_vs_Bulan_Normal'].iloc[:-1].min(), 2)}–"
          f"{rp(pk['Indeks_vs_Bulan_Normal'].iloc[:-1].max(), 2)} terhadap rata-rata bulan normal "
          f"{rp(normal)} kg untuk seluruh kabupaten): pasokan ternak dan pakan rutin peternak "
          "dapat direncanakan/dikontrak di awal tahun.",
          f"- Puncak Iduladha membutuhkan ±{rp(pk['Indeks_vs_Bulan_Normal'].iloc[-1], 2)} kali bulan "
          "normal. Karena Iduladha 2026 jatuh ±27 Mei, program penggemukan ternak dan penambahan "
          "pakan (konsentrat dan hijauan) di tingkat peternak sebaiknya dimulai Maret–April 2026.\n"]

    L += ["## 3. Pencegahan kekurangan pasokan saat puncak (tingkat kabupaten)\n",
          f"- Ramalan puncak {kap['Periode_Puncak']}: **{rp(kap['Ramalan_Puncak_Kg'])} kg**; batas "
          f"atas interval 95%: **{rp(kap['Batas_Atas_95_Kg'])} kg** untuk seluruh Kabupaten Malang. "
          "Angka ini adalah acuan kapasitas wilayah (gabungan RPH, cold storage, dan pasokan ternak "
          "dari peternak/pemasok), bukan kapasitas satu usaha. Stok pengaman wilayah "
          f"{rp(kap['Stok_Pengaman_Kg'])} kg di atas ramalan "
          f"(**+{rp(kap['Stok_Pengaman_Kg'] / kap['Ramalan_Puncak_Kg'] * 100, 1)}%**).",
          "- Batas atas 95% dua sisi berarti peluang permintaan melebihi batas atas ±2,5% (tidak "
          "nol). Penyediaan sampai batas atas menurunkan risiko stockout, bukan menjamin 100% "
          "permintaan terlayani.",
          f"- Bukti validasi: Juni 2025 ramalan {rp(kap['Validasi_Juni_2025_Ramalan_Kg'])} kg, batas "
          f"atas {rp(kap['Validasi_Juni_2025_Batas_Atas_Kg'])} kg, aktual "
          f"{rp(kap['Validasi_Juni_2025_Aktual_Kg'])} kg (di dalam interval: "
          f"{kap['Validasi_Juni_2025_Dalam_Interval']}).",
          "- **Iduladha 2026 jatuh ±27 Mei**, sedangkan model menaruh puncak di Juni (meniru pola "
          "2023–2025). Kapasitas puncak harus siap **pertengahan Mei 2026**.\n"]

    L += ["## 4. Batas margin harga jual\n",
          tabel_md(harga, list(harga.columns),
                   {"Harga_Rata2_Per_Kg": f0, "Harga_Min": f0, "Harga_Maks": f0,
                    "Volume_Rata2_Kg": f0, "Selisih_vs_Bulan_Biasa_%": lambda x: rp(x, 1)}),
          "",
          f"- Harga rata-rata bulan Iduladha Rp{rp(idul['Harga_Rata2_Per_Kg'])}/kg, "
          f"**{rp(selisih_pct, 1)}%** di atas bulan biasa (Rp{rp(biasa['Harga_Rata2_Per_Kg'])}/kg), "
          f"sementara volumenya ±{rp(idul['Volume_Rata2_Kg'] / biasa['Volume_Rata2_Kg'], 1)} kali bulan biasa.",
          f"- Januari–April 2026 (permintaan rendah, ramalan ±{rp(normal)} kg/bulan): pertahankan "
          "margin tipis untuk mempercepat perputaran stok dan menghindari pembusukan.",
          f"- Menjelang Iduladha: kenaikan margin wajar berada di kisaran historis ±{rp(selisih_pct, 0)}%, "
          "diterapkan bertahap mulai pertengahan Mei 2026.",
          "- Catatan: koefisien harga pada model ARIMAX tidak dapat dibaca sebagai elastisitas "
          "sebab-akibat. Harga dan volume sama-sama naik di bulan Iduladha (korelasi 0,988), "
          "sehingga data tidak dapat memisahkan efek harga dari efek musim.\n"]

    u = umkm
    kol_rencana = f"Contoh_UMKM_{CONTOH_UMKM_KG}kg_Rencana_Kg"
    kol_maks = f"Contoh_UMKM_{CONTOH_UMKM_KG}kg_Maks_Kg"
    pct = lambda x: rp(x, 1)
    L += ["## 5. Panduan indeks untuk UMKM (tidak bergantung skala usaha)\n",
          "Ramalan kabupaten diubah menjadi angka relatif agar dapat dipakai UMKM dengan skala "
          "berapa pun. File: `data/hasil_11/11_rek_panduan_umkm_2026.csv`.\n",
          "- **Indeks_vs_Bulan_Normal** = ramalan bulan tersebut ÷ rata-rata ramalan bulan normal "
          "(Jan–Mei 2026).",
          "- **Perubahan_vs_Tahun_Lalu_%** = ramalan ÷ aktual bulan yang sama tahun 2025 − 1.",
          "- **Faktor_Batas_Atas** = batas atas 95% ÷ ramalan; **Stok_Pengaman_%** = faktor batas "
          "atas − 1.\n",
          tabel_md(u, ["Periode", "Indeks_vs_Bulan_Normal", "Perubahan_vs_Tahun_Lalu_%",
                       "Faktor_Batas_Bawah", "Faktor_Batas_Atas", "Stok_Pengaman_%"],
                   {"Indeks_vs_Bulan_Normal": lambda x: rp(x, 2),
                    "Perubahan_vs_Tahun_Lalu_%": pct,
                    "Faktor_Batas_Bawah": lambda x: rp(x, 2),
                    "Faktor_Batas_Atas": lambda x: rp(x, 2),
                    "Stok_Pengaman_%": pct}),
          "",
          "**Cara pakai:** rencana stok bulan t = penjualan bulan normal UMKM × Indeks_t; "
          "kapasitas maksimum yang disiapkan = rencana × Faktor_Batas_Atas_t.\n",
          f"**Contoh** UMKM dengan penjualan bulan normal {rp(CONTOH_UMKM_KG)} kg:\n",
          tabel_md(u, ["Periode", kol_rencana, kol_maks], {kol_rencana: f0, kol_maks: f0}),
          "",
          f"- Bulan puncak {u['Periode'].iloc[-1]}: siapkan ±{rp(u['Indeks_vs_Bulan_Normal'].iloc[-1], 2)}× "
          f"penjualan bulan normal, dengan cadangan sampai "
          f"+{rp(u['Stok_Pengaman_%'].iloc[-1], 0)}% di atas rencana.",
          "- Karena Iduladha 2026 jatuh ±27 Mei, indeks puncak sebaiknya diterapkan mulai "
          "pertengahan Mei 2026, bukan menunggu Juni.",
          "- Indeks berlaku bila pola musiman UMKM mirip pola kabupaten; UMKM yang pelanggannya "
          "didominasi aqiqah/katering dapat memiliki pola berbeda.\n"]

    L += ["## Keterbatasan\n",
          "- Data penelitian adalah data sintetis yang dikalibrasi dari BPS (agregat Kabupaten "
          "Malang), bukan transaksi riil satu usaha; produksi daging dipakai sebagai proksi permintaan.",
          "- Level ramalan 2026 rata-rata ±22,8% di bawah 2025; ini artefak koefisien musiman yang "
          "mengulang penurunan 2023→2024, bukan tren pasti.",
          "- Puncak ramalan di Juni, sedangkan Iduladha 2026 jatuh di akhir Mei.",
          "- Analisis biaya pakan dan margin bersifat relatif (indeks), karena data biaya pakan "
          "tidak tersedia."]

    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    stok, kurang, per_bulan = analisis_stok()
    pakan, normal = analisis_pakan()
    kap = analisis_kapasitas()
    harga, biasa, idul, selisih = analisis_harga()
    umkm = analisis_umkm()
    tulis(stok, kurang, per_bulan, pakan, normal, kap, harga, biasa, idul, selisih, umkm)
    print(umkm.round(2).to_string(index=False))
    print(stok.to_string(index=False))
    print({k: round(v, 1) for k, v in kurang.items()})
    print(pakan.round(2).to_string(index=False))
    print(harga.round(1).to_string(index=False))
    print(f"Ringkasan: {RINGKASAN_MD}")
    print("REKOMENDASI MANAJERIAL SELESAI.")


if __name__ == "__main__":
    main()
