# Prediksi Permintaan Daging Kambing di Pasar Lokal Menggunakan ARIMA

**Judul 11** — Prediksi Permintaan Daging Kambing di Pasar Lokal Menggunakan ARIMA (Time Series Analysis).

Tools: **Python** (pandas, statsmodels, matplotlib, scipy) untuk analisis dan pemodelan;
**MS Access** sebagai sumber data dan sistem implementasi output untuk pengguna.

> **Ruang lingkup "pasar lokal":** permintaan daging kambing **Kabupaten Malang secara agregat**,
> dengan produksi daging (BPS) sebagai proksi permintaan. Data **tidak dibagi jumlah UMKM** karena
> jumlahnya tidak diketahui pasti. Rekomendasi disusun dua tingkat: angka kg untuk pemangku
> kepentingan tingkat kabupaten (Dinas, RPH, pemasok), dan angka indeks/persentase untuk UMKM
> dengan skala usaha berapa pun. Lihat `PANDUAN_PRODUSEN_ACCESS.md` bagian D2.

---

## 1. Ringkasan hasil

| | |
|---|---|
| **Data** | 36 bulan (Jan 2023–Des 2025), data sintetis dikalibrasi dari produksi BPS Kabupaten Malang |
| **Model final** | SARIMA(1,0,0)×(1,1,0,12), transformasi log |
| **Alasan dipilih** | Lulus Ljung-Box & Shapiro-Wilk, lebih baik dari seasonal naive, dan **tidak membutuhkan variabel eksogen masa depan** (beda dengan ARIMAX Harga yang MAPE-nya lebih rendah tapi butuh harga bulan yang diramal) |
| **Akurasi** | Rolling origin 6,59% · peramalan testing 9 bulan 6,98% · validasi ekstrapolasi 6 bulan 7,61% — semua di bawah target 15% |
| **Target akurasi** | MAPE < 15%, RMSE/MAE/MSE **relatif terhadap rata-rata permintaan** (RMSE < 10%×ȳ, MAE < 8%×ȳ), R² > 0,70 — model final lulus semua target |
| **Ramalan Jan–Jun 2026** | Bulan biasa ±66.000–71.000 kg; **Juni 177.280 kg** (batas atas 95%: 251.233 kg) |
| **Penyesuaian Iduladha** | Iduladha 2026 jatuh ±27 Mei (bukan Juni seperti 2023–2025); script 13 menggeser puncak ramalan ke **Mei 177.280 kg** tanpa mengubah model |
| **Sistem** | Ramalan 6 bulan dihitung langsung oleh query MS Access (`qry_12_Ramalan_6_Bulan`), hasilnya identik dengan Python (selisih < 0,0000003%), tanpa Python di sisi pengguna |

---

## 2. Kalau hanya ingin MELIHAT hasil (tanpa instal apa pun)

