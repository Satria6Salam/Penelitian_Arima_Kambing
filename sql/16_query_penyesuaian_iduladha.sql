-- Penyesuaian kalender Iduladha murni MS Access (dibuat oleh 16_penyesuaian_iduladha_access.py).
-- Bergantung pada qry_12_Ramalan_6_Bulan (script 12). Tabel isian:

CREATE TABLE Tbl_16_Tanggal_Iduladha (Tahun INTEGER PRIMARY KEY, Tanggal DATETIME);
CREATE TABLE Tbl_16_Jendela_Iduladha (Hari_Ke INTEGER PRIMARY KEY);
CREATE TABLE Tbl_16_Bulan_Lonjakan_Model (Bulan INTEGER PRIMARY KEY);

-- Simpan sebagai: qry_16_Bobot_Iduladha
SELECT DateSerial(Year(DateAdd('d', J.Hari_Ke, T.Tanggal)), Month(DateAdd('d', J.Hari_Ke, T.Tanggal)), 1) AS Periode, T.Tahun,
       Count(*) / N.Jumlah_Hari AS Bobot
FROM Tbl_16_Tanggal_Iduladha AS T, Tbl_16_Jendela_Iduladha AS J,
     (SELECT Count(*) AS Jumlah_Hari FROM Tbl_16_Jendela_Iduladha) AS N
GROUP BY DateSerial(Year(DateAdd('d', J.Hari_Ke, T.Tanggal)), Month(DateAdd('d', J.Hari_Ke, T.Tanggal)), 1), T.Tahun, N.Jumlah_Hari;

-- Simpan sebagai: qry_16_Ramalan_Dasar
SELECT Year(R.Periode) AS Tahun, R.Periode, R.Ramalan_Kg, R.Batas_Bawah_95_Kg, R.Batas_Atas_95_Kg
FROM qry_12_Ramalan_6_Bulan AS R;

-- Simpan sebagai: qry_16_Bulan_Pertama
SELECT Min(Periode) AS Periode_Pertama FROM qry_16_Ramalan_Dasar;

-- Simpan sebagai: qry_16_Lonjakan_Model
SELECT L.Tahun AS Tahun_L, DateSerial(L.Tahun, B.Bulan, 1) AS Periode_Lonjakan,
       Max(IIf(D.Periode = DateSerial(L.Tahun, B.Bulan, 1), D.Ramalan_Kg, Null)) AS Y_Lonjakan,
       Max(IIf(D.Periode = IIf(DateSerial(L.Tahun, B.Bulan, 1) = F.Periode_Pertama,
                               DateAdd('m', 1, DateSerial(L.Tahun, B.Bulan, 1)),
                               DateAdd('m', -1, DateSerial(L.Tahun, B.Bulan, 1))), D.Ramalan_Kg, Null)) AS Y_Acuan
FROM qry_16_Ramalan_Dasar AS D, Tbl_16_Tanggal_Iduladha AS L, Tbl_16_Bulan_Lonjakan_Model AS B,
     qry_16_Bulan_Pertama AS F
WHERE D.Tahun = L.Tahun
GROUP BY L.Tahun, DateSerial(L.Tahun, B.Bulan, 1);

-- Simpan sebagai: qry_16_Pengali_Iduladha
SELECT D.Periode, D.Ramalan_Kg, D.Batas_Bawah_95_Kg, D.Batas_Atas_95_Kg,
       IIf(L.Y_Lonjakan Is Null Or L.Y_Acuan Is Null, 0, IIf(W.Bobot Is Null, 0, W.Bobot)) AS Bobot_Iduladha,
       IIf(L.Y_Lonjakan Is Null Or L.Y_Acuan Is Null, 1,
           IIf(D.Periode = L.Periode_Lonjakan, L.Y_Acuan / L.Y_Lonjakan, 1)
           * (L.Y_Lonjakan / L.Y_Acuan) ^ IIf(W.Bobot Is Null, 0, W.Bobot)) AS Pengali
FROM (qry_16_Ramalan_Dasar AS D LEFT JOIN qry_16_Lonjakan_Model AS L ON D.Tahun = L.Tahun_L)
     LEFT JOIN qry_16_Bobot_Iduladha AS W ON D.Periode = W.Periode;

-- Simpan sebagai: qry_16_Ramalan_Disesuaikan
SELECT P.Periode, P.Ramalan_Kg AS Ramalan_Model_Kg, P.Bobot_Iduladha,
       P.Ramalan_Kg * P.Pengali AS Ramalan_Disesuaikan_Kg,
       P.Batas_Bawah_95_Kg * P.Pengali AS Batas_Bawah_95_Disesuaikan_Kg,
       P.Batas_Atas_95_Kg * P.Pengali AS Batas_Atas_95_Disesuaikan_Kg
FROM qry_16_Pengali_Iduladha AS P;
