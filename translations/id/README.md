<p align="center">
  <img src="https://www.openminion.com/brand/openminion-logo-transparent-v1.png" alt="OpenMinion logo" width="128" />
</p>

<h1 align="center">OpenMinion</h1>

<p align="center">
  <strong>Runtime lokal-pertama, Python-pertama untuk agen AI yang menggunakan alat.</strong>
</p>

<p align="center">
  <a href="https://github.com/OpenMinion/openminion">GitHub</a>
  · <a href="https://pypi.org/project/openminion/">PyPI</a>
  · <a href="https://www.openminion.com">Situs Web</a>
  · <a href="https://www.openminion.com/docs/">Dokumentasi</a>
  · <a href="https://x.com/OpenMinion">X</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/openminion/"><img alt="PyPI" src="https://img.shields.io/pypi/v/openminion?cacheSeconds=300"></a>
  <a href="https://pypi.org/project/openminion/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/openminion?cacheSeconds=300"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-6B7280">
</p>

OpenMinion adalah pratinjau publik dari runtime untuk menjalankan agen yang dapat diperiksa
pada mesin Anda sendiri. Satu runtime bersama mencakup CLI, API Python, API HTTP,
dan alur kerja berbasis daemon, dengan sesi tahan lama, alat terstruktur, dan
status jalan yang dapat diperiksa terintegrasi. Klaim otonomi jangka panjang,
kegigihan provider langsung, dan kegunaan memori/konteks tetap dibatasi bukti selama
periode alfa.

## Baca Ini Dulu