| Ingin melihat | Buka file |
|---|---|
| Daftar semua output (CSV & plot) per tahap | `OUTPUT_LAPORAN.md` |
| Penjelasan rumus + contoh perhitungan | `PANDUAN_PENJELASAN_RUMUS.md` dan folder `log_terminal\` |
| Hasil AIC/BIC | `06_ringkasan_aic_bic.md` |
| Uji diagnostik, rolling origin & target akurasi | `07_ringkasan_validasi.md` |
| Peramalan data testing | `08_ringkasan_forecasting.md` |
| Peramalan Jan–Jun 2026 + fan chart | `09_ringkasan_peramalan.md`, `data\hasil_09\grafik\09_fan_chart.png` |
| Penyesuaian kalender Iduladha (puncak digeser ke Mei) | `13_ringkasan_penyesuaian_iduladha.md`, `data\hasil_13\grafik\13_ramalan_disesuaikan.png` |
| Rekomendasi bisnis (kabupaten + indeks UMKM) | `11_rekomendasi_manajerial.md` |
| Alasan perubahan metode (log, multi-optimizer) | `perbandingan_versi_estimasi.md` |
| Struktur folder data | `data\README.md` |
| Panduan pengguna sistem MS Access | `PANDUAN_PRODUSEN_ACCESS.md` |
| Panduan demo Access saat presentasi | `PANDUAN_PRESENTASI_ACCESS.md` |
| Panduan presentasi forecasting 2026 sampai demo Access | `PANDUAN_PRESENTASI_FORECASTING_ACCESS.md` |
| Pembagian presentasi untuk 2 orang | `PEMBAGIAN_PRESENTASI_2_ORANG.md` |

File `.md` bisa dibuka dengan VS Code (klik kanan → *Open Preview*) atau Notepad.

---

## 3. Setup lingkungan Python (sekali saja)

### Langkah 1 — Install Python (64-bit)
Download Python **3.12+** dari https://www.python.org/downloads/windows/ → *Windows installer (64-bit)*,
centang **"Add python.exe to PATH"** saat instal. Versi yang dipakai saat penelitian: Python 3.13.

### Langkah 2 — Buat virtual environment & install library
Di folder proyek, VS Code → Terminal → New Terminal:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
- Error *"running scripts is disabled"* → jalankan sekali `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`,
  lalu ulangi `Activate.ps1`.
- Di VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → pilih yang `.venv`.

### Langkah 3 — Pastikan driver MS Access ada
Python membaca `.accdb` lewat **driver ODBC Access**; bit driver harus sama dengan bit Python.

| Kondisi | Yang dilakukan |
|---|---|
| MS Office/Access 64-bit terpasang | Biasanya driver sudah ada |
| Belum ada / tidak terdeteksi | Install **Microsoft Access Database Engine 2016 Redistributable** (`accessdatabaseengine_X64.exe`) |
| Office 32-bit, Python 64-bit | Jalankan installer lewat Command Prompt (Admin): `accessdatabaseengine_X64.exe /quiet` |

### Langkah 4 — Cek environment
```powershell
python 01_cek_environment.py
```
Semua baris harus `[OK]`: versi & bit Python, semua library, fungsi statistik (ADF, dekomposisi, SARIMA,
forecast CI 95%, Ljung-Box, Shapiro-Wilk), simpan grafik, dan koneksi ke Access.

---

## 4. Menjalankan ulang pipeline penelitian

Script dijalankan **berurutan** — setiap script memakai hasil script sebelumnya. Setiap script
mencetak contoh perhitungan rumus (tanda **COCOK ✔**) ke terminal, direkam di `log_terminal\`.

| No | Perintah | Fungsi | Waktu |
|---|---|---|---|
| 1 | `python 03_generate_data.py` | Membangkitkan data 36 bulan + transaksi (seed tetap, hasil selalu sama) | < 1 menit |
| 2 | `python 04_pra_proses_data.py` | Agregasi bulanan, interpolasi, cek outlier IQR | detik |
| 3 | `python 05_eksplorasi_data.py` | Dekomposisi, uji ADF, ACF/PACF, kandidat model | detik |
| 4 | `python 06_pemodelan_forecasting.py` | Bagi data 75:25, estimasi 28 kandidat, AIC/BIC per kelompok (d,D) | ±1 menit |
| 5 | `python 07_validasi_diagnostik_evaluasi.py` | Ljung-Box, Shapiro-Wilk, Q-Q, rolling origin, target akurasi relatif, rekomendasi model final | beberapa menit |
| 6 | `python 08_forecasting_data_testing.py` | Ramalan 9 bulan data testing + interval 95% | < 1 menit |
| 7 | `python 09_peramalan_visualisasi.py` | Validasi 6 bulan + ramalan utama Jan–Jun 2026 + fan chart | < 1 menit |
| 8 | `python 10_ekspor_output_laporan.py` | Plot & CSV pelengkap laporan (`data\laporan\`) | < 1 menit |
| 9 | `python 11_implementasi_access.py` | Tulis parameter & query ke Access (`qry_11_*`) | < 1 menit |
| 10 | `python 11_rekomendasi_manajerial.py` | Rekomendasi manajerial: stok kabupaten + indeks UMKM | detik |
| 11 | `python 12_ramalan_6_bulan_access.py` | Pasang query ramalan murni SQL (`qry_12_*`), verifikasi Access vs Python | < 1 menit |
| 12 | `python 13_penyesuaian_iduladha.py` | Post-processing: geser puncak ramalan ke tanggal Iduladha sebenarnya | detik |

Script yang mengakses database Access (butuh driver Access, lihat Langkah 3):
`02_buat_database.py`, `11_implementasi_access.py`, `12_ramalan_6_bulan_access.py`.
Database yang disertakan **sudah berisi** semua tabel dan query, jadi script ini tidak wajib dijalankan ulang.

---

## 5. Memakai sistem peramalan di MS Access

**Kebutuhan:** Microsoft Access (Office/Microsoft 365), atau *Microsoft 365 Access Runtime* untuk
sekadar menjalankan. Untuk script Python yang membaca database, cukup Access Database Engine
dengan bit yang sama dengan Python.

1. Buka `data\db_penjualan_kambing.accdb` → klik **Enable Content** bila muncul pita kuning.
2. Tekan **F11** bila panel kiri (*Navigation Pane*) tidak terlihat.
3. Klik ganda query **`qry_12_Ramalan_6_Bulan`** → ramalan 6 bulan + batas bawah/atas 95%,
   agregat seluruh Kabupaten Malang.
4. Data bulan baru diisi di tabel **`Tbl_Volume_Bulanan`** (Periode = tanggal 1 bulan itu,
   Permintaan_Kg = total kg kabupaten); ramalan otomatis bergeser.
5. UMKM tidak perlu membuka database — cukup memakai indeks dari `PANDUAN_PRODUSEN_ACCESS.md`
   bagian D2 (`data\hasil_11\11_rek_panduan_umkm_2026.csv`).

Panduan lengkap:
- `PANDUAN_PRODUSEN_ACCESS.md` — panduan pengguna (kabupaten & UMKM).
- `PANDUAN_PRESENTASI_ACCESS.md` — demo Access, arti setiap tabel/query, antisipasi pertanyaan.
- `PANDUAN_PRESENTASI_FORECASTING_ACCESS.md` — urutan presentasi hasil forecasting sampai demo Access.

Untuk mencoba-coba (termasuk simulasi input data), pakai salinan database
(`data\db_penjualan_kambing_DEMO.accdb`) agar data asli aman — lihat bagian 0 di
`PANDUAN_PRESENTASI_FORECASTING_ACCESS.md` untuk cara membuatnya.

---

## 6. Struktur folder

```
Penelitian ARIMA Kambing v2/
├── 01…13_*.py               script penelitian (jalankan berurutan, lihat bagian 4)
├── estimasi_model.py        modul bersama: transformasi log, multi-optimizer, target akurasi relatif
├── penjelasan.py            modul contoh perhitungan rumus di terminal
├── koneksi.py               koneksi Python <-> MS Access
├── *_ringkasan_*.md         ringkasan hasil tiap tahap
├── PANDUAN_*.md              panduan (rumus, Access, presentasi, teman)
├── PEMBAGIAN_PRESENTASI_2_ORANG.md
├── requirements.txt          daftar library Python
├── sql/                      query Access (.sql) dan modul VBA cadangan (.bas)
├── log_terminal/              output terminal tiap script (dibuat otomatis)
└── data/
    ├── db_penjualan_kambing.accdb   database MS Access (sistem peramalan)
    ├── sumber_bps/                   data BPS asli
    ├── hasil_generate/               data hasil generate (03)
    ├── olah/                         dataset hasil pra-proses (04)
    ├── eksplorasi/                   ADF, ACF/PACF, model_config (05)
    ├── hasil_06 … hasil_12/          hasil tiap tahap pemodelan & implementasi Access
    ├── hasil_13/                     ramalan yang sudah disesuaikan kalender Iduladha (13)
    └── laporan/                      plot & CSV pelengkap laporan (10)
