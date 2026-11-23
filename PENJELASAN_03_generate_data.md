# Penjelasan Kode `03_generate_data.py`

Penjelasan seluruh isi [03_generate_data.py](03_generate_data.py), urut dari atas ke bawah.

## Gambaran besar

Program ini membuat data permintaan daging kambing sintetis **tingkat Kabupaten Malang (agregat)** selama 36 bulan (Januari 2023 – Desember 2025), dikalibrasi dari produksi **karkas** tahunan BPS. Volume tiap bulan dibentuk berlapis:

```
Volume dasar (karkas BPS / 12, ±10%)  →  × faktor tren lokal  →  × faktor musim Iduladha  →  + white noise  =  Volume akhir
```

Volume akhir lalu dipecah menjadi struk transaksi, tiap struk diberi harga, dan semuanya diringkas lagi per bulan menjadi dataset SARIMAX.

## Bagian A – Parameter ([baris 61–131](03_generate_data.py#L61-L131))

Semua angka asumsi dikumpulkan di sini supaya rumus di bawahnya tidak perlu disentuh saat angka berubah.

- **`BASE_DIR`, `BPS_DIR`, `DATA_DIR`**: `Path(__file__).resolve().parent` adalah folder tempat file program berada. Input dibaca dari `data/sumber_bps/`, output ditulis ke `data/hasil_generate/`, sehingga folder selalu ketemu dari mana pun program dijalankan.
- **`SEED = 42`** dan **`rng = np.random.default_rng(SEED)`**: satu generator acak dipakai seluruh program, jadi hasilnya selalu sama tiap dijalankan. Karena generatornya satu, urutan pemanggilan ikut menentukan hasil: menukar urutan tahap akan mengubah semua angka.
- **`TAHUN_DATA`**: 3 tahun, menghasilkan 36 bulan.
- **`WILAYAH`, `K_TOLERANSI` (k = 10%)**: dasar perhitungan baseline. Data **tidak dibagi jumlah UMKM**; baseline adalah produksi karkas bulanan seluruh kabupaten.
- **`PEMOTONGAN_MEI/JUNI/JULI_2024`**: jumlah ekor dipotong. Mei vs Juli dipakai sebagai dasar memilih k, Mei vs Juni sebagai dasar koefisien musiman.
- **Tren**: tidak ada parameter khusus. Tren dibentuk dari baseline Kabupaten Malang sendiri (Bagian G), tidak memakai data nasional.
- **`BULAN_IDULADHA`**: dict tahun → nomor bulan (semuanya Juni).
- **`RENTANG_HARGA`**: dict produk → tuple `(min, maks)` Rp/kg. Harga Jeroan masih sementara, disamakan dengan Daging Variasi.
- **`KOLOM_BPS`**: nama pendek → nama kolom asli di CSV BPS.
- **`PRODUK`**: daftar 4 produk; urutannya dipakai konsisten untuk rasio dan undian.
- **`TAHUN_LABEL_KOMPONEN_TERTUKAR`** = `[2024, 2025]`: tahun yang label kolom "Daging Murni/Skeletal" dan "Karkas"-nya tertukar di tabel BPS (lihat Bagian D).

## Bagian B – Fungsi bantu tampilan ([baris 134–199](03_generate_data.py#L134-L199))

Fungsi-fungsi ini hanya memformat teks untuk terminal, tidak mengubah data.

### `angka(x, desimal)`

Mengubah `1234567.891` menjadi `'1.234.567,89'`.

```python
teks = f"{x:,.{desimal}f}"
return teks.replace(",", "#").replace(".", ",").replace("#", ".")
```

- Python menghasilkan gaya Inggris (`1,234,567.89`), lalu koma dan titik ditukar.
- Penukaran butuh karakter perantara `#`. Kalau koma langsung diganti titik, titik desimal yang asli tidak bisa dibedakan lagi.

### `persen(x, desimal, tanda)`

