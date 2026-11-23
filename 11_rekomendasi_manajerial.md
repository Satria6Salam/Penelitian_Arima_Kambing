# Rekomendasi Manajerial Berbasis Metrik Hasil Penelitian

Dibuat otomatis oleh `11_rekomendasi_manajerial.py`. Semua angka berasal dari hasil penelitian ini (bukan angka contoh dokumen alur).

## Sasaran rekomendasi

Data penelitian adalah permintaan daging kambing **agregat Kabupaten Malang** (produksi BPS sebagai proksi permintaan, tidak dibagi jumlah UMKM karena jumlahnya tidak diketahui pasti). Karena itu rekomendasi disusun dalam dua tingkat:

- **Tingkat kabupaten (angka kg):** Dinas yang membidangi peternakan, Rumah Potong Hewan (RPH), pemasok/pedagang besar ternak, dan asosiasi pedagang daging, untuk perencanaan pasokan ternak, kapasitas pemotongan, dan cold storage wilayah (bagian 1–4).
- **Tingkat UMKM (angka relatif/indeks):** pedagang, warung sate, dan katering dengan skala berapa pun cukup mengalikan penjualan bulan normalnya dengan indeks (bagian 5).

## Dasar akurasi model final SARIMA(1,0,0)x(1,1,0,12) log

- Validasi ekstrapolasi 6 bulan (Apr–Sep 2025): MAPE **10,46%**, aktual di dalam interval 95% pada 6 dari 6 bulan.
- Rolling origin 1 bulan (Apr–Des 2025): MAPE **7,51%**, R² 0,948.
- Peramalan 9 bulan data testing: MAPE **9,07%**, RMSE 18.484 kg; pembanding seasonal naive MAPE 8,81%.
- Seluruh MAPE berada di bawah target penelitian 15% (target ditetapkan penulis sebagai kriteria kelayakan praktis).

## 1. Penurunan risiko kelebihan dan kekurangan pasokan wilayah

**Asumsi:** rencana pasokan/pemotongan bulanan wilayah ditetapkan sama dengan ramalan. Metode lama diwakili seasonal naive (stok = penjualan bulan yang sama tahun lalu). Kelebihan stok = rencana − aktual bila positif; kekurangan = aktual − rencana bila positif. Periode: data testing Apr–Des 2025 (ramalan 9 bulan dari model yang dilatih s.d. Mar 2025).

| Metode_Rencana_Stok | Total_Aktual_Kg | Total_Rencana_Kg | Kelebihan_Stok_Kg | Kekurangan_Stok_Kg | Bulan_Kelebihan | Bulan_Kekurangan | Total_Selisih_Absolut_Kg |
|---|---|---|---|---|---|---|---|
| SARIMA D=1 | 1.311.283 | 1.221.618 | 18.938 | 108.603 | 2 | 7 | 127.541 |
| Seasonal naive | 1.311.283 | 1.241.051 | 36.263 | 106.495 | 3 | 6 | 142.758 |

- Kelebihan stok turun dari 36.263 kg menjadi 18.938 kg (**47,8%**).
- Kekurangan stok turun dari 106.495 kg menjadi 108.603 kg (**-2,0%**).
- Total selisih rencana vs aktual turun **10,7%**.
- Dalam persentase total permintaan: selisih rencana vs aktual model **9,7%**, metode lama **10,9%** (angka persentase ini berlaku juga untuk UMKM, tidak bergantung skala).
- Rekomendasi: jadikan ramalan model (garis tengah) dasar perencanaan pasokan dan pemotongan bulanan wilayah, dan perbarui ramalan setiap bulan setelah data aktual masuk (Tbl_Peramalan di Access) agar galat tidak menumpuk.

## 2. Perencanaan pasokan ternak dan pakan wilayah

**Asumsi:** kebutuhan ternak (dan pakan peternak) sebanding dengan volume permintaan. Angka "pakan ±70% biaya operasional" dari dokumen alur belum memiliki sumber di penelitian ini dan perlu rujukan sebelum dipakai.

| Periode | Ramalan_Kg | Indeks_vs_Rata2_6_Bulan | Indeks_vs_Bulan_Normal | Batas_Atas_95_Kg |
|---|---|---|---|---|
| 2026-01 | 108.757 | 0,76 | 0,99 | 126.325 |
| 2026-02 | 111.595 | 0,78 | 1,01 | 132.937 |
| 2026-03 | 112.341 | 0,79 | 1,02 | 134.952 |
| 2026-04 | 109.806 | 0,77 | 1,00 | 132.299 |
| 2026-05 | 301.478 | 2,12 | 2,73 | 363.624 |
| 2026-06 | 109.254 | 0,77 | 0,99 | 131.827 |

- Bulan selain puncak relatif datar (indeks 0,99–1,02 terhadap rata-rata bulan normal 110.351 kg untuk seluruh kabupaten): pasokan ternak dan pakan rutin peternak dapat direncanakan/dikontrak di awal tahun.
- Puncak Iduladha (2026-05) membutuhkan ±2,73 kali bulan normal. Karena Iduladha 2026 jatuh ±27 Mei, program penggemukan ternak dan penambahan pakan (konsentrat dan hijauan) di tingkat peternak sebaiknya dimulai Maret–April 2026.

## 3. Pencegahan kekurangan pasokan saat puncak (tingkat kabupaten)

