# Ringkasan Script 06: Estimasi Model dan Perbandingan AIC/BIC

Dibuat otomatis oleh `06_pemodelan_forecasting.py` (statsmodels 0.15.0, pandas 3.1.0).

## Pengaturan

- Data training: 27 observasi (Jan 2023 – Mar 2025), target `Total_Kuantitas_Kg`.
- Semua kandidat diestimasi dengan `SARIMAX`, `enforce_stationarity=True`, `enforce_invertibility=True`.
- **Transformasi data:** `log` (target ln(kg), harga ln(Rp/kg), Koefisien_Musim apa adanya); dihitung di dalam script, file data tidak diubah. Alasan: (1) pada skala kg (permintaan ±100.000, varians residual ±1e9) optimizer L-BFGS sering berhenti di optimum lokal dan std error tidak stabil; (2) lonjakan Iduladha bersifat perkalian (×2,717), sehingga residual model level di bulan Juni sangat besar dan tidak normal. Transformasi log mengubah efek perkalian menjadi penjumlahan (sesuai saran dokumen alur bila uji Shapiro-Wilk gagal). Log_Likelihood/AIC/BIC di tabel berskala data transformasi; kolom `*_setara_kg` di CSV sudah dikoreksi Jacobian ke satuan kg. Perbandingan dengan versi skala kg dan ribu kg: `perbandingan_versi_estimasi.md`.
- **Multi-optimizer:** lbfgs, bfgs, powell, nm serta Nelder-Mead dari tiga nilai awal AR/MA (0; +0,3; −0,3); dipilih LogL tertinggi yang konvergen dengan std error valid, lalu di-polish dengan lbfgs (modul `estimasi_model.py`).
- Variabel eksogen ARIMAX: `Harga_Rata2_Per_Kg`.
- Label Iduladha: `Koefisien_Musim` dari `volume_bulanan.csv` (dipakai apa adanya, digabung berdasarkan Periode).
- Peringatan observasi efektif: `nobs_effective < 20` atau `nobs_effective < 10 × jumlah parameter`.
- Peringkat AIC/BIC hanya dalam kelompok (d, D) yang sama. Tidak ada peringkat gabungan dan belum ada model final.

## Kelompok d=0, D=0 (26 model)

