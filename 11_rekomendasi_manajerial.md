# Rekomendasi Manajerial Berbasis Metrik Hasil Penelitian

Dibuat otomatis oleh `11_rekomendasi_manajerial.py`. Semua angka berasal dari hasil penelitian ini (bukan angka contoh dokumen alur).

## Sasaran rekomendasi

Data penelitian adalah permintaan daging kambing **agregat Kabupaten Malang** (produksi BPS sebagai proksi permintaan, tidak dibagi jumlah UMKM karena jumlahnya tidak diketahui pasti). Karena itu rekomendasi disusun dalam dua tingkat:

- **Tingkat kabupaten (angka kg):** Dinas yang membidangi peternakan, Rumah Potong Hewan (RPH), pemasok/pedagang besar ternak, dan asosiasi pedagang daging, untuk perencanaan pasokan ternak, kapasitas pemotongan, dan cold storage wilayah (bagian 1–4).
- **Tingkat UMKM (angka relatif/indeks):** pedagang, warung sate, dan katering dengan skala berapa pun cukup mengalikan penjualan bulan normalnya dengan indeks (bagian 5).

## Dasar akurasi model final SARIMA(1,0,0)x(1,1,0,12) log

- Validasi ekstrapolasi 6 bulan (Apr–Sep 2025): MAPE **7,61%**, aktual di dalam interval 95% pada 5 dari 6 bulan.
- Rolling origin 1 bulan (Apr–Des 2025): MAPE **6,59%**, R² 0,983.
- Peramalan 9 bulan data testing: MAPE **6,98%**, RMSE 7.818 kg; pembanding seasonal naive MAPE 14,73%.
- Seluruh MAPE berada di bawah target penelitian 15% (kategori akurat menurut Lewis, 1982: MAPE 10–20% baik, < 10% sangat akurat).

## 1. Penurunan risiko kelebihan dan kekurangan pasokan wilayah

**Asumsi:** rencana pasokan/pemotongan bulanan wilayah ditetapkan sama dengan ramalan. Metode lama diwakili seasonal naive (stok = penjualan bulan yang sama tahun lalu). Kelebihan stok = rencana − aktual bila positif; kekurangan = aktual − rencana bila positif. Periode: data testing Apr–Des 2025 (ramalan 9 bulan dari model yang dilatih s.d. Mar 2025).

| Metode_Rencana_Stok | Total_Aktual_Kg | Total_Rencana_Kg | Kelebihan_Stok_Kg | Kekurangan_Stok_Kg | Bulan_Kelebihan | Bulan_Kekurangan | Total_Selisih_Absolut_Kg |
|---|---|---|---|---|---|---|---|
| SARIMA D=1 | 1.023.755 | 1.000.444 | 19.561 | 42.872 | 2 | 7 | 62.432 |
| Seasonal naive | 1.023.755 | 847.385 | 0 | 176.369 | 0 | 9 | 176.369 |

- Pada periode ini permintaan 2025 lebih tinggi dari 2024, sehingga metode lama tidak pernah kelebihan stok tetapi selalu kekurangan. Model menghasilkan kelebihan stok 19.561 kg pada 2 bulan (1,9% dari total permintaan), sebagai imbalan dari penurunan kekurangan stok yang jauh lebih besar.
- Kekurangan stok turun dari 176.369 kg menjadi 42.872 kg (**75,7%**).
- Total selisih rencana vs aktual turun **64,6%**.
- Dalam persentase total permintaan: selisih rencana vs aktual model **6,1%**, metode lama **17,2%** (angka persentase ini berlaku juga untuk UMKM, tidak bergantung skala).
- Rekomendasi: jadikan ramalan model (garis tengah) dasar perencanaan pasokan dan pemotongan bulanan wilayah, dan perbarui ramalan setiap bulan setelah data aktual masuk (Tbl_Peramalan di Access) agar galat tidak menumpuk.

## 2. Perencanaan pasokan ternak dan pakan wilayah

**Asumsi:** kebutuhan ternak (dan pakan peternak) sebanding dengan volume permintaan. Angka "pakan ±70% biaya operasional" dari dokumen alur belum memiliki sumber di penelitian ini dan perlu rujukan sebelum dipakai.

| Periode | Ramalan_Kg | Indeks_vs_Rata2_6_Bulan | Indeks_vs_Bulan_Normal | Batas_Atas_95_Kg |
|---|---|---|---|---|
| 2026-01 | 71.327 | 0,82 | 1,03 | 83.880 |
| 2026-02 | 71.335 | 0,82 | 1,03 | 89.168 |
| 2026-03 | 69.364 | 0,80 | 1,01 | 90.514 |
| 2026-04 | 67.206 | 0,77 | 0,97 | 90.665 |
| 2026-05 | 65.768 | 0,76 | 0,95 | 91.146 |
| 2026-06 | 177.280 | 2,04 | 2,57 | 251.233 |

- Januari–Mei 2026 relatif datar (indeks 0,95–1,03 terhadap rata-rata bulan normal 69.000 kg untuk seluruh kabupaten): pasokan ternak dan pakan rutin peternak dapat direncanakan/dikontrak di awal tahun.
- Puncak Iduladha membutuhkan ±2,57 kali bulan normal. Karena Iduladha 2026 jatuh ±27 Mei, program penggemukan ternak dan penambahan pakan (konsentrat dan hijauan) di tingkat peternak sebaiknya dimulai Maret–April 2026.

## 3. Pencegahan kekurangan pasokan saat puncak (tingkat kabupaten)

