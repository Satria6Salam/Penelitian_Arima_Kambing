# Ringkasan Script 14: Pembanding Tambahan dan Uji Diebold-Mariano

Dibuat otomatis oleh `14_pembanding_tambahan.py`. Model final dan hasil script 06–13 tidak diubah.

## Desain
- Pembanding baru: **Holt-Winters** – ExponentialSmoothing(log y): tren aditif teredam + musiman aditif, m = 12; **Theta** – ThetaModel(log y): deseasonalize aditif, m = 12; **SARIMA airline** – SARIMA(0, 1, 1)x(0, 1, 1, 12) pada log y.
- Spesifikasi pembanding ditetapkan sebelum melihat data uji (tidak dipilih dari hasil uji).
- Skema sama dengan script 07 (rolling origin 1 bulan, 9 putaran) dan script 08 (multilangkah 9 bulan).
- Prediksi SARIMA D=1 dan Seasonal naive dibaca dari output 07/08 (tidak dihitung ulang).
- Pemeriksaan konsistensi: fungsi SARIMA bersama mereproduksi output 08 dengan selisih maks 0.000000%.

## Akurasi – Rolling origin
| Peringkat_MAPE | Label | MAPE_% | RMSE | MAE | R2 |
|---|---|---|---|---|---|
| 1 | SARIMA D=1 | 7,51 | 16.963 | 12.132 | 0,948 |
| 2 | Holt-Winters | 7,67 | 15.445 | 11.317 | 0,957 |
| 3 | SARIMA airline | 7,73 | 14.793 | 10.924 | 0,961 |
| 4 | Seasonal naive | 8,81 | 26.773 | 15.862 | 0,871 |
| 5 | Theta | 9,07 | 25.013 | 15.551 | 0,888 |

## Akurasi – Multilangkah
| Peringkat_MAPE | Label | MAPE_% | RMSE | MAE | R2 | MAPE_6_Bulan_Pertama_% |
|---|---|---|---|---|---|---|
| 1 | Holt-Winters | 7,43 | 14.758 | 11.111 | 0,961 | 5,75 |
| 2 | SARIMA airline | 7,66 | 14.517 | 10.720 | 0,962 | 4,04 |
| 3 | Theta | 8,23 | 26.502 | 15.348 | 0,874 | 8,70 |
| 4 | Seasonal naive | 8,81 | 26.773 | 15.862 | 0,871 | 7,83 |
| 5 | SARIMA D=1 | 9,07 | 18.484 | 14.171 | 0,939 | 10,46 |

## Uji Diebold-Mariano (galat rolling origin, h = 1, koreksi Harvey dkk., n = 9)
| Model_A | Model_B | Loss | Statistik_DM_HLN | P_value | Kesimpulan_5% |
|---|---|---|---|---|---|
| SARIMA D=1 | Holt-Winters | kuadrat | 0,444 | 0,6685 | Tidak berbeda signifikan |
| SARIMA D=1 | Holt-Winters | absolut | 0,320 | 0,7570 | Tidak berbeda signifikan |
| SARIMA D=1 | SARIMA airline | kuadrat | 0,444 | 0,6686 | Tidak berbeda signifikan |
| SARIMA D=1 | SARIMA airline | absolut | 0,370 | 0,7211 | Tidak berbeda signifikan |
| SARIMA D=1 | Seasonal naive | kuadrat | -1,096 | 0,3048 | Tidak berbeda signifikan |
| SARIMA D=1 | Seasonal naive | absolut | -0,995 | 0,3487 | Tidak berbeda signifikan |
| SARIMA D=1 | Theta | kuadrat | -1,184 | 0,2703 | Tidak berbeda signifikan |
| SARIMA D=1 | Theta | absolut | -0,996 | 0,3484 | Tidak berbeda signifikan |

Catatan: dengan hanya 9 titik uji, daya uji DM rendah; hasil tidak signifikan tidak berarti akurasinya sama.
