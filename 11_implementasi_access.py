"""
=============================================================================
PROGRAM IMPLEMENTASI SISTEM KE MS ACCESS (DEPLOYMENT)
File: 11_implementasi_access.py

Mengikuti tahap "IMPLEMENTASI SISTEM & ANALISIS DAMPAK BISNIS":
mengonversi parameter model final menjadi tabel dan query di database
MS Access peternakan (strategi Parameter-Driven Query).

Model final: SARIMA(1,0,0)x(1,1,0,12) pada ln(permintaan kg), parameter dari
fit 36 bulan (data/hasil_09/09_parameter_model_final.csv).

Persamaan yang dipakai di Access (bukan sekadar penjualan x faktor musiman):
    w_t      = ln y_t - ln y_(t-12)                     (differencing musiman log)
    w_hat_t  = phi*w_(t-1) + Phi*w_(t-12) - phi*Phi*w_(t-13)
    ln y_hat = ln y_(t-12) + w_hat_t ;  y_hat = exp(ln y_hat)
Interval 95% horizon h (h <= 12): ln y_hat ± 1,96 x sqrt(sigma2 x sum_{j<h} phi^(2j))
Untuk multi-step, nilai w masa depan diganti ramalannya secara rekursif.

Objek BARU yang dibuat (objek lama tidak diubah/dihapus):
- Tbl_Volume_Bulanan     : volume bulanan 36 bulan (data yang dipakai model)
- Tbl_Parameter_SARIMA   : parameter terkunci hasil pelatihan Python
- Tbl_Faktor_Musiman     : faktor musiman per bulan (informasi pendukung)
- Tbl_Peramalan          : ramalan 6 bulan + interval 95%
- qry_11_Volume_Bulanan, qry_11_Ramalan_1_Bulan_Historis,
  qry_11_Ramalan_Bulan_Depan, qry_11_Peramalan_6_Bulan, qry_11_Faktor_Musiman
Modul VBA untuk ramalan rekursif: sql/11_modul_peramalan.bas (impor manual).

Output: backup database, sql/11_*.sql, data/hasil_11/*.csv
=============================================================================
"""

import shutil
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import estimasi_model as em
from koneksi import get_conn, DB_PATH


# =============================================================================
# PENGATURAN PATH DAN KONSTANTA
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "sql"
OUTPUT_DIR = DATA_DIR / "hasil_11"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATASET_CSV = DATA_DIR / "olah" / "dataset_pra_proses_final.csv"
PARAM_CSV = DATA_DIR / "hasil_09" / "09_parameter_model_final.csv"
PERAMALAN_09_CSV = DATA_DIR / "hasil_09" / "09_peramalan_jan_jun_2026.csv"
VERIFIKASI_CSV = OUTPUT_DIR / "11_verifikasi_access_vs_python.csv"
OBJEK_CSV = OUTPUT_DIR / "11_objek_access.csv"

NAMA_MODEL = "SARIMA(1,0,0)x(1,1,0,12) log"
HORIZON = 6
Z = 1.959963984540054
M = 12

TABEL_BARU = ["Tbl_Volume_Bulanan", "Tbl_Parameter_SARIMA", "Tbl_Faktor_Musiman", "Tbl_Peramalan"]


# =============================================================================
# DEFINISI TABEL DAN QUERY (SQL ACCESS)
# =============================================================================

DDL = {
    "Tbl_Volume_Bulanan": """
        CREATE TABLE Tbl_Volume_Bulanan (
            Periode DATETIME CONSTRAINT pk_vol PRIMARY KEY,
            Tahun INTEGER,
            Bulan INTEGER,
            Permintaan_Kg DOUBLE,
            Harga_Rata2_Per_Kg DOUBLE,
            Sumber TEXT(100)
        )""",
    "Tbl_Parameter_SARIMA": """
        CREATE TABLE Tbl_Parameter_SARIMA (
            Nama_Parameter TEXT(30) CONSTRAINT pk_par PRIMARY KEY,
            Nilai DOUBLE,
            Keterangan TEXT(255),
            Nama_Model TEXT(60),
            Tanggal_Training DATETIME,
            Periode_Data TEXT(60)
        )""",
    "Tbl_Faktor_Musiman": """
        CREATE TABLE Tbl_Faktor_Musiman (
            Bulan INTEGER CONSTRAINT pk_fm PRIMARY KEY,
            Nama_Bulan TEXT(20),
            Rata2_Permintaan_Kg DOUBLE,
            Faktor_Musiman DOUBLE,
            Keterangan TEXT(255)
        )""",
    "Tbl_Peramalan": """
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
        )""",
}

