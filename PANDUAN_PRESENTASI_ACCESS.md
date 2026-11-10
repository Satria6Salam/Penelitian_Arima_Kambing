# Panduan Demo MS Access saat Presentasi ke Dosen

Panduan ini berisi persiapan, urutan demo, kalimat penjelasan, dan antisipasi pertanyaan.
Durasi demo sekitar 8–10 menit.

---

## 1. Persiapan (H-1 dan sebelum presentasi)

1. **Pakai file demo, bukan file asli.** Buka `data\db_penjualan_kambing_DEMO.accdb`. Isinya sama
   dengan database asli, jadi kalau Anda menambah data saat demo, file asli tetap aman.
   Jika file demo rusak/terisi data percobaan, salin ulang dari `db_penjualan_kambing.accdb`.
2. **Coba sekali sebelum presentasi** semua langkah di bagian 3, supaya tidak ada kejutan.
3. **Pesan keamanan:** saat membuka file, jika muncul pita kuning *SECURITY WARNING*, klik
   **Enable Content**. Lakukan ini sebelum dosen melihat layar.
4. **Tampilkan panel kiri** (Navigation Pane): tekan **F11** jika tersembunyi. Ubah tampilan panel ke
   **All Access Objects** (klik judul panel → *All Access Objects*) agar Tables dan Queries terlihat.
5. Siapkan juga di layar (tab terpisah): fan chart `data\hasil_09\grafik\09_fan_chart.png` dan gambar
   `data\hasil_11\access_output\11_hasil_access.png` sebagai cadangan jika Access bermasalah.
6. Tutup program Python dan Excel yang membuka file proyek.

---

## 2. Pesan utama yang ingin disampaikan

> "Model peramalan dilatih di Python, lalu parameternya disimpan di MS Access. Semua perhitungan
> ramalan dilakukan oleh query MS Access, sehingga pengelola data tingkat kabupaten (Dinas, RPH,
> asosiasi pedagang) cukup memakai Access tanpa Python. UMKM memakai hasilnya dalam bentuk indeks."

Tiga hal yang dibuktikan dalam demo:
1. Parameter model tersimpan di Access.
2. Ramalan 6 bulan + interval 95% dihitung langsung oleh query Access.
3. Ramalan otomatis diperbarui ketika data bulan baru dimasukkan.

---

## 3. Urutan demo (langkah klik + kalimat penjelasan)

### Langkah 1 – Data historis
- **Klik ganda** tabel **Tbl_Volume_Bulanan**.
- **Katakan:** "Ini data permintaan bulanan Januari 2023 sampai Desember 2025, 36 bulan, yang sama
  dengan data training dan testing di penelitian. Kolom Permintaan_Kg adalah total kg per bulan
  untuk **seluruh Kabupaten Malang**, berbasis produksi daging kambing BPS, tidak dibagi jumlah UMKM.
  Lonjakan setiap Juni adalah efek Iduladha."
- Tunjukkan baris Juni 2023, Juni 2024, Juni 2025 (nilainya jauh lebih besar).

### Langkah 2 – Parameter model
- **Klik ganda** tabel **Tbl_Parameter_SARIMA**.
- **Katakan:** "Ini parameter model final SARIMA(1,0,0)x(1,1,0,12) dengan transformasi log hasil
  pelatihan di Python: ar.L1 = 0,9459 (pengaruh bulan sebelumnya), ar.S.L12 = −0,7953 (pengaruh bulan
  yang sama tahun lalu), sigma2 = varians galat untuk interval kepercayaan, dan Z = 1,96 untuk
  interval 95%. Access cukup menyimpan angka-angka ini, tidak perlu menjalankan Python."

### Langkah 3 – Ramalan 6 bulan (inti demo)
- **Klik ganda** query **qry_12_Ramalan_6_Bulan**.
- **Katakan:** "Query ini menghitung ramalan 6 bulan setelah data terakhir, yaitu Januari sampai Juni
  2026. Kolom Ramalan_Kg adalah perkiraan paling mungkin; Batas_Bawah dan Batas_Atas adalah interval
  kepercayaan 95%."
