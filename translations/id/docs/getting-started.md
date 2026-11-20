# Mulai dengan OpenMinion

Status: aktif
Terakhir diperbarui: 2026-09-06

Tujuan: memberikan kontributor dan penulis otomatisasi ringkasan bootstrap dan eksekusi lokal paket untuk pekerjaan di dalam repositori `openminion`.

## Bootstrap cepat

```bash
python3.11 -m venv .venv
source .venv/bin/activate
make dev-install
make hooks-install
```

Di Windows PowerShell, gunakan `.venv\Scripts\Activate.ps1`, kemudian jalankan target `make` yang sama dari lingkungan yang menyediakan GNU Make. Untuk penggunaan biasa, `pipx install openminion` atau `uv tool install openminion` menghindari penggunaan alat checkout sepenuhnya.

Pertahankan `.venv` checkout-local saat menginstal. `make dev-install` memastikan bahwa OpenMinion mengimpor dari checkout ini dan memperbaiki binding editable yang sudah usang. Ia menolak instalasi melalui tautan simbolik `.venv` agar worktree lain tidak bisa secara diam-diam mengubah rujukan lingkungan.

Untuk peluncuran pengembang yang jaminan sumbernya, gunakan `make run-local ARGS="..."` dari root paket. Ini menempatkan `src` checkout saat ini di posisi pertama meskipun metadata paket editable lingkungan menunjuk ke tempat lain:

```bash
make run-local ARGS='--dir "$PWD"'
```

Jika Anda menjalankan CLI secara lokal, juga atur:

```bash
export OPENMINION_HOME=.
export OPENMINION_DATA_ROOT="$OPENMINION_HOME/.openminion"
```

## Peluncuran pertama

Untuk instalasi paket publik, lebih baik gunakan instalasi baris perintah terisolasi:

```bash
pipx install openminion
# or: uv tool install openminion
```

Mulailah dengan perintah kosong:

```bash
openminion --version
openminion --dir "$PWD"
```

Jika konfigurasi default normal sudah ada, ini membuka terminal default secara langsung. Jika konfigurasi default hilang dan terminal tersedia, OpenMinion meluncurkan setup, membimbing Anda melalui pengaturan hosted, lokal, atau impor, menulis konfigurasi kanonik di
`~/.openminion/agents.json` (atau `<OPENMINION_HOME>/.openminion/agents.json` saat root itu disetel), menjalankan `doctor`, lalu masuk ke CLI interaktif.

Pemeriksaan koneksi penyedia hosted direkomendasikan dan dipilih dengan menekan Enter; ini mengirim satu permintaan singkat yang mungkin menggunakan kuota. Pemeriksaan ini menampilkan kemajuan dan waktu yang telah berlalu. Menekan Ctrl-C menghentikan pemeriksaan di foreground tanpa mengulang; konfigurasi yang disimpan tetap tersedia tetapi belum diverifikasi. Tugas pertama yang berguna adalah:

```text
List this workspace using the file tools.
```

Peluncuran kosong berikutnya menggunakan kembali konfigurasi yang sama dan membuka terminal langsung.

Perintah langsung `openminion mcp ...` menggunakan `./.openminion/agents.json` ketika `--config` dihilangkan, sesuai dengan default lingkup proyek SDK Python. Gunakan `--config ~/.openminion/agents.json` untuk mengelola konfigurasi setup interaktif sebagai gantinya. Perintah MCP yang mengubah konfigurasi melaporkan `config_path` tepat yang mereka tulis.

`--dir` eksplisit mempercayai workspace itu untuk proses saat ini. Tanpa itu, worktree Git biasa dipercaya, direktori lain dimulai dalam mode Baca-saja, dan peluncuran dari direktori home atau root sistem file dihentikan dengan panduan `--dir PATH`. Untuk menggunakan direktori saudara yang ada untuk proses interaktif yang sama, tambahkan secara eksplisit:

```bash
openminion --dir "$PWD" --add-dir ../shared
```

