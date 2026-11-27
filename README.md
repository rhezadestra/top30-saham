# Top 30 Berita Saham

Aplikasi baca (PWA) berisi topik berita saham terbaru (bawaan **12 jam terakhir**; bisa dipilih 3, 6, 12, atau 24 jam) dari Kontan, CNBC Indonesia, IDX Channel, Bisnis, dan Investor.id. Daftarnya diperbarui otomatis kira-kira tiap 10 menit, tanpa edisi final.

Alamat: https://rhezadestra.github.io/top30-saham/

## Cara kerja

1. Workflow GitHub Actions `.github/workflows/live.yml` menjalankan `scripts/update_live.py` tiap 3 menit. Satu run berjalan ±55 menit lalu memicu run berikutnya sendiri, karena jadwal bawaan GitHub sering tertunda sampai satu jam. Jadwal `*/10` tetap ada sebagai cadangan untuk menyambung rantai jika putus. Untuk menghentikan, batalkan run yang sedang berjalan (Cancel) lalu nonaktifkan workflow di tab Actions.
2. Skrip mengambil RSS tiap media. Jika RSS langsung tidak bisa diambil dari server (Kontan, Bisnis, dan Investor.id memblokir), skrip memakai Google News RSS untuk situs media itu.
3. Berita pergerakan harga, net buy/sell asing, harga emas, dan kurs dibuang berdasarkan kata kunci di judul.
4. Artikel digabung per peristiwa: kode saham dan jenis aksi yang sama (dividen, rights issue, IPO, delisting, dan lain-lain) dengan beberapa kata kunci sama, atau judul yang sangat mirip.
5. Hasilnya ditulis ke `data/live.json`, lalu di-commit hanya jika ada perubahan atau sudah lebih dari 12 menit. GitHub Pages memperbarui situs dalam satu sampai dua menit.
6. Aplikasi mengecek `data/live.json` tiap 2 menit selama terbuka, dan setiap kali dibuka lagi.

## Isi folder

| File | Fungsi |
|---|---|
| `index.html` | Tampilan dan logika aplikasi |
| `manifest.webmanifest`, `sw.js`, `icons/` | Bagian PWA (pasang di layar utama, buka offline) |
| `scripts/update_live.py` | Pengambil berita, hanya pustaka standar Python |
| `.github/workflows/live.yml` | Pembaruan berantai tiap 3 menit |
| `data/live.json` | Topik 24 jam terakhir, dibaca aplikasi |
| `data/articles.json` | Simpanan artikel 36 jam, supaya artikel tidak hilang saat RSS bergulir |
| `data/ringkasan.json` | Ringkasan AI per topik (poin-poin), ditulis tugas terjadwal Claude |

## Ringkasan AI

Tugas terjadwal Claude berjalan tiap jam (menit ke-45, pukul 05.45–22.45 WIB). Tugas itu membaca `data/live.json`, membuka artikel sumber untuk topik yang belum punya ringkasan, lalu menulis 2–4 poin ke `data/ringkasan.json`:

```json
{
  "updated": "2026-11-27T12:45:00+07:00",
  "items": {
    "<id topik>": {
      "title": "judul topik saat diringkas",
      "at": "2026-11-27T12:45:00+07:00",
      "urls": ["semua URL sumber saat diringkas"],
      "points": ["poin 1", "poin 2"]
    }
  }
}
```

Tugas yang sama menandai topik kembar (peristiwa sama yang terpecah) di kunci `"merge": {"<id kembar>": "<id utama>"}`. Aplikasi menggabungkan sumber topik kembar ke topik utamanya, sehingga jumlah media ikut terhitung dan topik tidak tampil dua kali.

Setiap topik hanya melampirkan satu artikel: tautan langsung ke media jika ada (bukan Google News), yang terbit paling awal.

Aplikasi mencocokkan ringkasan lewat id topik, atau lewat URL artikel jika pengelompokan otomatis berubah. Topik yang belum diringkas menampilkan cuplikan RSS (jika ada) dan keterangan "Ringkasan AI menyusul".

## Kartu di Claude dan tombol "Perbarui sekarang"

`claude/app.html` adalah sumber halaman versi kartu Claude (artifact). Kartu itu salinan data, karena halaman di Claude tidak boleh mengambil data dari situs lain. Tombol **Perbarui sekarang** di kartu memanggil tugas Claude "Top 30 Berita Saham – segarkan kartu Claude" lewat sambungan Claude Code Remote. Tugas itu mengambil `data/live.json` dan `data/ringkasan.json` terbaru dari repo ini, lalu memublikasikan ulang kartu (±2–4 menit). Di GitHub Pages tombol ini tersembunyi, karena halaman mengecek data sendiri tiap menit.

## Aturan peringkat

Terpopuler: jumlah media yang memberitakan, lalu jumlah artikel, lalu kategori (aksi korporasi, regulasi, kinerja, makro), lalu artikel terbaru. Maksimal 30 topik. `data/live.json` menyimpan semua topik 24 jam (sampai 200); aplikasi yang memilih 30 teratas sesuai rentang dan urutan. Penanda "Baru" berarti topik belum ada sekitar satu jam sebelumnya; panah naik/turun hanya tampil di rentang 24 jam. Data menyimpan 24 jam, aplikasi menyaring sesuai rentang yang dipilih.

Terbaru: 30 topik dengan artikel paling baru di rentang yang dipilih. Pencarian mencakup semua topik di rentang itu.

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