Mengubah `0.1510` menjadi `'15,10%'`. Angkanya dimutlakkan dulu, lalu tanda ditempel manual: dengan `tanda=True` selalu ada `+` atau `-`, tanpa itu hanya `-` untuk nilai negatif.

### `bulan_tahun(tanggal)`

Mengambil nama bulan dari `NAMA_BULAN`. Indeksnya `tanggal.month - 1` karena list mulai dari 0 sedangkan bulan mulai dari 1.

### `rupiah(x)`

Menempelkan `"Rp "` di depan `angka(x, 0)`.

### `judul_tahap(teks)`

Mencetak judul diapit dua garis `=` sepanjang 100 karakter.

### `cetak_tabel(header, baris, rata, judul)`

Mencetak tabel berbingkai.

```python
rata = rata or "r" * len(header)
lebar = [max(len(str(h)), *(len(str(b[i])) for b in baris)) for i, h in enumerate(header)]
```

- Kalau `rata` tidak diisi, semua kolom rata kanan.
- Lebar tiap kolom adalah teks terpanjang di kolom itu, baik header maupun isi.

```python
def susun(sel):
    isi = [str(s).ljust(w) if r == "l" else str(s).rjust(w) for s, w, r in zip(sel, lebar, rata)]
    return "| " + " | ".join(isi) + " |"
```

- `susun` merakit satu baris: tiap sel diberi spasi sampai selebar kolomnya (`ljust` rata kiri, `rjust` rata kanan), lalu disambung dengan `|`.
- `garis` adalah pembatas `+-----+-----+`. Di bawah header, `-` diganti `=` supaya header terlihat terpisah.

## Bagian C – Tahap 1: time horizon ([baris 202–226](03_generate_data.py#L202-L226))

### `buat_time_horizon(tahun_list)`

Membuat kerangka waktu 36 baris.

```python
periode = pd.date_range(f"{tahun_list[0]}-01-01", periods=len(tahun_list) * 12, freq="MS")
```

- Mulai 1 Januari tahun pertama, sebanyak 3 × 12 = 36 tanggal.
- `freq="MS"` (Month Start) berarti tiap tanggal adalah tanggal 1 bulan berikutnya.

Hasilnya DataFrame berkolom `t` (1–36), `Periode`, `Tahun`, `Bulan`. Dua kolom terakhir diambil langsung dari `periode.year` dan `periode.month`.

## Bagian D – Tahap 2 Langkah 1: ekstraksi BPS ([baris 229–378](03_generate_data.py#L229-L378))

### `cari_file_bps(tahun)`

Mencari file berpola `bps_produksi_kambing_{tahun}*.csv`. Tanda `*` membuat nama file dengan akhiran tambahan tetap ketemu. Kalau ada beberapa, diambil yang pertama menurut abjad; kalau tidak ada, program berhenti dengan `FileNotFoundError`.

### `ke_angka(nilai)`

Membersihkan satu sel: tanda `(*)` dibuang, lalu dicoba `float()`. Kalau gagal (misalnya isinya `"..."`), hasilnya `NaN`.

- `"1462465.57 (*)"` → `1462465.57` (tanda `(*)` = angka sementara BPS)
- `"..."` → `NaN` (data tidak tersedia)

### `baca_bps_wilayah(tahun, wilayah)`

Membuka satu file CSV BPS untuk satu tahun, mengambil baris satu kabupaten, lalu mengembalikan angka produksinya sebagai dict, misalnya 2024: `{"Daging Murni": 1048096.31, "Karkas": 1393468.17, "Jeroan": 289375.55, ...}` (label sudah dibetulkan, lihat di bawah).

```python
df = pd.read_csv(cari_file_bps(tahun), encoding="utf-8-sig", dtype=str)
```

- `encoding="utf-8-sig"` membuang BOM, karakter tersembunyi di awal file BPS. Tanpa ini nama kolom pertama bisa terbaca `"﻿Kabupaten/Kota"` dan pencarian kolom gagal.
- `dtype=str` membuat semua sel dibaca sebagai teks dulu, karena isi sel BPS tidak selalu angka murni. Konversi ke angka dilakukan belakangan oleh `ke_angka`.

