"""Keterangan kolom CSV hasil: simpan_csv() menulis blok keterangan di atas tabel, baca_csv() melewatinya."""
import csv
import re
import sys
from pathlib import Path

import pandas as pd

TANDA = "#"
GARIS = "# " + "=" * 100

# -----------------------------------------------------------------------------
# KOLOM UMUM: nama kolom -> (arti, diperoleh dari). Dipakai bila tabel tidak
# mempunyai keterangan khusus untuk kolom tersebut.
# -----------------------------------------------------------------------------
U = {
    # --- waktu dan identitas ---
    "Periode": ("Bulan yang dicatat atau diramal (tahun-bulan).",
                "Kalender; satu baris mewakili satu bulan."),
    "t": ("Nomor urut bulan sejak awal data (1 = Januari 2023).",
          "Dihitung berurutan: Januari 2023 = 1, Februari 2023 = 2, dan seterusnya."),
    "Tahun": ("Tahun kalender.", "Diambil dari Periode."),
    "Bulan": ("Nomor bulan dalam setahun (1 = Januari ... 12 = Desember).", "Diambil dari Periode."),
    "Label": ("Nama singkat model. ARIMA = tanpa musiman; SARIMA D=0 / SARIMA D=1 = dengan pola musiman 12 bulan; "
              "ARIMAX Harga = ditambah data harga; ARIMAX Harga+Iduladha = ditambah harga dan penanda Iduladha; "
              "Seasonal naive = pembanding paling sederhana (ramalan = angka bulan yang sama tahun lalu).",
              "Ditetapkan di script 07: satu model terbaik (AIC terendah) dari tiap skenario."),
    "Nama_Model": ("Nama lengkap model beserta ordenya, misalnya SARIMA(1, 0, 0)x(1, 1, 0, 12). "
                   "y[t-12] = seasonal naive.",
                   "Dari daftar kandidat model yang diestimasi di script 06."),
    "Skenario": ("Keluarga model: ARIMA, SARIMA, atau ARIMAX.", "Ditetapkan saat menyusun daftar kandidat (script 06)."),
    "Order": ("Orde non-musiman (p, d, q): p = banyaknya bulan lalu yang dipakai (AR), d = banyaknya pembedaan, "
              "q = banyaknya galat lalu yang dipakai (MA).", "Ditetapkan saat menyusun daftar kandidat (script 06)."),
    "Seasonal_Order": ("Orde musiman (P, D, Q, m): sama seperti Order tetapi untuk pola tahunan; m = 12 bulan. "
                       "(0, 0, 0, 0) berarti model tanpa komponen musiman.",
                       "Ditetapkan saat menyusun daftar kandidat (script 06)."),
    "Eksogen": ("Variabel tambahan dari luar yang dipakai model selain data permintaan itu sendiri. "
                "Tanda - berarti tidak ada.", "Ditetapkan per skenario (ARIMAX memakai harga dan/atau penanda Iduladha)."),
    "Kelompok_Differencing": ("Kelompok pembedaan data: d = pembedaan biasa, D = pembedaan musiman (selisih dengan 12 bulan sebelumnya).",
                              "Diambil dari Order dan Seasonal_Order. AIC/BIC hanya adil dibandingkan antar model dalam kelompok yang sama."),
    "Kelompok": ("Kelompok pembedaan data: d = pembedaan biasa, D = pembedaan musiman (selisih dengan 12 bulan sebelumnya).",
                 "Diambil dari Order dan Seasonal_Order. AIC/BIC hanya adil dibandingkan antar model dalam kelompok yang sama."),
    "Horizon": ("Jarak bulan yang diramal dari bulan terakhir data latih (1 = satu bulan ke depan).",
                "Dihitung berurutan mulai dari bulan pertama setelah data latih."),
    "h": ("Urutan bulan ke depan yang diramal (1 = bulan pertama setelah data terakhir).",
          "Dihitung berurutan 1 sampai 6."),

    # --- data permintaan dan harga ---
    "Total_Kuantitas_Kg": ("Permintaan daging kambing seluruh Kabupaten Malang pada bulan itu (kg). Inilah angka yang diramal.",
                           "Jumlah Kuantitas_Kg semua struk transaksi pada bulan itu (script 04)."),
    "Jumlah_Transaksi": ("Banyaknya struk transaksi pada bulan itu.",
                         "Menghitung jumlah baris transaksi per bulan (script 04)."),
    "Harga_Rata2_Per_Kg": ("Harga jual rata-rata per kg pada bulan itu (rupiah).",
                           "Rata-rata Harga_Final semua struk transaksi bulan itu, dibulatkan (script 04)."),
    "Koefisien_Musim": ("Penanda bulan Iduladha: 1 = bulan biasa; 2,717 = bulan Iduladha (permintaan sekitar 2,7 kali bulan biasa).",
                        "Pengali musiman yang dipakai saat membangkitkan data (script 03): 1 + (22.359 - 8.229) / 8.229 = 2,717."),
    "Aktual_Kg": ("Permintaan yang benar-benar terjadi pada bulan itu (kg).",
                  "Diambil dari data (Total_Kuantitas_Kg)."),
    "Permintaan_Kg": ("Permintaan daging kambing seluruh Kabupaten Malang pada bulan itu (kg).",
                      "Diambil dari data permintaan bulanan."),

    # --- ramalan dan interval ---
    "Prediksi_Kg": ("Ramalan permintaan untuk bulan itu (kg).",
                    "Model meramal dalam bentuk logaritma, lalu dikembalikan ke kg dengan exp(ramalan log)."),
    "Ramalan_Kg": ("Ramalan permintaan untuk bulan itu (kg).",
                   "Model meramal dalam bentuk logaritma, lalu dikembalikan ke kg dengan exp(ramalan log)."),
    "Yhat_Kg": ("Ramalan permintaan untuk bulan itu (kg). Ini angka ramalan utama.",
                "exp(Yhat_log), yaitu ramalan logaritma dikembalikan ke satuan kg."),
    "Batas_Bawah_95_Kg": ("Batas bawah interval kepercayaan 95% (kg): perkiraan terendah yang masih wajar.",
                          "exp(ramalan log - 1,96 x galat baku ramalan)."),
    "Batas_Atas_95_Kg": ("Batas atas interval kepercayaan 95% (kg): perkiraan tertinggi yang masih wajar. "
                         "Dipakai sebagai acuan stok/kapasitas maksimum.",
                         "exp(ramalan log + 1,96 x galat baku ramalan)."),
    "Error_Kg": ("Selisih antara kenyataan dan ramalan (kg). Positif = ramalan terlalu rendah; negatif = ramalan terlalu tinggi.",
                 "Aktual_Kg - ramalan."),
    "APE_%": ("Besar kesalahan ramalan bulan itu dalam persen dari angka sebenarnya (makin kecil makin baik).",
              "|Aktual - Ramalan| / Aktual x 100."),

    # --- metrik akurasi ---
    "MAE": ("Rata-rata besar kesalahan ramalan (kg), tanpa melihat arah lebih/kurang. Makin kecil makin baik.",
            "Rata-rata dari |Aktual - Ramalan| seluruh bulan yang diuji."),
    "MSE": ("Rata-rata kuadrat kesalahan (kg kuadrat). Kesalahan besar dihukum lebih berat. Makin kecil makin baik.",
            "Rata-rata dari (Aktual - Ramalan) kuadrat."),
    "RMSE": ("Akar dari MSE (kg). Ukuran kesalahan tipikal yang peka terhadap kesalahan besar. Makin kecil makin baik.",
             "Akar kuadrat MSE."),
    "MAPE_%": ("Rata-rata kesalahan ramalan dalam persen. Contoh 6,6 berarti ramalan rata-rata meleset 6,6% dari kenyataan. "
               "Makin kecil makin baik.", "Rata-rata APE_% seluruh bulan yang diuji."),
    "R2": ("Seberapa baik ramalan mengikuti naik-turunnya data (maksimum 1 = sempurna).",
           "1 - jumlah (Aktual - Ramalan) kuadrat / jumlah (Aktual - rata-rata Aktual) kuadrat."),
    "APE_maks_%": ("Kesalahan persen terbesar di antara bulan-bulan yang diuji.", "Nilai APE_% tertinggi."),
    "RMSE_%_rata2": ("RMSE dinyatakan sebagai persen dari rata-rata permintaan aktual. Target: di bawah 10.",
                     "RMSE / rata-rata permintaan aktual periode uji x 100."),
    "MAE_%_rata2": ("MAE dinyatakan sebagai persen dari rata-rata permintaan aktual. Target: di bawah 8.",
                    "MAE / rata-rata permintaan aktual periode uji x 100."),
    "Target_MAPE_%": ("Lulus jika MAPE di bawah 15%; Gagal jika tidak.", "Membandingkan MAPE_% dengan target 15."),
    "Target_RMSE": ("Lulus jika RMSE di bawah 10% dari rata-rata permintaan aktual.",
                    "Membandingkan RMSE dengan 10% x rata-rata permintaan aktual periode uji."),
    "Target_MAE": ("Lulus jika MAE di bawah 8% dari rata-rata permintaan aktual.",
                   "Membandingkan MAE dengan 8% x rata-rata permintaan aktual periode uji."),
    "Target_MSE": ("Lulus jika MSE di bawah kuadrat dari target RMSE.",
                   "Membandingkan MSE dengan (10% x rata-rata permintaan aktual) kuadrat."),
    "Target_R2": ("Lulus jika R2 di atas 0,70.", "Membandingkan R2 dengan target 0,70."),

    # --- parameter model ---
    "Parameter": ("Nama parameter model. intercept = nilai dasar; ar.L1/ar.L2 = pengaruh 1/2 bulan sebelumnya; "
                  "ma.L1 = pengaruh galat bulan sebelumnya; ar.S.L12/ma.S.L12 = pengaruh bulan yang sama tahun lalu; "
                  "Harga_Rata2_Per_Kg / Koefisien_Musim = pengaruh variabel eksogen; sigma2 = ragam galat model.",
                  "Nama baku dari statsmodels sesuai orde model."),
    "Koefisien": ("Besar pengaruh parameter tersebut di dalam model (pada skala logaritma). Tanda negatif berarti arah pengaruh berlawanan.",
                  "Hasil estimasi kemungkinan maksimum (MLE) statsmodels."),
    "Std_Error": ("Galat baku koefisien: seberapa tidak pasti nilai koefisien. Makin kecil dibanding koefisiennya makin meyakinkan.",
                  "Dihitung statsmodels dari kelengkungan fungsi likelihood."),
    "z": ("Nilai uji z: berapa kali lipat koefisien dibanding galat bakunya.", "Koefisien / Std_Error."),
    "P_value": ("Peluang hasil seperti ini muncul hanya karena kebetulan. Di bawah 0,05 = dianggap bukan kebetulan.",
                "Dihitung dari statistik uji dengan sebaran teoretisnya."),
    "CI95_Bawah": ("Batas bawah rentang 95% untuk nilai koefisien yang sebenarnya.", "Koefisien - 1,96 x Std_Error."),
    "CI95_Atas": ("Batas atas rentang 95% untuk nilai koefisien yang sebenarnya.", "Koefisien + 1,96 x Std_Error."),
    "Signifikan_5%": ("Ya = pengaruh parameter nyata (P_value di bawah 0,05); Tidak = belum terbukti nyata; - = tidak diuji (sigma2).",
                      "Membandingkan P_value dengan 0,05."),

    # --- ukuran kecocokan model ---
    "Log_Likelihood": ("Ukuran seberapa cocok model dengan data latih (pada skala logaritma). Makin besar makin cocok.",
                       "Nilai log-likelihood hasil estimasi statsmodels."),
    "LogL": ("Ukuran seberapa cocok model dengan data latih (pada skala logaritma). Makin besar makin cocok.",
             "Nilai log-likelihood hasil estimasi statsmodels."),
    "AIC": ("Skor kecocokan model yang memberi penalti pada model rumit. Makin kecil makin baik (hanya dibandingkan dalam kelompok d, D yang sama).",
            "-2 x Log_Likelihood + 2 x Jumlah_Parameter."),
    "BIC": ("Seperti AIC tetapi penalti untuk model rumit lebih berat. Makin kecil makin baik.",
            "-2 x Log_Likelihood + Jumlah_Parameter x ln(nobs_effective)."),
    "AIC_06": ("Skor AIC model (makin kecil makin baik dalam kelompoknya).", "Diambil dari hasil script 06."),
    "BIC_06": ("Skor BIC model (makin kecil makin baik dalam kelompoknya).", "Diambil dari hasil script 06."),
    "nobs": ("Banyaknya bulan data latih.", "Jumlah baris data training (27 bulan)."),
    "nobs_effective": ("Banyaknya bulan yang benar-benar dipakai menghitung kecocokan model.",
                       "nobs - loglikelihood_burn."),
    "loglikelihood_burn": ("Banyaknya bulan awal yang tidak ikut dihitung karena terpakai untuk pembedaan musiman "
                           "(12 bulan pada model D=1, 0 pada model lain).", "Dilaporkan statsmodels."),
    "Jumlah_Parameter": ("Banyaknya parameter yang diestimasi model (termasuk sigma2).", "Dilaporkan statsmodels (df_model)."),
    "Transformasi": ("Bentuk data yang dimasukkan ke model. log = data diubah ke logaritma natural terlebih dahulu.",
                     "Pengaturan di estimasi_model.py."),
    "LogL_setara_kg": ("Log_Likelihood yang disetarakan ke satuan kg, supaya bisa dibandingkan dengan model tanpa logaritma.",
                       "Log_Likelihood - jumlah ln(permintaan) bulan yang dipakai (koreksi Jacobian)."),
    "AIC_setara_kg": ("AIC yang disetarakan ke satuan kg.", "AIC + 2 x jumlah ln(permintaan) bulan yang dipakai."),
    "BIC_setara_kg": ("BIC yang disetarakan ke satuan kg.", "BIC + 2 x jumlah ln(permintaan) bulan yang dipakai."),
    "LogL_lbfgs": ("Log-likelihood yang dicapai cara pencarian (optimizer) lbfgs.", "Hasil estimasi dengan optimizer lbfgs."),
    "LogL_bfgs": ("Log-likelihood yang dicapai optimizer bfgs.", "Hasil estimasi dengan optimizer bfgs."),
    "LogL_powell": ("Log-likelihood yang dicapai optimizer powell.", "Hasil estimasi dengan optimizer powell."),
    "LogL_nm": ("Log-likelihood yang dicapai optimizer Nelder-Mead (nm).", "Hasil estimasi dengan optimizer nm."),
    "LogL_nm_awal+0.0": ("Log-likelihood optimizer nm bila tebakan awal koefisien AR/MA = 0.",
                         "Hasil estimasi nm dengan nilai awal 0."),
    "LogL_nm_awal+0.3": ("Log-likelihood optimizer nm bila tebakan awal koefisien AR/MA = +0,3.",
                         "Hasil estimasi nm dengan nilai awal +0,3."),
    "LogL_nm_awal-0.3": ("Log-likelihood optimizer nm bila tebakan awal koefisien AR/MA = -0,3.",
                         "Hasil estimasi nm dengan nilai awal -0,3."),
    "Optimizer_Terpilih": ("Cara pencarian yang hasilnya dipakai untuk model ini.",
                           "Dipilih yang log-likelihood-nya tertinggi, konvergen, dan galat bakunya valid."),
    "Dipoles_lbfgs": ("True = hasil terbaik dihaluskan sekali lagi dengan lbfgs dan hasil halusnya dipakai.",
                      "Estimasi ulang lbfgs mulai dari titik terbaik; dipakai bila log-likelihood tidak turun."),
    "SE_Valid": ("True = semua galat baku koefisien wajar (terhingga, lebih dari 0, tidak sangat besar).",
                 "Pemeriksaan otomatis terhadap Std_Error hasil estimasi."),
    "Konvergen": ("True = proses pencarian parameter selesai dengan baik (menemukan titik terbaik).",
                  "Status konvergensi yang dilaporkan optimizer."),
    "Warning": ("Peringatan dari statsmodels saat estimasi. Tanda - berarti tidak ada.", "Dicatat otomatis saat estimasi."),
}

