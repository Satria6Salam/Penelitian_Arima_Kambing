# Ringkasan Script 15: Simulasi Banyak Seed dan Analisis Sensitivitas

Dibuat otomatis oleh `15_simulasi_sensitivitas.py`. Hasil script 03–14 tidak diubah.

## Desain
- Data dibangkitkan ulang dengan fungsi script 03 (seed 1–100 untuk skenario dasar, 1–50 untuk skenario sensitivitas); latih 27 bulan, uji 9 bulan multilangkah.
- Pemeriksaan: skenario dasar seed 42 mereproduksi volume_bulanan.csv (selisih maks 0.00 kg); MAPE SARIMA seed 42 = 9,07% (sama dengan Tabel 5 naskah).
- Orakel = nilai harapan proses pembangkit (μ × faktor tren × faktor musim): batas bawah galat yang dapat dicapai.

## Hasil per skenario (MAPE multilangkah 9 bulan, median [persentil 5–95])
| Skenario | SARIMA | Holt-Winters | Seasonal naive | Orakel | SARIMA < naive | SARIMA < HW | SARIMA < 15% |
|---|---|---|---|---|---|---|---|
| Dasar (k 10%, noise 5%, S 2,717) | 10,42 [7,23–17,68] | 8,45 [5,22–13,40] | 9,62 [6,47–13,25] | 6,35 [4,29–8,69] | 23% | 15% | 89% |
| k = 5% | 8,37 [5,25–12,54] | 6,41 [4,22–10,11] | 7,13 [5,04–10,15] | 4,55 [3,15–6,23] | 26% | 14% | 96% |
| k = 15% | 12,70 [8,51–18,44] | 11,40 [7,05–16,69] | 11,86 [7,81–16,16] | 8,66 [6,42–11,21] | 26% | 20% | 78% |
| Noise = 3% | 9,19 [6,38–12,94] | 7,80 [4,89–10,58] | 8,21 [5,46–10,99] | 5,61 [4,22–7,20] | 22% | 20% | 96% |
| Noise = 10% | 13,18 [9,38–23,69] | 12,49 [8,13–20,91] | 13,28 [9,05–17,82] | 9,03 [6,24–13,37] | 40% | 32% | 64% |
| S x 0,8 | 10,49 [7,21–16,49] | 8,72 [5,40–13,16] | 9,24 [6,28–12,45] | 6,39 [4,47–8,58] | 24% | 14% | 92% |
| S x 1,2 | 10,49 [7,21–16,49] | 8,72 [5,40–13,16] | 9,24 [6,28–12,45] | 6,39 [4,47–8,58] | 24% | 14% | 92% |

## Catatan skenario S
- Skenario S × 0,8 dan S × 1,2 memberi MAPE yang (hampir) sama. Ini konsekuensi desain data, bukan galat: Iduladha selalu jatuh di bulan yang sama dan semua komponen bersifat perkalian, sehingga pada skala log pengali S hanya menambah konstanta di bulan Iduladha yang dihapus oleh pembedaan musiman; rasio seasonal naive dan orakel juga tidak berubah. Besar lonjakan S baru berpengaruh bila bulan Iduladha bergeser.

## Cara membaca
- Kolom persen = porsi seed tempat SARIMA lebih akurat dari pembanding / memenuhi target MAPE < 15%.
- Bila MAPE SARIMA dekat dengan MAPE orakel, akurasi model terutama dibatasi oleh keacakan buatan pada data; akurasi tersebut menggambarkan kemampuan model menangkap pola pembangkit, bukan akurasi pada data permintaan riil.
