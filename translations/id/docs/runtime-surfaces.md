# OpenMinion Runtime Surfaces

Status: aktif
Terakhir diperbarui: 2026-10-06

Tujuan: memberikan kepada pengembang satu peta paket lokal dari permukaan publik `openminion` dan kapan harus menggunakan masing-masing.

## Permukaan utama

### 1. CLI Interaktif

Penggunaan:

1. `openminion`
2. `python -m openminion`

Terbaik untuk:

1. penggunaan operator lokal interaktif,
2. pekerjaan percakapan dengan penggunaan alat,
3. alur kerja terminal-first.

Catatan:

1. pemanggilan default meluncurkan satu-satunya perender terminal interaktif pada sebuah TTY,
2. masukan yang dipipakan menjalankan satu permintaan tanpa memasang perender interaktif,
3. nama perintah lama `focus`, `chat`, `tui`, dan `dashboard` sudah dihentikan dan ditolak,
4. startup membuat sesi baru kecuali jika `--session <id>` disediakan,
5. `openminion room` membuat dan mengelola sesi ruang agen-manusia lokal; gunakan ID ruang yang dikembalikan dengan `--session` untuk memasuki ruang tersebut di CLI interaktif.

### 2. API library Python

Gunakan:

1. `import openminion`
2. `from openminion import Agent, ProviderError, tool`
3. `from openminion.api import APIRuntime, Agent, RuntimeTurnHandle, TurnChunk, TurnResponse`

Terbaik untuk:

1. menyematkan OpenMinion ke dalam aplikasi Python,
2. komposisi runtime langsung,
3. eksekusi giliran eksplisit dari kode,
4. integrasi tool/penyerahan bertipe.

`Agent` memiliki sesi terisolasi secara default. Berikan `session_id` ke
konstruktor atau ke `run()` ketika aplikasi sudah memiliki kunci kontinuitas.
Berikan `config_path` untuk konfigurasi milik proyek dan `agent_id` untuk memilih
profil yang dikonfigurasi. Panggilan agent mengembalikan hasilnya ke Python tanpa pengiriman konsol,
dan `AgentRunResult.session_id` menampilkan kunci kontinuitas yang sudah diselesaikan.
`Agent` juga mendukung `with Agent(...) as agent:` untuk pembersihan deterministik.
`tools=None` mempertahankan eksposur tool default yang dikonfigurasi; `tools=[]` menonaktifkan
aplikasi dan tool orkestrasi untuk giliran tersebut. `handoffs` eksplisit menambahkan
tool transfer mereka ke dalam daftar. Permintaan tool yang dipaksa tidak menggantikan daftar putih yang kosong.
Skema keluaran terstruktur internal masih dapat digunakan untuk penalaran runtime;
mereka tidak dapat mengirimkan tool aplikasi.
Metode `run_stream()`-nya adalah giliran sinkron dengan callback progres. Untuk
streaming iterator, pembatalan, atau resolusi persetujuan eksplisit, panggil
`APIRuntime.submit_turn()` dan gunakan `RuntimeTurnHandle` yang dikembalikan.
`examples/sdk/submitted_stream.py` menunjukkan siklus hidup itu menggunakan impor publik.

`Agent.run()` dan callback progres `run_stream()` menerima kontrol opsional
`timeout_seconds`, `approval_callback`, dan `cancel_event` yang sudah dimiliki oleh ingress runtime.
Hasil mereka menampilkan ID hasil kanonik, metadata, dan statistik bersamaan dengan keluaran dan bidang kontinuitas yang sudah ada.
Laporan giliran `stats` mengamati panggilan LLM dan token input, output, dan pembacaan cache yang dilaporkan penyedia
melintasi refleksi, entri, aksi, dan penilaian, termasuk langkah kelanjutan dalam run yang sama.
Total ini juga mengisi metadata respons dan statistik pesan keluar yang dipertahankan.
Peristiwa panggilan kanonik mendukung tampilan penggunaan token terperinci; pengulangan acara panggilan yang sama tidak menambah penggunaan lagi.
Subtotal loop aksi tidak ditambahkan ke acara tersebut.

Panggilan menghitung permintaan klien logis, bukan upaya ulang transport mereka.
Koreksi keluaran terstruktur yang membuat permintaan lain adalah panggilan lain.
Penggunaan yang diketahui bertahan dari respons kosong yang ditolak dan kegagalan kebijakan respons.
Penggunaan yang tidak dilaporkan, termasuk penggunaan dari upaya transport yang gagal, tidak diketahui;
nol dalam ringkasan numerik bukan bukti penagihan nol.
Metadata respons `llm_usage_coverage` mencatat dimensi token yang dilaporkan, hilang, dan tidak valid.
Ketika fakta acara tidak tersedia, total aksi warisan dan hitungan inferensi tetap menjadi cadangan,
dengan hitungan yang dilabeli `unknown` daripada fase yang diduga.
Pelaporan ini tidak menyelesaikan anggaran eksekusi anak atau mengagregasi hasil tool anak;
itu terpisah dari pengamatan penggunaan LLM.