`--add-dir` dapat diulang dan tidak disimpan dengan sesi. Mulai ulang dengan opsi yang sama ketika Anda ingin mengulang hak akses. Akses file default tidak lagi menyertakan `~/projects` atau `~/Downloads`; pilih workspace yang eksplisit, gunakan `--add-dir`, atau konfigurasikan root kebijakan yang tepat yang Anda butuhkan.

Di dalam Focus, `/permissions` membuka empat postur sesi. Baca-saja hanya mengizinkan alat baca-saja yang terdaftar dan masih memblokir `exec.run`. Permintaan Ask memerlukan persetujuan untuk efek non-baca. Workspace otomatis melewati permintaan biasa hanya untuk `file.write` dan `file.edit` di dalam workspace yang diizinkan. Akses penuh melewati permintaan biasa setelah konfirmasi, tetapi aturan blok/tanya yang dikonfigurasi, penolakan yang dipilih, jalur workspace, pengaktifan host-execution, otorisasi finansial, perdagangan, blockchain, operasi yang tepat, dan konfirmasi `project.start` masih berlaku. Kontrol ini adalah kebijakan aplikasi, bukan sandbox sistem operasi. Gunakan `/permissions grants` dan `/permissions revoke <grant-id>` untuk memeriksa atau menghapus hak akses sesi aktif.

### Default kebijakan aksi persisten

`action_policy` tingkat atas adalah default untuk setiap agent tanpa kebijakan sendiri. Pertahankan perilaku berdasar kebijakan normal dengan:

```json
{
  "action_policy": {
    "mode": "auto",
    "default_action": "require_confirm",
    "allow_read_only_without_prompt": true
  }
}
```

Tetapkan pengganti spesifik agent di bawah `agents.<id>.action_policy`:

```json
{
  "default_agent": "local-coder",
  "agents": {
    "local-coder": {
      "provider": "openai",
      "action_policy": {
        "mode": "bypass"
      }
    }
  }
}
```

`action_policy.mode = "bypass"` menonaktifkan penegakan kebijakan aksi biasa untuk agent itu. Ini tidak mengatur Focus Akses penuh dengan sendiri karena Akses penuh juga menetapkan mode izin alat sesi. `permission_mode` bukan bidang yang didukung di bawah `agents.<id>`.

Untuk penggunaan interaktif, buka `/permissions`, pilih **Akses penuh**, dan kembali ke sesi bernama yang sama ketika Anda ingin menggunakan kembali postur. Untuk pekerjaan berbasis API, gabungkan kebijakan aksi per-agent di atas dengan masukan permintaan/sesi:

```json
{
  "agent_id": "local-coder",
  "session_id": "trusted-local-work",
  "permission_mode": "bypass",
  "message": "Run the requested local workflow."
}
```

Kontrol ini tidak mengekspos alat yang hilang, mengaktifkan host execution, memperluas root workspace, menggantikan blok eksplisit, atau menggantikan otorisasi satu kali tepat untuk aksi finansial, perdagangan, blockchain, dan operasi.

### Mulai ruang lokal human-plus-agents

Gunakan flag root eksplisit agar ruang dan telemetrinya tetap di bawah satu direktori runtime yang dipilih. Ganti `writer` dan `reviewer` dengan ID agent dari konfigurasi Anda:

```bash
runtime_root="$PWD/.openminion-room"
config_path="$HOME/.openminion/agents.json"
room_output="$(openminion \
  --home-root "$runtime_root/home" \
  --data-root "$runtime_root/data" \
  --config "$config_path" \
  room create \
  --name "Review room" \
  --human owner-local \
  --agent writer \
  --agent reviewer \
  --channel console \
  --target focus)"
room_id="$(printf '%s\n' "$room_output" | sed -n 's/^room=//p')"

openminion \
  --home-root "$runtime_root/home" \
  --data-root "$runtime_root/data" \
  --config "$config_path" \
  --agent writer \
  --session "$room_id" \
  --dir "$PWD"
```

Gunakan `/participants`, `/status`, dan `/sessions` untuk memeriksa ruang tersebut. Pemilik lokal dapat menggunakan `/invite`, `/kick`, `/activate`, dan `/routing`; alamat satu agent dengan `@reviewer`, atau pilih routing `broadcast` atau `sequential` untuk kedua agent.

