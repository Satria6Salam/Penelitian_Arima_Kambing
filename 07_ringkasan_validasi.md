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
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | intercept | 20.9054 | 37.2861 | 0.5607 | 0.5750 | -52.1740 | 93.9847 | Tidak |
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | Harga_Rata2_Per_Kg | -2.1614 | 5.2513 | -0.4116 | 0.6806 | -12.4538 | 8.1309 | Tidak |
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | Koefisien_Musim | 0.7102 | 0.2957 | 2.4021 | 0.0163 | 0.1307 | 1.2897 | Ya |
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | ar.L1 | 0.4222 | 0.2037 | 2.0719 | 0.0383 | 0.0228 | 0.8215 | Ya |
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | sigma2 | 0.0046 | 0.0015 | 3.0070 | 0.0026 | 0.0016 | 0.0077 | - |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | intercept | -96.6467 | 7.6654 | -12.6082 | 0.0000 | -111.6705 | -81.6228 | Ya |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | Harga_Rata2_Per_Kg | 9.2687 | 0.6554 | 14.1424 | 0.0000 | 7.9842 | 10.5532 | Ya |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | ma.L1 | 0.1098 | 0.2129 | 0.5156 | 0.6061 | -0.3075 | 0.5270 | Tidak |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | ma.L2 | 0.5475 | 0.2391 | 2.2893 | 0.0221 | 0.0788 | 1.0162 | Ya |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | sigma2 | 0.0054 | 0.0024 | 2.2856 | 0.0223 | 0.0008 | 0.0100 | - |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | intercept | 0.7204 | 0.6418 | 1.1225 | 0.2617 | -0.5375 | 1.9784 | Tidak |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | ar.L1 | 0.1188 | 0.2789 | 0.4259 | 0.6702 | -0.4278 | 0.6653 | Tidak |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | ar.S.L12 | 0.9302 | 0.0471 | 19.7648 | 0.0000 | 0.8380 | 1.0225 | Ya |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | sigma2 | 0.0111 | 0.0058 | 1.9081 | 0.0564 | -0.0003 | 0.0224 | - |
| ARIMA | ARIMA(1, 0, 1) | intercept | 4.9418 | 4.0205 | 1.2291 | 0.2190 | -2.9383 | 12.8219 | Tidak |
| ARIMA | ARIMA(1, 0, 1) | ar.L1 | 0.5784 | 0.3437 | 1.6832 | 0.0923 | -0.0951 | 1.2520 | Tidak |
| ARIMA | ARIMA(1, 0, 1) | ma.L1 | -1.0000 | 0.0012 | -830.0444 | 0.0000 | -1.0024 | -0.9976 | Ya |
| ARIMA | ARIMA(1, 0, 1) | sigma2 | 0.0560 | 0.0218 | 2.5648 | 0.0103 | 0.0132 | 0.0988 | - |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | ar.L1 | 0.4361 | 0.3193 | 1.3658 | 0.1720 | -0.1897 | 1.0618 | Tidak |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | ar.S.L12 | -0.6900 | 0.9796 | -0.7043 | 0.4812 | -2.6100 | 1.2300 | Tidak |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | sigma2 | 0.0059 | 0.0152 | 0.3874 | 0.6984 | -0.0239 | 0.0356 | - |

| Label | Nama_Model | LogL | AIC | BIC |
|---|---|---|---|---|
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | 34.1473 | -58.2946 | -51.8154 |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | 31.8559 | -53.7118 | -47.2327 |
| SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | 10.4578 | -12.9157 | -7.7323 |
| ARIMA | ARIMA(1, 0, 1) | -0.4555 | 8.9110 | 14.0943 |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | 13.2499 | -20.4999 | -18.3757 |

## 2. Validitas estimasi dan optimum lokal

- Konsistensi dengan script 06: selisih LogL maksimum 3.47e-01.
- Model dengan std error tidak valid: 0; tidak konvergen: 0.
- Model yang dengan lbfgs default saja masih berhenti di optimum lokal (diperbaiki oleh multi-optimizer, perbaikan LogL > 0.01): 15. Log lengkap: `data/hasil_07/07_cek_optimum_lokal.csv`.

