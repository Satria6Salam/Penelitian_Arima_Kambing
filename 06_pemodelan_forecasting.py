"""
=============================================================================
PROGRAM PEMODELAN ARIMA, SARIMA, DAN ARIMAX (REVISI)
File: 06_pemodelan_forecasting.py
Perbandingan dengan versi sebelumnya: perbandingan_versi_estimasi.md

Ruang Lingkup Tahapan:
1. Memuat dataset historis dan melakukan Train-Test Split kronologis.
2. Memuat parameter hasil eksplorasi dari model_config.json.
3. Menetapkan skenario pemodelan komparatif:
   - ARIMA
   - SARIMA (tanpa variabel eksogen, sebagai pembanding)
   - ARIMAX (variabel eksogen Harga_Rata2_Per_Kg [+ label Iduladha])
4. Melatih seluruh kandidat dengan SARIMAX Statsmodels secara konsisten:
   enforce_stationarity=True dan enforce_invertibility=True.
5. Membandingkan AIC dan BIC HANYA di dalam kelompok differencing (d, D)
   yang sama. Tidak ada peringkat gabungan dan tidak ada model final.

PERUBAHAN UTAMA DARI VERSI LAMA:
- enforce_stationarity / enforce_invertibility diubah menjadi True.
  Pada versi lama (False) statsmodels memakai inisialisasi diffuse untuk
  seluruh state, sehingga loglikelihood_burn sangat besar dan
  log-likelihood SARIMA D=1 hanya dihitung dari 1-2 observasi.
- Seluruh skenario diestimasi dengan kelas SARIMAX yang sama.
- nobs, nobs_effective, loglikelihood_burn diambil dari hasil Statsmodels.
- Peringatan untuk model dengan observasi efektif terlalu sedikit.
- Perbandingan AIC/BIC dikelompokkan berdasarkan (d, D).
- Hasil disimpan ke file BARU; dataset asli dan hasil lama tidak ditimpa.

REVISI TRANSFORMASI DAN MULTI-OPTIMIZER:
- Di dalam script, data ditransformasi sebelum estimasi (file data tidak
  diubah); pengaturan di estimasi_model.TRANSFORMASI. Versi final memakai
  transformasi log (ln kg, ln Rp/kg): pada skala kg optimizer L-BFGS sering
  berhenti di optimum lokal, dan lonjakan Iduladha yang bersifat perkalian
  membuat residual model level tidak normal.
- Setiap kandidat di-fit dengan lbfgs, bfgs, powell, nm; dipilih LogL
  tertinggi dengan std error valid, lalu di-polish dengan lbfgs
  (modul estimasi_model.py, dipakai bersama script 07).
- Pengecekan model bersarang: model yang lebih kompleks tidak boleh memiliki
  LogL lebih rendah dari model sederhana yang tercakup di dalamnya.

CATATAN:
Diagnostik residual, Ljung-Box, dan evaluasi data testing dikerjakan di
script 07; peramalan data testing (Apr-Des 2025) dikerjakan di script 08.
=============================================================================
"""

import json
import warnings
import numpy as np
import pandas as pd
import statsmodels

from pathlib import Path

import keterangan_csv as kk  # keterangan kolom pada setiap CSV hasil
import estimasi_model as em
import penjelasan  # contoh perhitungan rumus di terminal + log_terminal/


# =============================================================================
# PENGATURAN PATH DIREKTORI
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_CSV = DATA_DIR / "olah" / "dataset_pra_proses_final.csv"
CONFIG_JSON = DATA_DIR / "eksplorasi" / "model_config.json"
OUTPUT_DIR = DATA_DIR / "hasil_06"

# Output BARU (tidak menimpa training_set.csv, testing_set.csv,
# maupun perbandingan_aic_bic.csv dari versi lama)
TRAIN_CSV = OUTPUT_DIR / "06_training_set.csv"
TEST_CSV = OUTPUT_DIR / "06_testing_set.csv"
HASIL_ESTIMASI_CSV = OUTPUT_DIR / "06_hasil_estimasi.csv"
HASIL_AIC_BIC_CSV = OUTPUT_DIR / "06_perbandingan_aic_bic.csv"
BERSARANG_CSV = OUTPUT_DIR / "06_cek_model_bersarang.csv"
RINGKASAN_MD = BASE_DIR / "06_ringkasan_aic_bic.md"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# KONSTANTA PENELITIAN
# =============================================================================

TRAIN_RATIO = 0.75

TARGET_COL = "Total_Kuantitas_Kg"
PRICE_COL = "Harga_Rata2_Per_Kg"

# Label Iduladha yang sudah tersedia (dikonfirmasi peneliti):
# kolom Koefisien_Musim pada volume_bulanan.csv (1,000 = bulan biasa,
# 2,717 = bulan Iduladha). Kolom dipakai apa adanya dan hanya digabung
# ke dataset di memori berdasarkan Periode; file asli tidak diubah dan
# script TIDAK membuat dummy baru. Isi None untuk menonaktifkan.
IDULADHA_CSV = DATA_DIR / "hasil_generate" / "volume_bulanan.csv"
IDULADHA_COL = "Koefisien_Musim"

