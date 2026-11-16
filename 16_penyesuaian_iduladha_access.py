"""
=============================================================================
PROGRAM PENYESUAIAN KALENDER IDULADHA DI MS ACCESS (TANPA VBA, TANPA PYTHON)
File: 16_penyesuaian_iduladha_access.py

Script 13 menggeser puncak ramalan ke bulan Iduladha yang sebenarnya, tetapi
di Python. Akibatnya pengguna MS Access (qry_12_Ramalan_6_Bulan) masih melihat
puncak di bulan lonjakan model (Juni). Script ini memasang aturan yang SAMA
dengan script 13 sebagai tabel + query Access, di atas qry_12_Ramalan_6_Bulan:

  Bobot bulan  = porsi hari jendela H-7 s.d. H+3 yang jatuh di bulan itu
  R            = ramalan bulan lonjakan model / ramalan bulan acuan
                 (acuan = bulan sebelumnya; bila lonjakan di bulan pertama
                 ramalan, acuan = bulan sesudahnya)
  Pengali      = R^Bobot, dan bulan lonjakan model dibagi R
  Disesuaikan  = ramalan x pengali (batas 95% dikali pengali yang sama)

Agar tidak tumpang tindih:
- tanggal Iduladha, jendela H-7/H+3, dan bulan lonjakan historis diambil dari
  script 13 (TANGGAL_IDULADHA, HARI_SEBELUM/SESUDAH, bulan_iduladha_historis);
- koneksi ODBC, pembacaan lewat MS Access asli (DAO), dan rumus ramalan Python
  diambil dari script 12;
- query lama (qry_11_*, qry_12_*) tidak diubah; objek baru berawalan
  Tbl_16_/qry_16_.

Verifikasi: hasil query (ODBC dan DAO) vs 13_peramalan_disesuaikan_iduladha.csv,
dan uji dinamis di SALINAN database (tambah data Jan 2026) vs fungsi sesuaikan()
script 13 yang diterapkan pada ramalan Python script 12.

Output : objek baru di data/db_penjualan_kambing.accdb (backup dibuat dulu),
         data/hasil_16/*.csv, sql/16_query_penyesuaian_iduladha.sql
=============================================================================
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import keterangan_csv as kk
import pembanding as pb
from koneksi import DB_PATH

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "data" / "hasil_16"
OUT.mkdir(parents=True, exist_ok=True)
SQL_FILE = BASE_DIR / "sql" / "16_query_penyesuaian_iduladha.sql"

S12 = pb.muat_skrip("12_ramalan_6_bulan_access.py")
S13 = pb.muat_skrip("13_penyesuaian_iduladha.py")

KOLOM_HASIL = ["Ramalan_Disesuaikan_Kg", "Batas_Bawah_95_Disesuaikan_Kg", "Batas_Atas_95_Disesuaikan_Kg"]

TABEL = {
    "Tbl_16_Tanggal_Iduladha": "CREATE TABLE Tbl_16_Tanggal_Iduladha (Tahun INTEGER PRIMARY KEY, Tanggal DATETIME)",
    "Tbl_16_Jendela_Iduladha": "CREATE TABLE Tbl_16_Jendela_Iduladha (Hari_Ke INTEGER PRIMARY KEY)",
    "Tbl_16_Bulan_Lonjakan_Model": "CREATE TABLE Tbl_16_Bulan_Lonjakan_Model (Bulan INTEGER PRIMARY KEY)",
}

_TGL_JENDELA = "DateAdd('d', J.Hari_Ke, T.Tanggal)"
QUERIES = {
    "qry_16_Bobot_Iduladha": f"""
SELECT DateSerial(Year({_TGL_JENDELA}), Month({_TGL_JENDELA}), 1) AS Periode, T.Tahun,
       Count(*) / N.Jumlah_Hari AS Bobot
FROM Tbl_16_Tanggal_Iduladha AS T, Tbl_16_Jendela_Iduladha AS J,
     (SELECT Count(*) AS Jumlah_Hari FROM Tbl_16_Jendela_Iduladha) AS N
GROUP BY DateSerial(Year({_TGL_JENDELA}), Month({_TGL_JENDELA}), 1), T.Tahun, N.Jumlah_Hari""",
    "qry_16_Ramalan_Dasar": """
SELECT Year(R.Periode) AS Tahun, R.Periode, R.Ramalan_Kg, R.Batas_Bawah_95_Kg, R.Batas_Atas_95_Kg
FROM qry_12_Ramalan_6_Bulan AS R""",
    "qry_16_Bulan_Pertama": """
SELECT Min(Periode) AS Periode_Pertama FROM qry_16_Ramalan_Dasar""",
    "qry_16_Lonjakan_Model": """
