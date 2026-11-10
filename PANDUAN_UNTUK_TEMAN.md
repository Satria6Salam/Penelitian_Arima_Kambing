# Panduan Proyek: Prediksi Permintaan Daging Kambing (ARIMA/SARIMA/ARIMAX)

Panduan ini untuk siapa pun yang menerima folder proyek ini dan ingin **melihat hasil**,
**menjalankan ulang program**, atau **memakai sistem peramalan di MS Access**.

---

## 1. Gambaran singkat

- **Tujuan:** meramal permintaan bulanan daging kambing (kg) di pasar lokal Kabupaten Malang,
  dengan lonjakan besar setiap Iduladha.
- **Data:** 36 bulan (Jan 2023–Des 2025), dibangkitkan dari data produksi BPS (data sintetis).
- **Model final:** SARIMA(1,0,0)x(1,1,0,12) dengan transformasi log.
  - Akurasi data testing: MAPE 6,59% (rolling origin), 6,98% (9 bulan), R² 0,98.
  - Ramalan Jan–Jun 2026: bulan biasa ±66.000–71.000 kg; Juni ±177.280 kg (batas atas 95%: 251.233 kg).
- **Sistem:** ramalan bisa dijalankan langsung di **MS Access** tanpa Python.

---

## 2. Kalau hanya ingin MELIHAT hasil (tanpa instal apa pun)

