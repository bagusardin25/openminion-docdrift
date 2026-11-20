# Memahami anggaran putaran dan biaya token

Mulailah dengan pengaturan default yang ada dan alasan penghentian putaran yang sebenarnya. Daftar singkat alat, batas eksekusi, target paket-konteks dan batas keluaran provider mengendalikan pekerjaan yang berbeda. Meningkatkan salah satu tidak memperbaiki kehabisan batas yang lain.

## Apa yang dikendalikan oleh default

| Pengaturan atau pemilik | Default | Makna |
| --- | --- | --- |
| `runtime.tool_selection.max_tools_per_turn` | `6` | Maksimum entri dalam daftar pendek layanan seleksi, bukan jumlah panggilan yang dijalankan per giliran. |
| `runtime.tool_selection.tool_prompt_token_budget` | `600` | Perkiraan anggaran prompt untuk daftar pendek tersebut, bukan batas permintaan model secara lengkap. |
| Loop adaptif umum | `24` iterasi, `64` panggilan alat | Batas eksekusi loop; ekstensi adaptif dan strategi lain memiliki kebijakan tersendiri. |
| `security.tool_policy.max_calls_per_run` | `160` | Batas panggilan alat runtime, terpisah dari batas loop adaptif. |
| `runtime.session_context_token_budget` | `0` | Menonaktifkan batas tambahan opsional konteks sesi; anggaran paket dan ember khusus tujuan tetap berlaku. |
| `runtime.tool_schema_shortlisting_enabled` | Tidak disetel; default otak `false` | Mengendalikan panggilan pemilihan skema pendahuluan opsional dalam jalur adaptif yang memenuhi syarat. Ini tidak menonaktifkan penemuan alat dengan nama tepat. |

Override agent/profil dapat mengubah batas efektif. Periksa konfigurasi aktual dan alasan penghentian sebelum mengaitkan pemberhentian awal pada default.
Jangan menghapus persyaratan persetujuan atau memperpanjang giliran secara otomatis untuk menyembunyikan kegagalan anggaran.

Target konteks keputusan adalah `2,200` token untuk giliran 1 hingga 5, `2,800` untuk giliran 6 hingga 10 dan `3,200` setelah giliran 10. Dua giliran pertama mempertahankan ember giliran terakhir yang lebih kecil karena sedikit riwayat yang harus disertakan, tetapi tidak lagi menggunakan target keseluruhan yang lebih kecil. Permintaan penilai dan validasi mempertahankan target token `3,000` mereka sendiri. Ini adalah target paket konteks, bukan batas output provider atau ukuran permintaan lengkap.

## Ukuran katalog bukan ukuran permintaan

Jalur entri biasa menawarkan skema kontrol dan `tool.request`. Model meminta nama alat tepat, dan loop adaptif menampilkan skema mereka. Alat lain yang tersedia tetap dapat ditemukan melalui direktori alat yang ada. Oleh karena itu, katalog terkonfigurasi dengan banyak alat tidak berarti setiap permintaan model memuat setiap skema penuh.

Jika `tool.request` tidak diizinkan atau jalur eksekusi lain dipilih, eksposur bisa berbeda. Periksa permintaan keluar. Mengaktifkan penyaringan awal dapat menambah panggilan model pada jalur yang relevan; ini tidak harus mengubah jalur yang dipilih dari entri sama sekali.

Laporan token paket-konteks adalah perkiraan untuk paket, bukan permintaan lengkap provider. Prompt, skema, dan transkrip alat dapat menambah token kemudian. Konteks yang diperlukan yang dipasang dapat membuat paket melebihi targetnya; periksa penggunaan `over_budget`, penggunaan ember, dan keputusan pemangkasan daripada menginterpretasikan target sebagai batas keras pada permintaan wire. Waktu pembangunan ulang lokal, byte permintaan berulang dan token tak ter-cache yang ditagih oleh provider adalah pengukuran terpisah.