# Ramalan 1 bulan ke depan dari setiap bulan asal B (target T = B + 1 bulan).
# Baris yang dibutuhkan: B, B-11, B-12, B-23, B-24.
SQL_RAMALAN_HISTORIS = """
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
  AND PS.Nama_Parameter = 'sigma2'
"""

QUERIES = {
    "qry_11_Volume_Bulanan": """
SELECT Periode, Tahun, Bulan, Permintaan_Kg, Harga_Rata2_Per_Kg,
       Log(Permintaan_Kg) AS Ln_Permintaan
FROM Tbl_Volume_Bulanan
ORDER BY Periode""",
    "qry_11_Ramalan_1_Bulan_Historis": SQL_RAMALAN_HISTORIS,
    "qry_11_Ramalan_Bulan_Depan": """
SELECT R.*
FROM qry_11_Ramalan_1_Bulan_Historis AS R
WHERE R.Periode_Asal = (SELECT MAX(Periode) FROM Tbl_Volume_Bulanan)""",
    "qry_11_Peramalan_6_Bulan": """
SELECT Nama_Model, Format(Periode, 'mmmm yyyy') AS Bulan, Horizon,
       Round(Prediksi_Kg, 0) AS Ramalan_Kg,
       Round(Batas_Bawah_95_Kg, 0) AS Batas_Bawah_95,
       Round(Batas_Atas_95_Kg, 0) AS Batas_Atas_95, Sumber, Tanggal_Dibuat
FROM Tbl_Peramalan
WHERE Tanggal_Dibuat = (SELECT MAX(Tanggal_Dibuat) FROM Tbl_Peramalan)
ORDER BY Periode""",
    "qry_11_Faktor_Musiman": """
SELECT Bulan, Nama_Bulan, Round(Rata2_Permintaan_Kg, 0) AS Rata2_Kg,
       Round(Faktor_Musiman, 3) AS Faktor, Keterangan
FROM Tbl_Faktor_Musiman
ORDER BY Bulan""",
}

NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]


# =============================================================================
# FUNGSI BANTUAN
# =============================================================================

def objek_ada(cur, nama):
    tabel = {t.table_name for t in cur.tables(tableType="TABLE")}
    view = {t.table_name for t in cur.tables(tableType="VIEW")}
    return nama in tabel, nama in view


def muat_data():
    df = pd.read_csv(DATASET_CSV, parse_dates=["Periode"]).set_index("Periode").asfreq("MS")
    par = pd.read_csv(PARAM_CSV).set_index("Parameter")["Koefisien"]
    return df, par


def ramalan_rekursif(y, phi, Phi, sigma2, horizon=HORIZON):
    """Ramalan multi-step rekursif (persamaan yang sama dengan modul VBA)."""
    ln = list(np.log(y.values))
    w = [np.nan] * M + [ln[i] - ln[i - M] for i in range(M, len(ln))]
    hasil = []
    for h in range(1, horizon + 1):
        t = len(ln)
        w_hat = phi * w[t - 1] + Phi * w[t - 12] - phi * Phi * w[t - 13]
        ln_hat = ln[t - M] + w_hat
        se = np.sqrt(sigma2 * sum(phi ** (2 * j) for j in range(h)))
        hasil.append({
            "Horizon": h,
            "Ln_Prediksi": ln_hat,
            "SE_Log": se,
            "Prediksi_Kg": float(np.exp(ln_hat)),
            "Batas_Bawah_95_Kg": float(np.exp(ln_hat - Z * se)),
            "Batas_Atas_95_Kg": float(np.exp(ln_hat + Z * se)),
        })
        ln.append(ln_hat)
        w.append(w_hat)
    return pd.DataFrame(hasil)


# =============================================================================
# TAHAP 1: BACKUP DAN INVENTARIS DATABASE
# =============================================================================