Konfirmasi kebijakan aksi mencapai `approval_callback` sebelum eksekusi tool.
Mengembalikan true memberi izin panggilan itu sekali; false atau kegagalan callback mencegah
eksekusi. Tanpa callback, alur konfirmasi interaktif tetap ada.
Giliran yang diserahkan mengirimkan permintaan yang sama melalui acara alir persetujuan.

Fungsi `@tool` mana yang mendapatkan konfirmasi bergantung pada bagaimana mereka dideklarasikan.
Di bawah kebijakan aksi default:

- `@tool` tanpa atribut adalah penulisan lokal dengan kebalikan yang tidak diketahui,
  jadi dikonfirmasi sebelum dijalankan;
- `@tool(min_scope="READ_ONLY", idempotent=True)` adalah pembacaan tanpa efek samping
  dan berjalan tanpa konfirmasi, seperti di `examples/sdk/tool_agent.py`.
  Penolakan eksplisit, penanganan target sensitif, dan kebijakan operator tetap berlaku;
- `idempotent=True` sendirian masih meninggalkan penulisan, yang dikonfirmasi;
- `dangerous=True` bersifat destruktif dan tidak dapat dibatalkan, dan memerlukan konfirmasi
  kecuali ada izin yang sesuai atau aturan kebijakan eksplisit yang menyelesaikannya terlebih dahulu;
- `tags` dan `capabilities` tidak menyatakan risiko.

Docstring dari `openminion.tool` mencantumkan pemetaan lengkap.

Dalam alur itu, giliran diakhiri dengan metadata `respond_kind` `policy_confirmation_prompt`,
dan panggilan menunggu di thread giliran.
`run()` yang lebih kemudian tanpa thread memulai thread baru, jadi tidak menjawab konfirmasi.
Untuk menjawabnya, berikan `thread_id` dari hasil sebelumnya ke `run()` atau `run_stream()`:
runtime kemudian melanjutkan thread itu. Jika dihilangkan atau kosong, `thread_id` tidak mengubah apa pun.
ID thread dari sesi lain tidak menjawab konfirmasi sesi tersebut, dan dengan `approval_callback` callback masih memutuskan.

```python
first = agent.run("Remember that I write code in Iosevka 14.")
if first.metadata.get("respond_kind") == "policy_confirmation_prompt":
    # Answer the confirmation on the thread that is waiting for it.
    answer = agent.run("yes", thread_id=first.thread_id)
```

Simbol akar yang diekspor stabil dicatat di `API_COMPATIBILITY.md`.
Tipe siklus hidup giliran lanjutan diekspor dari `openminion.api`, bukan ditambahkan ke paket akar.

### 3. Permukaan runtime/API server

Penggunaan:

1. `openminion.api.APIRuntime`
2. `openminion.api.dispatch_request`

Terbaik untuk:

1. integrasi layanan HTTP lokal,
2. adaptasi permintaan/response,
3. komposisi runtime yang harus tetap berada di luar CLI interaktif.

### 4. CLI operator pendamping

Gunakan saat Anda memerlukan kontrol subsistem yang lebih sempit:

1. `telemetryctl`
2. `opsctl`
3. `openminiond`
4. `openminion-tool`
5. `identityctl`
6. `openminion-controlplane`
7. `runtimectl`
8. `brainctl`
9. `memctl`
10. `sessctl`
11. `contextctl` / `ctxctl`
12. `agentregctl`
13. `artifactctl`
14. `openminion-controlplane-telegram`
15. `openminion-controlplane-slack`
16. `skill` / `skillctl`
17. `a2actl`
18. `rlmctl`
19. `retrievectl`
20. `policyctl`

Terbaik untuk:

1. alur kerja operator yang deterministik,
2. inspeksi subsistem,
3. alur pemeliharaan lokal yang eksplisit.

### 5. Inspeksi grafik visual

Gunakan:

1. `openminion graph status`
2. `openminion graph view --current`
3. `openminion graph view --brain third --provider <name>`
4. `/graph` di dalam CLI interaktif untuk perintah viewer yang dapat disalin

Terbaik untuk:

1. memeriksa apakah lensa grafik visual sudah siap sebelum membukanya,
2. membuka grafik memori second-brain saat ini di viewer GraphFakos bersama,
3. membuka grafik provider third-brain yang dikonfigurasi ketika mereka menampilkan envelope viewer atau snapshot PragmaGraph,
4. memeriksa node, hubungan, asal-usul, kutipan, dan status provider,
5. menyematkan lensa grafik netral provider di aplikasi host tanpa mengimpor internal OpenMinion.