# Pengaturan estimasi (dipakai seragam untuk semua kandidat; lihat estimasi_model.py)
ENFORCE_STATIONARITY = em.ENFORCE_STATIONARITY
ENFORCE_INVERTIBILITY = em.ENFORCE_INVERTIBILITY

# Toleransi pelanggaran model bersarang (LogL)
TOLERANSI_BERSARANG = 1e-3

# Ambang peringatan observasi efektif.
# Peringatan muncul jika nobs_effective < MIN_NOBS_EFEKTIF
# atau nobs_effective < RASIO_NOBS_PER_PARAMETER x jumlah parameter.
MIN_NOBS_EFEKTIF = 20
RASIO_NOBS_PER_PARAMETER = 10


# =============================================================================
# FUNGSI BANTUAN: MEMUAT DAN MEMVALIDASI KONFIGURASI
# =============================================================================

def muat_konfigurasi(config_filepath):
    """
    Memuat konfigurasi hasil eksplorasi dari model_config.json.
    """

    if not config_filepath.exists():
        raise FileNotFoundError(
            f"File konfigurasi tidak ditemukan: {config_filepath}"
        )

    with open(config_filepath, "r", encoding="utf-8") as file:
        config = json.load(file)

    d_locked = int(config.get("derajat_pembedaan_non_musiman_d", 0))
    D_config = int(config.get("derajat_pembedaan_musiman_D", 0))
    m = int(config.get("periode_musiman_m", 12))

    kandidat_arima = config.get("daftar_kandidat_p_d_q", [])

    if not kandidat_arima:
        raise ValueError(
            "Daftar kandidat ARIMA tidak ditemukan dalam model_config.json."
        )

    kandidat_sarima = config.get("daftar_kandidat_sarima", [])

    # Validasi kandidat ARIMA
    kandidat_arima_valid = []

    for kandidat in kandidat_arima:

        if len(kandidat) != 3:
            raise ValueError(f"Format kandidat ARIMA tidak valid: {kandidat}")

        kandidat_arima_valid.append(tuple(map(int, kandidat)))

    # Validasi kandidat SARIMA (format dict terbaru atau list lama)
    kandidat_sarima_valid = []

    for kandidat in kandidat_sarima:

        if isinstance(kandidat, dict):
            order = tuple(map(int, kandidat["order"]))
            seasonal_order = tuple(map(int, kandidat["seasonal_order"]))

        elif isinstance(kandidat, (list, tuple)) and len(kandidat) == 2:
            order = tuple(map(int, kandidat[0]))
            seasonal_order = tuple(map(int, kandidat[1]))

        else:
            raise ValueError(
                f"Format kandidat SARIMA tidak dikenali: {kandidat}"
            )

        if len(order) != 3 or len(seasonal_order) != 4:
            raise ValueError(f"Orde SARIMA tidak lengkap: {kandidat}")

        if seasonal_order[3] <= 1:
            raise ValueError(f"Periode musiman tidak valid: {seasonal_order}")

        kandidat_sarima_valid.append((order, seasonal_order))

    return {
        "d": d_locked,
        "D": D_config,
        "m": m,
        "kandidat_arima": kandidat_arima_valid,
        "kandidat_sarima": kandidat_sarima_valid
    }


# =============================================================================
# FUNGSI BANTUAN: PEMERIKSAAN LABEL IDULADHA
# =============================================================================

def gabungkan_label_iduladha(df):
    """
    Menggabungkan label Iduladha yang sudah tersedia ke dataset (di memori).

    Label diambil apa adanya dari IDULADHA_CSV kolom IDULADHA_COL dan
    dicocokkan berdasarkan Periode. Fungsi ini tidak membuat label baru
    dan tidak mengubah file mana pun.
    """

    print("\n[LABEL IDULADHA]")

    if IDULADHA_COL is None:
        print("IDULADHA_COL           : None (label Iduladha tidak dipakai)")
        return df, None

    if not IDULADHA_CSV.exists():
        raise FileNotFoundError(f"File label Iduladha tidak ditemukan: {IDULADHA_CSV}")

    df_label = kk.baca_csv(IDULADHA_CSV)

    for kolom in ["Periode", IDULADHA_COL]:
        if kolom not in df_label.columns:
            raise ValueError(
                f"Kolom '{kolom}' tidak ada di {IDULADHA_CSV.name}. "
                "Script tidak membuat label pengganti."
            )

    df_label["Periode"] = pd.to_datetime(df_label["Periode"], errors="coerce")

    if df_label["Periode"].isna().any() or df_label["Periode"].duplicated().any():
        raise ValueError(
            f"Kolom Periode di {IDULADHA_CSV.name} tidak valid atau duplikat."
        )

    label = df_label.set_index("Periode")[IDULADHA_COL].astype(float)

    periode_hilang = df.index.difference(label.index)

    if len(periode_hilang) > 0:
        raise ValueError(
            f"Label Iduladha tidak tersedia untuk {len(periode_hilang)} periode: "
            f"{', '.join(p.strftime('%Y-%m') for p in periode_hilang)}"
        )

    df = df.join(label, how="left")

    bulan_iduladha = df.index[df[IDULADHA_COL] != df[IDULADHA_COL].min()]

    print(f"Sumber                 : {IDULADHA_CSV.name}, kolom {IDULADHA_COL}")
    print(f"Nilai unik             : {sorted(df[IDULADHA_COL].unique().tolist())}")
    print(
        "Periode bernilai beda  : "
        f"{', '.join(p.strftime('%Y-%m') for p in bulan_iduladha)}"
    )

    return df, IDULADHA_COL