def backup_dan_inventaris():
    print("\n" + "=" * 75)
    print("TAHAP 1: BACKUP DAN INVENTARIS DATABASE ACCESS")
    print("=" * 75)
    # Backup hanya dibuat sekali (kondisi database sebelum implementasi pertama kali)
    lama = sorted(DB_PATH.parent.glob("db_penjualan_kambing_backup_*.accdb"))
    if lama:
        backup = lama[0]
        print(f"Backup database sudah ada: {backup.name}")
    else:
        tanggal = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = DB_PATH.with_name(f"db_penjualan_kambing_backup_{tanggal}.accdb")
        shutil.copy2(DB_PATH, backup)
        print(f"Backup database: {backup.name}")

    with get_conn() as conn:
        cur = conn.cursor()
        tabel = sorted(t.table_name for t in cur.tables(tableType="TABLE"))
        view = sorted(t.table_name for t in cur.tables(tableType="VIEW"))
        n_trx, kg_trx = cur.execute(
            "SELECT COUNT(*), SUM(Kuantitas_Kg) FROM Transaksi_Penjualan").fetchone()
    print(f"Tabel yang ada : {', '.join(tabel)}")
    print(f"Query yang ada : {', '.join(view)}")
    print(f"Transaksi_Penjualan: {n_trx} baris, {kg_trx:,.0f} kg (data lama, tidak diubah)")
    return backup, n_trx, kg_trx


# =============================================================================
# TAHAP 2: MEMBUAT DAN MENGISI TABEL BARU
# =============================================================================

def buat_tabel(df, par):
    print("\n" + "=" * 75)
    print("TAHAP 2: MEMBUAT DAN MENGISI TABEL BARU")
    print("=" * 75)

    with get_conn() as conn:
        cur = conn.cursor()
        # Hapus objek buatan script ini (jika script dijalankan ulang), urutan query dulu
        for q in reversed(list(QUERIES)):
            if objek_ada(cur, q)[1]:
                cur.execute(f"DROP TABLE {q}")  # Access ODBC: query dihapus dengan DROP TABLE
        for t in TABEL_BARU:
            if objek_ada(cur, t)[0]:
                cur.execute(f"DROP TABLE [{t}]")
        conn.commit()

        for t in TABEL_BARU:
            cur.execute(DDL[t])
        conn.commit()

        for periode, r in df.iterrows():
            cur.execute(
                "INSERT INTO Tbl_Volume_Bulanan (Periode, Tahun, Bulan, Permintaan_Kg, "
                "Harga_Rata2_Per_Kg, Sumber) VALUES (?, ?, ?, ?, ?, ?)",
                periode.to_pydatetime(), periode.year, periode.month,
                float(r[em.TARGET_COL]), float(r[em.PRICE_COL]),
                "dataset_pra_proses_final.csv")

        tanggal_training = datetime.now().replace(microsecond=0)
        periode_data = f"{df.index[0]:%b %Y} - {df.index[-1]:%b %Y} ({len(df)} bulan)"
        parameter = [
            ("ar.L1", float(par["ar.L1"]), "phi: koefisien AR non-musiman pada w_t = ln y_t - ln y_(t-12)"),
            ("ar.S.L12", float(par["ar.S.L12"]), "Phi: koefisien AR musiman lag 12 pada w_t"),
            ("sigma2", float(par["sigma2"]), "Varians residual (skala log); SE 1 langkah = Sqr(sigma2)"),
            ("m", 12.0, "Periode musiman (bulan)"),
            ("Z_95", Z, "Nilai Z untuk interval kepercayaan 95%"),
        ]
        for nama, nilai, ket in parameter:
            cur.execute(
                "INSERT INTO Tbl_Parameter_SARIMA (Nama_Parameter, Nilai, Keterangan, Nama_Model, "
                "Tanggal_Training, Periode_Data) VALUES (?, ?, ?, ?, ?, ?)",
                nama, nilai, ket, NAMA_MODEL, tanggal_training, periode_data)

        rata_total = df[em.TARGET_COL].mean()
        fm = df.groupby(df.index.month)[em.TARGET_COL].mean()
        for bulan, nilai in fm.items():
            cur.execute(
                "INSERT INTO Tbl_Faktor_Musiman (Bulan, Nama_Bulan, Rata2_Permintaan_Kg, "
                "Faktor_Musiman, Keterangan) VALUES (?, ?, ?, ?, ?)",
                int(bulan), NAMA_BULAN[bulan - 1], float(nilai), float(nilai / rata_total),
                "Rata-rata bulan ini / rata-rata seluruh bulan (2023-2025). Informasi "
                "pendukung, bukan inti model SARIMA.")
        conn.commit()

    print(f"Tbl_Volume_Bulanan  : {len(df)} baris")
    print(f"Tbl_Parameter_SARIMA: phi {par['ar.L1']:.6f}, Phi {par['ar.S.L12']:.6f}, "
          f"sigma2 {par['sigma2']:.6f}")
    print(f"Tbl_Faktor_Musiman  : 12 baris (Juni = {fm[6] / rata_total:.3f})")
    return fm / rata_total