# -----------------------------------------------------------------------------
# KOLOM BERPOLA (nama kolom mengandung label model / angka contoh)
# -----------------------------------------------------------------------------
POLA = [
    (r"^Fitted_(.+)_Kg$", ("Nilai permintaan (kg) menurut model {0} untuk bulan data latih. Kosong pada bulan awal yang belum bisa dihitung model.",
                           "exp(nilai fitted pada skala logaritma) dari model {0}.")),
    (r"^Residual_(.+)$", ("Sisa (galat) model {0} pada skala logaritma: bagian data yang tidak terjelaskan model. Kosong pada bulan awal yang belum bisa dihitung.",
                          "ln(aktual) - ln(nilai fitted) dari model {0}.")),
    (r"^Contoh_UMKM_(\d+)kg_Rencana_Kg$", ("Contoh rencana stok (kg) untuk satu UMKM yang pada bulan normal menjual {0} kg.",
                                           "{0} x Indeks_vs_Bulan_Normal.")),
    (r"^Contoh_UMKM_(\d+)kg_Maks_Kg$", ("Contoh stok/kapasitas maksimum (kg) yang perlu disiapkan UMKM dengan penjualan bulan normal {0} kg.",
                                        "{0} x Indeks_vs_Bulan_Normal x Faktor_Batas_Atas.")),
    (r"^Rasio_(.+)$", ("Porsi produk {0} dari total empat jenis produk (0,38 berarti 38%).",
                       "Produksi {0} / (Daging Murni + Karkas + Jeroan + Daging Variasi) dari data BPS tahun itu.")),
    (r"^LB_Q_lag(\d+)$", ("Statistik uji Ljung-Box sampai lag {0}: makin besar berarti sisa model makin berpola. Kosong = lag tidak diuji.",
                          "Uji Ljung-Box pada residual (sisa) model sampai {0} bulan ke belakang.")),
    (r"^LB_df_lag(\d+)$", ("Derajat bebas uji Ljung-Box lag {0}.", "{0} - model_df.")),
    (r"^LB_p_lag(\d+)$", ("P-value Ljung-Box lag {0}. Di atas 0,05 = sisa model tidak berpola (baik).",
                          "Dari statistik LB_Q_lag{0} dengan sebaran chi-kuadrat.")),
]

_KOL_ESTIMASI = {
    "d": ("Banyaknya pembedaan biasa (selisih dengan bulan sebelumnya). 0 = tidak dibedakan.", "Angka tengah pada Order."),
    "D": ("Banyaknya pembedaan musiman (selisih dengan 12 bulan sebelumnya). 1 = dibedakan.", "Angka kedua pada Seasonal_Order."),
    "Status": ("Berhasil = model selesai diestimasi; Gagal = estimasi tidak berhasil.", "Hasil proses estimasi."),
    "Peringatan_Observasi": ("Catatan bila data terlalu sedikit dibanding jumlah parameter. Tanda - berarti aman.",
                             "Muncul bila nobs_effective di bawah 20 atau di bawah 10 x Jumlah_Parameter."),
    "Penyebab_Gagal": ("Penyebab kegagalan estimasi. Tanda - berarti tidak gagal.", "Pesan galat yang ditangkap saat estimasi."),
    "Rank_AIC_Kelompok": ("Peringkat AIC di dalam kelompoknya (1 = AIC terendah = terbaik).",
                          "Mengurutkan AIC dari kecil ke besar per Kelompok_Differencing."),
    "Rank_BIC_Kelompok": ("Peringkat BIC di dalam kelompoknya (1 = terbaik).",
                          "Mengurutkan BIC dari kecil ke besar per Kelompok_Differencing."),
    "Delta_AIC_Kelompok": ("Selisih AIC model ini dengan AIC terbaik di kelompoknya (0 = model terbaik).",
                           "AIC - AIC terendah dalam kelompok."),
    "Delta_BIC_Kelompok": ("Selisih BIC model ini dengan BIC terbaik di kelompoknya (0 = model terbaik).",
                           "BIC - BIC terendah dalam kelompok."),
    "Catatan_Kelompok": ("Catatan bila jumlah data efektif antar model dalam satu kelompok tidak sama. Tanda - berarti sama.",
                         "Pemeriksaan nobs_effective per kelompok."),
}

_KOL_PARAM_FINAL = {
    "Parameter": ("Nama parameter model final. ar.L1 = pengaruh bulan sebelumnya; ar.S.L12 = pengaruh bulan yang sama tahun lalu; "
                  "sigma2 = ragam galat model.", "Nama baku dari statsmodels."),
    "P_value": ("Peluang koefisien sebesar itu muncul hanya karena kebetulan. Di bawah 0,05 = pengaruhnya nyata (signifikan).",
                "Dari uji z = Koefisien / Std_Error."),
}

_KOL_RAMALAN_09 = {
    "t": ("Nomor urut bulan yang diramal, melanjutkan nomor urut data.", "Jumlah bulan data yang dipakai + h."),
    "Yhat_log": ("Ramalan dalam bentuk logaritma natural (bentuk asli keluaran model).",
                 "Keluaran langsung model SARIMA(1,0,0)x(1,1,0,12)."),
    "SE_log": ("Galat baku ramalan (skala logaritma): ukuran ketidakpastian. Makin jauh bulan yang diramal makin besar.",
               "Dihitung model dari ragam galat (sigma2) dan jarak ramalan h."),
    "Z": ("Angka baku untuk tingkat keyakinan 95% (sekitar 1,96).", "Nilai sebaran normal baku pada 97,5%."),
    "MoE_log": ("Margin kesalahan (skala logaritma): jarak dari ramalan ke batas interval.", "Z x SE_log."),
    "Batas_Bawah_log": ("Batas bawah interval 95% pada skala logaritma.", "Yhat_log - MoE_log."),
    "Batas_Atas_log": ("Batas atas interval 95% pada skala logaritma.", "Yhat_log + MoE_log."),
    "Batas_Bawah_95_Kg": ("Batas bawah interval kepercayaan 95% (kg): perkiraan terendah yang masih wajar.", "exp(Batas_Bawah_log)."),
    "Batas_Atas_95_Kg": ("Batas atas interval kepercayaan 95% (kg): perkiraan tertinggi yang masih wajar; acuan stok/kapasitas maksimum.",
                         "exp(Batas_Atas_log)."),
    "Lebar_Interval_Kg": ("Lebar rentang ketidakpastian (kg). Makin lebar makin tidak pasti.", "Batas_Atas_95_Kg - Batas_Bawah_95_Kg."),
    "Jarak_ke_Bawah_Kg": ("Jarak dari ramalan ke batas bawah (kg).", "Yhat_Kg - Batas_Bawah_95_Kg."),
    "Jarak_ke_Atas_Kg": ("Jarak dari ramalan ke batas atas (kg). Lebih besar dari jarak ke bawah karena efek logaritma.",
                         "Batas_Atas_95_Kg - Yhat_Kg."),
    "Bulan_Iduladha": ("Ya = bulan itu bulan Iduladha pada data; Tidak = bulan biasa.", "Koefisien_Musim lebih dari 1."),
    "Error_Kg": ("Selisih kenyataan dan ramalan (kg). Positif = ramalan terlalu rendah; negatif = terlalu tinggi.", "Aktual_Kg - Yhat_Kg."),
    "APE_%": ("Besar kesalahan ramalan bulan itu dalam persen (makin kecil makin baik).", "|Aktual_Kg - Yhat_Kg| / Aktual_Kg x 100."),
    "Aktual_dalam_Interval": ("Ya = angka sebenarnya berada di antara batas bawah dan batas atas; Tidak = di luar.",
                              "Memeriksa Batas_Bawah_95_Kg <= Aktual_Kg <= Batas_Atas_95_Kg."),
}

