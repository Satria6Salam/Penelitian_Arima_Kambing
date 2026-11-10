# Ringkasan Script 07: Estimasi Parameter, Validasi Diagnostik, dan Evaluasi Kinerja

Dibuat otomatis oleh `07_validasi_diagnostik_evaluasi.py` (statsmodels 0.15.0). Konfigurasi estimasi sama dengan script 06 (`enforce_stationarity=True`, `enforce_invertibility=True`, modul `estimasi_model.py`).

## Transformasi dan metode estimasi

- Transformasi: `log` (target ln(kg), harga ln(Rp/kg), Koefisien_Musim apa adanya); dihitung di dalam script, file data tidak diubah.
- Alasan: (1) pada skala kg (permintaan ±100.000, varians residual ±1e9) optimizer L-BFGS sering berhenti di optimum lokal dan std error tidak stabil; (2) lonjakan Iduladha bersifat perkalian (×2,717), sehingga residual model level di bulan Juni sangat besar dan seluruh model level gagal Shapiro-Wilk. Transformasi log mengubah efek perkalian menjadi penjumlahan, sesuai saran dokumen alur. Hasil level dan versi lain dirangkum di `perbandingan_versi_estimasi.md`.
- Setiap model di-fit dengan lbfgs, bfgs, powell, nm serta Nelder-Mead dari tiga nilai awal AR/MA (0; +0,3; −0,3). Dipilih LogL tertinggi yang konvergen dengan std error valid, lalu di-polish dengan lbfgs.
- Koefisien, std error, LogL, AIC, BIC, dan residual (bagian 1–3) berskala data transformasi. Prediksi rolling origin dikembalikan ke **kg** (exp dari ramalan log = median ramalan), dan seluruh metrik bagian 4 dalam **kg**.

## 1. Parameter model shortlist

Shortlist = AIC terendah per skenario di dalam kelompok (d, D)-nya. Tabel seluruh 28 kandidat: `data/hasil_07/07_parameter_estimasi.csv`; summary lengkap: `data/hasil_07/07_summary_shortlist.txt`. Satuan: data transformasi `log` (pada model log, koefisien harga = elastisitas permintaan terhadap harga).

| Label | Nama_Model | Parameter | Koefisien | Std_Error | z | P_value | CI95_Bawah | CI95_Atas | Signifikan_5% |
|---|---|---|---|---|---|---|---|---|---|
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | intercept | -4.3955 | 5.7067 | -0.7702 | 0.4412 | -15.5805 | 6.7895 | Tidak |
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | Harga_Rata2_Per_Kg | 4.4901 | 4.3004 | 1.0441 | 0.2964 | -3.9386 | 12.9188 | Tidak |
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | Koefisien_Musim | 0.3243 | 0.2367 | 1.3701 | 0.1707 | -0.1396 | 0.7882 | Tidak |
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | ar.L1 | 0.4829 | 0.1825 | 2.6468 | 0.0081 | 0.1253 | 0.8405 | Ya |
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | ar.L2 | 0.4108 | 0.1885 | 2.1795 | 0.0293 | 0.0414 | 0.7803 | Ya |
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | sigma2 | 0.0068 | 0.0029 | 2.3363 | 0.0195 | 0.0011 | 0.0125 | - |
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | intercept | -22.5998 | 14.0540 | -1.6081 | 0.1078 | -50.1451 | 4.9455 | Tidak |
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | Harga_Rata2_Per_Kg | 10.0785 | 0.5548 | 18.1673 | 0.0000 | 8.9912 | 11.1658 | Ya |
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | ar.L1 | 0.3865 | 0.2376 | 1.6266 | 0.1038 | -0.0792 | 0.8523 | Tidak |
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | ar.L2 | 0.4012 | 0.2199 | 1.8241 | 0.0681 | -0.0299 | 0.8322 | Tidak |
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | sigma2 | 0.0078 | 0.0035 | 2.2191 | 0.0265 | 0.0009 | 0.0146 | - |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | intercept | 0.2014 | 0.1982 | 1.0159 | 0.3097 | -0.1871 | 0.5899 | Tidak |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | ar.L1 | 0.7731 | 0.1222 | 6.3261 | 0.0000 | 0.5336 | 1.0127 | Ya |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | ar.S.L12 | 0.9235 | 0.0477 | 19.3472 | 0.0000 | 0.8299 | 1.0170 | Ya |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | sigma2 | 0.0212 | 0.0116 | 1.8280 | 0.0675 | -0.0015 | 0.0439 | - |
| ARIMA | ARIMA(0, 0, 0) | intercept | 11.5454 | 0.1022 | 113.0140 | 0.0000 | 11.3451 | 11.7456 | Ya |
| ARIMA | ARIMA(0, 0, 0) | sigma2 | 0.0982 | 0.0229 | 4.2858 | 0.0000 | 0.0533 | 0.1431 | - |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | ar.L1 | 0.9840 | 0.0288 | 34.1651 | 0.0000 | 0.9275 | 1.0404 | Ya |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | ar.S.L12 | -0.9463 | 0.0867 | -10.9190 | 0.0000 | -1.1162 | -0.7765 | Ya |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | sigma2 | 0.0024 | 0.0036 | 0.6721 | 0.5015 | -0.0046 | 0.0094 | - |