| Ingin melihat | Buka file |
|---|---|
| Daftar semua output (CSV & plot) per tahap | `OUTPUT_LAPORAN.md` |
| Penjelasan rumus + contoh perhitungan | `PANDUAN_PENJELASAN_RUMUS.md` dan folder `log_terminal\` |
| Hasil AIC/BIC | `06_ringkasan_aic_bic.md` |
| Uji diagnostik & akurasi | `07_ringkasan_validasi.md` |
| Peramalan data testing | `08_ringkasan_forecasting.md` |
| Peramalan Jan–Jun 2026 + fan chart | `09_ringkasan_peramalan.md`, `data\hasil_09\grafik\09_fan_chart.png` |
| Rekomendasi bisnis | `11_rekomendasi_manajerial.md` |
| Alasan perubahan metode (log, multi-optimizer) | `perbandingan_versi_estimasi.md` |
| Struktur folder data | `data\README.md` |
| Pembagian presentasi 2 orang | `PEMBAGIAN_PRESENTASI_2_ORANG.md` |

File `.md` bisa dibuka dengan VS Code (klik kanan → *Open Preview*) atau Notepad.

---

## 3. Kalau ingin MENJALANKAN ulang program Python

### 3.1 Persiapan (sekali saja)
1. Instal **Python 3.11 atau lebih baru, 64-bit** (centang *Add python.exe to PATH*).
2. Buka folder proyek di VS Code → *Terminal → New Terminal*, lalu:
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
   Jika muncul *running scripts is disabled*, jalankan sekali:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, lalu ulangi `Activate.ps1`.
3. Cek lingkungan: `python 01_cek_environment.py`

Versi yang dipakai saat penelitian: Python 3.13, pandas 3.0.5, numpy 2.5.3, statsmodels 0.15.0,
scipy 1.18.1, matplotlib 3.11.2, pyodbc 5.3.0.

### 3.2 Urutan menjalankan script

| No | Perintah | Fungsi | Waktu |
|---|---|---|---|
| 1 | `python 03_generate_data.py` | Membangkitkan data 36 bulan + transaksi (seed tetap, hasil selalu sama) | < 1 menit |
| 2 | `python 04_pra_proses_data.py` | Agregasi bulanan, interpolasi, cek outlier IQR | detik |
| 3 | `python 05_eksplorasi_data.py` | Dekomposisi, uji ADF, ACF/PACF, kandidat model | detik |
| 4 | `python 06_pemodelan_forecasting.py` | Bagi data 75:25, estimasi 28 kandidat, AIC/BIC | ±1 menit |
| 5 | `python 07_validasi_diagnostik_evaluasi.py` | Ljung-Box, Shapiro-Wilk, Q-Q, rolling origin, metrik | beberapa menit |
| 6 | `python 08_forecasting_data_testing.py` | Ramalan 9 bulan data testing + interval 95% | < 1 menit |
| 7 | `python 09_peramalan_visualisasi.py` | Ramalan Jan–Jun 2026 + fan chart | < 1 menit |
| 8 | `python 10_ekspor_output_laporan.py` | Plot & CSV pelengkap laporan (folder `data\laporan`) | < 1 menit |
| 9 | `python 11_rekomendasi_manajerial.py` | Rekomendasi manajerial berbasis angka hasil | detik |

Script harus dijalankan **berurutan** karena setiap script memakai hasil script sebelumnya.
Setiap script menampilkan contoh perhitungan rumus (tanda **COCOK ✔**) dan menyimpan
output terminal ke `log_terminal\`.

Script yang menulis ke database Access (perlu driver Access, lihat bagian 4):
`02_buat_database.py`, `11_implementasi_access.py`, `12_ramalan_6_bulan_access.py`.
Database yang dikirim **sudah berisi** semua tabel dan query, jadi script ini tidak wajib dijalankan.

---

## 4. Memakai sistem peramalan di MS Access

**Kebutuhan:** Microsoft Access (Office/Microsoft 365). Untuk script Python yang membaca database,
cukup *Microsoft Access Database Engine 2016 Redistributable* dengan bit yang sama dengan Python.

1. Buka `data\db_penjualan_kambing.accdb` → klik **Enable Content** bila muncul.
2. Tekan **F11** bila panel kiri tidak terlihat.
3. Klik ganda query **`qry_12_Ramalan_6_Bulan`** → ramalan 6 bulan + batas bawah/atas 95%.
4. Data bulan baru diisi di tabel **`Tbl_Volume_Bulanan`** (Periode = tanggal 1 bulan itu,
   Permintaan_Kg = total kg terjual); ramalan otomatis bergeser.

Panduan lengkap: `PANDUAN_PRODUSEN_ACCESS.md` (pengguna) dan `PANDUAN_PRESENTASI_ACCESS.md`
(demo, arti setiap tabel dan query). Untuk mencoba-coba, pakai salinan database agar data asli aman.

---

## 5. Struktur folder

```
Penelitian ARIMA Kambing/
├── 01 … 12_*.py            script penelitian (jalankan berurutan, lihat bagian 3)
├── estimasi_model.py       modul bersama: transformasi log + multi-optimizer
├── penjelasan.py           modul contoh perhitungan rumus di terminal
├── koneksi.py              koneksi Python ↔ MS Access
├── *_ringkasan_*.md        ringkasan hasil tiap tahap
├── PANDUAN_*.md            panduan (rumus, Access, presentasi, teman)
├── requirements.txt        daftar library Python
├── sql/                    query Access (.sql) dan modul VBA cadangan (.bas)
├── log_terminal/           output terminal tiap script (dibuat otomatis)
└── data/
    ├── db_penjualan_kambing.accdb   database MS Access (sistem peramalan)
    ├── sumber_bps/                  data BPS asli
    ├── hasil_generate/              data hasil generate (03)
    ├── olah/                        dataset hasil pra-proses (04)
    ├── eksplorasi/                  ADF, ACF/PACF, model_config (05)
    ├── hasil_06 … hasil_12/         hasil tiap tahap
    └── laporan/                     plot & CSV pelengkap laporan (10)
```

---

## 6. Masalah yang sering muncul

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | Virtual environment belum aktif atau belum `pip install -r requirements.txt`. |
| `TypeError ... result_object` | Versi statsmodels terlalu lama; jalankan `pip install -U statsmodels` (butuh ≥ 0.15). |
| `Data source name not found` / driver Access | Instal Access Database Engine dengan bit yang sama dengan Python (64-bit). |
| `PermissionError` saat menyimpan CSV | Tutup file CSV yang sedang terbuka di Excel. |
| `Could not use ...; file already in use` | Tutup MS Access sebelum menjalankan script yang mengakses database. |
| File `transaksi_penjualan.csv` tidak ada | Jalankan `python 03_generate_data.py` (hasil identik karena seed tetap). |
| Huruf aneh di terminal | Pakai terminal VS Code/Windows Terminal (UTF-8). |

---

## 7. Catatan penting

- Data penelitian adalah **data sintetis** yang dikalibrasi dari data tahunan BPS, bukan transaksi riil.
- Ramalan 2026 adalah **proyeksi**; akurasi model dibuktikan pada data testing 2025.
- Iduladha 2026 jatuh ±27 Mei, sedangkan model menaruh puncak di Juni (meniru 2023–2025).
- Level ramalan 2026 ±22,8% di bawah 2025 merupakan artefak model dari data 3 tahun.
