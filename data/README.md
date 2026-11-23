# Struktur Folder `data`

Folder ini disusun mengikuti urutan alur script. Setiap script membaca dari
folder tahap sebelumnya dan menulis ke foldernya sendiri. Folder output
dibuat otomatis oleh script (`mkdir(parents=True, exist_ok=True)`).

```
data/
├── db_penjualan_kambing.accdb   <- database MS Access (02_buat_database.py, koneksi.py)
├── sumber_bps/                  <- input asli dari BPS (dibaca 03)
├── hasil_generate/              <- output 03_generate_data.py
├── olah/                        <- output 04_pra_proses_data.py
├── eksplorasi/                  <- output 05_eksplorasi_data.py
├── hasil_06/                    <- output 06_pemodelan_forecasting.py
├── hasil_07/                    <- output 07_validasi_diagnostik_evaluasi.py
├── hasil_08/                    <- output 08_forecasting_data_testing.py
├── hasil_09/                    <- output 09_peramalan_visualisasi.py
├── laporan/                     <- output 10_ekspor_output_laporan.py
├── hasil_11/                    <- output 11_implementasi_access.py & 11_rekomendasi_manajerial.py
├── hasil_12/                    <- output 12_ramalan_6_bulan_access.py
├── hasil_13/                    <- output 13_penyesuaian_iduladha.py
├── hasil_14/                    <- output 14_pembanding_tambahan.py
├── hasil_15/                    <- output 15_simulasi_sensitivitas.py
├── hasil_16/                    <- output 16_penyesuaian_iduladha_access.py
└── hasil_17/                    <- output 17_validasi_data_latih.py
```

| Folder | File | Dibuat oleh | Dibaca oleh |
|---|---|---|---|
| `sumber_bps/` | `bps_produksi_kambing_2023.csv`, `_2024.csv`, `_2025.csv` | data BPS (manual) | 03 |
| `hasil_generate/` | `transaksi_penjualan.csv` | 03 | 04 |
| | `volume_bulanan.csv` (termasuk `Koefisien_Musim` = label Iduladha) | 03 | 06 |
| | `dataset_sarimax.csv` | 03 | 03 (validasi) |
| | `baseline_bps.csv` | 03 | - |
| `olah/` | `dataset_pra_proses_final.csv` | 04 | 05, 06 |
| `eksplorasi/` | `model_config.json` | 05 | 06 |
| | `tabel_dekomposisi_hasil.csv`, `time_series_plot.png`, `time_series_decomposition.png`, `acf_pacf_plot.png` | 05 | - |
| `hasil_06/` | `06_training_set.csv`, `06_testing_set.csv` (satuan asli kg dan Rp) | 06 | 07, 08 |
| | `06_hasil_estimasi.csv`, `06_perbandingan_aic_bic.csv`, `06_cek_model_bersarang.csv` | 06 | 07 |
| `hasil_07/` | `07_shortlist.csv`, `07_diagnostik_residual.csv`, `07_metrik_rolling_origin.csv`, `07_rolling_origin_prediksi.csv` | 07 | 08 |
| | `07_parameter_estimasi.csv`, `07_cek_optimum_lokal.csv`, `07_summary_shortlist.txt`, `grafik/` | 07 | - |
| `hasil_08/` | `08_cek_data_testing.csv`, `08_model_peramalan.csv`, `08_peramalan_testing.csv`, `08_evaluasi_peramalan.csv`, `08_multistep_vs_rolling.csv`, `grafik/` | 08 | - |
| `hasil_09/` | `09_parameter_model_final.csv`, `09_diagnostik_model_final.csv`, `09_peramalan_jan_jun_2026.csv`, `validasi_apr_sep_2025/`, `grafik/` | 09 | 11, 12, 13 |
| `laporan/` | plot & CSV pelengkap laporan (ADF, differencing, ACF/PACF, AIC/BIC, residual) | 10 | - |
| `hasil_11/` | `11_objek_access.csv`, `11_verifikasi_access_vs_python.csv`, `access_output/` (ekspor isi tabel & query Access) | 11_implementasi_access | - |
| | `11_rek_*.csv` (stok data uji, stok per bulan, kapasitas puncak, indeks kebutuhan, panduan UMKM, harga historis) | 11_rekomendasi_manajerial (setelah 13) | - |
| `hasil_12/` | `12_hasil_qry_12_Ramalan_6_Bulan_access.csv`, `12_verifikasi_ramalan_6_bulan.csv`, `12_uji_dinamis_ramalan_feb_jul_2026.csv` | 12 | - |
| `hasil_13/` | `13_bobot_jendela_iduladha.csv`, `13_peramalan_disesuaikan_iduladha.csv`, `grafik/` | 13 | 11_rekomendasi, 16 |
| `hasil_14/` | `14_metrik_pembanding.csv`, `14_prediksi_pembanding_baru.csv`, `14_uji_diebold_mariano.csv` | 14 | - |
| `hasil_15/` | `15_hasil_per_seed.csv`, `15_ringkasan_skenario.csv`, `grafik/15_boxplot_mape_simulasi.png` | 15 | - |
| `hasil_16/` | `16_hasil_qry_16_Ramalan_Disesuaikan_access.csv`, `16_verifikasi_penyesuaian_iduladha.csv`, `16_uji_dinamis_feb_jul_2026.csv` | 16 | - |
| `hasil_17/` | `17_validasi_prediksi.csv`, `17_validasi_metrik.csv` (validasi di dalam data latih; pemilihan model tanpa data uji) | 17 | - |

## Satuan pada hasil 06–08

Script 06–08 mengestimasi model pada data yang ditransformasi di dalam script
(modul `estimasi_model.py`, konstanta `TRANSFORMASI`; versi final `"log"`:
ln kg dan ln Rp/kg, `Koefisien_Musim` apa adanya). File data tidak diubah.
Koefisien, LogL, AIC, dan BIC berskala data transformasi; kolom `*_setara_kg`
sudah dikoreksi Jacobian ke satuan kg. Prediksi dan metrik di `hasil_07` dan
`hasil_08` dalam kg.

Angka dari versi estimasi sebelumnya (skala kg, enforce=False, ribu kg tanpa
log) dirangkum di `perbandingan_versi_estimasi.md` di folder proyek.