# =============================================================================
# FUNGSI 1: PEMBAGIAN KRONOLOGIS DATASET (TRAIN-TEST SPLIT)
# =============================================================================

def pemecahan_dan_ekspor_dataset(
    csv_filepath,
    config_filepath,
    train_ratio=TRAIN_RATIO
):
    """
    Memuat dataset dan melakukan pembagian kronologis.

    Training : 75% data awal.
    Testing  : 25% data akhir (hanya disimpan, tidak dievaluasi di script ini).
    """

    print("\n" + "=" * 75)
    print("TAHAP 1: PEMBAGIAN KRONOLOGIS DATASET (TRAIN-TEST SPLIT)")
    print("=" * 75)

    if not csv_filepath.exists():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {csv_filepath}")

    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio harus berada di antara 0 dan 1.")

    config = muat_konfigurasi(config_filepath)

    df = kk.baca_csv(csv_filepath)

    for kolom in ["Periode", TARGET_COL, PRICE_COL]:
        if kolom not in df.columns:
            raise ValueError(
                f"Kolom wajib '{kolom}' tidak ditemukan dalam dataset."
            )

    df["Periode"] = pd.to_datetime(df["Periode"], errors="coerce")

    if df["Periode"].isna().any():
        raise ValueError(
            "Terdapat nilai tanggal yang tidak valid pada kolom Periode."
        )

    df = df.sort_values("Periode")

    if df["Periode"].duplicated().any():
        raise ValueError("Terdapat periode bulanan yang duplikat.")

    df = df.set_index("Periode").asfreq("MS")

    df, kolom_iduladha = gabungkan_label_iduladha(df)

    kolom_cek = [TARGET_COL, PRICE_COL] + (
        [kolom_iduladha] if kolom_iduladha else []
    )

    if df[kolom_cek].isna().any().any():
        raise ValueError(
            "Terdapat nilai kosong pada variabel target/eksogen "
            "setelah validasi frekuensi bulanan. Periksa kembali dataset."
        )

    total_obs = len(df)

    if total_obs < 12:
        raise ValueError("Jumlah observasi terlalu sedikit untuk pemodelan.")

    train_size = int(total_obs * train_ratio)

    if train_size <= 0 or train_size >= total_obs:
        raise ValueError("Ukuran training atau testing tidak valid.")

    train_df = df.iloc[:train_size].copy()
    test_df = df.iloc[train_size:].copy()

    kk.simpan_csv(train_df.reset_index(), TRAIN_CSV, index=False)
    kk.simpan_csv(test_df.reset_index(), TEST_CSV, index=False)

    print("\n[INFORMASI DATASET]")
    print(f"Jumlah observasi       : {total_obs}")
    print(f"Periode awal           : {df.index.min().date()}")
    print(f"Periode akhir          : {df.index.max().date()}")
    print(f"Frekuensi              : {df.index.freqstr}")

    print("\n[HASIL TRAIN-TEST SPLIT]")
    print(
        f"Training Set           : {len(train_df)} observasi "
        f"({train_df.index[0].strftime('%b %Y')} - "
        f"{train_df.index[-1].strftime('%b %Y')})"
    )
    print(
        f"Testing Set            : {len(test_df)} observasi "
        f"({test_df.index[0].strftime('%b %Y')} - "
        f"{test_df.index[-1].strftime('%b %Y')})"
    )
    print(f"Rasio Training         : {train_ratio * 100:.0f}%")
    print(f"Rasio Testing          : {(1 - train_ratio) * 100:.0f}%")

    print("\n[VARIABEL PENELITIAN]")
    print(f"Variabel target        : {TARGET_COL}")
    print(f"Variabel eksogen       : {PRICE_COL}")
    print(
        "Label Iduladha         : "
        f"{kolom_iduladha if kolom_iduladha else 'tidak dipakai (belum tersedia)'}"
    )

    print("\n[EKSPOR DATASET]")
    print(f"Training Set           : {TRAIN_CSV}")
    print(f"Testing Set            : {TEST_CSV}")

    config["kolom_iduladha"] = kolom_iduladha

    return train_df, test_df, config


# =============================================================================
# FUNGSI 2: MENETAPKAN SKENARIO PEMODELAN
# =============================================================================

