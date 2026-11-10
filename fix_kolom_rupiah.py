"""
Perbaikan sekali jalan: ubah kolom harga dari tipe CURRENCY (tampil '$')
menjadi DOUBLE (angka biasa, satuan Rupiah). Data yang sudah ada tidak hilang.
Tutup MS Access dulu, lalu jalankan:  python fix_kolom_rupiah.py
"""
from koneksi import get_conn

with get_conn() as conn:
    cur = conn.cursor()
    for kolom in ["Harga_Per_Kg", "Total_Harga"]:
        cur.execute(f"ALTER TABLE Transaksi_Penjualan ALTER COLUMN {kolom} DOUBLE")
        print(f"  {kolom}: CURRENCY -> DOUBLE (Rupiah)")
    conn.commit()
print("Selesai. Buka lagi tabel Transaksi_Penjualan di Access, tanda $ sudah hilang.")
