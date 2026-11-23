# Panduan Pengguna: Meramal Permintaan Daging Kambing Kabupaten Malang di MS Access

Semua langkah dilakukan di **Microsoft Access**, tanpa Python dan tanpa kode program.

File database: `data\db_penjualan_kambing.accdb`

## Siapa pengguna panduan ini?

Data dan ramalan di database ini adalah permintaan daging kambing **agregat Kabupaten Malang**.
Produksi daging (BPS) dipakai sebagai proksi permintaan, dan angkanya **tidak dibagi jumlah UMKM**
karena jumlah UMKM di Kabupaten Malang tidak diketahui pasti. Karena itu ada dua jenis pengguna:

| Pengguna | Contoh | Yang dipakai |
|---|---|---|
| **Pengelola data tingkat kabupaten** | Dinas yang membidangi peternakan, Rumah Potong Hewan (RPH), pemasok/pedagang besar ternak, asosiasi pedagang daging | Mengisi data bulanan (bagian B) dan membaca ramalan dalam **kg** (bagian C dan D1) |
| **UMKM** | Pedagang daging, warung sate, katering/aqiqah | Membaca ramalan dalam bentuk **indeks/persentase** lalu mengalikannya dengan penjualan sendiri (bagian D2) |

---

## A. Membuka database

1. Klik ganda file `db_penjualan_kambing.accdb`.
2. Jika muncul pita kuning bertuliskan **SECURITY WARNING** di bagian atas, klik **Enable Content**.
3. Di panel kiri (*Navigation Pane*) terlihat daftar **Tables** (tabel) dan **Queries** (query).
   Jika panel tidak terlihat, tekan tombol **F11**.

---

## B. Mengisi data permintaan bulanan (setiap awal bulan, oleh pengelola data kabupaten)

Isi data bulan yang **baru saja selesai**, satu baris per bulan.

1. Di panel kiri, klik ganda tabel **Tbl_Volume_Bulanan**.
2. Gulir ke baris paling bawah (baris kosong bertanda `*`).
3. Isi kolom berikut:

| Kolom | Isi | Contoh (data Januari 2026) |
|---|---|---|
| **Periode** | Tanggal **1** dari bulan tersebut | `01/01/2026` |
| **Tahun** | Tahun | `2026` |
| **Bulan** | Nomor bulan (1–12) | `1` |
| **Permintaan_Kg** | Total daging kambing **seluruh Kabupaten Malang** bulan itu (kg) | `114195` |
| **Harga_Rata2_Per_Kg** | Harga rata-rata per kg (boleh dikosongkan) | `121000` |
| **Sumber** | Keterangan bebas | `Rekap RPH/Dinas Januari 2026` |

4. Tekan **Enter** sampai pindah ke baris baru. Data tersimpan otomatis.

Hal yang perlu diperhatikan:
- **Isi angka tingkat kabupaten, bukan penjualan satu usaha.** Model dilatih pada data agregat
  kabupaten. Jika satu bulan diisi angka satu UMKM, rumus musiman (yang membandingkan dengan bulan
  yang sama tahun lalu) akan menghasilkan ramalan yang salah. UMKM cukup memakai bagian D2.
- **Periode harus tanggal 1** (misalnya `01/02/2026` untuk Februari), bukan tanggal lain.
  Urutan tanggal/bulan mengikuti pengaturan Windows; jika ragu, ketik `1-Jan-2026`.
- **Jangan melompati bulan.** Rumus membutuhkan data bulanan yang berurutan.
- **Permintaan_Kg** diisi angka saja, tanpa titik ribuan.
- Jika salah ketik, perbaiki langsung di sel tersebut.

---

## C. Melihat hasil ramalan

### Ramalan 6 bulan ke depan (utama)

1. Di panel kiri bagian **Queries**, klik ganda **qry_16_Ramalan_Disesuaikan**.
2. Muncul 6 baris, yaitu 6 bulan setelah data terakhir yang diisi, dengan puncak Iduladha sudah
   ditempatkan di bulan yang benar sesuai tanggal di tabel **Tbl_16_Tanggal_Iduladha**.
3. Ramalan model sebelum disesuaikan tetap bisa dilihat di **qry_12_Ramalan_6_Bulan** (puncaknya
   selalu di Juni karena meniru pola 2023–2025). Kolom kedua query sama artinya; di qry_16 nama kolom
   diberi akhiran *Disesuaikan* dan ada kolom **Bobot_Iduladha** (porsi hari ramai Iduladha di bulan itu).

| Kolom | Arti |
|---|---|
| **Bulan_Ke** | Bulan ke-1 sampai ke-6 setelah data terakhir |
| **Periode** | Bulan yang diramal |
| **Ramalan_Kg** | Perkiraan permintaan paling mungkin untuk seluruh kabupaten. Dipakai untuk **rencana pasokan dan pemotongan rutin wilayah**. |
| **Batas_Bawah_95_Kg** | Perkiraan terendah yang masih wajar (skenario pasar sepi). |
| **Batas_Atas_95_Kg** | Perkiraan tertinggi yang masih wajar. Dipakai untuk **menyiapkan kapasitas cadangan wilayah** (kapasitas RPH, cold storage, pasokan ternak dari peternak/pemasok). |

Ramalan berubah otomatis setiap kali data bulan baru ditambahkan di Tbl_Volume_Bulanan
(langkah B). Tidak ada tombol yang perlu ditekan; cukup buka ulang query ini.

### Memperbarui tanggal Iduladha (setahun sekali)

