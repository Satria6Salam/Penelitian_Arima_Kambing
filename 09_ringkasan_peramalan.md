# Ringkasan Script 09: Peramalan dan Visualisasi Model Final

Dibuat otomatis oleh `09_peramalan_visualisasi.py` (statsmodels 0.15.0).

## Desain

- Model final: **SARIMA(1,0,0)x(1,1,0,12)** dengan transformasi log, model valid dari script 07 yang tidak memerlukan data masa depan.
- Interval 95%: Ŷ ± Z × SE dengan Z = 1.96, dihitung pada skala log lalu dikembalikan ke kg dengan exp(). Karena itu interval di kg tidak simetris (sisi atas lebih lebar). Ŷ = exp(ramalan log) adalah median ramalan.
- Bagian A memvalidasi ekstrapolasi pada data testing; Bagian B adalah peramalan utama Jan–Jun 2026.

## A. Validasi ekstrapolasi Apr–Sep 2025

Parameter dikunci dari 27 bulan training (Jan 2023–Mar 2025), lalu diekstrapolasi 6 bulan dan dibandingkan dengan aktual testing. MAPE **10,46%**, aktual di dalam interval 95% pada **6 dari 6** bulan. Fan chart: `data/hasil_09/validasi_apr_sep_2025/grafik/09_fan_chart_validasi.png`.

| h | Periode | Yhat_Kg | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Aktual_Kg | APE_% | Aktual_dalam_Interval |
|---|---|---|---|---|---|---|---|
| 1 | 2025-04 | 116.699 | 100.411 | 135.630 | 112.878 | 3,39 | Ya |
| 2 | 2025-05 | 104.256 | 88.486 | 122.836 | 116.787 | 10,73 | Ya |
| 3 | 2025-06 | 312.294 | 264.403 | 368.861 | 356.163 | 12,32 | Ya |
| 4 | 2025-07 | 112.492 | 95.196 | 132.929 | 125.856 | 10,62 | Ya |
| 5 | 2025-08 | 115.319 | 97.580 | 136.283 | 130.954 | 11,94 | Ya |
| 6 | 2025-09 | 106.815 | 90.382 | 126.234 | 123.878 | 13,77 | Ya |

## B. Model final untuk peramalan (fit 36 bulan, Jan 2023–Dec 2025)

### Parameter terkunci

| Parameter | Koefisien | Std_Error | P_value | CI95_Bawah | CI95_Atas |
|---|---|---|---|---|---|
| ar.L1 | 0.6049 | 0.2286 | 0.0081 | 0.1569 | 1.0528 |
| ar.S.L12 | -0.6906 | 0.1956 | 0.0004 | -1.0739 | -0.3073 |
| sigma2 | 0.0058 | 0.0028 | 0.0397 | 0.0003 | 0.0114 |

LogL 23.5529; AIC -41.1057; BIC -37.5716; optimizer bfgs; konvergen True.

### Validitas residual

| Jumlah_Residual | Uji | Statistik | df | P_value | Keputusan |
|---|---|---|---|---|---|
| 24 | Ljung-Box lag 6 | 7.3915 | 4 | 0.1166 | Lulus (white noise) |
| 24 | Ljung-Box lag 9 | 9.6395 | 7 | 0.2099 | Lulus (white noise) |
| 24 | Ljung-Box lag 12 | 11.9561 | 10 | 0.2880 | Lulus (white noise) |
| 24 | Shapiro-Wilk | 0.9759 | - | 0.8092 | Lulus (normal) |

Model tetap valid (lulus seluruh uji) setelah di-fit ulang pada 36 bulan.

### Peramalan Jan–Jun 2026

| h | t | Periode | Yhat_Kg | SE_log | Batas_Bawah_95_Kg | Batas_Atas_95_Kg | Lebar_Interval_Kg |
|---|---|---|---|---|---|---|---|
| 1 | 37 | 2026-01 | 108.757 | 0.0764 | 93.632 | 126.325 | 32.693 |
| 2 | 38 | 2026-02 | 111.595 | 0.0893 | 93.679 | 132.937 | 39.259 |
| 3 | 39 | 2026-03 | 112.341 | 0.0936 | 93.519 | 134.952 | 41.433 |
| 4 | 40 | 2026-04 | 109.806 | 0.0951 | 91.137 | 132.299 | 41.162 |
| 5 | 41 | 2026-05 | 109.254 | 0.0956 | 90.582 | 131.776 | 41.194 |
| 6 | 42 | 2026-06 | 301.478 | 0.0958 | 249.855 | 363.766 | 113.911 |

Efek corong: SE skala log naik dari 0.0764 (h=1) menjadi 0.0958 (h=6); lebar interval relatif terhadap Ŷ naik dari 30,1% menjadi 37,8%.

### Contoh perhitungan manual

#### Kasus A: bulan ke-37 (2026-01), meramal 1 langkah ke depan