- Tunjukkan: Januari ±71.327 kg; Juni ±177.280 kg dengan batas atas ±251.233 kg.
- **Katakan:** "Angka ini untuk seluruh kabupaten. Batas atas 251 ton adalah acuan kapasitas wilayah,
  yaitu gabungan RPH, cold storage, dan pasokan ternak, bukan kapasitas satu usaha."
- **Katakan:** "Rentang interval makin lebar ke bulan yang lebih jauh, sesuai prinsip corong
  ketidakpastian. Hasil query ini sama persis dengan hasil Python; selisihnya di bawah 0,000001%."

### Langkah 4 – Menunjukkan rumusnya (opsional, jika dosen bertanya "dihitung bagaimana?")
- Pada query yang terbuka, klik **Home → View → SQL View**.
- **Katakan:** "Rumusnya: ln ŷ = ln y(t−12) + φ^h·(w_L − Φ·w_(L−12)) + Φ·w_(t−12), dengan
  w = ln y(t) − ln y(t−12). Hasilnya dikembalikan ke kg dengan fungsi Exp. Batasnya ŷ dalam log
  ± 1,96 × SE, dengan SE yang membesar sesuai jarak bulan."
- Kembali ke **Datasheet View** (Home → View → Datasheet View). **Jangan menyimpan perubahan** jika
  muncul pertanyaan *save changes* — pilih **No**.

### Langkah 5 – Ramalan bulan depan
- **Klik ganda** query **qry_11_Ramalan_Bulan_Depan**.
- **Katakan:** "Ini versi ringkas: hanya ramalan satu bulan berikutnya, Januari 2026."

### Langkah 6 – Bukti ketepatan (validasi historis)
- **Klik ganda** query **qry_11_Ramalan_1_Bulan_Historis**.
- **Katakan:** "Query yang sama dipakai untuk meramal bulan-bulan 2025 satu bulan ke depan. Contoh
  Juni 2025: ramalan 275.623 kg, aktual 274.672 kg, meleset hanya 0,3%." (Bandingkan dengan
  Tbl_Volume_Bulanan.)

### Langkah 7 – Simulasi input data bulan baru (demo dinamis)
- **Klik ganda** tabel **Tbl_Volume_Bulanan**, gulir ke baris kosong paling bawah (tanda `*`).
- Isi: **Periode** `01/01/2026`, **Tahun** `2026`, **Bulan** `1`, **Permintaan_Kg** `74894`,
  **Sumber** `Simulasi presentasi`. Tekan **Enter**.
- Tutup tabel, lalu **klik ganda lagi** **qry_12_Ramalan_6_Bulan**.
- **Katakan:** "Misalkan Januari 2026 sudah lewat dan penjualan sungguhannya 74.894 kg. Setelah angka
  ini diisi, ramalan otomatis bergeser ke Februari sampai Juli 2026 tanpa menjalankan Python. Inilah
  cara pengelola data kabupaten memperbarui ramalan setiap bulan."
- Hasil yang muncul: Februari ±74.704 kg … Juni ±183.952 kg, Juli ±75.443 kg.
- **Setelah demo:** hapus baris simulasi (klik kotak di kiri baris → tekan **Delete** → **Yes**),
  atau abaikan karena ini file DEMO.

### Langkah 8 – Penutup
- **Katakan:** "Dengan cara ini pengelola data kabupaten cukup memakai MS Access: isi total permintaan
  kabupaten setiap bulan, lalu buka query ramalan. UMKM tidak perlu membuka database; mereka cukup
  memakai indeks, misalnya Juni 2,57 kali bulan normal, lalu mengalikannya dengan penjualan sendiri.
  Parameter model diperbarui setahun sekali oleh peneliti."
