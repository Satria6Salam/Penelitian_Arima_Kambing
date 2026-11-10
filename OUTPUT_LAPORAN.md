# Indeks Output Laporan Penelitian

Daftar lokasi output (CSV dan plot) untuk setiap hasil penelitian. Semua path relatif terhadap folder proyek. Output baru yang melengkapi plot/CSV dibuat oleh `10_ekspor_output_laporan.py` di folder `data\laporan\`.

## 1. Hasil ADF

ADF seri asli: statistik -5.7452, p 0.000001, kritis 5% -2.9485 → stasioner (d = 0).

**File CSV/data:**

- `data\laporan\01_hasil_adf.csv`

**Plot:**

- `data\laporan\01_plot_adf.png`
- `data\eksplorasi\time_series_plot.png`

## 2. Hasil Differencing

ADF untuk seri asli, Δ1, Δ12, dan Δ12 log; seri asli sudah stasioner (d=0). D=1 diuji di tahap pemodelan dan dipakai model final (log).

**File CSV/data:**

- `data\laporan\02_hasil_differencing.csv`
- `data\laporan\02_seri_differencing.csv`
- `data\eksplorasi\model_config.json`

**Plot:**

- `data\laporan\02_plot_differencing.png`

## 3. Hasil ACF & PACF

Lag 12 signifikan: ACF 0.3876, PACF 0.6007 pada seri asli → pola musiman m = 12; kandidat model di model_config.json. Plot asli script 05 (seri asli, d=0): acf_pacf_plot.png. Plot tambahan 03_plot_acf_pacf_diff12_log.png memakai seri BERBEDA, yaitu Δ12 log (input model final).

**File CSV/data:**

- `data\laporan\03_tabel_acf_pacf.csv`
- `data\eksplorasi\model_config.json`

**Plot:**

- `data\eksplorasi\acf_pacf_plot.png`
- `data\laporan\03_plot_acf_pacf_diff12_log.png`
- `data\eksplorasi\time_series_decomposition.png`

## 4. Hasil Pembagian Dataset

Training Jan 2023–Mar 2025 (27 bulan), testing Apr 2025–Dec 2025 (9 bulan).

**File CSV/data:**

- `data\hasil_06\06_training_set.csv`
- `data\hasil_06\06_testing_set.csv`
- `data\laporan\04_ringkasan_pembagian_dataset.csv`
- `data\hasil_08\08_cek_data_testing.csv`

**Plot:**

- `data\laporan\04_plot_pembagian_dataset.png`

## 5. Hasil Penetapan 4 Skenario Pemodelan

Skenario: ARIMA (baseline), SARIMA (musiman, D=0 dan D=1), ARIMAX + Harga, ARIMAX + Harga + Iduladha. Ensemble tidak diestimasi.

**File CSV/data:**

- `data\laporan\05_ringkasan_skenario.csv`
- `data\laporan\05_daftar_kandidat_skenario.csv`
- `data\eksplorasi\model_config.json`

**Plot:**

- `data\laporan\05_plot_skenario_pemodelan.png`

Ringkasan teks: `06_ringkasan_aic_bic.md`

## 6. Hasil Training

Estimasi MLE seluruh kandidat (nobs, LogL, optimizer, konvergensi), tabel parameter (koefisien, SE, p-value, CI 95%), dan nilai fitted model shortlist. Summary lengkap: data\hasil_07\07_summary_shortlist.txt.

**File CSV/data:**

- `data\hasil_06\06_hasil_estimasi.csv`
- `data\hasil_07\07_parameter_estimasi.csv`
- `data\laporan\06_fitted_training.csv`

**Plot:**

- `data\laporan\06_plot_fitted_vs_aktual.png`

Ringkasan teks: `06_ringkasan_aic_bic.md`

## 7. Hasil AIC & BIC

AIC/BIC, Delta, dan peringkat per kelompok (d, D); kolom *_setara_kg sudah dikoreksi ke satuan kg.

**File CSV/data:**

- `data\hasil_06\06_perbandingan_aic_bic.csv`
- `data\hasil_06\06_cek_model_bersarang.csv`

**Plot:**

- `data\laporan\07_plot_aic_bic.png`

Ringkasan teks: `06_ringkasan_aic_bic.md`

## 8. Hasil Validasi Diagnostik & Evaluasi Kinerja

Ljung-Box (lag 6/9/12) dan Shapiro-Wilk, Q-Q plot per model, rolling origin 9 putaran, MAPE/RMSE/MAE/MSE/R² vs target, serta peramalan multi-step data testing.

**File CSV/data:**

- `data\hasil_07\07_diagnostik_residual.csv`
- `data\laporan\08_residual_training.csv`
- `data\hasil_07\07_rolling_origin_prediksi.csv`
- `data\hasil_07\07_metrik_rolling_origin.csv`
- `data\hasil_08\08_peramalan_testing.csv`
- `data\hasil_08\08_evaluasi_peramalan.csv`
- `data\hasil_08\08_multistep_vs_rolling.csv`

**Plot:**

- `data\laporan\08_plot_ljungbox_shapiro.png`
- `data\laporan\08_plot_residual_acf.png`
- `data\hasil_07\grafik\07_qq_ARIMA.png`
- `data\hasil_07\grafik\07_qq_ARIMAX_Harga.png`
- `data\hasil_07\grafik\07_qq_ARIMAX_HargaplusIduladha.png`
- `data\hasil_07\grafik\07_qq_SARIMA_D0.png`
- `data\hasil_07\grafik\07_qq_SARIMA_D1.png`
- `data\hasil_07\grafik\07_rolling_origin_vs_aktual.png`
- `data\laporan\08_plot_metrik_rolling_origin.png`
- `data\hasil_08\grafik\08_fan_chart_ARIMAX_Harga.png`
- `data\hasil_08\grafik\08_fan_chart_ARIMAX_HargaplusIduladha.png`
- `data\hasil_08\grafik\08_fan_chart_SARIMA_D1.png`
- `data\hasil_08\grafik\08_perbandingan_peramalan.png`

Ringkasan teks: `07_ringkasan_validasi.md, 08_ringkasan_forecasting.md`

## 9. Hasil Peramalan 6 Bulan ke Depan

Peramalan Jan–Jun 2026 dengan interval 95% (fan chart) dari model final SARIMA(1,0,0)x(1,1,0,12) log; validasi ekstrapolasi Apr–Sep 2025.

**File CSV/data:**

- `data\hasil_09\09_peramalan_jan_jun_2026.csv`
- `data\hasil_09\09_parameter_model_final.csv`
- `data\hasil_09\09_diagnostik_model_final.csv`
- `data\hasil_09\validasi_apr_sep_2025\09_peramalan_validasi_apr_sep_2025.csv`

**Plot:**

- `data\hasil_09\grafik\09_fan_chart.png`
- `data\hasil_09\validasi_apr_sep_2025\grafik\09_fan_chart_validasi.png`

Ringkasan teks: `09_ringkasan_peramalan.md`