def tetapkan_skenario_pemodelan(config):
    """
    Menetapkan daftar kandidat untuk setiap skenario.

    Setiap kandidat berisi: skenario, nama, order, seasonal_order,
    dan daftar kolom eksogen.
    """

    m = config["m"]
    kandidat_arima = config["kandidat_arima"]
    kandidat_sarima = config["kandidat_sarima"]
    kolom_iduladha = config["kolom_iduladha"]

    print("\n" + "=" * 75)
    print("TAHAP 2-3: PEMUATAN PARAMETER DAN PENETAPAN SKENARIO")
    print("=" * 75)

    print("\n[PARAMETER HASIL EKSPLORASI DATA]")
    print(f"Derajat differencing d : {config['d']}")
    print(f"Differencing musiman D : {config['D']} (nilai di model_config.json)")
    print(f"Periode musiman m      : {m}")

    D_kandidat = sorted({so[1] for _, so in kandidat_sarima})

    if any(D != config["D"] for D in D_kandidat):
        print(
            f"Catatan: kandidat SARIMA memuat D = {D_kandidat}, berbeda dari "
            f"D = {config['D']} di konfigurasi. Kandidat dengan D berbeda "
            "dibandingkan dalam kelompok terpisah."
        )

    daftar = []

    # Skenario 1: ARIMA
    for order in kandidat_arima:
        daftar.append({
            "Skenario": "ARIMA",
            "Nama_Model": f"ARIMA{order}",
            "order": order,
            "seasonal_order": (0, 0, 0, 0),
            "exog": []
        })

    # Skenario 2: SARIMA tanpa eksogen (model pembanding)
    for order, seasonal_order in kandidat_sarima:
        daftar.append({
            "Skenario": "SARIMA",
            "Nama_Model": f"SARIMA{order}x{seasonal_order}",
            "order": order,
            "seasonal_order": seasonal_order,
            "exog": []
        })

    # Skenario 3a: ARIMAX dengan harga
    for order in kandidat_arima:
        daftar.append({
            "Skenario": "ARIMAX",
            "Nama_Model": f"ARIMAX{order} + Harga",
            "order": order,
            "seasonal_order": (0, 0, 0, 0),
            "exog": [PRICE_COL]
        })

    # Skenario 3b: ARIMAX dengan harga + label Iduladha (hanya bila tersedia)
    if kolom_iduladha:
        for order in kandidat_arima:
            daftar.append({
                "Skenario": "ARIMAX",
                "Nama_Model": f"ARIMAX{order} + Harga + Iduladha",
                "order": order,
                "seasonal_order": (0, 0, 0, 0),
                "exog": [PRICE_COL, kolom_iduladha]
            })

    for skenario in ["ARIMA", "SARIMA", "ARIMAX"]:
        anggota = [k for k in daftar if k["Skenario"] == skenario]
        print("\n" + "-" * 75)
        print(f"SKENARIO {skenario}: {len(anggota)} kandidat")
        print("-" * 75)
        for i, k in enumerate(anggota, start=1):
            eksogen = ", ".join(k["exog"]) if k["exog"] else "-"
            print(f"{i}. {k['Nama_Model']:<38} eksogen: {eksogen}")

    print(f"\nTOTAL kandidat model individual: {len(daftar)}")

    return daftar


# =============================================================================
# FUNGSI BANTUAN: KONVERGENSI DAN PERINGATAN OBSERVASI EFEKTIF
# =============================================================================

def periksa_konvergensi(result):
    """
    Mengambil status konvergensi dari mle_retvals hasil Statsmodels.
    """

    mle_retvals = getattr(result, "mle_retvals", None)

    if isinstance(mle_retvals, dict):
        converged = mle_retvals.get("converged")
        if converged is not None:
            return bool(converged)

    return None


def peringatan_nobs_efektif(nobs_effective, jumlah_parameter):
    """
    Memberi peringatan jika jumlah observasi efektif terlalu sedikit.
    """

    catatan = []

    if nobs_effective < MIN_NOBS_EFEKTIF:
        catatan.append(f"nobs_effective {nobs_effective} < {MIN_NOBS_EFEKTIF}")

    if nobs_effective < RASIO_NOBS_PER_PARAMETER * jumlah_parameter:
        catatan.append(
            f"nobs_effective {nobs_effective} < "
            f"{RASIO_NOBS_PER_PARAMETER} x {jumlah_parameter} parameter"
        )

    return "; ".join(catatan) if catatan else "-"


# =============================================================================
# FUNGSI 4: FITTING SELURUH KANDIDAT MODEL
# =============================================================================