1. Baca [Sekilas](#at-a-glance) untuk mengonfirmasi batas produk saat ini.
2. Ikuti [Install](#install) dan [Mulai Cepat](#quick-start) untuk satu kali jalan lokal.
3. Gunakan [Permukaan Runtime](#runtime-surfaces) untuk memilih operasi CLI, Python, HTTP,
   atau berbasis daemon.
4. Baca [Pengembangan](#development) sebelum mengubah runtime.
5. Gunakan [situs dokumentasi](https://www.openminion.com/docs/) untuk manual lengkap operator dan kontributor.

## Kepercayaan dan Keamanan Merek

- GitHub Resmi: <https://github.com/OpenMinion/openminion>
- Situs web dan dokumentasi resmi: <https://www.openminion.com>
- Akun X resmi: <https://x.com/OpenMinion>

OpenMinion tidak memiliki token resmi, koin, NFT, airdrop, program staking,
produk treasury, atau penawaran investasi. Klaim sebaliknya tidak sah
dan harus diperlakukan sebagai penipuan.

## Sekilas

| | |
| --- | --- |
| Paket | `openminion` |
| Jalur saat ini | Pratinjau publik untuk tonggak sumber/CLI yang dapat digunakan secara luas `0.1.x` |
| Python | 3.11+ |
| Cocok untuk | Alur kerja lokal terbatas, penggunaan alat, integrasi, dan agen yang digerakkan operator |
| Permukaan utama | CLI, API Python, API HTTP lokal, dan eksekusi berbasis daemon |
| Model status | Sesi lokal, percakapan, thread, run, artefak, dan catatan memori |
| Bukan klaim | Otonomi selesai tanpa pengawasan atau pengelolaan cloud control plane |

OpenMinion dapat digunakan untuk pekerjaan lokal yang terfokus hari ini, namun masih dalam pengembangan aktif.
Prompt end-to-end yang kompleks dan tugas panjang tanpa pengawasan masih terus diperbaiki.
Dukungan sertifikasi otonomi 2 jam saat ini hanya untuk validasi; pilot sertifikasi penuh 8 jam dan 24 jam
masih membutuhkan jendela run yang disetujui, akses provider/model, workspace, dan anggaran.

[Kontrak kompatibilitas 0.1.x](API_COMPATIBILITY.md#01x-compatibility-contract)
mencakup permukaan Python dan CLI yang terdokumentasi. Ini tidak mengklaim biner Desktop bertanda tangan,
layanan cloud yang dikelola, atau sertifikasi otonomi jangka panjang yang selesai.

## Perintah Umum

```bash
openminion config init
openminion setup --list-providers
openminion setup --list-providers --json
openminion run "hello"
openminion
openminion tools list
openminion doctor --check-turn --json
# Optional: install "openminion[acp]" before using a local ACP client.
openminion acp
```

Permukaan operator yang berguna:

```bash
openminion agent ls
openminion agent status --agent-id default
openminion agent logs
openminion agent inspect --agent-id default --json
```

## Instalasi

Instal paket saat ini sebagai aplikasi command-line yang terisolasi:

```bash
pipx install openminion
```

atau, dengan `uv`:

```bash
uv tool install openminion
```

Instalasi ke dalam lingkungan Python yang sudah ada juga didukung:

```bash
python3.11 -m pip install openminion
```

Untuk checkout sumber:

```bash
git clone https://github.com/OpenMinion/openminion.git
cd openminion
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Pada Windows PowerShell, aktifkan lingkungan yang sama dengan:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Untuk data lokal terisolasi selama pengembangan:

```bash
export OPENMINION_HOME="$PWD"
export OPENMINION_DATA_ROOT="$OPENMINION_HOME/.openminion"
```

## Memulai Cepat

Untuk sesi nyata yang didukung model, mulai dengan perintah dasar berikut:

```bash
openminion --version
openminion --dir "$PWD"
```

Setup akan meminta provider, model, dan kredensial. Untuk provider bawaan,
OpenMinion akan memilih adaptor API secara otomatis. Sebagai contoh, MiniMax tetap
menjadi provider saat menggunakan API yang kompatibel dengan OpenAI. Tekan Enter saat
pemeriksaan provider hosted untuk mengirim satu permintaan tes yang direkomendasikan
sebelum Focus dibuka; permintaan ini mungkin mengonsumsi sedikit kuota. Gunakan perintah
provider-list di atas untuk katalog dalam bentuk yang dapat dibaca manusia atau mesin.

`--dir` yang eksplisit mempercayai workspace itu untuk proses saat ini. Peluncuran dasar
juga mempercayai Git worktree biasa; direktori implisit lain memulai dalam mode Baca saja.
Meluncurkan dari direktori home Anda atau root filesystem memerlukan `--dir PATH` yang eksplisit.
Tambahkan direktori lainnya yang sudah ada untuk proses saat ini dengan opsi `--add-dir PATH` yang
berulang:

```bash
openminion --dir "$PWD" --add-dir ../shared
```

Alat file terstruktur tetap terbatas pada workspace, direktori yang secara eksplisit
ditambahkan, dan root kebijakan yang dikonfigurasi. Perintah host tetap dinonaktifkan
ketika sandbox tidak dikonfigurasi. `--allow-unsandboxed-exec` adalah opt-in eksplisit: perintah akan menggunakan
izin OS proses OpenMinion dan tidak terbatas pada root workspace; kebijakan perintah dan
persetujuan masih berlaku. Sandbox lokal asli dan kesetaraan perintah tanpa persetujuan
belum disediakan.

Dalam Focus, `/permissions` membuka mode Baca saja, Ask, Workspace auto, dan Akses penuh.
Workspace auto sengaja dibuat sempit: hanya `file.write` dan `file.edit` yang melewati prompt biasa mereka,
dan penegakan workspace/path tetap aktif. Akses penuh memerlukan konfirmasi dan tidak
melewati aturan blok/tanya yang dikonfigurasi, penolakan terpilih, pengaktifan execution host,
autorisasi keuangan atau operasional yang tepat, atau `project.start`. Sikap izin dan grant sesi tepat
bertahan dengan sesi OpenMinion; `/permissions grants` mencantumkan grant aktif dan `/permissions revoke <grant-id>` menghapus salah satu.

Untuk default kebijakan aksi yang tahan lama, letakkan `action_policy` di root konfigurasi atau di bawah
profil satu agent. Bentuk per agent adalah:

```json
{
  "agents": {
    "local-coder": {
      "provider": "openai",
      "action_policy": {"mode": "bypass"}
    }
  }
}
```

Ini menonaktifkan prompt kebijakan aksi biasa untuk agent itu, namun ini bukan saklar
Akses penuh yang persisten: Akses penuh juga mengatur mode izin alat sesi. `permission_mode` tidak didukung
dalam `agents.<id>`. Pilih Akses penuh melalui `/permissions` dan gunakan ulang sesi yang sama, atau lewati
`permission_mode` sebagai input API/permintaan yang dipercaya. Lihat [Getting Started](docs/getting-started.md#persistent-action-policy-defaults).

Saat setup selesai dan CLI interaktif terbuka, tanya: `List this workspace
using the file tools.` Konfigurasi default disimpan
pada `~/.openminion/agents.json`, sehingga peluncuran dasar berikutnya menggunakan ulang konfigurasi tersebut.

Perintah langsung `openminion mcp ...` menggunakan `./.openminion/agents.json` ketika `--config` dihilangkan, sesuai dengan default proyek berbasis SDK Python.
Lewati `--config ~/.openminion/agents.json` untuk mengelola konfigurasi setup interaktif sebagai gantinya. Perintah MCP yang
mengubah konfigurasi melaporkan `config_path` yang tepat yang ditulis.

Untuk tur produk tanpa kredensial, buat konfigurasi echo/demo eksplisit:

```bash
openminion config init --provider echo
openminion run "hello"
openminion status readiness
```

Mode demo melatih konfigurasi, penyimpanan, sesi, dan sistem CLI, namun tidak memanggil model
atau membuktikan kualitas tugas yang didukung provider. Laporan kesiapan memberi label
status ini `demo`, bukan `ready`.

Buka CLI interaktif:

```bash
openminion --dir "$PWD"
```

Jalankan dua agent yang sudah dikonfigurasi dalam satu ruang Focus dengan root runtime yang eksplisit:

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

Dalam Focus, gunakan `/participants` untuk memeriksa ruangan, `/routing broadcast` atau `/routing sequential` untuk mengubah modenya, dan
alamatkan satu agent dengan `@reviewer`. Mutasi ruangan memerlukan pemilik lokal; peserta bisa
mengirim dan pengamat tidak bisa.

Sematkan sesi agent terisolasi dari Python:

```python
from openminion import Agent, ProviderError, tool

@tool(min_scope="READ_ONLY", idempotent=True)
def lookup_order(order_id: str) -> str:
    return f"order {order_id}: ready"

try:
    with Agent(
        instructions="Answer briefly.",
        tools=[lookup_order],
        session_id="customer-42",
    ) as agent:
        result = agent.run("Check order A-104")
        print(result.text, result.session_id)
except ProviderError as exc:
    print(f"provider failed: {exc}")
```

`lookup_order` menyatakan dirinya hanya-baca, sehingga kebijakan aksi default menjalankannya tanpa
konfirmasi. Dalam kebijakan yang sama, `@tool` dianggap sebagai tulis dan harus dikonfirmasi
terlebih dahulu; lihat [Runtime surfaces](docs/runtime-surfaces.md) untuk bagaimana opsi `@tool` dipetakan ke persetujuan.

Lewati `config_path="path/to/agents.json"` untuk menggunakan konfigurasi milik proyek dan `agent_id="reviewer"` untuk memilih profil yang sudah dikonfigurasi.
Untuk komposisi runtime lanjutan, buat `APIRuntime` langsung dan lewati sebagai `runtime=` sebagai gantinya.

Lihat [`examples/starter/quickstart.py`](examples/starter/quickstart.py) untuk contoh lengkap yang dapat dijalankan dan
[`docs/getting-started.md`](docs/getting-started.md) untuk bootstrap kontributor.

## Apa yang Disediakan OpenMinion

- satu model orkestrasi di seluruh CLI, Python, HTTP, dan jalur berbasis daemon
- abstraksi provider untuk backend model lokal dan hosted
- alat terstruktur dengan kontrak berorientasi model dan eksekusi yang dibatasi kebijakan
- sesi lokal yang tahan lama, run, artifact, catatan memori, dan status percakapan
- alur kerja lokal interaktif dan satu kali
- diagnostik, status, log, inspeksi, dan jejak yang siap OpenTelemetry
- permukaan ekstensi untuk alat, provider, keterampilan, memori, dan integrasi

## Apa yang Tidak Disediakan oleh OpenMinion

- otonomi “selesaikan tugas kompleks apa pun dan tinggalkan” yang selesai
- plane kontrol yang dihosting atau layanan agent cloud yang dikelola
- bukti sertifikasi yang didukung provider tanpa kredensial provider yang dikonfigurasi dan jendela run yang disetujui
- pembungkus prompt kotak hitam yang menyembunyikan status runtime
- izin otomatis untuk melakukan tindakan yang tidak aman atau berhak istimewa
- produk cryptocurrency atau produk investasi apa pun

## Runtime Surfaces

| Surface | Gunakan ketika |
| --- | --- |
| `openminion run` | Anda menginginkan satu permintaan lokal yang terbatas |
| `openminion` | Anda menginginkan sesi fokus interaktif |
| `APIRuntime` dan `Agent` | Anda ingin menyematkan runtime dalam Python |
| Local HTTP API | Anda menginginkan proses lain untuk mengirim giliran atau permintaan alat |
| `openminiond` | Anda menginginkan eksekusi lokal yang didukung daemon |
| Operator CLIs | Anda memerlukan kontrol sesi fokus, memori, kebijakan, runtime, atau artefak |

Paket root mengekspor facade Python yang didukung: `APIRuntime`, `Agent`, `AgentOutputValidationError`, `AgentRunResult`, `Handoff`, `MemoryBundle`, `OpenMinionConfig`, `ProviderError`, `TurnTimeoutError`, `subagent`, `tool`, dan `__version__`. Lihat [`API_COMPATIBILITY.md`](API_COMPATIBILITY.md) sebelum bergantung pada internal paket yang lebih dalam.

`Agent.run_stream()` adalah API kenyamanan callback-progress sinkron.
Untuk streaming iterator bertipe, pembatalan, atau resolusi persetujuan yang disiarkan, gunakan `APIRuntime.submit_turn()` dan kontrak lanjutan yang diekspor dari `openminion.api`. Lihat [`examples/sdk/`](examples/sdk/) untuk kedua alur tersebut.

## Peta Repositori

```text
src/openminion/
  api/         Public Python and HTTP runtime entrypoints
  base/        Foundational contracts and shared primitives
  cli/         CLI entrypoints and terminal UX
  modules/     Feature and subsystem owners
  services/    Cross-owner runtime orchestration
  tools/       Tool host and tool families
docs/          Package-local public documentation
examples/      Runnable usage examples
scripts/       Validation and operator utilities
tests/         Package and integration proof
```

Untuk detail per pemilik, baca [`docs/source-tree-owner-map.md`](docs/source-tree-owner-map.md).

## Pengembangan

Sebelum berkontribusi, baca [CONTRIBUTING.md](CONTRIBUTING.md) dan [CODE_QUALITY.md](CODE_QUALITY.md).

```bash
make dev-install
make hooks-install
make lint
```

Gunakan pengujian terfokus selama iterasi. Jalankan `make lint` sebelum persetujuan fitur; simpan `make check` untuk penyapuan integrasi yang lebih luas secara sengaja.

## Dokumentasi dan Rilis

- [`docs/README.md`](docs/README.md): peta dokumentasi paket
- [`docs/runtime-surfaces.md`](docs/runtime-surfaces.md): runtime dan library yang didukung
- [`docs/system-operations.md`](docs/system-operations.md): operasi lokal dan diagnostik
- [`docs/security-scanning.md`](docs/security-scanning.md): audit lokal terbatas Semgrep dan Trivy
- [`docs/testing-and-validation.md`](docs/testing-and-validation.md): inventaris validasi
- [`docs/certification-readiness-matrix.md`](docs/certification-readiness-matrix.md): cakupan bukti saat ini
- [`API_COMPATIBILITY.md`](API_COMPATIBILITY.md): kompatibilitas impor publik dan perintah
- [`RELEASING.md`](RELEASING.md): pemeriksaan rilis dan alur publikasi

Biaya model-provider, layanan hosted, dan infrastruktur pihak ketiga terpisah dari runtime berlisensi Apache-2.0. Tinjau ketentuan dan biaya provider sebelum mengaktifkan backend berbayar.

## Lisensi dan Batasan Penggunaan Merek

- Lisensi kode sumber: Apache-2.0
- Lisensi merek/merk dagang: tidak ada

Lisensi ini memberikan hak untuk menggunakan, memodifikasi, dan mendistribusikan ulang kode. Lisensi ini tidak memberikan hak untuk menyajikan fork, clone, token, website, atau akun sosial sebagai proyek resmi OpenMinion atau mengimplikasikan afiliasi atau dukungan.