| Nama_Model | Kelompok | LogL_lbfgs | LogL_07 | Optimizer_Terpilih | Perbaikan_vs_lbfgs_default |
|---|---|---|---|---|---|
| ARIMAX(1, 0, 0) + Harga + Iduladha | d=0, D=0 | 33.8078 | 34.1473 | bfgs | 0.3395 |
| ARIMAX(0, 0, 2) + Harga + Iduladha | d=0, D=0 | 34.8148 | 34.8378 | bfgs | 0.0230 |
| ARIMAX(1, 0, 1) + Harga + Iduladha | d=0, D=0 | 34.4261 | 34.6447 | bfgs | 0.2186 |
| ARIMAX(0, 0, 1) + Harga + Iduladha | d=0, D=0 | 33.0916 | 33.2722 | bfgs | 0.1806 |
| ARIMAX(0, 0, 2) + Harga | d=0, D=0 | 1.0876 | 31.8559 | nm_awal+0.3 | 30.7683 |
| ARIMAX(1, 0, 2) + Harga | d=0, D=0 | 2.1931 | 32.0515 | nm | 29.8584 |
| ARIMAX(0, 0, 0) + Harga | d=0, D=0 | 28.1311 | 29.1476 | bfgs | 1.0165 |
| ARIMAX(1, 0, 0) + Harga | d=0, D=0 | 0.2408 | 29.6622 | nm_awal+0.0 | 29.4215 |
| ARIMAX(0, 0, 1) + Harga | d=0, D=0 | 29.1166 | 29.4277 | bfgs | 0.3111 |
| ARIMAX(1, 0, 1) + Harga | d=0, D=0 | 2.1262 | 30.2955 | bfgs | 28.1693 |
| ARIMAX(2, 0, 0) + Harga | d=0, D=0 | 28.1048 | 29.6622 | warm | 1.5575 |
| ARIMAX(2, 0, 1) + Harga | d=0, D=0 | 2.4457 | 30.2955 | warm | 27.8498 |
| ARIMA(1, 0, 1) | d=0, D=0 | -0.6668 | -0.4555 | nm_awal+0.3 | 0.2113 |
| ARIMA(1, 0, 2) | d=0, D=0 | -0.9829 | -0.3712 | nm | 0.6117 |
| ARIMA(2, 0, 1) | d=0, D=0 | -0.5587 | -0.5221 | nm | 0.0366 |

## 3. Diagnostik residual (training)

Residual burn-in (`loglikelihood_burn`) dibuang. Ljung-Box lag [6, 9, 12], df = lag − (p+q+P+Q); lag dengan df ≤ 0 atau lag ≥ jumlah residual dilewati. Keputusan α = 0.05. Q-Q plot: `data/hasil_07/grafik/07_qq_*.png`.

| Label | Jumlah_Residual | model_df | LB_Q_lag6 | LB_p_lag6 | LB_Q_lag9 | LB_p_lag9 | LB_Q_lag12 | LB_p_lag12 | LB_lag_dilewati | Ljung_Box | Shapiro_W | Shapiro_p | Shapiro_Wilk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARIMA | 27 | 2 | 1.1418 | 0.8876 | 2.1328 | 0.9521 | 11.3710 | 0.3294 | - | Lulus | 0.8080 | 0.0002 | Gagal |
| SARIMA D=0 | 27 | 2 | 4.1183 | 0.3902 | 5.9932 | 0.5405 | 7.7421 | 0.6540 | - | Lulus | 0.6926 | 0.0000 | Gagal |
| SARIMA D=1 | 15 | 2 | 8.4731 | 0.0757 | 9.2109 | 0.2379 | 9.6828 | 0.4687 | - | Lulus | 0.9484 | 0.5003 | Lulus |
| ARIMAX Harga | 27 | 2 | 1.0915 | 0.8956 | 2.6046 | 0.9190 | 2.8669 | 0.9844 | - | Lulus | 0.9779 | 0.8127 | Lulus |
| ARIMAX Harga+Iduladha | 27 | 1 | 1.2375 | 0.9412 | 3.1275 | 0.9261 | 4.7007 | 0.9448 | - | Lulus | 0.9723 | 0.6637 | Lulus |

