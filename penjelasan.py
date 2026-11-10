"""
=============================================================================
MODUL PENJELASAN RUMUS DI TERMINAL (dipakai script 03-09)
File: penjelasan.py

Menampilkan CONTOH PERHITUNGAN setiap rumus memakai data nyata penelitian,
lalu mencocokkannya dengan hasil program (CSV/plot). Setiap bagian diberi
nomor sesuai pertanyaan dosen:
  [1] Generate data            [6] Penetapan 4 skenario
  [2] Pra-proses data          [7] Pemilihan model
  [3] Pembagian data           [8] AIC dan BIC
  [4] Stasioneritas (ADF)      [9] Validasi diagnostik & evaluasi kinerja
  [5] ACF dan PACF                 (Ljung-Box, Shapiro-Wilk, Q-Q, rolling
                                    origin, MAPE/RMSE/MAE/MSE/R², ramalan)
Aturan: bila perhitungan diulang n kali, yang ditampilkan perhitungan ke-1.

Modul ini HANYA menampilkan perhitungan; tidak mengubah data atau hasil.
Output terminal setiap script juga disimpan ke folder log_terminal/.
=============================================================================
"""

import atexit
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log_terminal"
LEBAR = 78


# =============================================================================
# TAMPILAN TERMINAL DAN LOG
# =============================================================================

class _Tee:
    def __init__(self, *aliran):
        self.aliran = aliran

    def write(self, data):
        for a in self.aliran:
            a.write(data)
        return len(data)

    def flush(self):
        for a in self.aliran:
            a.flush()


def mulai(nama_log):
    """UTF-8 di terminal + salin seluruh output ke log_terminal/<nama_log>.txt."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    LOG_DIR.mkdir(exist_ok=True)
    f = open(LOG_DIR / f"{nama_log}.txt", "w", encoding="utf-8")
    asli = sys.stdout
    sys.stdout = _Tee(asli, f)

    def _tutup():
        sys.stdout.flush()
        sys.stdout = asli
        f.close()

    atexit.register(_tutup)


def fmt(x, d=2):
    """Angka gaya Indonesia: titik ribuan, koma desimal."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "-"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fp(x, d=2):
    """Angka dalam rumus: bilangan negatif diberi tanda kurung."""
    return f"({fmt(x, d)})" if x < 0 else fmt(x, d)


def kepala(no, judul, sumber=""):
    teks = f" [{no}] {judul}"
    teks2 = f"     {sumber}" if sumber else ""
    w = max(LEBAR - 2, len(teks) + 1, len(teks2) + 1)
    print("\n" + "╔" + "═" * w + "╗")
    print("║" + teks.ljust(w) + "║")
    if sumber:
        print("║" + teks2.ljust(w) + "║")
    print("╚" + "═" * w + "╝")


def sub(judul):
    print("\n  ┌─ " + judul)


def rumus(teks):
    print(f"  │ Rumus   : {teks}")


def lanjut(teks):
    print(f"  │           {teks}")


def isi(label, nilai):
    print(f"  │ {label:<24}: {nilai}")


def baris(teks=""):
    print(f"  │ {teks}")


def cek(label, manual, program, d=4, tol_rel=1e-6, tol_abs=None):
    manual, program = float(manual), float(program)
    selisih = abs(manual - program)
    batas = tol_abs if tol_abs is not None else max(tol_rel * abs(program), 1e-9)
    status = "COCOK ✔" if selisih <= batas else "BERBEDA ✘"
    print(f"  └─ Cek {label}: manual = {fmt(manual, d)} | program = {fmt(program, d)} "
          f"| selisih = {fmt(selisih, 6)} → {status}")


def akhir_bagian():
    print("  " + "─" * (LEBAR - 4))


# =============================================================================
# [1] GENERATE DATA (script 03)
# =============================================================================

