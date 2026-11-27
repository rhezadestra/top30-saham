# Top 30 Berita Saham

Aplikasi baca (PWA) berisi topik berita saham **24 jam terakhir** dari Kontan, CNBC Indonesia, IDX Channel, Bisnis, dan Investor.id. Daftarnya diperbarui otomatis kira-kira tiap 10 menit, tanpa edisi final.

Alamat: https://rhezadestra.github.io/top30-saham/

## Cara kerja

1. Workflow GitHub Actions `.github/workflows/live.yml` menjalankan `scripts/update_live.py` tiap 10 menit. GitHub kadang menunda jadwal beberapa menit.
2. Skrip mengambil RSS tiap media. Jika RSS langsung tidak bisa diambil dari server (Kontan, Bisnis, dan Investor.id memblokir), skrip memakai Google News RSS untuk situs media itu.
3. Berita pergerakan harga, net buy/sell asing, harga emas, dan kurs dibuang berdasarkan kata kunci di judul.
4. Artikel digabung per peristiwa: kode saham dan jenis aksi yang sama (dividen, rights issue, IPO, dan lain-lain), atau judul yang sangat mirip.
5. Hasilnya ditulis ke `data/live.json`, lalu di-commit hanya jika ada perubahan atau sudah lebih dari 30 menit. GitHub Pages memperbarui situs dalam satu sampai dua menit.
6. Aplikasi mengecek `data/live.json` tiap 2 menit selama terbuka, dan setiap kali dibuka lagi.

## Isi folder

| File | Fungsi |
|---|---|
| `index.html` | Tampilan dan logika aplikasi |
| `manifest.webmanifest`, `sw.js`, `icons/` | Bagian PWA (pasang di layar utama, buka offline) |
| `scripts/update_live.py` | Pengambil berita, hanya pustaka standar Python |
| `.github/workflows/live.yml` | Jadwal tiap 10 menit |
| `data/live.json` | Topik 24 jam terakhir, dibaca aplikasi |
| `data/articles.json` | Simpanan artikel 36 jam, supaya artikel tidak hilang saat RSS bergulir |

## Aturan peringkat

Terpopuler: jumlah media yang memberitakan, lalu jumlah artikel, lalu kategori (aksi korporasi, regulasi, kinerja, makro), lalu artikel terbaru. Maksimal 30 topik. Panah naik/turun dan penanda "Baru" dibanding peringkat sekitar satu jam sebelumnya.

Terbaru: diurutkan dari artikel paling baru.

## Mengubah sesuatu

- Daftar sumber dan alamat RSS: `MEDIA` di `scripts/update_live.py`.
- Kata kunci yang dibuang: `HARD_EXCLUDE` dan `SOFT_PRICE`.
- Kata kunci kategori: `CAT_RULES`.
- Frekuensi: baris `cron` di `.github/workflows/live.yml` (minimal 5 menit).
- Menjalankan manual: tab Actions di GitHub, pilih "Perbarui berita live", lalu Run workflow.

## Catatan

- Ringkasan adalah cuplikan pembuka dari RSS media. Media yang diambil lewat Google News hanya menampilkan judul.
- Pengelompokan dan penyaringan otomatis bisa meleset; topik yang sama kadang terpecah, atau berita harga lolos.
- Cek aturan pemakaian konten tiap media sebelum aplikasi dibagikan ke orang lain.
- Bahan riset, bukan rekomendasi beli atau jual.