```python
baris = df[df["Kabupaten/Kota"].str.strip() == wilayah]
```

- Menyaring tabel sehingga hanya tersisa baris yang nama kabupatennya sama persis dengan `wilayah`.
- `.str.strip()` membuang spasi di awal/akhir nama, jadi `"Malang "` tetap cocok.
- Karena perbandingannya sama persis (`==`), `"Malang"` tidak akan cocok dengan `"Kota Malang"`. Yang diambil adalah Kabupaten Malang.

```python
if baris.empty:
    raise ValueError(f"Wilayah '{wilayah}' tidak ada di data BPS {tahun}")
baris = baris.iloc[0]
```

- Kalau tidak ada baris yang cocok, program langsung berhenti dengan pesan yang jelas, bukan lanjut dengan data kosong.
- Hasil saringan masih berupa tabel (walau isinya 1 baris). `.iloc[0]` mengambilnya sebagai satu Series supaya bisa diakses dengan `baris[nama_kolom]`.

```python
pemetaan_kolom = KOLOM_BPS.copy()
if tahun in TAHUN_LABEL_KOMPONEN_TERTUKAR:
    pemetaan_kolom["Daging Murni"] = KOLOM_BPS["Karkas"]
    pemetaan_kolom["Karkas"] = KOLOM_BPS["Daging Murni"]
return {nama: ke_angka(baris[kolom]) for nama, kolom in pemetaan_kolom.items()}
```

- **Label komponen tertukar (2024 & 2025).** Catatan kaki tabel BPS: *Jumlah Produksi Daging (Karkas) = karkas + jeroan + daging variasi* dan *Jumlah (Meatyield) = daging murni + jeroan + daging variasi*. Pada tabel 2024 dan 2025, kedua rumus itu hanya cocok bila nilai di kolom berlabel "Daging Murni/Skeletal" dibaca sebagai karkas dan sebaliknya. Karkas berisi tulang, jadi memang harus lebih besar dari daging murni. Contoh 2024: 1.393.468 + 289.376 + 79.010 = 1.761.853 (Total Karkas resmi). Tabel 2023 tidak tertukar.
- Untuk tiap pasangan di pemetaan, sel diambil lalu diubah menjadi angka.
- Hasilnya dict dengan 6 kunci: `Daging Murni`, `Karkas`, `Jeroan`, `Daging Variasi`, `Total Karkas`, `Total Meatyield`.

### `lengkapi_komponen_kosong(data_tahunan)`

Mengisi rincian produk 2023 yang kosong di BPS.

```python
lengkap = [d for d in data_tahunan.values() if not np.isnan(d["Karkas"])]
e = jeroan + variasi
assert abs(total_karkas - (d["Karkas"] + e)) < 1
assert abs(d["Total Meatyield"] - (d["Daging Murni"] + e)) < 1
assert d["Karkas"] > d["Daging Murni"]
s_tahun = e / total_karkas
p_tahun = jeroan / e
```

- `lengkap` berisi tahun yang rinciannya ada (2024 dan 2025).
- Tiga `assert` memeriksa rumus BPS pada tahun lengkap. Kalau label tertukar tidak dibetulkan, program berhenti di sini.
- `s` adalah rata-rata porsi E = Jeroan + Daging Variasi terhadap **Total Karkas** (rata-rata dari 2024 dan 2025).
- `p` adalah rata-rata porsi Jeroan di dalam gabungan itu.

```python
for d in data_tahunan.values():
    d["Diestimasi"] = bool(np.isnan(d["Karkas"]))
    if d["Diestimasi"]:
        e = s * d["Total Karkas"]
        d["Jeroan"] = p * e
        d["Daging Variasi"] = (1 - p) * e
        d["Karkas"] = d["Total Meatyield"] - e
        d["Daging Murni"] = d["Total Karkas"] - e
```

