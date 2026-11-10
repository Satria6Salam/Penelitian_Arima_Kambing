"""
=============================================================================
PROGRAM GENERATE DATA PENJUALAN DAGING KAMBING (DATA SINTETIS BERBASIS BPS)
Penelitian Judul 11 - Prediksi Permintaan Daging Kambing Menggunakan ARIMA
=============================================================================

APA YANG DILAKUKAN PROGRAM INI?
    Membuat data tiruan (sintetis) penjualan daging kambing untuk pasar
    Kabupaten Malang selama 36 bulan (Januari 2023 - Desember 2025).
    Semua angka dasar diambil dari data resmi (BPS, Kemenag, harga pasar),
    lalu diolah bertahap sesuai dokumen "cara kerja":

    Tahap 1 : Time horizon       -> membuat urutan bulan t = 1..36
    Tahap 2 : Baseline           -> volume dasar per bulan dari data BPS
              Langkah 1 : ambil data produksi Kabupaten Malang dari CSV BPS
              Langkah 2 : produksi tahunan  / 12   = produksi bulanan kabupaten
              Langkah 3 : produksi bulanan kabupaten menjadi baseline (tanpa dibagi jumlah UMKM)
              Langkah 4 : rasio 4 jenis produk (Daging Murni, Karkas, Jeroan, Variasi)
              Langkah 5 : undian jenis produk sesuai rasio (multinomial)
              Langkah 6 : undian volume bulanan  mu +- 10%  (random uniform)
              Langkah 7 : pecah volume bulanan menjadi struk transaksi 5-35 kg
    Tahap 3 : Tren linier        -> volume naik/turun mengikuti tren nasional
    Tahap 4 : Faktor musiman     -> volume bulan Iduladha x 2,717
    Tahap 5 : Variabel eksogen   -> harga jual per kg & jumlah pesanan (untuk ARIMAX)
    Tahap 6 : White noise        -> galat acak kecil berdistribusi normal
    Tahap 7 : Kompilasi & ekspor -> gabungkan semua variabel, simpan ke .csv

URUTAN EKSEKUSI DI PROGRAM
    Tahap 1 -> Tahap 2 (Langkah 1-6) -> Tahap 3 -> Tahap 4 -> Tahap 6
            -> Langkah 7 -> Tahap 5 -> Tahap 7
    Alasan: struk transaksi (Langkah 7) baru dipecah setelah volume bulanan
    FINAL terbentuk (sudah ada tren, musim, dan noise), dan harga (Tahap 5)
    diundi per struk transaksi, jadi harus setelah Langkah 7.

CARA MENJALANKAN
    python 03_generate_data.py

INPUT  (folder data/)
    bps_produksi_kambing_2023.csv, bps_produksi_kambing_2024.csv,
    bps_produksi_kambing_2025.csv
    Sumber: BPS, "Jumlah Produksi Daging Kambing Menurut Kabupaten/Kota dan
    Jenis Produksi di Provinsi Jawa Timur (kg)", 2023-2025.

OUTPUT (folder data/)
    dataset_sarimax.csv      -> DATASET UTAMA: 36 bulan, siap untuk ADF & SARIMAX
    volume_bulanan.csv       -> semua kolom per bulan dari Tahap 1-6 (untuk ditelusuri)
    transaksi_penjualan.csv  -> rincian setiap struk transaksi + harga
    baseline_bps.csv         -> hasil perhitungan baseline per tahun (Tahap 2)
=============================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd

import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/


# #############################################################################
#                           BAGIAN A - PARAMETER
#  Semua angka asumsi & referensi dikumpulkan di sini supaya mudah dijelaskan
#  dan mudah diubah tanpa menyentuh rumus di bawahnya.
# #############################################################################

# --- Lokasi file -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent     # folder tempat program ini berada
BPS_DIR = BASE_DIR / "data" / "sumber_bps"     # folder input (CSV BPS)
DATA_DIR = BASE_DIR / "data" / "hasil_generate"  # folder output data hasil generate

# --- Pengaturan acak ---------------------------------------------------------
# Seed membuat angka acak SELALU SAMA setiap program dijalankan,
# sehingga hasil penelitian bisa diulang (reproducible).
SEED = 42

# --- Tahap 1: time horizon ---------------------------------------------------
TAHUN_DATA = [2023, 2024, 2025]     # 3 tahun x 12 bulan = 36 bulan
                                    # merujuk pada 3 file bps_produksi_kambaing_[tahun]

# --- Tahap 2: baseline -------------------------------------------------------
WILAYAH = "Malang"                  # nama baris di CSV BPS (Kabupaten Malang, BUKAN "Kota Malang")
K_TOLERANSI = 0.10                  # ?? k  = toleransi variasi bulanan +-10% (Langkah 6)
PEMOTONGAN_MEI_2024 = 8_229         # ekor kambing dipotong bulan Mei 2024 (BPS)  -> dasar k https://data.goodstats.id/statistic/hewan-kurban-terbanyak-sapi-kambing-atau-domba-Co1Yj 
PEMOTONGAN_JULI_2024 = 8_011        # ekor kambing dipotong bulan Juli 2024 (BPS) -> dasar k https://data.goodstats.id/statistic/hewan-kurban-terbanyak-sapi-kambing-atau-domba-Co1Yj 
BERAT_PESANAN_MIN = 5.0             # ?? kg, berat terkecil satu struk (Langkah 7)
BERAT_PESANAN_MAKS = 35.0           # ?? kg, berat terbesar satu struk (Langkah 7)

# --- Tahap 3: tren linier ----------------------------------------------------
# Produksi daging kambing nasional (ribu ton), sumber: BPS via GoodStats
# https://goodstats.id/article/produksi-daging-kambing-di-indonesia-kembali-meningkat-2025-jawa-timur-jadi-sentra-produksi-tertinggi-PplRu  
PRODUKSI_NASIONAL = {
    2016: 67.85, 2017: 70.35, 2018: 70.16, 2019: 72.85, 2020: 61.71,
    2021: 59.73, 2022: 60.77, 2023: 61.32, 2024: 52.99, 2025: 60.99,
}
TAHUN_STABIL = 2023                 # tahun pertama = fase stabil (tanpa tren)

# --- Tahap 4: faktor musiman Iduladha ----------------------------------------
# https://data.goodstats.id/statistic/hewan-kurban-terbanyak-sapi-kambing-atau-domba-Co1Yj
PEMOTONGAN_JUNI_2024 = 22_359       # ekor kambing dipotong bulan Juni 2024 (saat Iduladha, BPS)
BULAN_IDULADHA = {2023: 6, 2024: 6, 2025: 6}   # Iduladha 29 Jun 2023, 17 Jun 2024, 6 Jun 2025
# Referensi pendukung (validasi skala pasar, tidak masuk hitungan):
# Kemenag RI Iduladha 1447 H/2026 M -> kurban nasional 2.032.753 ekor, Jawa Timur 455.007 ekor.

# --- Tahap 5: harga jual (Rp/kg), referensi harga eceran 2026 ----------------
# https://kumparan.com/kabar-harian/harga-daging-kambing-1-kg-berapa-ini-perkiraan-umumnya-27TpPvrHoWY
RENTANG_HARGA = {
    "Daging Murni":   (95_000, 180_000),  # daging murni/premium (has dalam/paha)
    "Karkas":         (120_000, 125_000),  # karkas kambing segar
    "Jeroan":         (25_000, 50_000),  # SEMENTARA = daging standar (belum ada referensi jeroan)
    "Daging Variasi": (75_000, 120_000),  # daging standar (campur tulang/tetelan)
}
MARKUP_IDULADHA = (10_000, 15_000)  # Rp/kg, kenaikan harga menjelang Iduladha
PEMBULATAN_HARGA = 500              # harga dibulatkan ke kelipatan Rp 500

# --- Tahap 6: white noise ----------------------------------------------------
SIGMA_NOISE = 0.05                  # sigma = 5% x volume bulan t (asumsi metodologis 5%-10%)

# --- Struktur CSV BPS (nama kolom asli) --------------------------------------
KOLOM_BPS = {
    "Daging Murni":    "Produksi Daging Kambing - Daging Murni/Skeletal (Kg)",
    "Karkas":          "Produksi Daging Kambing - Karkas (Kg)",
    "Jeroan":          "Produksi Daging Kambing - Jeroan (Kg)",
    "Daging Variasi":  "Produksi Daging Kambing - Daging Variasi (Kg)",
    "Total Karkas":    "Produksi Daging Kambing - Jumlah Produksi Daging (Karkas) (Kg)",
    "Total Meatyield": "Produksi Daging Kambing - Jumlah Produksi Daging (Meatyield) (Kg)",
}
PRODUK = ["Daging Murni", "Karkas", "Jeroan", "Daging Variasi"]

# Generator angka acak tunggal yang dipakai seluruh program
rng = np.random.default_rng(SEED)


# #############################################################################
#                    BAGIAN B - FUNGSI BANTU TAMPILAN TERMINAL
#  Fungsi-fungsi ini hanya untuk merapikan tampilan, tidak mengubah data.
# #############################################################################

def angka(x, desimal=2):
    """Format angka gaya Indonesia: 1234567.891 -> '1.234.567,89'."""
    teks = f"{x:,.{desimal}f}"                          # format bawaan: 1,234,567.89
    return teks.replace(",", "#").replace(".", ",").replace("#", ".")


def persen(x, desimal=2, tanda=False):
    """Format pecahan menjadi persen: 0.1510 -> '15,10%' (atau '+15,10%' jika tanda=True)."""
    teks = angka(abs(x) * 100, desimal) + "%"
    if tanda:
        return ("+" if x >= 0 else "-") + teks
    return ("-" if x < 0 else "") + teks


NAMA_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def bulan_tahun(tanggal):
    """Format tanggal menjadi nama bulan Indonesia: 2025-12-01 -> 'Des 2025'."""
    return f"{NAMA_BULAN[tanggal.month - 1]} {tanggal.year}"


def rupiah(x):
    """Format rupiah: 1945250 -> 'Rp 1.945.250'."""
    return "Rp " + angka(x, 0)


def judul_tahap(teks):
    """Mencetak judul besar untuk setiap tahap."""
    print()
    print("=" * 100)
    print(f"  {teks}")
    print("=" * 100)


def cetak_tabel(header, baris, rata=None, judul=None):
    """
    Mencetak tabel berbingkai di terminal.

    header : list judul kolom
    baris  : list of list, isi tabel (sudah berupa teks)
    rata   : string per kolom, 'l' = rata kiri, 'r' = rata kanan (default: semua kanan)
    judul  : teks kecil di atas tabel (opsional)
    """
    rata = rata or "r" * len(header)
    # lebar kolom = teks terpanjang di kolom tersebut (header atau isi)
    lebar = [max(len(str(h)), *(len(str(b[i])) for b in baris)) for i, h in enumerate(header)]

    def susun(sel):
        isi = [str(s).ljust(w) if r == "l" else str(s).rjust(w) for s, w, r in zip(sel, lebar, rata)]
        return "| " + " | ".join(isi) + " |"

    garis = "+" + "+".join("-" * (w + 2) for w in lebar) + "+"
    if judul:
        print(f"\n  {judul}")
    print(garis)
    print(susun(header))
    print(garis.replace("-", "="))
    for b in baris:
        print(susun(b))
    print(garis)


# #############################################################################
#                       BAGIAN C - TAHAP 1: TIME HORIZON
# #############################################################################

def buat_time_horizon(tahun_list):
    """
    Membuat indeks waktu bulanan yang berurutan (sekuensial).

    Jumlah bulan = jumlah tahun x 12 = 3 x 12 = 36
        t = 1  -> Januari 2023
        t = 36 -> Desember 2025

    36 bulan = 3 siklus tahunan, syarat minimal agar ARIMA/SARIMA (m = 12)
    dapat mengenali pola musiman.

    Hasil: tabel dengan kolom t, Periode (tanggal 1 tiap bulan), Tahun, Bulan.
    """
    # pd.date_range membuat deretan tanggal; freq="MS" = Month Start (tanggal 1 tiap bulan)
    periode = pd.date_range(f"{tahun_list[0]}-01-01", periods=len(tahun_list) * 12, freq="MS")
    return pd.DataFrame({
        "t": np.arange(1, len(periode) + 1),     # 1, 2, 3, ..., 36
        "Periode": periode,
        "Tahun": periode.year,
        "Bulan": periode.month,
    })


# #############################################################################
#           BAGIAN D - TAHAP 2 / LANGKAH 1: EKSTRAKSI DATA BPS
# #############################################################################

def cari_file_bps(tahun):
    """Mencari file CSV BPS untuk satu tahun di folder data/."""
    kandidat = sorted(BPS_DIR.glob(f"bps_produksi_kambing_{tahun}*.csv"))
    if not kandidat:
        raise FileNotFoundError(f"File BPS tahun {tahun} tidak ditemukan di {BPS_DIR}")
    return kandidat[0]


def ke_angka(nilai):
    """
    Mengubah isi sel CSV BPS menjadi angka.
        "1462465.57 (*)" -> 1462465.57   (tanda (*) = angka sementara BPS, dibuang)
        "..."            -> NaN          (artinya data tidak tersedia)
    """
    teks = str(nilai).replace("(*)", "").strip()
    try:
        return float(teks)
    except ValueError:
        return np.nan

def baca_bps_wilayah(tahun, wilayah):
    """
    Langkah 1 - membaca satu file CSV BPS dan mengambil baris satu kabupaten.
    Menangani penyesuaian header terbalik pada dataset BPS 2024 & 2025.
    """
    df = pd.read_csv(cari_file_bps(tahun), encoding="utf-8-sig", dtype=str)
    baris = df[df["Kabupaten/Kota"].str.strip() == wilayah]
    if baris.empty:
        raise ValueError(f"Wilayah '{wilayah}' tidak ada di data BPS {tahun}")
    baris = baris.iloc[0]

    # Salin pemetaan kolom dasar
    pemetaan_kolom = KOLOM_BPS.copy()

    # Penyesuaian khusus untuk CSV 2024 & 2025 yang nama kolom totalnya terbalik
    if tahun in [2024, 2025]:
        pemetaan_kolom["Total Meatyield"] = KOLOM_BPS["Total Karkas"]
        pemetaan_kolom["Total Karkas"] = KOLOM_BPS["Total Meatyield"]

    return {nama: ke_angka(baris[kolom]) for nama, kolom in pemetaan_kolom.items()}

import numpy as np

def lengkapi_komponen_kosong(data_tahunan):
    """
    ========================================================================================
    FUNGSI IMPUTASI STATISTIK BPS 2023 (HISTORICAL PROPORTION-BASED ALGEBRAIC IMPUTATION)
    ========================================================================================
    
    1. LATAR BELAKANG & MASALAH DATASET BPS:
       - Dataset BPS 2023 hanya menerbitkan 2 angka total (Total Karkas & Total Meatyield).
       - Rincian 4 komponen produk (Daging Murni, Karkas, Jeroan, Daging Variasi) bernilai "..." (NaN).
       - Dataset 2024 & 2025 memiliki rincian produk yang lengkap.
       
    2. PEMETAAN KOLOM & RUMUS DASAR (HUBUNGAN ALJABAR BPS):
       Definisi Edible Portion (E) = Jeroan + Daging Variasi
       
       A. Dataset 2024 & 2025 (Header Kolom Terbalik pada CSV BPS):
          - Total Meatyield (dari kolom 'Karkas' CSV)    = Karkas + E
          - Total Karkas    (dari kolom 'Meatyield' CSV) = Daging Murni + E
          
       B. Dataset 2023 (Header Kolom Normal / Tidak Terbalik):
          - Total Karkas    (dari kolom 'Karkas' CSV)    = Karkas + E
          - Total Meatyield (dari kolom 'Meatyield' CSV) = Daging Murni + E
          
    3. RUMUS PEMBALIKAN UNTUK ESTIMASI RINCIAN PRODUK 2023:
          - E_2023          = s * Total_Meatyield_2023
          - Jeroan_2023     = p * E_2023
          - Variasi_2023    = (1 - p) * E_2023
          - Karkas_2023     = Total_Karkas_2023 - E_2023
          - Daging_Murni_23 = Total_Meatyield_2023 - E_2023
    ========================================================================================
    """
    
    # --------------------------------------------------------------------------------------
    # 1: EKSTRAKSI RASIO PROPORSI HISTORIS (s dan p) DARI DATASET LENGKAP (2024 & 2025)
    # --------------------------------------------------------------------------------------
    # Siapkan wadah (list) kosong untuk menyimpan data
    lengkap = []
    daftar_s = []
    daftar_p = []

    # Proses penyaringan: Cari tahun yang datanya lengkap (Karkas tidak kosong)
    for d in data_tahunan.values():
        if not np.isnan(d["Karkas"]):  # Jika angka Karkas BUKAN NaN (kosong)
            lengkap.append(d)          # Masukkan data tahun tersebut ke wadah 'lengkap'

    # Proses perhitungan: Hitung rasio untuk setiap tahun yang lengkap
    for d in lengkap:
        # Ambil angka-angka dari buku catatan tahun tersebut biar variabelnya lebih ringkas dibaca
        jeroan = d["Jeroan"]
        variasi = d["Daging Variasi"]
        total_meatyield = d["Total Meatyield"]
        
        # Hitung Edible Portion (E)
        e = jeroan + variasi
        
        # Hitung rasio untuk tahun ini
        s_tahun = e / total_meatyield
        p_tahun = jeroan / e
        
        # Simpan hasil hitungan tahun ini ke wadah masing-masing
        daftar_s.append(s_tahun)
        daftar_p.append(p_tahun)

    # Tahap Akhir: Hitung rata-rata dari seluruh tahun yang berhasil dikumpulkan
    s = np.mean(daftar_s)
    p = np.mean(daftar_p)

    # --------------------------------------------------------------------------------------
    # 2: EKSEKUSI IMPUTASI DATA BPS 2023 (PENYESUAIAN RUAS LURUS)
    # --------------------------------------------------------------------------------------
    for d in data_tahunan.values():
        # Menandai apakah data tahun ini memerlukan taksiran/imputasi
        d["Diestimasi"] = bool(np.isnan(d["Karkas"]))
        
        if d["Diestimasi"]:
            # 1. Estimasi Total Edible Portion 2023 (E = Jeroan + Daging Variasi)
            #    Rumus: E_2023 = s * Total Meatyield 2023
            e = s * d["Total Meatyield"]
            
            # 2. Break-down Nilai E_2023 menjadi Komponen Jeroan & Daging Variasi
            #    Rumus: Jeroan = p * E
            d["Jeroan"] = p * e
            #    Rumus: Daging Variasi = (1 - p) * E
            d["Daging Variasi"] = (1 - p) * e
            
            # 3. Hitung Produk Utama 2023 (Header Normal 2023)
            #    Rumus Karkas: Total Karkas - E  (Karkas = Total Karkas - E)
            d["Karkas"] = d["Total Karkas"] - e
            
            #    Rumus Daging Murni: Total Meatyield - E  (Daging Murni = Total Meatyield - E)
            d["Daging Murni"] = d["Total Meatyield"] - e

    return data_tahunan


# #############################################################################
#      BAGIAN E - TAHAP 2 / LANGKAH 2-4: BASELINE WILAYAH & RASIO PRODUK
# #############################################################################

def hitung_baseline(data_tahunan):
    """
    Menghitung baseline bulanan wilayah (mu) dan rasio produk untuk setiap tahun.

    Langkah 2 - dari tahunan ke bulanan (tingkat kabupaten):
        Karkas Bulanan Kabupaten = Karkas Tahunan Kabupaten / 12
        contoh 2024: 1.048.096,31 / 12 = 87.341,36 kg per bulan

    Langkah 3 - menetapkan baseline bulanan wilayah:
        mu = Karkas Bulanan Kabupaten
        contoh 2024: mu = 87.341,36 kg per bulan

    Langkah 4 - rasio komposisi produk:
        Rasio produk i = Produksi produk i / (Murni + Karkas + Jeroan + Variasi)
        contoh 2024: Karkas = 1.048.096,31 / 2.809.949,68 = 37,30%

    Baseline bersifat time-varying: bulan-bulan di 2023 memakai data BPS 2023,
    2024 memakai data 2024, 2025 memakai data 2025.
    """
    hasil = []
    for tahun, d in data_tahunan.items():
        karkas_bulanan_kab = d["Karkas"] / 12                     # Langkah 2
        mu = karkas_bulanan_kab              # Langkah 3
        total_4_produk = sum(d[p] for p in PRODUK)                # penyebut Langkah 4
        baris = {
            "Tahun": tahun,
            "Karkas_Tahunan_Kab": d["Karkas"],
            "Karkas_Bulanan_Kab": karkas_bulanan_kab,
            "Mu_Lokal": mu,
            "Diestimasi": d["Diestimasi"],
        }
        for p in PRODUK:
            baris[f"Rasio_{p}"] = d[p] / total_4_produk           # Langkah 4
        hasil.append(baris)
    return pd.DataFrame(hasil)

    """
    hasil = [
        {
            "Tahun": 2023,
            "Karkas_Tahunan_Kab": 515642.23,
            "Karkas_Bulanan_Kab": 42970.18,
            "Mu_Lokal": 572.93,
            "Diestimasi": True,
            # ... (rasio produk)
        },
        {
            "Tahun": 2024,
            "Karkas_Tahunan_Kab": 430336.95,
            "Karkas_Bulanan_Kab": 35861.41,
            "Mu_Lokal": 478.15,
            "Diestimasi": False, 
            # ... (rasio produk)
        }
    ]
    """


# #############################################################################
#        BAGIAN F - TAHAP 2 / LANGKAH 6: VOLUME BULANAN ACAK (+-10%)
# #############################################################################

def hitung_variasi_relatif(a, b):
    """
    Selisih relatif dua bulan non-musiman (dasar memilih nilai k):
        selisih = |a - b| / ((a + b) / 2) x 100%
        Mei vs Juli 2024: |8.229 - 8.011| / 8.120 x 100% = 2,68%
    """
    return abs(a - b) / ((a + b) / 2) * 100


def buat_volume_bulanan(horizon, baseline):
    """
    Mengundi volume dasar setiap bulan (Langkah 6, Stochastic Noise Margin):

        Volume ~ Uniform( mu - k.mu , mu + k.mu )

        contoh 2024 (mu = 87.341,36 ; k = 0,10):
            batas bawah = 87.341,36 - 8.734,14 = 78.607,22 kg
            batas atas  = 87.341,36 + 8.734,14 = 96.075,50 kg

    k = 10% adalah asumsi variasi bulanan sintetis yang lebih lebar daripada
    variasi data BPS Mei-Juli 2024 (2,68%).
    """
    data = []
    for _, b in horizon.iterrows():
        # ambil mu sesuai tahun bulan ini (time-varying)
        mu = baseline.loc[baseline["Tahun"] == b["Tahun"], "Mu_Lokal"].iloc[0]
        batas_bawah = mu - K_TOLERANSI * mu                       # mu - k.mu
        batas_atas = mu + K_TOLERANSI * mu                        # mu + k.mu
        volume = rng.uniform(batas_bawah, batas_atas)             # undian seragam
        data.append({**b.to_dict(), "Mu_Lokal": mu, "Batas_Bawah": batas_bawah,
                     "Batas_Atas": batas_atas, "Target_Kg": round(volume, 2)})
    return pd.DataFrame(data)


# #############################################################################
#                    BAGIAN G - TAHAP 3: INJEKSI TREN LINIER
# #############################################################################

def hitung_growth_rate(produksi, tahun):
    """
    Laju pertumbuhan produksi nasional dari tahun sebelumnya:

        Growth = (Produksi tahun ini - Produksi tahun lalu) / Produksi tahun lalu

        2023 -> 2024: (52,99 - 61,32) / 61,32 = -13,58%   (kontraksi)
        2024 -> 2025: (60,99 - 52,99) / 52,99 = +15,10%   (pemulihan)
    """
    return (produksi[tahun] - produksi[tahun - 1]) / produksi[tahun - 1]


def hitung_gradien_per_tahun(tahun_list):
    """
    Menentukan gradien bulanan (m) untuk setiap fase tahunan:

        2023 (t = 1-12)  : fase stabil     -> m = 0
        2024 (t = 13-24) : fase kontraksi  -> m = -13,58% / 12 = -1,1317% per bulan
        2025 (t = 25-36) : fase pemulihan  -> m = +15,10% / 12 = +1,2581% per bulan

    Rumus: m = Growth tahunan / 12   (pertumbuhan setahun dibagi rata ke 12 bulan)
    t_awal_fase = nomor bulan tepat sebelum fase dimulai (0, 12, 24).
    """
    hasil = []
    for i, tahun in enumerate(tahun_list):
        growth = 0.0 if tahun == TAHUN_STABIL else hitung_growth_rate(PRODUKSI_NASIONAL, tahun)
        hasil.append({"Tahun": tahun,
                      "t_awal_fase": i * 12,
                      "Growth_Tahunan": growth,
                      "m_Bulanan": growth / 12})
    return pd.DataFrame(hasil)


def injeksi_tren(volume_bulanan, gradien):
    """
    Menerapkan persamaan garis linier ke setiap bulan:

        Faktor Tren_t = 1 + m x (t - t_awal_fase)
        Volume Tren_t = Volume Tahap 2_t x Faktor Tren_t

    Volume Tren dihitung dari baseline wilayah:
        Volume Tren_Kg = Target_Kg x Faktor Tren
    """

    data_hasil = []
    
    # Proses membaca tabel volume bulanan satu baris demi baris
    for index, baris_bulan in volume_bulanan.iterrows():
        # Ambil tahun dari baris bulan saat ini (misal: 2024 atau 2025)
        tahun_ini = baris_bulan["Tahun"]
        
        # 3. Cari informasi gradien (m_Bulanan dan t_awal_fase) yang cocok dengan tahun tersebut
        # Kita saring tabel gradien berdasarkan tahunnya
        baris_gradien = gradien[gradien["Tahun"] == tahun_ini].iloc[0]
        
        # Ambil nilai m_Bulanan dan t_awal_fase dari baris yang cocok
        m_bulanan = baris_gradien["m_Bulanan"]
        t_awal_fase = baris_gradien["t_awal_fase"]
        
        # Ambil nomor bulan berjalan (t) dan target kg dasar (Target_Kg) dari baris bulan
        t_berjalan = baris_bulan["t"]
        target_kg_dasar = baris_bulan["Target_Kg"]
        
        # 4. Hitung selisih waktu (sudah berapa bulan berjalan sejak awal fase)
        selisih_waktu = t_berjalan - t_awal_fase
        
        # 5. Hitung Faktor Tren menggunakan rumus matematika: 1 + (m * selisih_waktu)
        faktor_tren = 1 + (m_bulanan * selisih_waktu)
        
        # 6. Hitung volume akhir setelah dikalikan tren, lalu bulatkan 2 angka di belakang koma
        volume_tren_kg = round(target_kg_dasar * faktor_tren, 2)
        
        # 7. Salin data asli dari baris bulan, lalu tambahkan kolom-kolom baru hasil perhitungan tren
        baris_baru = baris_bulan.to_dict()  # Ubah baris data asli jadi kamus data
        baris_baru["t_awal_fase"] = t_awal_fase
        baris_baru["m_Bulanan"] = m_bulanan
        baris_baru["Faktor_Tren"] = faktor_tren
        baris_baru["Volume_Tren_Kg"] = volume_tren_kg
        
        # 8. Masukkan baris lengkap ini ke laci penampung
        data_hasil.append(baris_baru)
        
    # 9. Setelah semua baris selesai dihitung, ubah tumpukan laci menjadi tabel DataFrame yang rapi
    return pd.DataFrame(data_hasil)


# #############################################################################
#             BAGIAN H - TAHAP 4: PENYISIPAN FAKTOR MUSIMAN (IDULADHA)
# #############################################################################

def hitung_koefisien_musiman(sebelum, saat):
    """
    Mengubah persentase lonjakan menjadi koefisien pengali musiman (S):

        Lonjakan = (Juni - Mei) / Mei = (22.359 - 8.229) / 8.229 = +171,7%
        S        = 1 + 1,717 = 2,717

    Artinya: volume bulan Iduladha = 2,717 kali volume bulan biasa.
    S dibulatkan 3 desimal sesuai nilai yang dipakai di dokumen.
    """
    lonjakan = (saat - sebelum) / sebelum
    return round(1 + lonjakan, 3)


def tentukan_indeks_iduladha(horizon):
    """
    Mencari nomor bulan (t) yang bertepatan dengan Iduladha:
        Juni 2023 -> t = 6,  Juni 2024 -> t = 18,  Juni 2025 -> t = 30
    """
    is_iduladha = horizon.apply(lambda r: r["Bulan"] == BULAN_IDULADHA[r["Tahun"]], axis=1)
    return set(horizon.loc[is_iduladha, "t"].astype(int))


def sisipkan_musiman(volume_bulanan, koefisien_s, indeks_iduladha):
    """
    Percabangan if-else untuk setiap bulan:

        JIKA t adalah bulan Iduladha (6, 18, 30) : Volume Musim = Volume Tren x 2,717
        SELAIN ITU (bulan biasa)                 : Volume Musim = Volume Tren x 1

    Contoh dokumen: t = 6 -> 868,20 x 2,717 = 2.358,90 kg
    (Di dokumen hasil ini disebut "Volume Akhir"; di program dinamai Volume_Musim_Kg
    karena volume akhir yang sebenarnya baru terbentuk setelah white noise di Tahap 6.)
    """
    koefisien, volume_musim = [], []
    for _, b in volume_bulanan.iterrows():
        if int(b["t"]) in indeks_iduladha:          # cabang 1: bulan Iduladha
            s = koefisien_s
        else:                                       # cabang 2: bulan biasa
            s = 1.0
        koefisien.append(s)
        volume_musim.append(round(b["Volume_Tren_Kg"] * s, 2))
    df = volume_bulanan.copy()
    df["Koefisien_Musim"] = koefisien
    df["Volume_Musim_Kg"] = volume_musim
    return df


# #############################################################################
#                    BAGIAN I - TAHAP 6: PENAMBAHAN WHITE NOISE
# #############################################################################

def tambah_white_noise(volume_bulanan, sigma_persen):
    """
    Menambahkan galat acak (white noise) berdistribusi normal ke setiap bulan:

        sigma_t        = 0,05 x Volume_t            (5% dari volume bulan t)
        epsilon_t      ~ N(0, sigma_t^2)            (rata-rata 0, simpangan baku sigma_t)
        Volume Akhir_t = Volume_t + epsilon_t

    Volume_t di sini = Volume_Musim_Kg (hasil Tahap 4).
    Contoh: Volume_t = 873 kg -> sigma = 43,65 kg. Sekitar 68% bulan akan
    bergeser kurang dari +-43,65 kg. Noise kecil ini membuat grafik terlihat
    alami tanpa merusak tren (Tahap 3) dan puncak Iduladha (Tahap 4).
    """
    df = volume_bulanan.copy()
    df["Sigma_Noise"] = (sigma_persen * df["Volume_Musim_Kg"]).round(2)          # sigma_t
    df["Noise_Kg"] = [round(rng.normal(0, s), 2) for s in df["Sigma_Noise"]]     # epsilon_t
    # Volume akhir = Volume_t + epsilon_t ; clip menjaga volume tidak pernah negatif
    df["Volume_Akhir_Kg"] = (df["Volume_Musim_Kg"] + df["Noise_Kg"]).clip(lower=0.01).round(2)
    return df


# #############################################################################
#       BAGIAN J - TAHAP 2 / LANGKAH 5 & 7: PEMECAHAN MENJADI TRANSAKSI
# #############################################################################

def undi_jenis_produk(peluang):
    """
    Langkah 5 - undian multinomial: memilih SATU jenis produk dengan peluang
    sesuai rasio BPS. Contoh 2024:
        Daging Murni 49,59% | Karkas 37,30% | Jeroan 10,30% | Daging Variasi 2,81%
    """
    return PRODUK[rng.choice(len(PRODUK), p=peluang)]


def pecah_menjadi_transaksi(volume_bulanan, baseline):
    """
    Langkah 7 - memecah volume akhir setiap bulan menjadi struk-struk transaksi.

    Algoritma perulangan untuk setiap bulan:
      1. akumulasi = 0 ; target = Volume_Akhir_Kg bulan itu
      2. ULANGI selama akumulasi < target:
           a. undi berat struk         ~ Uniform(5 kg, 35 kg)
           b. jika akumulasi + berat melebihi target -> berat = target - akumulasi
              (struk terakhir dipotong supaya total PAS sama dengan target)
           c. undi jenis produk        (Langkah 5)
           d. undi tanggal transaksi   (hari acak di bulan itu)
           e. akumulasi = akumulasi + berat
      3. berhenti ketika akumulasi = target
    """
    transaksi = []
    for _, bln in volume_bulanan.iterrows():
        b = baseline.loc[baseline["Tahun"] == bln["Tahun"]].iloc[0]
        peluang = [b[f"Rasio_{p}"] for p in PRODUK]          # rasio BPS tahun berjalan
        target = bln["Volume_Akhir_Kg"]
        akumulasi = 0.0                                                            # (1)
        hari_dlm_bulan = bln["Periode"].days_in_month

        while akumulasi < target - 1e-9:                                           # (2)
            berat = round(rng.uniform(BERAT_PESANAN_MIN, BERAT_PESANAN_MAKS), 2)   # (a)
            if akumulasi + berat > target:                                         # (b)
                berat = round(target - akumulasi, 2)
            if berat <= 0:
                break
            produk = undi_jenis_produk(peluang)                                    # (c)
            tanggal = bln["Periode"] + pd.Timedelta(days=int(rng.integers(0, hari_dlm_bulan)))  # (d)
            transaksi.append({"t": bln["t"], "Tanggal_Transaksi": tanggal,
                              "Jenis_Produk": produk, "Kuantitas_Kg": berat})
            akumulasi = round(akumulasi + berat, 2)                                # (e)

    # urutkan menurut tanggal, lalu beri nomor transaksi TRX000001, TRX000002, ...
    df = pd.DataFrame(transaksi).sort_values("Tanggal_Transaksi", kind="stable").reset_index(drop=True)
    df.insert(0, "ID_Transaksi", [f"TRX{i:06d}" for i in range(1, len(df) + 1)])
    return df


# #############################################################################
#          BAGIAN K - TAHAP 5: VARIABEL EKSOGEN (HARGA & JUMLAH PESANAN)
# #############################################################################

def undi_harga_normal(produk):
    """
    Harga dasar per kg untuk satu transaksi (base price):

        P_normal = Uniform(P_min, P_max)   sesuai jenis produk

        Daging Murni  : Uniform(180.000, 220.000)
        Karkas        : Uniform(120.000, 145.000)
        Daging Variasi: Uniform(140.000, 170.000)

    Hasil dibulatkan ke kelipatan Rp 500 (contoh: 125.500, 138.000).
    """
    p_min, p_max = RENTANG_HARGA[produk]
    harga = rng.uniform(p_min, p_max)
    return round(harga / PEMBULATAN_HARGA) * PEMBULATAN_HARGA


def buat_harga_jual(transaksi, indeks_iduladha):
    """
    Menentukan harga akhir dan pendapatan setiap transaksi (percabangan if-else):

        JIKA t bulan Iduladha : P_final = P_normal + Uniform(10.000, 15.000)
        SELAIN ITU            : P_final = P_normal

        Total Pendapatan = Kuantitas (kg) x P_final

    Contoh dokumen:
        t = 5 : Karkas 15,5 kg x Rp 125.500                     = Rp 1.945.250
        t = 6 : Karkas 15,5 kg x (Rp 138.000 + Rp 12.000)       = Rp 2.325.000
    """
    harga_normal, markup, harga_final, pendapatan = [], [], [], []
    for _, trx in transaksi.iterrows():
        p_normal = undi_harga_normal(trx["Jenis_Produk"])
        if int(trx["t"]) in indeks_iduladha:            # cabang 1: bulan Iduladha
            delta_p = round(rng.uniform(*MARKUP_IDULADHA) / PEMBULATAN_HARGA) * PEMBULATAN_HARGA
        else:                                           # cabang 2: bulan biasa
            delta_p = 0
        p_final = p_normal + delta_p
        harga_normal.append(float(p_normal))
        markup.append(float(delta_p))
        harga_final.append(float(p_final))
        pendapatan.append(round(trx["Kuantitas_Kg"] * p_final, 2))

    df = transaksi.copy()
    df["Harga_Normal"] = harga_normal
    df["Markup_Musiman"] = markup
    df["Harga_Final"] = harga_final
    df["Total_Pendapatan"] = pendapatan
    return df


def rekap_eksogen_bulanan(transaksi):
    """
    Meringkas transaksi menjadi variabel eksogen per bulan (untuk ARIMAX):

        Jumlah_Pesanan     = banyaknya struk pada bulan t
        Total_Pendapatan   = jumlah pendapatan semua struk bulan t
        Harga_Rata2_Per_Kg = Total_Pendapatan / Total kg    (rata-rata tertimbang volume)
    """
    rekap = transaksi.groupby("t").agg(
        Jumlah_Pesanan=("ID_Transaksi", "count"),
        Total_Kg=("Kuantitas_Kg", "sum"),
        Total_Pendapatan=("Total_Pendapatan", "sum"),
    )
    rekap["Harga_Rata2_Per_Kg"] = (rekap["Total_Pendapatan"] / rekap["Total_Kg"]).round(0)
    rekap["Total_Pendapatan"] = rekap["Total_Pendapatan"].round(0)
    return rekap


# #############################################################################
#                 BAGIAN L - TAHAP 7: KOMPILASI & EKSPOR DATA
# #############################################################################

def kompilasi_dataset(volume):
    """
    Menggabungkan variabel waktu, target permintaan, dan variabel eksogen
    menjadi satu tabel rapi (36 baris x 7 kolom) yang siap dimodelkan:

        Periode            : tanggal awal bulan (indeks waktu untuk SARIMAX)
        t, Tahun, Bulan    : variabel waktu
        Permintaan_Kg      : variabel TARGET (y) = Volume_Akhir_Kg hasil Tahap 6
        Harga_Rata2_Per_Kg : variabel eksogen 1 (X1) dari Tahap 5
        Jumlah_Pesanan     : variabel eksogen 2 (X2) dari Tahap 5
    """
    dataset = pd.DataFrame({
        "Periode": volume["Periode"].dt.strftime("%Y-%m-%d"),
        "t": volume["t"].astype(int),
        "Tahun": volume["Tahun"].astype(int),
        "Bulan": volume["Bulan"].astype(int),
        "Permintaan_Kg": volume["Volume_Akhir_Kg"],
        "Harga_Rata2_Per_Kg": volume["Harga_Rata2_Per_Kg"],
        "Jumlah_Pesanan": volume["Jumlah_Pesanan"].astype(int),
    })
    return dataset


def ekspor_csv(dataset, volume, transaksi, baseline):
    """
    Menyimpan semua tabel ke folder data/ dalam format .csv
    (pemisah koma, desimal titik -> format standar yang dibaca pandas).
    Mengembalikan daftar (nama file, keterangan, tabel) untuk ditampilkan.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    daftar = [
        ("dataset_sarimax.csv",     "Dataset utama 36 bulan (ADF & SARIMAX)", dataset),
        ("volume_bulanan.csv",      "Semua kolom per bulan Tahap 1-6",         volume),
        ("transaksi_penjualan.csv", "Rincian struk transaksi + harga",         transaksi),
        ("baseline_bps.csv",        "Baseline & rasio produk per tahun",        baseline),
    ]
    file_terkunci = []
    for nama, _, tabel in daftar:
        try:
            tabel.to_csv(DATA_DIR / nama, index=False)
        except PermissionError:
            # Windows mengunci file yang sedang dibuka (misalnya di Excel),
            # sehingga Python tidak bisa menimpanya.
            file_terkunci.append(nama)

    if file_terkunci:
        print("\n  [GAGAL MENYIMPAN] File berikut sedang dibuka di program lain (misalnya Excel):")
        for nama in file_terkunci:
            print(f"     - {DATA_DIR / nama}")
        print("  Tutup file tersebut, lalu jalankan ulang:  python 03_generate_data.py\n")
        raise SystemExit(1)
    return daftar