Layar pertama langsung menuju provider model. OpenAI, Anthropic, OpenRouter, MiniMax, dan Ollama lokal muncul pertama; provider tambahan, endpoint eksperimental, endpoint khusus, dan impor konfigurasi tetap tersedia dari menu yang sama.

Mode demo bukan bagian dari onboarding normal. Ini tetap tersedia melalui jalur pengembangan/uji `openminion --demo` yang eksplisit. Demo non-interaktif juga dapat dibuat dengan `openminion config init --provider echo`. Ini memverifikasi konfigurasi lokal, penyimpanan, sesi, dan jalur CLI saja; tidak memanggil model. Oleh karena itu, `openminion status readiness` melaporkan `overall=demo` untuk konfigurasi tersebut sebagai ganti mengklaim kesiapan provider.

Setup menunjukkan tiga identitas yang penting selama putaran pertama:

1. provider, seperti OpenAI, Anthropic, OpenRouter, Ollama, MiniMax, Kimi, Z.ai, DeepSeek, Qwen/DashScope, Gemini, xAI, Mistral, Together, Cerebras, Groq, Cortensor Portal, Cortensor Router, atau endpoint khusus;
2. ID model, seperti `gpt-4.1-mini` atau `MiniMax-M2.7`; dan
3. adaptor API, seperti kompatibel OpenAI atau kompatibel Anthropic.

Untuk provider bawaan, OpenMinion secara otomatis memilih adaptor API. Adaptor menggambarkan kompatibilitas, bukan identitas provider. MiniMax tetap menjadi provider ketika menggunakan adaptor yang kompatibel dengan OpenAI.

Pengaturan provider di `agents.json` memiliki satu lokasi edit: blok tingkat atas `providers`. `openminion config init` menulis `providers.<id>` sekali dan tidak menduplikasinya di bawah `system.providers`, sehingga mengedit `providers.openai.base_url` (atau bidang lain) akan berlaku pada muatan berikutnya. Konfigurasi lama yang hanya mendefinisikan `system.providers` masih dapat dimuat, dan konfigurasi yang dengan sengaja mendefinisikan kedua blok mempertahankan preseden yang ada (`system.providers` menang); penyimpanan kemudian menulis nilai efektif kembali ke blok tingkat atas dan menghapus duplikatnya.

Kredensial lingkungan lebih diutamakan. Misalnya, pengaturan OpenAI membaca `OPENAI_API_KEY`; pengaturan MiniMax membaca `MINIMAX_API_KEY` sambil menggunakan adaptor yang kompatibel dengan OpenAI yang ada. Kompatibilitas tidak berarti berbagi akun atau kredensial; setiap provider tetap menggunakan kuncinya sendiri. Setup interaktif dapat menyimpan kunci yang ditempel secara lokal hanya setelah prompt tersembunyi, peringatan, dan konfirmasi. Pada sistem POSIX, direktori konfigurasi milik setup diperketat menjadi hanya pemilik `0700`, dan file konfigurasi yang dibuat setup adalah hanya pemilik `0600`.

Katalog setup dimiliki oleh runtime, jadi gunakan CLI daripada tabel provider yang disalin saat memilih atau mengintegrasikan provider:

```bash
# Human-readable catalog
openminion setup --list-providers

# Stable machine-readable catalog for clients and scripts
openminion setup --list-providers --json
```

Form JSON melaporkan setiap ID provider, label, variabel lingkungan kredensial, persyaratan kredensial, URL dasar default, dan model yang direkomendasikan menurut urutan. Mencantumkan provider tidak membuat permintaan ke provider.