def latih_semua_kandidat(train_df, daftar_kandidat):
    """
    Melatih seluruh kandidat dengan SARIMAX menggunakan Training Set.

    Semua nilai (nobs, nobs_effective, loglikelihood_burn, llf, AIC, BIC)
    diambil langsung dari objek hasil estimasi yang baru di-fit.
    """

    print("\n" + "=" * 75)
    print("TAHAP 4: PELATIHAN SELURUH KANDIDAT MODEL (FITTING)")
    print("=" * 75)
    print(f"enforce_stationarity   : {ENFORCE_STATIONARITY}")
    print(f"enforce_invertibility  : {ENFORCE_INVERTIBILITY}")
    print(f"Transformasi           : {em.TRANSFORMASI} ({em.DESKRIPSI_TRANSFORMASI})")
    print(f"Optimizer              : {', '.join(m for m, _ in em.OPTIMIZER)} + polish lbfgs")

    data_skala = em.skala_data(train_df)
    y_train = data_skala[TARGET_COL]

    fitted_models = {}
    hasil_estimasi = []

    for nomor, kandidat in enumerate(daftar_kandidat, start=1):

        order = kandidat["order"]
        seasonal_order = kandidat["seasonal_order"]
        nama_model = kandidat["Nama_Model"]
        d, D = order[1], seasonal_order[1]

        print(f"\n[{nomor}/{len(daftar_kandidat)}] {nama_model}")

        baris = {
            "Skenario": kandidat["Skenario"],
            "Nama_Model": nama_model,
            "Order": str(order),
            "Seasonal_Order": str(seasonal_order),
            "Eksogen": ", ".join(kandidat["exog"]) if kandidat["exog"] else "-",
            "d": d,
            "D": D,
            "Kelompok_Differencing": f"d={d}, D={D}",
        }

        x_train = (
            data_skala[kandidat["exog"]].astype(float)
            if kandidat["exog"] else None
        )

        try:
            result, info_fit = em.fit_terbaik(y_train, x_train, order, seasonal_order)

            if not np.isfinite(result.llf):
                raise ValueError("Log-likelihood tidak terhingga (non-finite).")

            converged = periksa_konvergensi(result)

            nobs = int(result.nobs)
            nobs_effective = int(result.nobs_effective)
            burn = int(result.loglikelihood_burn)
            jumlah_parameter = int(result.df_model)

            fitted_models[nama_model] = result

            baris.update({
                "nobs": nobs,
                "nobs_effective": nobs_effective,
                "loglikelihood_burn": burn,
                "Jumlah_Parameter": jumlah_parameter,
                "Log_Likelihood": float(result.llf),
                "AIC": float(result.aic),
                "BIC": float(result.bic),
                "Transformasi": em.TRANSFORMASI,
                "LogL_setara_kg": em.logl_setara_kg(result, train_df[TARGET_COL]),
                "AIC_setara_kg": em.aic_setara_kg(result, train_df[TARGET_COL]),
                "BIC_setara_kg": em.bic_setara_kg(result, train_df[TARGET_COL]),
                **{k: v for k, v in info_fit.items() if k.startswith("LogL_")},
                "Optimizer_Terpilih": info_fit["Optimizer_Terpilih"],
                "Dipoles_lbfgs": info_fit["Dipoles_lbfgs"],
                "SE_Valid": info_fit["SE_Valid"],
                "Konvergen": converged,
                "Status": (
                    "Berhasil (tidak konvergen)" if converged is False
                    else "Berhasil (std error tidak valid)" if not info_fit["SE_Valid"]
                    else "Berhasil"
                ),
                "Peringatan_Observasi": peringatan_nobs_efektif(
                    nobs_effective, jumlah_parameter
                ),
                "Warning": info_fit["Warning"],
                "Penyebab_Gagal": "-",
            })

            print(f"Status          : {baris['Status']}")
            print(f"nobs / efektif  : {nobs} / {nobs_effective} (burn {burn})")
            print(f"Jumlah parameter: {jumlah_parameter}")
            print(f"Log-Likelihood  : {result.llf:.4f}")
            print(f"AIC             : {result.aic:.4f}")
            print(f"BIC             : {result.bic:.4f}")
            print(f"Optimizer       : {info_fit['Optimizer_Terpilih']} "
                  f"(polish lbfgs: {info_fit['Dipoles_lbfgs']}, SE valid: {info_fit['SE_Valid']})")
            print(f"Konvergen       : {converged}")

            if baris["Peringatan_Observasi"] != "-":
                print(f"PERINGATAN      : {baris['Peringatan_Observasi']}")

            if info_fit["Warning"] != "-":
                for pesan in info_fit["Warning"].split(" | "):
                    print(f"Warning         : {pesan}")

        except Exception as e:

            print("Status          : GAGAL")
            print(f"Penyebab        : {type(e).__name__}: {e}")

            baris.update({
                "nobs": len(y_train),
                "nobs_effective": None,
                "loglikelihood_burn": None,
                "Jumlah_Parameter": None,
                "Log_Likelihood": None,
                "AIC": None,
                "BIC": None,
                "Konvergen": False,
                "Status": "Gagal",
                "Peringatan_Observasi": "-",
                "Warning": "-",
                "Penyebab_Gagal": f"{type(e).__name__}: {e}",
            })

        hasil_estimasi.append(baris)

    df_estimasi = pd.DataFrame(hasil_estimasi)
    kk.simpan_csv(df_estimasi, HASIL_ESTIMASI_CSV, index=False)

    print("\n" + "=" * 75)
    print("RINGKASAN PROSES FITTING")
    print("=" * 75)

    jumlah_gagal = int((df_estimasi["Status"] == "Gagal").sum())

    print(f"Total kandidat       : {len(df_estimasi)}")
    print(f"Berhasil diestimasi  : {len(df_estimasi) - jumlah_gagal}")
    print(f"Gagal diestimasi     : {jumlah_gagal}")
    print(f"Hasil estimasi disimpan ke: {HASIL_ESTIMASI_CSV}")

    return fitted_models, df_estimasi


# =============================================================================
# FUNGSI 5: PERBANDINGAN AIC DAN BIC PER KELOMPOK DIFFERENCING
# =============================================================================

