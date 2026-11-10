# Ringkasan Script 13: Penyesuaian Kalender Iduladha

Dibuat otomatis oleh `13_penyesuaian_iduladha.py`. Model, parameter, dan hasil script 03–12 **tidak diubah**; script ini hanya menyesuaikan ramalan script 09 (*post-processing*).

## Masalah

Pada data 2023–2025 Iduladha selalu jatuh di bulan Juni, sehingga SARIMA musiman (periode tetap 12 bulan) meramal lonjakan di bulan yang sama. Iduladha maju ±11 hari per tahun, sehingga lonjakan nyata bergeser.

## Metode

- Asumsi: lonjakan pada bulan Iduladha historis disebabkan oleh Iduladha, bukan oleh bulan kalendernya (berbasis teori; data 2023–2025 tidak dapat membedakan keduanya).
- Jendela permintaan Iduladha: H−7 sampai H+3 (belanja menjelang hari raya sampai hari penyembelihan dan tasyrik). Bobot bulan = porsi hari jendela di bulan tersebut.
- Pengali efek Iduladha R = Ŷ bulan lonjakan model ÷ Ŷ bulan sebelumnya.
- Ŷ disesuaikan = Ŷ dasar × R^bobot; bulan lonjakan model dilepas efeknya (Ŷ ÷ R).
- Batas interval 95% dikalikan pengali yang sama, sehingga lebar interval pada skala log (ditentukan horizon h) tetap.

## Perhitungan

- Iduladha 2026: **27 Mei 2026**. Lonjakan model di 2026-06, acuan bulan normal 2026-05: R = 177.280 ÷ 65.768 = **2,696**.

| Tahun | Tanggal_Iduladha | Periode | Bobot | Dalam_Horizon |
|---|---|---|---|---|
| 2026 | 2026-05-27 | 2026-05 | 1,00 | Ya |

## Hasil Jan–Jun 2026 (seluruh Kabupaten Malang)

| Periode | Yhat_Kg | Bobot_Iduladha | Yhat_Disesuaikan_Kg | Batas_Bawah_95_Disesuaikan_Kg | Batas_Atas_95_Disesuaikan_Kg |
|---|---|---|---|---|---|
| 2026-01 | 71.327 | 0,00 | 71.327 | 60.653 | 83.880 |
| 2026-02 | 71.335 | 0,00 | 71.335 | 57.069 | 89.168 |
| 2026-03 | 69.364 | 0,00 | 69.364 | 53.157 | 90.514 |
| 2026-04 | 67.206 | 0,00 | 67.206 | 49.817 | 90.665 |
| 2026-05 | 65.768 | 1,00 | 177.280 | 127.920 | 245.686 |
| 2026-06 | 177.280 | 0,00 | 65.768 | 46.408 | 93.203 |

Grafik: `data/hasil_13/grafik/13_ramalan_disesuaikan.png`.

## Indeks untuk UMKM (disesuaikan)

| Periode | Indeks_vs_Bulan_Normal_Disesuaikan | Faktor_Batas_Atas |
|---|---|---|
| 2026-01 | 1,03 | 1,18 |
| 2026-02 | 1,03 | 1,25 |
| 2026-03 | 1,01 | 1,30 |
| 2026-04 | 0,97 | 1,35 |
| 2026-05 | 2,57 | 1,39 |
| 2026-06 | 0,95 | 1,42 |

Rata-rata bulan normal (disesuaikan): 69.000 kg.

## Implikasi

- Puncak permintaan 2026 berada di **2026-05**: Ŷ 177.280 kg, batas atas 95% 245.686 kg (acuan kapasitas wilayah).
- Bulan yang semula diramal sebagai puncak kembali ke level bulan normal.
- Gunakan tabel ini untuk perencanaan; ramalan asli script 09 tetap dilaporkan sebagai hasil model.

## Keterbatasan

- Penyesuaian ini bukan bagian dari estimasi model statistik; besar lonjakan R diambil dari ramalan model dan diasumsikan sama walaupun bulannya bergeser.
- Tanggal Iduladha adalah perkiraan; perbarui `TANGGAL_IDULADHA` sesuai ketetapan resmi.
- Data historis sintetis menempatkan seluruh efek Iduladha di bulan Juni, sehingga penyesuaian tidak dapat divalidasi dengan data 2023–2025.
