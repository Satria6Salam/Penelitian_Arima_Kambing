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
- Ramalan 9 bulan sekaligus: **MAPE 9,07%**, RMSE 18.484 kg, MAE 14.171 kg, R² 0,94. Seasonal naive: MAPE 8,81% (RMSE 26.773 kg).
- Target relatif (ȳ testing 145.698 kg): RMSE < 14.570 kg, MAE < 11.656 kg → MAPE dan R² **lulus**, RMSE dan MAE **belum lulus**.
- Interval 95% memuat aktual pada **9 dari 9 bulan**.
- Juni 2025 (Iduladha): ramalan 312.294 kg vs aktual 356.163 kg (meleset 12,3%); seasonal naive meleset 20,7%.
- Model cenderung meramal terlalu rendah (7 dari 9 bulan di bawah aktual).

**Kalimat kunci:**
> "Model dilatih sampai Maret 2025, lalu meramal April sampai Desember 2025 tanpa melihat data aktual.
> Hasilnya MAPE 9,07%, memenuhi target 15%. Namun metode 'sama dengan tahun lalu' juga mencapai 8,81%,
> jadi keunggulan SARIMA pada peramalan 9 bulan tidak terlihat; keunggulannya ada pada rolling origin (7,51%)."

**Jika ditanya soal ARIMAX** (MAPE multilangkah 6,38%): ARIMAX memakai harga **aktual** bulan testing; saat
meramal 2026 harga belum diketahui, jadi model final dipilih dari model tanpa eksogen masa depan.

---

## 2. Peramalan Jan–Jun 2026 (±3 menit)

**Tujuan:** menunjukkan ramalan masa depan dari model final yang di-fit ulang pada 36 bulan.

| Jenis | File | Yang ditunjukkan |
|---|---|---|
| Kode | [09_peramalan_visualisasi.py](09_peramalan_visualisasi.py) | `HORIZON = 6`, `Z = 1,96`; `bagian_validasi()` (parameter dikunci dari training, uji Apr–Sep 2025); `bagian_utama()` (fit 36 bulan, ramal 6 bulan); `ekstrapolasi()` (interval di skala log lalu `exp()`) |
| CSV | `data\hasil_09\validasi_apr_sep_2025\09_peramalan_validasi_apr_sep_2025.csv` | Validasi 6 bulan: MAPE 10,46%, 6/6 di dalam interval |
| CSV | `data\hasil_09\09_parameter_model_final.csv` | φ = 0,6049; Φ = −0,6906; σ² = 0,0058 |
| CSV | `data\hasil_09\09_diagnostik_model_final.csv` | Ljung-Box & Shapiro-Wilk tetap lulus setelah fit 36 bulan |
| CSV | `data\hasil_09\09_peramalan_jan_jun_2026.csv` | Ŷ, SE, batas bawah/atas per bulan |
| Plot | `09_fan_chart_validasi.png` lalu `09_fan_chart.png` | Validasi dulu, baru ramalan 2026 |
| Ringkasan | [09_ringkasan_peramalan.md](09_ringkasan_peramalan.md) | Termasuk contoh hitung manual h = 1 |

**Angka kunci (seluruh Kabupaten Malang):**

| Bulan 2026 | Ŷ (kg) | Batas bawah | Batas atas |
|---|---|---|---|
| Jan | 108.757 | 93.632 | 126.325 |
| Feb | 111.595 | 93.679 | 132.937 |
| Mar | 112.341 | 93.519 | 134.952 |
| Apr | 109.806 | 91.137 | 132.299 |
| Mei | 109.254 | 90.582 | 131.776 |
| Jun | 301.478 | 249.855 | 363.766 |

Ini ramalan **model** (puncak di Juni). Versi yang dipakai untuk perencanaan adalah hasil penyesuaian
Iduladha di bagian 3 (puncak di Mei).

**Kalimat kunci:**
> "Pita biru melebar ke bulan yang lebih jauh: SE skala log naik dari 0,0764 (Januari) ke 0,0958 (Juni).
> Ini efek corong ketidakpastian. Interval tidak simetris karena dihitung di skala log."

Contoh hitung (jika diminta): ln Ŷ Jan = 11,5969 → Ŷ = e^11,5969 = 108.757 kg;
batas = exp(11,5969 ∓ 1,96 × 0,0764) = 93.632 – 126.325 kg.

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