def jelaskan_03(g, baseline, volume, transaksi, gradien, koef_s):
    """g = globals() script 03 (konstanta)."""
    kepala(1, "RUMUS GENERATE DATA (data historis sintetis berbasis BPS)",
           "Script 03_generate_data.py · pembanding: data/hasil_generate/volume_bulanan.csv")

    b = baseline.iloc[0]
    sub(f"1a. Baseline bulanan (Tahap 2), tahun {int(b['Tahun'])}")
    rumus("μ = Karkas Tahunan Kabupaten / 12")
    isi("Karkas tahunan BPS", f"{fmt(b['Karkas_Tahunan_Kab'])} kg ({g['WILAYAH']})")
    isi("Hitung", f"{fmt(b['Karkas_Tahunan_Kab'])} / 12 = {fmt(b['Karkas_Tahunan_Kab'] / 12)} kg/bulan")
    cek("μ", b["Karkas_Tahunan_Kab"] / 12, b["Mu_Lokal"], 2)

    sub(f"1b. Rasio komposisi produk (peluang jenis produk), tahun {int(b['Tahun'])}")
    rumus("Rasio produk i = Produksi produk i / (Murni + Karkas + Jeroan + Variasi)")
    total = sum(b[f"Rasio_{p}"] for p in g["PRODUK"])
    for p in g["PRODUK"]:
        isi(p, f"{fmt(b[f'Rasio_{p}'] * 100, 2)}%")
    cek("jumlah rasio = 1", total, 1.0, 6)

    v1 = volume.iloc[0]
    k = g["K_TOLERANSI"]
    sub(f"1c. Volume dasar bulan t = 1 ({v1['Periode']:%b %Y}) — undian seragam")
    rumus("Volume dasar ~ Uniform(μ − k·μ , μ + k·μ),  k = 10%")
    isi("Batas bawah", f"{fmt(v1['Mu_Lokal'])} − {fmt(k, 1)} × {fmt(v1['Mu_Lokal'])} = {fmt(v1['Mu_Lokal'] * (1 - k))} kg")
    isi("Batas atas", f"{fmt(v1['Mu_Lokal'])} + {fmt(k, 1)} × {fmt(v1['Mu_Lokal'])} = {fmt(v1['Mu_Lokal'] * (1 + k))} kg")
    isi("Hasil undian (seed 42)", f"{fmt(v1['Target_Kg'])} kg (berada di dalam rentang)")
    cek("batas bawah", v1["Mu_Lokal"] * (1 - k), v1["Batas_Bawah"], 2)

    gr = gradien[gradien["Tahun"] == 2024].iloc[0]
    prod = g["PRODUKSI_NASIONAL"]
    v13 = volume[volume["t"] == 13].iloc[0]
    sub("1d. Injeksi tren linier (Tahap 3) — bulan pertama yang memiliki tren: t = 13 (Jan 2024)")
    rumus("Growth = (Produksi_2024 − Produksi_2023) / Produksi_2023 ;  m = Growth / 12")
    lanjut("Faktor Tren_t = 1 + m × (t − t_awal_fase) ;  Volume Tren = Volume dasar × Faktor Tren")
    growth = (prod[2024] - prod[2023]) / prod[2023]
    isi("Growth 2024", f"({fmt(prod[2024])} − {fmt(prod[2023])}) / {fmt(prod[2023])} = {fmt(growth * 100, 4)}%")
    isi("m per bulan", f"{fmt(growth * 100, 4)}% / 12 = {fmt(growth / 12 * 100, 4)}%")
    faktor = 1 + gr["m_Bulanan"] * (13 - gr["t_awal_fase"])
    isi("Faktor tren t = 13", f"1 + ({fmt(gr['m_Bulanan'], 6)}) × (13 − {int(gr['t_awal_fase'])}) = {fmt(faktor, 6)}")
    isi("Volume tren", f"{fmt(v13['Target_Kg'])} × {fmt(faktor, 6)} = {fmt(v13['Target_Kg'] * faktor)} kg")
    baris("Catatan: tahun 2023 fase stabil (m = 0), sehingga faktor tren t = 1–12 = 1.")
    cek("volume tren t=13", round(v13["Target_Kg"] * faktor, 2), v13["Volume_Tren_Kg"], 2, tol_abs=0.006)

    v6 = volume[volume["t"] == 6].iloc[0]
    sub("1e. Faktor musiman Iduladha (Tahap 4) — bulan Iduladha pertama: t = 6 (Jun 2023)")
    rumus("S = 1 + (Pemotongan Juni − Pemotongan Mei) / Pemotongan Mei  (BPS 2024)")
    lanjut("Volume Musim_t = Volume Tren_t × S  (bulan Iduladha), × 1 (bulan biasa)")
    mei, jun = g["PEMOTONGAN_MEI_2024"], g["PEMOTONGAN_JUNI_2024"]
    isi("S", f"1 + ({fmt(jun, 0)} − {fmt(mei, 0)}) / {fmt(mei, 0)} = {fmt(1 + (jun - mei) / mei, 4)} → {fmt(koef_s, 3)}")
    isi("Volume musim t = 6", f"{fmt(v6['Volume_Tren_Kg'])} × {fmt(koef_s, 3)} = {fmt(v6['Volume_Tren_Kg'] * koef_s)} kg")
    cek("volume musim t=6", round(v6["Volume_Tren_Kg"] * koef_s, 2), v6["Volume_Musim_Kg"], 2, tol_abs=0.006)

    sub(f"1f. White noise (Tahap 6) — bulan t = 1 ({v1['Periode']:%b %Y})")
    rumus("σ_t = 5% × Volume Musim_t ;  ε_t ~ N(0, σ_t²) ;  Volume Akhir_t = Volume Musim_t + ε_t")
    isi("σ_1", f"0,05 × {fmt(v1['Volume_Musim_Kg'])} = {fmt(0.05 * v1['Volume_Musim_Kg'])} kg")
    isi("ε_1 (undian normal)", f"{fmt(v1['Noise_Kg'])} kg")
    isi("Volume akhir", f"{fmt(v1['Volume_Musim_Kg'])} + ({fmt(v1['Noise_Kg'])}) = "
        f"{fmt(v1['Volume_Musim_Kg'] + v1['Noise_Kg'])} kg")
    cek("volume akhir t=1", v1["Volume_Musim_Kg"] + v1["Noise_Kg"], v1["Volume_Akhir_Kg"], 2, tol_abs=0.006)

    tr = transaksi.iloc[0]
    pmin, pmax = g["RENTANG_HARGA"][tr["Jenis_Produk"]]
    sub(f"1g. Transaksi pertama ({tr['ID_Transaksi']}, {tr['Tanggal_Transaksi']:%d-%m-%Y})")
    rumus("Berat ~ Uniform(5, 35) kg ;  Harga normal ~ Uniform(P_min, P_max), dibulatkan Rp500")
    lanjut("Harga final = Harga normal + markup (Rp10.000–15.000 hanya di bulan Iduladha)")
    lanjut("Total pendapatan = Kuantitas × Harga final")
    isi("Jenis produk (undian)", f"{tr['Jenis_Produk']} (rentang Rp{fmt(pmin, 0)}–{fmt(pmax, 0)}/kg)")
    isi("Kuantitas", f"{fmt(tr['Kuantitas_Kg'])} kg")
    isi("Harga final", f"{fmt(tr['Harga_Normal'], 0)} + {fmt(tr['Markup_Musiman'], 0)} = {fmt(tr['Harga_Final'], 0)}")
    isi("Pendapatan", f"{fmt(tr['Kuantitas_Kg'])} × {fmt(tr['Harga_Final'], 0)} = "
        f"Rp{fmt(tr['Kuantitas_Kg'] * tr['Harga_Final'])}")
    cek("pendapatan", tr["Kuantitas_Kg"] * tr["Harga_Final"], tr["Total_Pendapatan"], 2, tol_abs=0.006)

    trx1 = transaksi[transaksi["t"] == 1]
    sub("1h. Rekap bulanan variabel eksogen — bulan t = 1")
    rumus("Jumlah pesanan = banyak struk ;  Harga rata-rata = Σ Pendapatan / Σ kg")
    isi("Jumlah struk", f"{len(trx1)} transaksi")
    isi("Σ kg", f"{fmt(trx1['Kuantitas_Kg'].sum())} kg (= volume akhir {fmt(v1['Volume_Akhir_Kg'])} kg)")
    isi("Harga rata-rata", f"Rp{fmt(trx1['Total_Pendapatan'].sum(), 0)} / {fmt(trx1['Kuantitas_Kg'].sum())} "
        f"= Rp{fmt(trx1['Total_Pendapatan'].sum() / trx1['Kuantitas_Kg'].sum(), 0)}/kg")
    cek("harga rata-rata t=1", round(trx1["Total_Pendapatan"].sum() / trx1["Kuantitas_Kg"].sum(), 0),
        v1["Harga_Rata2_Per_Kg"], 0, tol_abs=0.5)
    akhir_bagian()


