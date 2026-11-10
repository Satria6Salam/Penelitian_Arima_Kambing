# Ringkasan Script 09: Peramalan dan Visualisasi Model Final

Dibuat otomatis oleh `09_peramalan_visualisasi.py` (statsmodels 0.15.0).

## Desain

- Model final: **SARIMA(1,0,0)x(1,1,0,12)** dengan transformasi log, model valid dari script 07 yang tidak memerlukan data masa depan.
- Interval 95%: Ŷ ± Z × SE dengan Z = 1.96, dihitung pada skala log lalu dikembalikan ke kg dengan exp(). Karena itu interval di kg tidak simetris (sisi atas lebih lebar). Ŷ = exp(ramalan log) adalah median ramalan.
- Bagian A memvalidasi ekstrapolasi pada data testing; Bagian B adalah peramalan utama Jan–Jun 2026.

## A. Validasi ekstrapolasi Apr–Sep 2025

Parameter dikunci dari 27 bulan training (Jan 2023–Mar 2025), lalu diekstrapolasi 6 bulan dan dibandingkan dengan aktual testing. MAPE **7,61%**, aktual di dalam interval 95% pada **5 dari 6** bulan. Fan chart: `data/hasil_09/validasi_apr_sep_2025/grafik/09_fan_chart_validasi.png`.

| h | Periode | Yhat_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Aktual_Kg | APE_% | Aktual_dalam_Interval |
|---|---|---|---|---|---|---|---|
| 1 | 2025-04 | 94.591 | 85.941 | 104.112 | 85.690 | 10,39 | Tidak |
| 2 | 2025-05 | 84.589 | 73.940 | 96.772 | 89.364 | 5,34 | Ya |
| 3 | 2025-06 | 269.022 | 228.447 | 316.802 | 274.672 | 2,06 | Ya |
| 4 | 2025-07 | 90.987 | 75.447 | 109.728 | 97.810 | 6,98 | Ya |
| 5 | 2025-08 | 95.426 | 77.525 | 117.461 | 102.546 | 6,94 | Ya |
| 6 | 2025-09 | 84.106 | 67.106 | 105.414 | 97.732 | 13,94 | Ya |

## B. Model final untuk peramalan (fit 36 bulan, Jan 2023–Dec 2025)

### Parameter terkunci

| Parameter | Koefisien | Std_Error | P_value | CI95_Bawah | CI95_Atas |
|---|---|---|---|---|---|
| ar.L1 | 0.9459 | 0.0560 | 0.0000 | 0.8361 | 1.0557 |
| ar.S.L12 | -0.7953 | 0.1571 | 0.0000 | -1.1033 | -0.4873 |
| sigma2 | 0.0068 | 0.0038 | 0.0741 | -0.0007 | 0.0143 |

LogL 18.9741; AIC -31.9482; BIC -28.4141; optimizer nm; konvergen True.

### Validitas residual

| Jumlah_Residual | Uji | Statistik | df | P_value | Keputusan |
|---|---|---|---|---|---|
| 24 | Ljung-Box lag 6 | 9.0589 | 4 | 0.0596 | Lulus (white noise) |
| 24 | Ljung-Box lag 9 | 10.8464 | 7 | 0.1455 | Lulus (white noise) |
| 24 | Ljung-Box lag 12 | 11.5533 | 10 | 0.3161 | Lulus (white noise) |
| 24 | Shapiro-Wilk | 0.9712 | - | 0.6959 | Lulus (normal) |

Model tetap valid (lulus seluruh uji) setelah di-fit ulang pada 36 bulan.

### Peramalan Jan–Jun 2026

| h | t | Periode | Yhat_Kg | SE_log | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Lebar_Interval_Kg |
|---|---|---|---|---|---|---|---|
| 1 | 37 | 2026-01 | 71.327 | 0.0827 | 60.653 | 83.880 | 23.226 |
| 2 | 38 | 2026-02 | 71.335 | 0.1138 | 57.069 | 89.168 | 32.099 |
| 3 | 39 | 2026-03 | 69.364 | 0.1358 | 53.157 | 90.514 | 37.357 |
| 4 | 40 | 2026-04 | 67.206 | 0.1528 | 49.817 | 90.665 | 40.848 |
| 5 | 41 | 2026-05 | 65.768 | 0.1665 | 47.456 | 91.146 | 43.689 |
| 6 | 42 | 2026-06 | 177.280 | 0.1779 | 125.095 | 251.233 | 126.137 |

Efek corong: SE skala log naik dari 0.0827 (h=1) menjadi 0.1779 (h=6); lebar interval relatif terhadap Ŷ naik dari 32,6% menjadi 71,2%.

### Contoh perhitungan manual

#### Kasus A: bulan ke-37 (2026-01), meramal 1 langkah ke depan

- Ŷ (skala log) = 11.1750 → Ŷ = exp(11.1750) = **71.327 kg**
- SE (skala log) = 0.0827
- Margin of Error = Z × SE = 1.96 × 0.0827 = 0.1621
- Batas bawah = exp(11.1750 − 0.1621) = exp(11.0129) = **60.653 kg**
- Batas atas = exp(11.1750 + 0.1621) = exp(11.3371) = **83.880 kg**
- Interval tidak simetris di kg: Ŷ − bawah = 10.674 kg, atas − Ŷ = 12.552 kg (lebar 23.226 kg).
- Interpretasi bisnis: dengan keyakinan 95%, permintaan 2026-01 berada di kisaran 60.653–83.880 kg.

