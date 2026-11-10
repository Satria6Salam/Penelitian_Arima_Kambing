# Panduan Presentasi: Hasil Forecasting sampai Simulasi MS Access

Cakupan: peramalan data testing → peramalan Jan–Jun 2026 → penyesuaian Iduladha →
implementasi MS Access → demo/simulasi Access → (opsional) rekomendasi.
Durasi sekitar **15–18 menit** (demo Access ±6 menit).

Alur yang diceritakan:

```
08 Peramalan data testing  →  09 Ramalan Jan–Jun 2026  →  13 Penyesuaian Iduladha
   (bukti akurasi)              (model final, fan chart)      (puncak geser ke Mei)
                                         │
                                         ▼
               11/12 Implementasi Access (parameter + query)  →  DEMO MS Access
```

---

## 0. Persiapan (H-1 dan sebelum presentasi)

1. **Buat file demo** (database asli jangan dipakai untuk demo). Tutup MS Access dulu, lalu di PowerShell
   dari folder proyek:
   ```powershell
   Copy-Item data\db_penjualan_kambing.accdb data\db_penjualan_kambing_DEMO.accdb
   ```
2. **Buka tab-tab berikut sebelum presentasi** (urut sesuai alur):

   | Urutan | Jenis | File |
   |---|---|---|
   | 1 | Plot | `data\hasil_08\grafik\08_fan_chart_SARIMA_D1.png` |
   | 2 | Plot | `data\hasil_08\grafik\08_perbandingan_peramalan.png` |
   | 3 | CSV | `data\hasil_08\08_evaluasi_peramalan.csv` |
   | 4 | Plot | `data\hasil_09\validasi_apr_sep_2025\grafik\09_fan_chart_validasi.png` |
   | 5 | Plot | `data\hasil_09\grafik\09_fan_chart.png` |
   | 6 | CSV | `data\hasil_09\09_peramalan_jan_jun_2026.csv` |
   | 7 | Plot | `data\hasil_13\grafik\13_ramalan_disesuaikan.png` |
   | 8 | CSV | `data\hasil_13\13_peramalan_disesuaikan_iduladha.csv` |
   | 9 | Kode | `sql\12_query_ramalan_6_bulan.sql` |
   | 10 | CSV | `data\hasil_12\12_verifikasi_ramalan_6_bulan.csv` |
   | 11 | Access | `data\db_penjualan_kambing_DEMO.accdb` (sudah **Enable Content**, panel kiri **All Access Objects**) |
   | 12 | Cadangan | `data\hasil_11\access_output\11_hasil_access.png` (jika Access bermasalah) |

3. File kode (`.py`) cukup dibuka di VS Code. **Tidak perlu menjalankan ulang script saat presentasi**,
   karena semua hasil sudah tersimpan. Tunjukkan fungsi kuncinya saja (lihat tiap bagian).
4. Tutup Python/Excel yang membuka file `.accdb`.

---

## 1. Peramalan pada data testing (±3 menit)

**Tujuan:** membuktikan model mampu meramal data yang tidak pernah dilihat (blind forecast).

| Jenis | File | Yang ditunjukkan |
|---|---|---|
| Kode | [08_forecasting_data_testing.py](08_forecasting_data_testing.py) | `peramalan()`: model dilatih 27 bulan training lalu meramal 9 bulan sekaligus; `evaluasi()`: MAPE, RMSE, MAE, MSE, R², cakupan interval 95% |
| CSV | `data\hasil_08\08_peramalan_testing.csv` | Ramalan vs aktual per bulan (Apr–Des 2025) |
| CSV | `data\hasil_08\08_evaluasi_peramalan.csv` | Metrik akurasi per model + status target |
| CSV | `data\hasil_08\08_multistep_vs_rolling.csv` | Akurasi makin jauh horizon |
| Plot | `08_fan_chart_SARIMA_D1.png` | Garis ramalan, pita 95%, titik aktual testing |
| Plot | `08_perbandingan_peramalan.png` | Semua model + seasonal naive dalam satu grafik |
| Ringkasan | [08_ringkasan_forecasting.md](08_ringkasan_forecasting.md) | Tabel siap kutip |

**Angka kunci (SARIMA D=1, model final):**
- Ramalan 9 bulan sekaligus: **MAPE 6,98%**, RMSE 7.818 kg, R² 0,98. Seasonal naive: MAPE 14,73%.
- Target relatif (ȳ testing 113.751 kg): RMSE < 11.375 kg, MAE < 9.100 kg → **lulus semua target**.
- Interval 95% memuat aktual pada **8 dari 9 bulan**.
- Juni 2025 (Iduladha): ramalan 269.022 kg vs aktual 274.672 kg (meleset 2,1%).