def bandingkan_aic_bic(df_estimasi):
    """
    Membandingkan AIC dan BIC di dalam setiap kelompok (d, D).

    Model dengan differencing berbeda memodelkan data berbeda
    (y vs Δ12 y) dengan jumlah observasi efektif berbeda, sehingga
    likelihood-nya tidak dapat dibandingkan. Karena itu tidak dibuat
    peringkat gabungan dan tidak ditetapkan model final.
    """

    print("\n" + "=" * 75)
    print("TAHAP 5: PERBANDINGAN AIC DAN BIC PER KELOMPOK DIFFERENCING (d, D)")
    print("=" * 75)

    df_valid = df_estimasi[
        (df_estimasi["Status"] != "Gagal")
        & df_estimasi["AIC"].notna()
        & df_estimasi["BIC"].notna()
    ].copy()

    if df_valid.empty:
        print("Tidak ada kandidat yang berhasil diestimasi.")
        kk.simpan_csv(df_estimasi, HASIL_AIC_BIC_CSV, index=False)
        return df_estimasi

    kelompok = df_valid.groupby("Kelompok_Differencing")

    df_valid["Rank_AIC_Kelompok"] = kelompok["AIC"].rank(method="min").astype(int)
    df_valid["Rank_BIC_Kelompok"] = kelompok["BIC"].rank(method="min").astype(int)
    df_valid["Delta_AIC_Kelompok"] = df_valid["AIC"] - kelompok["AIC"].transform("min")
    df_valid["Delta_BIC_Kelompok"] = df_valid["BIC"] - kelompok["BIC"].transform("min")

    # Dalam satu kelompok, nobs_effective harus sama agar AIC/BIC sebanding
    df_valid["Catatan_Kelompok"] = "-"

    for nama_kelompok, isi in kelompok:
        if isi["nobs_effective"].nunique() > 1:
            df_valid.loc[isi.index, "Catatan_Kelompok"] = (
                "nobs_effective berbeda dalam kelompok: "
                f"{sorted(isi['nobs_effective'].unique().tolist())}"
            )

    df_valid = df_valid.sort_values(
        ["Kelompok_Differencing", "Rank_AIC_Kelompok", "Nama_Model"]
    )

    kolom_tampil = [
        "Nama_Model", "nobs", "nobs_effective", "loglikelihood_burn",
        "Jumlah_Parameter", "Log_Likelihood", "AIC", "Delta_AIC_Kelompok",
        "BIC", "Delta_BIC_Kelompok", "Rank_AIC_Kelompok", "Rank_BIC_Kelompok",
        "Konvergen"
    ]

    for nama_kelompok, isi in df_valid.groupby("Kelompok_Differencing"):
        print("\n" + "-" * 75)
        print(f"KELOMPOK {nama_kelompok}  ({len(isi)} model)")
        print("-" * 75)
        print(
            isi[kolom_tampil].to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}"
            )
        )

        catatan = isi["Catatan_Kelompok"].unique()
        if catatan[0] != "-":
            print(f"CATATAN: {catatan[0]}")

        n_peringatan = int((isi["Peringatan_Observasi"] != "-").sum())
        if n_peringatan:
            print(
                f"PERINGATAN: {n_peringatan} model memiliki observasi efektif "
                "terlalu sedikit (lihat kolom Peringatan_Observasi)."
            )

    df_gagal = df_estimasi[df_estimasi["Status"] == "Gagal"]

    df_hasil = pd.concat([df_valid, df_gagal], ignore_index=True)
    kk.simpan_csv(df_hasil, HASIL_AIC_BIC_CSV, index=False)

    print("\nHasil perbandingan disimpan ke:")
    print(HASIL_AIC_BIC_CSV)

    print("\nCATATAN METODOLOGIS:")
    print("- AIC/BIC berasal dari hasil estimasi Statsmodels pada run ini")
    print(f"  (data transformasi: {em.TRANSFORMASI}). Kolom *_setara_kg = nilai yang")
    print("  dikoreksi Jacobian ke satuan kg.")
    print("- BIC Statsmodels memakai nobs_effective, bukan nobs.")
    print("- Peringkat hanya berlaku di dalam kelompok (d, D) yang sama.")
    print("- Tidak ada peringkat gabungan antar-kelompok.")
    print("- AIC/BIC terendah BELUM berarti model final; diagnostik residual")
    print("  dan evaluasi testing dilakukan pada script berikutnya.")

    return df_hasil


# =============================================================================
# FUNGSI 5B: PENGECEKAN MODEL BERSARANG
# =============================================================================