# =============================================================================
# TAHAP 3: MEMBUAT SAVED QUERY
# =============================================================================

def buat_query():
    print("\n" + "=" * 75)
    print("TAHAP 3: MEMBUAT SAVED QUERY DI ACCESS")
    print("=" * 75)
    SQL_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        cur = conn.cursor()
        for nama, sql in QUERIES.items():
            cur.execute(f"CREATE VIEW {nama} AS {sql.strip()}")
            print(f"- {nama}")
        conn.commit()

    teks = ["-- " + "=" * 74,
            "-- Query MS Access tahap Implementasi (dibuat otomatis oleh 11_implementasi_access.py)",
            "-- Query ini SUDAH tersimpan di database. File ini sebagai dokumentasi/cadangan:",
            "-- Access -> Create -> Query Design -> SQL View -> paste SATU query -> Save.",
            "-- " + "=" * 74, ""]
    for nama, sql in DDL.items():
        teks += [f"-- Tabel: {nama}", sql.strip() + ";", ""]
    for nama, sql in QUERIES.items():
        teks += [f"-- Simpan sebagai: {nama}", sql.strip() + ";", ""]
    (SQL_DIR / "11_query_implementasi.sql").write_text("\n".join(teks), encoding="utf-8")
    print(f"SQL disimpan ke: sql\\11_query_implementasi.sql")


# =============================================================================
# TAHAP 4: ISI TBL_PERAMALAN DAN TULIS MODUL VBA
# =============================================================================

def isi_peramalan(df, par):
    print("\n" + "=" * 75)
    print("TAHAP 4: MENGISI Tbl_Peramalan (RAMALAN REKURSIF 6 BULAN)")
    print("=" * 75)
    hasil = ramalan_rekursif(df[em.TARGET_COL], par["ar.L1"], par["ar.S.L12"], par["sigma2"])
    periode = pd.date_range(df.index[-1] + pd.offsets.MonthBegin(1), periods=HORIZON, freq="MS")
    hasil.insert(0, "Periode", periode)
    dibuat = datetime.now().replace(microsecond=0)
    with get_conn() as conn:
        cur = conn.cursor()
        for _, r in hasil.iterrows():
            cur.execute(
                "INSERT INTO Tbl_Peramalan (Nama_Model, Periode, Horizon, Prediksi_Kg, "
                "Batas_Bawah_95_Kg, Batas_Atas_95_Kg, Sumber, Tanggal_Dibuat) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                NAMA_MODEL, r["Periode"].to_pydatetime(), int(r["Horizon"]), float(r["Prediksi_Kg"]),
                float(r["Batas_Bawah_95_Kg"]), float(r["Batas_Atas_95_Kg"]),
                "Python (rumus rekursif = modul VBA)", dibuat)
        conn.commit()
    print(hasil[["Periode", "Prediksi_Kg", "Batas_Bawah_95_Kg", "Batas_Atas_95_Kg"]].to_string(
        index=False, float_format=lambda x: f"{x:,.0f}"))
    tulis_vba()
    return hasil