**Kalimat kunci:**
> "Model dilatih sampai Maret 2025, lalu meramal April sampai Desember 2025 tanpa melihat data aktual.
> Hasilnya MAPE 6,98%, kurang dari setengah kesalahan metode 'sama dengan tahun lalu'."

**Jika ditanya soal ARIMAX** (MAPE 3,84%): ARIMAX memakai harga **aktual** bulan testing; saat
meramal 2026 harga belum diketahui, jadi model final dipilih dari model tanpa eksogen masa depan.

---

## 2. Peramalan Jan–Jun 2026 (±3 menit)

**Tujuan:** menunjukkan ramalan masa depan dari model final yang di-fit ulang pada 36 bulan.

| Jenis | File | Yang ditunjukkan |
|---|---|---|
| Kode | [09_peramalan_visualisasi.py](09_peramalan_visualisasi.py) | `HORIZON = 6`, `Z = 1,96`; `bagian_validasi()` (parameter dikunci dari training, uji Apr–Sep 2025); `bagian_utama()` (fit 36 bulan, ramal 6 bulan); `ekstrapolasi()` (interval di skala log lalu `exp()`) |
| CSV | `data\hasil_09\validasi_apr_sep_2025\09_peramalan_validasi_apr_sep_2025.csv` | Validasi 6 bulan: MAPE 7,61%, 5/6 di dalam interval |
| CSV | `data\hasil_09\09_parameter_model_final.csv` | φ = 0,9459; Φ = −0,7953; σ² = 0,0068 |
| CSV | `data\hasil_09\09_diagnostik_model_final.csv` | Ljung-Box & Shapiro-Wilk tetap lulus setelah fit 36 bulan |
| CSV | `data\hasil_09\09_peramalan_jan_jun_2026.csv` | Ŷ, SE, batas bawah/atas per bulan |
| Plot | `09_fan_chart_validasi.png` lalu `09_fan_chart.png` | Validasi dulu, baru ramalan 2026 |
| Ringkasan | [09_ringkasan_peramalan.md](09_ringkasan_peramalan.md) | Termasuk contoh hitung manual h = 1 |

**Angka kunci (seluruh Kabupaten Malang):**

| Bulan 2026 | Ŷ (kg) | Batas bawah | Batas atas |
|---|---|---|---|
| Jan | 71.327 | 60.653 | 83.880 |
| Feb | 71.335 | 57.069 | 89.168 |
| Mar | 69.364 | 53.157 | 90.514 |
| Apr | 67.206 | 49.817 | 90.665 |
| Mei | 65.768 | 47.456 | 91.146 |
| Jun | 177.280 | 125.095 | 251.233 |

**Kalimat kunci:**
> "Pita biru melebar ke bulan yang lebih jauh: SE skala log naik dari 0,083 (Januari) ke 0,178 (Juni).
> Ini efek corong ketidakpastian. Interval tidak simetris karena dihitung di skala log."

Contoh hitung (jika diminta): ln Ŷ Jan = 11,1750 → Ŷ = e^11,1750 = 71.327 kg;
batas = exp(11,1750 ∓ 1,96 × 0,0827) = 60.653 – 83.880 kg.

---

## 3. Penyesuaian kalender Iduladha (±2 menit)

**Tujuan:** menjelaskan bahwa puncak ramalan model (Juni) perlu digeser karena Iduladha 2026 jatuh ±27 Mei.

| Jenis | File | Yang ditunjukkan |
|---|---|---|
| Kode | [13_penyesuaian_iduladha.py](13_penyesuaian_iduladha.py) | `TANGGAL_IDULADHA` (tabel tanggal), `bobot_jendela()` (porsi hari H−7 s.d. H+3 per bulan), `sesuaikan()` (Ŷ disesuaikan = Ŷ dasar × R^bobot) |
| CSV | `data\hasil_13\13_bobot_jendela_iduladha.csv` | 2026: bobot Mei = 1,00 |
| CSV | `data\hasil_13\13_peramalan_disesuaikan_iduladha.csv` | Ramalan sebelum vs sesudah + indeks UMKM |
| Plot | `13_ramalan_disesuaikan.png` | Garis abu-abu (model) vs biru (disesuaikan), garis merah 27 Mei |
| Ringkasan | [13_ringkasan_penyesuaian_iduladha.md](13_ringkasan_penyesuaian_iduladha.md) | Metode + keterbatasan |

**Angka kunci:** R = 177.280 ÷ 65.768 = **2,696**. Setelah disesuaikan: **Mei 177.280 kg** (batas atas
245.686 kg), Juni kembali normal 65.768 kg.

