-- ============================================================================
-- Query MS Access - Penelitian Judul 11 (ARIMA Daging Kambing)
-- Cara pakai: di Access -> Create -> Query Design -> (tutup Show Table)
--             -> klik "SQL View" -> paste SATU query -> Save dengan nama di judulnya.
-- Catatan: Access hanya menerima satu statement per query & tidak mengenal komentar "--".
-- ============================================================================


-- [1] Simpan sebagai: qry_Permintaan_Bulanan
--     Agregasi bulanan (GROUP BY MONTH) -> sumber data time series untuk Python
--     (semua jenis produk: Daging Murni, Karkas, Jeroan, Daging Variasi)
SELECT
    DateSerial(Year(Tanggal_Transaksi), Month(Tanggal_Transaksi), 1) AS Periode,
    SUM(Kuantitas_Kg)                      AS Permintaan_Kg,
    ROUND(SUM(Total_Harga) / SUM(Kuantitas_Kg), 0) AS Harga_Rata2_Per_Kg,
    COUNT(ID_Transaksi)                    AS Jumlah_Pesanan
FROM Transaksi_Penjualan
GROUP BY DateSerial(Year(Tanggal_Transaksi), Month(Tanggal_Transaksi), 1)
ORDER BY DateSerial(Year(Tanggal_Transaksi), Month(Tanggal_Transaksi), 1);


-- [2] Simpan sebagai: qry_Permintaan_Per_Tipe_Pelanggan
--     Analisis tambahan berdasarkan tipe pelanggan
SELECT
    DateSerial(Year(T.Tanggal_Transaksi), Month(T.Tanggal_Transaksi), 1) AS Periode,
    P.Tipe_Pelanggan,
    SUM(T.Kuantitas_Kg) AS Permintaan_Kg
FROM Transaksi_Penjualan AS T
INNER JOIN Pelanggan AS P ON T.ID_Pelanggan = P.ID_Pelanggan
GROUP BY DateSerial(Year(T.Tanggal_Transaksi), Month(T.Tanggal_Transaksi), 1), P.Tipe_Pelanggan;


-- [3] Simpan sebagai: qry_Prediksi_6_Bulan
--     Implementasi output: menampilkan forecast terbaru dari model terbaik
--     (Hasil_Prediksi diisi oleh Python setelah modeling)
SELECT
    H.Nama_Model,
    Format(H.Periode, "mmmm yyyy") AS Bulan,
    ROUND(H.Prediksi_Kg, 1)        AS Prediksi_Kg,
    ROUND(H.Batas_Bawah_Kg, 1)     AS Batas_Bawah_CI95,
    ROUND(H.Batas_Atas_Kg, 1)      AS Batas_Atas_CI95
FROM Hasil_Prediksi AS H
WHERE H.Tanggal_Dibuat = (SELECT MAX(Tanggal_Dibuat) FROM Hasil_Prediksi)
ORDER BY H.Periode;


-- [4] Simpan sebagai: qry_Perbandingan_Model
--     Tabel perbandingan 4 skenario model, diurutkan AIC terendah
SELECT Skenario, Nama_Model, AIC, BIC, MAPE_Persen, RMSE_Kg, MAE_Kg, R2, LjungBox_p, ShapiroWilk_p
FROM Evaluasi_Model
ORDER BY AIC;
