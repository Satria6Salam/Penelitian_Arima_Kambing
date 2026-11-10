-- ==========================================================================
-- Query MS Access tahap Implementasi (dibuat otomatis oleh 11_implementasi_access.py)
-- Query ini SUDAH tersimpan di database. File ini sebagai dokumentasi/cadangan:
-- Access -> Create -> Query Design -> SQL View -> paste SATU query -> Save.
-- ==========================================================================

-- Tabel: Tbl_Volume_Bulanan
CREATE TABLE Tbl_Volume_Bulanan (
            Periode DATETIME CONSTRAINT pk_vol PRIMARY KEY,
            Tahun INTEGER,
            Bulan INTEGER,
            Permintaan_Kg DOUBLE,
            Harga_Rata2_Per_Kg DOUBLE,
            Sumber TEXT(100)
        );

-- Tabel: Tbl_Parameter_SARIMA
CREATE TABLE Tbl_Parameter_SARIMA (
            Nama_Parameter TEXT(30) CONSTRAINT pk_par PRIMARY KEY,
            Nilai DOUBLE,
            Keterangan TEXT(255),
            Nama_Model TEXT(60),
            Tanggal_Training DATETIME,
            Periode_Data TEXT(60)
        );

-- Tabel: Tbl_Faktor_Musiman
CREATE TABLE Tbl_Faktor_Musiman (
            Bulan INTEGER CONSTRAINT pk_fm PRIMARY KEY,
            Nama_Bulan TEXT(20),
            Rata2_Permintaan_Kg DOUBLE,
            Faktor_Musiman DOUBLE,
            Keterangan TEXT(255)
        );

-- Tabel: Tbl_Peramalan
CREATE TABLE Tbl_Peramalan (
            ID_Peramalan COUNTER CONSTRAINT pk_ram PRIMARY KEY,
            Nama_Model TEXT(60),
            Periode DATETIME,
            Horizon INTEGER,
            Prediksi_Kg DOUBLE,
            Batas_Bawah_95_Kg DOUBLE,
            Batas_Atas_95_Kg DOUBLE,
            Sumber TEXT(60),
            Tanggal_Dibuat DATETIME
        );

-- Simpan sebagai: qry_11_Volume_Bulanan
SELECT Periode, Tahun, Bulan, Permintaan_Kg, Harga_Rata2_Per_Kg,
       Log(Permintaan_Kg) AS Ln_Permintaan
FROM Tbl_Volume_Bulanan
ORDER BY Periode;

-- Simpan sebagai: qry_11_Ramalan_1_Bulan_Historis
SELECT
    DateAdd('m', 1, B.Periode) AS Periode_Ramalan,
    B.Periode AS Periode_Asal,
    Exp(Log(L11.Permintaan_Kg)
        + P1.Nilai * (Log(B.Permintaan_Kg) - Log(L12.Permintaan_Kg))
        + P2.Nilai * (Log(L11.Permintaan_Kg) - Log(L23.Permintaan_Kg))
        - P1.Nilai * P2.Nilai * (Log(L12.Permintaan_Kg) - Log(L24.Permintaan_Kg))) AS Prediksi_Kg,
    Exp(Log(L11.Permintaan_Kg)
        + P1.Nilai * (Log(B.Permintaan_Kg) - Log(L12.Permintaan_Kg))
        + P2.Nilai * (Log(L11.Permintaan_Kg) - Log(L23.Permintaan_Kg))
        - P1.Nilai * P2.Nilai * (Log(L12.Permintaan_Kg) - Log(L24.Permintaan_Kg))
        - 1.96 * Sqr(PS.Nilai)) AS Batas_Bawah_95_Kg,
    Exp(Log(L11.Permintaan_Kg)
        + P1.Nilai * (Log(B.Permintaan_Kg) - Log(L12.Permintaan_Kg))
        + P2.Nilai * (Log(L11.Permintaan_Kg) - Log(L23.Permintaan_Kg))
        - P1.Nilai * P2.Nilai * (Log(L12.Permintaan_Kg) - Log(L24.Permintaan_Kg))
        + 1.96 * Sqr(PS.Nilai)) AS Batas_Atas_95_Kg
FROM Tbl_Volume_Bulanan AS B, Tbl_Volume_Bulanan AS L11, Tbl_Volume_Bulanan AS L12,
     Tbl_Volume_Bulanan AS L23, Tbl_Volume_Bulanan AS L24,
     Tbl_Parameter_SARIMA AS P1, Tbl_Parameter_SARIMA AS P2, Tbl_Parameter_SARIMA AS PS
WHERE L11.Periode = DateAdd('m', -11, B.Periode)
  AND L12.Periode = DateAdd('m', -12, B.Periode)
  AND L23.Periode = DateAdd('m', -23, B.Periode)
  AND L24.Periode = DateAdd('m', -24, B.Periode)
  AND P1.Nama_Parameter = 'ar.L1'
  AND P2.Nama_Parameter = 'ar.S.L12'
  AND PS.Nama_Parameter = 'sigma2';

-- Simpan sebagai: qry_11_Ramalan_Bulan_Depan
SELECT R.*
FROM qry_11_Ramalan_1_Bulan_Historis AS R
WHERE R.Periode_Asal = (SELECT MAX(Periode) FROM Tbl_Volume_Bulanan);

-- Simpan sebagai: qry_11_Peramalan_6_Bulan
SELECT Nama_Model, Format(Periode, 'mmmm yyyy') AS Bulan, Horizon,
       Round(Prediksi_Kg, 0) AS Ramalan_Kg,
       Round(Batas_Bawah_95_Kg, 0) AS Batas_Bawah_95,
       Round(Batas_Atas_95_Kg, 0) AS Batas_Atas_95, Sumber, Tanggal_Dibuat
FROM Tbl_Peramalan
WHERE Tanggal_Dibuat = (SELECT MAX(Tanggal_Dibuat) FROM Tbl_Peramalan)
ORDER BY Periode;

-- Simpan sebagai: qry_11_Faktor_Musiman
SELECT Bulan, Nama_Bulan, Round(Rata2_Permintaan_Kg, 0) AS Rata2_Kg,
       Round(Faktor_Musiman, 3) AS Faktor, Keterangan
FROM Tbl_Faktor_Musiman
ORDER BY Bulan;