SELECT L.Tahun AS Tahun_L, DateSerial(L.Tahun, B.Bulan, 1) AS Periode_Lonjakan,
       Max(IIf(D.Periode = DateSerial(L.Tahun, B.Bulan, 1), D.Ramalan_Kg, Null)) AS Y_Lonjakan,
       Max(IIf(D.Periode = IIf(DateSerial(L.Tahun, B.Bulan, 1) = F.Periode_Pertama,
                               DateAdd('m', 1, DateSerial(L.Tahun, B.Bulan, 1)),
                               DateAdd('m', -1, DateSerial(L.Tahun, B.Bulan, 1))), D.Ramalan_Kg, Null)) AS Y_Acuan
FROM qry_16_Ramalan_Dasar AS D, Tbl_16_Tanggal_Iduladha AS L, Tbl_16_Bulan_Lonjakan_Model AS B,
     qry_16_Bulan_Pertama AS F
WHERE D.Tahun = L.Tahun
GROUP BY L.Tahun, DateSerial(L.Tahun, B.Bulan, 1)""",
    "qry_16_Pengali_Iduladha": """
SELECT D.Periode, D.Ramalan_Kg, D.Batas_Bawah_95_Kg, D.Batas_Atas_95_Kg,
       IIf(L.Y_Lonjakan Is Null Or L.Y_Acuan Is Null, 0, IIf(W.Bobot Is Null, 0, W.Bobot)) AS Bobot_Iduladha,
       IIf(L.Y_Lonjakan Is Null Or L.Y_Acuan Is Null, 1,
           IIf(D.Periode = L.Periode_Lonjakan, L.Y_Acuan / L.Y_Lonjakan, 1)
           * (L.Y_Lonjakan / L.Y_Acuan) ^ IIf(W.Bobot Is Null, 0, W.Bobot)) AS Pengali
FROM (qry_16_Ramalan_Dasar AS D LEFT JOIN qry_16_Lonjakan_Model AS L ON D.Tahun = L.Tahun_L)
     LEFT JOIN qry_16_Bobot_Iduladha AS W ON D.Periode = W.Periode""",
    "qry_16_Ramalan_Disesuaikan": """
SELECT P.Periode, P.Ramalan_Kg AS Ramalan_Model_Kg, P.Bobot_Iduladha,
       P.Ramalan_Kg * P.Pengali AS Ramalan_Disesuaikan_Kg,
       P.Batas_Bawah_95_Kg * P.Pengali AS Batas_Bawah_95_Disesuaikan_Kg,
       P.Batas_Atas_95_Kg * P.Pengali AS Batas_Atas_95_Disesuaikan_Kg