Portal Cortensor tetap merupakan jalur hosting eksperimental karena ketersediaan layanan saat ini dapat lambat atau tidak stabil. Portal mengelola routing, kuota, kapasitas, dan siklus hidup permintaan internalnya. OpenMinion menetapkan batas waktu provider yang ada secara default menjadi 480 detik; nilai `timeout_seconds` yang dikonfigurasi lebih besar dipertahankan oleh runtime. Dukungan Portal saat ini meliputi teks, streaming teks, panggilan alat OpenAI asli, kelanjutan hasil alat, dan delta panggilan alat yang dipancarkan secara streaming. OpenMinion mempertahankan ID panggilan alat Portal, argumen, alasan penyelesaian, penggunaan, dan fakta korelasi `X-Request-ID`. Permintaan Portal tidak secara otomatis dicoba ulang karena pengiriman ulang belum bersifat idempoten. Portal saat ini menghilangkan `X-Request-ID` dari respons validasi permintaan FastAPI `422`; OpenMinion tidak dapat menangkap header yang tidak ada.

Jalankan penerimaan Portal awal secara serial. Dua permintaan simultan yang ditugaskan ke sesi Cortensor yang sama saat ini dapat menampilkan
`router_v4_correlation_mismatch` sebagai `502 router_error`; OpenMinion melaporkan kegagalan itu tanpa mencobanya ulang.

```bash
export CORTENSOR_API_KEY="..."
openminion setup --provider cortensor-portal --agent cortensor-portal --no-focus
```

Jalur Router langsung yang canggih tetap terpisah dan mempertahankan semantik sesi Router-nya. Gunakan preset `cortensor-router`. ID pengaturan warisan `cortensor`
hanya mengarah ke jalur langsung ini.

```bash
openminion setup --provider cortensor-router --agent cortensor-router --no-focus
```

Preset lokal `ollama` tidak memerlukan kredensial dan default ke endpoint lokal Ollama.

`/v1/models` berguna untuk diagnosis, tetapi tidak membuktikan kesiapan inferensi. Tambahkan `--check-provider` hanya ketika permintaan teks yang mengkonsumsi kuota diotorisasi.

Kecuali pengaturan menyatakan `live`, model yang diperiksa hanya merupakan fallback yang direkomendasikan. Dukungan provider berbasis fixture berarti OpenMinion memiliki cakupan permintaan lokal dan konfigurasi; ini bukan akun langsung, penagihan, kuota, atau jaminan ketersediaan model.

Commerce saat ini adalah fondasi lokal yang dikonfigurasi nonaktif. Tidak ada provider produksi yang dapat diaktifkan. Lihat [Commerce Order Care](guides/commerce-order-care.md) untuk siklus hidup lima alat, batas persetujuan satu kali yang tepat, pemulihan, perilaku pengalihan, dan perbedaan antara fixture, model langsung, sandbox, dan bukti produksi.

Untuk memindahkan pengaturan yang ada, ekspor tanpa rahasia yang tertanam dan impor di mesin baru:

```bash
openminion config export --out openminion-config.yaml
openminion setup
```

Pilih **Import an existing OpenMinion config**, masukkan jalur ekspor, dan konfirmasi ringkasan sumber/target yang telah disunting. Nilai yang diimpor menggantikan bidang yang cocok sementara pengaturan yang tidak terkait di konfigurasi target yang ada dipertahankan. Setara mandiri adalah:

```bash
openminion config import openminion-config.yaml
```

Tambahkan `--force` hanya ketika file yang diimpor harus menggantikan, bukan menggabungkan dengan konfigurasi yang ada. Kredensial tidak termasuk dalam ekspor normal, jadi setel variabel lingkungan provider yang dirujuk pada mesin tujuan. Batas token, anggaran konteks, dan nama variabel lingkungan kredensial tetap ada dalam ekspor; nilai kredensial, termasuk header otentikasi, tidak ada. Lihat [turn budgets and token cost](turn-budgets.md) sebelum mengubah batas untuk menangani penghentian awal atau giliran yang mahal.