**Kalimat kunci:**
> "SARIMA memakai musim tetap 12 bulan, jadi ia mengulang puncak di Juni seperti 2023–2025. Iduladha
> maju sekitar 11 hari per tahun, sehingga hasil model kami sesuaikan sebagai post-processing: model dan
> parameternya tidak diubah, hanya efek Iduladhanya dipindah ke bulan yang benar."

Keterbatasan yang harus disebut: penyesuaian berbasis asumsi teori (data 2023–2025 semuanya Juni,
sehingga tidak bisa divalidasi dengan data historis).

---

## 4. Implementasi ke MS Access (±2 menit, sebelum demo)

**Tujuan:** menjelaskan bagaimana model Python dipindahkan ke Access (strategi *parameter-driven query*).

| Jenis | File | Yang ditunjukkan |
|---|---|---|
| Kode | [11_implementasi_access.py](11_implementasi_access.py) | `buat_tabel()`: membuat Tbl_Volume_Bulanan & Tbl_Parameter_SARIMA; `buat_query()`: query qry_11_*; `verifikasi()`: Access vs Python |
| Kode | [12_ramalan_6_bulan_access.py](12_ramalan_6_bulan_access.py) | `pasang_query()`: memasang 4 query qry_12_*; `baca_dao()`: membaca hasil dari MS Access asli; uji dinamis di salinan database |
| Kode SQL | [sql/12_query_ramalan_6_bulan.sql](sql/12_query_ramalan_6_bulan.sql) | Rumus SARIMA bentuk tertutup dalam SQL (Exp, Log, Sqr) |
| CSV | `data\hasil_11\access_output\Tbl_Parameter_SARIMA.csv` | Parameter yang disimpan di Access |
| CSV | `data\hasil_12\12_verifikasi_ramalan_6_bulan.csv` | Selisih Access vs Python < 0,0000003% |
| CSV | `data\hasil_12\12_uji_dinamis_ramalan_feb_jul_2026.csv` | Hasil yang akan muncul saat simulasi input Januari 2026 |

**Kalimat kunci:**
> "Python hanya dipakai untuk melatih model. Parameternya disimpan di tabel Access, dan ramalan dihitung
> oleh query SQL dengan rumus SARIMA yang sama. Rumus rekursif kami jabarkan menjadi bentuk tertutup
> karena Access menolak query bertingkat terlalu dalam. Hasilnya identik dengan Python."

Rumus yang ditampilkan (h ≤ 12):
```
w_t            = ln y_t − ln y_(t−12)
ln ŷ(L+h)      = ln y_(L+h−12) + φ^h·(w_L − Φ·w_(L−12)) + Φ·w_(L+h−12)
SE(h)          = √( σ² · (1 − φ^(2h)) / (1 − φ²) )
batas 95%      = exp( ln ŷ ∓ 1,96 · SE(h) )
```

---

## 5. Urutan mengoperasikan MS Access saat demo (±6 menit)

Pakai `db_penjualan_kambing_DEMO.accdb`. Detail kalimat per langkah ada di
[PANDUAN_PRESENTASI_ACCESS.md](PANDUAN_PRESENTASI_ACCESS.md) bagian 3.

| No | Klik | Yang dijelaskan | Angka yang ditunjuk |
|---|---|---|---|
| 1 | Buka file → **Enable Content** → F11 (panel kiri) → **All Access Objects** | Struktur: tabel input, tabel parameter, query | – |
| 2 | Klik ganda tabel **Tbl_Volume_Bulanan** | Data input 36 bulan, agregat Kabupaten Malang | Juni 2023/2024/2025 jauh lebih besar |
| 3 | Klik ganda tabel **Tbl_Parameter_SARIMA** | Parameter hasil pelatihan Python | ar.L1 0,9459; ar.S.L12 −0,7953; sigma2 0,0068; Z 1,96 |
| 4 | Klik ganda query **qry_12_Ramalan_6_Bulan** | **Inti demo**: ramalan 6 bulan + interval 95% dihitung Access | Jan 71.327; Jun 177.280 (batas atas 251.233) |
| 5 | (Opsional) **Home → View → SQL View** | Rumus SARIMA di SQL; kembali ke Datasheet View, **No** saat ditanya save | – |
| 6 | Klik ganda **qry_11_Ramalan_1_Bulan_Historis** | Bukti ketepatan pada 2025 | Jun 2025: ramalan 275.623 vs aktual 274.672 (0,3%) |
| 7 | Klik ganda **qry_11_Ramalan_Bulan_Depan** | Versi ringkas: hanya bulan berikutnya | Jan 2026: 71.327 |
| 8 | **Simulasi input**: buka **Tbl_Volume_Bulanan** → baris `*` paling bawah → isi Periode `01/01/2026`, Tahun `2026`, Bulan `1`, Permintaan_Kg `74894`, Sumber `Simulasi presentasi` → **Enter** → tutup tabel | Pengelola data kabupaten mengisi data bulan yang baru lewat | – |
| 9 | Klik ganda lagi **qry_12_Ramalan_6_Bulan** | Ramalan otomatis bergeser ke Feb–Jul 2026 tanpa Python | Feb 74.704; Jun 183.952; Jul 75.443 |
| 10 | Kembali ke plot `13_ramalan_disesuaikan.png` | Access menampilkan ramalan model (puncak Juni); untuk perencanaan, puncak dibaca di **Mei** sesuai penyesuaian Iduladha | Mei 2026: 177.280 kg |
| 11 | Setelah demo: hapus baris simulasi (klik kotak kiri baris → Delete → Yes) | – | – |

