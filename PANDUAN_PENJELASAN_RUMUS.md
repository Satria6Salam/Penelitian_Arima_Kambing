# Panduan Penjelasan Rumus di Terminal

Setiap script 03–09 kini menampilkan **CONTOH PERHITUNGAN** rumus memakai data nyata
penelitian, lalu mencocokkannya dengan hasil program (tanda **COCOK ✔**). Bagian diberi
nomor sesuai pertanyaan dosen, misalnya `[5] RUMUS ACF DAN PACF`. Bila perhitungan
diulang berkali-kali, yang ditampilkan hanya perhitungan ke-1.

Output terminal setiap script juga tersimpan otomatis di folder **`log_terminal\`**,
sehingga saat presentasi cukup membuka file .txt-nya (cari teks `[5]`, `[9]`, dst.)
tanpa menjalankan ulang script.

## Peta pertanyaan → script → bagian terminal → pembanding

| No | Pertanyaan dosen | Script | Bagian di terminal / log | Isi contoh perhitungan | File pembanding |
|---|---|---|---|---|---|
| 1 | Generate data pakai rumus apa? | `03_generate_data.py` | `[1] RUMUS GENERATE DATA` (1a–1h) | baseline μ = karkas/12, rasio produk, Uniform(μ ± 10%), tren linier, faktor Iduladha 2,717, white noise 5%, harga & pendapatan transaksi, harga rata-rata bulanan | `data\hasil_generate\volume_bulanan.csv`, `transaksi_penjualan.csv` |
| 2 | Pra-proses data pakai rumus apa? | `04_pra_proses_data.py` | `[2] RUMUS PRA-PROSES DATA` (2a–2c) | agregasi bulanan, interpolasi linier, Q1/Q3/IQR dan batas outlier | `data\olah\dataset_pra_proses_final.csv` |
| 3 | Rumus memecah data? | `06_pemodelan_forecasting.py` | `[3] RUMUS PEMBAGIAN DATA` | n_train = int(36 × 0,75) = 27, n_test = 9 | `data\hasil_06\06_training_set.csv`, `06_testing_set.csv` |
| 4 | Bagaimana mengatasi stasioner? | `05_eksplorasi_data.py` | `[4] STASIONERITAS: UJI ADF DAN DIFFERENCING` | regresi ADF, γ̂, SE, t-ADF = −5,7452, nilai kritis, keputusan; rumus Δy dan Δ₁₂ ln y | `data\eksplorasi\model_config.json` |
| 5 | Rumus ACF dan PACF? | `05_eksplorasi_data.py` | `[5] RUMUS ACF DAN PACF` (5a–5b) | r₁ dan r₁₂ = 0,3876 manual, batas Bartlett, PACF Yule-Walker lag 1, 2, 12 = 0,6007 | `data\eksplorasi\acf_pacf_plot.png` |
| 6 | Bagaimana menetapkan 4 skenario? | `06_pemodelan_forecasting.py` | `[6] PENETAPAN 4 SKENARIO PEMODELAN` | dasar tiap skenario dan jumlah kandidat (8 + 4 + 8 + 8 = 28) | `data\hasil_06\06_hasil_estimasi.csv` |
| 7 | Bagaimana memilih model? | `06` dan `07` | `[7] CARA MEMILIH MODEL` (06) dan bagian TAHAP 7 REKOMENDASI (07) | peringkat AIC per kelompok (d, D), shortlist, aturan model final | `06_perbandingan_aic_bic.csv`, `07_ringkasan_validasi.md` |
| 8 | Bagaimana menghitung AIC dan BIC? | `06_pemodelan_forecasting.py` | `[8] RUMUS AIC DAN BIC` | log-likelihood dari filter Kalman (suku ke-1 dan total), AIC = −2LL + 2k, BIC = −2LL + k·ln n | `data\hasil_06\06_perbandingan_aic_bic.csv` |
| 9 | Ljung-Box, Shapiro-Wilk, Q-Q, rolling origin, MAPE, RMSE, MAE, MSE, R² | `07_validasi_diagnostik_evaluasi.py` | `[9] VALIDASI DIAGNOSTIK & EVALUASI KINERJA` (9a–9f) | Q Ljung-Box lag 6, W Shapiro-Wilk, titik Q-Q pertama, ramalan putaran 1 rolling origin, MAE/MSE/RMSE/MAPE/R², lulus/tidak target | `data\hasil_07\07_diagnostik_residual.csv`, `07_metrik_rolling_origin.csv`, `grafik\07_qq_*.png` |
| 9 (lanjutan) | Ramalan & interval 95% data testing | `08_forecasting_data_testing.py` | `[9] LANJUTAN — RAMALAN MULTI-STEP DATA TESTING` | rumus ramalan h = 1, SE, batas bawah/atas, cakupan interval, MAPE 9 bulan | `data\hasil_08\08_peramalan_testing.csv` |
| 9 (lanjutan) | Ramalan 6 bulan ke depan | `09_peramalan_visualisasi.py` | `[9] LANJUTAN — RAMALAN 6 BULAN KE DEPAN` | ramalan Jan 2026, SE, interval 95%, efek corong | `data\hasil_09\09_peramalan_jan_jun_2026.csv`, `grafik\09_fan_chart.png` |

## Cara menjalankan

Jalankan dari folder proyek, berurutan (setiap script memakai hasil script sebelumnya):

```
python 03_generate_data.py
python 04_pra_proses_data.py
python 05_eksplorasi_data.py
python 06_pemodelan_forecasting.py
python 07_validasi_diagnostik_evaluasi.py
python 08_forecasting_data_testing.py
python 09_peramalan_visualisasi.py
```

Script 06 dan 07 membutuhkan beberapa menit. Untuk sekadar membaca penjelasan,
buka file di `log_terminal\` (misalnya `log_terminal\05_eksplorasi_data.txt`).

## Catatan

- Penjelasan rumus dibuat oleh modul bersama `penjelasan.py`; modul ini hanya menampilkan
  perhitungan dan tidak mengubah data maupun hasil.
- Model dihitung pada skala ln(kg), sehingga log-likelihood, AIC, dan BIC bernilai kecil/negatif;
  ramalan dan metrik dikembalikan ke kg.
- Cadangan script sebelum perubahan ada di `backup_script_sebelum_penjelasan\`.