_KOL_ADF = {
    "Seri": ("Bentuk data yang diuji (asli, atau sudah dibedakan).", "Ditetapkan di script 10."),
    "Jumlah_Observasi": ("Banyaknya titik data yang dipakai uji.", "Dilaporkan uji ADF (jumlah data dikurangi lag yang dipakai)."),
    "ADF_Statistic": ("Statistik uji ADF. Makin negatif makin kuat bukti data stasioner (rata-rata dan ragamnya stabil).",
                      "Uji Augmented Dickey-Fuller (statsmodels) dengan konstanta."),
    "P_value": ("P-value uji ADF. Di bawah 0,05 = data stasioner.", "Dari ADF_Statistic."),
    "Used_Lag": ("Banyaknya lag yang dipakai uji.", "Dipilih otomatis berdasarkan AIC."),
    "Kritis_1%": ("Nilai pembanding (kritis) pada tingkat 1%.", "Tabel nilai kritis ADF."),
    "Kritis_5%": ("Nilai pembanding (kritis) pada tingkat 5%. Dipakai untuk keputusan.", "Tabel nilai kritis ADF."),
    "Kritis_10%": ("Nilai pembanding (kritis) pada tingkat 10%.", "Tabel nilai kritis ADF."),
    "Keputusan": ("Kesimpulan uji: stasioner atau tidak stasioner.",
                  "Stasioner bila P_value di bawah 0,05 dan ADF_Statistic lebih kecil dari Kritis_5%."),
    "Dipakai": ("Apakah bentuk data ini dipakai dalam pemodelan, dan oleh model mana.", "Keputusan metodologi penelitian."),
}

_KOL_SHORTLIST = {
    "Ljung_Box": ("Lulus = sisa (residual) model tidak berpola lagi.", "Hasil uji Ljung-Box di script 07."),
    "Shapiro_Wilk": ("Lulus = sisa (residual) model menyebar normal.", "Hasil uji Shapiro-Wilk di script 07."),
    "MAPE_rolling_07_%": ("MAPE model pada uji rolling origin (ramal 1 bulan, ulang 9 kali).",
                          "Diambil dari 07_metrik_rolling_origin.csv."),
}

_KOL_ACCESS_RAMAL = {
    "Periode_Ramalan": ("Bulan yang diramal.", "Satu bulan setelah Periode_Asal."),
    "Periode_Asal": ("Bulan data terakhir yang dipakai untuk meramal.", "Dari Tbl_Volume_Bulanan di MS Access."),
    "Prediksi_Kg": ("Ramalan permintaan (kg) hasil hitungan query MS Access.",
                    "Rumus SARIMA(1,0,0)x(1,1,0,12) log dalam SQL: exp(ln permintaan 12 bulan lalu + pengaruh selisih musiman bulan-bulan sebelumnya)."),
    "Batas_Bawah_95_Kg": ("Batas bawah interval 95% (kg).", "exp(ramalan log - 1,96 x akar sigma2)."),
    "Batas_Atas_95_Kg": ("Batas atas interval 95% (kg).", "exp(ramalan log + 1,96 x akar sigma2)."),
}

_KOL_RAMAL_12 = {
    "Periode": ("Bulan yang diramal.", "Enam bulan setelah data terakhir di Tbl_Volume_Bulanan."),
    "Ramalan_Kg": ("Ramalan permintaan (kg) hasil query MS Access.",
                   "Query qry_12_Ramalan_6_Bulan: rumus SARIMA(1,0,0)x(1,1,0,12) log ditulis dalam SQL."),
    "Batas_Bawah_95_Kg": ("Batas bawah interval 95% (kg).", "exp(ramalan log - 1,96 x galat baku ramalan) dalam SQL."),
    "Batas_Atas_95_Kg": ("Batas atas interval 95% (kg).", "exp(ramalan log + 1,96 x galat baku ramalan) dalam SQL."),
}