- Setiap tahun diberi penanda `Diestimasi` (True hanya untuk 2023).
- `e` adalah taksiran Jeroan + Daging Variasi 2023 (E_2023 = s × Total Karkas 2023), lalu dibagi dua memakai `p`.
- Karkas dan Daging Murni dihitung sebagai sisa dari kedua total resmi, sehingga total BPS 2023 tidak berubah.
- Dict diubah langsung di tempat, jadi `data_bps` di `main` ikut terisi.

## Bagian E – Tahap 2 Langkah 2–4: baseline ([baris 381–419](03_generate_data.py#L381-L419))

### `hitung_baseline(data_tahunan)`

Menghasilkan satu baris per tahun.

```python
karkas_bulanan_kab = d["Karkas"] / 12
mu = karkas_bulanan_kab
total_4_produk = sum(d[p] for p in PRODUK)
```

- Langkah 2: produksi karkas setahun dibagi 12 menjadi produksi bulanan kabupaten.
- Langkah 3: `mu` = produksi karkas bulanan kabupaten itu sendiri (tidak dibagi jumlah UMKM). Hasil: 105.975 (2023, ditaksir), 116.122 (2024), dan 121.872 (2025) kg per bulan.
- `mu` dihitung dari kolom Karkas saja, bukan dari total keempat produk.

```python
for p in PRODUK:
    baris[f"Rasio_{p}"] = d[p] / total_4_produk
```

- Langkah 4: porsi tiap produk terhadap jumlah keempatnya. Keempat rasio berjumlah 1, sehingga bisa langsung dipakai sebagai peluang undian.

Hasilnya tabel `baseline` berkolom `Tahun`, `Karkas_Tahunan_Kab`, `Karkas_Bulanan_Kab`, `Mu_Lokal`, `Diestimasi`, dan empat kolom `Rasio_...`.

## Bagian F – Tahap 2 Langkah 6: volume dasar acak ([baris 422–457](03_generate_data.py#L422-L457))

### `hitung_variasi_relatif(a, b)`

Menghitung selisih dua angka dibagi rata-ratanya, dalam persen. Hasilnya (2,68% untuk Mei vs Juli 2024) hanya ditampilkan sebagai pembenaran nilai k, tidak masuk hitungan.

### `buat_volume_bulanan(horizon, baseline)`

Mengundi volume dasar tiap bulan.

```python
for _, b in horizon.iterrows():
    mu = baseline.loc[baseline["Tahun"] == b["Tahun"], "Mu_Lokal"].iloc[0]
    batas_bawah = mu - K_TOLERANSI * mu
    batas_atas = mu + K_TOLERANSI * mu
    volume = rng.uniform(batas_bawah, batas_atas)
```

- `iterrows()` berjalan baris demi baris; `_` adalah indeks yang tidak dipakai.
- `mu` diambil dari baris baseline yang tahunnya sama dengan bulan itu, jadi tiap tahun punya baseline sendiri.
- `rng.uniform` mengundi satu angka dengan peluang merata di antara `mu − 10%` dan `mu + 10%`.

```python
data.append({**b.to_dict(), "Mu_Lokal": mu, "Batas_Bawah": batas_bawah,
             "Batas_Atas": batas_atas, "Target_Kg": round(volume, 2)})
```

- `**b.to_dict()` menyalin kolom lama (`t`, `Periode`, `Tahun`, `Bulan`), lalu ditambah empat kolom baru. `Target_Kg` adalah volume dasar hasil undian.

## Bagian G – Tahap 3: tren lokal Kabupaten Malang ([baris 460–510](03_generate_data.py#L460-L510))

Tren diambil dari baseline Kabupaten Malang sendiri, tidak dari data nasional.

### `hitung_gradien_per_tahun(baseline)`

Menentukan titik jangkar tren.

```python
jangkar["t_Tengah"] = [6.5 + 12 * i for i in range(len(jangkar))]
segmen = [(mu[i + 1] - mu[i]) / 12 for i in range(len(mu) - 1)]
jangkar["m_Segmen_Kg"] = segmen + segmen[-1:]
```