## 4. Rolling origin (9 putaran, latih ulang penuh)

Target akurasi: MAPE < 15%, RMSE < 10% × ȳ, MAE < 8% × ȳ, MSE < (10% × ȳ)², R² > 0.7 (ȳ = rata-rata permintaan aktual periode evaluasi).

Pada periode testing: ȳ = 145,698 kg → MAPE < 15%, RMSE < 14,570 kg, MAE < 11,656 kg, MSE < 212,279,308 kg², R² > 0.7.

> Target RMSE/MAE/MSE dibuat **relatif terhadap rata-rata permintaan** karena data penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM yang tidak diketahui pasti). Proporsi target mengikuti dokumen alur: MAE/RMSE = 400/500 = 0,8 dan MSE = RMSE². MAPE dan R² tidak bergantung skala.

| Label | MAPE_% | RMSE | RMSE_%_rata2 | MAE | MAE_%_rata2 | MSE | R2 | APE_maks_% | Target_MAPE_% | Target_RMSE | Target_MAE | Target_MSE | Target_R2 | Lebih_baik_dari_naive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARIMAX Harga+Iduladha | 4.382 | 15,502.578 | 10.640 | 8,574.172 | 5.885 | 240,329,911.227 | 0.957 | 12.411 | Lulus | Gagal | Lulus | Gagal | Lulus | Ya |
| SARIMA D=1 | 7.510 | 16,963.421 | 11.643 | 12,132.241 | 8.327 | 287,757,652.983 | 0.948 | 13.741 | Lulus | Gagal | Gagal | Gagal | Lulus | Ya |
| SARIMA D=0 | 8.268 | 30,144.810 | 20.690 | 16,119.089 | 11.063 | 908,709,540.002 | 0.837 | 24.122 | Lulus | Gagal | Gagal | Gagal | Lulus | Ya |
| Seasonal naive | 8.810 | 26,773.137 | 18.376 | 15,862.021 | 10.887 | 716,800,849.637 | 0.871 | 21.913 | Lulus | Gagal | Gagal | Gagal | Lulus | - |
| ARIMAX Harga | 9.392 | 29,173.207 | 20.023 | 16,868.982 | 11.578 | 851,076,023.183 | 0.847 | 37.928 | Lulus | Gagal | Gagal | Gagal | Lulus | Tidak |
| ARIMA | 18.466 | 78,742.271 | 54.045 | 39,461.444 | 27.084 | 6,200,345,171.412 | -0.112 | 64.381 | Gagal | Gagal | Gagal | Gagal | Gagal | Tidak |

### Error per putaran (APE %)

| Periode_Target | ARIMA | ARIMAX Harga | ARIMAX Harga+Iduladha | SARIMA D=0 | SARIMA D=1 | Seasonal naive |
|---|---|---|---|---|---|---|
| 2025-04 | 7.85 | 0.38 | 2.45 | 0.20 | 3.39 | 1.49 |
| 2025-05 | 7.16 | 0.49 | 2.94 | 6.94 | 12.28 | 7.83 |
| 2025-06 | 64.38 | 19.85 | 12.41 | 24.12 | 12.28 | 20.73 |
| 2025-07 | 31.17 | 4.81 | 6.08 | 2.27 | 4.43 | 3.80 |
| 2025-08 | 24.64 | 37.93 | 7.70 | 10.35 | 6.41 | 11.35 |
| 2025-09 | 15.30 | 4.24 | 1.19 | 0.83 | 7.45 | 1.78 |
| 2025-10 | 8.35 | 3.29 | 2.01 | 3.58 | 4.52 | 3.12 |
| 2025-11 | 2.51 | 6.16 | 0.49 | 6.59 | 3.10 | 7.28 |
| 2025-12 | 4.83 | 7.39 | 4.17 | 19.53 | 13.74 | 21.91 |

### Prediksi per putaran (kg)