## Ekstraksi fakta otomatis

Ekstraksi fakta otomatis diaktifkan secara default. Saat dijalankan, giliran melakukan satu pemanggilan model terstruktur tambahan sebelum pesan pengguna diinterpretasikan. Pemanggilan tersebut meminta fakta kandidat, preferensi pengguna, dan tugas yang secara eksplisit dinyatakan oleh pengguna. Hasilnya disimpan sebagai kandidat memori; ini bukan bagian dari balasan.

Sakelar yang didukung adalah bagian top-level `brain.auto_fact_extraction`:

| Bidang | Default | Arti |
| --- | --- | --- |
| `enabled` | `true` | Menjalankan ekstraksi pada giliran yang memenuhi syarat. |
| `model_tier` | `reflect` | Tingkatan model yang digunakan untuk memilih model ekstraksi. |
| `max_items_per_turn` | `5` | Maksimum kandidat yang diminta dari satu pesan. |
| `min_user_message_chars` | `8` | Pesan yang lebih pendek, setelah pemangkasan, diabaikan. |
| `initial_confidence` | `0.3` | Keyakinan yang diberikan kepada kandidat yang disimpan. |
| `timeout_seconds` | `20` | Timeout pembacaan transportasi untuk pemanggilan; bukan batasan waktu ekstraksi total (#634). |

```json
{
  "brain": {
    "auto_fact_extraction": {"enabled": false}
  }
}
```

Kunci `auto_fact_extraction` di bawah `agents.<id>` saat ini tidak berpengaruh. Parser profil agent tidak membacanya, dan bagian top-level tetap berlaku.

Model berasal dari profil agent yang efektif. Dengan tingkatan `reflect` default, ekstraksi menggunakan `reflect_model`, kemudian `decide_model`, lalu `act_model`, mana yang diatur lebih dulu. Itu tidak selalu merupakan model dari permintaan aksi utama. Tingkatan lain mencoba `<tier>_model`, kemudian `reflect_model`, lalu `decide_model`.

Pemanggilan melewati jalur retry output terstruktur yang sudah ada. Ini adalah satu pemanggilan ekstraksi logis, tapi bisa membuat lebih dari satu permintaan provider, dan penggunaan yang ditagih adalah pengukuran terpisah. Penghitung panggilan LLM giliran mencatatnya hanya saat pemanggilan terstruktur kembali, sehingga kegagalan provider bisa membuat permintaan model tidak tercatat; penghitung tersebut bukan hitungan dari permintaan provider yang dicoba. Ini hanya menawarkan alat output terstruktur `submit_output` yang dipaksakan. Daftar alat itu berlaku untuk pemanggilan tambahan ini: entri dan permintaan aksi giliran berikutnya membawa alat mereka sendiri.

Ekstraksi tidak dijalankan ketika:

- `enabled` adalah `false`;
- pesan lebih pendek dari `min_user_message_chars`;
- pesan merupakan perintah eksplisit `tool <name> ...`;
- penangkapan dikecualikan untuk giliran atau penulisan memori tidak diizinkan;
- giliran melewati penambahan pesan pengguna awal;
- layanan LLM, konteks, atau memori tidak tersedia, atau tidak ada model ekstraksi yang dikonfigurasi.

Ekstraksi yang gagal mengeluarkan `brain.auto_fact_extraction.skipped` dengan alasan `extraction_failed`, dan giliran terus berlanjut. Peristiwa `started`, `completed` dan `skipped` dari `brain.auto_fact_extraction` menunjukkan apa yang terjadi pada giliran tertentu. Saat mengukur jumlah permintaan atau biaya, hitung pemanggilan ini secara terpisah, atau bandingkan dengan `enabled` yang diatur ke `false` sebagai satu pengaturan yang diubah.

## Memilih perubahan berdasarkan bukti

Gunakan tugas representatif dengan batas dan catat:

1. Paket/commit, provider/model, profil efektif, prompt dan hasil yang diharapkan.
2. Setiap tujuan permintaan aktual, jumlah/ukuran skema, token input/output dan token cache yang dilaporkan oleh provider. Jaga penggunaan cache yang tidak diketahui berbeda dari nol, dan hilangkan kredensial serta konten prompt pribadi.
3. Penggunaan ember paket-konteks, segmen yang hilang dan `over_budget`, serta waktu perakitan lokal terpisah dari latensi provider.
4. Panggilan alat yang dieksekusi, iterasi loop, alasan penghentian tepat, keputusan kebijakan dan apakah tugas selesai dengan benar.

Bandingkan satu pengaturan pada satu waktu dalam sesi terisolasi yang setara. Pertahankan akses alat, kebijakan dan kriteria keberhasilan tanpa perubahan. Periksa penemuan alat yang diperlukan dan putaran tindak lanjut serta biaya. Ulangi sebelum mengklaim keunggulan kecepatan atau biaya; caching provider, latensi dan pilihan model bervariasi antar sampel.

Naikkan hanya batas yang habis ketika beban kerja yang valid menunjukkan bahwa batas tersebut terlalu kecil. Jika penyesuaian paket diterapkan dua kali, perbaiki pemilik tersebut daripada memperbesar defaultnya. Jika total yang ditampilkan tidak sesuai dengan jejak permintaan, selesaikan ketidaksesuaian akuntansi sebelum menggunakan mereka untuk menyetel default.

## Penilaian pemelihara untuk masalah #497

Pengukuran pada 29 Oktober 2026 di `bffd935d5` menggunakan profil resmi MiniMax-M2.7
dengan pemikiran minimal, status lokal baru, dan perlengkapan cari/baca/rangkum.
Batas konteks sesi adalah `0`; pasangan percobaan berbeda pada fitur pemilihan awal
yang dinonaktifkan atau diaktifkan. Keduanya selesai dengan benar dengan dua
pemanggilan alat file yang dieksekusi dan tanpa kesalahan alat.

| Pengamatan | Dinonaktifkan | Diaktifkan |
| --- | --- | --- |
| Permintaan provider aktual | 6 | 6 |
| Skema lengkap per permintaan | 1, 8, 4, 5, 5, 1 | 1, 8, 4, 5, 5, 1 |
| Token input dilaporkan provider | 30,541 | 30,882 |
| Token output dilaporkan provider | 1,755 | 1,904 |
| Token input cache dilaporkan provider | 6,215 | 6,318 |
| Waktu giliran terukur | 33.76 s | 42.04 s |
| Total waktu perakitan paket konteks terukur | 0.0430 s | 0.0393 s |

Ini adalah dua pengamatan, bukan tolok ukur kinerja perbandingan atau kualifikasi DeepSeek.
Keduanya tidak menghabiskan anggaran eksekusi. Keduanya menggunakan jalur skema yang diminta masuk,
jadi pasangan ini tidak mengukur manfaat dari pemilih awal opsional pada jalur lain.
Ringkasan respons hanya melaporkan satu panggilan LLM dan menghilangkan beberapa fase penggunaan;
tabel menggunakan tanggapan provider yang diambil sebagai gantinya.
Tidak ada klaim harga atau biaya yang ditagih berdasarkan total ini.

Rekomendasi saat ini adalah mempertahankan pengaturan default di atas.
Peningkatan menyeluruh, pembalikan pemilihan global, atau cache konteks baru
tidak didukung oleh bukti ini. Penyempurnaan lebih lanjut membutuhkan bukti khusus beban kerja dan
akuntansi giliran secara menyeluruh dan akurat. Ikuti penyelidikan dan perbaikannya yang terkait di
[#497](https://github.com/openminion/openminion/issues/497); penyesuaian jendela ganda yang dilaporkan secara mandiri tetap terpisah di
[#482](https://github.com/openminion/openminion/issues/482).
