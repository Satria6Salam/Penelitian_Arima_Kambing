# Ringkasan Script 08: Peramalan dan Visualisasi pada Data Testing

Dibuat otomatis oleh `08_peramalan_visualisasi.py` (statsmodels 0.15.0).

## Pemeriksaan data testing

| Pemeriksaan | Hasil | Lulus |
|---|---|---|
| Jumlah baris testing | 9 | Ya |
| Jumlah baris training | 27 | Ya |
| Proporsi testing | 25.0% dari 36 bulan | Ya |
| Periode testing | 2025-04 s.d. 2025-12 | Ya |
| Tidak tumpang tindih dengan training | training berakhir 2025-03 | Ya |
| Testing berurutan bulanan tanpa celah | MS | Ya |
| Testing tepat setelah training | 2025-03 -> 2025-04 | Ya |
| Kolom tersedia | Total_Kuantitas_Kg, Harga_Rata2_Per_Kg, Koefisien_Musim | Ya |
| Tidak ada nilai kosong | - | Ya |
| Bulan Iduladha di testing | 2025-06 | Ya |

## Desain

- Periode peramalan = data testing 25% (`06_testing_set.csv`, Apr–Des 2025, 9 bulan).
- Model = model valid dari script 07 (lulus Ljung-Box dan Shapiro-Wilk), dilatih pada 27 bulan training lalu meramal 9 bulan sekaligus tanpa melihat data testing (berbeda dengan rolling origin script 07 yang meramal 1 bulan lalu dilatih ulang).
- Transformasi estimasi: `log` (target ln(kg), harga ln(Rp/kg), Koefisien_Musim apa adanya). Ramalan dan batas CI 95% dihitung pada skala log lalu dikembalikan ke kg dengan exp(); karena exp monoton, batasnya tetap CI 95% dan menjadi tidak simetris. exp(mean log) = median ramalan; kolom `Prediksi_Mean_Lognormal_Kg` di CSV memakai koreksi bias lognormal exp(μ + σ²/2).
- **ARIMAX memakai nilai eksogen aktual periode testing** (harga dan Koefisien_Musim dari `06_testing_set.csv`). Dalam peramalan nyata harga masa depan belum diketahui, sehingga akurasi ARIMAX di sini adalah batas atas (optimistis).

## Akurasi peramalan 9 bulan (kg)

| Label | Nama_Model | MAPE_% | RMSE | MAE | MSE | R2 | Bias_rata2_Kg | APE_maks_% | Bulan_APE_maks |
|---|---|---|---|---|---|---|---|---|---|
| ARIMAX Harga+Iduladha | ARIMAX(1, 0, 0) + Harga + Iduladha | 6.38 | 17,478.76 | 11,258.40 | 305,507,189.75 | 0.95 | 10,108.37 | 13.02 | 2025-06 |
| ARIMAX Harga | ARIMAX(0, 0, 2) + Harga | 7.81 | 24,632.80 | 14,561.95 | 606,774,847.75 | 0.89 | 12,940.37 | 18.96 | 2025-06 |
| Seasonal naive | y[t-12] | 8.81 | 26,773.14 | 15,862.02 | 716,800,849.64 | 0.87 | 7,803.57 | 21.91 | 2025-12 |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | 9.07 | 18,483.89 | 14,171.24 | 341,654,048.93 | 0.94 | 9,962.76 | 13.77 | 2025-09 |

### Terhadap target akurasi

Target: MAPE < 15%, RMSE < 10% × ȳ, MAE < 8% × ȳ, MSE < (10% × ȳ)², R² > 0.7 (ȳ = rata-rata permintaan aktual periode evaluasi). Pada data testing: ȳ = 145,698 kg → MAPE < 15%, RMSE < 14,570 kg, MAE < 11,656 kg, MSE < 212,279,308 kg², R² > 0.7.

| Label | RMSE_%_rata2 | MAE_%_rata2 | Target_MAPE_% | Target_RMSE | Target_MAE | Target_MSE | Target_R2 |
|---|---|---|---|---|---|---|---|
| ARIMAX Harga+Iduladha | 12.00 | 7.73 | Lulus | Gagal | Lulus | Gagal | Lulus |
| ARIMAX Harga | 16.91 | 9.99 | Lulus | Gagal | Gagal | Gagal | Lulus |
| Seasonal naive | 18.38 | 10.89 | Lulus | Gagal | Gagal | Gagal | Lulus |
| SARIMA D=1 | 12.69 | 9.73 | Lulus | Gagal | Gagal | Gagal | Lulus |

> Target RMSE/MAE/MSE relatif terhadap rata-rata permintaan aktual, karena data penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM).

## Interval kepercayaan 95%

| Label | Jumlah_Dalam_CI | Cakupan_CI_95_% | Lebar_CI_rata2_Kg | Lebar_CI_rata2_%_aktual | MAPE_mean_lognormal_% |
|---|---|---|---|---|---|
| ARIMAX Harga+Iduladha | 9/9 | 100.00 | 39,602.45 | 27.58 | 6.23 |
| ARIMAX Harga | 7/9 | 77.78 | 42,901.97 | 30.09 | 7.66 |
| SARIMA D=1 | 9/9 | 100.00 | 45,005.42 | 31.33 | 8.95 |

## Multi-step (08) vs rolling origin 1 langkah (07)

| Label | MAPE_MultiStep | MAPE_Rolling | MAPE_h1_3 | MAPE_h4_6 | MAPE_h7_9 |
|---|---|---|---|---|---|
| SARIMA D=1 | 9.07 | 7.51 | 8.81 | 12.11 | 6.29 |
| ARIMAX Harga | 7.81 | 9.39 | 6.63 | 11.35 | 5.44 |
| ARIMAX Harga+Iduladha | 6.38 | 4.38 | 5.78 | 10.47 | 2.88 |
| Seasonal naive | 8.81 | 8.81 | 10.02 | 5.64 | 10.77 |

