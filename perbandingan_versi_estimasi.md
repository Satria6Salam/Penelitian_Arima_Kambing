# Perbandingan Versi Estimasi Model (Bukti untuk Bab 3/4)

Dokumen ini merangkum angka dari empat versi estimasi yang dijalankan selama
penelitian, supaya alasan perubahan metode tetap terdokumentasi walaupun file
hasil versi lama sudah dihapus. Data: training Jan 2023–Mar 2025 (27 bulan),
testing Apr–Des 2025 (9 bulan), target `Total_Kuantitas_Kg`.

| Versi | Pengaturan | Masalah utama |
|---|---|---|
| V0 | Skala kg, `enforce_stationarity/invertibility=False`, optimizer lbfgs | Log-likelihood SARIMA D=1 hanya dihitung dari 1–2 observasi → AIC/BIC tidak valid |
| V1 | Skala kg, `enforce_*=True`, optimizer lbfgs saja | 18 pelanggaran model bersarang; 26 dari 28 model terjebak optimum lokal |
| V2 | Skala ribu kg, `enforce_*=True`, multi-optimizer | Estimasi sudah benar (0 pelanggaran), tetapi semua model gagal Shapiro-Wilk |
| V3 (final) | Transformasi log (ln kg, ln Rp/kg), `enforce_*=True`, multi-optimizer | Tiga model lulus Ljung-Box dan Shapiro-Wilk |

## V0 → V1: perbaikan `enforce_stationarity/invertibility`

Dengan `enforce_*=False`, statsmodels memakai inisialisasi diffuse untuk semua
state sehingga `loglikelihood_burn` = jumlah state.

| Model | Burn | nobs efektif | LogL | AIC | BIC |
|---|---|---|---|---|---|
| SARIMA(0,0,1)x(0,1,1,12), V0 | 26 | 1 | −11,74 | 29,49 | 23,49 |
| SARIMA(1,0,0)x(1,1,0,12), V0 | 25 | 2 | −23,00 | 52,00 | 48,08 |
| SARIMA(0,0,1)x(0,0,1,12), V0 | 14 | 13 | −154,78 | 317,56 | 319,82 |
| SARIMA(1,0,0)x(1,1,0,12), V1 | 12 | 15 | −173,14 | 352,28 | 354,41 |

BIC < AIC pada V0 terjadi karena ln(1) = 0, tanda bahwa likelihood tidak valid.

## V1 → V2: multi-optimizer dan penskalaan

Pada skala kg (permintaan ±100.000 kg, varians residual ±1e9), optimizer lbfgs
sering berhenti di optimum lokal.

| Ukuran | V1 (kg, lbfgs) | V2 (ribu kg, multi-optimizer) | V3 (log, multi-optimizer) |
|---|---|---|---|
| Pelanggaran model bersarang (142 pasangan) | 18 | 0 | 0 |
| Model tidak konvergen | 0 | 0 | 0 |
| Contoh: AIC ARIMA(0,0,2) setara kg | 707,69 | 670,53 | 644,01 |
| Contoh: AIC ARIMAX(2,0,0)+Harga setara kg (peringkat dalam kelompok D=0) | 669,61 (20) | 620,04 (2) | 579,83 (2) |

Pada V1, ARIMA(0,0,2) memiliki LogL lebih buruk dari ARIMA(0,0,0), padahal
ARIMA(0,0,0) adalah kasus khusus darinya, bukti estimasi belum optimum.

## V2 → V3: transformasi log

Lonjakan Iduladha bersifat perkalian (volume × 2,717). Pada skala level,
residual Juni 2023 dan Juni 2024 sekitar +62.000 kg dan −59.000 kg sehingga
residual tidak normal. Transformasi log mengubah efek perkalian menjadi
penjumlahan (sesuai saran dokumen alur bila uji Shapiro-Wilk gagal).

### Diagnostik residual model shortlist (Shapiro-Wilk W; p)

| Skenario | V1 (kg, lbfgs) | V2 (ribu kg) | V3 (log, final) |
|---|---|---|---|
| ARIMA | 0,542; <0,001 (gagal) | 0,542; <0,001 (gagal) | 0,739; <0,001 (gagal) |
| SARIMA D=0 | 0,459; <0,001 (gagal) | 0,540; <0,001 (gagal) | 0,714; <0,001 (gagal) |
| SARIMA D=1 | 0,950; 0,524 (lulus*) | 0,791; 0,003 (gagal) | 0,930; 0,273 (lulus) |
| ARIMAX Harga | 0,883; 0,006 (gagal) | 0,834; 0,001 (gagal) | 0,962; 0,415 (lulus) |
| ARIMAX Harga+Iduladha | 0,858; 0,002 (gagal) | 0,829; 0,001 (gagal) | 0,981; 0,874 (lulus) |

\* Lulusnya SARIMA D=1 pada V1 berasal dari estimasi yang belum optimal; setelah
estimasi diperbaiki (V2) model ini gagal. Semua model lulus Ljung-Box di ketiga versi.

### Rolling origin 9 bulan (MAPE % / RMSE kg)

| Skenario | V1 (kg, lbfgs) | V2 (ribu kg) | V3 (log, final) |
|---|---|---|---|
| ARIMA | 24,46 / 58.173 | 24,46 / 58.173 | 17,54 / 58.572 |
| SARIMA D=0 | 14,93 / 56.424 | 11,13 / 33.696 | 8,36 / 22.987 |
| SARIMA D=1 | 5,74 / 10.007 | 11,40 / 19.428 | 6,59 / 7.395 |
| ARIMAX Harga | 4,75 / 7.799 | 5,54 / 7.525 | 4,12 / 10.525 |
| ARIMAX Harga+Iduladha | 4,01 / 5.063 | 4,04 / 5.470 | 4,59 / 11.305 |
| Seasonal naive | 14,73 / 28.534 | 14,73 / 28.534 | 14,73 / 28.534 |

Model shortlist berbeda antar-versi pada beberapa skenario karena peringkat AIC
berubah setelah estimasi diperbaiki (contoh ARIMAX Harga: (1,0,2) → (1,0,1) → (2,0,0)).

## Kesimpulan

V3 (log + multi-optimizer) adalah satu-satunya versi yang menghasilkan model
dengan residual white noise dan berdistribusi normal, tanpa pelanggaran model
bersarang dan seluruh model konvergen. Versi ini dipakai di script 06–08.