# =============================================================================
# [2] PRA-PROSES DATA (script 04)
# =============================================================================

def _kuantil_linear(x_urut, q):
    n = len(x_urut)
    posisi = q * (n - 1)
    lo = int(np.floor(posisi))
    hi = min(lo + 1, n - 1)
    frac = posisi - lo
    return posisi, lo, hi, frac, x_urut[lo] + frac * (x_urut[hi] - x_urut[lo])


def jelaskan_04(df_mentah, df_tahap1):
    kepala(2, "RUMUS PRA-PROSES DATA (agregasi, interpolasi, outlier IQR)",
           "Script 04_pra_proses_data.py · pembanding: data/olah/dataset_pra_proses_final.csv")

    p1 = df_tahap1["Periode"].iloc[0]
    bulan1 = df_mentah[df_mentah["Tanggal_Transaksi"].dt.to_period("M") == p1.to_period("M")]
    sub(f"2a. Agregasi bulanan (GROUP BY MONTH) — bulan pertama {p1:%b %Y}")
    rumus("Total_Kuantitas = Σ Kuantitas_Kg semua transaksi di bulan itu")
    lanjut("Harga_Rata2 = rata-rata Harga_Final ;  Jumlah_Transaksi = banyak transaksi")
    contoh = " + ".join(fmt(v) for v in bulan1["Kuantitas_Kg"].head(3)) + " + …"
    isi("Kuantitas", f"{contoh} ({len(bulan1)} transaksi)")
    isi("Total", f"{fmt(bulan1['Kuantitas_Kg'].sum())} kg")
    cek("total kg", round(bulan1["Kuantitas_Kg"].sum(), 2), df_tahap1["Total_Kuantitas_Kg"].iloc[0], 2, tol_abs=0.006)
    isi("Harga rata-rata", f"Σ Harga_Final / {len(bulan1)} = Rp{fmt(bulan1['Harga_Final'].mean(), 2)}")
    cek("harga rata-rata", round(bulan1["Harga_Final"].mean(), 0), df_tahap1["Harga_Rata2_Per_Kg"].iloc[0], 0, tol_abs=0.5)

    y = df_tahap1["Total_Kuantitas_Kg"].values
    sub("2b. Interpolasi linier (mengisi bulan yang kosong)")
    rumus("y_t = y_(t−1) + (y_(t+1) − y_(t−1)) × (t − (t−1)) / ((t+1) − (t−1))  = (y_(t−1) + y_(t+1)) / 2")
    baris(f"Data saat ini lengkap {len(y)} bulan berurutan → tidak ada bulan yang diinterpolasi.")
    baris("Ilustrasi bila bulan ke-2 kosong:")
    isi("Perkiraan bulan ke-2", f"({fmt(y[0])} + {fmt(y[2])}) / 2 = {fmt((y[0] + y[2]) / 2)} kg "
        f"(aktual {fmt(y[1])} kg)")

    x = np.sort(y)
    n = len(x)
    pos1, lo1, hi1, f1, q1 = _kuantil_linear(x, 0.25)
    pos3, lo3, hi3, f3, q3 = _kuantil_linear(x, 0.75)
    iqr = q3 - q1
    sub(f"2c. Deteksi outlier metode IQR pada Total_Kuantitas_Kg (n = {n})")
    rumus("Posisi kuantil = q × (n − 1) pada data terurut ;  Q = x_lo + pecahan × (x_hi − x_lo)")
    lanjut("IQR = Q3 − Q1 ;  Batas bawah = Q1 − 1,5·IQR ;  Batas atas = Q3 + 1,5·IQR")
    isi("Q1", f"posisi 0,25×{n - 1} = {fmt(pos1, 2)} → {fmt(x[lo1])} + {fmt(f1, 2)}×({fmt(x[hi1])} − {fmt(x[lo1])}) = {fmt(q1)}")
    isi("Q3", f"posisi 0,75×{n - 1} = {fmt(pos3, 2)} → {fmt(x[lo3])} + {fmt(f3, 2)}×({fmt(x[hi3])} − {fmt(x[lo3])}) = {fmt(q3)}")
    isi("IQR", f"{fmt(q3)} − {fmt(q1)} = {fmt(iqr)}")
    isi("Batas bawah", f"{fmt(q1)} − 1,5 × {fmt(iqr)} = {fmt(q1 - 1.5 * iqr)}")
    isi("Batas atas", f"{fmt(q3)} + 1,5 × {fmt(iqr)} = {fmt(q3 + 1.5 * iqr)}")
    cek("Q1", q1, np.quantile(y, 0.25), 2)
    cek("Q3", q3, np.quantile(y, 0.75), 2)
    luar = df_tahap1[(df_tahap1["Total_Kuantitas_Kg"] < q1 - 1.5 * iqr) | (df_tahap1["Total_Kuantitas_Kg"] > q3 + 1.5 * iqr)]
    baris(f"Aturan: nilai di luar batas DIPERTAHANKAN bila bulan Juni (Iduladha), selain itu dipotong ke batas.")
    baris(f"Outlier terdeteksi: {', '.join(p.strftime('%Y-%m') for p in luar['Periode'])} "
          f"(semuanya Juni → dipertahankan sebagai pola musiman)" if len(luar) else "Outlier: tidak ada")
    akhir_bagian()


# =============================================================================
# [4] STASIONERITAS DAN [5] ACF/PACF (script 05)
# =============================================================================

