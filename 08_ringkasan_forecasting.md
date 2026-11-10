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
| ARIMAX Harga | ARIMAX(2, 0, 0) + Harga | 3.84 | 9,318.33 | 5,463.25 | 86,831,344.02 | 0.97 | 3,814.17 | 13.40 | 2025-08 |
| ARIMAX Harga+Iduladha | ARIMAX(2, 0, 0) + Harga + Iduladha | 4.54 | 10,722.75 | 6,465.63 | 114,977,429.29 | 0.96 | 5,490.47 | 12.82 | 2025-08 |
| SARIMA D=1 | SARIMA(1, 0, 0)x(1, 1, 0, 12) | 6.98 | 7,818.15 | 6,936.90 | 61,123,460.52 | 0.98 | 2,590.12 | 13.94 | 2025-09 |
| Seasonal naive | y[t-12] | 14.73 | 28,533.76 | 19,596.61 | 814,175,425.30 | 0.75 | 19,596.61 | 27.67 | 2025-06 |

### Terhadap target akurasi

Target: MAPE < 15%, RMSE < 10% × ȳ, MAE < 8% × ȳ, MSE < (10% × ȳ)², R² > 0.7 (ȳ = rata-rata permintaan aktual periode evaluasi). Pada data testing: ȳ = 113,751 kg → MAPE < 15%, RMSE < 11,375 kg, MAE < 9,100 kg, MSE < 129,391,859 kg², R² > 0.7.

| Label | RMSE_%_rata2 | MAE_%_rata2 | Target_MAPE_% | Target_RMSE | Target_MAE | Target_MSE | Target_R2 |
|---|---|---|---|---|---|---|---|
| ARIMAX Harga | 8.19 | 4.80 | Lulus | Lulus | Lulus | Lulus | Lulus |
| ARIMAX Harga+Iduladha | 9.43 | 5.68 | Lulus | Lulus | Lulus | Lulus | Lulus |
| SARIMA D=1 | 6.87 | 6.10 | Lulus | Lulus | Lulus | Lulus | Lulus |
| Seasonal naive | 25.08 | 17.23 | Lulus | Gagal | Gagal | Gagal | Lulus |

> Target RMSE/MAE/MSE relatif terhadap rata-rata permintaan aktual, karena data penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM).

## Interval kepercayaan 95%

| Label | Jumlah_Dalam_CI | Cakupan_CI_95_% | Lebar_CI_rata2_Kg | Lebar_CI_rata2_%_aktual | MAPE_mean_lognormal_% |
|---|---|---|---|---|---|
| ARIMAX Harga | 9/9 | 100.00 | 47,995.56 | 42.98 | 3.91 |
| ARIMAX Harga+Iduladha | 9/9 | 100.00 | 49,228.77 | 44.48 | 4.26 |
| SARIMA D=1 | 8/9 | 88.89 | 43,129.33 | 39.07 | 6.78 |

## Multi-step (08) vs rolling origin 1 langkah (07)

| Label | MAPE_MultiStep | MAPE_Rolling | MAPE_h1_3 | MAPE_h4_6 | MAPE_h7_9 |
|---|---|---|---|---|---|
| SARIMA D=1 | 6.98 | 6.59 | 5.93 | 9.29 | 5.72 |
| ARIMAX Harga | 3.84 | 4.00 | 4.25 | 5.82 | 1.45 |
| ARIMAX Harga+Iduladha | 4.54 | 4.59 | 4.39 | 7.49 | 1.75 |
| Seasonal naive | 14.73 | 14.73 | 15.45 | 18.08 | 10.65 |

### Juni 2025 (Iduladha, horizon 3)

| Label | Aktual_Kg | Prediksi_MultiStep_Kg | APE_MultiStep_% | Prediksi_Rolling_Kg | APE_Rolling_% |
|---|---|---|---|---|---|
| SARIMA D=1 | 274,672.1 | 269,021.5 | 2.1 | 273,123.1 | 0.6 |
| ARIMAX Harga | 274,672.1 | 250,758.8 | 8.7 | 246,391.1 | 10.3 |
| ARIMAX Harga+Iduladha | 274,672.1 | 246,323.9 | 10.3 | 242,988.4 | 11.5 |
| Seasonal naive | 274,672.1 | 198,665.4 | 27.7 | 198,665.4 | 27.7 |

## Peramalan per bulan

### SARIMA D=1: SARIMA(1, 0, 0)x(1, 1, 0, 12)