- Baseline tiap tahun ditempatkan di tengah tahunnya: t = 6,5; 18,5; 30,5.
- `m_Segmen_Kg` = kenaikan level per bulan antar-titik. 2023 → 2024: (116.122,35 − 105.975,26) / 12 = 845,59 kg per bulan; 2024 → 2025: (121.872,13 − 116.122,35) / 12 = 479,15 kg per bulan.
- Tahun terakhir tidak punya titik sesudahnya, jadi memakai segmen sebelumnya (garis diperpanjang).

### `level_tren(t, gradien)`

```
Mu_Tren_t = mu_i + m_Segmen_i × (t − t_Tengah_i)
```

- `i` adalah titik jangkar terakhir yang `t_Tengah`-nya ≤ t. Sebelum titik pertama dan sesudah titik terakhir, garis diperpanjang.
- Hasilnya level bulanan yang bergerak halus dari sekitar 101 ribu kg (Januari 2023) ke sekitar 124,5 ribu kg (Desember 2025).

### `injeksi_tren(volume_bulanan, gradien)`

```python
hasil["Mu_Tren_Kg"] = [level_tren(t, gradien) for t in hasil["t"]]
hasil["Faktor_Tren"] = hasil["Mu_Tren_Kg"] / hasil["Mu_Lokal"]
hasil["Volume_Tren_Kg"] = (hasil["Target_Kg"] * hasil["Faktor_Tren"]).round(2)
```

- `Faktor_Tren` = level tren dibagi baseline tahun itu, sehingga volume dasar hasil undian digeser mengikuti tren.
- Rata-rata tahunan `Mu_Tren_Kg` sama dengan baseline BPS: 2023 dan 2025 tepat sama, 2024 selisih −0,47% karena kemiringan berubah di tengah tahun.
- Tidak ada lompatan level di awal tahun, dan kenaikan level tidak dihitung dua kali (versi lama menambahkan tren nasional di atas baseline yang sudah naik per tahun).

## Bagian H – Tahap 4: musiman Iduladha ([baris 513–562](03_generate_data.py#L513-L562))

### `hitung_koefisien_musiman(sebelum, saat)`

Menghitung lonjakan Mei ke Juni, yaitu (22.359 − 8.229) / 8.229 = 1,717, lalu mengembalikan `1 + lonjakan` dibulatkan 3 desimal: S = 2,717.

### `tentukan_indeks_iduladha(horizon)`

Mencari nilai `t` bulan Iduladha.

```python
is_iduladha = horizon.apply(lambda r: r["Bulan"] == BULAN_IDULADHA[r["Tahun"]], axis=1)
return set(horizon.loc[is_iduladha, "t"].astype(int))
```

- `apply(..., axis=1)` memeriksa tiap baris: apakah bulannya sama dengan bulan Iduladha tahun itu.
- Hasilnya `set` `{6, 18, 30}`. Dipakai `set` karena pengecekan `in` nanti dilakukan berulang kali.

### `sisipkan_musiman(volume_bulanan, koefisien_s, indeks_iduladha)`

Berisi percabangan sederhana per bulan: kalau `t` ada di himpunan Iduladha, pengalinya 2,717; kalau tidak, 1. Hasilnya dua kolom baru: `Koefisien_Musim` dan `Volume_Musim_Kg = Volume_Tren_Kg × s`. `.copy()` dipakai supaya tabel masukan tidak ikut berubah.

## Bagian I – Tahap 6: white noise ([baris 565–587](03_generate_data.py#L565-L587))

### `tambah_white_noise(volume_bulanan, sigma_persen)`

```python
df["Sigma_Noise"] = (sigma_persen * df["Volume_Musim_Kg"]).round(2)
df["Noise_Kg"] = [round(rng.normal(0, s), 2) for s in df["Sigma_Noise"]]
df["Volume_Akhir_Kg"] = (df["Volume_Musim_Kg"] + df["Noise_Kg"]).clip(lower=0.01).round(2)
```