# -----------------------------------------------------------------------------
# KETERANGAN PER TABEL: nama file -> oleh, isi, baris, kolom khusus
# -----------------------------------------------------------------------------
TABEL = {
    # ----------------------------- script 03 --------------------------------
    "baseline_bps.csv": {
        "oleh": "03_generate_data.py",
        "isi": "Angka dasar (baseline) permintaan per tahun yang diturunkan dari data produksi daging kambing BPS Kabupaten Malang.",
        "baris": "satu tahun (2023, 2024, 2025).",
        "kolom": {
            "Karkas_Tahunan_Kab": ("Produksi karkas kambing Kabupaten Malang dalam setahun (kg).",
                                   "Data BPS; bila tidak tersedia untuk tahun itu, ditaksir dari perbandingan tahun lain."),
            "Karkas_Bulanan_Kab": ("Produksi karkas rata-rata per bulan (kg).", "Karkas_Tahunan_Kab / 12."),
            "Mu_Lokal": ("Baseline permintaan bulanan pasar lokal (kg) = angka dasar sebelum ditambah tren, musim, dan acak.",
                         "Sama dengan Karkas_Bulanan_Kab (tingkat kabupaten, tidak dibagi jumlah UMKM)."),
            "Diestimasi": ("True = angka karkas tahun itu hasil taksiran; False = langsung dari BPS.",
                           "True bila kolom karkas pada data BPS tahun itu kosong."),
        },
    },
    "volume_bulanan.csv": {
        "oleh": "03_generate_data.py",
        "isi": "Jejak langkah demi langkah pembentukan data permintaan sintetis tiap bulan: baseline -> undian volume -> tren -> musim Iduladha -> acak (noise) -> volume akhir.",
        "baris": "satu bulan (Januari 2023 - Desember 2025, 36 bulan).",
        "kolom": {
            "Mu_Lokal": ("Baseline permintaan bulanan (kg) untuk tahun bulan itu.", "Karkas tahunan Kabupaten Malang (BPS) / 12."),
            "Batas_Bawah": ("Batas terendah undian volume dasar (kg).", "Mu_Lokal - 10% x Mu_Lokal."),
            "Batas_Atas": ("Batas tertinggi undian volume dasar (kg).", "Mu_Lokal + 10% x Mu_Lokal."),
            "Target_Kg": ("Volume dasar bulan itu sebelum tren dan musim (kg).",
                          "Undian acak merata di antara Batas_Bawah dan Batas_Atas (seed tetap 42)."),
            "t_awal_fase": ("Nomor bulan tepat sebelum tahun itu mulai (0, 12, atau 24).", "(urutan tahun - 1) x 12."),
            "m_Bulanan": ("Laju tren per bulan (0,01 berarti naik 1% per bulan; negatif = turun).",
                          "Pertumbuhan tahunan produksi daging kambing nasional / 12; tahun 2023 = 0 (fase stabil)."),
            "Faktor_Tren": ("Pengali tren untuk bulan itu.", "1 + m_Bulanan x (t - t_awal_fase)."),
            "Volume_Tren_Kg": ("Volume setelah diberi tren (kg).", "Target_Kg x Faktor_Tren."),
            "Volume_Musim_Kg": ("Volume setelah diberi efek musim Iduladha (kg).", "Volume_Tren_Kg x Koefisien_Musim."),
            "Sigma_Noise": ("Besar simpangan acak yang diizinkan bulan itu (kg).", "5% x Volume_Musim_Kg."),
            "Noise_Kg": ("Gangguan acak bulan itu (kg), bisa positif atau negatif.",
                         "Undian acak sebaran normal dengan rata-rata 0 dan simpangan baku Sigma_Noise."),
            "Volume_Akhir_Kg": ("Permintaan akhir bulan itu (kg). Inilah data permintaan yang dipakai penelitian.",
                                "Volume_Musim_Kg + Noise_Kg."),
            "Total_Transaksi_Kg": ("Jumlah kg seluruh struk transaksi bulan itu.", "Jumlah Kuantitas_Kg di transaksi_penjualan.csv per bulan."),
            "Jumlah_Pesanan": ("Banyaknya struk transaksi bulan itu.", "Menghitung baris transaksi per bulan."),
            "Harga_Rata2_Per_Kg": ("Harga jual rata-rata per kg bulan itu (rupiah), tertimbang volume.",
                                   "Total_Pendapatan / Total_Transaksi_Kg, dibulatkan."),
            "Total_Pendapatan": ("Total nilai penjualan bulan itu (rupiah).", "Jumlah Total_Pendapatan semua struk bulan itu."),
            "Cocok": ("True = total kg struk sama dengan Volume_Akhir_Kg (pemeriksaan konsistensi).",
                      "Selisih Total_Transaksi_Kg dan Volume_Akhir_Kg kurang dari 0,01 kg."),
        },
    },
    "transaksi_penjualan.csv": {
        "oleh": "03_generate_data.py",
        "isi": "Rincian struk transaksi penjualan daging kambing (data sintetis). Volume bulanan dipecah menjadi struk 5-35 kg lalu diberi jenis produk dan harga.",
        "baris": "satu struk transaksi.",
        "kolom": {
            "ID_Transaksi": ("Nomor unik struk.", "Nomor urut TRX000001, TRX000002, ... setelah diurutkan menurut tanggal."),
            "t": ("Nomor urut bulan transaksi (1 = Januari 2023).", "Bulan asal volume yang dipecah."),
            "Tanggal_Transaksi": ("Tanggal transaksi.", "Undian hari acak di dalam bulan tersebut."),
            "Jenis_Produk": ("Jenis produk: Daging Murni, Karkas, Jeroan, atau Daging Variasi.",
                             "Undian acak dengan peluang sesuai rasio produk BPS tahun itu."),
            "Kuantitas_Kg": ("Berat pembelian pada struk itu (kg).",
                             "Undian acak merata 5-35 kg; struk terakhir tiap bulan dipotong agar total pas sama dengan volume bulan itu."),
            "Harga_Normal": ("Harga dasar per kg sebelum kenaikan Iduladha (rupiah).",
                             "Undian acak merata dalam rentang harga jenis produknya, dibulatkan ke kelipatan Rp 500."),
            "Markup_Musiman": ("Tambahan harga per kg karena Iduladha (rupiah); 0 pada bulan biasa.",
                               "Undian acak Rp 10.000-15.000 bila transaksi terjadi di bulan Iduladha."),
            "Harga_Final": ("Harga jual per kg yang dibayar (rupiah).", "Harga_Normal + Markup_Musiman."),
            "Total_Pendapatan": ("Nilai penjualan struk itu (rupiah).", "Kuantitas_Kg x Harga_Final."),
        },
    },
    "dataset_sarimax.csv": {
        "oleh": "03_generate_data.py",
        "isi": "Dataset utama 36 bulan hasil pembangkitan data: permintaan bulanan beserta harga dan jumlah pesanan.",
        "baris": "satu bulan (Januari 2023 - Desember 2025).",
        "kolom": {
            "Permintaan_Kg": ("Permintaan daging kambing seluruh Kabupaten Malang pada bulan itu (kg).",
                              "Volume_Akhir_Kg dari volume_bulanan.csv (baseline BPS x tren x musim Iduladha + acak)."),
            "Harga_Rata2_Per_Kg": ("Harga jual rata-rata per kg bulan itu (rupiah), tertimbang volume.",
                                   "Total pendapatan bulan itu / total kg bulan itu, dibulatkan."),
            "Jumlah_Pesanan": ("Banyaknya struk transaksi bulan itu.", "Menghitung baris transaksi per bulan."),
        },
    },
    # ----------------------------- script 04 --------------------------------
    "dataset_pra_proses_final.csv": {
        "oleh": "04_pra_proses_data.py",
        "isi": "Data bulanan siap analisis hasil pra-proses: struk transaksi dijumlahkan per bulan, bulan kosong diisi interpolasi, dan pencilan (outlier) diperiksa dengan metode IQR.",
        "baris": "satu bulan (Januari 2023 - Desember 2025, 36 bulan).",
        "kolom": {
            "Total_Kuantitas_Kg": ("Permintaan daging kambing seluruh Kabupaten Malang pada bulan itu (kg). Inilah angka yang diramal.",
                                   "Jumlah Kuantitas_Kg semua struk bulan itu. Nilai di luar batas IQR dipangkas, kecuali bulan Iduladha (Juni) yang dipertahankan."),
        },
    },
    # ----------------------------- script 05 --------------------------------
    "tabel_dekomposisi_hasil.csv": {
        "oleh": "05_eksplorasi_data.py",
        "isi": "Data bulanan yang diurai (dekomposisi aditif, periode 12 bulan) menjadi tiga bagian: tren, musiman, dan sisa. Permintaan = Trend + Seasonal + Residual.",
        "baris": "satu bulan (Januari 2023 - Desember 2025).",
        "kolom": {
            "Trend_Kg": ("Arah umum jangka panjang permintaan (kg). Kosong pada 6 bulan pertama dan 6 bulan terakhir.",
                         "Rata-rata bergerak terpusat 12 bulan."),
            "Seasonal_Kg": ("Efek musiman bulan itu (kg): berapa kg bulan tersebut biasanya di atas (+) atau di bawah (-) tren. Nilainya sama untuk bulan yang sama tiap tahun.",
                            "Rata-rata (data - tren) untuk bulan kalender yang sama, lalu dipusatkan agar jumlah setahun = 0."),
            "Residual_Kg": ("Sisa yang tidak terjelaskan tren maupun musim (kg).", "Total_Kuantitas_Kg - Trend_Kg - Seasonal_Kg."),
        },
    },
    # ----------------------------- script 06 --------------------------------
    "06_training_set.csv": {
        "oleh": "06_pemodelan_forecasting.py",
        "isi": "Data latih (training): 75% data pertama secara urutan waktu, dipakai untuk membangun model.",
        "baris": "satu bulan (Januari 2023 - Maret 2025, 27 bulan).",
        "kolom": {},
    },
    "06_testing_set.csv": {
        "oleh": "06_pemodelan_forecasting.py",
        "isi": "Data uji (testing): 25% data terakhir, disembunyikan dari model lalu dipakai untuk mengukur ketepatan ramalan.",
        "baris": "satu bulan (April 2025 - Desember 2025, 9 bulan).",
        "kolom": {},
    },
    "06_hasil_estimasi.csv": {
        "oleh": "06_pemodelan_forecasting.py",
        "isi": "Hasil estimasi seluruh 28 kandidat model (ARIMA, SARIMA, ARIMAX) pada data latih, lengkap dengan ukuran kecocokan dan catatan proses estimasi.",
        "baris": "satu kandidat model.",
        "kolom": _KOL_ESTIMASI,
    },
    "06_perbandingan_aic_bic.csv": {
        "oleh": "06_pemodelan_forecasting.py",
        "isi": "Hasil estimasi 28 kandidat model yang sudah diberi peringkat AIC dan BIC di dalam kelompok pembedaannya (d, D). Peringkat 1 = kandidat terbaik di kelompok itu.",
        "baris": "satu kandidat model, diurutkan per kelompok lalu peringkat AIC.",
        "kolom": _KOL_ESTIMASI,
    },
    "06_cek_model_bersarang.csv": {
        "oleh": "06_pemodelan_forecasting.py",
        "isi": "Pemeriksaan kewajaran estimasi: model yang lebih rumit seharusnya tidak lebih buruk kecocokannya daripada model sederhana yang tercakup di dalamnya.",
        "baris": "satu pasangan model (sederhana vs lebih rumit).",
        "kolom": {
            "Model_Sederhana": ("Model yang lebih sederhana dalam pasangan.", "Kandidat yang ordenya dan eksogennya tercakup dalam Model_Kompleks."),
            "Model_Kompleks": ("Model yang lebih rumit dalam pasangan.", "Kandidat dengan orde/eksogen lebih banyak, pembedaan sama."),
            "LogL_Sederhana": ("Log-likelihood model sederhana.", "Dari hasil estimasi."),
            "LogL_Kompleks": ("Log-likelihood model rumit.", "Dari hasil estimasi."),
            "Selisih_LogL": ("Kenaikan kecocokan dari model sederhana ke model rumit. Seharusnya 0 atau positif.",
                             "LogL_Kompleks - LogL_Sederhana."),
            "Pelanggaran": ("Ya = model rumit justru lebih buruk (estimasi belum optimal); Tidak = wajar.",
                            "Ya bila LogL_Kompleks lebih kecil dari LogL_Sederhana melebihi toleransi 0,001."),
        },
    },
    # ----------------------------- script 07 --------------------------------
    "07_parameter_estimasi.csv": {
        "oleh": "07_validasi_diagnostik_evaluasi.py",
        "isi": "Nilai parameter (koefisien) seluruh 28 kandidat model beserta uji signifikansinya. Menjawab: seberapa besar dan seberapa nyata pengaruh tiap komponen model.",
        "baris": "satu parameter dari satu model.",
        "kolom": {
            "P_value": ("Peluang koefisien sebesar itu muncul hanya karena kebetulan. Di bawah 0,05 = pengaruhnya nyata (signifikan).",
                        "Dari nilai z dengan sebaran normal baku."),
        },
    },
    "07_cek_optimum_lokal.csv": {
        "oleh": "07_validasi_diagnostik_evaluasi.py",
        "isi": "Catatan proses pencarian parameter tiap model dengan beberapa cara (optimizer). Menunjukkan apakah cara bawaan (lbfgs) terjebak di hasil yang belum terbaik.",
        "baris": "satu kandidat model.",
        "kolom": {
            "LogL_06": ("Log-likelihood model menurut script 06.", "Diambil dari 06_perbandingan_aic_bic.csv."),
            "LogL_07": ("Log-likelihood model saat diestimasi ulang di script 07 (seharusnya sama dengan LogL_06).",
                        "Hasil estimasi ulang dengan pengaturan yang sama."),
            "Perbaikan_vs_lbfgs_default": ("Kenaikan log-likelihood berkat mencoba beberapa optimizer dibanding lbfgs saja.",
                                           "LogL_07 - LogL_lbfgs."),
            "Optimum_lokal_lbfgs": ("Ya = lbfgs saja terjebak di hasil yang belum terbaik (dan sudah diperbaiki); Tidak = lbfgs sudah cukup.",
                                    "Ya bila Perbaikan_vs_lbfgs_default lebih dari 0,01."),
            "Warning_Fit": ("Peringatan dari statsmodels saat estimasi. Tanda - berarti tidak ada.", "Dicatat otomatis saat estimasi."),
        },
    },
    "07_shortlist.csv": {
        "oleh": "07_validasi_diagnostik_evaluasi.py",
        "isi": "Daftar pendek 5 model: satu model terbaik (AIC terendah) dari tiap skenario. Lima model inilah yang diuji lebih lanjut.",
        "baris": "satu model terpilih per skenario.",
        "kolom": {},
    },
    "07_diagnostik_residual.csv": {
        "oleh": "07_validasi_diagnostik_evaluasi.py",
        "isi": "Uji kelayakan 5 model shortlist dari sisa (residual)-nya. Model yang baik menyisakan galat yang tidak berpola (Ljung-Box) dan menyebar normal (Shapiro-Wilk).",
        "baris": "satu model shortlist.",
        "kolom": {
            "Residual_Dibuang_Burn": ("Banyaknya residual awal yang tidak dipakai uji (12 pada model D=1).",
                                      "Sama dengan loglikelihood_burn model."),
            "Jumlah_Residual": ("Banyaknya residual yang diuji.", "Jumlah data latih - Residual_Dibuang_Burn."),
            "model_df": ("Banyaknya koefisien AR dan MA model (pengurang derajat bebas Ljung-Box).", "p + q + P + Q."),
            "LB_lag_diuji": ("Daftar lag Ljung-Box yang diuji.", "Lag 6, 9, 12 yang derajat bebasnya positif dan lebih kecil dari jumlah residual."),
            "LB_lag_dilewati": ("Daftar lag yang tidak bisa diuji. Tanda - berarti tidak ada.",
                                "Lag dengan derajat bebas 0 atau kurang, atau tidak lebih kecil dari jumlah residual."),
            "Ljung_Box": ("Kesimpulan Ljung-Box: Lulus = residual tidak berpola (white noise); Gagal = masih ada pola.",
                          "Lulus bila P-value semua lag yang diuji tidak di bawah 0,05."),
            "Shapiro_W": ("Statistik uji Shapiro-Wilk (0-1). Makin dekat 1 makin mirip sebaran normal.",
                          "Uji Shapiro-Wilk (scipy) pada residual."),
            "Shapiro_p": ("P-value Shapiro-Wilk. Di atas 0,05 = residual menyebar normal.", "Dari statistik Shapiro_W."),
            "Shapiro_Wilk": ("Kesimpulan Shapiro-Wilk: Lulus = residual normal; Gagal = tidak normal.",
                             "Lulus bila Shapiro_p di atas 0,05."),
        },
    },
    "07_rolling_origin_prediksi.csv": {
        "oleh": "07_validasi_diagnostik_evaluasi.py",
        "isi": "Hasil uji rolling origin: model dilatih, meramal 1 bulan ke depan, lalu data aktual bulan itu ditambahkan dan model dilatih ulang; diulang 9 kali (April - Desember 2025).",
        "baris": "satu ramalan 1 bulan dari satu model pada satu putaran.",
        "kolom": {
            "Putaran": ("Urutan putaran uji (1-9).", "Putaran 1 meramal April 2025, putaran 9 meramal Desember 2025."),
            "Panjang_Data_Latih": ("Banyaknya bulan data yang dipakai melatih model pada putaran itu.", "27 + (Putaran - 1)."),
            "Periode_Target": ("Bulan yang diramal pada putaran itu.", "Satu bulan setelah data latih putaran itu."),
            "Aktual": ("Permintaan sebenarnya pada bulan target (kg).", "Dari data testing."),
            "Prediksi": ("Ramalan 1 bulan ke depan (kg).",
                         "exp(ramalan log model). ARIMAX memakai harga aktual bulan target. Seasonal naive = aktual 12 bulan sebelumnya."),
            "Error": ("Selisih kenyataan dan ramalan (kg). Positif = ramalan terlalu rendah.", "Aktual - Prediksi."),
            "APE_%": ("Besar kesalahan ramalan putaran itu dalam persen.", "|Aktual - Prediksi| / Aktual x 100."),
            "Optimizer": ("Cara pencarian parameter yang dipakai pada putaran itu. Tanda - untuk seasonal naive.",
                          "Optimizer dengan hasil terbaik saat melatih ulang."),
        },
    },
    "07_metrik_rolling_origin.csv": {
        "oleh": "07_validasi_diagnostik_evaluasi.py",
        "isi": "Rapor ketepatan tiap model pada uji rolling origin (9 ramalan 1 bulan ke depan) dan kelulusannya terhadap target akurasi. Diurutkan dari MAPE terkecil.",
        "baris": "satu model (termasuk pembanding seasonal naive).",
        "kolom": {
            "APE_std_%": ("Simpangan baku kesalahan persen antar putaran: makin kecil berarti ketepatan makin konsisten.",
                          "Simpangan baku APE_% dari 9 putaran."),
            "Lebih_baik_dari_naive": ("Ya = model lebih tepat daripada cara sederhana (sama dengan tahun lalu); - untuk baris seasonal naive.",
                                      "Ya bila MAPE_% model lebih kecil dari MAPE_% seasonal naive."),
        },
    },
    # ----------------------------- script 08 --------------------------------
    "08_cek_data_testing.csv": {
        "oleh": "08_forecasting_data_testing.py",
        "isi": "Daftar pemeriksaan bahwa data uji (testing) lengkap dan pembagian data latih/uji benar sebelum dipakai meramal.",
        "baris": "satu butir pemeriksaan.",
        "kolom": {
            "Pemeriksaan": ("Hal yang diperiksa.", "Daftar pemeriksaan tetap di script 08."),
            "Hasil": ("Temuan pemeriksaan.", "Dihitung dari 06_training_set.csv dan 06_testing_set.csv."),
            "Lulus": ("Ya = sesuai yang diharapkan; Tidak = ada masalah.", "Membandingkan temuan dengan syaratnya."),
        },
    },
    "08_model_peramalan.csv": {
        "oleh": "08_forecasting_data_testing.py",
        "isi": "Daftar model yang lulus kedua uji residual (Ljung-Box dan Shapiro-Wilk) sehingga boleh dipakai meramal data testing.",
        "baris": "satu model yang lulus.",
        "kolom": _KOL_SHORTLIST,
    },
    "08_peramalan_testing.csv": {
        "oleh": "08_forecasting_data_testing.py",
        "isi": "Ramalan 9 bulan sekaligus (April - Desember 2025) dari model yang dilatih hanya dengan 27 bulan data latih, dibandingkan dengan angka sebenarnya.",
        "baris": "satu bulan ramalan dari satu model.",
        "kolom": {
            "Prediksi_Kg": ("Ramalan permintaan (kg), berupa nilai tengah (median).",
                            "exp(ramalan log). Seasonal naive = aktual bulan yang sama tahun lalu."),
            "Prediksi_Mean_Lognormal_Kg": ("Ramalan versi rata-rata (kg), sedikit lebih tinggi dari Prediksi_Kg. Hanya pembanding.",
                                           "exp(ramalan log + 0,5 x ragam ramalan)."),
            "Lebar_CI_Kg": ("Lebar interval kepercayaan 95% (kg). Makin lebar makin tidak pasti.",
                            "Batas_Atas_95_Kg - Batas_Bawah_95_Kg."),
            "SE_Skala_Transformasi": ("Galat baku ramalan pada skala logaritma (ukuran ketidakpastian).",
                                      "Dihitung model; membesar seiring jauhnya bulan yang diramal."),
            "Error_Kg": ("Selisih kenyataan dan ramalan (kg). Positif = ramalan terlalu rendah.", "Aktual_Kg - Prediksi_Kg."),
            "APE_%": ("Besar kesalahan ramalan bulan itu dalam persen.", "|Aktual_Kg - Prediksi_Kg| / Aktual_Kg x 100."),
            "Dalam_CI_95": ("Ya = angka sebenarnya berada di dalam interval 95%; Tidak = di luar; - = tidak ada interval (seasonal naive).",
                            "Memeriksa Batas_Bawah_95_Kg <= Aktual_Kg <= Batas_Atas_95_Kg."),
        },
    },
    "08_evaluasi_peramalan.csv": {
        "oleh": "08_forecasting_data_testing.py",
        "isi": "Rapor ketepatan tiap model untuk ramalan 9 bulan sekaligus pada data testing (April - Desember 2025) dan kelulusannya terhadap target akurasi. Diurutkan dari MAPE terkecil.",
        "baris": "satu model (termasuk pembanding seasonal naive).",
        "kolom": {
            "Bulan_APE_maks": ("Bulan dengan kesalahan persen terbesar.", "Periode dengan APE_% tertinggi."),
            "Bias_rata2_Kg": ("Kecenderungan arah kesalahan (kg). Positif = ramalan cenderung terlalu rendah; negatif = cenderung terlalu tinggi.",
                              "Rata-rata Error_Kg (Aktual - Prediksi) dari 9 bulan."),
            "MAPE_mean_lognormal_%": ("MAPE bila memakai ramalan versi rata-rata (Prediksi_Mean_Lognormal_Kg). Hanya pembanding.",
                                      "Rata-rata kesalahan persen dari ramalan versi rata-rata."),
            "Cakupan_CI_95_%": ("Persentase bulan yang angka sebenarnya masuk interval 95% (idealnya sekitar 95).",
                                "Jumlah bulan Dalam_CI_95 = Ya / 9 x 100."),
            "Jumlah_Dalam_CI": ("Banyaknya bulan yang angka sebenarnya masuk interval, dari 9 bulan.", "Menghitung Dalam_CI_95 = Ya."),
            "Lebar_CI_rata2_Kg": ("Rata-rata lebar interval 95% (kg).", "Rata-rata Lebar_CI_Kg."),
            "Lebar_CI_rata2_%_aktual": ("Rata-rata lebar interval dibanding angka sebenarnya (persen).",
                                        "Rata-rata (Lebar_CI_Kg / Aktual_Kg) x 100."),
        },
    },
    "08_multistep_vs_rolling.csv": {
        "oleh": "08_forecasting_data_testing.py",
        "isi": "Perbandingan dua cara meramal data testing: sekaligus 9 bulan (multi-step, script 08) dan 1 bulan dengan latih ulang tiap bulan (rolling origin, script 07).",
        "baris": "satu bulan dari satu model.",
        "kolom": {
            "Prediksi_MultiStep_Kg": ("Ramalan cara sekaligus 9 bulan (kg).", "Prediksi_Kg dari 08_peramalan_testing.csv."),
            "APE_MultiStep_%": ("Kesalahan persen ramalan cara sekaligus.", "|Aktual - Prediksi_MultiStep| / Aktual x 100."),
            "Prediksi_Rolling_Kg": ("Ramalan cara 1 bulan dengan latih ulang (kg).", "Prediksi dari 07_rolling_origin_prediksi.csv."),
            "APE_Rolling_%": ("Kesalahan persen ramalan cara rolling origin.", "|Aktual - Prediksi_Rolling| / Aktual x 100."),
            "Selisih_APE_poin": ("Beda kesalahan kedua cara (poin persen). Positif = cara sekaligus lebih meleset.",
                                 "APE_MultiStep_% - APE_Rolling_%."),
        },
    },
    # ----------------------------- script 09 --------------------------------
    "09_parameter_model_validasi.csv": {
        "oleh": "09_peramalan_visualisasi.py",
        "isi": "Parameter model final SARIMA(1,0,0)x(1,1,0,12) log bila dilatih dengan 27 bulan data latih saja (dipakai untuk validasi April - September 2025).",
        "baris": "satu parameter model.",
        "kolom": _KOL_PARAM_FINAL,
    },
    "09_peramalan_validasi_apr_sep_2025.csv": {
        "oleh": "09_peramalan_visualisasi.py",
        "isi": "Validasi model final: model dilatih dengan 27 bulan, meramal 6 bulan (April - September 2025), lalu dibandingkan dengan angka sebenarnya yang sudah diketahui.",
        "baris": "satu bulan yang diramal.",
        "kolom": _KOL_RAMALAN_09,
    },
    "09_parameter_model_final.csv": {
        "oleh": "09_peramalan_visualisasi.py",
        "isi": "Parameter model final SARIMA(1,0,0)x(1,1,0,12) log yang dilatih dengan seluruh 36 bulan data. Parameter inilah yang dipakai meramal 2026 dan dipasang di MS Access.",
        "baris": "satu parameter model.",
        "kolom": _KOL_PARAM_FINAL,
    },
    "09_diagnostik_model_final.csv": {
        "oleh": "09_peramalan_visualisasi.py",
        "isi": "Uji kelayakan model final (dilatih 36 bulan) dari sisa (residual)-nya: tidak berpola (Ljung-Box) dan menyebar normal (Shapiro-Wilk).",
        "baris": "satu uji.",
        "kolom": {
            "Jumlah_Residual": ("Banyaknya residual yang diuji.", "36 bulan dikurangi 12 bulan awal yang terpakai pembedaan musiman."),
            "Uji": ("Nama uji dan lag-nya.", "Ljung-Box lag 6, 9, 12 dan Shapiro-Wilk."),
            "Statistik": ("Nilai statistik uji (Q untuk Ljung-Box, W untuk Shapiro-Wilk).", "Dihitung dari residual model final."),
            "df": ("Derajat bebas uji Ljung-Box. Kosong untuk Shapiro-Wilk.", "Lag - banyaknya koefisien AR/MA model (2)."),
            "P_value": ("P-value uji. Di atas 0,05 = lulus.", "Dari statistik uji."),
            "Keputusan": ("Lulus (white noise) = residual tidak berpola; Lulus (normal) = residual normal; Gagal = syarat tidak terpenuhi.",
                          "Lulus bila P_value di atas 0,05."),
        },
    },
    "09_peramalan_jan_jun_2026.csv": {
        "oleh": "09_peramalan_visualisasi.py",
        "isi": "HASIL UTAMA PENELITIAN: ramalan permintaan daging kambing Kabupaten Malang Januari - Juni 2026 dari model final SARIMA(1,0,0)x(1,1,0,12) log, beserta interval kepercayaan 95%.",
        "baris": "satu bulan yang diramal.",
        "kolom": _KOL_RAMALAN_09,
    },
    # ----------------------------- script 10 --------------------------------
    "01_hasil_adf.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Hasil uji stasioneritas ADF pada data permintaan asli. Stasioner = rata-rata dan ragam data stabil sepanjang waktu, sehingga tidak perlu pembedaan (d = 0).",
        "baris": "satu seri data yang diuji.",
        "kolom": _KOL_ADF,
    },
    "02_hasil_differencing.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Hasil uji stasioneritas ADF pada data asli dan beberapa bentuk pembedaan (differencing), beserta keterangan bentuk mana yang dipakai model.",
        "baris": "satu bentuk data yang diuji.",
        "kolom": _KOL_ADF,
    },
    "02_seri_differencing.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Data permintaan dalam beberapa bentuk: asli, selisih dengan bulan sebelumnya, selisih dengan 12 bulan sebelumnya, logaritma, dan selisih musiman logaritma (bentuk yang dipakai model final).",
        "baris": "satu bulan (Januari 2023 - Desember 2025).",
        "kolom": {
            "Asli_Kg": ("Permintaan asli bulan itu (kg).", "Total_Kuantitas_Kg."),
            "Diff1_Kg": ("Perubahan dari bulan sebelumnya (kg). Kosong pada bulan pertama.", "Asli bulan ini - Asli bulan lalu."),
            "Diff12_Kg": ("Perubahan dari bulan yang sama tahun lalu (kg). Kosong pada 12 bulan pertama.",
                          "Asli bulan ini - Asli 12 bulan sebelumnya."),
            "Log": ("Logaritma natural permintaan.", "ln(Asli_Kg)."),
            "Diff12_Log": ("Perubahan logaritma dari bulan yang sama tahun lalu (kira-kira persen perubahan tahunan). Bentuk yang dipakai model final.",
                           "ln(Asli bulan ini) - ln(Asli 12 bulan sebelumnya)."),
        },
    },
    "03_tabel_acf_pacf.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Nilai ACF dan PACF data permintaan asli per lag (jarak bulan). Dipakai untuk melihat pola musiman dan memilih orde model; nilai besar di lag 12 menandakan pola tahunan.",
        "baris": "satu lag (0 sampai 12 atau lebih).",
        "kolom": {
            "Lag_k": ("Jarak waktu dalam bulan (lag 12 = dibandingkan dengan 12 bulan sebelumnya).", "Urutan 0, 1, 2, ..."),
            "Nilai_ACF": ("Kekuatan hubungan data dengan dirinya sendiri k bulan sebelumnya (-1 sampai 1).",
                          "Fungsi autokorelasi (statsmodels)."),
            "ACF_Batas_Signifikansi": ("Ambang batas: ACF dianggap nyata bila besarnya melebihi angka ini.",
                                       "Setengah lebar selang kepercayaan 95% (rumus Bartlett)."),
            "ACF_Signifikan": ("True = hubungan pada lag itu nyata.", "True bila |Nilai_ACF| lebih besar dari ACF_Batas_Signifikansi."),
            "Nilai_PACF": ("Kekuatan hubungan langsung dengan k bulan sebelumnya setelah pengaruh lag di antaranya dihilangkan.",
                           "Fungsi autokorelasi parsial (metode Yule-Walker)."),
            "PACF_Batas_Signifikansi": ("Ambang batas: PACF dianggap nyata bila besarnya melebihi angka ini.",
                                        "Setengah lebar selang kepercayaan 95%."),
            "PACF_Signifikan": ("True = hubungan langsung pada lag itu nyata.",
                                "True bila |Nilai_PACF| lebih besar dari PACF_Batas_Signifikansi."),
        },
    },
    "04_ringkasan_pembagian_dataset.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Ringkasan pembagian data menjadi data latih (75%) dan data uji (25%) secara urutan waktu.",
        "baris": "satu bagian data (Training atau Testing).",
        "kolom": {
            "Bagian": ("Training = data untuk membangun model; Testing = data untuk menguji ramalan.", "Pembagian kronologis 75:25."),
            "Jumlah_Bulan": ("Banyaknya bulan pada bagian itu.", "Menghitung baris data."),
            "Proporsi_%": ("Porsi bagian itu dari seluruh data (persen).", "Jumlah_Bulan / 36 x 100."),
            "Periode_Awal": ("Bulan pertama bagian itu.", "Baris pertama."),
            "Periode_Akhir": ("Bulan terakhir bagian itu.", "Baris terakhir."),
            "Rata2_Kg": ("Rata-rata permintaan bulanan pada bagian itu (kg).", "Rata-rata Total_Kuantitas_Kg."),
            "Bulan_Iduladha": ("Daftar bulan Iduladha yang termasuk bagian itu.", "Bulan dengan Koefisien_Musim lebih dari 1."),
        },
    },
    "05_daftar_kandidat_skenario.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Daftar 28 kandidat model yang dicoba, dikelompokkan menurut skenario pemodelan.",
        "baris": "satu kandidat model.",
        "kolom": {
            "Skenario_Detail": ("Skenario lebih rinci: ARIMA, SARIMA, ARIMAX Harga, atau ARIMAX Harga+Iduladha.",
                                "Dari Skenario dan variabel eksogennya."),
            "Status": ("Berhasil = model selesai diestimasi; Gagal = tidak berhasil.", "Dari 06_hasil_estimasi.csv."),
        },
    },
    "05_ringkasan_skenario.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Ringkasan jumlah kandidat model per skenario dan kelompok pembedaan.",
        "baris": "satu skenario dalam satu kelompok pembedaan.",
        "kolom": {
            "Skenario_Detail": ("Nama skenario pemodelan.", "Dari Skenario dan variabel eksogennya."),
            "Jumlah_Kandidat": ("Banyaknya kandidat model pada skenario itu.", "Menghitung baris 05_daftar_kandidat_skenario.csv."),
            "Berhasil": ("Banyaknya kandidat yang berhasil diestimasi.", "Menghitung Status = Berhasil."),
        },
    },
    "06_fitted_training.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Perbandingan data latih yang sebenarnya dengan nilai yang dihasilkan tiap model shortlist untuk bulan yang sama (fitted). Makin dekat dengan aktual makin baik model meniru data latih.",
        "baris": "satu bulan data latih (Januari 2023 - Maret 2025).",
        "kolom": {"Aktual_Kg": ("Permintaan sebenarnya bulan itu (kg).", "Total_Kuantitas_Kg data latih.")},
    },
    "08_residual_training.csv": {
        "oleh": "10_ekspor_output_laporan.py",
        "isi": "Sisa (residual) tiap model shortlist pada data latih, dalam skala logaritma. Dipakai untuk uji Ljung-Box, Shapiro-Wilk, dan Q-Q plot.",
        "baris": "satu bulan data latih (Januari 2023 - Maret 2025).",
        "kolom": {},
    },
    # ------------------------ script 11 (implementasi Access) ----------------
    "11_verifikasi_access_vs_python.csv": {
        "oleh": "11_implementasi_access.py",
        "isi": "Bukti bahwa angka ramalan yang dihitung MS Access sama dengan yang dihitung Python (statsmodels). Selisih mendekati nol berarti rumus di Access benar.",
        "baris": "satu angka yang dibandingkan (satu besaran pada satu bulan).",
        "kolom": {
            "Uji": ("Jenis pembandingan yang dilakukan.", "Tiga uji: ramalan bulan depan, ramalan 6 bulan, dan ramalan 1 bulan historis."),
            "Besaran": ("Angka yang dibandingkan: ramalan, batas bawah, atau batas atas.", "Nama kolom hasil di Access."),
            "Access": ("Nilai hasil hitungan MS Access (kg).", "Dibaca dari query/tabel di database Access."),
            "Python": ("Nilai hasil hitungan Python statsmodels (kg).", "Dari 09_peramalan_jan_jun_2026.csv atau prediksi 1 langkah statsmodels."),
            "Aktual_Kg": ("Permintaan sebenarnya bulan itu (kg); hanya diisi pada uji historis.", "Dari data permintaan."),
            "Selisih": ("Beda hasil Access dan Python (kg). Mendekati 0 = sama.", "Access - Python."),
            "Selisih_Relatif_%": ("Beda hasil dalam persen terhadap hasil Python.", "Selisih / Python x 100."),
        },
    },
    "11_objek_access.csv": {
        "oleh": "11_implementasi_access.py",
        "isi": "Daftar objek (tabel, query, modul, backup) yang dibuat script di database MS Access.",
        "baris": "satu objek.",
        "kolom": {
            "Jenis": ("Jenis objek: Tabel, Query, Modul VBA, atau Backup database.", "Ditetapkan script 11."),
            "Nama": ("Nama objek di MS Access atau nama filenya.", "Ditetapkan script 11."),
        },
    },
    # ------------------------ script 11 (rekomendasi) ------------------------
    "11_rek_stok_testing.csv": {
        "oleh": "11_rekomendasi_manajerial.py",
        "isi": "Simulasi manfaat ramalan untuk perencanaan stok selama 9 bulan testing (April - Desember 2025): rencana stok mengikuti ramalan model dibanding cara lama (disamakan dengan tahun lalu).",
        "baris": "satu cara merencanakan stok.",
        "kolom": {
            "Metode_Rencana_Stok": ("SARIMA D=1 = stok mengikuti ramalan model final; Seasonal naive = stok disamakan dengan bulan yang sama tahun lalu.",
                                    "Dua cara yang dibandingkan."),
            "Total_Aktual_Kg": ("Total permintaan sebenarnya selama 9 bulan (kg).", "Jumlah Aktual_Kg 9 bulan."),
            "Total_Rencana_Kg": ("Total stok yang direncanakan selama 9 bulan (kg).", "Jumlah ramalan 9 bulan."),
            "Kelebihan_Stok_Kg": ("Total stok berlebih (kg) pada bulan-bulan ketika rencana di atas kenyataan.",
                                  "Jumlah (Rencana - Aktual) untuk bulan yang Rencana lebih besar."),
            "Kekurangan_Stok_Kg": ("Total kekurangan stok (kg) pada bulan-bulan ketika rencana di bawah kenyataan.",
                                   "Jumlah (Aktual - Rencana) untuk bulan yang Aktual lebih besar."),
            "Bulan_Kelebihan": ("Banyaknya bulan yang stoknya berlebih.", "Menghitung bulan dengan Rencana lebih besar dari Aktual."),
            "Bulan_Kekurangan": ("Banyaknya bulan yang stoknya kurang.", "Menghitung bulan dengan Aktual lebih besar dari Rencana."),
            "Total_Selisih_Absolut_Kg": ("Total selisih rencana dan kenyataan tanpa melihat arah (kg). Makin kecil makin baik.",
                                         "Kelebihan_Stok_Kg + Kekurangan_Stok_Kg."),
        },
    },
    "11_rek_stok_per_bulan.csv": {
        "oleh": "11_rekomendasi_manajerial.py",
        "isi": "Rincian per bulan untuk simulasi stok: permintaan sebenarnya dibanding rencana stok dari dua cara.",
        "baris": "satu bulan testing (April - Desember 2025).",
        "kolom": {
            "SARIMA D=1": ("Rencana stok bila mengikuti ramalan model final (kg).", "Prediksi_Kg model SARIMA D=1 dari 08_peramalan_testing.csv."),
            "Seasonal naive": ("Rencana stok bila disamakan dengan bulan yang sama tahun lalu (kg).", "Permintaan aktual 12 bulan sebelumnya."),
        },
    },
    "11_rek_indeks_kebutuhan_2026.csv": {
        "oleh": "11_rekomendasi_manajerial.py",
        "isi": "Indeks kebutuhan pasokan Januari - Juni 2026: perbandingan ramalan tiap bulan terhadap rata-rata, untuk merencanakan pasokan ternak dan pakan.",
        "baris": "satu bulan yang diramal.",
        "kolom": {
            "Ramalan_Kg": ("Ramalan permintaan bulan itu (kg).", "Yhat_Kg dari 09_peramalan_jan_jun_2026.csv."),
            "Indeks_vs_Rata2_6_Bulan": ("Perbandingan dengan rata-rata 6 bulan (1 = sama dengan rata-rata; 2 = dua kali lipat).",
                                        "Ramalan_Kg / rata-rata Ramalan_Kg 6 bulan."),
            "Indeks_vs_Bulan_Normal": ("Perbandingan dengan bulan normal (1 = seperti bulan biasa; 2,57 = 2,57 kali bulan biasa).",
                                       "Ramalan_Kg / rata-rata Ramalan_Kg bulan-bulan selain bulan puncak."),
            "Batas_Atas_95_Kg": ("Batas atas interval 95% (kg), acuan kapasitas maksimum.", "Dari 09_peramalan_jan_jun_2026.csv."),
        },
    },
    "11_rek_kapasitas_puncak.csv": {
        "oleh": "11_rekomendasi_manajerial.py",
        "isi": "Kebutuhan kapasitas pada bulan puncak (Iduladha) 2026 dan bukti dari validasi Juni 2025 bahwa batas atas ramalan mampu menampung lonjakan sebenarnya.",
        "baris": "satu baris ringkasan bulan puncak.",
        "kolom": {
            "Periode_Puncak": ("Bulan dengan ramalan tertinggi.", "Bulan dengan Yhat_Kg terbesar pada ramalan 2026."),
            "Ramalan_Puncak_Kg": ("Ramalan permintaan bulan puncak (kg).", "Yhat_Kg bulan puncak."),
            "Batas_Atas_95_Kg": ("Batas atas interval 95% bulan puncak (kg) = kapasitas yang sebaiknya disiapkan.",
                                 "Dari 09_peramalan_jan_jun_2026.csv."),
            "Stok_Pengaman_Kg": ("Tambahan stok di atas ramalan untuk berjaga-jaga (kg).", "Batas_Atas_95_Kg - Ramalan_Puncak_Kg."),
            "Validasi_Juni_2025_Ramalan_Kg": ("Ramalan Juni 2025 pada tahap validasi (kg).", "Yhat_Kg Juni 2025 dari 09_peramalan_validasi_apr_sep_2025.csv."),
            "Validasi_Juni_2025_Batas_Atas_Kg": ("Batas atas ramalan Juni 2025 pada tahap validasi (kg).", "Dari file validasi yang sama."),
            "Validasi_Juni_2025_Aktual_Kg": ("Permintaan sebenarnya Juni 2025 (kg).", "Dari file validasi yang sama."),
            "Validasi_Juni_2025_Dalam_Interval": ("Ya = permintaan sebenarnya Juni 2025 masuk interval ramalan.", "Dari file validasi yang sama."),
        },
    },
    "11_rek_panduan_umkm_2026.csv": {
        "oleh": "11_rekomendasi_manajerial.py",
        "isi": "Panduan untuk UMKM: ramalan tingkat kabupaten diubah menjadi angka perbandingan (indeks) yang bisa dipakai usaha skala berapa pun. Rencana stok = penjualan bulan normal x indeks.",
        "baris": "satu bulan yang diramal (Januari - Juni 2026).",
        "kolom": {
            "Indeks_vs_Bulan_Normal": ("Pengali terhadap penjualan bulan normal (1 = seperti biasa; 2,57 = siapkan 2,57 kali biasanya).",
                                       "Ramalan bulan itu / rata-rata ramalan bulan-bulan selain bulan puncak."),
            "Perubahan_vs_Tahun_Lalu_%": ("Perkiraan perubahan dibanding bulan yang sama tahun 2025 (persen; negatif = turun).",
                                          "(Ramalan / aktual bulan yang sama tahun lalu - 1) x 100."),
            "Faktor_Batas_Bawah": ("Pengali untuk skenario terendah yang masih wajar.", "Batas_Bawah_95_Kg / Yhat_Kg."),
            "Faktor_Batas_Atas": ("Pengali untuk skenario tertinggi yang masih wajar (untuk kapasitas maksimum).", "Batas_Atas_95_Kg / Yhat_Kg."),
            "Stok_Pengaman_%": ("Tambahan stok berjaga-jaga di atas rencana (persen).", "(Batas_Atas_95_Kg / Yhat_Kg - 1) x 100."),
        },
    },
    "11_rek_harga_historis.csv": {
        "oleh": "11_rekomendasi_manajerial.py",
        "isi": "Perbandingan harga dan volume antara bulan Iduladha dan bulan biasa pada data 2023-2025, sebagai dasar saran harga/margin.",
        "baris": "satu kategori bulan (Bulan Iduladha atau Bulan biasa).",
        "kolom": {
            "Kategori": ("Kelompok bulan.", "Bulan Iduladha bila Koefisien_Musim lebih dari 1; selain itu Bulan biasa."),
            "Jumlah_Bulan": ("Banyaknya bulan pada kategori itu.", "Menghitung bulan."),
            "Harga_Rata2_Per_Kg": ("Rata-rata harga per kg pada kategori itu (rupiah).", "Rata-rata Harga_Rata2_Per_Kg bulanan."),
            "Harga_Min": ("Harga rata-rata bulanan terendah (rupiah).", "Nilai terkecil Harga_Rata2_Per_Kg bulanan."),
            "Harga_Maks": ("Harga rata-rata bulanan tertinggi (rupiah).", "Nilai terbesar Harga_Rata2_Per_Kg bulanan."),
            "Volume_Rata2_Kg": ("Rata-rata permintaan bulanan pada kategori itu (kg).", "Rata-rata Total_Kuantitas_Kg."),
            "Selisih_vs_Bulan_Biasa_%": ("Seberapa lebih mahal dibanding bulan biasa (persen).",
                                         "(Harga kategori / harga Bulan biasa - 1) x 100."),
        },
    },
    # ----------------------------- script 12 --------------------------------
    "12_hasil_qry_12_Ramalan_6_Bulan_access.csv": {
        "oleh": "12_ramalan_6_bulan_access.py",
        "isi": "Hasil query MS Access qry_12_Ramalan_6_Bulan: ramalan 6 bulan ke depan yang dihitung sepenuhnya di dalam MS Access (tanpa Python).",
        "baris": "satu bulan yang diramal.",
        "kolom": _KOL_RAMAL_12,
    },
    "12_uji_dinamis_ramalan_feb_jul_2026.csv": {
        "oleh": "12_ramalan_6_bulan_access.py",
        "isi": "Uji bahwa ramalan di MS Access otomatis bergeser saat data baru diisi: pada SALINAN database ditambahkan data contoh Januari 2026 (ramalan Januari + 5%), hasilnya ramalan menjadi Februari - Juli 2026.",
        "baris": "satu bulan yang diramal setelah data contoh ditambahkan.",
        "kolom": _KOL_RAMAL_12,
    },
    "12_verifikasi_ramalan_6_bulan.csv": {
        "oleh": "12_ramalan_6_bulan_access.py",
        "isi": "Bukti bahwa ramalan 6 bulan dari query MS Access sama dengan hasil Python. Selisih mendekati nol berarti query Access benar.",
        "baris": "satu angka yang dibandingkan (satu besaran pada satu bulan).",
        "kolom": {
            "Uji": ("Jenis pembandingan: Access asli (DAO) vs statsmodels, driver ODBC vs statsmodels, atau uji dinamis di salinan database.",
                    "Tiga uji di script 12."),
            "Besaran": ("Angka yang dibandingkan: ramalan, batas bawah, atau batas atas.", "Nama kolom hasil query."),
            "Access_DAO": ("Nilai dari MS Access asli (mesin DAO) (kg). Kosong bila uji tidak memakainya.", "Menjalankan query lewat MS Access."),
            "Access_ODBC": ("Nilai dari driver ODBC Access (kg). Kosong bila uji tidak memakainya.", "Menjalankan query lewat pyodbc."),
            "Python_statsmodels": ("Nilai pembanding dari Python statsmodels (kg).", "Dari 09_peramalan_jan_jun_2026.csv."),
            "Python_rumus_sama": ("Nilai pembanding dari Python dengan rumus yang sama seperti query (kg); dipakai pada uji dinamis.",
                                  "Rumus rekursif SARIMA dihitung ulang di Python dari data salinan database."),
            "Selisih_Relatif_%": ("Beda hasil Access dengan pembandingnya (persen). Mendekati 0 = sama.",
                                  "(nilai Access - nilai pembanding) / nilai pembanding x 100."),
        },
    },
    # ----------------------------- script 13 --------------------------------
    "13_peramalan_disesuaikan_iduladha.csv": {
        "oleh": "13_penyesuaian_iduladha.py",
        "isi": "Ramalan 2026 setelah puncak Iduladha digeser ke bulan Iduladha yang sebenarnya. Model belajar dari data dengan Iduladha di bulan Juni, padahal Iduladha 2026 jatuh sekitar 27 Mei, jadi lonjakan dipindah ke Mei.",
        "baris": "satu bulan yang diramal (Januari - Juni 2026).",
        "kolom": {
            "Yhat_Kg": ("Ramalan asli model sebelum disesuaikan (kg).", "Dari 09_peramalan_jan_jun_2026.csv."),
            "Bobot_Iduladha": ("Porsi masa ramai Iduladha (7 hari sebelum sampai 3 hari sesudah) yang jatuh di bulan itu (0 sampai 1).",
                               "Jumlah hari masa ramai yang ada di bulan itu / 11 hari."),
            "Pengali_R": ("Pengali lonjakan Iduladha untuk bulan itu (1 = tidak ada lonjakan).",
                          "R pangkat Bobot_Iduladha; R = ramalan bulan lonjakan model / ramalan bulan normal sebelumnya."),
            "Dasar_Kg": ("Ramalan tanpa efek Iduladha (kg).", "Bulan lonjakan model: Yhat_Kg / R; bulan lain: sama dengan Yhat_Kg."),
            "Yhat_Disesuaikan_Kg": ("RAMALAN SETELAH DISESUAIKAN (kg): angka yang dipakai untuk perencanaan.", "Dasar_Kg x Pengali_R."),
            "Batas_Bawah_95_Disesuaikan_Kg": ("Batas bawah interval 95% setelah disesuaikan (kg).",
                                              "Batas bawah asli dilepas efek Iduladha-nya lalu dikali Pengali_R."),
            "Batas_Atas_95_Disesuaikan_Kg": ("Batas atas interval 95% setelah disesuaikan (kg); acuan kapasitas maksimum.",
                                             "Batas atas asli dilepas efek Iduladha-nya lalu dikali Pengali_R."),
            "Selisih_vs_Model_Kg": ("Perubahan akibat penyesuaian (kg). Positif = naik; negatif = turun.", "Yhat_Disesuaikan_Kg - Yhat_Kg."),
            "Indeks_vs_Bulan_Normal_Disesuaikan": ("Pengali terhadap bulan normal setelah disesuaikan (untuk UMKM).",
                                                   "Yhat_Disesuaikan_Kg / rata-rata Yhat_Disesuaikan_Kg bulan tanpa Iduladha."),
            "Faktor_Batas_Atas": ("Pengali untuk skenario tertinggi yang masih wajar.", "Batas_Atas_95_Disesuaikan_Kg / Yhat_Disesuaikan_Kg."),
        },
    },
    "13_bobot_jendela_iduladha.csv": {
        "oleh": "13_penyesuaian_iduladha.py",
        "isi": "Pembagian masa ramai Iduladha (7 hari sebelum sampai 3 hari sesudah hari raya = 11 hari) ke bulan kalender. Menentukan bulan mana yang menerima lonjakan.",
        "baris": "satu bulan yang terkena masa ramai Iduladha.",
        "kolom": {
            "Tahun": ("Tahun ramalan.", "Dari periode ramalan."),
            "Tanggal_Iduladha": ("Perkiraan tanggal Iduladha tahun itu.", "Daftar tanggal Iduladha di script 13."),
            "Periode": ("Bulan yang terkena masa ramai Iduladha.", "Bulan kalender dari hari-hari masa ramai."),
            "Bobot": ("Porsi masa ramai yang jatuh di bulan itu (1 = seluruhnya).", "Jumlah hari masa ramai di bulan itu / 11 hari."),
            "Dalam_Horizon": ("Ya = bulan itu termasuk bulan yang diramal; Tidak = di luar rentang ramalan.",
                              "Mencocokkan dengan periode ramalan Januari - Juni 2026."),
        },
    },
    # ------------------- ekspor objek MS Access (hasil_11/access_output) -----
    "Tbl_Parameter_SARIMA.csv": {
        "oleh": "ekspor tabel MS Access Tbl_Parameter_SARIMA",
        "isi": "Isi tabel Tbl_Parameter_SARIMA di MS Access: parameter model final yang dipakai query peramalan.",
        "baris": "satu parameter.",
        "kolom": {
            "Nama_Parameter": ("Nama parameter (ar.L1, ar.S.L12, sigma2, dan lainnya).", "Dari 09_parameter_model_final.csv."),
            "Nilai": ("Nilai parameter.", "Koefisien hasil estimasi Python (36 bulan data)."),
            "Keterangan": ("Penjelasan singkat parameter.", "Ditulis script 11."),
            "Nama_Model": ("Nama model final.", "Ditulis script 11."),
            "Tanggal_Training": ("Waktu parameter dimasukkan ke Access.", "Waktu script 11 dijalankan."),
            "Periode_Data": ("Rentang data yang dipakai melatih model.", "Ditulis script 11."),
        },
    },
    "Tbl_Peramalan.csv": {
        "oleh": "ekspor tabel MS Access Tbl_Peramalan",
        "isi": "Isi tabel Tbl_Peramalan di MS Access: ramalan 6 bulan yang disimpan script 11.",
        "baris": "satu bulan yang diramal.",
        "kolom": {
            "ID_Peramalan": ("Nomor urut baris.", "Nomor otomatis MS Access."),
            "Nama_Model": ("Nama model yang dipakai.", "Ditulis script 11."),
            "Prediksi_Kg": ("Ramalan permintaan (kg).", "Rumus rekursif SARIMA(1,0,0)x(1,1,0,12) log, sama dengan modul VBA."),
            "Sumber": ("Asal hitungan ramalan.", "Ditulis script 11."),
            "Tanggal_Dibuat": ("Waktu ramalan disimpan.", "Waktu script 11 dijalankan."),
        },
    },
    "qry_11_Faktor_Musiman.csv": {
        "oleh": "ekspor query MS Access qry_11_Faktor_Musiman",
        "isi": "Hasil query qry_11_Faktor_Musiman: perbandingan rata-rata permintaan tiap bulan kalender terhadap rata-rata seluruh bulan (informasi pendukung).",
        "baris": "satu bulan kalender (Januari - Desember).",
        "kolom": {
            "Nama_Bulan": ("Nama bulan.", "Dari nomor bulan."),
            "Rata2_Kg": ("Rata-rata permintaan bulan itu selama 2023-2025 (kg).", "Rata-rata Permintaan_Kg per bulan kalender."),
            "Faktor": ("Perbandingan dengan rata-rata seluruh bulan (di atas 1 = lebih ramai dari biasanya).",
                       "Rata2_Kg / rata-rata seluruh bulan."),
            "Keterangan": ("Penjelasan cara hitung.", "Teks tetap dari query."),
        },
    },
    "qry_11_Peramalan_6_Bulan.csv": {
        "oleh": "ekspor query MS Access qry_11_Peramalan_6_Bulan",
        "isi": "Hasil query qry_11_Peramalan_6_Bulan: tampilan ramalan 6 bulan dari Tbl_Peramalan dengan angka dibulatkan.",
        "baris": "satu bulan yang diramal.",
        "kolom": {
            "Bulan": ("Bulan yang diramal (nama bulan dan tahun).", "Dari Periode di Tbl_Peramalan."),
            "Ramalan_Kg": ("Ramalan permintaan (kg), dibulatkan.", "Prediksi_Kg di Tbl_Peramalan."),
            "Batas_Bawah_95": ("Batas bawah interval 95% (kg), dibulatkan.", "Batas_Bawah_95_Kg di Tbl_Peramalan."),
            "Batas_Atas_95": ("Batas atas interval 95% (kg), dibulatkan.", "Batas_Atas_95_Kg di Tbl_Peramalan."),
            "Nama_Model": ("Nama model yang dipakai.", "Dari Tbl_Peramalan."),
            "Sumber": ("Asal hitungan ramalan.", "Dari Tbl_Peramalan."),
            "Tanggal_Dibuat": ("Waktu ramalan disimpan.", "Dari Tbl_Peramalan."),
        },
    },
    "qry_11_Ramalan_1_Bulan_Historis.csv": {
        "oleh": "ekspor query MS Access qry_11_Ramalan_1_Bulan_Historis",
        "isi": "Hasil query qry_11_Ramalan_1_Bulan_Historis: ramalan 1 bulan ke depan untuk bulan-bulan yang sudah lewat, dihitung di MS Access (untuk dibandingkan dengan kenyataan).",
        "baris": "satu bulan yang diramal.",
        "kolom": _KOL_ACCESS_RAMAL,
    },
    "qry_11_Ramalan_Bulan_Depan.csv": {
        "oleh": "ekspor query MS Access qry_11_Ramalan_Bulan_Depan",
        "isi": "Hasil query qry_11_Ramalan_Bulan_Depan: ramalan untuk satu bulan setelah data terakhir, dihitung di MS Access.",
        "baris": "satu bulan yang diramal.",
        "kolom": _KOL_ACCESS_RAMAL,
    },
    "qry_11_Volume_Bulanan.csv": {
        "oleh": "ekspor query MS Access qry_11_Volume_Bulanan",
        "isi": "Hasil query qry_11_Volume_Bulanan: data permintaan bulanan di MS Access beserta logaritmanya (bahan hitung query peramalan).",
        "baris": "satu bulan data.",
        "kolom": {
            "Harga_Rata2_Per_Kg": ("Harga jual rata-rata per kg bulan itu (rupiah).", "Dari Tbl_Volume_Bulanan."),
            "Ln_Permintaan": ("Logaritma natural permintaan.", "Log(Permintaan_Kg) di MS Access."),
        },
    },
}