- Jika ada waktu, tunjukkan `PANDUAN_PRODUSEN_ACCESS.md` (bagian D2: tabel indeks UMKM) sebagai
  panduan pengguna.

---

## 4. Antisipasi pertanyaan dosen

| Pertanyaan | Jawaban singkat |
|---|---|
| Kenapa Access, bukan Python? | Pengelola data di Dinas/RPH/asosiasi umumnya memakai Access/Excel; pengguna tidak perlu instal atau memahami Python. Python dipakai peneliti untuk melatih model. |
| Kenapa datanya tidak dibagi jumlah UMKM? | Jumlah UMKM daging kambing di Kabupaten Malang tidak diketahui pasti, sehingga pembagian akan bergantung pada asumsi tanpa sumber. Data dipakai apa adanya (agregat kabupaten dari BPS). Karena model memakai log dan differencing musiman, skala data tidak memengaruhi parameter maupun MAPE; yang berubah hanya satuan tafsirannya. |
| Lalu "pasar lokal" itu apa? | Pasar daging kambing Kabupaten Malang secara agregat. Angka kg untuk perencanaan tingkat kabupaten; UMKM memakai indeks/persentase yang tidak bergantung skala usaha. |
| Bagaimana UMKM memakai hasilnya? | Rencana stok = penjualan bulan normal UMKM × indeks bulan; kapasitas maksimum = rencana × faktor batas atas. Contoh UMKM 500 kg/bulan: Juni 2026 rencana ±1.285 kg, maksimum ±1.821 kg (`data\hasil_11\11_rek_panduan_umkm_2026.csv`). |
| Kenapa model final SARIMA, padahal MAPE ARIMAX lebih kecil (4,00% vs 6,59%)? | ARIMAX butuh harga rata-rata bulan yang diramal. Saat meramal Jan–Jun 2026 harga itu belum diketahui. Di evaluasi, ARIMAX memakai harga aktual testing sehingga akurasinya optimistis. Model final dipilih dari model yang lulus diagnostik **dan** tidak butuh data masa depan. |
| Target RMSE/MAE/MSE-nya berapa? | Dibuat relatif terhadap rata-rata permintaan (ȳ testing 113.751 kg): RMSE < 10% × ȳ = 11.375 kg, MAE < 8% × ȳ = 9.100 kg, MSE < (10% × ȳ)². Model final lulus semua target: RMSE 7.395 kg (6,5% ȳ), MAE 6.102 kg. |
| Kenapa tidak sekadar "penjualan × faktor musiman" seperti contoh? | Itu hanya ilustrasi. Query memakai persamaan SARIMA lengkap (AR, AR musiman, differencing musiman, log), sehingga hasilnya identik dengan model statsmodels. Faktor musiman tetap disediakan di qry_11_Faktor_Musiman sebagai informasi. |
| Apakah hasil Access sama dengan Python? | Ya, sudah diverifikasi; selisih di bawah 0,000001% (`data\hasil_12\12_verifikasi_ramalan_6_bulan.csv`). |
| Bagaimana kalau parameternya berubah? | Peneliti melatih ulang model setahun sekali di Python dan cukup memperbarui isi Tbl_Parameter_SARIMA; query tidak perlu diubah. |
| Ramalan 2026 sudah divalidasi? | Belum bisa karena data aktual 2026 belum ada. Akurasi dibuktikan pada data testing 2025: MAPE 6,59–7,61%, di bawah target 15%. Ramalan 2026 adalah proyeksi. |
| Kenapa puncak di Juni padahal Iduladha 2026 akhir Mei? | Model meniru pola 2023–2025 (Iduladha di Juni). Ini keterbatasan yang dicatat; rekomendasinya kapasitas puncak disiapkan sejak pertengahan Mei. |
| Kenapa ramalan 2026 lebih rendah dari 2025? | Efek koefisien musiman yang mengulang penurunan level 2023→2024 dari data 3 tahun; dicatat sebagai keterbatasan, bukan tren pasti. |
| Kenapa ada transformasi log? | Lonjakan Iduladha bersifat perkalian (±2,7 kali); log membuat residual model normal (lulus Shapiro-Wilk) dan estimasi stabil. |
| Tabel Transaksi_Penjualan dipakai? | Tidak untuk ramalan. Data ramalan memakai Tbl_Volume_Bulanan (total kg per bulan). |