**Kalimat penutup demo:**
> "Pengelola data kabupaten cukup mengisi total permintaan setiap bulan, lalu membuka satu query.
> UMKM memakai hasilnya sebagai indeks, misalnya bulan Iduladha 2,57 kali bulan normal.
> Parameter model diperbarui setahun sekali oleh peneliti."

---

## 6. (Opsional) Rekomendasi singkat sebagai penutup (±1–2 menit)

| Jenis | File |
|---|---|
| Kode | [11_rekomendasi_manajerial.py](11_rekomendasi_manajerial.py) (`analisis_stok()`, `analisis_umkm()`) |
| CSV | `data\hasil_11\11_rek_stok_testing.csv`, `data\hasil_11\11_rek_panduan_umkm_2026.csv` |
| Ringkasan | [11_rekomendasi_manajerial.md](11_rekomendasi_manajerial.md) |

- Kabupaten: kekurangan pasokan turun **75,7%** dibanding "sama seperti tahun lalu"; kapasitas wilayah
  puncak disiapkan sampai batas atas, **siap pertengahan Mei 2026**.
- UMKM: rencana stok = penjualan bulan normal × indeks (Iduladha ±2,57×, faktor batas atas ±1,4).

---

## 7. Rundown waktu

| Menit | Bagian | Tampilan utama |
|---|---|---|
| 0–3 | 1. Peramalan data testing | `08_fan_chart_SARIMA_D1.png`, `08_evaluasi_peramalan.csv` |
| 3–6 | 2. Ramalan Jan–Jun 2026 | `09_fan_chart_validasi.png`, `09_fan_chart.png` |
| 6–8 | 3. Penyesuaian Iduladha | `13_ramalan_disesuaikan.png` |
| 8–10 | 4. Implementasi Access | `12_query_ramalan_6_bulan.sql`, `12_verifikasi_ramalan_6_bulan.csv` |
| 10–16 | 5. Demo Access | `db_penjualan_kambing_DEMO.accdb` |
| 16–18 | 6. Rekomendasi & penutup | `11_rekomendasi_manajerial.md` |

---

## 8. Antisipasi pertanyaan (khusus bagian ini)

| Pertanyaan | Jawaban singkat |
|---|---|
| Kenapa ramalan Access puncaknya di Juni, padahal sudah disesuaikan ke Mei? | Access menghitung persis model SARIMA (hasilnya identik dengan Python). Penyesuaian Iduladha adalah post-processing di script 13 untuk perencanaan; model dan query tidak diubah. |
| Kenapa ramalan 2026 lebih rendah dari 2025 (±−23%)? | Efek koefisien musiman Φ = −0,80 yang mengulang penurunan 2023→2024 dari data yang hanya 3 tahun. Dibaca sebagai skenario konservatif dan diperbarui saat data 2026 masuk. |
| Kenapa interval melebar? | SE(h) bertambah dengan horizon h; makin jauh bulan, makin besar ketidakpastian (corong). |
| Apakah 8 dari 9 bulan di dalam interval 95% itu wajar? | Ya. Interval 95% berarti ±1 dari 20 bulan boleh di luar; 1 dari 9 masih wajar untuk sampel kecil. |
| Apakah angka 251 ton untuk satu usaha? | Tidak. Itu kapasitas wilayah Kabupaten Malang. UMKM memakai indeks. |
| Bagaimana jika data bulan baru salah isi? | Perbaiki langsung di Tbl_Volume_Bulanan; query menghitung ulang setiap kali dibuka. |

Pertanyaan umum lain (data tidak dibagi UMKM, pemilihan SARIMA vs ARIMAX, target RMSE relatif) ada di
[PANDUAN_PRESENTASI_ACCESS.md](PANDUAN_PRESENTASI_ACCESS.md) bagian 4.
