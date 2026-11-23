# Ringkasan Validasi di Dalam Data Latih (Script 17)

Pemilihan model final diulang tanpa data uji: rolling origin 1 bulan di dalam data latih, latih awal Jan 2023 - Sep 2024, 6 putaran (target Okt 2024 - Mar 2025).

| Model | MAPE validasi (%) | RMSE (kg) | Ljung-Box | Shapiro-Wilk | Lebih baik dari naive | Aturan 1 | Butuh eksogen | Model final |
|---|---:|---:|---|---|---|---|---|---|
| ARIMA: ARIMA(1, 0, 1) | 7,27 | 11.506 | Lulus | Gagal | Ya | Gagal | Tidak | Tidak |
| SARIMA D=0: SARIMA(1, 0, 0)x(1, 0, 0, 12) | 7,87 | 9.971 | Lulus | Gagal | Ya | Gagal | Tidak | Tidak |
| SARIMA D=1: SARIMA(1, 0, 0)x(1, 1, 0, 12) | 7,53 | 9.906 | Lulus | Lulus | Ya | Lolos | Tidak | Ya |
| ARIMAX Harga: ARIMAX(0, 0, 2) + Harga | 8,96 | 11.300 | Lulus | Lulus | Tidak | Gagal | Ya | Tidak |
| ARIMAX Harga+Iduladha: ARIMAX(1, 0, 0) + Harga + Iduladha | 8,04 | 10.884 | Lulus | Lulus | Tidak | Gagal | Ya | Tidak |
| Seasonal naive: y[t-12] | 7,98 | 10.450 | - | - | - | - | - | Tidak |

**Model final (tanpa data uji): SARIMA D=1.** Model final script 07 (MAPE rolling origin data uji): SARIMA D=1.
Hasil SAMA: pemilihan model tidak bergantung pada data uji.

Catatan: jendela validasi Okt 2024 - Mar 2025 tidak memuat bulan Iduladha.

## Angka pendukung evaluasi (dikutip di artikel)

| Besaran | Nilai | Cara hitung |
|---|---:|---|
| MAPE multilangkah data uji (%) | 9,071 | Rata-rata APE_% SARIMA D=1 di 08_peramalan_testing.csv |
| Bootstrap 95% MAPE uji - batas bawah (%) | 5,815 | Persentil 2,5 dari 10000 rata-rata 9 APE yang diambil ulang (seed 42) |
| Bootstrap 95% MAPE uji - batas atas (%) | 11,911 | Persentil 97,5 dari 10000 rata-rata 9 APE yang diambil ulang (seed 42) |
| Porsi Juni 2025 terhadap variasi total data uji (%) | 88,276 | (y Juni - rata-rata uji)^2 / jumlah (y - rata-rata uji)^2 |
| Rata-rata pertumbuhan tahunan aktual Apr-Des 2024 (%) | 6,430 | Rata-rata ln y_t - ln y_(t-12), Apr-Des 2024 |
| Bulan uji yang diramal tumbuh negatif dibanding tahun lalu | 7,000 | Jumlah bulan Apr-Des 2025 dengan ln ramalan - ln aktual 12 bulan sebelumnya < 0 |
| Selisih maksimum MAPE SARIMA skenario S x 0,8 vs S x 1,2 per seed (poin) | 0,001 | Maks |MAPE S x 0,8 - MAPE S x 1,2| per seed di 15_hasil_per_seed.csv |