| Periode | Aktual_Kg | Prediksi_Kg | Prediksi_Mean_Lognormal_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Error_Kg | APE_% | Dalam_CI_95 |
|---|---|---|---|---|---|---|---|---|
| 2025-04 | 85,690 | 94,591 | 94,704 | 85,941 | 104,112 | -8,901 | 10 | Tidak |
| 2025-05 | 89,364 | 84,589 | 84,789 | 73,940 | 96,772 | 4,775 | 5 | Ya |
| 2025-06 | 274,672 | 269,022 | 269,959 | 228,447 | 316,802 | 5,651 | 2 | Ya |
| 2025-07 | 97,810 | 90,987 | 91,403 | 75,447 | 109,728 | 6,823 | 7 | Ya |
| 2025-08 | 102,546 | 95,426 | 95,964 | 77,525 | 117,461 | 7,120 | 7 | Ya |
| 2025-09 | 97,732 | 84,106 | 84,666 | 67,106 | 105,414 | 13,626 | 14 | Ya |
| 2025-10 | 94,733 | 90,330 | 91,021 | 70,913 | 115,063 | 4,403 | 5 | Ya |
| 2025-11 | 92,390 | 91,916 | 92,708 | 71,105 | 118,819 | 474 | 1 | Ya |
| 2025-12 | 88,817 | 99,476 | 100,426 | 75,922 | 130,338 | -10,659 | 12 | Ya |

### ARIMAX Harga: ARIMAX(2, 0, 0) + Harga

| Periode | Aktual_Kg | Prediksi_Kg | Prediksi_Mean_Lognormal_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Error_Kg | APE_% | Dalam_CI_95 |
|---|---|---|---|---|---|---|---|---|
| 2025-04 | 85,690 | 87,607 | 87,948 | 73,701 | 104,136 | -1,917 | 2 | Ya |
| 2025-05 | 89,364 | 90,976 | 91,383 | 75,587 | 109,497 | -1,611 | 2 | Ya |
| 2025-06 | 274,672 | 250,759 | 252,179 | 203,605 | 308,833 | 23,913 | 9 | Ya |
| 2025-07 | 97,810 | 95,118 | 95,707 | 76,502 | 118,263 | 2,692 | 3 | Ya |
| 2025-08 | 102,546 | 88,802 | 89,398 | 70,793 | 111,393 | 13,744 | 13 | Ya |
| 2025-09 | 97,732 | 99,003 | 99,699 | 78,500 | 124,861 | -1,271 | 1 | Ya |
| 2025-10 | 94,733 | 96,368 | 97,071 | 76,090 | 122,052 | -1,635 | 2 | Ya |
| 2025-11 | 92,390 | 90,991 | 91,671 | 71,636 | 115,575 | 1,399 | 2 | Ya |
| 2025-12 | 88,817 | 89,803 | 90,486 | 70,549 | 114,313 | -986 | 1 | Ya |

### ARIMAX Harga+Iduladha: ARIMAX(2, 0, 0) + Harga + Iduladha

| Periode | Aktual_Kg | Prediksi_Kg | Prediksi_Mean_Lognormal_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Error_Kg | APE_% | Dalam_CI_95 |
|---|---|---|---|---|---|---|---|---|
| 2025-04 | 85,690 | 87,510 | 87,807 | 74,464 | 102,842 | -1,820 | 2 | Ya |
| 2025-05 | 89,364 | 90,013 | 90,390 | 75,239 | 107,687 | -648 | 1 | Ya |
| 2025-06 | 274,672 | 246,324 | 247,705 | 200,217 | 303,048 | 28,348 | 10 | Ya |
| 2025-07 | 97,810 | 92,023 | 92,620 | 73,632 | 115,008 | 5,787 | 6 | Ya |
| 2025-08 | 102,546 | 89,399 | 90,059 | 70,484 | 113,389 | 13,148 | 13 | Ya |
| 2025-09 | 97,732 | 94,094 | 94,856 | 73,365 | 120,680 | 3,638 | 4 | Ya |
| 2025-10 | 94,733 | 93,185 | 93,998 | 71,970 | 120,655 | 1,548 | 2 | Ya |
| 2025-11 | 92,390 | 91,056 | 91,899 | 69,782 | 118,815 | 1,334 | 1 | Ya |
| 2025-12 | 88,817 | 90,737 | 91,619 | 69,085 | 119,174 | -1,920 | 2 | Ya |

## Grafik

- Fan chart per model: `data/hasil_08/grafik/08_fan_chart_*.png`
- Perbandingan semua model: `data/hasil_08/grafik/08_perbandingan_peramalan.png`