| Nama_Model | nobs | nobs_effective | loglikelihood_burn | Jumlah_Parameter | Log_Likelihood | AIC | Delta_AIC_Kelompok | BIC | Delta_BIC_Kelompok | Rank_AIC_Kelompok | Rank_BIC_Kelompok | Optimizer_Terpilih | Konvergen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARIMAX(1, 0, 0) + Harga + Iduladha | 27 | 27 | 0 | 5 | 34.1473 | -58.2946 | 0.0000 | -51.8154 | 0.0000 | 1.0000 | 1.0000 | bfgs | True |
| ARIMAX(2, 0, 0) + Harga + Iduladha | 27 | 27 | 0 | 6 | 34.8704 | -57.7409 | 0.5537 | -49.9659 | 1.8495 | 2.0000 | 4.0000 | warm | True |
| ARIMAX(0, 0, 2) + Harga + Iduladha | 27 | 27 | 0 | 6 | 34.8378 | -57.6755 | 0.6191 | -49.9005 | 1.9149 | 3.0000 | 5.0000 | bfgs | True |
| ARIMAX(1, 0, 1) + Harga + Iduladha | 27 | 27 | 0 | 6 | 34.6447 | -57.2894 | 1.0051 | -49.5144 | 2.3010 | 4.0000 | 6.0000 | bfgs | True |
| ARIMAX(0, 0, 1) + Harga + Iduladha | 27 | 27 | 0 | 5 | 33.2722 | -56.5444 | 1.7502 | -50.0652 | 1.7502 | 5.0000 | 3.0000 | bfgs | True |
| ARIMAX(1, 0, 2) + Harga + Iduladha | 27 | 27 | 0 | 7 | 35.0553 | -56.1105 | 2.1841 | -47.0397 | 4.7757 | 6.0000 | 9.0000 | bfgs | True |
| ARIMAX(0, 0, 0) + Harga + Iduladha | 27 | 27 | 0 | 4 | 31.9658 | -55.9315 | 2.3631 | -50.7482 | 1.0672 | 7.0000 | 2.0000 | bfgs | True |
| ARIMAX(2, 0, 1) + Harga + Iduladha | 27 | 27 | 0 | 7 | 34.8758 | -55.7516 | 2.5429 | -46.6808 | 5.1346 | 8.0000 | 10.0000 | bfgs | True |
| ARIMAX(0, 0, 2) + Harga | 27 | 27 | 0 | 5 | 32.2026 | -54.4052 | 3.8893 | -47.9261 | 3.8893 | 9.0000 | 8.0000 | warm | True |
| ARIMAX(1, 0, 2) + Harga | 27 | 27 | 0 | 6 | 32.2026 | -52.4052 | 5.8893 | -44.6302 | 7.1852 | 10.0000 | 13.0000 | warm | True |
| ARIMAX(0, 0, 0) + Harga | 27 | 27 | 0 | 3 | 29.1476 | -52.2951 | 5.9994 | -48.4076 | 3.4078 | 11.0000 | 7.0000 | bfgs | True |
| ARIMAX(1, 0, 0) + Harga | 27 | 27 | 0 | 4 | 29.6622 | -51.3245 | 6.9701 | -46.1411 | 5.6743 | 12.0000 | 11.0000 | nm_awal+0.0 | True |
| ARIMAX(0, 0, 1) + Harga | 27 | 27 | 0 | 4 | 29.4277 | -50.8554 | 7.4392 | -45.6720 | 6.1434 | 13.0000 | 12.0000 | bfgs | True |
| ARIMAX(1, 0, 1) + Harga | 27 | 27 | 0 | 5 | 30.2955 | -50.5911 | 7.7035 | -44.1119 | 7.7035 | 14.0000 | 14.0000 | bfgs | True |
| ARIMAX(2, 0, 0) + Harga | 27 | 27 | 0 | 5 | 29.6622 | -49.3245 | 8.9701 | -42.8453 | 8.9701 | 15.0000 | 15.0000 | warm | True |
| ARIMAX(2, 0, 1) + Harga | 27 | 27 | 0 | 6 | 30.2955 | -48.5911 | 9.7035 | -40.8160 | 10.9994 | 16.0000 | 16.0000 | warm | True |
| SARIMA(1, 0, 0)x(1, 0, 0, 12) | 27 | 27 | 0 | 4 | 10.4578 | -12.9157 | 45.3789 | -7.7323 | 44.0831 | 17.0000 | 17.0000 | bfgs | True |
| SARIMA(0, 0, 1)x(0, 0, 1, 12) | 27 | 27 | 0 | 4 | 3.7006 | 0.5987 | 58.8933 | 5.7821 | 57.5975 | 18.0000 | 18.0000 | nm | True |
| ARIMA(1, 0, 1) | 27 | 27 | 0 | 4 | -0.4555 | 8.9110 | 67.2056 | 14.0943 | 65.9097 | 19.0000 | 20.0000 | nm_awal+0.3 | True |
| ARIMA(0, 0, 0) | 27 | 27 | 0 | 2 | -2.6454 | 9.2908 | 67.5854 | 11.8824 | 63.6979 | 20.0000 | 19.0000 | lbfgs | True |
| ARIMA(0, 0, 1) | 27 | 27 | 0 | 3 | -2.3590 | 10.7180 | 69.0126 | 14.6055 | 66.4209 | 21.0000 | 21.0000 | powell | True |
| ARIMA(1, 0, 2) | 27 | 27 | 0 | 5 | -0.3712 | 10.7423 | 69.0369 | 17.2215 | 69.0369 | 22.0000 | 24.0000 | nm | True |
| ARIMA(0, 0, 2) | 27 | 27 | 0 | 4 | -1.4114 | 10.8228 | 69.1174 | 16.0061 | 67.8215 | 23.0000 | 23.0000 | nm_awal+0.3 | True |
| ARIMA(1, 0, 0) | 27 | 27 | 0 | 3 | -2.4173 | 10.8346 | 69.1292 | 14.7221 | 66.5375 | 24.0000 | 22.0000 | bfgs | True |
| ARIMA(2, 0, 1) | 27 | 27 | 0 | 5 | -0.5221 | 11.0442 | 69.3388 | 17.5234 | 69.3388 | 25.0000 | 25.0000 | nm | True |
| ARIMA(2, 0, 0) | 27 | 27 | 0 | 4 | -2.3256 | 12.6511 | 70.9457 | 17.8345 | 69.6499 | 26.0000 | 26.0000 | nm | True |