| Label | Nama_Model | LogL | AIC | BIC |
|---|---|---|---|---|
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | 28.3542 | -44.7084 | -36.9334 |
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | 26.8078 | -43.6157 | -37.1365 |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | 1.7372 | 4.5257 | 9.7090 |
| ARIMA | ARIMA(0, 0, 0) | -6.9815 | 17.9630 | 20.5546 |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | 9.2738 | -12.5475 | -10.4234 |

## 2. Validitas estimasi dan optimum lokal

- Konsistensi dengan script 06: selisih LogL maksimum 0.00e+00.
- Model dengan std error tidak valid: 0; tidak konvergen: 0.
- Model yang dengan lbfgs default saja masih berhenti di optimum lokal (diperbaiki oleh multi-optimizer, perbaikan LogL > 0.01): 13. Log lengkap: `data/hasil_07/07_cek_optimum_lokal.csv`.

| Nama_Model | Kelompok | LogL_lbfgs | LogL_07 | Optimizer_Terpilih | Perbaikan_vs_lbfgs_default |
|---|---|---|---|---|---|
| ARIMAX(2, 0, 0) + Harga | d=0, D=0 | 17.7846 | 26.8078 | nm_awal+0.0 | 9.0232 |
| ARIMAX(1, 0, 2) + Harga | d=0, D=0 | 15.1396 | 27.7892 | nm_awal+0.3 | 12.6496 |
| ARIMAX(2, 0, 1) + Harga + Iduladha | d=0, D=0 | 28.5281 | 28.5402 | nm_awal+0.3 | 0.0121 |
| ARIMAX(1, 0, 1) + Harga + Iduladha | d=0, D=0 | 27.4987 | 27.5388 | bfgs | 0.0402 |
| ARIMAX(1, 0, 1) + Harga | d=0, D=0 | 26.1720 | 26.2271 | bfgs | 0.0551 |
| ARIMAX(2, 0, 1) + Harga | d=0, D=0 | 9.3936 | 27.1831 | powell | 17.7895 |
| ARIMAX(1, 0, 0) + Harga | d=0, D=0 | 15.6151 | 24.6046 | bfgs | 8.9894 |
| ARIMAX(0, 0, 2) + Harga + Iduladha | d=0, D=0 | 23.9792 | 24.0194 | nm_awal+0.0 | 0.0401 |
| ARIMAX(0, 0, 2) + Harga | d=0, D=0 | 21.4167 | 21.4379 | bfgs | 0.0212 |
| ARIMAX(0, 0, 1) + Harga | d=0, D=0 | 16.9533 | 16.9959 | bfgs | 0.0426 |
| ARIMAX(0, 0, 1) + Harga + Iduladha | d=0, D=0 | 16.5196 | 17.1738 | bfgs | 0.6542 |
| ARIMAX(0, 0, 0) + Harga | d=0, D=0 | 10.5188 | 10.7284 | bfgs | 0.2097 |
| ARIMAX(0, 0, 0) + Harga + Iduladha | d=0, D=0 | 9.4622 | 10.8312 | bfgs | 1.3689 |

## 3. Diagnostik residual (training)

Residual burn-in (`loglikelihood_burn`) dibuang. Ljung-Box lag [6, 9, 12], df = lag − (p+q+P+Q); lag dengan df ≤ 0 atau lag ≥ jumlah residual dilewati. Keputusan α = 0.05. Q-Q plot: `data/hasil_07/grafik/07_qq_*.png`.

