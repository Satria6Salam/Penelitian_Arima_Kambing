"""
Membuat database MS Access untuk penelitian Judul 11 beserta struktur tabelnya.
Jalankan:  python 02_buat_database.py

Tabel (mengikuti metodologi):
  - Pelanggan            : tipe pelanggan untuk analisis tambahan
  - Transaksi_Penjualan  : tanggal, jenis produk (daging/karkas), kuantitas kg, harga
  - Hasil_Prediksi       : output forecast 6 bulan + CI 95% dari Python (dibaca query Access)
  - Evaluasi_Model       : AIC, BIC, MAPE, RMSE, MAE, MSE, R2, Ljung-Box, Shapiro-Wilk per model

Script ini aman dijalankan berulang: file/tabel yang sudah ada tidak ditimpa.
"""
import msaccessdb

from koneksi import DB_PATH, GRAFIK_DIR, OUTPUT_DIR, get_conn

TABEL = {
    "Pelanggan": """
        CREATE TABLE Pelanggan (
            ID_Pelanggan    TEXT(10) NOT NULL PRIMARY KEY,
            Nama_Pelanggan  TEXT(100),
            Tipe_Pelanggan  TEXT(30),      -- mis. Rumah Tangga, Warung Sate, Restoran, Aqiqah/Katering
            Alamat          TEXT(150)
        )""",
    "Transaksi_Penjualan": """
        CREATE TABLE Transaksi_Penjualan (
            ID_Transaksi       TEXT(15) NOT NULL PRIMARY KEY,
            Tanggal_Transaksi  DATETIME NOT NULL,
            ID_Pelanggan       TEXT(10),
            Jenis_Produk       TEXT(20) NOT NULL,   -- 'Daging' atau 'Karkas' (bukan kambing hidup)
            Kuantitas_Kg       DOUBLE NOT NULL,
            Harga_Per_Kg       CURRENCY NOT NULL,
            Total_Harga        CURRENCY,
            CONSTRAINT fk_trx_pelanggan FOREIGN KEY (ID_Pelanggan)
                REFERENCES Pelanggan (ID_Pelanggan)
        )""",
    "Hasil_Prediksi": """
        CREATE TABLE Hasil_Prediksi (
            ID_Prediksi     COUNTER PRIMARY KEY,
            Nama_Model      TEXT(50) NOT NULL,     -- mis. 'SARIMA(1,1,1)(0,1,1,12)'
            Periode         DATETIME NOT NULL,     -- tanggal 1 tiap bulan yang diprediksi
            Prediksi_Kg     DOUBLE,
            Batas_Bawah_Kg  DOUBLE,                -- CI 95%
            Batas_Atas_Kg   DOUBLE,
            Tanggal_Dibuat  DATETIME
        )""",
    "Evaluasi_Model": """
        CREATE TABLE Evaluasi_Model (
            ID_Evaluasi     COUNTER PRIMARY KEY,
            Skenario        TEXT(30),              -- Model 1 ARIMA / Model 2 SARIMA / Model 3 ARIMAX + Harga / Model 4 ARIMAX + Harga + Iduladha
            Nama_Model      TEXT(50),
            AIC             DOUBLE,
            BIC             DOUBLE,
            MAPE_Persen     DOUBLE,
            RMSE_Kg         DOUBLE,
            MAE_Kg          DOUBLE,
            MSE             DOUBLE,
            R2              DOUBLE,
            LjungBox_p      DOUBLE,
            ShapiroWilk_p   DOUBLE,
            Tanggal_Dibuat  DATETIME
        )""",
}


def bersihkan_komentar(sql: str) -> str:
    # Access SQL tidak mendukung komentar '--'
    return "\n".join(line.split("--")[0] for line in sql.splitlines())


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRAFIK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        print(f"Database sudah ada: {DB_PATH}")
    else:
        msaccessdb.create(str(DB_PATH))
        print(f"Database dibuat   : {DB_PATH}")

    with get_conn() as conn:
        cur = conn.cursor()
        sudah_ada = {t.table_name for t in cur.tables(tableType="TABLE")}
        for nama, ddl in TABEL.items():   # urutan penting: Pelanggan dulu (FK)
            if nama in sudah_ada:
                print(f"  - {nama:<20} sudah ada, dilewati")
            else:
                cur.execute(bersihkan_komentar(ddl))
                print(f"  + {nama:<20} dibuat")
        conn.commit()

    print("\nSelesai. Buka file .accdb di MS Access untuk melihat tabelnya.")
    print("Query agregasi bulanan & query prediksi ada di: sql/query_access.sql")


if __name__ == "__main__":
    main()