Sebuah `file.read` mencakup `content_sha256` untuk teks UTF-8 penuh sebelum konversi baris baru atau pemotongan. Pembacaan lokal mempertahankan tampilan teks baris baru universal yang ada; sidik jari membedakan byte LF, CRLF, dan CR asli. Pembacaan di memori mempertahankan karakter baris baru asli. Pembacaan lokal lengkap juga mencakup `version` yang tidak tembus pandang. Untuk penimpaan kondisional, `file.write` menerima
`expected_content_sha256` (operkan `content_sha256` dari bacaan secara langsung) dan `expected_version`. Ketidaksesuaian mengembalikan `PRECONDITION_FAILED` sebelum pemangkasan. Penambahan kondisional ditolak. Penggantian kondisional lokal memerlukan penguncian file advisori dan gagal tertutup ketika tidak tersedia; kunci tersebut mengoordinasikan penulis yang berpartisipasi, bukan proses eksternal sembarangan. Backend di memori mendukung prekondisi konten.

Loop adaptif memungkinkan satu percobaan baca aman identik setelah kegagalan transien terstruktur. Ini juga dapat mencoba menimpa identik satu kali setelah pembacaan ulang lengkap jalur yang sama yang membantah konten yang diakui, menambahkan konten dan prekondisi versi yang tersedia. Izin dan anggaran diperiksa ulang. Penambahan, efek eksternal dan pembacaan parsial tidak menerima pemulihan ini.

Alat file mempertahankan byte baris baru di luar rentang yang diedit dan menolak konten UTF-8 tidak valid sebelum memodifikasi berkas. `file.read_range` menghitung berkas aktual dan menolak awal di luar EOF. `file.search` mendukung glob relatif akar pencarian dan menandai hasil tidak lengkap sebagai terpangkas. `file.trash` menggunakan fasilitas sampah asli melalui Send2Trash dan tidak pernah menggantikan penghapusan permanen. Pemulihan berkas/direktori asli diverifikasi di macOS; pemulihan Windows dan Linux masih memerlukan kualifikasi khusus platform. Backend memori menolak sampah tanpa menghapus konten karena tidak memiliki fasilitas sampah yang dapat dipulihkan.

Otomatisasi dapat menggunakan jalur pengaturan yang sama tanpa prompt:

```bash
openminion setup \
  --provider minimax \
  --model MiniMax-M2.7 \
  --agent minimax-m27 \
  --no-focus
```

Di dalam CLI interaktif, `/model` hanya menampilkan model yang dikonfigurasikan untuk agent aktif. Sebuah koneksi adalah layanan dan rute kredensial/endpoint, sementara format API menjelaskan bagaimana OpenMinion berkomunikasi dengannya. Misalnya, MiniMax adalah koneksi dan OpenAI-compatible adalah format API.

```text
/model
/model use 2
/model default 2
/model add MiniMax-M2.7-highspeed
/model setup
```

`/model use <#>` mengubah sesi saat ini dan dipulihkan saat sesi tersebut dilanjutkan. `/model default <#>` memperbarui default tersimpan dari agent aktif.
`/model add <model>` menambahkan model ke koneksi saat ini dan langsung memilihnya untuk sesi; default agent tetap tidak berubah. `/model setup` menggunakan preset provider yang sama dan penulis konfigurasi di dalam terminal Focus untuk menambahkan koneksi berbeda, meninjaunya, menyimpannya, dan menggunakannya tanpa perlu memulai ulang.
`openminion setup` tetap tersedia untuk pengaturan pertama kali dan pengaturan skrip.

Untuk provider yang kompatibel dengan OpenAI lainnya, pilih preset provider dan model:

```bash
openminion setup \
  --provider qwen-dashscope \
  --model qwen3.7-plus \
  --agent qwen3.7-plus \
  --no-focus
```

Polanya sama untuk `kimi`, `zai`, `zai-coding`, dan `deepseek` dengan variabel lingkungan dan ID model masing-masing.

Pengaturan non-interaktif membaca kredensial dari variabel lingkungan provider dan secara default tidak mengirim permintaan ke provider jarak jauh. Tambahkan `--check-provider` hanya saat sesi diizinkan untuk membuat satu permintaan terbatas ke provider yang dapat mengkonsumsi kuota.

Endpoint kustom bersifat eksplisit:

```bash
openminion setup \
  --provider custom-openai-compatible \
  --api-format openai-compatible \
  --base-url https://example.test/v1 \
  --model provider-model-id \
  --agent custom-openai \
  --no-focus
```

