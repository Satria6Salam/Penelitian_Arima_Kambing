"""
=============================================================================
PROGRAM RAMALAN 6 BULAN MURNI QUERY MS ACCESS (TANPA VBA, TANPA PYTHON)
File: 12_ramalan_6_bulan_access.py

Melengkapi implementasi MS Access (script 11) agar produsen cukup memakai
MS Access: ramalan 6 bulan dihitung oleh rangkaian saved query SQL dan
otomatis mengikuti data terakhir di Tbl_Volume_Bulanan.

Persamaan (model final SARIMA(1,0,0)x(1,1,0,12) pada ln kg), L = bulan terakhir:
    w_t       = ln y_t - ln y_(t-12)
    rekursi   : w_hat(h) = phi*w_hat(h-1) + Phi*w_(L+h-12) - phi*Phi*w_(L+h-13)
    bentuk tertutup (h <= 12, hasil penjabaran rekursi di atas):
    ln y_hat(L+h) = ln y_(L+h-12) + phi^h * (w_L - Phi*w_(L-12)) + Phi*w_(L+h-12)
    SE(h)     = Sqr(sigma2 * (1 - phi^(2h)) / (1 - phi^2))
    batas     = Exp(ln y_hat -/+ Z_95 * SE(h))
Bentuk tertutup dipakai karena MS Access menolak 6 query bertingkat
("Query is too complex"); hasilnya identik dengan rekursi.

Query baru (objek lama tidak diubah):
    qry_12_Data_Log        : ln y dan w_t per bulan
    qry_12_Bulan_Terakhir  : bulan data terakhir
    qry_12_Titik_Awal      : w_L dan w_(L-12) dari bulan terakhir
    qry_12_Ramalan_6_Bulan : hasil akhir untuk produsen (satu query)

Pengujian:
- via driver ODBC (ACE) dan via MS Access asli (DAO, PowerShell COM);
- hasil harus sama dengan data/hasil_09/09_peramalan_jan_jun_2026.csv;
- uji dinamis di SALINAN database: tambah 1 bulan data -> ramalan bergeser.
Output: data/hasil_12/, sql/12_query_ramalan_6_bulan.sql
=============================================================================
"""

import shutil
import subprocess
import tempfile
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc

import keterangan_csv as kk  # keterangan kolom pada setiap CSV hasil
from koneksi import DB_PATH, ACCESS_DRIVER

# Tanpa connection pooling agar file salinan uji bisa dihapus setelah dipakai
pyodbc.pooling = False


# =============================================================================
# PENGATURAN PATH
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "sql"
OUT = DATA_DIR / "hasil_12"
OUT.mkdir(parents=True, exist_ok=True)

REF_CSV = DATA_DIR / "hasil_09" / "09_peramalan_jan_jun_2026.csv"
HORIZON = 6


# =============================================================================
# DEFINISI QUERY
# =============================================================================

QUERIES = {
    "qry_12_Data_Log": """
SELECT B.Periode, Log(B.Permintaan_Kg) AS LnY,
       Log(B.Permintaan_Kg) - Log(A.Permintaan_Kg) AS W
FROM Tbl_Volume_Bulanan AS B, Tbl_Volume_Bulanan AS A
WHERE A.Periode = DateAdd('m', -12, B.Periode)""",
    "qry_12_Bulan_Terakhir": """
SELECT MAX(Periode) AS Periode_Akhir FROM Tbl_Volume_Bulanan""",
    "qry_12_Titik_Awal": """
SELECT A.Periode_Akhir, W0.W AS W_L, W12.W AS W_L12
FROM qry_12_Bulan_Terakhir AS A, qry_12_Data_Log AS W0, qry_12_Data_Log AS W12
WHERE W0.Periode = A.Periode_Akhir
  AND W12.Periode = DateAdd('m', -12, A.Periode_Akhir)""",
    "qry_12_Ramalan_6_Bulan": f"""
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
                    AND DateAdd('m', {HORIZON} - 12, T.Periode_Akhir)
  AND P1.Nama_Parameter = 'ar.L1' AND P2.Nama_Parameter = 'ar.S.L12'
  AND S2.Nama_Parameter = 'sigma2' AND Z.Nama_Parameter = 'Z_95'""",
}


# =============================================================================
# FUNGSI BANTUAN
# =============================================================================

def koneksi(db):
    return pyodbc.connect(f"DRIVER={{{ACCESS_DRIVER}}};DBQ={db};")


def objek(cur, tipe):
    return {t.table_name for t in cur.tables(tableType=tipe)}