- `Sigma_Noise` adalah 5% dari volume bulan itu, jadi bulan Iduladha yang volumenya besar mendapat noise yang lebih besar juga.
- `rng.normal(0, s)` mengundi galat berdistribusi normal dengan rata-rata 0, sehingga bisa positif atau negatif.
- `clip(lower=0.01)` adalah pengaman agar volume tidak pernah nol atau negatif.
- `Volume_Akhir_Kg` inilah yang menjadi variabel target `Permintaan_Kg`.

## Bagian J – Langkah 5 & 7: pemecahan menjadi transaksi ([baris 590–641](03_generate_data.py#L590-L641))

### `undi_jenis_produk(peluang)`

```python
return PRODUK[rng.choice(len(PRODUK), p=peluang)]
```

- `rng.choice(4, p=peluang)` mengundi angka 0–3 dengan peluang sesuai rasio BPS, lalu angka itu dipakai sebagai indeks ke `PRODUK`.

### `pecah_menjadi_transaksi(volume_bulanan, baseline)`

Memecah volume tiap bulan menjadi struk.

```python
b = baseline.loc[baseline["Tahun"] == bln["Tahun"]].iloc[0]
peluang = [b[f"Rasio_{p}"] for p in PRODUK]
target = bln["Volume_Akhir_Kg"]
akumulasi = 0.0
hari_dlm_bulan = bln["Periode"].days_in_month
```

- Peluang produk diambil dari rasio tahun berjalan.
- `target` adalah volume yang harus habis terbagi; `akumulasi` mencatat yang sudah terbagi.
- `days_in_month` memberi jumlah hari bulan itu (28–31).

```python
while akumulasi < target - 1e-9:
    berat = round(rng.uniform(BERAT_PESANAN_MIN, BERAT_PESANAN_MAKS), 2)
    if akumulasi + berat > target:
        berat = round(target - akumulasi, 2)
    if berat <= 0:
        break
```

- Perulangan berjalan selama target belum tercapai. `1e-9` adalah toleransi kecil supaya galat pembulatan desimal tidak membuat perulangan berjalan sekali lagi.
- Berat tiap struk diundi merata 5–35 kg.
- Kalau struk itu membuat total melebihi target, beratnya dipotong menjadi sisa yang dibutuhkan. Akibatnya struk terakhir tiap bulan bisa kurang dari 5 kg.
- `if berat <= 0: break` adalah pengaman agar tidak ada struk kosong.

```python
produk = undi_jenis_produk(peluang)
tanggal = bln["Periode"] + pd.Timedelta(days=int(rng.integers(0, hari_dlm_bulan)))
akumulasi = round(akumulasi + berat, 2)
```

- `rng.integers(0, hari_dlm_bulan)` mengundi 0 sampai (jumlah hari − 1). Ditambahkan ke tanggal 1, hasilnya selalu jatuh di dalam bulan itu.

```python
df = pd.DataFrame(transaksi).sort_values("Tanggal_Transaksi", kind="stable").reset_index(drop=True)
df.insert(0, "ID_Transaksi", [f"TRX{i:06d}" for i in range(1, len(df) + 1)])
```

- Semua struk diurutkan menurut tanggal. `kind="stable"` menjaga urutan asli untuk struk bertanggal sama.
- ID diberikan setelah pengurutan, jadi `TRX000001` adalah transaksi paling awal. `{i:06d}` berarti angka 6 digit dengan nol di depan.

## Bagian K – Tahap 5: variabel eksogen ([baris 644–714](03_generate_data.py#L644-L714))

### `undi_harga_normal(produk)`

```python
p_min, p_max = RENTANG_HARGA[produk]
harga = rng.uniform(p_min, p_max)
return round(harga / PEMBULATAN_HARGA) * PEMBULATAN_HARGA
```

- Harga diundi merata di rentang produk itu.
- Dibagi 500, dibulatkan, lalu dikali 500 lagi: hasilnya selalu kelipatan Rp 500.