**Angka kunci:** R = 301.478 ÷ 109.254 = **2,759**. Setelah disesuaikan: **Mei 301.478 kg** (batas atas
363.624 kg), Juni kembali normal 109.254 kg.

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
| Kode | [16_penyesuaian_iduladha_access.py](16_penyesuaian_iduladha_access.py) | Tabel `Tbl_16_*` dan query `qry_16_*`: penyesuaian Iduladha dihitung di Access, diverifikasi terhadap script 13 |
| Kode SQL | [sql/12_query_ramalan_6_bulan.sql](sql/12_query_ramalan_6_bulan.sql) | Rumus SARIMA bentuk tertutup dalam SQL (Exp, Log, Sqr) |
| CSV | `data\hasil_11\access_output\Tbl_Parameter_SARIMA.csv` | Parameter yang disimpan di Access |
| CSV | `data\hasil_12\12_verifikasi_ramalan_6_bulan.csv` | Selisih Access vs Python maks. 9,1 × 10⁻⁸% |
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
| 3 | Klik ganda tabel **Tbl_Parameter_SARIMA** | Parameter hasil pelatihan Python | ar.L1 0,6049; ar.S.L12 −0,6906; sigma2 0,0058; Z 1,96 |
| 4 | Klik ganda query **qry_12_Ramalan_6_Bulan** | **Inti demo**: ramalan 6 bulan + interval 95% dihitung Access | Jan 108.757; Jun 301.478 (batas atas 363.766) |
| 5 | (Opsional) **Home → View → SQL View** | Rumus SARIMA di SQL; kembali ke Datasheet View, **No** saat ditanya save | – |
| 6 | Klik ganda **qry_11_Ramalan_1_Bulan_Historis** | Bukti ketepatan pada 2025 | Jun 2025: ramalan 335.676 vs aktual 356.163 (5,8%) |
| 7 | Klik ganda **qry_11_Ramalan_Bulan_Depan** | Versi ringkas: hanya bulan berikutnya | Jan 2026: 108.757 |
| 8 | **Simulasi input**: buka **Tbl_Volume_Bulanan** → baris `*` paling bawah → isi Periode `01/01/2026`, Tahun `2026`, Bulan `1`, Permintaan_Kg `114195`, Sumber `Simulasi presentasi` → **Enter** → tutup tabel | Pengelola data kabupaten mengisi data bulan yang baru lewat | – |
| 9 | Klik ganda lagi **qry_12_Ramalan_6_Bulan** | Ramalan otomatis bergeser ke Feb–Jul 2026 tanpa Python | Feb 114.937; Jun 302.671; Jul 122.358 |
| 10 | Klik ganda **qry_16_Ramalan_Disesuaikan** (lalu tunjukkan plot `13_ramalan_disesuaikan.png`) | Ramalan yang puncaknya sudah digeser ke bulan Iduladha, dihitung Access | Setelah simulasi: Mei 302.671; Juni 109.970 (tanpa simulasi: Mei 301.478) |
| 11 | Setelah demo: hapus baris simulasi (klik kotak kiri baris → Delete → Yes) | – | – |

**Kalimat penutup demo:**
> "Pengelola data kabupaten cukup mengisi total permintaan setiap bulan, lalu membuka satu query.
> UMKM memakai hasilnya sebagai indeks, misalnya Mei 2026 (bulan Iduladha) 2,73 kali bulan normal.
> Parameter model diperbarui setahun sekali oleh peneliti."

---

## 6. (Opsional) Rekomendasi singkat sebagai penutup (±1–2 menit)

| Jenis | File |
|---|---|
| Kode | [11_rekomendasi_manajerial.py](11_rekomendasi_manajerial.py) (`analisis_stok()`, `analisis_umkm()`) |
| CSV | `data\hasil_11\11_rek_stok_testing.csv`, `data\hasil_11\11_rek_panduan_umkm_2026.csv` |
| Ringkasan | [11_rekomendasi_manajerial.md](11_rekomendasi_manajerial.md) |

- Kabupaten: pada data testing, total selisih rencana stok vs aktual turun **10,7%** dibanding "sama seperti
  tahun lalu" (kelebihan stok 36.263 → 18.938 kg, kekurangan sedikit naik 106.495 → 108.603 kg karena model
  cenderung meramal rendah). Kapasitas wilayah puncak disiapkan sampai batas atas 363.624 kg, **siap pertengahan Mei 2026**.
- UMKM: rencana stok = penjualan bulan normal × indeks (Mei 2026 ±2,73×, faktor batas atas 1,16–1,21).

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
| Kenapa qry_12 puncaknya di Juni, padahal sudah disesuaikan ke Mei? | qry_12 menghitung persis model SARIMA (identik dengan Python). Penyesuaian Iduladha adalah post-processing: di Python oleh script 13, di Access oleh `qry_16_Ramalan_Disesuaikan` (hasil keduanya sama). Model dan parameternya tidak diubah. |
| Kenapa ramalan 2026 lebih rendah dari 2025 (±−6%)? | Dengan data hanya 3 tahun, koefisien model belum stabil (φ 0,436 di data latih → 0,605 pada 36 bulan). Dibaca sebagai skenario konservatif dan diperbarui saat data 2026 masuk. |
| Kenapa interval melebar? | SE(h) bertambah dengan horizon h; makin jauh bulan, makin besar ketidakpastian (corong). |
| Semua 9 bulan di dalam interval 95%, apakah intervalnya terlalu lebar? | Untuk 9 titik, 9 dari 9 masih wajar (interval 95% berarti ±1 dari 20 boleh di luar). Lebar interval relatif 30–38% dari ramalan, jadi ramalan tetap perlu diperbarui setiap bulan. |
| Apakah angka ±364 ton untuk satu usaha? | Tidak. Itu kapasitas wilayah Kabupaten Malang. UMKM memakai indeks. |
| Bagaimana jika data bulan baru salah isi? | Perbaiki langsung di Tbl_Volume_Bulanan; query menghitung ulang setiap kali dibuka. |

Pertanyaan umum lain (data tidak dibagi UMKM, pemilihan SARIMA vs ARIMAX, target RMSE relatif) ada di
[PANDUAN_PRESENTASI_ACCESS.md](PANDUAN_PRESENTASI_ACCESS.md) bagian 4.
