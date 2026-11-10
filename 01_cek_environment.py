"""
Cek apakah environment siap untuk penelitian Judul 11 (ARIMA daging kambing).
Jalankan:  python 01_cek_environment.py
"""
import importlib
import platform
import struct
import sys
import tempfile
import warnings
from pathlib import Path

warnings.simplefilter("ignore", FutureWarning)
hasil = []


def lapor(nama, ok, info=""):
    hasil.append(ok)
    print(f"  [{'OK' if ok else 'GAGAL'}] {nama}" + (f"  -> {info}" if info else ""))


print("\n=== 1. Python ===")
bit = struct.calcsize("P") * 8
lapor("Versi Python >= 3.10", sys.version_info >= (3, 10), platform.python_version())
print(f"  [INFO] Python {bit}-bit  (driver Access harus {bit}-bit juga)")
if sys.prefix != sys.base_prefix:
    print("  [OK] Berjalan di virtual environment (.venv)")
else:
    print("  [SARAN] Tidak di .venv -> disarankan aktifkan .venv (README Langkah 2)")

print("\n=== 2. Library analisis ===")
for mod in ["pandas", "numpy", "statsmodels", "matplotlib", "scipy", "pyodbc", "msaccessdb"]:
    try:
        m = importlib.import_module(mod)
        lapor(mod, True, getattr(m, "__version__", "terpasang"))
    except ImportError:
        lapor(mod, False, "jalankan: pip install -r requirements.txt")

print("\n=== 3. Fungsi statistik yang dipakai di metodologi ===")
try:
    import numpy as np
    import pandas as pd
    from scipy.stats import shapiro
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.stattools import adfuller

    # data dummy 36 bulan dengan pola musiman (hanya untuk uji, bukan data penelitian)
    rng = np.random.default_rng(42)
    idx = pd.date_range("2023-01-01", periods=36, freq="MS")
    y = pd.Series(1000 + 5 * np.arange(36) + 200 * np.sin(2 * np.pi * np.arange(36) / 12)
                  + rng.normal(0, 30, 36), index=idx)

    adf_p = adfuller(y)[1]
    seasonal_decompose(y, period=12)
    model = SARIMAX(y[:28], order=(1, 1, 1), seasonal_order=(0, 1, 0, 12)).fit(disp=False)
    fc = model.get_forecast(6).conf_int(alpha=0.05)
    lb = acorr_ljungbox(model.resid, lags=[6])["lb_pvalue"].iloc[0]
    sw = shapiro(model.resid)[1]
    lapor("ADF, dekomposisi, SARIMA, forecast CI 95%, Ljung-Box, Shapiro-Wilk", True,
          f"AIC={model.aic:.1f}")
except Exception as e:
    lapor("Uji fungsi statistik", False, repr(e))

print("\n=== 4. Matplotlib (simpan grafik) ===")
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])
    tmp_png = Path(tempfile.gettempdir()) / "cek_plot.png"
    fig.savefig(tmp_png)
    plt.close(fig)
    lapor("Simpan grafik PNG", tmp_png.exists())
except Exception as e:
    lapor("Simpan grafik PNG", False, repr(e))

print("\n=== 5. MS Access (driver ODBC) ===")
try:
    import pyodbc
    drivers = [d for d in pyodbc.drivers() if "Access" in d]
    ada = "Microsoft Access Driver (*.mdb, *.accdb)" in drivers
    lapor("Driver 'Microsoft Access Driver (*.mdb, *.accdb)'", ada,
          ", ".join(drivers) if drivers else
          f"tidak ada driver Access {bit}-bit -> install Access Database Engine {bit}-bit (README Langkah 3)")
    if ada:
        import msaccessdb
        tmp_db = Path(tempfile.gettempdir()) / "cek_koneksi.accdb"
        if tmp_db.exists():
            tmp_db.unlink()
        msaccessdb.create(str(tmp_db))
        conn = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={tmp_db};")
        cur = conn.cursor()
        cur.execute("CREATE TABLE uji (id COUNTER PRIMARY KEY, nilai DOUBLE)")
        cur.execute("INSERT INTO uji (nilai) VALUES (?)", 3.14)
        conn.commit()
        n = cur.execute("SELECT COUNT(*) FROM uji").fetchval()
        conn.close()
        tmp_db.unlink()
        lapor("Buat .accdb, CREATE TABLE, INSERT, SELECT", n == 1)
except Exception as e:
    lapor("Koneksi MS Access", False, repr(e))

print("\n" + "=" * 50)
if all(hasil):
    print("SEMUA OK - environment siap. Lanjut: python 02_buat_database.py")
else:
    print(f"{hasil.count(False)} cek GAGAL - perbaiki sesuai petunjuk di atas / README.")
print("=" * 50)