Endpoint kustom menggunakan `custom-openai-compatible` atau `custom-anthropic-compatible`; keduanya memerlukan format API yang eksplisit, URL dasar, dan ID model.

## Akses perintah per-agent

Eksekusi host tanpa sandbox tetap dinonaktifkan secara default. Profil agent lokal terpercaya dapat mengizinkan eksekusi tertentu dan memilih untuk menggunakan eksekusi host tanpa mengubah profil lain:

```json
{
  "agents": {
    "local-docker": {
      "provider": "minimax",
      "command_policy": {
        "allow": ["docker"],
        "allow_host": true
      }
    }
  }
}
```

Eksekusi harus berasal dari direktori host terpercaya. Aturan persetujuan perintah berbahaya yang sudah ada tetap berlaku; pengaturan profil ini tidak melewati aturan tersebut. Nama eksekusi harus tepat; `"*"` bukan entri izinkan-semua yang didukung.
Jika tidak ada sandbox perintah yang dikonfigurasi, `exec.run` mengembalikan
`SANDBOX_UNAVAILABLE` dan merekomendasikan alat file terstruktur, sandbox yang dikonfigurasi, atau memulai ulang dengan `--allow-unsandboxed-exec`. Flag ini menjalankan perintah dengan izin OS dari proses OpenMinion; perintah tidak dibatasi pada workspace atau direktori tambahan. Akses penuh tidak mengaktifkan eksekusi host.
Sandbox lokal asli dan kesetaraan perintah tanpa persetujuan masih menjadi pekerjaan masa depan.

## Baca terlebih dahulu

Sebelum melakukan perubahan kode yang substansial, baca:

1. [`engineering-patterns.md`](engineering-patterns.md)
2. [`code-quality-enforcement.md`](code-quality-enforcement.md)
3. [`source-tree-owner-map.md`](source-tree-owner-map.md)
4. [`runtime-surfaces.md`](runtime-surfaces.md)

## Siklus eksekusi normal

1. Pilih satu perubahan fokus.
2. Terapkan kode dan dokumentasi bersama ketika permukaan publik berubah.
3. Tambahkan atau perbarui pengujian untuk perilaku yang Anda ubah.
4. Jalankan validasi fokus selama iterasi.
5. Jalankan `make lint` sebelum menandai pekerjaan siap.
6. Catat perintah validasi dalam deskripsi PR.

## Bentuk pull request

Bentuk PR yang disukai:

1. judul singkat, asli GitHub,
2. butir datar yang merangkum perubahan,
3. label `Validation` polos diikuti dengan butir perintah yang tepat.

Contoh:

`Add package-local workspace sync helpers`

- menambah perencanaan sinkronisasi workspace bertipe
- menambah helper apply/status eksplisit
- menyelaraskan dokumentasi publik

Validasi
- `make lint`
- `python -m pytest -q tests/<target>`

## Bentuk pesan commit

Gunakan pesan commit dalam bentuk:

1. `<type>(<scope>): <summary>`

Tipe yang disetujui saat ini adalah:

1. `feat`
2. `fix`
3. `docs`
4. `refactor`
5. `test`
6. `chore`
7. `style`
8. `build`

Panduan:

1. sertakan scope secara default di `openminion`,
2. pilih scope pemilik nyata seperti `agent`, `api`, `cli`, `e2e`, `gateway`,
   `runtime`, `telemetry`, `tool`, atau `tools`,
3. buat ringkasan spesifik pada perubahan yang dilakukan,
4. hindari subjek kabur seperti `update`,
5. pilih tipe yang paling spesifik dan benar; jangan gunakan `chore` jika `docs`,
   `test`, `refactor`, atau `build` lebih akurat,
6. jangan gunakan singkatan lokal atau label perencanaan sebagai tipe commit biasa.

## Pengingat batas

1. `README.md` adalah kontrak paket dan permukaan instalasi.
2. `API_COMPATIBILITY.md` adalah janji impor/ekspor publik.
3. `docs/` adalah lapisan dokumentasi publik lokal paket.
4. `tests/` dan `scripts/` penting, tetapi bukan API library publik.