def pasang_query(db):
    """Membuat (ulang) query qry_12_* di database db."""
    with koneksi(db) as conn:
        cur = conn.cursor()
        ada = objek(cur, "VIEW")
        # Hapus semua query qry_12_* buatan script ini (termasuk versi lama qry_12_Langkah*)
        for q in sorted((q for q in ada if q.startswith("qry_12_")),
                        key=lambda n: (n != "qry_12_Ramalan_6_Bulan", "Langkah" not in n, n)):
            cur.execute(f"DROP TABLE {q}")
        conn.commit()
        for nama, sql in QUERIES.items():
            cur.execute(f"CREATE VIEW {nama} AS {sql.strip()}")
        conn.commit()


def baca_odbc(db, sql):
    with koneksi(db) as conn:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return pd.read_sql(sql, conn)


def baca_dao(db, nama_query):
    """Menjalankan query lewat mesin MS Access asli (DAO.DBEngine.120) via PowerShell."""
    ps = f"""
$e = New-Object -ComObject DAO.DBEngine.120
$d = $e.OpenDatabase('{db}')
$r = $d.OpenRecordset('SELECT * FROM {nama_query} ORDER BY 1')
$hdr = @(); for ($i=0; $i -lt $r.Fields.Count; $i++) {{ $hdr += $r.Fields.Item($i).Name }}
Write-Output ($hdr -join ';')
while (-not $r.EOF) {{
  $v = @(); for ($i=0; $i -lt $r.Fields.Count; $i++) {{
    $x = $r.Fields.Item($i).Value
    if ($x -is [datetime]) {{ $v += $x.ToString('yyyy-MM-dd') }}
    elseif ($x -is [double]) {{ $v += $x.ToString('R', [Globalization.CultureInfo]::InvariantCulture) }}
    else {{ $v += [string]$x }}
  }}
  Write-Output ($v -join ';'); $r.MoveNext()
}}
$r.Close(); $d.Close()
"""
    hasil = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=120)
    if hasil.returncode != 0 or not hasil.stdout.strip():
        raise RuntimeError(f"DAO gagal: {hasil.stderr.strip()[:300]}")
    baris = [b.split(";") for b in hasil.stdout.strip().splitlines()]
    return pd.DataFrame(baris[1:], columns=baris[0])


def ramalan_python(db):
    """Rumus rekursif yang sama, dihitung di Python dari isi database (pembanding)."""
    v = baca_odbc(db, "SELECT Periode, Permintaan_Kg FROM Tbl_Volume_Bulanan ORDER BY Periode")
    p = baca_odbc(db, "SELECT Nama_Parameter, Nilai FROM Tbl_Parameter_SARIMA").set_index("Nama_Parameter")["Nilai"]
    phi, Phi, s2, z = p["ar.L1"], p["ar.S.L12"], p["sigma2"], p["Z_95"]
    ln = list(np.log(v["Permintaan_Kg"].values))
    w = [np.nan] * 12 + [ln[i] - ln[i - 12] for i in range(12, len(ln))]
    akhir = pd.Timestamp(v["Periode"].max())
    out = []
    for h in range(1, HORIZON + 1):
        t = len(ln)
        wh = phi * w[t - 1] + Phi * w[t - 12] - phi * Phi * w[t - 13]
        lh = ln[t - 12] + wh
        se = np.sqrt(s2 * (1 - phi ** (2 * h)) / (1 - phi ** 2))
        out.append({"Periode": (akhir + pd.DateOffset(months=h)).strftime("%Y-%m"),
                    "Ramalan_Kg": np.exp(lh), "Batas_Bawah_95_Kg": np.exp(lh - z * se),
                    "Batas_Atas_95_Kg": np.exp(lh + z * se)})
        ln.append(lh)
        w.append(wh)
    return pd.DataFrame(out)


def normalisasi(df):
    d = df.copy()
    d["Periode"] = pd.to_datetime(d["Periode"]).dt.strftime("%Y-%m")
    for k in ["Ramalan_Kg", "Batas_Bawah_95_Kg", "Batas_Atas_95_Kg"]:
        d[k] = d[k].astype(float)
    return d.sort_values("Periode").reset_index(drop=True)[
        ["Periode", "Ramalan_Kg", "Batas_Bawah_95_Kg", "Batas_Atas_95_Kg"]]


