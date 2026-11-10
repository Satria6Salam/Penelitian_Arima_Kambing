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
| ARIMAX(2, 0, 0) + Harga + Iduladha | 27 | 27 | 0 | 6 | 28.3542 | -44.7084 | 0.0000 | -36.9334 | 0.2031 | 1.0000 | 2.0000 | nm_awal+0.3 | True |
| ARIMAX(2, 0, 0) + Harga | 27 | 27 | 0 | 5 | 26.8078 | -43.6157 | 1.0927 | -37.1365 | 0.0000 | 2.0000 | 1.0000 | nm_awal+0.0 | True |
| ARIMAX(1, 0, 2) + Harga | 27 | 27 | 0 | 6 | 27.7892 | -43.5784 | 1.1300 | -35.8034 | 1.3332 | 3.0000 | 6.0000 | nm_awal+0.3 | True |
| ARIMAX(1, 0, 2) + Harga + Iduladha | 27 | 27 | 0 | 7 | 28.6480 | -43.2960 | 1.4124 | -34.2251 | 2.9114 | 4.0000 | 9.0000 | bfgs | True |
| ARIMAX(2, 0, 1) + Harga + Iduladha | 27 | 27 | 0 | 7 | 28.5402 | -43.0803 | 1.6281 | -34.0094 | 3.1271 | 5.0000 | 10.0000 | nm_awal+0.3 | True |
| ARIMAX(1, 0, 1) + Harga + Iduladha | 27 | 27 | 0 | 6 | 27.5388 | -43.0776 | 1.6308 | -35.3026 | 1.8339 | 6.0000 | 7.0000 | bfgs | True |
| ARIMAX(1, 0, 1) + Harga | 27 | 27 | 0 | 5 | 26.2271 | -42.4543 | 2.2541 | -35.9751 | 1.1614 | 7.0000 | 4.0000 | bfgs | True |
| ARIMAX(1, 0, 0) + Harga + Iduladha | 27 | 27 | 0 | 5 | 26.1898 | -42.3796 | 2.3288 | -35.9004 | 1.2361 | 8.0000 | 5.0000 | bfgs | True |
| ARIMAX(2, 0, 1) + Harga | 27 | 27 | 0 | 6 | 27.1831 | -42.3661 | 2.3423 | -34.5911 | 2.5454 | 9.0000 | 8.0000 | powell | True |
| ARIMAX(1, 0, 0) + Harga | 27 | 27 | 0 | 4 | 24.6046 | -41.2091 | 3.4993 | -36.0258 | 1.1107 | 10.0000 | 3.0000 | bfgs | True |
| ARIMAX(0, 0, 2) + Harga + Iduladha | 27 | 27 | 0 | 6 | 24.0194 | -36.0388 | 8.6696 | -28.2638 | 8.8728 | 11.0000 | 11.0000 | nm_awal+0.0 | True |
| ARIMAX(0, 0, 2) + Harga | 27 | 27 | 0 | 5 | 21.4379 | -32.8757 | 11.8327 | -26.3965 | 10.7400 | 12.0000 | 12.0000 | bfgs | True |
| ARIMAX(0, 0, 1) + Harga | 27 | 27 | 0 | 4 | 16.9959 | -25.9918 | 18.7166 | -20.8085 | 16.3281 | 13.0000 | 13.0000 | bfgs | True |
| ARIMAX(0, 0, 1) + Harga + Iduladha | 27 | 27 | 0 | 5 | 17.1738 | -24.3476 | 20.3608 | -17.8684 | 19.2681 | 14.0000 | 14.0000 | bfgs | True |
| ARIMAX(0, 0, 0) + Harga | 27 | 27 | 0 | 3 | 10.7284 | -15.4568 | 29.2516 | -11.5693 | 25.5672 | 15.0000 | 15.0000 | bfgs | True |
| ARIMAX(0, 0, 0) + Harga + Iduladha | 27 | 27 | 0 | 4 | 10.8312 | -13.6623 | 31.0461 | -8.4790 | 28.6575 | 16.0000 | 16.0000 | bfgs | True |
| SARIMA(1, 0, 0)x(1, 0, 0, 12) | 27 | 27 | 0 | 4 | 1.7372 | 4.5257 | 49.2341 | 9.7090 | 46.8456 | 17.0000 | 17.0000 | bfgs | True |
| SARIMA(0, 0, 1)x(0, 0, 1, 12) | 27 | 27 | 0 | 4 | -3.4295 | 14.8590 | 59.5674 | 20.0423 | 57.1788 | 18.0000 | 18.0000 | nm_awal+0.3 | True |
| ARIMA(0, 0, 0) | 27 | 27 | 0 | 2 | -6.9815 | 17.9630 | 62.6714 | 20.5546 | 57.6912 | 19.0000 | 19.0000 | powell | True |
| ARIMA(1, 0, 0) | 27 | 27 | 0 | 3 | -6.6138 | 19.2276 | 63.9360 | 23.1151 | 60.2516 | 20.0000 | 20.0000 | bfgs | True |
| ARIMA(0, 0, 1) | 27 | 27 | 0 | 3 | -6.7144 | 19.4287 | 64.1371 | 23.3162 | 60.4527 | 21.0000 | 21.0000 | powell | True |
| ARIMA(1, 0, 1) | 27 | 27 | 0 | 4 | -5.9398 | 19.8797 | 64.5881 | 25.0630 | 62.1995 | 22.0000 | 22.0000 | bfgs | True |
| ARIMA(2, 0, 0) | 27 | 27 | 0 | 4 | -6.1244 | 20.2487 | 64.9571 | 25.4321 | 62.5686 | 23.0000 | 23.0000 | nm | True |
| ARIMA(0, 0, 2) | 27 | 27 | 0 | 4 | -6.2817 | 20.5634 | 65.2718 | 25.7468 | 62.8833 | 24.0000 | 24.0000 | bfgs | True |
| ARIMA(2, 0, 1) | 27 | 27 | 0 | 5 | -5.8603 | 21.7207 | 66.4291 | 28.1999 | 65.3364 | 25.0000 | 25.0000 | nm | True |
| ARIMA(1, 0, 2) | 27 | 27 | 0 | 5 | -5.8605 | 21.7209 | 66.4293 | 28.2001 | 65.3366 | 26.0000 | 26.0000 | nm_awal+0.3 | True |