---

## 5. Jika terjadi masalah saat demo

| Masalah | Solusi |
|---|---|
| Muncul pita kuning *SECURITY WARNING* | Klik **Enable Content**. |
| Panel kiri tidak terlihat | Tekan **F11**. |
| Query tidak muncul di panel | Klik judul panel → **All Access Objects**. |
| Pesan "file already in use" / terkunci | Tutup Access lain atau Python yang membuka file; atau pakai file DEMO. |
| Muncul kotak "Enter Parameter Value" | Biasanya salah ketik saat mengedit SQL. Klik Cancel, tutup query tanpa menyimpan, buka ulang. |
| Hasil ramalan tidak berubah setelah input | Pastikan Periode diisi tanggal 1 bulan yang tepat dan tidak ada bulan terlewat; tutup lalu buka ulang query. |
| Access gagal total | Tampilkan gambar cadangan `11_hasil_access.png` dan fan chart `09_fan_chart.png`. |

---

## 6. Penjelasan tabel dan query di database

Objek di database dibagi menjadi tiga kelompok:
- **Inti sistem peramalan** (dipakai pengelola data kabupaten dan saat demo),
- **Query pendukung perhitungan** (dipakai oleh query lain; tidak perlu dibuka pengguna),
- **Objek lama dari tahap awal penelitian** (tidak dipakai untuk peramalan).

### 6.1 Tabel inti sistem peramalan

| Tabel | Fungsi | Kolom penting |
|---|---|---|
| **Tbl_Volume_Bulanan** | Data permintaan bulanan agregat Kabupaten Malang yang menjadi **input** peramalan. Diisi pengelola data kabupaten setiap awal bulan untuk bulan yang baru lewat. | `Periode` (tanggal 1 tiap bulan), `Tahun`, `Bulan`, `Permintaan_Kg` (total kg kabupaten), `Harga_Rata2_Per_Kg`, `Sumber` |
| **Tbl_Parameter_SARIMA** | Menyimpan **parameter model** hasil pelatihan Python. Jangan diubah pengguna. | `Nama_Parameter`, `Nilai`, `Keterangan`. Isinya: `ar.L1` = φ (pengaruh bulan sebelumnya, 0,9459), `ar.S.L12` = Φ (pengaruh bulan yang sama tahun lalu, −0,7953), `sigma2` (varians galat, 0,0068), `m` = 12 (periode musiman), `Z_95` = 1,96 |
| **Tbl_Faktor_Musiman** | Informasi pendukung: rata-rata permintaan tiap bulan dibanding rata-rata keseluruhan. **Bukan** bagian rumus ramalan. | `Bulan`, `Nama_Bulan`, `Rata2_Permintaan_Kg`, `Faktor_Musiman` (Juni = 2,452 artinya Juni ±2,5 kali rata-rata) |
| **Tbl_Peramalan** | Arsip hasil ramalan 6 bulan yang disimpan pada tahap implementasi (script 11). Ramalan terbaru yang selalu mengikuti data dihitung oleh `qry_12_Ramalan_6_Bulan`. | `Periode`, `Horizon`, `Prediksi_Kg`, `Batas_Bawah_95_Kg`, `Batas_Atas_95_Kg`, `Sumber`, `Tanggal_Dibuat` |

### 6.2 Query inti (yang dibuka pengguna / saat demo)