def tulis_vba():
    vba = r'''Attribute VB_Name = "Modul_Peramalan_SARIMA"
' ============================================================================
' Modul VBA peramalan rekursif SARIMA(1,0,0)x(1,1,0,12) pada ln(permintaan)
' Dibuat oleh 11_implementasi_access.py. Cara impor di MS Access:
'   Database Tools -> Visual Basic -> File -> Import File... -> pilih file ini.
' Cara pakai: jalankan IsiPeramalan 6 (Immediate Window: IsiPeramalan 6)
' atau panggil dari tombol/form/makro (RunCode: IsiPeramalan(6)).
' Sumber data: Tbl_Volume_Bulanan, parameter: Tbl_Parameter_SARIMA,
' hasil ditulis ke Tbl_Peramalan (satu batch per Tanggal_Dibuat).
' ============================================================================
Option Compare Database
Option Explicit

Private Function Param(ByVal nama As String) As Double
    Param = DLookup("Nilai", "Tbl_Parameter_SARIMA", "Nama_Parameter='" & nama & "'")
End Function

Public Function IsiPeramalan(Optional ByVal horizon As Integer = 6) As Boolean
    Dim db As DAO.Database, rs As DAO.Recordset, rsOut As DAO.Recordset
    Dim n As Long, i As Long, h As Integer, j As Integer
    Dim lnY() As Double, w() As Double
    Dim phi As Double, Phi12 As Double, sigma2 As Double, z As Double
    Dim wHat As Double, lnHat As Double, se As Double, sumPsi As Double
    Dim periodeAkhir As Date, dibuat As Date

    phi = Param("ar.L1"): Phi12 = Param("ar.S.L12")
    sigma2 = Param("sigma2"): z = Param("Z_95")

    Set db = CurrentDb
    Set rs = db.OpenRecordset("SELECT Periode, Permintaan_Kg FROM Tbl_Volume_Bulanan ORDER BY Periode", dbOpenSnapshot)
    rs.MoveLast: n = rs.RecordCount: rs.MoveFirst
    If n < 26 Then
        MsgBox "Data bulanan minimal 26 bulan.", vbExclamation
        Exit Function
    End If

    ReDim lnY(1 To n + horizon): ReDim w(1 To n + horizon)
    For i = 1 To n
        lnY(i) = Log(rs!Permintaan_Kg)
        periodeAkhir = rs!Periode
        rs.MoveNext
    Next i
    rs.Close
    For i = 13 To n
        w(i) = lnY(i) - lnY(i - 12)
    Next i

    dibuat = Now()
    Set rsOut = db.OpenRecordset("Tbl_Peramalan", dbOpenDynaset)
    For h = 1 To horizon
        i = n + h
        wHat = phi * w(i - 1) + Phi12 * w(i - 12) - phi * Phi12 * w(i - 13)
        lnHat = lnY(i - 12) + wHat
        lnY(i) = lnHat: w(i) = wHat
        sumPsi = 0
        For j = 0 To h - 1
            sumPsi = sumPsi + phi ^ (2 * j)
        Next j
        se = Sqr(sigma2 * sumPsi)
        rsOut.AddNew
        rsOut!Nama_Model = "SARIMA(1,0,0)x(1,1,0,12) log"
        rsOut!Periode = DateAdd("m", h, periodeAkhir)
        rsOut!Horizon = h
        rsOut!Prediksi_Kg = Exp(lnHat)
        rsOut!Batas_Bawah_95_Kg = Exp(lnHat - z * se)
        rsOut!Batas_Atas_95_Kg = Exp(lnHat + z * se)
        rsOut!Sumber = "VBA Modul_Peramalan_SARIMA"
        rsOut!Tanggal_Dibuat = dibuat
        rsOut.Update
    Next h
    rsOut.Close
    IsiPeramalan = True
    MsgBox "Peramalan " & horizon & " bulan tersimpan di Tbl_Peramalan. Buka qry_11_Peramalan_6_Bulan.", vbInformation
End Function
'''
    path = SQL_DIR / "11_modul_peramalan.bas"
    path.write_text(vba, encoding="cp1252")
    print(f"Modul VBA disimpan ke: sql\\{path.name} (impor manual di MS Access)")


# =============================================================================
# TAHAP 5: VERIFIKASI ACCESS VS PYTHON
# =============================================================================