- Ramalan puncak 2026-06: **177.280 kg**; batas atas interval 95%: **251.233 kg** untuk seluruh Kabupaten Malang. Angka ini adalah acuan kapasitas wilayah (gabungan RPH, cold storage, dan pasokan ternak dari peternak/pemasok), bukan kapasitas satu usaha. Stok pengaman wilayah 73.953 kg di atas ramalan (**+41,7%**).
- Batas atas 95% dua sisi berarti peluang permintaan melebihi batas atas ±2,5% (tidak nol). Penyediaan sampai batas atas menurunkan risiko stockout, bukan menjamin 100% permintaan terlayani.
- Bukti validasi: Juni 2025 ramalan 269.022 kg, batas atas 316.802 kg, aktual 274.672 kg (di dalam interval: Ya).
- **Iduladha 2026 jatuh ±27 Mei**, sedangkan model menaruh puncak di Juni (meniru pola 2023–2025). Kapasitas puncak harus siap **pertengahan Mei 2026**.

## 4. Batas margin harga jual

| Kategori | Jumlah_Bulan | Harga_Rata2_Per_Kg | Harga_Min | Harga_Maks | Volume_Rata2_Kg | Selisih_vs_Bulan_Biasa_% |
|---|---|---|---|---|---|---|
| Bulan Iduladha | 3 | 133.197 | 132.865 | 133.371 | 272.065 | 10,4 |
| Bulan biasa | 33 | 120.655 | 119.448 | 121.667 | 96.316 | 0,0 |

- Harga rata-rata bulan Iduladha Rp133.197/kg, **10,4%** di atas bulan biasa (Rp120.655/kg), sementara volumenya ±2,8 kali bulan biasa.
- Januari–April 2026 (permintaan rendah, ramalan ±69.000 kg/bulan): pertahankan margin tipis untuk mempercepat perputaran stok dan menghindari pembusukan.
- Menjelang Iduladha: kenaikan margin wajar berada di kisaran historis ±10%, diterapkan bertahap mulai pertengahan Mei 2026.
- Catatan: koefisien harga pada model ARIMAX tidak dapat dibaca sebagai elastisitas sebab-akibat. Harga dan volume sama-sama naik di bulan Iduladha (korelasi 0,988), sehingga data tidak dapat memisahkan efek harga dari efek musim.

## 5. Panduan indeks untuk UMKM (tidak bergantung skala usaha)

Ramalan kabupaten diubah menjadi angka relatif agar dapat dipakai UMKM dengan skala berapa pun. File: `data/hasil_11/11_rek_panduan_umkm_2026.csv`.

- **Indeks_vs_Bulan_Normal** = ramalan bulan tersebut ÷ rata-rata ramalan bulan normal (Jan–Mei 2026).
- **Perubahan_vs_Tahun_Lalu_%** = ramalan ÷ aktual bulan yang sama tahun 2025 − 1.
- **Faktor_Batas_Atas** = batas atas 95% ÷ ramalan; **Stok_Pengaman_%** = faktor batas atas − 1.

| Periode | Indeks_vs_Bulan_Normal | Perubahan_vs_Tahun_Lalu_% | Faktor_Batas_Bawah | Faktor_Batas_Atas | Stok_Pengaman_% |
|---|---|---|---|---|---|
| 2026-01 | 1,03 | -16,5 | 0,85 | 1,18 | 17,6 |
| 2026-02 | 1,03 | -13,6 | 0,80 | 1,25 | 25,0 |
| 2026-03 | 1,01 | -23,5 | 0,77 | 1,30 | 30,5 |
| 2026-04 | 0,97 | -21,6 | 0,74 | 1,35 | 34,9 |
| 2026-05 | 0,95 | -26,4 | 0,72 | 1,39 | 38,6 |
| 2026-06 | 2,57 | -35,5 | 0,71 | 1,42 | 41,7 |

**Cara pakai:** rencana stok bulan t = penjualan bulan normal UMKM × Indeks_t; kapasitas maksimum yang disiapkan = rencana × Faktor_Batas_Atas_t.

**Contoh** UMKM dengan penjualan bulan normal 500 kg:

| Periode | Contoh_UMKM_500kg_Rencana_Kg | Contoh_UMKM_500kg_Maks_Kg |
|---|---|---|
| 2026-01 | 517 | 608 |
| 2026-02 | 517 | 646 |
| 2026-03 | 503 | 656 |
| 2026-04 | 487 | 657 |
| 2026-05 | 477 | 660 |
| 2026-06 | 1.285 | 1.821 |

- Bulan puncak 2026-06: siapkan ±2,57× penjualan bulan normal, dengan cadangan sampai +42% di atas rencana.
- Karena Iduladha 2026 jatuh ±27 Mei, indeks puncak sebaiknya diterapkan mulai pertengahan Mei 2026, bukan menunggu Juni.
- Indeks berlaku bila pola musiman UMKM mirip pola kabupaten; UMKM yang pelanggannya didominasi aqiqah/katering dapat memiliki pola berbeda.

## Keterbatasan

- Data penelitian adalah data sintetis yang dikalibrasi dari BPS (agregat Kabupaten Malang), bukan transaksi riil satu usaha; produksi daging dipakai sebagai proksi permintaan.
- Level ramalan 2026 rata-rata ±22,8% di bawah 2025; ini artefak koefisien musiman yang mengulang penurunan 2023→2024, bukan tren pasti.
- Puncak ramalan di Juni, sedangkan Iduladha 2026 jatuh di akhir Mei.
- Analisis biaya pakan dan margin bersifat relatif (indeks), karena data biaya pakan tidak tersedia.