## Kelompok d=0, D=1 (2 model)

| Nama_Model | nobs | nobs_effective | loglikelihood_burn | Jumlah_Parameter | Log_Likelihood | AIC | Delta_AIC_Kelompok | BIC | Delta_BIC_Kelompok | Rank_AIC_Kelompok | Rank_BIC_Kelompok | Optimizer_Terpilih | Konvergen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SARIMA(1, 0, 0)x(1, 1, 0, 12) | 27 | 15 | 12 | 3 | 9.2738 | -12.5475 | 0.0000 | -10.4234 | 0.0000 | 1.0000 | 1.0000 | nm_awal+0.3 | True |
| SARIMA(0, 0, 1)x(0, 1, 1, 12) | 27 | 15 | 12 | 3 | 0.6424 | 4.7151 | 17.2627 | 6.8393 | 17.2627 | 2.0000 | 2.0000 | nm_awal+0.3 | True |

## Pengecekan model bersarang

142 pasangan model bersarang diperiksa; pelanggaran (LogL model kompleks < model sederhana − 0.001): **0**. Detail: `data/hasil_06/06_cek_model_bersarang.csv`.

## Model gagal, tidak konvergen, atau dengan peringatan

| Nama_Model | Status | Peringatan_Observasi | Warning | Penyebab_Gagal |
|---|---|---|---|---|
| ARIMAX(2, 0, 0) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(2, 0, 0) + Harga | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(1, 0, 2) + Harga | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(1, 0, 2) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 7 parameter | - | - |
| ARIMAX(2, 0, 1) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 7 parameter | - | - |
| ARIMAX(1, 0, 1) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(1, 0, 1) + Harga | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(1, 0, 0) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(2, 0, 1) + Harga | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(1, 0, 0) + Harga | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMAX(0, 0, 2) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 6 parameter | - | - |
| ARIMAX(0, 0, 2) + Harga | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(0, 0, 1) + Harga | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMAX(0, 0, 1) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMAX(0, 0, 0) + Harga | Berhasil | nobs_effective 27 < 10 x 3 parameter | - | - |
| ARIMAX(0, 0, 0) + Harga + Iduladha | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| SARIMA(1, 0, 0)x(1, 0, 0, 12) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| SARIMA(0, 0, 1)x(0, 0, 1, 12) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMA(1, 0, 0) | Berhasil | nobs_effective 27 < 10 x 3 parameter | - | - |
| ARIMA(0, 0, 1) | Berhasil | nobs_effective 27 < 10 x 3 parameter | - | - |
| ARIMA(1, 0, 1) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMA(2, 0, 0) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMA(0, 0, 2) | Berhasil | nobs_effective 27 < 10 x 4 parameter | - | - |
| ARIMA(2, 0, 1) | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| ARIMA(1, 0, 2) | Berhasil | nobs_effective 27 < 10 x 5 parameter | - | - |
| SARIMA(1, 0, 0)x(1, 1, 0, 12) | Berhasil | nobs_effective 15 < 20; nobs_effective 15 < 10 x 3 parameter | - | - |
| SARIMA(0, 0, 1)x(0, 1, 1, 12) | Berhasil | nobs_effective 15 < 20; nobs_effective 15 < 10 x 3 parameter | - | - |

## Tahap berikutnya

Diagnostik residual, uji Ljung–Box, dan evaluasi data testing (script 07); peramalan data testing Apr–Des 2025 (script 08).
