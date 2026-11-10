# Pembagian Presentasi untuk 2 Orang

**Judul:** Prediksi Permintaan Daging Kambing di Pasar Lokal Menggunakan ARIMA/SARIMA/ARIMAX
**Durasi total:** ±20 menit (Presenter 1 ±9 menit, Presenter 2 ±11 menit termasuk demo Access)

| | Presenter 1 — "Data & Pembentukan Model" | Presenter 2 — "Validasi, Ramalan & Sistem" |
|---|---|---|
| Fokus | Dari data mentah sampai model terpilih | Dari pengujian model sampai sistem siap dipakai pengguna (tingkat kabupaten dan UMKM) |
| Pertanyaan dosen yang dijawab | [1] generate data, [2] pra-proses, [3] pembagian data, [4] stasioneritas, [5] ACF/PACF, [6] skenario, [7] pemilihan model, [8] AIC/BIC | [9] Ljung-Box, Shapiro-Wilk, Q-Q, rolling origin, MAPE/RMSE/MAE/MSE/R², ramalan & interval 95%, MS Access, rekomendasi |
| Log terminal | `log_terminal\03…06_*.txt` | `log_terminal\07…09_*.txt` |

---

## PRESENTER 1 — Data & Pembentukan Model (±9 menit)

### 1. Pembukaan (±1 menit)
- Latar belakang: permintaan daging kambing melonjak tajam saat Iduladha, sehingga pasokan wilayah
  dan pelaku usaha sering kelebihan/kekurangan stok.
- Ruang lingkup: "pasar lokal" = pasar daging kambing **Kabupaten Malang secara agregat**.
- Tujuan: meramal permintaan bulanan dan menyediakan sistem peramalan di MS Access.
- Alur penelitian: generate data → pra-proses → eksplorasi → pemodelan → validasi → peramalan → implementasi.

### 2. Data penelitian (±2 menit) — `[1]`, `[2]`
- Data 36 bulan (Jan 2023–Des 2025) dibangkitkan dari data BPS Kabupaten Malang (sintetis, dikalibrasi BPS).
- Baseline = produksi kabupaten, **tidak dibagi jumlah UMKM** karena jumlahnya tidak diketahui pasti;
  produksi daging dipakai sebagai proksi permintaan. Dengan log dan differencing musiman, skala data
  tidak memengaruhi parameter maupun MAPE.
- Rumus inti: baseline μ = karkas tahunan / 12; tren linier dari pertumbuhan produksi nasional;
  faktor Iduladha **S = 1 + (22.359 − 8.229) / 8.229 = 2,717**; white noise 5%.
- Pra-proses: agregasi bulanan, interpolasi linier (tidak ada bulan kosong), IQR —
  outlier hanya bulan Juni (Iduladha) dan **dipertahankan** sebagai pola musiman.
- Tampilkan: `data\eksplorasi\time_series_plot.png`.

### 3. Eksplorasi data (±2 menit) — `[4]`, `[5]`
- Uji ADF: t-ADF **−5,7452** < kritis 5% −2,9485, p = 0,000001 → data **stasioner (d = 0)**.
- ACF lag 12 = **0,3876**, PACF lag 12 = **0,6007**, keduanya signifikan → pola musiman **m = 12**.
- Tampilkan: `data\eksplorasi\acf_pacf_plot.png` dan `time_series_decomposition.png`.

### 4. Pembagian data & skenario (±1,5 menit) — `[3]`, `[6]`
- Kronologis 75% : 25% → training 27 bulan (Jan 2023–Mar 2025), testing 9 bulan (Apr–Des 2025).
- 4 skenario, 28 kandidat: ARIMA (8), SARIMA D=0/D=1 (4), ARIMAX + Harga (8), ARIMAX + Harga + Iduladha (8).

### 5. Estimasi & pemilihan model (±2,5 menit) — `[7]`, `[8]`
- Estimasi MLE dengan statsmodels; data ditransformasi **log** dan memakai **multi-optimizer**
  (alasan: lonjakan Iduladha bersifat perkalian; optimizer default sempat terjebak optimum lokal).
- AIC = −2·LL + 2k, BIC = −2·LL + k·ln n; dibandingkan **hanya dalam kelompok differencing yang sama**.
- Contoh: SARIMA(1,0,0)x(1,1,0,12) LL 9,2738 → AIC −12,55; terbaik di kelompok D=1.
- Tampilkan: `data\laporan\07_plot_aic_bic.png`.

**Kalimat transisi:**
> "Model dengan AIC terendah belum tentu layak. Selanjutnya rekan saya akan menjelaskan
> pengujian kelayakan model, hasil ramalan, dan sistem di MS Access."

---

## PRESENTER 2 — Validasi, Ramalan & Sistem (±11 menit)

### 6. Validasi diagnostik (±2 menit) — `[9]`
- Ljung-Box (white noise) dan Shapiro-Wilk (normalitas) pada 5 model shortlist.
- Tiga model lulus keduanya; model final **SARIMA(1,0,0)x(1,1,0,12) log**:
  Ljung-Box lag 6 Q = 7,49, p = 0,11; Shapiro-Wilk W = 0,930, p = 0,27.