```

---

## 7. Masalah yang sering muncul

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | Virtual environment belum aktif atau belum `pip install -r requirements.txt` |
| `TypeError ... result_object` | Versi statsmodels terlalu lama; `pip install -U statsmodels` (butuh ≥ 0.15) |
| `Data source name not found` / driver Access | Instal Access Database Engine dengan bit yang sama dengan Python (64-bit) |
| `PermissionError` saat menyimpan CSV | Tutup file CSV yang sedang terbuka di Excel |
| `Could not use ...; file already in use` | Tutup MS Access sebelum menjalankan script yang mengakses database |
| File `transaksi_penjualan.csv` tidak ada | Jalankan `python 03_generate_data.py` (hasil identik karena seed tetap) |
| Huruf aneh di terminal | Pakai terminal VS Code/Windows Terminal (UTF-8) |

---

## 8. Catatan penting

- Data penelitian adalah **data sintetis** yang dikalibrasi dari data produksi tahunan BPS Kabupaten
  Malang (bukan transaksi riil), dan **tidak dibagi jumlah UMKM** karena jumlahnya tidak diketahui
  pasti. Produksi daging dipakai sebagai proksi permintaan.
- Model final dipilih dari model yang **tidak membutuhkan eksogen masa depan** (lihat `07_ringkasan_validasi.md`
  bagian 5); ARIMAX Harga punya MAPE lebih rendah tapi memakai harga aktual periode testing,
  sehingga akurasinya optimistis dan tidak bisa dipakai untuk meramal sungguhan.
- Ramalan 2026 adalah **proyeksi**; akurasi model dibuktikan pada data testing 2025.
- **Iduladha 2026 jatuh ±27 Mei**, sedangkan model dasar menaruh puncak di Juni (meniru pola
  2023–2025 yang seluruhnya jatuh di Juni). Script 13 menyesuaikan ini sebagai *post-processing*
  tanpa mengubah model atau parameter.
- Level ramalan 2026 ±22,8% di bawah 2025 merupakan artefak koefisien musiman (Φ = −0,80) dari
  data yang hanya 3 tahun, bukan tren pasti.
