# Setup Environment — Judul 11
**Prediksi Permintaan Daging Kambing di Pasar Lokal Menggunakan ARIMA (Time Series Analysis)**

Tools sesuai metodologi: **Python (Pandas, Statsmodels, Matplotlib)** untuk analisis, **MS Access** untuk sumber data dan implementasi output.

```
Penelitian ARIMA Kambing/
├── README.md               <- panduan ini
├── requirements.txt        <- daftar library Python
├── koneksi.py              <- helper koneksi Python <-> Access (get_conn, baca_sql, tulis_df)
├── 01_cek_environment.py   <- cek semua komponen sudah siap
├── 02_buat_database.py     <- membuat .accdb + 4 tabel
├── sql/query_access.sql    <- query untuk disimpan di Access
├── data/                   <- (dibuat otomatis) db_penjualan_kambing.accdb
└── output/grafik/          <- (dibuat otomatis) grafik hasil analisis
```

---

## Langkah 1 — Install Python (64-bit)
1. Download Python **3.12** dari https://www.python.org/downloads/windows/ → pilih *Windows installer (64-bit)*.
2. Saat install, **centang "Add python.exe to PATH"**.
3. Cek di PowerShell / terminal VS Code:
   ```powershell
   python --version
   ```
> Sudah punya Python? Tidak masalah, asal versi ≥ 3.10. Yang penting catat dia **64-bit atau 32-bit** (script cek di Langkah 4 akan memberi tahu).

## Langkah 2 — Buat virtual environment & install library
Buka folder `Penelitian ARIMA Kambing` di VS Code → Terminal → New Terminal, lalu:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
- Kalau muncul error *"running scripts is disabled on this system"*, jalankan sekali:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` lalu ulangi `Activate.ps1`.
- Di VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → pilih yang `.venv`.

## Langkah 3 — Pastikan driver MS Access ada (bagian yang paling sering bermasalah)
Python membaca file `.accdb` lewat **driver ODBC Access**, dan **bit driver harus sama dengan bit Python**.

| Kondisi di laptop | Yang perlu dilakukan |
|---|---|
| MS Office/Access **64-bit** terpasang | Biasanya driver sudah ada. Jalankan Langkah 4 dulu. |
| Belum ada MS Access / driver tidak terdeteksi | Install **Microsoft Access Database Engine 2016 Redistributable** → file `accessdatabaseengine_X64.exe` (https://www.microsoft.com/en-us/download/details.aspx?id=54920) |
| Office **32-bit** tapi Python **64-bit** | Installer 64-bit akan menolak. Jalankan lewat Command Prompt (Run as Administrator): `accessdatabaseengine_X64.exe /quiet` |

Untuk **membuka** file `.accdb` dan membuat query/form, tetap butuh aplikasi **MS Access** (bagian dari Office, atau *Microsoft 365 Access Runtime* hanya untuk menjalankan).

## Langkah 4 — Cek environment
```powershell
python 01_cek_environment.py
```
Semua baris harus `[OK]`. Script ini menguji: versi & bit Python, semua library, fungsi statistik yang dipakai di metodologi (ADF, dekomposisi, SARIMA, forecast CI 95%, Ljung-Box, Shapiro-Wilk), simpan grafik, dan koneksi ke Access (buat file, CREATE TABLE, INSERT, SELECT).

## Langkah 5 — Buat database Access
```powershell
python 02_buat_database.py
```
Menghasilkan `data/db_penjualan_kambing.accdb` dengan tabel:

| Tabel | Isi | Peran di metodologi |
|---|---|---|
| `Pelanggan` | ID, nama, **tipe pelanggan**, alamat | analisis tambahan |
| `Transaksi_Penjualan` | tanggal, ID pelanggan, **jenis produk (Daging/Karkas)**, **kuantitas kg**, **harga/kg**, total | sumber data time series |
| `Hasil_Prediksi` | model, periode, prediksi kg, batas bawah/atas CI 95% | implementasi output forecast 6 bulan |
| `Evaluasi_Model` | AIC, BIC, MAPE, RMSE, MAE, MSE, R², p Ljung-Box, p Shapiro-Wilk | perbandingan 4 skenario model |

## Langkah 6 — Simpan query di Access
Buka `.accdb` di MS Access → **Create → Query Design → SQL View**, paste satu per satu dari `sql/query_access.sql`:
- `qry_Permintaan_Bulanan` — agregasi bulanan (GROUP BY MONTH) + harga rata-rata + jumlah pesanan (variabel eksogen ARIMAX)
- `qry_Permintaan_Per_Tipe_Pelanggan`
- `qry_Prediksi_6_Bulan` — menampilkan forecast terbaru (output untuk manajemen)
- `qry_Perbandingan_Model`

> Saat Python menulis ke `Hasil_Prediksi`, pakai **satu nilai `Tanggal_Dibuat` yang sama** untuk 6 baris dalam satu kali forecast, supaya `qry_Prediksi_6_Bulan` mengambil batch terbaru dengan benar.

## Cara pakai di analisis nanti
```python
from koneksi import baca_sql, tulis_df

df = baca_sql("SELECT * FROM qry_Permintaan_Bulanan")   # query Access bisa dibaca seperti tabel
df["Periode"] = pd.to_datetime(df["Periode"])
y = df.set_index("Periode")["Permintaan_Kg"].asfreq("MS")
y = y.interpolate("linear")                               # imputasi bulan kosong
```

## Masalah umum
| Error | Solusi |
|---|---|
| `Data source name not found and no default driver specified` | Driver Access belum ada / beda bit → Langkah 3 |
| `Could not use ''; file already in use` | Tutup file `.accdb` di MS Access (atau hapus file `.laccdb`) |
| `ModuleNotFoundError` | `.venv` belum aktif, atau belum `pip install -r requirements.txt` |
| Grafik tidak muncul di terminal | Simpan dengan `plt.savefig(...)` atau jalankan di Jupyter notebook VS Code |
