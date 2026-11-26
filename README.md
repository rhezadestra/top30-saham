# Top 30 Berita Saham (prototipe PWA)

Aplikasi baca rangkuman harian topik berita saham dari Kontan, CNBC Indonesia, IDX Channel, Bisnis, dan Investor.id. Edisi final dikunci setiap pukul **19.00 WIB** (rentang 19.01 hari sebelumnya sampai 19.00). Tab **Hari ini** menampilkan edisi yang sedang berjalan dan diperbarui tiap jam pukul 06.00 sampai 19.00 WIB.

## Isi folder

| File | Fungsi |
|---|---|
| `index.html` | Seluruh tampilan dan logika aplikasi |
| `manifest.webmanifest` | Nama, warna, dan ikon saat dipasang di layar utama |
| `sw.js` | Service worker: aplikasi tetap terbuka saat offline |
| `icons/` | Ikon 192, 512, dan maskable, plus ikon iPhone |
| `data/index.json` | Daftar edisi |
| `data/YYYY-MM-DD.json` | Satu file per edisi final |
| `data/sementara.json` | Edisi berjalan untuk tab Hari ini, ditimpa tiap jam |

## Cara memasang di HP

PWA harus dibuka lewat alamat **https**. Unggah seluruh isi folder ini ke layanan hosting statis, misalnya GitHub Pages, Netlify, atau Cloudflare Pages. Lalu buka alamatnya di HP:

- **iPhone (Safari):** ketuk Bagikan, lalu Tambahkan ke Layar Utama.
- **Android (Chrome):** ketuk tombol Pasang aplikasi di halaman, atau menu ⋮ lalu Instal aplikasi.

Membuka `index.html` langsung dari file di komputer tidak akan memuat data, karena browser memblokir pengambilan file lokal.

## Alur pembaruan

Dikerjakan oleh tugas terjadwal tiap jam, menit ke-02, pukul 06.02 sampai 19.02 WIB:

1. **06.02 sampai 18.02:** cari berita baru di rentang `sementara.json`, gabungkan per peristiwa, simpan peringkat sebelumnya ke `prevRanks`, perbarui `updated`, lalu timpa `data/sementara.json`.
2. **19.02:** salin isi akhir `sementara.json` menjadi `data/YYYY-MM-DD.json` (tanpa `live` dan `prevRanks`), catat di `data/index.json`, lalu kosongkan `sementara.json` untuk rentang 19.01 hari ini sampai 19.00 besok.
3. Commit dan push ke `main`. GitHub Pages memperbarui situs dalam satu sampai dua menit.

Aplikasi mengecek pembaruan tiap 5 menit dan setiap kali dibuka lagi.

Format satu edisi:

```json
{
  "date": "2026-11-26",
  "window": { "start": "2026-11-25T19:01:00+07:00", "end": "2026-11-26T19:00:00+07:00" },
  "target": 30,
  "sample": false,
  "media": [{ "name": "Kontan", "abbr": "KON" }],
  "topics": [
    {
      "id": "2026-11-25-aadi-dividen",
      "title": "AADI bagikan dividen interim US$500 juta",
      "category": "Aksi korporasi",
      "tickers": ["AADI"],
      "summary": "Ringkasan satu atau dua kalimat, ditulis ulang.",
      "sources": [{ "media": "Kontan", "time": "2026-11-26T06:53:00+07:00", "url": "https://..." }]
    }
  ]
}
```

`sementara.json` memakai format yang sama, ditambah `"live": true`, `"updated"` (jam pembaruan), dan `"prevRanks"` (peringkat per `id` pada pembaruan sebelumnya, untuk panah naik/turun dan penanda Baru).

Jika jam terbit artikel tidak bisa dicek, isi `"time"` dengan tanggal terbit pukul 12.00 dan tambahkan `"approx": true`.

Kategori yang dikenali: `Aksi korporasi`, `Regulasi`, `Kinerja`, `Makro`.

Peringkat dihitung di aplikasi, bukan di file data:

1. Artikel di luar rentang waktu tidak dihitung. Topik yang terbit setelah 19.00 tampil di bagian "Masuk edisi berikutnya".
2. Urutan: jumlah media, lalu jumlah artikel, lalu kategori (aksi korporasi, regulasi, kinerja, makro), lalu jam terbit paling awal.
3. Maksimal 30 topik; jika kurang, ditampilkan apa adanya.

## Catatan

- Edisi 25 November adalah data contoh. Edisi 26 November disusun dari pencarian dan belum mencakup semua artikel lima media.
- Sebelum dipakai rutin atau dibagikan, cek aturan pemakaian konten tiap media.
- Bahan riset, bukan rekomendasi beli atau jual.