Catatan:

1. pasang `openminion[viewer]` untuk menyertakan dukungan GraphFakos dan snapshot PragmaGraph,
2. permukaan visual adalah lensa atas status grafik saat ini, bukan backend memori atau pengindeks grafik,
3. `openminion graph status --json` melaporkan ketersediaan GraphFakos, jalur database memori second-brain, provider third-brain yang aktif, kesiapan visual, kode diagnostik, panduan memori kosong, dan perintah berikut yang disarankan,
4. `openminion graph view --dry-run --json` membangun grafik yang dipilih dan mengembalikan jumlah, filter, facet, detail provider, metadata status kosong, dan ringkasan manifest viewer tanpa memulai viewer browser lokal,
5. `openminion graph view --html-out viewer.html` menulis halaman visual statis untuk inspeksi atau berbagi,
6. `openminion graph view --current --agent <id>` dan `openminion graph view --current --session <id>` mempersempit tampilan second-brain ke satu cakupan memori,
7. `openminion graph view --current --node-kind fact`, `--edge-kind`, `--tag`, `--source`, `--min-score`, dan `--evidence-filter` memaparkan filter viewer GraphFakos dari CLI OpenMinion,
8. viewer lokal yang disajikan mengarahkan formulir workbench melalui handler aksi netral provider GraphFakos, sementara lensa second-brain Sophiagraph saat ini mengembalikan status eksplisit unsupported/owned-by-provider untuk penulisan tahan lama,
9. viewer second-brain yang disajikan dapat melakukan streaming patch langsung GraphFakos `snapshot_reset` melalui aliran peristiwa lokal `/api/live` ketika memori Sophiagraph berubah; probe HTML statis dan JSON menyegarkan dengan menjalankan ulang perintah viewer yang sama,
10. lihat `docs/graph-viewer.md` dan `examples/graph-viewer/` untuk envelope provider third-brain yang dapat disalin.

### 6. ACP dan MCP yang dipublikasikan

Gunakan `openminion acp` untuk koneksi lokal Agent Client Protocol. ACP mengirim teks asisten serta pembaruan siklus hidup panggilan alat (`in_progress`, `completed`, atau `failed`). Argumen alat dan keluaran alat tidak disalin ke dalam pembaruan kemajuan tersebut; persetujuan berlanjut melalui permintaan izin ACP.

Saat `runtime.mcp_publish` diaktifkan, `openminion mcp serve` mempublikasikan alat runtime yang diizinkan melalui MCP. Alat yang dipublikasikan menyatakan skema input dan output. Panggilan yang berhasil mengembalikan objek JSON yang sama sebagai blok konten teks dan sebagai `structuredContent`; keluaran yang tidak sesuai skema yang dinyatakan dikembalikan sebagai kesalahan alat MCP.

## Contoh permukaan

Pohon `examples/` milik paket merupakan bagian dari permukaan pengajaran publik:

1. `examples/starter/provider.py`
2. `examples/starter/channel.py`
3. `examples/starter/hello.py`
4. `examples/starter/tool.py`
5. `examples/starter/hello.manifest.json`
6. `examples/starter/quickstart.py`
7. `examples/agents/hello/`
8. `examples/skills/hello/`
9. `examples/modules/sample/`

Impor akar `openminion` dan `openminion.api` yang digunakan oleh contoh-contoh ini adalah permukaan paket publik. Contoh ekstensi mencerminkan output scaffold saat ini; impor dalam yang lebih sempit mereka dipertahankan sebagai kontrak pengajaran untuk lini sebelum versi 1.0, bukan janji stabilitas untuk sisa pohon paket mereka.

## Tidak sepenuhnya publik

Dapat diimpor tidak otomatis berarti API publik yang stabil.

Perlakukan pohon-pohon ini sebagai milik internal/paket kecuali dokumen yang lebih sempit menyatakan lain:

1. `openminion.modules.*`
2. `openminion.services.*`
3. `openminion.tools.*`
4. `tests/`
5. `scripts/`

Satu contoh yang patut disebut: `openminion.modules.brain.runtime.approval` mengekspor
`gate_destructive_action` dan `LLMActionApprovalVerifier`, tapi tidak ada pemanggil produksi dalam pohon repositori yang membuat atau memanggil mereka,
dan bendera `enabled`-nya default ke false. Ketidakhadiran itu hanya mencakup repositori ini —
importir eksternal tidak dapat diamati di sini, itulah sebabnya ekspor dipertahankan daripada dihapus.
Persetujuan aksi destruktif dimiliki oleh alur konfirmasi kebijakan, yang memegang
konfirmasi, kontrak izin dan pemutaran ulang. Paket persetujuan adalah kode yang tersedia,
bukan gerbang yang menilai aksi destruktif hari ini.