| Query | Fungsi | Hasil |
|---|---|---|
| **qry_12_Ramalan_6_Bulan** | **Query utama.** Menghitung ramalan 6 bulan setelah data terakhir di Tbl_Volume_Bulanan, langsung dengan rumus SARIMA. Otomatis bergeser saat data bulan baru diisi. | `Bulan_Ke` (1–6), `Periode`, `Ramalan_Kg`, `Batas_Bawah_95_Kg`, `Batas_Atas_95_Kg` |
| **qry_11_Ramalan_Bulan_Depan** | Ramalan satu bulan berikutnya saja (versi ringkas). | `Periode_Ramalan`, `Periode_Asal` (data terakhir), `Prediksi_Kg`, batas bawah/atas 95% |
| **qry_11_Ramalan_1_Bulan_Historis** | Ramalan satu bulan ke depan untuk setiap bulan di masa lalu (2025). Dipakai untuk **membuktikan ketepatan** dengan membandingkan terhadap data aktual. | `Periode_Ramalan`, `Periode_Asal`, `Prediksi_Kg`, batas bawah/atas 95% |
| **qry_11_Peramalan_6_Bulan** | Menampilkan isi arsip Tbl_Peramalan (ramalan yang disimpan script 11) dalam format bulan yang rapi. | `Bulan` (nama bulan), `Horizon`, `Ramalan_Kg`, `Batas_Bawah_95`, `Batas_Atas_95` |
| **qry_11_Volume_Bulanan** | Menampilkan data bulanan beserta nilai logaritmanya. | `Periode`, `Permintaan_Kg`, `Ln_Permintaan` |
| **qry_11_Faktor_Musiman** | Menampilkan Tbl_Faktor_Musiman dengan angka dibulatkan. | `Nama_Bulan`, `Rata2_Kg`, `Faktor` |

Perbedaan `qry_12_Ramalan_6_Bulan` dan `qry_11_Peramalan_6_Bulan`: keduanya menampilkan ramalan 6 bulan
dengan angka yang sama saat ini, tetapi **qry_12 dihitung ulang setiap dibuka** (ikut data terbaru),
sedangkan **qry_11 hanya menampilkan arsip** yang pernah disimpan. Untuk pengguna gunakan **qry_12**.

### 6.3 Query pendukung perhitungan (tidak perlu dibuka)

| Query | Fungsi |
|---|---|
| **qry_12_Data_Log** | Menghitung ln(permintaan) dan selisih musiman w = ln y(t) − ln y(t−12) untuk setiap bulan. |
| **qry_12_Bulan_Terakhir** | Mencari bulan data terakhir di Tbl_Volume_Bulanan (titik awal ramalan). |
| **qry_12_Titik_Awal** | Mengambil nilai w bulan terakhir dan w 12 bulan sebelumnya, sebagai bahan rumus ramalan. |

Alur perhitungannya:
`Tbl_Volume_Bulanan` → `qry_12_Data_Log` → `qry_12_Bulan_Terakhir` + `qry_12_Titik_Awal`
→ `qry_12_Ramalan_6_Bulan` (memakai parameter dari `Tbl_Parameter_SARIMA`).

### 6.4 Objek lama dari tahap awal penelitian (tidak dipakai untuk peramalan)

| Objek | Keterangan |
|---|---|
| **Transaksi_Penjualan** | Tabel transaksi dari tahap awal (versi data lama, 1.787 transaksi). Tidak dipakai model. |
| **Pelanggan** | Daftar pelanggan dan tipenya (30 baris). |
| **Hasil_Prediksi**, **Evaluasi_Model** | Tabel rancangan awal, masih kosong. Hasil penelitian akhir disimpan di tabel/query baru di atas. |
| **qry_Permintaan_Bulanan**, **qry_Permintaan_Per_Tipe_Pelanggan**, **qry_Prediksi_6_Bulan**, **qry_Perbandingan_Model** | Query rancangan awal yang membaca tabel lama di atas. |

Jika dosen bertanya tentang objek lama: "Objek ini dari rancangan awal database dan dipertahankan apa
adanya. Sistem peramalan final memakai Tbl_Volume_Bulanan, Tbl_Parameter_SARIMA, dan query qry_11/qry_12."