| Label | Jumlah_Residual | model_df | LB_Q_lag6 | LB_p_lag6 | LB_Q_lag9 | LB_p_lag9 | LB_Q_lag12 | LB_p_lag12 | LB_lag_dilewati | Ljung_Box | Shapiro_W | Shapiro_p | Shapiro_Wilk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARIMA | 27 | 0 | 5.4700 | 0.4851 | 5.9261 | 0.7473 | 9.7256 | 0.6400 | - | Lulus | 0.7392 | 0.0000 | Gagal |
| SARIMA D=0 | 27 | 2 | 9.4402 | 0.0510 | 10.3911 | 0.1675 | 12.8346 | 0.2331 | - | Lulus | 0.7141 | 0.0000 | Gagal |
| SARIMA D=1 | 15 | 2 | 7.4853 | 0.1124 | 7.8678 | 0.3444 | 9.9739 | 0.4428 | - | Lulus | 0.9300 | 0.2731 | Lulus |
| ARIMAX Harga | 27 | 2 | 4.5460 | 0.3371 | 6.3460 | 0.5000 | 10.4992 | 0.3978 | - | Lulus | 0.9622 | 0.4149 | Lulus |
| ARIMAX Harga+Iduladha | 27 | 2 | 1.9104 | 0.7522 | 3.0060 | 0.8845 | 7.6443 | 0.6635 | - | Lulus | 0.9805 | 0.8743 | Lulus |

## 4. Rolling origin (9 putaran, latih ulang penuh)

Target akurasi: MAPE < 15%, RMSE < 10% × ȳ, MAE < 8% × ȳ, MSE < (10% × ȳ)², R² > 0.7 (ȳ = rata-rata permintaan aktual periode evaluasi).

Pada periode testing: ȳ = 113,751 kg → MAPE < 15%, RMSE < 11,375 kg, MAE < 9,100 kg, MSE < 129,391,859 kg², R² > 0.7.

> Target RMSE/MAE/MSE dibuat **relatif terhadap rata-rata permintaan** karena data penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM yang tidak diketahui pasti). Proporsi target mengikuti dokumen alur: MAE/RMSE = 400/500 = 0,8 dan MSE = RMSE². MAPE dan R² tidak bergantung skala.

| Label | MAPE_% | RMSE | RMSE_%_rata2 | MAE | MAE_%_rata2 | MSE | R2 | APE_maks_% | Target_MAPE_% | Target_RMSE | Target_MAE | Target_MSE | Target_R2 | Lebih_baik_dari_naive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARIMAX Harga | 4.003 | 10,399.789 | 9.143 | 5,927.776 | 5.211 | 108,155,608.659 | 0.967 | 10.430 | Lulus | Lulus | Lulus | Lulus | Lulus | Ya |
| ARIMAX Harga+Iduladha | 4.586 | 11,304.698 | 9.938 | 6,687.913 | 5.879 | 127,796,186.552 | 0.961 | 11.535 | Lulus | Lulus | Lulus | Lulus | Lulus | Ya |
| SARIMA D=1 | 6.586 | 7,395.249 | 6.501 | 6,102.489 | 5.365 | 54,689,701.138 | 0.983 | 13.502 | Lulus | Lulus | Lulus | Lulus | Lulus | Ya |
| SARIMA D=0 | 8.364 | 22,986.773 | 20.208 | 12,699.812 | 11.165 | 528,391,736.826 | 0.838 | 23.615 | Lulus | Gagal | Gagal | Gagal | Lulus | Ya |
| Seasonal naive | 14.727 | 28,533.759 | 25.085 | 19,596.608 | 17.228 | 814,175,425.297 | 0.750 | 27.672 | Lulus | Gagal | Gagal | Gagal | Lulus | - |
| ARIMA | 17.544 | 58,572.084 | 51.492 | 28,811.254 | 25.328 | 3,430,689,041.569 | -0.052 | 62.820 | Gagal | Gagal | Gagal | Gagal | Gagal | Tidak |

### Error per putaran (APE %)

| Periode_Target | ARIMA | ARIMAX Harga | ARIMAX Harga+Iduladha | SARIMA D=0 | SARIMA D=1 | Seasonal naive |
|---|---|---|---|---|---|---|
| 2025-04 | 20.55 | 2.24 | 2.12 | 0.83 | 10.39 | 5.09 |
| 2025-05 | 14.82 | 0.02 | 0.35 | 9.23 | 13.50 | 13.58 |
| 2025-06 | 62.82 | 10.30 | 11.54 | 23.62 | 0.56 | 27.67 |
| 2025-07 | 7.91 | 0.01 | 2.20 | 16.48 | 1.11 | 14.45 |
| 2025-08 | 2.67 | 10.43 | 7.48 | 12.38 | 1.14 | 23.04 |
| 2025-09 | 7.64 | 5.80 | 5.84 | 2.77 | 5.60 | 16.76 |
| 2025-10 | 10.80 | 4.83 | 5.88 | 0.86 | 9.57 | 14.68 |
| 2025-11 | 13.27 | 1.38 | 1.80 | 1.20 | 4.37 | 13.37 |
| 2025-12 | 17.41 | 1.02 | 4.08 | 7.90 | 13.03 | 3.90 |

