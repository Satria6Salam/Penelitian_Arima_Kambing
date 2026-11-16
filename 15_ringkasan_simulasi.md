# Ringkasan Script 15: Simulasi Banyak Seed dan Analisis Sensitivitas

Dibuat otomatis oleh `15_simulasi_sensitivitas.py`. Hasil script 03–14 tidak diubah.

## Desain
- Data dibangkitkan ulang dengan fungsi script 03 (seed 1–100 untuk skenario dasar, 1–50 untuk skenario sensitivitas); latih 27 bulan, uji 9 bulan multilangkah.
- Pemeriksaan: skenario dasar seed 42 mereproduksi volume_bulanan.csv (selisih maks 0.00 kg); MAPE SARIMA seed 42 = 6,98% (sama dengan Tabel 5 naskah).
- Orakel = nilai harapan proses pembangkit (μ × faktor tren × faktor musim): batas bawah galat yang dapat dicapai.

## Hasil per skenario (MAPE multilangkah 9 bulan, median [persentil 5–95])
| Skenario | SARIMA | Holt-Winters | Seasonal naive | Orakel | SARIMA < naive | SARIMA < HW | SARIMA < 15% |
|---|---|---|---|---|---|---|---|
| Dasar (k 10%, noise 5%, S 2,717) | 10,77 [5,65–26,38] | 12,11 [6,43–26,92] | 17,48 [13,14–22,32] | 6,35 [4,29–8,69] | 81% | 58% | 80% |
| k = 5% | 8,05 [4,41–17,68] | 10,67 [4,53–24,35] | 16,50 [12,48–20,93] | 4,55 [3,15–6,23] | 88% | 68% | 92% |
| k = 15% | 13,90 [6,75–26,77] | 16,31 [10,10–29,28] | 17,26 [12,05–23,05] | 8,66 [6,42–11,21] | 70% | 62% | 60% |
| Noise = 3% | 9,49 [5,58–17,14] | 10,05 [6,12–24,83] | 16,85 [12,87–21,05] | 5,61 [4,22–7,20] | 90% | 56% | 92% |
| Noise = 10% | 15,54 [9,61–31,60] | 18,82 [11,49–36,26] | 18,29 [13,04–24,56] | 9,03 [6,24–13,37] | 64% | 62% | 44% |
| S x 0,8 | 10,32 [5,66–20,03] | 12,22 [7,51–29,39] | 16,88 [12,50–21,76] | 6,39 [4,47–8,58] | 82% | 66% | 84% |
| S x 1,2 | 10,32 [5,66–20,03] | 12,22 [7,51–29,40] | 16,88 [12,50–21,76] | 6,39 [4,47–8,58] | 82% | 66% | 84% |

## Catatan skenario S
- Skenario S × 0,8 dan S × 1,2 memberi MAPE yang (hampir) sama. Ini konsekuensi desain data, bukan galat: Iduladha selalu jatuh di bulan yang sama dan semua komponen bersifat perkalian, sehingga pada skala log pengali S hanya menambah konstanta di bulan Iduladha yang dihapus oleh pembedaan musiman; rasio seasonal naive dan orakel juga tidak berubah. Besar lonjakan S baru berpengaruh bila bulan Iduladha bergeser.

## Cara membaca
- Kolom persen = porsi seed tempat SARIMA lebih akurat dari pembanding / memenuhi target MAPE < 15%.
- Bila MAPE SARIMA dekat dengan MAPE orakel, akurasi model terutama dibatasi oleh keacakan buatan pada data; akurasi tersebut menggambarkan kemampuan model menangkap pola pembangkit, bukan akurasi pada data permintaan riil.
