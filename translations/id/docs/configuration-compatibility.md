# Catatan kompatibilitas konfigurasi

Status: pratinjau publik

Beberapa pengaturan diterima, diurai, dan diserialisasi ulang oleh pemuat konfigurasi tanpa mengubah perilaku runtime, karena perilaku yang pernah mereka gambarkan telah dihapus atau dimiliki di tempat lain. Halaman ini adalah catatan kanonik tunggal untuk masing-masing, sehingga operator dapat membedakan kenop yang didukung dari bidang kompatibilitas tanpa harus membaca sumbernya.

## `self_improvement.max_applied_notes`

Kunci tingkat atas di bawah `self_improvement` dalam konfigurasi yang disimpan.

- **Diterima dan dipertahankan.** Parser membacanya dan serializer menulisnya kembali. Parser menormalkan `0` ke `1`; format serializer adalah hal terpisah dari nilai itu sendiri.
- **Tidak ada konsumen produksi saat ini dalam jalur pemilihan catatan.** Batas efektif adalah `CONTEXT_IMPROVEMENT_NOTE_LIMIT = 6` dalam `modules/context/config.py`, diterapkan ketika paket konteks diberi peringkat untuk tujuan `decide` di `modules/context/retrieval/bundle.py`. Pengaturan ini tidak mengubahnya.
- **Panduan operator:** biarkan tidak diatur. Mengubah batas efektif adalah perubahan sumber di pemilik konteks, bukan perubahan konfigurasi.

## `self_improvement.min_token_overlap`

Kunci tingkat atas di bawah `self_improvement` dalam konfigurasi yang disimpan.

- **Diterima dan dipertahankan**, namun tidak aktif.
- **Catatan historis:** kunci ini memilih catatan berdasarkan tumpang tindih token sebelum pemilih tumpang tindih leksikal dihapus di bawah SIRH-03. Ini tidak mengaktifkan kembali perilaku tersebut, dan pencocokan saat ini bersifat struktural: status aktif, kepemilikan agent, dan tag `tool:*` / `error:*`.
- **Panduan operator:** biarkan tidak diatur. Mengaturnya tidak dapat mengembalikan pencocokan leksikal, dan tidak ada jalur pemilihan catatan runtime dalam pohon sumber yang membacanya. Parser dan serializer memang menangani kunci ini; konsumen luar pohon tidak diaudit.

## Perilaku terukur yang tidak diubah oleh bidang-bidang ini

Dengan delapan catatan pencocokan aktif dan tetangga calon/agent asing yang hadir:

| pengaturan | kartu overlay | referensi catatan akhir |
| --- | --- | --- |
| default (`max_applied_notes: 3`) | 8 | 6 |
| `max_applied_notes: 1` | 8 | 6 |
| `max_applied_notes: 100` | 8 | 6 |
| `min_token_overlap: 999` | 8 | 6 |

Menonaktifkan self-improvement sama sekali tidak menghasilkan overlay, catatan calon dan agent asing tetap keluar, dan giliran tanpa konteks alat yang cocok tidak menghasilkan overlay. Batas pemilik konteks sebanyak enam adalah yang membatasi referensi.

## Terkait

- [`runtime-surfaces.md`](runtime-surfaces.md) untuk runtime yang didukung tempat permukaan pengaturan ini berada.
- [`turn-budgets.md`](turn-budgets.md) untuk konteks dan anggaran giliran yang termasuk dalam batas efektif.