### Juni 2025 (Iduladha, horizon 3)

| Label | Aktual_Kg | Prediksi_MultiStep_Kg | APE_MultiStep_% | Prediksi_Rolling_Kg | APE_Rolling_% |
|---|---|---|---|---|---|
| SARIMA D=1 | 356,163.3 | 312,294.4 | 12.3 | 312,438.6 | 12.3 |
| ARIMAX Harga | 356,163.3 | 288,641.5 | 19.0 | 285,482.1 | 19.8 |
| ARIMAX Harga+Iduladha | 356,163.3 | 309,801.9 | 13.0 | 311,960.1 | 12.4 |
| Seasonal naive | 356,163.3 | 282,346.2 | 20.7 | 282,346.2 | 20.7 |

## Peramalan per bulan

### SARIMA D=1: SARIMA(1, 0, 0)x(1, 1, 0, 12)

| Periode | Aktual_Kg | Prediksi_Kg | Prediksi_Mean_Lognormal_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Error_Kg | APE_% | Dalam_CI_95 |
|---|---|---|---|---|---|---|---|---|
| 2025-04 | 112,878 | 116,699 | 117,043 | 100,411 | 135,630 | -3,821 | 3 | Ya |
| 2025-05 | 116,787 | 104,256 | 104,621 | 88,486 | 122,836 | 12,531 | 11 | Ya |
| 2025-06 | 356,163 | 312,294 | 313,423 | 264,403 | 368,861 | 43,869 | 12 | Ya |
| 2025-07 | 125,856 | 112,492 | 112,900 | 95,196 | 132,929 | 13,364 | 11 | Ya |
| 2025-08 | 130,954 | 115,319 | 115,739 | 97,580 | 136,283 | 15,635 | 12 | Ya |
| 2025-09 | 123,878 | 106,815 | 107,203 | 90,382 | 126,234 | 17,064 | 14 | Ya |
| 2025-10 | 119,197 | 113,198 | 113,610 | 95,784 | 133,779 | 5,999 | 5 | Ya |
| 2025-11 | 115,410 | 115,269 | 115,689 | 97,536 | 136,227 | 141 | 0 | Ya |
| 2025-12 | 110,158 | 125,275 | 125,731 | 106,003 | 148,052 | -15,117 | 14 | Ya |

### ARIMAX Harga: ARIMAX(0, 0, 2) + Harga

| Periode | Aktual_Kg | Prediksi_Kg | Prediksi_Mean_Lognormal_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Error_Kg | APE_% | Dalam_CI_95 |
|---|---|---|---|---|---|---|---|---|
| 2025-04 | 112,878 | 112,446 | 112,749 | 97,377 | 129,847 | 432 | 0 | Ya |
| 2025-05 | 116,787 | 116,132 | 116,449 | 100,481 | 134,219 | 656 | 1 | Ya |
| 2025-06 | 356,163 | 288,641 | 289,664 | 244,787 | 340,352 | 67,522 | 19 | Tidak |
| 2025-07 | 125,856 | 116,269 | 116,680 | 98,604 | 137,099 | 9,587 | 8 | Ya |
| 2025-08 | 130,954 | 108,444 | 108,828 | 91,968 | 127,872 | 22,511 | 17 | Tidak |
| 2025-09 | 123,878 | 112,445 | 112,843 | 95,361 | 132,590 | 11,433 | 9 | Ya |
| 2025-10 | 119,197 | 107,578 | 107,959 | 91,233 | 126,851 | 11,619 | 10 | Ya |
| 2025-11 | 115,410 | 116,805 | 117,218 | 99,058 | 137,731 | -1,395 | 1 | Ya |
| 2025-12 | 110,158 | 116,060 | 116,471 | 98,427 | 136,853 | -5,902 | 5 | Ya |

### ARIMAX Harga+Iduladha: ARIMAX(1, 0, 0) + Harga + Iduladha

| Periode | Aktual_Kg | Prediksi_Kg | Prediksi_Mean_Lognormal_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Error_Kg | APE_% | Dalam_CI_95 |
|---|---|---|---|---|---|---|---|---|
| 2025-04 | 112,878 | 115,644 | 115,912 | 101,201 | 132,148 | -2,766 | 2 | Ya |
| 2025-05 | 116,787 | 114,609 | 114,922 | 99,158 | 132,466 | 2,178 | 2 | Ya |
| 2025-06 | 356,163 | 309,802 | 310,671 | 267,518 | 358,769 | 46,361 | 13 | Ya |
| 2025-07 | 125,856 | 112,774 | 113,092 | 97,348 | 130,643 | 13,082 | 10 | Ya |
| 2025-08 | 130,954 | 114,470 | 114,793 | 98,807 | 132,616 | 16,484 | 13 | Ya |
| 2025-09 | 123,878 | 113,444 | 113,764 | 97,920 | 131,429 | 10,435 | 8 | Ya |
| 2025-10 | 119,197 | 114,594 | 114,917 | 98,912 | 132,761 | 4,603 | 4 | Ya |
| 2025-11 | 115,410 | 112,404 | 112,722 | 97,022 | 130,225 | 3,006 | 3 | Ya |
| 2025-12 | 110,158 | 112,567 | 112,885 | 97,163 | 130,414 | -2,410 | 2 | Ya |

## Grafik

- Fan chart per model: `data/hasil_08/grafik/08_fan_chart_*.png`
- Perbandingan semua model: `data/hasil_08/grafik/08_perbandingan_peramalan.png`