| Periode_Target | Aktual | ARIMA | ARIMAX Harga | ARIMAX Harga+Iduladha | SARIMA D=0 | SARIMA D=1 | Seasonal naive |
|---|---|---|---|---|---|---|---|
| 2025-04 | 112,878 | 121,738 | 112,446 | 115,644 | 112,653 | 116,699 | 111,191 |
| 2025-05 | 116,787 | 125,154 | 116,220 | 113,358 | 108,678 | 102,448 | 107,648 |
| 2025-06 | 356,163 | 126,861 | 285,482 | 311,960 | 270,251 | 312,439 | 282,346 |
| 2025-07 | 125,856 | 86,627 | 119,803 | 118,208 | 128,714 | 120,282 | 121,071 |
| 2025-08 | 130,954 | 98,688 | 81,286 | 120,865 | 117,406 | 122,558 | 116,087 |
| 2025-09 | 123,878 | 104,924 | 118,630 | 122,400 | 124,911 | 114,646 | 121,679 |
| 2025-10 | 119,197 | 109,241 | 115,277 | 121,596 | 123,468 | 124,580 | 122,921 |
| 2025-11 | 115,410 | 112,513 | 122,516 | 114,849 | 123,013 | 118,993 | 123,811 |
| 2025-12 | 110,158 | 115,479 | 118,303 | 114,753 | 131,671 | 125,295 | 134,296 |

## 5. Rekomendasi model

Aturan pemilihan:

1. **Layak statistik**: lulus Ljung-Box dan Shapiro-Wilk, serta MAPE rolling origin lebih baik dari seasonal naive.
2. **Layak peramalan**: layak statistik **dan tidak membutuhkan nilai eksogen masa depan**. Saat meramal Jan–Jun 2026, harga rata-rata per kg bulan-bulan tersebut belum diketahui, sehingga ARIMAX tidak dapat dipakai tanpa meramal harga terlebih dahulu (yang menambah ketidakpastian). Pada evaluasi ini ARIMAX memakai harga **aktual** periode testing, sehingga akurasinya merupakan batas atas yang optimistis.
3. **Model final** = layak peramalan dengan MAPE rolling origin terendah. AIC hanya dibandingkan di dalam kelompok (d, D).

| Peringkat | Label | Nama_Model | Ljung_Box | Shapiro_Wilk | MAPE_% | RMSE | R2 | Butuh_Eksogen_Masa_Depan | Layak_Statistik | Layak_Peramalan |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | Lulus | Lulus | 7.510 | 16,963.421 | 0.948 | Tidak | True | True |
| 2 | ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | Lulus | Lulus | 4.382 | 15,502.578 | 0.957 | Ya | True | False |
| 3 | ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | Lulus | Lulus | 9.392 | 29,173.207 | 0.847 | Ya | False | False |
| 4 | SARIMA D=0 | SARIMA(1, 0, 0)x(1, 0, 0, 12) | Lulus | Gagal | 8.268 | 30,144.810 | 0.837 | Tidak | False | False |
| 5 | ARIMA | ARIMA(1, 0, 1) | Lulus | Gagal | 18.466 | 78,742.271 | -0.112 | Tidak | False | False |

**Model final untuk peramalan: SARIMA D=1 — SARIMA(1, 0, 0)x(1, 1, 0, 12)** (lulus Ljung-Box dan Shapiro-Wilk, lebih baik dari seasonal naive, tidak membutuhkan nilai eksogen masa depan, dan memiliki MAPE rolling origin terendah di antara model yang memenuhi syarat tersebut).

Catatan: MAPE rolling origin terendah dimiliki **ARIMAX Harga+Iduladha** (4.38% vs 7.51%). Model ini valid secara statistik dan dilaporkan sebagai pembanding, tetapi tidak dipilih sebagai model final karena membutuhkan harga masa depan. Model final dipakai di script 09 (peramalan Jan–Jun 2026) dan script 11–12 (implementasi MS Access).

## Catatan

- ARIMAX memakai nilai eksogen aktual bulan yang diramal (Harga_Rata2_Per_Kg dan Koefisien_Musim) dari dataset. Dalam praktik, harga bulan depan belum diketahui dan harus diasumsikan, sehingga akurasi ARIMAX di sini cenderung optimistis.
- Koefisien_Musim adalah pengali yang dipakai untuk membangkitkan data sintetis, sehingga model dengan label ini diberi informasi persis tentang pola musiman data.
- Peramalan multi-step pada data testing (Apr–Des 2025) dikerjakan di script 08.