def bandingkan(a, b, label_a, label_b, uji):
    baris = []
    for i in range(len(a)):
        for k in ["Ramalan_Kg", "Batas_Bawah_95_Kg", "Batas_Atas_95_Kg"]:
            x, y = float(a[k].iloc[i]), float(b[k].iloc[i])
            baris.append({"Uji": uji, "Periode": a["Periode"].iloc[i], "Besaran": k,
                          label_a: x, label_b: y, "Selisih_Relatif_%": (x - y) / y * 100})
    return pd.DataFrame(baris)


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    print("=" * 75)
    print("RAMALAN 6 BULAN MURNI QUERY MS ACCESS")
    print("=" * 75)

    if DB_PATH.with_suffix(".laccdb").exists():
        raise RuntimeError("Database sedang dibuka di MS Access. Tutup Access lalu jalankan ulang.")

    # 1. Backup
    hari_ini = sorted(DB_PATH.parent.glob(f"db_penjualan_kambing_backup_{datetime.now():%Y%m%d}_*.accdb"))
    if hari_ini:
        backup = hari_ini[0]
        print(f"Backup database      : {backup.name} (sudah ada hari ini)")
    else:
        backup = DB_PATH.with_name(f"db_penjualan_kambing_backup_{datetime.now():%Y%m%d_%H%M%S}.accdb")
        shutil.copy2(DB_PATH, backup)
        print(f"Backup database      : {backup.name}")

    # 2. Pasang query
    pasang_query(DB_PATH)
    print(f"Query dibuat         : {', '.join(QUERIES)}")

    # 3. Uji di database asli: ODBC dan Access asli (DAO) vs statsmodels
    ref = kk.baca_csv(REF_CSV).rename(columns={"Yhat_Kg": "Ramalan_Kg"})
    ref = normalisasi(ref)
    odbc = normalisasi(baca_odbc(DB_PATH, "SELECT * FROM qry_12_Ramalan_6_Bulan"))
    dao = normalisasi(baca_dao(str(DB_PATH), "qry_12_Ramalan_6_Bulan"))
    ver = pd.concat([
        bandingkan(dao, ref, "Access_DAO", "Python_statsmodels", "MS Access asli (DAO) vs statsmodels"),
        bandingkan(odbc, ref, "Access_ODBC", "Python_statsmodels", "Driver ODBC vs statsmodels"),
    ])

    # Query lama qry_11_* di Access asli
    q11 = {}
    for q in ["qry_11_Ramalan_Bulan_Depan", "qry_11_Peramalan_6_Bulan", "qry_11_Volume_Bulanan",
              "qry_11_Faktor_Musiman", "qry_11_Ramalan_1_Bulan_Historis"]:
        q11[q] = len(baca_dao(str(DB_PATH), q))
    kk.simpan_csv(dao, OUT / "12_hasil_qry_12_Ramalan_6_Bulan_access.csv", index=False)

    # 4. Uji dinamis di SALINAN database
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        salinan = Path(tmp) / "uji_dinamis.accdb"
        shutil.copy2(DB_PATH, salinan)
        dummy_periode = datetime(2026, 1, 1)
        dummy_kg = float(ref["Ramalan_Kg"].iloc[0]) * 1.05   # contoh: aktual Jan 2026 = ramalan + 5%
        with koneksi(salinan) as conn:
            conn.cursor().execute(
                "INSERT INTO Tbl_Volume_Bulanan (Periode, Tahun, Bulan, Permintaan_Kg, Sumber) "
                "VALUES (?, 2026, 1, ?, 'UJI DUMMY')", dummy_periode, dummy_kg)
            conn.commit()
        dao_baru = normalisasi(baca_dao(str(salinan), "qry_12_Ramalan_6_Bulan"))
        py_baru = normalisasi(ramalan_python(salinan))
    ver = pd.concat([ver, bandingkan(dao_baru, py_baru, "Access_DAO", "Python_rumus_sama",
                                     "Uji dinamis (+data Jan 2026 dummy) di salinan database")])
    kk.simpan_csv(ver, OUT / "12_verifikasi_ramalan_6_bulan.csv", index=False)
    kk.simpan_csv(dao_baru, OUT / "12_uji_dinamis_ramalan_feb_jul_2026.csv", index=False)

    # 5. Dokumentasi SQL
    teks = ["-- Query ramalan 6 bulan murni MS Access (dibuat oleh 12_ramalan_6_bulan_access.py).",
            "-- Sudah tersimpan di database; file ini sebagai dokumentasi/cadangan.", ""]
    for n, s in QUERIES.items():
        teks += [f"-- Simpan sebagai: {n}", s.strip() + ";", ""]
    (SQL_DIR / "12_query_ramalan_6_bulan.sql").write_text("\n".join(teks), encoding="utf-8")

    # Ringkasan
    print("\nHasil qry_12_Ramalan_6_Bulan di MS Access asli:")
    print(dao.to_string(index=False, float_format=lambda x: f"{x:,.0f}"))
    for uji, isi in ver.groupby("Uji", sort=False):
        print(f"- {uji}: selisih relatif maks {isi['Selisih_Relatif_%'].abs().max():.8f}%")
    print("Query lama di Access asli:", {k: f"{v} baris" for k, v in q11.items()})
    print(f"Uji dinamis: data Jan 2026 dummy {dummy_kg:,.0f} kg -> ramalan "
          f"{dao_baru['Periode'].iloc[0]} s.d. {dao_baru['Periode'].iloc[-1]}")
    print(dao_baru.to_string(index=False, float_format=lambda x: f"{x:,.0f}"))
    print("=" * 75)
    print("TAHAP 12 SELESAI. Ramalan 6 bulan kini dihitung langsung oleh query MS Access.")
    print("=" * 75)


if __name__ == "__main__":
    main()