def cari_kolom(nama_file, kolom):
    """Mengembalikan (arti, diperoleh dari) untuk satu kolom pada satu file."""
    khusus = TABEL.get(nama_file, {}).get("kolom", {})
    if kolom in khusus:
        return khusus[kolom]
    if kolom in U:
        return U[kolom]
    for pola, (arti, asal) in POLA:
        cocok = re.match(pola, kolom)
        if cocok:
            return arti.format(*cocok.groups()), asal.format(*cocok.groups())
    return ("(keterangan belum tersedia)", "-")


def baris_keterangan(nama_file, kolom):
    """Menyusun baris-baris keterangan untuk satu file; kosong bila file tidak terdaftar."""
    info = TABEL.get(nama_file)
    if info is None:
        return []
    baris = [
        GARIS,
        f"# KETERANGAN TABEL : {nama_file} (dibuat oleh {info['oleh']})",
        f"# Isi tabel        : {info['isi']}",
        f"# Satu baris data  : {info['baris']}",
        "# Keterangan kolom : nomor. NAMA KOLOM = arti | Diperoleh dari: cara menghitung/sumbernya",
    ]
    for i, k in enumerate(kolom, start=1):
        arti, asal = cari_kolom(nama_file, str(k))
        baris.append(f"#   {i}. {k} = {arti} | Diperoleh dari: {asal}")
    baris += [
        "# Catatan          : baris berawalan tanda # adalah keterangan, bukan data. Tabel data dimulai tepat di bawah garis ini.",
        GARIS,
    ]
    return baris