def verifikasi(df, par, hasil):
    print("\n" + "=" * 75)
    print("TAHAP 5: VERIFIKASI HASIL ACCESS VS PYTHON")
    print("=" * 75)
    baris = []

    # (a) Query bulan depan (Access) vs statsmodels Jan 2026
    ref = pd.read_csv(PERAMALAN_09_CSV)
    with get_conn() as conn:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            q1 = pd.read_sql("SELECT * FROM qry_11_Ramalan_Bulan_Depan", conn)
            q6 = pd.read_sql("SELECT * FROM qry_11_Peramalan_6_Bulan", conn)
            qh = pd.read_sql("SELECT * FROM qry_11_Ramalan_1_Bulan_Historis", conn)
    r = ref.iloc[0]
    for kol_a, kol_p in [("Prediksi_Kg", "Yhat_Kg"), ("Batas_Bawah_95_Kg", "Batas_Bawah_95_Kg"),
                         ("Batas_Atas_95_Kg", "Batas_Atas_95_Kg")]:
        baris.append({"Uji": "Query Access qry_11_Ramalan_Bulan_Depan vs statsmodels",
                      "Periode": r["Periode"], "Besaran": kol_a,
                      "Access": float(q1[kol_a].iloc[0]), "Python": float(r[kol_p])})

    # (b) Tbl_Peramalan (lewat query Access) vs statsmodels 6 bulan
    for h in range(HORIZON):
        r = ref.iloc[h]
        for kol_a, kol_p in [("Prediksi_Kg", "Yhat_Kg"), ("Batas_Bawah_95_Kg", "Batas_Bawah_95_Kg"),
                             ("Batas_Atas_95_Kg", "Batas_Atas_95_Kg")]:
            baris.append({"Uji": "Tbl_Peramalan (rumus rekursif) vs statsmodels",
                          "Periode": r["Periode"], "Besaran": kol_a,
                          "Access": float(hasil[kol_a].iloc[h]), "Python": float(r[kol_p])})

    # (c) One-step historis: query Access vs prediksi 1 langkah statsmodels (parameter sama)
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    ln = np.log(df[em.TARGET_COL])
    model = SARIMAX(ln, order=(1, 0, 0), seasonal_order=(1, 1, 0, 12), trend="n",
                    enforce_stationarity=True, enforce_invertibility=True)
    res = model.filter(np.array([par["ar.L1"], par["ar.S.L12"], par["sigma2"]]))
    pred = np.exp(res.get_prediction().predicted_mean)
    qh["Periode_Ramalan"] = pd.to_datetime(qh["Periode_Ramalan"])
    for _, q in qh.sort_values("Periode_Ramalan").iterrows():
        p = q["Periode_Ramalan"]
        if p in pred.index:
            baris.append({"Uji": "One-step historis: qry_11_Ramalan_1_Bulan_Historis vs statsmodels",
                          "Periode": p.strftime("%Y-%m"), "Besaran": "Prediksi_Kg",
                          "Access": float(q["Prediksi_Kg"]), "Python": float(pred.loc[p]),
                          "Aktual_Kg": float(df.loc[p, em.TARGET_COL])})

    ver = pd.DataFrame(baris)
    ver["Selisih"] = ver["Access"] - ver["Python"]
    ver["Selisih_Relatif_%"] = ver["Selisih"] / ver["Python"] * 100
    ver.to_csv(VERIFIKASI_CSV, index=False)

    for uji, isi in ver.groupby("Uji", sort=False):
        print(f"- {uji}: {len(isi)} nilai, selisih relatif maks "
              f"{isi['Selisih_Relatif_%'].abs().max():.6f}%")
    print(f"Isi qry_11_Peramalan_6_Bulan: {len(q6)} baris")
    print(f"Verifikasi disimpan ke: {VERIFIKASI_CSV}")
    return ver


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    print("=" * 75)
    print("PROGRAM IMPLEMENTASI SISTEM KE MS ACCESS")
    print("=" * 75)
    df, par = muat_data()
    backup, n_trx, kg_trx = backup_dan_inventaris()
    buat_tabel(df, par)
    buat_query()
    hasil = isi_peramalan(df, par)
    verifikasi(df, par, hasil)

    objek = pd.DataFrame(
        [{"Jenis": "Tabel", "Nama": t} for t in TABEL_BARU]
        + [{"Jenis": "Query", "Nama": q} for q in QUERIES]
        + [{"Jenis": "Modul VBA (impor manual)", "Nama": "sql/11_modul_peramalan.bas"},
           {"Jenis": "Backup database", "Nama": f"data/{backup.name}"}])
    objek.to_csv(OBJEK_CSV, index=False)

    print("\n" + "=" * 75)
    print("TAHAP 11 SELESAI. Tabel, query, dan peramalan sudah tersedia di MS Access.")
    print("=" * 75)


if __name__ == "__main__":
    main()