### `buat_harga_jual(transaksi, indeks_iduladha)`

Menentukan harga tiap struk.

```python
p_normal = undi_harga_normal(trx["Jenis_Produk"])
if int(trx["t"]) in indeks_iduladha:
    delta_p = round(rng.uniform(*MARKUP_IDULADHA) / PEMBULATAN_HARGA) * PEMBULATAN_HARGA
else:
    delta_p = 0
p_final = p_normal + delta_p
```

- `*MARKUP_IDULADHA` membongkar tuple menjadi dua argumen, setara `rng.uniform(10_000, 15_000)`.
- Markup hanya ada di bulan Iduladha dan ikut dibulatkan ke kelipatan 500.
- Empat kolom baru ditambahkan: `Harga_Normal`, `Markup_Musiman`, `Harga_Final`, dan `Total_Pendapatan = Kuantitas_Kg × Harga_Final`.

### `rekap_eksogen_bulanan(transaksi)`

Meringkas struk menjadi angka bulanan.

```python
rekap = transaksi.groupby("t").agg(
    Jumlah_Pesanan=("ID_Transaksi", "count"),
    Total_Kg=("Kuantitas_Kg", "sum"),
    Total_Pendapatan=("Total_Pendapatan", "sum"),
)
rekap["Harga_Rata2_Per_Kg"] = (rekap["Total_Pendapatan"] / rekap["Total_Kg"]).round(0)
```

- `groupby("t")` mengelompokkan struk per bulan. Tiap baris `agg` berbentuk `nama_kolom_baru=(kolom_sumber, cara_hitung)`.
- Harga rata-rata dihitung dari total pendapatan dibagi total kg, jadi struk yang lebih berat berpengaruh lebih besar (rata-rata tertimbang).
- Indeks tabel hasilnya adalah `t`, dan ini dimanfaatkan di `main`.

## Bagian L – Tahap 7: kompilasi dan ekspor ([baris 717–797](03_generate_data.py#L717-L797))

### `kompilasi_dataset(volume)`

Memilih 7 kolom dari tabel `volume` dan memberi nama final. `Volume_Akhir_Kg` berganti nama menjadi `Permintaan_Kg` (y). `Periode` diubah ke teks `YYYY-MM-DD` dengan `strftime`, dan kolom hitungan dipaksa `int`.

### `ekspor_csv(dataset, volume, transaksi, baseline)`

Menyimpan empat tabel ke `data/hasil_generate/` (dengan keterangan kolom dari `keterangan_csv.py`).

```python
DATA_DIR.mkdir(exist_ok=True)
for nama, _, tabel in daftar:
    try:
        tabel.to_csv(DATA_DIR / nama, index=False)
    except PermissionError:
        file_terkunci.append(nama)
```

- `mkdir(exist_ok=True)` membuat folder output kalau belum ada, tanpa error kalau sudah ada.
- `index=False` supaya nomor baris pandas tidak ikut tertulis.
- `PermissionError` muncul kalau file sedang dibuka di Excel. Nama file itu dicatat dan perulangan lanjut ke file berikutnya.
- Kalau ada file terkunci, daftarnya dicetak lalu program berhenti dengan `SystemExit(1)`. File lain yang tidak terkunci sudah telanjur tersimpan saat itu.

### `validasi_dataset(transaksi)`

Membaca ulang `dataset_sarimax.csv` dari disk dan menjalankan 6 pemeriksaan.

```python
selisih_bulan = df["Periode"].dt.to_period("M").astype(int).diff().dropna()
```

- Tiap tanggal diubah menjadi nomor urut bulan, lalu dihitung selisih antarbaris. Kalau semua selisih bernilai 1, tidak ada bulan yang terlewat atau ganda.

Pemeriksaan lainnya: jumlah baris 36, tidak ada sel kosong, permintaan selalu positif, total kg dataset sama dengan total kg seluruh struk (toleransi 0,5 kg), dan kolom numerik terbaca sebagai angka. Tiap pemeriksaan dikembalikan sebagai tuple `(nama, True/False, keterangan)`.