- Ramalan puncak 2026-05: **301.478 kg**; batas atas interval 95%: **363.624 kg** untuk seluruh Kabupaten Malang. Angka ini adalah acuan kapasitas wilayah (gabungan RPH, cold storage, dan pasokan ternak dari peternak/pemasok), bukan kapasitas satu usaha. Stok pengaman wilayah 62.146 kg di atas ramalan (**+20,6%**).
- Batas atas 95% dua sisi berarti peluang permintaan melebihi batas atas ±2,5% (tidak nol). Penyediaan sampai batas atas menurunkan risiko stockout, bukan menjamin 100% permintaan terlayani.
- Bukti validasi: Juni 2025 ramalan 312.294 kg, batas atas 368.861 kg, aktual 356.163 kg (di dalam interval: Ya).
- Ramalan sudah disesuaikan dengan kalender Iduladha 2026 (±27 Mei, script 13), sehingga puncaknya berada di 2026-05. Kapasitas puncak harus siap **pertengahan Mei 2026**.

## 4. Batas margin harga jual

| Kategori | Jumlah_Bulan | Harga_Rata2_Per_Kg | Harga_Min | Harga_Maks | Volume_Rata2_Kg | Selisih_vs_Bulan_Biasa_% |
|---|---|---|---|---|---|---|
| Bulan Iduladha | 3 | 130.898 | 130.377 | 131.222 | 320.368 | 10,5 |
| Bulan biasa | 33 | 118.511 | 117.243 | 119.216 | 115.082 | 0,0 |

- Harga rata-rata bulan Iduladha Rp130.898/kg, **10,5%** di atas bulan biasa (Rp118.511/kg), sementara volumenya ±2,8 kali bulan biasa.
- Januari–April 2026 (permintaan rendah, ramalan ±110.351 kg/bulan): pertahankan margin tipis untuk mempercepat perputaran stok dan menghindari pembusukan.
- Menjelang Iduladha: kenaikan margin wajar berada di kisaran historis ±10%, diterapkan bertahap mulai pertengahan Mei 2026.
- Catatan: koefisien harga pada model ARIMAX tidak dapat dibaca sebagai elastisitas sebab-akibat. Harga dan volume sama-sama naik di bulan Iduladha (korelasi Pearson 0,970 selama 36 bulan), sehingga data tidak dapat memisahkan efek harga dari efek musim.

## 5. Panduan indeks untuk UMKM (tidak bergantung skala usaha)

Ramalan kabupaten diubah menjadi angka relatif agar dapat dipakai UMKM dengan skala berapa pun. File: `data/hasil_11/11_rek_panduan_umkm_2026.csv`.

- **Indeks_vs_Bulan_Normal** = ramalan bulan tersebut ÷ rata-rata ramalan bulan normal (bulan selain puncak Iduladha). Ramalan yang dipakai sudah disesuaikan kalender Iduladha.
- **Perubahan_vs_Tahun_Lalu_%** = ramalan ÷ aktual bulan yang sama tahun 2025 − 1.
- **Faktor_Batas_Atas** = batas atas 95% ÷ ramalan; **Stok_Pengaman_%** = faktor batas atas − 1.

| Periode | Indeks_vs_Bulan_Normal | Perubahan_vs_Tahun_Lalu_% | Faktor_Batas_Bawah | Faktor_Batas_Atas | Stok_Pengaman_% |
|---|---|---|---|---|---|
| 2026-01 | 0,99 | -5,7 | 0,86 | 1,16 | 16,2 |
| 2026-02 | 1,01 | 1,0 | 0,84 | 1,19 | 19,1 |
| 2026-03 | 1,02 | -6,7 | 0,83 | 1,20 | 20,1 |
| 2026-04 | 1,00 | -2,7 | 0,83 | 1,20 | 20,5 |
| 2026-05 | 2,73 | 158,1 | 0,83 | 1,21 | 20,6 |
| 2026-06 | 0,99 | -69,3 | 0,83 | 1,21 | 20,7 |

**Cara pakai:** rencana stok bulan t = penjualan bulan normal UMKM × Indeks_t; kapasitas maksimum yang disiapkan = rencana × Faktor_Batas_Atas_t.

**Contoh** UMKM dengan penjualan bulan normal 500 kg:

| Periode | Contoh_UMKM_500kg_Rencana_Kg | Contoh_UMKM_500kg_Maks_Kg |
|---|---|---|
| 2026-01 | 493 | 572 |
| 2026-02 | 506 | 602 |
| 2026-03 | 509 | 611 |
| 2026-04 | 498 | 599 |
| 2026-05 | 1.366 | 1.648 |
| 2026-06 | 495 | 597 |

- Bulan puncak 2026-05: siapkan ±2,73× penjualan bulan normal, dengan cadangan sampai +21% di atas rencana.
- Karena Iduladha 2026 jatuh ±27 Mei, indeks puncak sebaiknya diterapkan mulai pertengahan Mei 2026.
- Indeks berlaku bila pola musiman UMKM mirip pola kabupaten; UMKM yang pelanggannya didominasi aqiqah/katering dapat memiliki pola berbeda.

## Keterbatasan

- Data penelitian adalah data sintetis yang dikalibrasi dari BPS (agregat Kabupaten Malang), bukan transaksi riil satu usaha; produksi daging dipakai sebagai proksi permintaan.
- Ramalan model Jan–Jun 2026 rata-rata 6,0% di bawah bulan yang sama tahun 2025 (dibandingkan sebelum penyesuaian kalender, Juni dengan Juni). Dengan data tiga tahun, koefisien musiman belum stabil, sehingga arah ini belum pasti.
- Penyesuaian kalender Iduladha belum dapat divalidasi secara empiris karena seluruh Iduladha historis (2023–2025) jatuh di bulan Juni.
- Analisis biaya pakan dan margin bersifat relatif (indeks), karena data biaya pakan tidak tersedia.