def validasi_dataset(transaksi):
    """
    Membaca ulang dataset_sarimax.csv dengan pandas (seperti di tahap analisis nanti)
    dan memeriksa apakah datanya layak masuk ke uji ADF dan pemodelan SARIMAX.
    Mengembalikan list (nama pemeriksaan, lolos True/False, keterangan).
    """
    df = pd.read_csv(DATA_DIR / "dataset_sarimax.csv", parse_dates=["Periode"])
    selisih_bulan = df["Periode"].dt.to_period("M").astype(int).diff().dropna()
    total_dataset = df["Permintaan_Kg"].sum()
    total_transaksi = transaksi["Kuantitas_Kg"].sum()
    return [
        ("Jumlah observasi = 36 bulan", len(df) == 36, f"{len(df)} baris"),
        ("Tidak ada nilai kosong (missing)", df.isna().sum().sum() == 0, f"{df.isna().sum().sum()} sel kosong"),
        ("Periode berurutan tiap bulan", (selisih_bulan == 1).all(),
         f"{bulan_tahun(df['Periode'].min())} - {bulan_tahun(df['Periode'].max())}"),
        ("Permintaan selalu positif", (df["Permintaan_Kg"] > 0).all(),
         f"min {angka(df['Permintaan_Kg'].min())} kg"),
        ("Total kg dataset = total kg transaksi", abs(total_dataset - total_transaksi) < 0.5,
         f"{angka(total_dataset)} kg"),
        ("Kolom numerik terbaca sebagai angka",
         all(pd.api.types.is_numeric_dtype(df[k]) for k in ["Permintaan_Kg", "Harga_Rata2_Per_Kg", "Jumlah_Pesanan"]),
         "Permintaan, Harga, Pesanan"),
    ]