#### Kasus B: bulan ke-38 (2026-02), meramal 2 langkah ke depan

- Ŷ (skala log) = 11.1751 → Ŷ = exp(11.1751) = **71.335 kg**
- SE (skala log) = 0.1138
- Margin of Error = Z × SE = 1.96 × 0.1138 = 0.2231
- Batas bawah = exp(11.1751 − 0.2231) = exp(10.9520) = **57.069 kg**
- Batas atas = exp(11.1751 + 0.2231) = exp(11.3983) = **89.168 kg**
- Interval tidak simetris di kg: Ŷ − bawah = 14.266 kg, atas − Ŷ = 17.833 kg (lebar 32.099 kg).
- Interpretasi bisnis: dengan keyakinan 95%, permintaan 2026-02 berada di kisaran 57.069–89.168 kg.

#### Bulan puncak: bulan ke-42 (2026-06), h = 6

- Ŷ (skala log) = 12.0855 → Ŷ = exp(12.0855) = **177.280 kg**
- SE (skala log) = 0.1779
- Margin of Error = Z × SE = 1.96 × 0.1779 = 0.3487
- Batas bawah = exp(12.0855 − 0.3487) = exp(11.7368) = **125.095 kg**
- Batas atas = exp(12.0855 + 0.3487) = exp(12.4341) = **251.233 kg**
- Interval tidak simetris di kg: Ŷ − bawah = 52.184 kg, atas − Ŷ = 73.953 kg (lebar 126.137 kg).
- Interpretasi bisnis: dengan keyakinan 95%, permintaan 2026-06 berada di kisaran 125.095–251.233 kg.

### Fan chart

`data/hasil_09/grafik/09_fan_chart.png`: garis hitam = aktual historis Jan 2023–Des 2025, garis biru putus-putus = peramalan Jan–Jun 2026 (tersambung dari Des 2025), pita biru muda = interval 95%, garis merah = perkiraan Iduladha 2026 (±27 Mei).

### Keterbatasan: pergeseran Iduladha 2026

Iduladha 2026 diperkirakan jatuh sekitar **27 May 2026** (akhir Mei), bukan Juni. Model SARIMA musiman lag 12 meniru pola 2023–2025, ketika Iduladha selalu jatuh di bulan Juni, sehingga lonjakan diramalkan di **2026-06**. Dalam kenyataan, lonjakan permintaan 2026 kemungkinan besar bergeser ke Mei (atau terbagi antara Mei dan Juni). Model tidak diubah dan tidak ditambahkan dummy baru; hasil Mei dan Juni 2026 perlu dibaca dengan catatan ini.

### Keterbatasan: level ramalan 2026 lebih rendah dari 2025

| Periode | Yhat_Kg | Aktual_Tahun_Lalu_Kg | Perubahan_% |
|---|---|---|---|
| 2026-01 | 71.327 | 85.388 | -16,5 |
| 2026-02 | 71.335 | 82.547 | -13,6 |
| 2026-03 | 69.364 | 90.640 | -23,5 |
| 2026-04 | 67.206 | 85.690 | -21,6 |
| 2026-05 | 65.768 | 89.364 | -26,4 |
| 2026-06 | 177.280 | 274.672 | -35,5 |

Ramalan 2026 rata-rata **-22,8%** dibanding bulan yang sama tahun 2025. Penurunan ini bukan tren yang terlihat di 2025 (Jul–Des 2025 justru lebih tinggi dari 2024), melainkan efek koefisien AR musiman (-0.80) yang ikut mengulang penurunan level tajam dari 2023 ke 2024 (misalnya Desember 2023 → Desember 2024 turun sekitar 31%). Dengan data hanya 3 tahun, pola ini sebaiknya dibaca sebagai skenario konservatif, bukan prediksi penurunan pasar yang pasti; ramalan perlu diperbarui setelah data 2026 tersedia.

### Implikasi manajerial

- **Pemesanan stok bulan normal (garis tengah):** Ŷ berkisar 65.768–71.335 kg per bulan (rata-rata 69.000 kg).
- **Batas bawah bulan normal:** 47.456–60.653 kg, volume minimum yang hampir pasti terserap.
- **Persiapan puncak Iduladha:** Ŷ puncak 177.280 kg (±2,57 kali bulan normal) dengan batas atas 95% **251.233 kg** sebagai acuan kapasitas cold storage, pasokan ternak, dan modal cadangan (stok pengaman 73.953 kg di atas Ŷ).
- Karena Iduladha 2026 jatuh ±27 Mei, persiapan kapasitas puncak sebaiknya sudah siap pada pertengahan Mei 2026, bukan menunggu Juni.
- Interval melebar untuk bulan yang lebih jauh; rencana April–Juni sebaiknya diperbarui setelah data aktual Januari–Maret 2026 tersedia.