- Ŷ (skala log) = 11.5969 → Ŷ = exp(11.5969) = **108.757 kg**
- SE (skala log) = 0.0764
- Margin of Error = Z × SE = 1.96 × 0.0764 = 0.1497
- Batas bawah = exp(11.5969 − 0.1497) = exp(11.4471) = **93.632 kg**
- Batas atas = exp(11.5969 + 0.1497) = exp(11.7466) = **126.325 kg**
- Interval tidak simetris di kg: Ŷ − bawah = 15.125 kg, atas − Ŷ = 17.568 kg (lebar 32.693 kg).
- Interpretasi bisnis: dengan keyakinan 95%, permintaan 2026-01 berada di kisaran 93.632–126.325 kg.

#### Kasus B: bulan ke-38 (2026-02), meramal 2 langkah ke depan

- Ŷ (skala log) = 11.6226 → Ŷ = exp(11.6226) = **111.595 kg**
- SE (skala log) = 0.0893
- Margin of Error = Z × SE = 1.96 × 0.0893 = 0.1750
- Batas bawah = exp(11.6226 − 0.1750) = exp(11.4476) = **93.679 kg**
- Batas atas = exp(11.6226 + 0.1750) = exp(11.7976) = **132.937 kg**
- Interval tidak simetris di kg: Ŷ − bawah = 17.916 kg, atas − Ŷ = 21.343 kg (lebar 39.259 kg).
- Interpretasi bisnis: dengan keyakinan 95%, permintaan 2026-02 berada di kisaran 93.679–132.937 kg.

#### Bulan puncak: bulan ke-42 (2026-06), h = 6

- Ŷ (skala log) = 12.6165 → Ŷ = exp(12.6165) = **301.478 kg**
- SE (skala log) = 0.0958
- Margin of Error = Z × SE = 1.96 × 0.0958 = 0.1878
- Batas bawah = exp(12.6165 − 0.1878) = exp(12.4286) = **249.855 kg**
- Batas atas = exp(12.6165 + 0.1878) = exp(12.8043) = **363.766 kg**
- Interval tidak simetris di kg: Ŷ − bawah = 51.623 kg, atas − Ŷ = 62.289 kg (lebar 113.911 kg).
- Interpretasi bisnis: dengan keyakinan 95%, permintaan 2026-06 berada di kisaran 249.855–363.766 kg.

### Fan chart

`data/hasil_09/grafik/09_fan_chart.png`: garis hitam = aktual historis Jan 2023–Des 2025, garis biru putus-putus = peramalan Jan–Jun 2026 (tersambung dari Des 2025), pita biru muda = interval 95%, garis merah = perkiraan Iduladha 2026 (±27 Mei).

### Keterbatasan: pergeseran Iduladha 2026

Iduladha 2026 diperkirakan jatuh sekitar **27 May 2026** (akhir Mei), bukan Juni. Model SARIMA musiman lag 12 meniru pola 2023–2025, ketika Iduladha selalu jatuh di bulan Juni, sehingga lonjakan diramalkan di **2026-06**. Dalam kenyataan, lonjakan permintaan 2026 kemungkinan besar bergeser ke Mei (atau terbagi antara Mei dan Juni). Model tidak diubah dan tidak ditambahkan dummy baru; hasil Mei dan Juni 2026 perlu dibaca dengan catatan ini.

### Keterbatasan: level ramalan 2026 lebih rendah dari 2025

| Periode | Yhat_Kg | Aktual_Tahun_Lalu_Kg | Perubahan_% |
|---|---|---|---|
| 2026-01 | 108.757 | 115.284 | -5,7 |
| 2026-02 | 111.595 | 110.522 | 1,0 |
| 2026-03 | 112.341 | 120.367 | -6,7 |
| 2026-04 | 109.806 | 112.878 | -2,7 |
| 2026-05 | 109.254 | 116.787 | -6,5 |
| 2026-06 | 301.478 | 356.163 | -15,4 |

Ramalan 2026 rata-rata **-6,0%** dibanding bulan yang sama tahun 2025. Penurunan ini bukan tren yang terlihat di 2025 (Jul–Des 2025 justru lebih tinggi dari 2024), melainkan efek koefisien AR musiman (-0.69) yang ikut mengulang penurunan level tajam dari 2023 ke 2024 (misalnya Desember 2023 → Desember 2024 turun sekitar 31%). Dengan data hanya 3 tahun, pola ini sebaiknya dibaca sebagai skenario konservatif, bukan prediksi penurunan pasar yang pasti; ramalan perlu diperbarui setelah data 2026 tersedia.

### Implikasi manajerial

- **Pemesanan stok bulan normal (garis tengah):** Ŷ berkisar 108.757–112.341 kg per bulan (rata-rata 110.351 kg).
- **Batas bawah bulan normal:** 90.582–93.679 kg, volume minimum yang hampir pasti terserap.
- **Persiapan puncak Iduladha:** Ŷ puncak 301.478 kg (±2,73 kali bulan normal) dengan batas atas 95% **363.766 kg** sebagai acuan kapasitas cold storage, pasokan ternak, dan modal cadangan (stok pengaman 62.289 kg di atas Ŷ).
- Karena Iduladha 2026 jatuh ±27 Mei, persiapan kapasitas puncak sebaiknya sudah siap pada pertengahan Mei 2026, bukan menunggu Juni.
- Interval melebar untuk bulan yang lebih jauh; rencana April–Juni sebaiknya diperbarui setelah data aktual Januari–Maret 2026 tersedia.
