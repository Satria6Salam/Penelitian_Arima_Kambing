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
- Data 36 bulan (Jan 2023–Des 2025) dibangkitkan dari produksi **karkas** BPS Kabupaten Malang (sintetis, dikalibrasi BPS).
  Label kolom komponen BPS 2024–2025 tertukar (dicek dengan rumus catatan kaki BPS) dan sudah dibaca benar;
  komponen 2023 tidak diterbitkan, jadi ditaksir dari proporsi 2024–2025 tanpa mengubah total resmi.
- Baseline = produksi kabupaten, **tidak dibagi jumlah UMKM** karena jumlahnya tidak diketahui pasti;
  produksi daging dipakai sebagai proksi permintaan. Dengan log dan differencing musiman, skala data
  tidak memengaruhi parameter maupun MAPE.
- Rumus inti: baseline μ = karkas tahunan / 12 (105.975 / 116.122 / 121.872 kg); tren lokal = garis lurus
  antar-titik tengah tahun dari μ Malang sendiri (rata-rata tahunannya sama dengan μ);
  faktor Iduladha **S = 1 + (22.359 − 8.229) / 8.229 = 2,717**; white noise 5%.
- Pra-proses: agregasi bulanan, interpolasi linier (tidak ada bulan kosong), IQR —
  outlier hanya bulan Juni (Iduladha) dan **dipertahankan** sebagai pola musiman.
- Tampilkan: `data\eksplorasi\time_series_plot.png`.

### 3. Eksplorasi data (±2 menit) — `[4]`, `[5]`
- Uji ADF: t-ADF **−6,3385** < kritis 5% −2,9485, p < 0,000001 → data **stasioner (d = 0)**.
- ACF lag 12 = **0,5611**, PACF lag 12 = **0,7168**, keduanya signifikan → pola musiman **m = 12**.
- Tampilkan: `data\eksplorasi\acf_pacf_plot.png` dan `time_series_decomposition.png`.

### 4. Pembagian data & skenario (±1,5 menit) — `[3]`, `[6]`
- Kronologis 75% : 25% → training 27 bulan (Jan 2023–Mar 2025), testing 9 bulan (Apr–Des 2025).
- 4 skenario, 28 kandidat: ARIMA (8), SARIMA D=0/D=1 (4), ARIMAX + Harga (8), ARIMAX + Harga + Iduladha (8).

### 5. Estimasi & pemilihan model (±2,5 menit) — `[7]`, `[8]`
- Estimasi MLE dengan statsmodels; data ditransformasi **log** dan memakai **multi-optimizer**
  (alasan: lonjakan Iduladha bersifat perkalian; optimizer default sempat terjebak optimum lokal), plus nilai awal
  dari model bersarang yang lebih sederhana (*warm start*).
- AIC = −2·LL + 2k, BIC = −2·LL + k·ln n; dibandingkan **hanya dalam kelompok differencing yang sama**.
- Contoh: SARIMA(1,0,0)x(1,1,0,12) LL 13,2499 → AIC −20,50; terbaik di kelompok D=1.
- Tampilkan: `data\laporan\07_plot_aic_bic.png`.

**Kalimat transisi:**
> "Model dengan AIC terendah belum tentu layak. Selanjutnya rekan saya akan menjelaskan
> pengujian kelayakan model, hasil ramalan, dan sistem di MS Access."

---

## PRESENTER 2 — Validasi, Ramalan & Sistem (±11 menit)

### 6. Validasi diagnostik (±2 menit) — `[9]`
- Ljung-Box (white noise) dan Shapiro-Wilk (normalitas) pada 5 model shortlist.
- Tiga model lulus keduanya; model final **SARIMA(1,0,0)x(1,1,0,12) log**:
  Ljung-Box lag 6 Q = 8,47, p = 0,076 (lag 9 dan 12 juga lulus); Shapiro-Wilk W = 0,948, p = 0,50.
- Tampilkan: Q-Q plot `data\hasil_07\grafik\07_qq_SARIMA_D1.png`, `data\laporan\08_plot_ljungbox_shapiro.png`.

### 7. Evaluasi kinerja (±2 menit) — `[9]`
- Rolling origin 9 putaran (latih → ramal 1 bulan → tambah data aktual → latih ulang).
- Target relatif terhadap rata-rata permintaan testing (ȳ = 145.698 kg): MAPE < 15%,
  RMSE < 10% × ȳ = 14.570 kg, MAE < 8% × ȳ = 11.656 kg, MSE < (10% × ȳ)², R² > 0,70.
