"""
=============================================================================
PROGRAM PRA-PEMROSESAN DATA (DATA PREPROCESSING & TRANSFORMATION)
File: 04_pra_proses_data.py
Tahap 1: Agregasi Data Harian ke Bulanan (GROUP BY MONTH)
Tahap 2: Penyelarasan Indeks Waktu & Imputasi Interpolasi Linier
Tahap 3: Pembersihan Anomali (Outlier) dengan Interquartile Range (IQR) & Filter Musiman
=============================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path

import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/

# =============================================================================
# PENGATURAN PATH DIREKTORI
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INPUT_FILE = DATA_DIR / "hasil_generate" / "transaksi_penjualan.csv"
OUTPUT_DIR = DATA_DIR / "olah"
OUTPUT_FILE = OUTPUT_DIR / "dataset_pra_proses_final.csv"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# FUNGSI 1: MEMUAT DATA MENTAH
# =============================================================================
def muat_data_transaksi(filepath):
    print(f"-> Memuat data transaksi dari: {filepath.name}")
    df = pd.read_csv(filepath)
    df['Tanggal_Transaksi'] = pd.to_datetime(df['Tanggal_Transaksi'])
    return df


# =============================================================================
# FUNGSI 2: AGREGASI BULANAN (GROUP BY MONTH) - TAHAP 1
# =============================================================================
def agregasi_bulanan(df):
    print("\n-> Mengeksekusi Pra-Pemrosesan Tahap 1: Agregasi Bulanan...")
    df['Periode_Bulan'] = df['Tanggal_Transaksi'].dt.to_period('M')
    
    df_agregasi = df.groupby('Periode_Bulan').agg(
        Total_Kuantitas_Kg=('Kuantitas_Kg', 'sum'),
        Harga_Rata2_Per_Kg=('Harga_Final', 'mean'),
        Jumlah_Transaksi=('ID_Transaksi', 'count')
    ).reset_index()
    
    df_agregasi['Periode'] = df_agregasi['Periode_Bulan'].dt.to_timestamp()
    df_agregasi['Total_Kuantitas_Kg'] = df_agregasi['Total_Kuantitas_Kg'].round(2)
    df_agregasi['Harga_Rata2_Per_Kg'] = df_agregasi['Harga_Rata2_Per_Kg'].round(0)
    
    return df_agregasi[['Periode', 'Jumlah_Transaksi', 'Total_Kuantitas_Kg', 'Harga_Rata2_Per_Kg']]


# =============================================================================
# FUNGSI 3: PENYELARASAN INDEKS WAKTU & INTERPOLASI LINIER - TAHAP 2
# =============================================================================
def selaraskan_indeks_waktu(df):
    print("\n-> Mengeksekusi Pra-Pemrosesan Tahap 2: Penyelarasan & Interpolasi Linier...")
    df = df.set_index('Periode')
    
    idx_sempurna = pd.date_range(start=df.index.min(), end=df.index.max(), freq='MS')
    df_selaras = df.reindex(idx_sempurna)
    
    jumlah_kosong = df_selaras.isnull().sum().sum()
    if jumlah_kosong > 0:
        print(f"   [INFO] Terdeteksi {jumlah_kosong} sel data kosong. Melakukan interpolasi...")
        df_selaras = df_selaras.interpolate(method='linear')
        df_selaras['Total_Kuantitas_Kg'] = df_selaras['Total_Kuantitas_Kg'].round(2)
        df_selaras['Harga_Rata2_Per_Kg'] = df_selaras['Harga_Rata2_Per_Kg'].round(0)
        df_selaras['Jumlah_Transaksi'] = df_selaras['Jumlah_Transaksi'].round(0).astype(int)
    else:
        print("   [INFO] Indeks waktu sudah rapat. Tidak ada data yang perlu diinterpolasi.")
        df_selaras['Jumlah_Transaksi'] = df_selaras['Jumlah_Transaksi'].astype(int)
        
    return df_selaras.reset_index().rename(columns={'index': 'Periode'})


# =============================================================================
# FUNGSI 4: PEMBERSIHAN OUTLIER METODE IQR DENGAN FILTER MUSIMAN - TAHAP 3
# =============================================================================
def bersihkan_outlier_iqr(df, kolom='Total_Kuantitas_Kg'):
    print(f"\n-> Mengeksekusi Pra-Pemrosesan Tahap 3: Pembersihan Outlier IQR pada '{kolom}'...")
    
    # 1. Menghitung Kuartil dan IQR
    Q1 = df[kolom].quantile(0.25)
    Q3 = df[kolom].quantile(0.75)
    IQR = Q3 - Q1
    
    # 2. Menghitung Batas Matematis
    batas_bawah = Q1 - (1.5 * IQR)
    batas_atas = Q3 + (1.5 * IQR)
    
    print(f"   [MATEMATIKA] Q1: {Q1:.2f}, Q3: {Q3:.2f}, IQR: {IQR:.2f}")
    print(f"   [MATEMATIKA] Batas Bawah: {batas_bawah:.2f}, Batas Atas: {batas_atas:.2f}")
    
    # 3. Deteksi Outlier
    kondisi_outlier = (df[kolom] < batas_bawah) | (df[kolom] > batas_atas)
    outlier_terdeteksi = df[kondisi_outlier]
    jumlah_outlier = len(outlier_terdeteksi)
    
    # 4. Penanganan Outlier (Capping bersyarat)
    if jumlah_outlier > 0:
        print(f"   [INFO] Terdeteksi {jumlah_outlier} data melebihi batas (outlier):")
        
        # Iterasi untuk mengecek dan mencetak riwayat tiap outlier
        for index, row in outlier_terdeteksi.iterrows():
            periode = row['Periode']
            nilai = row[kolom]
            
            # Cek apakah ini bulan Iduladha (Juni = Bulan ke-6)
            is_iduladha = (periode.month == 6)
            
            if is_iduladha:
                status = "Periode Iduladha -> DIPERTAHANKAN (Musiman Valid)"
            else:
                if nilai < batas_bawah:
                    status = f"Bukan Iduladha -> DISESUAIKAN ke Batas Bawah ({batas_bawah:.2f})"
                else:
                    status = f"Bukan Iduladha -> DISESUAIKAN ke Batas Atas ({batas_atas:.2f})"
            
            print(f"      - Periode: {periode.strftime('%Y-%m')}, Nilai: {nilai:.2f} kg | Aksi: {status}")

        # Terapkan pemotongan hanya pada data yang bukan bulan ke-6 (Iduladha)
        kondisi_bukan_iduladha = df['Periode'].dt.month != 6
        
        kondisi_potong_bawah = (df[kolom] < batas_bawah) & kondisi_bukan_iduladha
        kondisi_potong_atas = (df[kolom] > batas_atas) & kondisi_bukan_iduladha
        
        df.loc[kondisi_potong_bawah, kolom] = batas_bawah
        df.loc[kondisi_potong_atas, kolom] = batas_atas
        
        df[kolom] = df[kolom].round(2)
        
    else:
        print("   [INFO] Tidak ditemukan anomali. Seluruh data berada dalam rentang normal IQR.")
        
    return df


# =============================================================================
# FUNGSI 5: MENYIMPAN HASIL AKHIR
# =============================================================================
def simpan_hasil_pra_proses(df, filepath):
    print(f"\n-> Menyimpan hasil akhir pra-pemrosesan ke: {filepath.name}")
    df.to_csv(filepath, index=False)
    print("-> SELURUH SIKLUS PRA-PEMROSESAN (TAHAP 1-3) SELESAI.\n")


# =============================================================================
# FUNGSI UTAMA (MAIN)
# =============================================================================
def main():
    penjelasan.mulai("04_pra_proses_data")
    print("=================================================================")
    print("          PROSES PRA-PEMROSESAN DATA & TRANSFORMASI              ")
    print("=================================================================\n")
    
    try:
        # Pemuatan Data
        df_mentah = muat_data_transaksi(INPUT_FILE)
        
        # Tahap 1: Agregasi Bulanan
        df_tahap1 = agregasi_bulanan(df_mentah)
        print("\n[HASIL TAHAP 1] Data Agregasi (5 Baris Pertama):")
        print(df_tahap1.head().to_string(index=False))
        
        # Tahap 2: Penyelarasan Waktu & Interpolasi Linier
        df_tahap2 = selaraskan_indeks_waktu(df_tahap1)
        print("\n[HASIL TAHAP 2] Data Setelah Penyelarasan/Interpolasi (5 Baris Pertama):")
        print(df_tahap2.head().to_string(index=False))
        
        # Tahap 3: Pembersihan Outlier IQR
        df_final = bersihkan_outlier_iqr(df_tahap2, kolom='Total_Kuantitas_Kg')

        # Contoh perhitungan rumus [2]
        penjelasan.jelaskan_04(df_mentah, df_tahap1)
        
        # Ekspor Hasil Akhir
        simpan_hasil_pra_proses(df_final, OUTPUT_FILE)
        
    except FileNotFoundError:
        print(f"\n[ERROR] File {INPUT_FILE.name} tidak ditemukan.")
    except Exception as e:
        print(f"\n[ERROR] Terjadi kesalahan sistem: {e}")

if __name__ == "__main__":
    main()