- Tampilkan: Q-Q plot `data\hasil_07\grafik\07_qq_SARIMA_D1.png`, `data\laporan\08_plot_ljungbox_shapiro.png`.

### 7. Evaluasi kinerja (±2 menit) — `[9]`
- Rolling origin 9 putaran (latih → ramal 1 bulan → tambah data aktual → latih ulang).
- Target relatif terhadap rata-rata permintaan testing (ȳ = 113.751 kg): MAPE < 15%,
  RMSE < 10% × ȳ = 11.375 kg, MAE < 8% × ȳ = 9.100 kg, MSE < (10% × ȳ)², R² > 0,70.
- Model final: **MAPE 6,59%**, RMSE 7.395 kg (6,5% ȳ), MAE 6.102 kg, R² 0,983 → **lulus semua target**.
- Pembanding seasonal naive: MAPE 14,73%, RMSE 25% ȳ → gagal target RMSE/MAE/MSE.
- Pemilihan model final: ARIMAX Harga punya MAPE terendah (4,00%) tetapi butuh harga bulan yang
  diramal (belum diketahui saat meramal 2026). Model final = model lulus diagnostik **dan** tanpa
  eksogen masa depan dengan MAPE terendah → **SARIMA(1,0,0)x(1,1,0,12) log**.
- Tampilkan: `data\laporan\08_plot_metrik_rolling_origin.png`.

### 8. Hasil peramalan (±2 menit)
- Validasi 6 bulan (Apr–Sep 2025): MAPE 7,61%, 5 dari 6 aktual di dalam interval 95%;
  Juni 2025 ramalan 269.022 kg vs aktual 274.672 kg (meleset 2,1%).
- Ramalan Jan–Jun 2026 (seluruh Kabupaten Malang): bulan normal ±66.000–71.000 kg;
  **Juni 177.280 kg**, batas atas 251.233 kg.
- Tampilkan: `data\hasil_09\grafik\09_fan_chart.png` (jelaskan corong ketidakpastian).

### 9. Demo sistem MS Access (±3 menit)
- Buka `data\db_penjualan_kambing_DEMO.accdb` → Enable Content.
- Tunjukkan berurutan: `Tbl_Volume_Bulanan` → `Tbl_Parameter_SARIMA` → `qry_12_Ramalan_6_Bulan`.
- Simulasi: isi data Januari 2026 (74.894 kg) → ramalan bergeser ke Feb–Jul 2026.
- Pesan: hasil Access sama dengan Python; pengelola data kabupaten (Dinas/RPH/asosiasi) tidak perlu
  menjalankan Python.
- Panduan rinci: `PANDUAN_PRESENTASI_ACCESS.md`.

### 10. Rekomendasi & penutup (±2 menit)
- **Tingkat kabupaten** (Dinas, RPH, pemasok, asosiasi pedagang):
  - Kekurangan pasokan turun **75,7%** dibanding perencanaan "sama seperti tahun lalu"; total
    selisih rencana vs aktual turun 64,6%.
  - Pasokan ternak dan pakan peternak direncanakan awal tahun; penggemukan tambahan Maret–April.
  - Kapasitas wilayah (RPH, cold storage, pasokan ternak) sampai batas atas 251.233 kg (+41,7% di atas
    ramalan), siap **pertengahan Mei** (Iduladha 2026 ±27 Mei).
- **Tingkat UMKM** (indeks, tidak bergantung skala usaha):
  - Rencana stok = penjualan bulan normal × indeks; Juni 2026 indeks **2,57**, faktor batas atas 1,42.
  - Contoh UMKM 500 kg/bulan: Juni rencana ±1.285 kg, maksimum ±1.821 kg.
  - Harga Iduladha historis 10,4% lebih tinggi → margin tipis Jan–Apr, naik bertahap mulai Mei.
- Keterbatasan: data sintetis agregat kabupaten (produksi sebagai proksi permintaan); puncak model di
  Juni; level 2026 turun ±22,8% (artefak model).
- Kesimpulan & terima kasih.

---

## Pembagian menjawab pertanyaan

| Topik pertanyaan | Menjawab |
|---|---|
| Sumber data, generate data, tidak dibagi jumlah UMKM, pra-proses, ADF, ACF/PACF, skenario, AIC/BIC, transformasi log | Presenter 1 |
| Ljung-Box, Shapiro-Wilk, Q-Q, rolling origin, metrik & target relatif, alasan SARIMA bukan ARIMAX, ramalan & interval, Access, rekomendasi kabupaten & indeks UMKM | Presenter 2 |
| Pertanyaan umum (kontribusi, keterbatasan) | Presenter yang ditanya, lalu dilengkapi rekan |

Jika ditanya "bagaimana perhitungannya?": buka file log terkait di `log_terminal\`, cari nomor
bagian (`[1]`–`[9]`), tunjukkan baris rumus → angka → **COCOK ✔** (lihat `PANDUAN_PENJELASAN_RUMUS.md`).

## Persiapan bersama
- Gladi bersih minimal sekali dengan pengatur waktu.
- Satu laptop: buka lebih dulu file Access DEMO, folder `log_terminal\`, dan gambar-gambar yang ditampilkan.
- Presenter 1 memegang slide bagian 1–5; Presenter 2 memegang slide 6–10 dan demo Access.
