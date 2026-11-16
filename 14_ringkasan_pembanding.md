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
| 1 | SARIMA airline | 6,20 | 10.865 | 7.724 | 0,964 |
| 2 | SARIMA D=1 | 6,59 | 7.395 | 6.102 | 0,983 |
| 3 | Holt-Winters | 6,67 | 8.426 | 7.231 | 0,978 |
| 4 | Theta | 13,40 | 64.072 | 26.468 | -0,259 |
| 5 | Seasonal naive | 14,73 | 28.534 | 19.597 | 0,750 |

## Akurasi – Multilangkah
| Peringkat_MAPE | Label | MAPE_% | RMSE | MAE | R2 | MAPE_6_Bulan_Pertama_% |
|---|---|---|---|---|---|---|
| 1 | SARIMA D=1 | 6,98 | 7.818 | 6.937 | 0,981 | 7,61 |
| 2 | Holt-Winters | 8,88 | 15.258 | 11.277 | 0,929 | 10,22 |
| 3 | SARIMA airline | 10,37 | 17.578 | 13.090 | 0,905 | 11,96 |
| 4 | Seasonal naive | 14,73 | 28.534 | 19.597 | 0,750 | 16,77 |
| 5 | Theta | 20,61 | 65.878 | 33.678 | -0,331 | 23,14 |

## Uji Diebold-Mariano (galat rolling origin, h = 1, koreksi Harvey dkk., n = 9)
| Model_A | Model_B | Loss | Statistik_DM_HLN | P_value | Kesimpulan_5% |
|---|---|---|---|---|---|
| SARIMA D=1 | Holt-Winters | kuadrat | -0,591 | 0,5706 | Tidak berbeda signifikan |
| SARIMA D=1 | Holt-Winters | absolut | -0,598 | 0,5661 | Tidak berbeda signifikan |
| SARIMA D=1 | SARIMA airline | kuadrat | -0,744 | 0,4783 | Tidak berbeda signifikan |
| SARIMA D=1 | SARIMA airline | absolut | -0,511 | 0,6232 | Tidak berbeda signifikan |
| SARIMA D=1 | Seasonal naive | kuadrat | -1,205 | 0,2627 | Tidak berbeda signifikan |
| SARIMA D=1 | Seasonal naive | absolut | -1,639 | 0,1397 | Tidak berbeda signifikan |
| SARIMA D=1 | Theta | kuadrat | -0,998 | 0,3474 | Tidak berbeda signifikan |
| SARIMA D=1 | Theta | absolut | -0,960 | 0,3653 | Tidak berbeda signifikan |

Catatan: dengan hanya 9 titik uji, daya uji DM rendah; hasil tidak signifikan tidak berarti akurasinya sama.