def _baris_adalah_keterangan(teks):
    return teks.lstrip('"').startswith(TANDA)


def simpan_csv(df, path, **kw):
    """Pengganti df.to_csv(path, ...): menulis blok keterangan lalu tabel datanya."""
    path = Path(path)
    kolom = list(df.columns)
    if kw.get("index", True):
        kolom = [kw.get("index_label") or df.index.name or ""] + kolom
    with open(path, "w", encoding="utf-8", newline="") as f:
        tulis = csv.writer(f, quoting=csv.QUOTE_ALL)
        for baris in baris_keterangan(path.name, kolom):
            tulis.writerow([baris])
        df.to_csv(f, **kw)


def baca_csv(path, **kw):
    """Pengganti pd.read_csv(path, ...): melewati blok keterangan di awal file."""
    with open(path, "r", encoding=kw.pop("encoding", "utf-8"), newline="") as f:
        posisi = f.tell()
        while _baris_adalah_keterangan(f.readline()):
            posisi = f.tell()
        f.seek(posisi)
        return pd.read_csv(f, **kw)


def pasang_keterangan(path):
    """Memasang/memperbarui blok keterangan pada CSV yang sudah ada tanpa mengubah datanya."""
    path = Path(path)
    if path.name not in TABEL:
        return False
    with open(path, "r", encoding="utf-8", newline="") as f:
        data = f.readlines()
    while data and _baris_adalah_keterangan(data[0]):
        data = data[1:]
    if not data:
        return False
    kolom = next(csv.reader([data[0]]))
    with open(path, "w", encoding="utf-8", newline="") as f:
        tulis = csv.writer(f, quoting=csv.QUOTE_ALL)
        for baris in baris_keterangan(path.name, kolom):
            tulis.writerow([baris])
        f.writelines(data)
    return True


def main():
    data_dir = Path(__file__).resolve().parent / "data"
    for path in sorted(data_dir.rglob("*.csv")):
        if path.parent.name == "sumber_bps":
            continue
        status = "keterangan dipasang" if pasang_keterangan(path) else "dilewati (tidak terdaftar)"
        print(f"{path.relative_to(data_dir)} : {status}")


if __name__ == "__main__":
    sys.exit(main())
