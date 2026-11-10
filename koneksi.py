"""
Helper koneksi Python <-> MS Access untuk penelitian ARIMA daging kambing.

Pakai di script / notebook lain:
    from koneksi import get_conn, baca_sql, DB_PATH
    df = baca_sql("SELECT * FROM Transaksi_Penjualan")
"""
import warnings
from pathlib import Path

import pandas as pd
import pyodbc

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "db_penjualan_kambing.accdb"
OUTPUT_DIR = BASE_DIR / "output"
GRAFIK_DIR = OUTPUT_DIR / "grafik"

ACCESS_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"


def get_conn(db_path: Path = DB_PATH) -> pyodbc.Connection:
    """Buka koneksi ODBC ke file .accdb."""
    if ACCESS_DRIVER not in pyodbc.drivers():
        raise RuntimeError(
            "Driver MS Access tidak ditemukan. Install 'Microsoft Access Database "
            "Engine 2016 Redistributable' yang bit-nya SAMA dengan Python kamu "
            "(lihat README bagian Langkah 3)."
        )
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"Database belum ada: {db_path}\nJalankan dulu: python 02_buat_database.py"
        )
    return pyodbc.connect(f"DRIVER={{{ACCESS_DRIVER}}};DBQ={db_path};")


def baca_sql(query: str, params=None, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Jalankan SELECT di Access dan kembalikan DataFrame."""
    with get_conn(db_path) as conn:
        with warnings.catch_warnings():
            # pandas memberi UserWarning untuk koneksi DBAPI non-SQLAlchemy; aman diabaikan
            warnings.simplefilter("ignore", UserWarning)
            return pd.read_sql(query, conn, params=params)


def _ke_python(v):
    """Ubah tipe numpy/pandas ke tipe Python biasa yang diterima pyodbc."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if hasattr(v, "to_pydatetime"):
        return v.to_pydatetime()
    if hasattr(v, "item"):          # numpy int64 / float64
        return v.item()
    return v


def tulis_df(df: pd.DataFrame, tabel: str, hapus_dulu: bool = False,
             db_path: Path = DB_PATH) -> int:
    """Tulis DataFrame ke tabel Access yang sudah ada (nama kolom harus sama)."""
    kolom = list(df.columns)
    sql = f"INSERT INTO [{tabel}] ({', '.join(f'[{k}]' for k in kolom)}) " \
          f"VALUES ({', '.join('?' for _ in kolom)})"
    baris = [tuple(_ke_python(v) for v in row) for row in df.itertuples(index=False)]
    with get_conn(db_path) as conn:
        cur = conn.cursor()
        if hapus_dulu:
            cur.execute(f"DELETE FROM [{tabel}]")
        cur.executemany(sql, baris)
        conn.commit()
    return len(baris)
