-- Query ramalan 6 bulan murni MS Access (dibuat oleh 12_ramalan_6_bulan_access.py).
-- Sudah tersimpan di database; file ini sebagai dokumentasi/cadangan.

-- Simpan sebagai: qry_12_Data_Log
SELECT B.Periode, Log(B.Permintaan_Kg) AS LnY,
       Log(B.Permintaan_Kg) - Log(A.Permintaan_Kg) AS W
FROM Tbl_Volume_Bulanan AS B, Tbl_Volume_Bulanan AS A
WHERE A.Periode = DateAdd('m', -12, B.Periode);

-- Simpan sebagai: qry_12_Bulan_Terakhir
SELECT MAX(Periode) AS Periode_Akhir FROM Tbl_Volume_Bulanan;

-- Simpan sebagai: qry_12_Titik_Awal
SELECT A.Periode_Akhir, W0.W AS W_L, W12.W AS W_L12
FROM qry_12_Bulan_Terakhir AS A, qry_12_Data_Log AS W0, qry_12_Data_Log AS W12
WHERE W0.Periode = A.Periode_Akhir
  AND W12.Periode = DateAdd('m', -12, A.Periode_Akhir);

-- Simpan sebagai: qry_12_Ramalan_6_Bulan
SELECT DateDiff('m', T.Periode_Akhir, D.Periode) + 12 AS Bulan_Ke,
       DateAdd('m', 12, D.Periode) AS Periode,
       Exp(D.LnY + P1.Nilai ^ (DateDiff('m', T.Periode_Akhir, D.Periode) + 12)
           * (T.W_L - P2.Nilai * T.W_L12) + P2.Nilai * D.W) AS Ramalan_Kg,
       Exp(D.LnY + P1.Nilai ^ (DateDiff('m', T.Periode_Akhir, D.Periode) + 12)
           * (T.W_L - P2.Nilai * T.W_L12) + P2.Nilai * D.W
           - Z.Nilai * Sqr(S2.Nilai * (1 - P1.Nilai ^ (2 * (DateDiff('m', T.Periode_Akhir, D.Periode) + 12)))
                         / (1 - P1.Nilai ^ 2))) AS Batas_Bawah_95_Kg,
       Exp(D.LnY + P1.Nilai ^ (DateDiff('m', T.Periode_Akhir, D.Periode) + 12)
           * (T.W_L - P2.Nilai * T.W_L12) + P2.Nilai * D.W
           + Z.Nilai * Sqr(S2.Nilai * (1 - P1.Nilai ^ (2 * (DateDiff('m', T.Periode_Akhir, D.Periode) + 12)))
                         / (1 - P1.Nilai ^ 2))) AS Batas_Atas_95_Kg
FROM qry_12_Titik_Awal AS T, qry_12_Data_Log AS D,
     Tbl_Parameter_SARIMA AS P1, Tbl_Parameter_SARIMA AS P2,
     Tbl_Parameter_SARIMA AS S2, Tbl_Parameter_SARIMA AS Z
WHERE D.Periode BETWEEN DateAdd('m', -11, T.Periode_Akhir)
                    AND DateAdd('m', 6 - 12, T.Periode_Akhir)
  AND P1.Nama_Parameter = 'ar.L1' AND P2.Nama_Parameter = 'ar.S.L12'
  AND S2.Nama_Parameter = 'sigma2' AND Z.Nama_Parameter = 'Z_95';