# #############################################################################
#                          BAGIAN M - PROGRAM UTAMA
# #############################################################################

def main():
    penjelasan.mulai("03_generate_data")
    # =========================================================================
    # TAHAP 1 - TIME HORIZON
    # =========================================================================
    horizon = buat_time_horizon(TAHUN_DATA)
    judul_tahap("TAHAP 1  -  PENENTUAN TIME HORIZON")
    print(f"  {len(horizon)} bulan berurutan: t = 1 ({bulan_tahun(horizon['Periode'].iloc[0])}) "
          f"sampai t = {len(horizon)} ({bulan_tahun(horizon['Periode'].iloc[-1])})")

    # =========================================================================
    # TAHAP 2 - BASELINE (Langkah 1-4 dan 6)
    # =========================================================================
    data_bps = {th: baca_bps_wilayah(th, WILAYAH) for th in TAHUN_DATA}   # Langkah 1
    data_bps = lengkapi_komponen_kosong(data_bps)
    baseline = hitung_baseline(data_bps)                                   # Langkah 2-4

    judul_tahap(f"TAHAP 2  -  PEMBENTUKAN BASELINE  (Pasar Lokal Kabupaten {WILAYAH}, k = {persen(K_TOLERANSI, 0)})")
    cetak_tabel(
        ["Tahun", "Karkas Tahunan Kab (kg)", "Karkas Bulanan Kab (kg)", "mu Lokal (kg/bln)",
         "Batas -10% (kg)", "Batas +10% (kg)", "Sumber Rincian"],
        [[b.Tahun, angka(b.Karkas_Tahunan_Kab), angka(b.Karkas_Bulanan_Kab), angka(b.Mu_Lokal),
          angka(b.Mu_Lokal * (1 - K_TOLERANSI)), angka(b.Mu_Lokal * (1 + K_TOLERANSI)),
          "Estimasi*" if b.Diestimasi else "BPS"] for b in baseline.itertuples()],
        rata="rrrrrrl", judul="Langkah 1-3 dan 6: baseline bulanan per tahun")
    print("  * rincian produk 2023 tidak tersedia di BPS, ditaksir dari proporsi 2024-2025")

    cetak_tabel(
        ["Tahun"] + PRODUK,
        [[b["Tahun"]] + [persen(b[f"Rasio_{p}"]) for p in PRODUK] for _, b in baseline.iterrows()],
        judul="Langkah 4: rasio komposisi produk (peluang undian Langkah 5)")

    variasi = hitung_variasi_relatif(PEMOTONGAN_MEI_2024, PEMOTONGAN_JULI_2024)
    print(f"\n  Langkah 6: variasi Mei vs Juli 2024 = |8.229 - 8.011| / 8.120 = {angka(variasi)}%"
          f"  ->  dilebarkan menjadi k = {persen(K_TOLERANSI, 0)} untuk skala pasar lokal")
    volume = buat_volume_bulanan(horizon, baseline)                        # Langkah 6

    # =========================================================================
    # TAHAP 3 - INJEKSI TREN LINIER
    # =========================================================================
    gradien = hitung_gradien_per_tahun(TAHUN_DATA)
    judul_tahap("TAHAP 3  -  INJEKSI TREN LINIER  (Faktor Tren = 1 + m x (t - t_awal_fase))")
    nama_fase = {0: "Stabil", 1: "Kontraksi", 2: "Pemulihan"}
    cetak_tabel(
        ["Tahun", "Fase", "Rentang t", "Growth Nasional", "m per Bulan", "Faktor Awal", "Faktor Akhir"],
        [[g.Tahun, nama_fase[i], f"{g.t_awal_fase + 1}-{g.t_awal_fase + 12}",
          persen(g.Growth_Tahunan, tanda=True), persen(g.m_Bulanan, 4, tanda=True),
          angka(1 + g.m_Bulanan * 1, 4), angka(1 + g.m_Bulanan * 12, 4)]
         for i, g in enumerate(gradien.itertuples())],
        rata="rlrrrrr")
    m3 = gradien["m_Bulanan"].iloc[-1]
    # print(f"  Cek dokumen: 872,18 x (1 + {angka(m3, 6)} x 1)  = {angka(872.18 * (1 + m3))} kg (t = 25)")
    # print(f"               872,18 x (1 + {angka(m3, 6)} x 12) = {angka(872.18 * (1 + m3 * 12))} kg (t = 36)")
    volume = injeksi_tren(volume, gradien)

    # =========================================================================
    # TAHAP 4 - FAKTOR MUSIMAN IDULADHA
    # =========================================================================
    koef_s = hitung_koefisien_musiman(PEMOTONGAN_MEI_2024, PEMOTONGAN_JUNI_2024)
    indeks_iduladha = tentukan_indeks_iduladha(horizon)
    judul_tahap("TAHAP 4  -  PENYISIPAN FAKTOR MUSIMAN IDULADHA")
    print(f"  Lonjakan pemotongan kambing Mei -> Juni 2024 = (22.359 - 8.229) / 8.229 = "
          f"{persen(koef_s - 1, 1, tanda=True)}")
    print(f"  Koefisien musiman S = 1 + {angka(koef_s - 1, 3)} = {angka(koef_s, 3)}")
    print(f"  Bulan Iduladha      : t = {', '.join(str(t) for t in sorted(indeks_iduladha))} (Juni 2023, 2024, 2025)")
    # print(f"  Cek dokumen         : 868,20 x {angka(koef_s, 3)} = {angka(868.20 * koef_s)} kg")
    volume = sisipkan_musiman(volume, koef_s, indeks_iduladha)

    # =========================================================================
    # TAHAP 6 - WHITE NOISE (dijalankan sebelum Langkah 7, lihat docstring atas)
    # =========================================================================
    judul_tahap(f"TAHAP 6  -  PENAMBAHAN WHITE NOISE  (epsilon ~ N(0, sigma^2), sigma = {persen(SIGMA_NOISE, 0)} x Volume)")
    # print(f"  Cek dokumen: sigma = {angka(SIGMA_NOISE)} x 873 = {angka(SIGMA_NOISE * 873)} kg")
    volume = tambah_white_noise(volume, SIGMA_NOISE)

    # Tabel ringkas pembentukan volume dari tahap ke tahap
    cetak_tabel(
        ["t", "Periode", "Tahap 2 Dasar", "x Tren", "Tahap 3 Tren", "x Musim",
         "Tahap 4 Musim", "+ Noise", "Tahap 6 AKHIR"],
        [[b.t, b.Periode.strftime("%Y-%m") + (" *" if b.Koefisien_Musim > 1 else "  "),
          angka(b.Target_Kg), angka(b.Faktor_Tren, 4), angka(b.Volume_Tren_Kg),
          angka(b.Koefisien_Musim, 3), angka(b.Volume_Musim_Kg),
          ("+" if b.Noise_Kg >= 0 else "") + angka(b.Noise_Kg), angka(b.Volume_Akhir_Kg)]
         for b in volume.itertuples()],
        rata="rlrrrrrrr", judul="Pembentukan volume per bulan (kg)   * = bulan Iduladha")

    # =========================================================================
    # TAHAP 2 / LANGKAH 5 & 7 - PEMECAHAN MENJADI TRANSAKSI
    # =========================================================================
    transaksi = pecah_menjadi_transaksi(volume, baseline)

    # =========================================================================
    # TAHAP 5 - VARIABEL EKSOGEN
    # =========================================================================
    judul_tahap("TAHAP 5  -  VARIABEL EKSOGEN: HARGA JUAL & JUMLAH PESANAN")
    cetak_tabel(
        ["Jenis Produk", "Harga Min (Rp/kg)", "Harga Maks (Rp/kg)", "Peluang Rata-rata"],
        [[p, angka(RENTANG_HARGA[p][0], 0), angka(RENTANG_HARGA[p][1], 0),
          persen(baseline[f"Rasio_{p}"].mean())] for p in PRODUK],
        rata="lrrr", judul="Rentang harga normal per jenis produk")
    print(f"  Markup bulan Iduladha (t = 6, 18, 30): + Uniform({angka(MARKUP_IDULADHA[0], 0)}, "
          f"{angka(MARKUP_IDULADHA[1], 0)}) Rp/kg")
    print(f"  Cek dokumen: 15,5 kg x 125.500 = {rupiah(15.5 * 125_500)} | 15,5 kg x 150.000 = {rupiah(15.5 * 150_000)}")

    transaksi = buat_harga_jual(transaksi, indeks_iduladha)
    rekap = rekap_eksogen_bulanan(transaksi)

    # gabungkan rekap bulanan ke tabel volume
    volume["Total_Transaksi_Kg"] = volume["t"].map(rekap["Total_Kg"].round(2))
    volume["Jumlah_Pesanan"] = volume["t"].map(rekap["Jumlah_Pesanan"])
    volume["Harga_Rata2_Per_Kg"] = volume["t"].map(rekap["Harga_Rata2_Per_Kg"])
    volume["Total_Pendapatan"] = volume["t"].map(rekap["Total_Pendapatan"])
    # cek Langkah 7: total kg semua struk bulan itu harus sama dengan volume akhir
    volume["Cocok"] = (volume["Total_Transaksi_Kg"] - volume["Volume_Akhir_Kg"]).abs() < 0.01

    cetak_tabel(
        ["t", "Periode", "Volume Akhir (kg)", "Total Struk (kg)", "Cek", "Jumlah Pesanan",
         "Harga Rata2 (Rp/kg)", "Total Pendapatan (Rp)"],
        [[b.t, b.Periode.strftime("%Y-%m") + (" *" if b.Koefisien_Musim > 1 else "  "),
          angka(b.Volume_Akhir_Kg), angka(b.Total_Transaksi_Kg), "OK" if b.Cocok else "BEDA",
          b.Jumlah_Pesanan, angka(b.Harga_Rata2_Per_Kg, 0), angka(b.Total_Pendapatan, 0)]
         for b in volume.itertuples()],
        rata="rlrrlrrr", judul="Rekap bulanan transaksi & variabel eksogen   * = bulan Iduladha")

    komposisi = transaksi["Jenis_Produk"].value_counts(normalize=True).reindex(PRODUK)
    cetak_tabel(
        ["Jenis Produk", "Jumlah Struk", "Hasil Undian", "Rasio BPS Rata-rata"],
        [[p, int((transaksi["Jenis_Produk"] == p).sum()), persen(komposisi[p]),
          persen(baseline[f"Rasio_{p}"].mean())] for p in PRODUK]
        + [["TOTAL", len(transaksi), "100,00%", "100,00%"]],
        rata="lrrr", judul="Komposisi produk hasil undian (Langkah 5) vs rasio BPS")

    # =========================================================================
    # TAHAP 7 - KOMPILASI & EKSPOR DATA
    # =========================================================================
    penjelasan.jelaskan_03(globals(), baseline, volume, transaksi, gradien, koef_s)

    judul_tahap("TAHAP 7  -  KOMPILASI & EKSPOR DATA (.csv)")
    dataset = kompilasi_dataset(volume)
    daftar_file = ekspor_csv(dataset, volume, transaksi, baseline)

    cetak_tabel(
        ["File", "Isi", "Baris", "Kolom"],
        [[nama, ket, len(tabel), tabel.shape[1]] for nama, ket, tabel in daftar_file],
        rata="llrr", judul=f"File tersimpan di: {DATA_DIR}")

    cetak_tabel(
        list(dataset.columns),
        [[r.Periode, r.t, r.Tahun, r.Bulan, angka(r.Permintaan_Kg), angka(r.Harga_Rata2_Per_Kg, 0),
          r.Jumlah_Pesanan] for r in dataset.head(3).itertuples()]
        + [["...", "...", "...", "...", "...", "...", "..."]]
        + [[r.Periode, r.t, r.Tahun, r.Bulan, angka(r.Permintaan_Kg), angka(r.Harga_Rata2_Per_Kg, 0),
            r.Jumlah_Pesanan] for r in dataset.tail(2).itertuples()],
        rata="lrrrrrr", judul="Cuplikan dataset_sarimax.csv (y = Permintaan_Kg, X = Harga & Pesanan)")

    cetak_tabel(
        ["Pemeriksaan", "Hasil", "Keterangan"],
        [[nama, "LOLOS" if ok else "GAGAL", ket] for nama, ok, ket in validasi_dataset(transaksi)],
        rata="lll", judul="Validasi: dataset dibaca ulang dengan pandas")
    print("\n  Dataset siap masuk tahap pra-pemrosesan, uji ADF, dan pemodelan SARIMAX.\n")


if __name__ == "__main__":
    main()
