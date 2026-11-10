"""
Runner untuk menjalankan seluruh pipeline script 03-13 secara berurutan.
Pakai: python jalankan_pipeline.py [--mulai N] [--sampai N]
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PIPELINE = [
    "03_generate_data.py",
    "04_pra_proses_data.py",
    "05_eksplorasi_data.py",
    "06_pemodelan_forecasting.py",
    "07_validasi_diagnostik_evaluasi.py",
    "08_forecasting_data_testing.py",
    "09_peramalan_visualisasi.py",
    "10_ekspor_output_laporan.py",
    "11_implementasi_access.py",
    "11_rekomendasi_manajerial.py",
    "12_ramalan_6_bulan_access.py",
    "13_penyesuaian_iduladha.py",
]


def main():
    mulai = 1
    sampai = len(PIPELINE)
    args = sys.argv[1:]
    if "--mulai" in args:
        mulai = int(args[args.index("--mulai") + 1])
    if "--sampai" in args:
        sampai = int(args[args.index("--sampai") + 1])

    terpilih = PIPELINE[mulai - 1 : sampai]
    print(f"Menjalankan {len(terpilih)} script ({mulai} s.d. {sampai} dari {len(PIPELINE)}):")
    for i, nama in enumerate(terpilih, start=mulai):
        print(f"  {i}. {nama}")
    print()

    waktu_mulai_total = time.time()
    for i, nama in enumerate(terpilih, start=mulai):
        skrip = ROOT / nama
        if not skrip.exists():
            print(f"[GAGAL] Script tidak ditemukan: {skrip}")
            sys.exit(1)

        print(f"\n{'=' * 70}")
        print(f"[{i}/{len(PIPELINE)}] Menjalankan {nama} ...")
        print(f"{'=' * 70}")

        t0 = time.time()
        hasil = subprocess.run([sys.executable, str(skrip)], cwd=str(ROOT))
        durasi = time.time() - t0

        if hasil.returncode != 0:
            print(f"\n[GAGAL] {nama} berhenti dengan kode {hasil.returncode} (setelah {durasi:.1f} detik).")
            print("Pipeline dihentikan. Perbaiki error di atas lalu jalankan ulang.")
            sys.exit(hasil.returncode)

        print(f"[OK] {nama} selesai dalam {durasi:.1f} detik.")

    total = time.time() - waktu_mulai_total
    print(f"\n{'=' * 70}")
    print(f"SELESAI. Semua {len(terpilih)} script berhasil dijalankan dalam {total:.1f} detik.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
