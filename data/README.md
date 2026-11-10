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
└── hasil_08/                    <- output 08_forecasting_data_testing.py
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

## Satuan pada hasil 06–08

Script 06–08 mengestimasi model pada data yang ditransformasi di dalam script
(modul `estimasi_model.py`, konstanta `TRANSFORMASI`; versi final `"log"`:
ln kg dan ln Rp/kg, `Koefisien_Musim` apa adanya). File data tidak diubah.
Koefisien, LogL, AIC, dan BIC berskala data transformasi; kolom `*_setara_kg`
sudah dikoreksi Jacobian ke satuan kg. Prediksi dan metrik di `hasil_07` dan
`hasil_08` dalam kg.

Angka dari versi estimasi sebelumnya (skala kg, enforce=False, ribu kg tanpa
log) dirangkum di `perbandingan_versi_estimasi.md` di folder proyek.