def jelaskan_05(y, periode, alpha=0.05):
    from statsmodels.tsa.stattools import adfuller, acf, pacf

    y = np.asarray(y, dtype=float)
    n = len(y)

    kepala(4, "STASIONERITAS: UJI ADF DAN DIFFERENCING",
           "Script 05_eksplorasi_data.py · pembanding: terminal ADF di atas, data/eksplorasi/model_config.json")
    stat, p, lag, nobs, crit, _ = adfuller(y, maxlag=None, regression="c", autolag="AIC", result_object=False)
    dy = np.diff(y)
    Y = dy[lag:]
    X = [np.ones(len(Y)), y[lag:-1]]
    for i in range(1, lag + 1):
        X.append(dy[lag - i:-i])
    X = np.column_stack(X)
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    s2 = resid @ resid / (len(Y) - X.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    t_manual = beta[1] / se[1]

    sub(f"4a. Regresi Augmented Dickey-Fuller (lag terpilih AIC = {lag})")
    rumus("Δy_t = α + γ·y_(t−1) + Σ β_i·Δy_(t−i) + e_t   (H0: γ = 0 → tidak stasioner)")
    lanjut("t-ADF = γ̂ / SE(γ̂) ;  SE(γ̂) = √( s² · [(XᵀX)⁻¹]_γγ ) ;  s² = Σe² / (n − p)")
    isi("Contoh baris pertama", f"Δy_2 = y_2 − y_1 = {fmt(y[1])} − {fmt(y[0])} = {fmt(dy[0])}")
    isi("Jumlah observasi regresi", f"{len(Y)}")
    isi("α̂ (konstanta)", fmt(beta[0], 4))
    isi("γ̂ (koefisien y_(t−1))", fmt(beta[1], 6))
    isi("SE(γ̂)", fmt(se[1], 6))
    isi("t-ADF", f"{fmt(beta[1], 6)} / {fmt(se[1], 6)} = {fmt(t_manual, 4)}")
    cek("t-ADF", t_manual, stat, 4)
    isi("Nilai kritis (MacKinnon)", f"1% {fmt(crit['1%'], 4)} | 5% {fmt(crit['5%'], 4)} | 10% {fmt(crit['10%'], 4)}")
    isi("p-value", fmt(p, 6))
    keputusan = "TOLAK H0 → data STASIONER, d = 0" if (p < alpha and stat < crit["5%"]) else "GAGAL TOLAK H0 → perlu differencing"
    isi("Keputusan", f"t-ADF {fmt(stat, 4)} < kritis 5% {fmt(crit['5%'], 4)} dan p < 0,05 → {keputusan}")

    sub("4b. Differencing (cara mengatasi data tidak stasioner)")
    rumus("Differencing biasa : Δy_t = y_t − y_(t−1)")
    lanjut("Differencing musiman: Δ₁₂y_t = y_t − y_(t−12) ;  pada log: w_t = ln y_t − ln y_(t−12)")
    isi(f"Δy ({periode[1]:%b %Y})", f"{fmt(y[1])} − {fmt(y[0])} = {fmt(y[1] - y[0])}")
    isi(f"Δ₁₂y ({periode[12]:%b %Y})", f"{fmt(y[12])} − {fmt(y[0])} = {fmt(y[12] - y[0])}")
    isi(f"w ({periode[12]:%b %Y})", f"ln {fmt(y[12])} − ln {fmt(y[0])} = {fmt(np.log(y[12]), 6)} − "
        f"{fmt(np.log(y[0]), 6)} = {fmt(np.log(y[12]) - np.log(y[0]), 6)}")
    baris("Hasil ADF: seri asli sudah stasioner → d = 0 (tidak didifferencing).")
    baris("Differencing musiman D = 1 pada log tetap diuji di tahap pemodelan (model final memakainya).")
    akhir_bagian()

    kepala(5, "RUMUS ACF DAN PACF",
           "Pembanding: data/eksplorasi/acf_pacf_plot.png dan tabel ACF/PACF di atas")
    ybar = y.mean()
    dev = y - ybar
    pembagi = (dev ** 2).sum()
    acf_sm, ci = acf(y, nlags=12, alpha=alpha, fft=False, bartlett_confint=True, result_object=False)
    sub("5a. ACF (Autocorrelation Function)")
    rumus("r_k = Σ_(t=1..n−k) (y_t − ȳ)(y_(t+k) − ȳ) / Σ_(t=1..n) (y_t − ȳ)²")
    isi("ȳ", f"Σy / {n} = {fmt(ybar)}")
    isi("Penyebut Σ(y − ȳ)²", fmt(pembagi, 2))
    for k_ in (1, 12):
        pemb = (dev[:-k_] * dev[k_:]).sum()
        r = pemb / pembagi
        isi(f"Lag {k_}: pembilang", f"(y₁−ȳ)(y_{1 + k_}−ȳ) + … = {fmt(pemb, 2)}")
        isi(f"r_{k_}", f"{fmt(pemb, 2)} / {fmt(pembagi, 2)} = {fmt(r, 4)}")
        cek(f"ACF lag {k_}", r, acf_sm[k_], 4)
        if k_ == 1:
            print("  ┌─ (lanjutan)")
    z975 = stats.norm.ppf(1 - alpha / 2)
    batas12 = z975 * np.sqrt((1 + 2 * (acf_sm[1:12] ** 2).sum()) / n)
    rumus("Batas signifikansi (Bartlett) lag k = 1,96 × √((1 + 2 Σ_(j<k) r_j²) / n)")
    isi("Batas lag 12", f"1,96 × √((1 + 2×{fmt((acf_sm[1:12] ** 2).sum(), 4)}) / {n}) = {fmt(batas12, 4)}")
    cek("batas lag 12", batas12, ci[12, 1] - acf_sm[12], 4)
    isi("Keputusan", f"|r_12| = {fmt(abs(acf_sm[12]), 4)} > {fmt(batas12, 4)} → SIGNIFIKAN → pola musiman m = 12")

    pacf_sm = pacf(y, nlags=12, method="yw")
    # Yule-Walker 'yw' statsmodels memakai autokovariansi dengan pembagi (n − k)
    acov = np.array([(dev[:n - k_] * dev[k_:]).sum() / (n - k_) for k_ in range(13)])
    rho = acov / acov[0]
    phi22 = (rho[2] - rho[1] ** 2) / (1 - rho[1] ** 2)
    R = np.array([[rho[abs(i - j)] for j in range(12)] for i in range(12)])
    phi_12 = np.linalg.solve(R, rho[1:13])[-1]
    sub("5b. PACF metode Yule-Walker")
    rumus("ρ*_k = [Σ (y_t−ȳ)(y_(t+k)−ȳ) / (n−k)] / [Σ (y_t−ȳ)² / n]   (autokorelasi Yule-Walker)")
    lanjut("PACF lag 1 = ρ*_1 ;  PACF lag 2 = (ρ*_2 − ρ*_1²) / (1 − ρ*_1²)")
    lanjut("PACF lag k = koefisien terakhir dari sistem Yule-Walker R·φ = ρ (matriks k × k)")
    isi("ρ*_1", fmt(rho[1], 4))
    cek("PACF lag 1", rho[1], pacf_sm[1], 4)
    print("  ┌─ (lanjutan)")
    isi("PACF lag 2", f"({fmt(rho[2], 4)} − ({fmt(rho[1], 4)})²) / (1 − ({fmt(rho[1], 4)})²) = {fmt(phi22, 4)}")
    cek("PACF lag 2", phi22, pacf_sm[2], 4)
    print("  ┌─ (lanjutan)")
    isi("PACF lag 12", f"solusi sistem Yule-Walker 12×12 → {fmt(phi_12, 4)}")
    cek("PACF lag 12", phi_12, pacf_sm[12], 4)
    rumus("Batas signifikansi PACF = ± 1,96 / √n")
    isi("Batas", f"1,96 / √{n} = {fmt(1.96 / np.sqrt(n), 4)} → PACF lag 12 {fmt(pacf_sm[12], 4)} SIGNIFIKAN")
    akhir_bagian()


# =============================================================================
# [3] PEMBAGIAN DATA, [6] SKENARIO, [7] PEMILIHAN MODEL, [8] AIC/BIC (script 06)
# =============================================================================

def _logl_manual(res):
    """Log-likelihood Gaussian dari inovasi filter Kalman (setelah burn-in)."""
    fr = res.filter_results
    v = np.asarray(fr.forecasts_error[0])
    F = np.asarray(fr.forecasts_error_cov[0, 0])
    b = int(res.loglikelihood_burn)
    v, F = v[b:], F[b:]
    suku1 = -0.5 * (np.log(2 * np.pi) + np.log(F[0]) + v[0] ** 2 / F[0])
    total = float(np.sum(-0.5 * (np.log(2 * np.pi) + np.log(F) + v ** 2 / F)))
    return total, v[0], F[0], suku1, len(v)


def jelaskan_06(train_df, test_df, daftar_kandidat, df_hasil, fitted_models, y_kolom="Total_Kuantitas_Kg"):
    total = len(train_df) + len(test_df)
    kepala(3, "RUMUS PEMBAGIAN DATA (TRAIN-TEST SPLIT KRONOLOGIS)",
           "Script 06 · pembanding: data/hasil_06/06_training_set.csv dan 06_testing_set.csv")
    sub("3a. Pembagian 75% : 25% tanpa pengacakan")
    rumus("n_train = int(n × 0,75) ;  n_test = n − n_train")
    isi("n_train", f"int({total} × 0,75) = int({fmt(total * 0.75, 2)}) = {len(train_df)} bulan")
    isi("n_test", f"{total} − {len(train_df)} = {len(test_df)} bulan")
    isi("Training", f"{train_df.index[0]:%b %Y} – {train_df.index[-1]:%b %Y}")
    isi("Testing", f"{test_df.index[0]:%b %Y} – {test_df.index[-1]:%b %Y} (urutan waktu tetap)")
    cek("n_train", int(total * 0.75), len(train_df), 0, tol_abs=0)
    akhir_bagian()

    kepala(6, "PENETAPAN 4 SKENARIO PEMODELAN",
           "Pembanding: data/hasil_06/06_hasil_estimasi.csv (kolom Skenario, Eksogen)")
    sub("6a. Dasar penetapan skenario")
    baris("1. ARIMA      : kandidat orde (p,d,q) dari lag ACF/PACF (model_config.json), tanpa musiman.")
    baris("2. SARIMA     : ARIMA + komponen musiman m = 12 karena ACF/PACF lag 12 signifikan;")
    baris("                diuji D = 0 dan D = 1 (differencing musiman).")
    baris("3. ARIMAX     : ARIMA + variabel eksogen Harga_Rata2_Per_Kg.")
    baris("4. ARIMAX+Idul: ARIMA + Harga + label Iduladha (Koefisien_Musim).")
    hit = pd.Series([k["Skenario"] + (" + Iduladha" if len(k["exog"]) > 1 else "") for k in daftar_kandidat]).value_counts()
    for nama, jml in hit.items():
        isi(nama, f"{jml} kandidat")
    isi("Total", f"{len(daftar_kandidat)} kandidat model")
    akhir_bagian()

    kepala(8, "RUMUS AIC DAN BIC",
           "Pembanding: data/hasil_06/06_perbandingan_aic_bic.csv")
    valid = df_hasil[df_hasil["Status"] != "Gagal"]
    for kel, isi_kel in valid.groupby("Kelompok_Differencing"):
        nama = isi_kel.sort_values("AIC")["Nama_Model"].iloc[0]
        res = fitted_models[nama]
        ll, v1, F1, suku1, n_eff = _logl_manual(res)
        k = int(res.df_model)
        aic = -2 * ll + 2 * k
        bic = -2 * ll + k * np.log(n_eff)
        sub(f"8. Contoh kelompok {kel}: {nama}")
        rumus("Log-likelihood LL = Σ −½ [ ln(2π) + ln F_t + v_t² / F_t ]  (v = galat ramalan 1 langkah,")
        lanjut("F = variansnya, dari filter Kalman; dijumlah setelah burn-in)")
        lanjut("AIC = −2·LL + 2·k ;  BIC = −2·LL + k·ln(n_efektif)")
        isi("Suku ke-1", f"−½[ln(2π) + ln({fmt(F1, 6)}) + ({fmt(v1, 6)})² / {fmt(F1, 6)}] = {fmt(suku1, 6)}")
        isi("LL (jumlah n suku)", f"n_efektif = {n_eff} → LL = {fmt(ll, 4)}")
        cek("LL", ll, res.llf, 4)
        print("  ┌─ (lanjutan)")
        isi("k (parameter)", f"{k} → {', '.join(res.params.index)}")
        isi("AIC", f"−2 × ({fmt(ll, 4)}) + 2 × {k} = {fmt(aic, 4)}")
        cek("AIC", aic, res.aic, 4)
        print("  ┌─ (lanjutan)")
        isi("BIC", f"−2 × ({fmt(ll, 4)}) + {k} × ln({n_eff}) = {fmt(bic, 4)}")
        cek("BIC", bic, res.bic, 4)
    baris("Catatan: model dihitung pada ln(kg). AIC setara kg = AIC + 2·Σ ln y (koreksi Jacobian),")
    baris("hanya untuk membandingkan dengan versi skala kg; peringkat dalam kelompok tidak berubah.")
    akhir_bagian()

    kepala(7, "CARA MEMILIH MODEL",
           "Pembanding: 06_perbandingan_aic_bic.csv (Rank_AIC_Kelompok) dan 07_ringkasan_validasi.md")
    sub("7a. Tahap 06: peringkat AIC/BIC HANYA di dalam kelompok differencing (d, D) yang sama")
    baris("Alasan: model D=0 dan D=1 menghitung likelihood pada data berbeda (y vs Δ₁₂y),")
    baris("sehingga AIC/BIC tidak boleh dibandingkan lintas kelompok.")
    for kel, isi_kel in valid.groupby("Kelompok_Differencing"):
        top = isi_kel.sort_values("AIC").head(3)
        baris(f"Kelompok {kel}:")
        for _, r in top.iterrows():
            baris(f"   #{int(r['Rank_AIC_Kelompok'])} {r['Nama_Model']:<36} AIC {fmt(r['AIC'], 4)} "
                  f"(Δ {fmt(r['Delta_AIC_Kelompok'], 4)})")
    sub("7b. Tahap 07: shortlist & model final")
    baris("1. Shortlist = AIC terendah per skenario dalam kelompoknya (5 model).")
    baris("2. Model final = lulus Ljung-Box DAN Shapiro-Wilk, lebih baik dari seasonal naive,")
    baris("   lalu MAPE rolling origin terendah (lihat bagian [9] di script 07).")
    akhir_bagian()


# =============================================================================
# [9] VALIDASI DIAGNOSTIK & EVALUASI (script 07)
# =============================================================================

def _shapiro_manual(x):
    """Statistik W Shapiro-Wilk dengan koefisien a_i pendekatan Royston (1992)."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    m = stats.norm.ppf((np.arange(1, n + 1) - 0.375) / (n + 0.25))
    mm = m @ m
    c = m / np.sqrt(mm)
    u = 1 / np.sqrt(n)
    a = np.zeros(n)
    a[-1] = c[-1] + 0.221157 * u - 0.147981 * u ** 2 - 2.071190 * u ** 3 + 4.434685 * u ** 4 - 2.706056 * u ** 5
    a[-2] = c[-2] + 0.042981 * u - 0.293762 * u ** 2 - 1.752461 * u ** 3 + 5.682633 * u ** 4 - 3.582633 * u ** 5
    phi = (mm - 2 * m[-1] ** 2 - 2 * m[-2] ** 2) / (1 - 2 * a[-1] ** 2 - 2 * a[-2] ** 2)
    a[2:-2] = m[2:-2] / np.sqrt(phi)
    a[0], a[1] = -a[-1], -a[-2]
    b = a @ x
    ss = ((x - x.mean()) ** 2).sum()
    return b ** 2 / ss, a, x, b, ss


def _ramalan_1_langkah(ln, params):
    """ln y_hat(T+1) = ln y(T−11) + φ·w_T + Φ·w_(T−11) − φΦ·w_(T−12)."""
    phi, Phi = params["ar.L1"], params["ar.S.L12"]
    T = len(ln) - 1
    w = lambda t: ln[t] - ln[t - 12]
    wT, w11, w12 = w(T), w(T - 11), w(T - 12)
    lnhat = ln[T - 11] + phi * wT + Phi * w11 - phi * Phi * w12
    return lnhat, wT, w11, w12, ln[T - 11]


def jelaskan_07(train, test, shortlist, hasil_fit, df_diag, df_roll, df_metrik,
                label_final="SARIMA D=1", target_col="Total_Kuantitas_Kg", lags=(6, 9, 12)):
    s = next(x for x in shortlist if x["Label"] == label_final)
    res = hasil_fit[s["Nama_Model"]]
    burn = int(res.loglikelihood_burn)
    e = np.asarray(res.resid)[burn:]
    n = len(e)
    p, _, q = s["order"]
    P, _, Q, _ = s["seasonal_order"]
    model_df = p + q + P + Q
    diag = df_diag.set_index("Label").loc[label_final]

    kepala(9, f"VALIDASI DIAGNOSTIK & EVALUASI KINERJA — model {s['Nama_Model']} (log)",
           "Script 07 · pembanding: data/hasil_07/07_diagnostik_residual.csv, 07_metrik_rolling_origin.csv")

    # Ljung-Box
    h = lags[0]
    eb = e - e.mean()
    den = (eb ** 2).sum()
    r = np.array([(eb[:-k] * eb[k:]).sum() / den for k in range(1, h + 1)])
    Qs = n * (n + 2) * np.sum(r ** 2 / (n - np.arange(1, h + 1)))
    df_lb = h - model_df
    pval = 1 - stats.chi2.cdf(Qs, df_lb)
    sub(f"9a. Uji Ljung-Box (white noise residual), lag h = {h}")
    rumus("Q = n(n + 2) Σ_(k=1..h) r_k² / (n − k) ;  df = h − (p + q + P + Q) ;  p = P(χ²_df > Q)")
    isi("Residual", f"{n} nilai setelah burn-in {burn} bulan; e₁ = {fmt(e[0], 6)}")
    isi("r₁ … r₆", ", ".join(fmt(v, 4) for v in r))
    isi("Q", f"{n} × {n + 2} × Σ r_k²/(n − k) = {fmt(Qs, 4)}")
    isi("df", f"{h} − {model_df} = {df_lb}")
    isi("Nilai kritis χ²(0,05)", f"{fmt(stats.chi2.ppf(0.95, df_lb), 4)} → Q {'<' if Qs < stats.chi2.ppf(0.95, df_lb) else '>'} kritis")
    isi("p-value", f"{fmt(pval, 4)} {'> 0,05 → LULUS (white noise)' if pval > 0.05 else '< 0,05 → GAGAL'}")
    cek(f"Q lag {h}", Qs, diag[f"LB_Q_lag{h}"], 4)
    print("  ┌─ (lanjutan)")
    cek(f"p lag {h}", pval, diag[f"LB_p_lag{h}"], 4)

    # Shapiro-Wilk
    W, a, x, b, ss = _shapiro_manual(e)
    sub("9b. Uji Shapiro-Wilk (normalitas residual)")
    rumus("W = (Σ a_i · x_(i))² / Σ (x_i − x̄)²   (x_(i) = residual terurut, a_i = bobot normal)")
    isi("Pasangan ke-1 (ujung)", f"a_n = {fmt(a[-1], 4)} × ({fmt(x[-1], 6)} − {fp(x[0], 6)})")
    isi("b = Σ a_i x_(i)", fmt(b, 6))
    isi("SS = Σ(x − x̄)²", fmt(ss, 6))
    isi("W", f"{fmt(b, 6)}² / {fmt(ss, 6)} = {fmt(W, 4)}")
    cek("W", W, diag["Shapiro_W"], 3, tol_abs=0.002)
    isi("p-value (scipy)", f"{fmt(diag['Shapiro_p'], 4)} {'> 0,05 → LULUS (normal)' if diag['Shapiro_p'] > 0.05 else '< 0,05 → GAGAL'}")

    # Q-Q plot
    pp = np.arange(1, n + 1) / (n + 1)
    z = stats.norm.ppf(pp)
    sub("9c. Inspeksi Q-Q plot (titik pertama)")
    rumus("Peluang plot p_i = i / (n + 1) ;  kuantil teoritis z_i = Φ⁻¹(p_i) ;  garis acuan: x̄ + s·z")
    isi("Titik i = 1", f"p₁ = 1/{n + 1} = {fmt(pp[0], 4)} → z₁ = {fmt(z[0], 4)} ; residual terkecil = {fmt(x[0], 6)}")
    isi("Garis acuan di z₁", f"{fmt(x.mean(), 6)} + {fmt(x.std(ddof=1), 6)} × {fp(z[0], 4)} = "
        f"{fmt(x.mean() + x.std(ddof=1) * z[0], 6)}")
    baris("Titik yang menempel garis = residual normal. Plot: data/hasil_07/grafik/07_qq_*.png")

    # Rolling origin
    roll = df_roll[df_roll["Label"] == label_final].sort_values("Putaran")
    r1 = roll.iloc[0]
    ln_train = np.log(train[target_col].values.astype(float))
    lnhat, wT, w11, w12, ln_base = _ramalan_1_langkah(ln_train, res.params)
    phi, Phi = res.params["ar.L1"], res.params["ar.S.L12"]
    sub(f"9d. Time Series Cross-Validation (rolling origin) — putaran 1")
    baris(f"Putaran 1: latih {train.index[0]:%b %Y}–{train.index[-1]:%b %Y} ({len(train)} bulan) → ramal {r1['Periode_Target']}")
    baris("Putaran 2: tambah data aktual Apr 2025 → latih ulang → ramal Mei 2025, dst. (9 putaran)")
    rumus("w_t = ln y_t − ln y_(t−12) ;  ln ŷ_(T+1) = ln y_(T−11) + φ·w_T + Φ·w_(T−11) − φΦ·w_(T−12)")
    isi("φ, Φ", f"{fmt(phi, 6)} , {fmt(Phi, 6)}")
    isi("w_T, w_(T−11), w_(T−12)", f"{fmt(wT, 6)} , {fmt(w11, 6)} , {fmt(w12, 6)}")
    isi("ln ŷ", f"{fmt(ln_base, 6)} + {fp(phi, 4)}×{fp(wT, 6)} + {fp(Phi, 4)}×{fp(w11, 6)} − "
        f"{fp(phi * Phi, 4)}×{fp(w12, 6)} = {fmt(lnhat, 6)}")
    isi("ŷ = exp(ln ŷ)", f"{fmt(np.exp(lnhat))} kg ; aktual {fmt(r1['Aktual'])} kg")
    cek("ramalan putaran 1", np.exp(lnhat), r1["Prediksi"], 2, tol_rel=1e-6)

    # Metrik
    akt, pre = roll["Aktual"].values, roll["Prediksi"].values
    err = akt - pre
    nn = len(err)
    mae, mse = np.mean(np.abs(err)), np.mean(err ** 2)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs(err / akt)) * 100
    sse, sst = np.sum(err ** 2), np.sum((akt - akt.mean()) ** 2)
    r2 = 1 - sse / sst
    met = df_metrik.set_index("Label").loc[label_final]
    sub(f"9e. Metrik akurasi dari {nn} putaran rolling origin")
    isi("Bulan ke-1", f"e₁ = {fmt(akt[0])} − {fmt(pre[0])} = {fmt(err[0])} ; |e₁|/y₁ = {fmt(abs(err[0] / akt[0]) * 100, 2)}%")
    rumus("MAE = Σ|e| / n")
    isi("MAE", f"{fmt(np.abs(err).sum())} / {nn} = {fmt(mae)} kg")
    cek("MAE", mae, met["MAE"], 2)
    print("  ┌─"); rumus("MSE = Σe² / n ;  RMSE = √MSE")
    isi("MSE", f"{fmt(sse, 0)} / {nn} = {fmt(mse, 0)} kg²")
    isi("RMSE", f"√{fmt(mse, 0)} = {fmt(rmse)} kg")
    cek("RMSE", rmse, met["RMSE"], 2)
    print("  ┌─"); rumus("MAPE = (Σ |e / y| / n) × 100%")
    isi("MAPE", f"{fmt(np.sum(np.abs(err / akt)), 4)} / {nn} × 100% = {fmt(mape, 2)}%")
    cek("MAPE", mape, met["MAPE_%"], 4)
    print("  ┌─"); rumus("R² = 1 − SSE / SST ;  SSE = Σe² ;  SST = Σ(y − ȳ)²")
    isi("R²", f"1 − {fmt(sse, 0)} / {fmt(sst, 0)} = {fmt(r2, 4)}")
    cek("R²", r2, met["R2"], 4)
    sub("9f. Perbandingan dengan target penelitian (relatif terhadap rata-rata permintaan)")
    ybar = akt.mean()
    b_rmse, b_mae = 0.10 * ybar, 0.08 * ybar
    rumus("ȳ = Σy / n ;  RMSE < 10% × ȳ ;  MAE < 8% × ȳ ;  MSE < (10% × ȳ)²")
    isi("ȳ (rata-rata aktual)", f"{fmt(akt.sum())} / {nn} = {fmt(ybar)} kg")
    isi("Batas RMSE", f"10% × {fmt(ybar)} = {fmt(b_rmse)} kg")
    isi("Batas MAE", f"8% × {fmt(ybar)} = {fmt(b_mae)} kg")
    isi("Batas MSE", f"{fmt(b_rmse)}² = {fmt(b_rmse ** 2, 0)} kg²")
    for nama, nilai, syarat, ok in [
        ("MAPE", f"{fmt(mape, 2)}%", "< 15%", mape < 15),
        ("RMSE", f"{fmt(rmse)} kg", f"< {fmt(b_rmse, 0)} kg", rmse < b_rmse),
        ("MAE", f"{fmt(mae)} kg", f"< {fmt(b_mae, 0)} kg", mae < b_mae),
        ("MSE", f"{fmt(mse, 0)}", f"< {fmt(b_rmse ** 2, 0)}", mse < b_rmse ** 2),
        ("R²", fmt(r2, 4), "> 0,70", r2 > 0.70)]:
        isi(nama, f"{nilai:<18} target {syarat:<16} → {'LULUS' if ok else 'TIDAK LULUS'}")
    baris("Catatan: target RMSE/MAE/MSE dibuat relatif terhadap rata-rata permintaan karena data")
    baris("penelitian adalah agregat Kabupaten Malang (tidak dibagi jumlah UMKM yang tidak pasti).")
    akhir_bagian()


# =============================================================================
# [9] RAMALAN MULTI-STEP DATA TESTING (script 08) DAN 2026 (script 09)
# =============================================================================

def _jelaskan_ramalan(ln, params, periode_awal, pred_csv, bawah_csv, atas_csv, aktual=None):
    phi, Phi, s2 = params["ar.L1"], params["ar.S.L12"], params["sigma2"]
    lnhat, wT, w11, w12, ln_base = _ramalan_1_langkah(ln, params)
    se1 = np.sqrt(s2)
    z = stats.norm.ppf(0.975)
    sub(f"Ramalan h = 1 ({periode_awal})")
    rumus("ln ŷ = ln y_(T−11) + φ·w_T + Φ·w_(T−11) − φΦ·w_(T−12) ;  ŷ = exp(ln ŷ)  (median ramalan)")
    isi("ln ŷ", f"{fmt(ln_base, 6)} + {fp(phi, 4)}×{fp(wT, 6)} + {fp(Phi, 4)}×{fp(w11, 6)} − "
        f"{fp(phi * Phi, 4)}×{fp(w12, 6)} = {fmt(lnhat, 6)}")
    isi("ŷ", f"exp({fmt(lnhat, 6)}) = {fmt(np.exp(lnhat))} kg")
    cek("ramalan h=1", np.exp(lnhat), pred_csv, 2)
    sub("Interval kepercayaan 95% (h = 1)")
    rumus("SE(h) = √( σ² × (1 − φ^(2h)) / (1 − φ²) ) ;  Batas = exp( ln ŷ ∓ 1,96 × SE )")
    isi("SE(1)", f"√{fmt(s2, 6)} = {fmt(se1, 6)}")
    isi("Margin of Error", f"1,96 × {fmt(se1, 6)} = {fmt(z * se1, 6)}")
    isi("Batas bawah", f"exp({fmt(lnhat, 6)} − {fmt(z * se1, 6)}) = {fmt(np.exp(lnhat - z * se1))} kg")
    isi("Batas atas", f"exp({fmt(lnhat, 6)} + {fmt(z * se1, 6)}) = {fmt(np.exp(lnhat + z * se1))} kg")
    cek("batas bawah", np.exp(lnhat - z * se1), bawah_csv, 2)
    print("  ┌─ (lanjutan)")
    cek("batas atas", np.exp(lnhat + z * se1), atas_csv, 2)
    se6 = np.sqrt(s2 * (1 - phi ** 12) / (1 - phi ** 2))
    baris(f"Efek corong: SE(6) = √({fmt(s2, 6)}×(1 − {fmt(phi, 4)}^12)/(1 − {fmt(phi, 4)}²)) = {fmt(se6, 6)} > SE(1)")
    if aktual is not None:
        baris(f"Aktual {fmt(aktual)} kg → error {fmt(aktual - np.exp(lnhat))} kg, "
              f"APE {fmt(abs(aktual - np.exp(lnhat)) / aktual * 100, 2)}%")


def jelaskan_08(train, test, df, df_eval, label_final="SARIMA D=1", target_col="Total_Kuantitas_Kg"):
    import estimasi_model as em
    kepala(9, "LANJUTAN — RAMALAN MULTI-STEP DATA TESTING (Apr–Des 2025)",
           "Script 08 · pembanding: data/hasil_08/08_peramalan_testing.csv, 08_evaluasi_peramalan.csv")
    data = em.skala_data(train)
    res, _ = em.fit_terbaik(data[target_col], None, (1, 0, 0), (1, 1, 0, 12))
    isi_m = df[df["Label"] == label_final].sort_values("Horizon")
    r1 = isi_m.iloc[0]
    _jelaskan_ramalan(np.log(train[target_col].values.astype(float)), res.params, r1["Periode"],
                      r1["Prediksi_Kg"], r1["Batas_Bawah_95_Kg"], r1["Batas_Atas_95_Kg"], r1["Aktual_Kg"])
    sub("Cakupan interval dan MAPE 9 bulan")
    rumus("Cakupan = banyak aktual di dalam interval / banyak bulan ;  MAPE = Σ|e/y| / n × 100%")
    n_in = int((isi_m["Dalam_CI_95"] == "Ya").sum())
    mape = isi_m["APE_%"].mean()
    isi("Cakupan", f"{n_in} / {len(isi_m)} = {fmt(n_in / len(isi_m) * 100, 2)}%")
    isi("MAPE", f"{fmt(isi_m['APE_%'].sum(), 4)} / {len(isi_m)} = {fmt(mape, 2)}%")
    cek("MAPE", mape, df_eval.set_index("Label").loc[label_final, "MAPE_%"], 4)
    akhir_bagian()


def jelaskan_09(data_penuh, result, df, target_col="Total_Kuantitas_Kg"):
    kepala(9, "LANJUTAN — RAMALAN 6 BULAN KE DEPAN (Jan–Jun 2026)",
           "Script 09 · pembanding: data/hasil_09/09_peramalan_jan_jun_2026.csv, 09_fan_chart.png")
    baris(f"Parameter dikunci dari fit {len(data_penuh)} bulan (Jan 2023–Des 2025).")
    r1 = df.iloc[0]
    _jelaskan_ramalan(np.log(data_penuh[target_col].values.astype(float)), result.params, r1["Periode"],
                      r1["Yhat_Kg"], r1["Batas_Bawah_95_Kg"], r1["Batas_Atas_95_Kg"])
    baris("h = 2 … 6: w ramalan sebelumnya dipakai lagi (rekursif); SE(h) membesar → pita melebar.")
    akhir_bagian()