FROM qry_16_Pengali_Iduladha AS P""",
}


# =============================================================================
# PEMASANGAN OBJEK
# =============================================================================

def backup():
    """Satu backup per hari, pola nama sama dengan script 12."""
    ada = sorted(DB_PATH.parent.glob(f"db_penjualan_kambing_backup_{datetime.now():%Y%m%d}_*.accdb"))
    if ada:
        return ada[0].name, False
    tujuan = DB_PATH.with_name(f"db_penjualan_kambing_backup_{datetime.now():%Y%m%d_%H%M%S}.accdb")
    shutil.copy2(DB_PATH, tujuan)
    return tujuan.name, True


def pasang(db):
    with S12.koneksi(db) as conn:
        cur = conn.cursor()
        for q in reversed(list(QUERIES)):                       # hapus versi lama (dependen dulu)
            if q in S12.objek(cur, "VIEW"):
                cur.execute(f"DROP TABLE {q}")
        for t in TABEL:
            if t in S12.objek(cur, "TABLE"):
                cur.execute(f"DROP TABLE {t}")
        conn.commit()
        for sql in TABEL.values():
            cur.execute(sql)
        cur.executemany("INSERT INTO Tbl_16_Tanggal_Iduladha (Tahun, Tanggal) VALUES (?, ?)",
                        [(th, datetime.fromisoformat(tg)) for th, tg in S13.TANGGAL_IDULADHA.items()])
        cur.executemany("INSERT INTO Tbl_16_Jendela_Iduladha (Hari_Ke) VALUES (?)",
                        [(d,) for d in range(-S13.HARI_SEBELUM, S13.HARI_SESUDAH + 1)])
        cur.executemany("INSERT INTO Tbl_16_Bulan_Lonjakan_Model (Bulan) VALUES (?)",
                        [(b,) for b in S13.bulan_iduladha_historis()])
        conn.commit()
        for nama, sql in QUERIES.items():
            cur.execute(f"CREATE VIEW {nama} AS {sql.strip()}")
        conn.commit()


# =============================================================================
# VERIFIKASI
# =============================================================================

def rapikan(df):
    d = df.copy()
    d["Periode"] = pd.to_datetime(d["Periode"]).dt.strftime("%Y-%m")
    for k in KOLOM_HASIL + ["Bobot_Iduladha"]:
        d[k] = d[k].astype(float)
    return d.sort_values("Periode").reset_index(drop=True)[["Periode", "Bobot_Iduladha"] + KOLOM_HASIL]


def referensi_13(ramalan):
    """Terapkan fungsi sesuaikan() script 13 pada tabel ramalan (Periode, Ramalan_Kg, batas)."""
    f = ramalan.rename(columns={"Ramalan_Kg": "Yhat_Kg"}).copy()
    f, *_ = S13.sesuaikan(f, S13.bulan_iduladha_historis())
    return rapikan(f.rename(columns={"Yhat_Disesuaikan_Kg": "Ramalan_Disesuaikan_Kg"}))


def bandingkan(a, b, uji):
    baris = []
    for i in range(len(a)):
        for k in ["Bobot_Iduladha"] + KOLOM_HASIL:
            x, y = float(a[k].iloc[i]), float(b[k].iloc[i])
            baris.append({"Uji": uji, "Periode": a["Periode"].iloc[i], "Besaran": k, "Access": x, "Python": y,
                          "Selisih_Relatif_%": 0.0 if x == y else (x - y) / (y if y else 1) * 100})
    return pd.DataFrame(baris)


def main():
    print("=" * 75); print("SCRIPT 16: PENYESUAIAN KALENDER IDULADHA DI MS ACCESS"); print("=" * 75)
    if DB_PATH.with_suffix(".laccdb").exists():
        raise RuntimeError("Database sedang dibuka di MS Access. Tutup Access lalu jalankan ulang.")
    nama_backup, baru = backup()
    print(f"Backup database : {nama_backup}{'' if baru else ' (sudah ada hari ini)'}")
    pasang(DB_PATH)
    print(f"Objek dibuat    : {', '.join(TABEL)}, {', '.join(QUERIES)}")

    # 1. Database asli vs output script 13
    ref13 = kk.baca_csv(S13.HASIL_CSV).rename(columns={"Yhat_Disesuaikan_Kg": "Ramalan_Disesuaikan_Kg"})
    ref13 = rapikan(ref13)
    dao = rapikan(S12.baca_dao(str(DB_PATH), "qry_16_Ramalan_Disesuaikan"))
    odbc = rapikan(S12.baca_odbc(DB_PATH, "SELECT * FROM qry_16_Ramalan_Disesuaikan"))
    ver = [bandingkan(dao, ref13, "MS Access asli (DAO) vs output script 13"),
           bandingkan(odbc, ref13, "Driver ODBC vs output script 13")]

    # 2. Uji dinamis di salinan: + data Jan 2026 dummy (sama seperti script 12)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        salinan = Path(tmp) / "uji_dinamis_16.accdb"
        shutil.copy2(DB_PATH, salinan)
        dummy = float(ref13["Ramalan_Disesuaikan_Kg"].iloc[0]) * 1.05
        with S12.koneksi(salinan) as conn:
            conn.cursor().execute("INSERT INTO Tbl_Volume_Bulanan (Periode, Tahun, Bulan, Permintaan_Kg, Sumber) "
                                  "VALUES (?, 2026, 1, ?, 'UJI DUMMY')", datetime(2026, 1, 1), dummy)
            conn.commit()
        dao_baru = rapikan(S12.baca_dao(str(salinan), "qry_16_Ramalan_Disesuaikan"))
        ref_baru = referensi_13(S12.ramalan_python(salinan))
    ver.append(bandingkan(dao_baru, ref_baru, "Uji dinamis (+data Jan 2026 dummy): DAO vs sesuaikan() script 13"))
    ver = pd.concat(ver, ignore_index=True)

    kk.simpan_csv(dao, OUT / "16_hasil_qry_16_Ramalan_Disesuaikan_access.csv", index=False)
    kk.simpan_csv(dao_baru, OUT / "16_uji_dinamis_feb_jul_2026.csv", index=False)
    kk.simpan_csv(ver, OUT / "16_verifikasi_penyesuaian_iduladha.csv", index=False)

    teks = ["-- Penyesuaian kalender Iduladha murni MS Access (dibuat oleh 16_penyesuaian_iduladha_access.py).",
            "-- Bergantung pada qry_12_Ramalan_6_Bulan (script 12). Tabel isian:", ""]
    teks += [f"{s};" for s in TABEL.values()] + [""]
    for n, s in QUERIES.items():
        teks += [f"-- Simpan sebagai: {n}", s.strip() + ";", ""]
    SQL_FILE.write_text("\n".join(teks), encoding="utf-8")

    print("\nqry_16_Ramalan_Disesuaikan (MS Access asli):")
    print(dao.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    for uji, isi in ver.groupby("Uji", sort=False):
        print(f"- {uji}: selisih relatif maks {isi['Selisih_Relatif_%'].abs().max():.8f}%")
    print("Uji dinamis (Feb-Jul 2026):")
    print(dao_baru.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))


if __name__ == "__main__":
    main()