Buka tabel **Tbl_16_Tanggal_Iduladha** dan pastikan ada baris untuk tahun yang diramal
(misalnya `2026` → `27/05/2026`; tahun berikutnya diisi sesuai keputusan pemerintah). Jika ramalan
melewati tahun yang belum ada tanggalnya, tambahkan barisnya.

### Ramalan bulan depan saja

- Klik ganda **qry_11_Ramalan_Bulan_Depan**. Hasilnya satu baris: ramalan bulan berikutnya
  beserta batas bawah dan batas atas.

### Query lain (informasi pendukung)

| Query | Isi |
|---|---|
| qry_11_Volume_Bulanan | Daftar data permintaan bulanan yang sudah diisi |
| qry_11_Faktor_Musiman | Rata-rata permintaan per bulan (Juni ±2,4 kali rata-rata seluruh bulan) |
| qry_11_Ramalan_1_Bulan_Historis | Ramalan 1 bulan ke depan untuk bulan-bulan lalu, untuk mengecek ketepatan model |

---

## D. Cara membaca hasil untuk keputusan

### D1. Tingkat kabupaten (angka kg)

- **Bulan biasa:** rencanakan pasokan ternak dan jadwal pemotongan wilayah sesuai **Ramalan_Kg**.
- **Menjelang Iduladha:** siapkan kapasitas wilayah sampai **Batas_Atas_95_Kg**. Contoh Mei 2026
  (Iduladha 27 Mei): ramalan disesuaikan 301.478 kg, batas atas 363.624 kg untuk **seluruh Kabupaten
  Malang**, bukan untuk satu usaha. Batas atas tidak menjamin 100%; masih ada peluang kecil (±2,5%)
  permintaan lebih tinggi.
- **Perhatikan tanggal Iduladha.** Model meniru pola Iduladha di bulan Juni (2023–2025), lalu
  qry_16 memindahkan puncaknya ke bulan Iduladha sebenarnya. Untuk 2026 puncak ada di Mei, jadi
  siapkan kapasitas puncak sejak **pertengahan Mei**. Juni 2026 kembali ke level bulan biasa (±109.254 kg).
- Ramalan bulan yang lebih jauh lebih tidak pasti (batas bawah–atas lebih lebar). Perbarui rencana
  setiap bulan setelah data aktual diisi.

### D2. Tingkat UMKM (angka relatif, untuk skala usaha berapa pun)

UMKM tidak perlu mengisi database. Cukup ubah ramalan kabupaten menjadi **indeks**:

- **Indeks bulan** = ramalan disesuaikan bulan tersebut ÷ rata-rata ramalan bulan normal (bulan tanpa Iduladha; 2026: 110.351 kg).
- **Faktor batas atas** = Batas_Atas_95_Kg ÷ Ramalan_Kg.

Lalu:
- **Rencana stok UMKM** = penjualan bulan normal UMKM × indeks bulan.
- **Kapasitas maksimum yang disiapkan** = rencana stok × faktor batas atas.

Nilai untuk Januari–Juni 2026 (dari `data\hasil_11\11_rek_panduan_umkm_2026.csv`), dengan contoh
UMKM yang biasanya menjual **500 kg per bulan**:

| Periode | Indeks | Faktor batas atas | Rencana UMKM 500 kg | Maksimum disiapkan |
|---|---|---|---|---|
| Jan 2026 | 0,99 | 1,16 | 493 kg | 572 kg |
| Feb 2026 | 1,01 | 1,19 | 506 kg | 602 kg |
| Mar 2026 | 1,02 | 1,20 | 509 kg | 611 kg |
| Apr 2026 | 0,99 | 1,20 | 498 kg | 599 kg |
| Mei 2026 (Iduladha 27 Mei) | 2,73 | 1,21 | 1.366 kg | 1.648 kg |
| Jun 2026 | 0,99 | 1,21 | 495 kg | 597 kg |

Catatan untuk UMKM:
- Indeks puncak (±2,73×) sudah ditempatkan di Mei karena Iduladha 2026 jatuh 27 Mei; siapkan stok sejak **pertengahan Mei**.
- Indeks berlaku bila pola musiman usaha mirip pola kabupaten. Usaha yang pelanggannya didominasi
  aqiqah/katering bisa memiliki pola berbeda, jadi sesuaikan dengan pengalaman sendiri.
- Indeks diperbarui setiap kali pengelola data kabupaten menambah data bulan baru.

---

## E. Yang TIDAK boleh diubah

- **Tbl_Parameter_SARIMA**: berisi angka hasil pelatihan model. Jangan diubah.
- Query yang namanya diawali **qry_11_**, **qry_12_**, dan **qry_16_**: jangan diedit atau dihapus.
- Tabel **Tbl_16_Jendela_Iduladha** dan **Tbl_16_Bulan_Lonjakan_Model**: jangan diubah (yang boleh diperbarui hanya Tbl_16_Tanggal_Iduladha).
- Tabel lama (Transaksi_Penjualan, Pelanggan, Hasil_Prediksi, Evaluasi_Model) tidak dipakai
  untuk ramalan ini.

---

## F. Pemeliharaan oleh peneliti (bukan pengguna)

- Parameter model dilatih ulang **setahun sekali** oleh peneliti dengan Python, setelah data
  bertambah. Hasilnya cukup memperbarui isi Tbl_Parameter_SARIMA; pengguna tidak perlu mengubah
  apa pun.
- Sebelum peneliti menjalankan script Python yang mengakses database, **tutup MS Access** terlebih
  dahulu.