## Bagian M – Program utama ([baris 800–962](03_generate_data.py#L800-L962))

`main()` memanggil fungsi-fungsi di atas secara berurutan dan mencetak tabel di tiap tahap. Tabel `volume` bertambah kolom di setiap tahap:

| Urutan | Pemanggilan | Kolom yang ditambahkan |
|---|---|---|
| Tahap 1 | `buat_time_horizon` | `t`, `Periode`, `Tahun`, `Bulan` |
| Tahap 2 | `baca_bps_wilayah` → `lengkapi_komponen_kosong` → `hitung_baseline` → `buat_volume_bulanan` | `Mu_Lokal`, `Batas_Bawah`, `Batas_Atas`, `Target_Kg` |
| Tahap 3 | `hitung_gradien_per_tahun` → `injeksi_tren` | `Mu_Tren_Kg`, `Faktor_Tren`, `Volume_Tren_Kg` |
| Tahap 4 | `hitung_koefisien_musiman`, `tentukan_indeks_iduladha` → `sisipkan_musiman` | `Koefisien_Musim`, `Volume_Musim_Kg` |
| Tahap 6 | `tambah_white_noise` | `Sigma_Noise`, `Noise_Kg`, `Volume_Akhir_Kg` |
| Langkah 7 | `pecah_menjadi_transaksi` | (tabel `transaksi` baru) |
| Tahap 5 | `buat_harga_jual` → `rekap_eksogen_bulanan` | `Jumlah_Pesanan`, `Harga_Rata2_Per_Kg`, `Total_Pendapatan` |
| Tahap 7 | `kompilasi_dataset` → `ekspor_csv` → `validasi_dataset` | (4 file CSV) |

Tahap 6 dijalankan sebelum Langkah 7 dan Tahap 5 karena struk baru bisa dipecah setelah volume akhir terbentuk, dan harga diundi per struk.

Beberapa baris di `main` yang perlu dipahami:

```python
data_bps = {th: baca_bps_wilayah(th, WILAYAH) for th in TAHUN_DATA}
```

- Membaca CSV sekali per tahun. Hasilnya dict bersarang `{2023: {...}, 2024: {...}, 2025: {...}}`.

```python
volume["Jumlah_Pesanan"] = volume["t"].map(rekap["Jumlah_Pesanan"])
```

- `rekap` berindeks `t`, jadi `.map()` mencocokkan tiap nilai `t` di `volume` dengan baris `rekap` yang sesuai. Ini cara menempelkan hasil rekap ke tabel bulanan.

```python
volume["Cocok"] = (volume["Total_Transaksi_Kg"] - volume["Volume_Akhir_Kg"]).abs() < 0.01
```

- Pemeriksaan Langkah 7: total kg semua struk tiap bulan harus sama dengan volume akhirnya. Hasilnya tampil sebagai `OK` atau `BEDA` di tabel.

```python
print(f"  Cek dokumen: 15,5 kg x 125.500 = {rupiah(15.5 * 125_500)} | 15,5 kg x 150.000 = {rupiah(15.5 * 150_000)}")
```

- Baris "Cek dokumen" menghitung ulang contoh harga dari dokumen metodologi (15,5 kg) supaya bisa dibandingkan langsung. Angkanya ditulis manual dan tidak memengaruhi data yang dihasilkan.

```python
[... for b in baseline.itertuples()]
```

- `itertuples()` mirip `iterrows()`, tetapi kolom diakses dengan titik (`b.Tahun`, `b.Mu_Lokal`). Untuk kolom yang namanya mengandung spasi seperti `Rasio_Daging Murni`, program memakai `iterrows()` dan `b["..."]`.

```python
if __name__ == "__main__":
    main()
```

- `main()` hanya berjalan kalau file ini dieksekusi langsung, tidak saat di-import oleh file lain.