- Model final: **MAPE 7,51%**, RMSE 16.963 kg (11,6% ȳ), MAE 12.132 kg, R² 0,948 → lulus MAPE dan R²,
  **belum lulus** RMSE/MAE/MSE (galat terbesar di bulan Iduladha yang volumenya besar).
- Pembanding seasonal naive: MAPE 8,81%, RMSE 26.773 kg (18,4% ȳ). Model final terbaik di antara model
  tanpa harga masa depan pada skema ini; pembanding Holt-Winters 7,67% dan airline 7,73% (script 14).
- Pemilihan model final: ARIMAX Harga+Iduladha punya MAPE terendah (4,38%) tetapi butuh harga bulan yang
  diramal (belum diketahui saat meramal 2026). Model final = model lulus diagnostik **dan** tanpa
  eksogen masa depan dengan MAPE terendah → **SARIMA(1,0,0)x(1,1,0,12) log**.
- Tampilkan: `data\laporan\08_plot_metrik_rolling_origin.png`.

### 8. Hasil peramalan (±2 menit)
- Peramalan 9 bulan sekaligus (Apr–Des 2025): MAPE 9,07%, semua aktual di dalam interval 95%;
  tetapi Holt-Winters (7,43%), airline (7,66%), dan seasonal naive (8,81%) lebih kecil, dan uji
  Diebold-Mariano tidak menunjukkan beda signifikan. Simulasi 100 seed: median MAPE 10,42%, target
  tercapai di 89% seed. Jawab jujur: model **layak**, tetapi **tidak lebih unggul** dari metode sederhana.
- Validasi 6 bulan (Apr–Sep 2025): MAPE 10,46%, 6 dari 6 aktual di dalam interval 95%;
  Juni 2025 ramalan 312.294 kg vs aktual 356.163 kg (meleset 12,3%).
- Ramalan Jan–Jun 2026 (seluruh Kabupaten Malang): bulan normal ±108.757–112.341 kg; model menaruh
  puncak di Juni (301.478 kg). Setelah penyesuaian Iduladha (27 Mei 2026, R = 2,759): **Mei 301.478 kg**,
  batas atas 363.624 kg; Juni kembali ±109.254 kg.
- Tampilkan juga: `data\hasil_13\grafik\13_ramalan_disesuaikan.png`.
- Tampilkan: `data\hasil_09\grafik\09_fan_chart.png` (jelaskan corong ketidakpastian).

### 9. Demo sistem MS Access (±3 menit)
- Buka `data\db_penjualan_kambing_DEMO.accdb` → Enable Content.
- Tunjukkan berurutan: `Tbl_Volume_Bulanan` → `Tbl_Parameter_SARIMA` → `qry_12_Ramalan_6_Bulan` →
  `qry_16_Ramalan_Disesuaikan` (puncak pindah ke Mei).
- Simulasi: isi data Januari 2026 (114.195 kg) → ramalan bergeser ke Feb–Jul 2026.
- Pesan: hasil Access sama dengan Python; pengelola data kabupaten (Dinas/RPH/asosiasi) tidak perlu
  menjalankan Python.
- Panduan rinci: `PANDUAN_PRESENTASI_ACCESS.md`.

### 10. Rekomendasi & penutup (±2 menit)
- **Tingkat kabupaten** (Dinas, RPH, pemasok, asosiasi pedagang):
  - Pada data testing, total selisih rencana vs aktual turun **10,7%** dibanding perencanaan "sama seperti
    tahun lalu" (kelebihan stok 36.263 → 18.938 kg; kekurangan sedikit naik 106.495 → 108.603 kg).
  - Pasokan ternak dan pakan peternak direncanakan awal tahun; penggemukan tambahan Maret–April.
  - Kapasitas wilayah (RPH, cold storage, pasokan ternak) sampai batas atas 363.624 kg (+20,6% di atas
    ramalan Mei 301.478 kg), siap **pertengahan Mei** (Iduladha 2026 27 Mei).
- **Tingkat UMKM** (indeks, tidak bergantung skala usaha):
  - Rencana stok = penjualan bulan normal × indeks; Mei 2026 indeks **2,73**, faktor batas atas 1,21.
  - Contoh UMKM 500 kg/bulan: Mei rencana ±1.366 kg, maksimum ±1.648 kg.
  - Harga Iduladha historis 10,4% lebih tinggi → margin tipis Jan–Apr, naik bertahap mulai Mei.
- Keterbatasan: data sintetis agregat kabupaten (produksi sebagai proksi permintaan); data hanya 3 tahun
  dan 9 titik uji (daya uji rendah); penyesuaian Iduladha belum bisa divalidasi karena Iduladha historis
  selalu Juni; rata-rata ramalan 2026 ±6,0% di bawah 2025 (keterbatasan data, bukan tren pasti).
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