def cek_model_bersarang(df_hasil):
    """
    Model A tercakup (nested) dalam model B bila keduanya memiliki d, D, s
    yang sama, orde p, q, P, Q milik A <= milik B, dan eksogen A subset B.
    LogL model B tidak boleh lebih rendah dari LogL model A; bila terjadi,
    berarti estimasi B belum mencapai optimum.
    """

    print("\n" + "=" * 75)
    print("TAHAP 5B: PENGECEKAN MODEL BERSARANG (NESTED)")
    print("=" * 75)

    df_valid = df_hasil[df_hasil["Status"] != "Gagal"]
    info = []
    for _, r in df_valid.iterrows():
        o = tuple(int(x) for x in r["Order"].strip("()").split(","))
        so = tuple(int(x) for x in r["Seasonal_Order"].strip("()").split(","))
        eks = set() if r["Eksogen"] == "-" else {e.strip() for e in r["Eksogen"].split(",")}
        info.append((r["Nama_Model"], o, so, eks, float(r["Log_Likelihood"])))

    baris = []
    for nama_a, o_a, so_a, eks_a, ll_a in info:
        for nama_b, o_b, so_b, eks_b, ll_b in info:
            if nama_a == nama_b:
                continue
            if o_a[1] != o_b[1] or so_a[1] != so_b[1]:
                continue
            # Periode musiman harus sama bila A memiliki komponen musiman
            if any(so_a[:3]) and so_a[3] != so_b[3]:
                continue
            if not (o_a[0] <= o_b[0] and o_a[2] <= o_b[2]
                    and so_a[0] <= so_b[0] and so_a[2] <= so_b[2]
                    and eks_a <= eks_b):
                continue
            baris.append({
                "Model_Sederhana": nama_a,
                "Model_Kompleks": nama_b,
                "LogL_Sederhana": ll_a,
                "LogL_Kompleks": ll_b,
                "Selisih_LogL": ll_b - ll_a,
                "Pelanggaran": "Ya" if ll_b < ll_a - TOLERANSI_BERSARANG else "Tidak",
            })

    df_nested = pd.DataFrame(baris, columns=[
        "Model_Sederhana", "Model_Kompleks", "LogL_Sederhana",
        "LogL_Kompleks", "Selisih_LogL", "Pelanggaran"])
    kk.simpan_csv(df_nested, BERSARANG_CSV, index=False)

    pelanggaran = df_nested[df_nested["Pelanggaran"] == "Ya"]
    print(f"Pasangan bersarang diperiksa : {len(df_nested)}")
    print(f"Pelanggaran (LogL kompleks < sederhana - {TOLERANSI_BERSARANG}): {len(pelanggaran)}")
    if len(pelanggaran):
        print(pelanggaran[["Model_Sederhana", "Model_Kompleks", "Selisih_LogL"]].to_string(
            index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"Hasil disimpan ke: {BERSARANG_CSV}")
    return df_nested


# =============================================================================
# FUNGSI 6: RINGKASAN MARKDOWN
# =============================================================================

def tabel_markdown(df, kolom):
    def fmt(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "-"
        if isinstance(v, (float, np.floating)):
            return f"{v:.4f}"
        return str(v)

    baris = [
        "| " + " | ".join(kolom) + " |",
        "|" + "|".join(["---"] * len(kolom)) + "|"
    ]
    for _, r in df.iterrows():
        baris.append("| " + " | ".join(fmt(r[k]) for k in kolom) + " |")
    return "\n".join(baris)


def tulis_ringkasan(df_hasil, config, train_df, df_nested):
    L = []
    L.append("# Ringkasan Script 06: Estimasi Model dan Perbandingan AIC/BIC\n")
    L.append(
        f"Dibuat otomatis oleh `06_pemodelan_forecasting.py` "
        f"(statsmodels {statsmodels.__version__}, pandas {pd.__version__}).\n"
    )
    L.append("## Pengaturan\n")
    L.append(
        f"- Data training: {len(train_df)} observasi "
        f"({train_df.index[0]:%b %Y} – {train_df.index[-1]:%b %Y}), "
        f"target `{TARGET_COL}`."
    )
    L.append(
        f"- Semua kandidat diestimasi dengan `SARIMAX`, "
        f"`enforce_stationarity={ENFORCE_STATIONARITY}`, "
        f"`enforce_invertibility={ENFORCE_INVERTIBILITY}`."
    )
    L.append(
        f"- **Transformasi data:** `{em.TRANSFORMASI}` ({em.DESKRIPSI_TRANSFORMASI}); "
        "dihitung di dalam script, file data tidak diubah. Alasan: (1) pada skala kg "
        "(permintaan ±100.000, varians residual ±1e9) optimizer L-BFGS sering berhenti "
        "di optimum lokal dan std error tidak stabil; (2) lonjakan Iduladha bersifat "
        "perkalian (×2,717), sehingga residual model level di bulan Juni sangat besar dan "
        "tidak normal. Transformasi log mengubah efek perkalian menjadi penjumlahan "
        "(sesuai saran dokumen alur bila uji Shapiro-Wilk gagal). Log_Likelihood/AIC/BIC "
        "di tabel berskala data transformasi; kolom `*_setara_kg` di CSV sudah dikoreksi "
        "Jacobian ke satuan kg. Perbandingan dengan versi skala kg dan ribu kg: "
        "`perbandingan_versi_estimasi.md`."
    )
    L.append(
        f"- **Multi-optimizer:** {', '.join(m for m, _ in em.OPTIMIZER)} serta Nelder-Mead "
        "dari tiga nilai awal AR/MA (0; +0,3; −0,3); dipilih LogL tertinggi yang konvergen "
        "dengan std error valid, lalu di-polish dengan lbfgs (modul `estimasi_model.py`)."
    )
    L.append(f"- Variabel eksogen ARIMAX: `{PRICE_COL}`.")
    L.append(
        "- Label Iduladha: "
        + (f"`{config['kolom_iduladha']}` dari `{IDULADHA_CSV.name}` "
           "(dipakai apa adanya, digabung berdasarkan Periode)."
           if config["kolom_iduladha"]
           else "**tidak dipakai** (`IDULADHA_COL = None`).")
    )
    L.append(
        f"- Peringatan observasi efektif: `nobs_effective < {MIN_NOBS_EFEKTIF}` "
        f"atau `nobs_effective < {RASIO_NOBS_PER_PARAMETER} × jumlah parameter`."
    )
    L.append(
        "- Peringkat AIC/BIC hanya dalam kelompok (d, D) yang sama. "
        "Tidak ada peringkat gabungan dan belum ada model final.\n"
    )

    df_valid = df_hasil[df_hasil["Status"] != "Gagal"]
    kolom = [
        "Nama_Model", "nobs", "nobs_effective", "loglikelihood_burn",
        "Jumlah_Parameter", "Log_Likelihood", "AIC", "Delta_AIC_Kelompok",
        "BIC", "Delta_BIC_Kelompok", "Rank_AIC_Kelompok", "Rank_BIC_Kelompok",
        "Optimizer_Terpilih", "Konvergen"
    ]

    for nama_kelompok, isi in df_valid.groupby("Kelompok_Differencing"):
        L.append(f"## Kelompok {nama_kelompok} ({len(isi)} model)\n")
        L.append(tabel_markdown(isi, kolom))
        if isi["Catatan_Kelompok"].iloc[0] != "-":
            L.append(f"\n> Catatan: {isi['Catatan_Kelompok'].iloc[0]}")
        L.append("")

    L.append("## Pengecekan model bersarang\n")
    pel = df_nested[df_nested["Pelanggaran"] == "Ya"]
    L.append(f"{len(df_nested)} pasangan model bersarang diperiksa; pelanggaran (LogL model "
             f"kompleks < model sederhana − {TOLERANSI_BERSARANG}): **{len(pel)}**. "
             "Detail: `data/hasil_06/06_cek_model_bersarang.csv`.\n")
    if len(pel):
        L.append(tabel_markdown(pel, ["Model_Sederhana", "Model_Kompleks",
                                      "LogL_Sederhana", "LogL_Kompleks", "Selisih_LogL"]))
        L.append("")

    L.append("## Model gagal, tidak konvergen, atau dengan peringatan\n")
    df_catatan = df_hasil[
        (df_hasil["Status"] != "Berhasil")
        | (df_hasil["Warning"] != "-")
        | (df_hasil["Peringatan_Observasi"] != "-")
    ]
    if df_catatan.empty:
        L.append("Tidak ada.\n")
    else:
        L.append(tabel_markdown(
            df_catatan,
            ["Nama_Model", "Status", "Peringatan_Observasi", "Warning",
             "Penyebab_Gagal"]
        ))
        L.append("")

    L.append("## Tahap berikutnya\n")
    L.append(
        "Diagnostik residual, uji Ljung–Box, dan evaluasi data testing (script 07); "
        "peramalan data testing Apr–Des 2025 (script 08)."
    )

    RINGKASAN_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nRingkasan Markdown disimpan ke: {RINGKASAN_MD}")


# =============================================================================
# FUNGSI UTAMA
# =============================================================================

def main():
    penjelasan.mulai("06_pemodelan_forecasting")

    print("\n")
    print("=" * 75)
    print("PROGRAM PEMODELAN ARIMA, SARIMA, DAN ARIMAX (REVISI)")
    print("TAHAP 1 SAMPAI TAHAP 5")
    print("=" * 75)

    try:

        train_df, test_df, config = pemecahan_dan_ekspor_dataset(
            INPUT_CSV,
            CONFIG_JSON,
            train_ratio=TRAIN_RATIO
        )

        daftar_kandidat = tetapkan_skenario_pemodelan(config)

        fitted_models, df_estimasi = latih_semua_kandidat(
            train_df,
            daftar_kandidat
        )

        df_hasil = bandingkan_aic_bic(df_estimasi)

        df_nested = cek_model_bersarang(df_hasil)

        # Contoh perhitungan rumus [3] pembagian data, [6] skenario, [8] AIC/BIC, [7] pemilihan model
        penjelasan.jelaskan_06(train_df, test_df, daftar_kandidat, df_hasil, fitted_models)

        tulis_ringkasan(df_hasil, config, train_df, df_nested)

        print("\n" + "=" * 75)
        print("PEMODELAN TAHAP 1-5 SELESAI")
        print("=" * 75)

        print("\nFile hasil:")
        print(f"- {TRAIN_CSV}")
        print(f"- {TEST_CSV}")
        print(f"- {HASIL_ESTIMASI_CSV}")
        print(f"- {HASIL_AIC_BIC_CSV}")
        print(f"- {BERSARANG_CSV}")
        print(f"- {RINGKASAN_MD}")

        print("\nLanjut ke 07_validasi_diagnostik_evaluasi.py untuk validasi diagnostik "
              "dan evaluasi kinerja.")

    except Exception as e:

        print("\n" + "=" * 75)
        print("[ERROR] TERJADI KESALAHAN PADA PROGRAM")
        print("=" * 75)
        print(f"{type(e).__name__}: {e}")
        raise


# =============================================================================
# EKSEKUSI PROGRAM
# =============================================================================

if __name__ == "__main__":
    main()