### Prediksi per putaran (kg)

| Periode_Target | Aktual | ARIMA | ARIMAX Harga | ARIMAX Harga+Iduladha | SARIMA D=0 | SARIMA D=1 | Seasonal naive |
|---|---|---|---|---|---|---|---|
| 2025-04 | 85,690 | 103,297 | 87,607 | 87,510 | 86,404 | 94,591 | 81,326 |
| 2025-05 | 89,364 | 102,610 | 89,380 | 89,053 | 81,113 | 77,298 | 77,228 |
| 2025-06 | 274,672 | 102,122 | 246,391 | 242,988 | 209,807 | 273,123 | 198,665 |
| 2025-07 | 97,810 | 105,546 | 97,796 | 95,663 | 113,930 | 96,725 | 83,675 |
| 2025-08 | 102,546 | 105,287 | 91,851 | 94,878 | 89,852 | 101,377 | 78,919 |
| 2025-09 | 97,732 | 105,200 | 103,400 | 103,442 | 100,442 | 92,261 | 81,357 |
| 2025-10 | 94,733 | 104,966 | 99,309 | 100,303 | 93,915 | 103,799 | 80,821 |
| 2025-11 | 92,390 | 104,650 | 91,113 | 94,051 | 91,278 | 96,430 | 80,042 |
| 2025-12 | 88,817 | 104,278 | 89,723 | 92,437 | 95,832 | 100,392 | 85,352 |

## 5. Rekomendasi model

Aturan pemilihan:

1. **Layak statistik**: lulus Ljung-Box dan Shapiro-Wilk, serta MAPE rolling origin lebih baik dari seasonal naive.
2. **Layak peramalan**: layak statistik **dan tidak membutuhkan nilai eksogen masa depan**. Saat meramal Jan–Jun 2026, harga rata-rata per kg bulan-bulan tersebut belum diketahui, sehingga ARIMAX tidak dapat dipakai tanpa meramal harga terlebih dahulu (yang menambah ketidakpastian). Pada evaluasi ini ARIMAX memakai harga **aktual** periode testing, sehingga akurasinya merupakan batas atas yang optimistis.
3. **Model final** = layak peramalan dengan MAPE rolling origin terendah. AIC hanya dibandingkan di dalam kelompok (d, D).

| Peringkat | Label | Nama_Model | Ljung_Box | Shapiro_Wilk | MAPE_% | RMSE | R2 | Butuh_Eksogen_Masa_Depan | Layak_Statistik | Layak_Peramalan |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | Lulus | Lulus | 6.586 | 7,395.249 | 0.983 | Tidak | True | True |
| 2 | ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | Lulus | Lulus | 4.003 | 10,399.789 | 0.967 | Ya | True | False |
| 3 | ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | Lulus | Lulus | 4.586 | 11,304.698 | 0.961 | Ya | True | False |
| 4 | SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | Lulus | Gagal | 8.364 | 22,986.773 | 0.838 | Tidak | False | False |
| 5 | ARIMA | ARIMA(0, 0, 0) | Lulus | Gagal | 17.544 | 58,572.084 | -0.052 | Tidak | False | False |

**Model final untuk peramalan: SARIMA D=1 — SARIMA(1, 0, 0)x(1, 1, 0, 12)** (lulus Ljung-Box dan Shapiro-Wilk, lebih baik dari seasonal naive, tidak membutuhkan nilai eksogen masa depan, dan memiliki MAPE rolling origin terendah di antara model yang memenuhi syarat tersebut).

Catatan: MAPE rolling origin terendah dimiliki **ARIMAX Harga** (4.00% vs 6.59%). Model ini valid secara statistik dan dilaporkan sebagai pembanding, tetapi tidak dipilih sebagai model final karena membutuhkan harga masa depan. Model final dipakai di script 09 (peramalan Jan–Jun 2026) dan script 11–12 (implementasi MS Access).

## Catatan

- ARIMAX memakai nilai eksogen aktual bulan yang diramal (Harga_Rata2_Per_Kg dan Koefisien_Musim) dari dataset. Dalam praktik, harga bulan depan belum diketahui dan harus diasumsikan, sehingga akurasi ARIMAX di sini cenderung optimistis.
- Koefisien_Musim adalah pengali yang dipakai untuk membangkitkan data sintetis, sehingga model dengan label ini diberi informasi persis tentang pola musiman data.
- Peramalan multi-step pada data testing (Apr–Des 2025) dikerjakan di script 08.