## Kelompok d=0, D=1 (2 model)

| Nama_Model | nobs | nobs_effective | loglikelihood_burn | Jumlah_Parameter | Log_Likelihood | AIC | Delta_AIC_Kelompok | BIC | Delta_BIC_Kelompok | Rank_AIC_Kelompok | Rank_BIC_Kelompok | Optimizer_Terpilih | Konvergen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SARIMA(1, 0, 0)x(1, 1, 0, 12) | 27 | 15 | 12 | 3 | 13.2499 | -20.4999 | 0.0000 | -18.3757 | 0.0000 | 1.0000 | 1.0000 | nm_awal+0.3 | True |
| SARIMA(0, 0, 1)x(0, 1, 1, 12) | 27 | 15 | 12 | 3 | 12.7177 | -19.4354 | 1.0645 | -17.3112 | 1.0645 | 2.0000 | 2.0000 | bfgs | True |

## Pengecekan model bersarang

142 pasangan model bersarang diperiksa; pelanggaran (LogL model kompleks < model sederhana − 0.001): **1**. Detail: `data/hasil_06/06_cek_model_bersarang.csv`.

| Model_Sederhana | Model_Kompleks | LogL_Sederhana | LogL_Kompleks | Selisih_LogL |
|---|---|---|---|---|
| ARIMA(1, 0, 1) | ARIMA(2, 0, 1) | -0.4555 | -0.5221 | -0.0666 |

## Model gagal, tidak konvergen, atau dengan peringatan

| Nama_Model | Status | Peringatan_Observasi | Warning | Penyebab_Gagal |
|---|---|---|---|---|
| ARIMAX(1, 0, 0) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(2, 0, 0) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(0, 0, 2) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(1, 0, 1) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(0, 0, 1) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(1, 0, 2) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 7 parameter | - | - |
| ARIMAX(0, 0, 0) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMAX(2, 0, 1) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 7 parameter | - | - |
| ARIMAX(0, 0, 2) + Harga | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(1, 0, 2) + Harga | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(0, 0, 0) + Harga | Berhasil | nobs_effective 27 < 10 x 3 parameter | - | - |
| ARIMAX(1, 0, 0) + Harga | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMAX(0, 0, 1) + Harga | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMAX(1, 0, 1) + Harga | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(2, 0, 0) + Harga | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(2, 0, 1) + Harga | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| SARIMA(1, 0, 0)x(1, 0, 0, 12) | Berhasil | nobs_effective 27 < 10 x 4 parameter | EstimationWarning: Non-stationary starting seasonal autoregressive Using zeros as starting parameters. | - |
| SARIMA(0, 0, 1)x(0, 0, 1, 12) | Berhasil | nobs_effective 27 < 10 x 4 parameter | EstimationWarning: Too few observations to estimate starting parameters for seasonal ARMA. All parameters except for variances will be set to zeros. | - |
| ARIMA(1, 0, 1) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMA(0, 0, 1) | Berhasil | nobs_effective 27 < 10 x 3 parameter | - | - |
| ARIMA(1, 0, 2) | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMA(0, 0, 2) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMA(1, 0, 0) | Berhasil | nobs_effective 27 < 10 x 3 parameter | - | - |
| ARIMA(2, 0, 1) | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMA(2, 0, 0) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| SARIMA(1, 0, 0)x(1, 1, 0, 12) | Berhasil | nobs_effective 15 < 20; nobs_effective 15 < 10 x 3 parameter | - | - |
| SARIMA(0, 0, 1)x(0, 1, 1, 12) | Berhasil | nobs_effective 15 < 20; nobs_effective 15 < 10 x 3 parameter | EstimationWarning: Too few observations to estimate starting parameters for seasonal ARMA. All parameters except for variances will be set to zeros. | - |

## Tahap berikutnya

Diagnostik residual, uji Ljung–Box, dan evaluasi data testing (script 07); peramalan data testing Apr–Des 2025 (script 08).
