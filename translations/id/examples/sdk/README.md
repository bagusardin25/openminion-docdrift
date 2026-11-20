# Contoh SDK Python

Program-program ini adalah referensi yang dapat disalin untuk API Python publik OpenMinion.
Mereka mengharapkan provider model yang telah dikonfigurasi kecuali contoh menyatakan sebaliknya.

Pasang paket yang sedang digunakan dan konfigurasikan provider terlebih dahulu:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install openminion
openminion setup --no-chat
openminion doctor --check-turn
```

Untuk melihat pratinjau sumber, kloning repositori dan jalankan `python -m pip install -e .`
dari hasil checkout itu daripada menggunakan commit lama yang ditentukan.

Jalankan contoh dari akar repositori:

```bash
python examples/sdk/tool_agent.py
```

## Peta contoh

| Berkas | Gunakan untuk |
| --- | --- |
| `tool_agent.py` | Alat Python yang dihias dan panggilan alat pertama yang dipaksa |
| `structured_output.py` | Output yang tervalidasi menggunakan Pydantic |
| `sessions.py` | ID sesi yang dibagikan dan terisolasi |
| `streaming_progress.py` | Jalankan sinkron dengan callback kemajuan |
| `submitted_stream.py` | Streaming iterator bertipe dan resolusi persetujuan |
| `delegation.py` | Penyerahan rekan (dengan jeda persetujuan) dan subagen terbatas |
| `application_runtime.py` | Siklus hidup `APIRuntime` yang dimiliki aplikasi |
| `provider_switching.py` | Memilih agen yang dikonfigurasi tanpa mengubah kode |
| `error_handling.py` | Kegagalan provider, tenggat waktu giliran, dan validasi output |

Gunakan `python <file> --help` untuk melihat opsi setiap program. Perintah penyiapan dan penggantian provider ada di `examples/providers/README.md`.

Contoh output terstruktur meminta provider untuk JSON yang tepat. OpenMinion juga menjaga perilaku `0.1.x` terbatas yang menerima satu objek JSON yang valid secara skema yang dibungkus dalam prosa provider.

## Persetujuan penyerahan

`delegation.py --mode handoff` mengekspos researcher sebagai alat `transfer_to_researcher`. Sebuah `Handoff` menyatakan tidak ada metadata risiko, sehingga kebijakan menempatkannya pada default ketidakpastian kebalikan dan menjeda untuk konfirmasi sebelum target dijalankan.

- Tanpa `approval_callback`, jalannya berakhir pada jeda itu: `result.text` adalah prompt operator ("Policy confirmation required. …"), bukan jawaban researcher, dan `result.metadata["respond_kind"]` adalah `policy_confirmation_prompt`. Kode aplikasi yang menjaga Agent-nya tetap terbuka menjawabnya di thread yang menunggu dengan `agent.run("yes",
  thread_id=result.thread_id)`; sebuah `run()` biasa yang datang kemudian memulai thread baru dan tidak menjawabnya.
- Dengan `approval_callback`, callback memutuskan untuk panggilan itu sebelum target dijalankan: mengembalikan true mengizinkan panggilan tersebut; mengembalikan false mengakhiri giliran dengan "Confirmation denied. The action was not run."; callback yang melempar kesalahan menyebabkan jalannya gagal dengan error tersebut. Dalam kedua kasus kegagalan itu, researcher tidak dijalankan.

Bendera `--approval` pada contoh menguji setiap jalur; skrip mencetak tampilan operator dan keluar:

```bash
python examples/sdk/delegation.py --mode handoff
python examples/sdk/delegation.py --mode handoff --approval allow_once
python examples/sdk/delegation.py --mode handoff --approval deny
```

Callback contoh hanya memutuskan untuk `transfer_to_researcher`: konfirmasi untuk alat lain ditolak, dan izinnya digunakan sekali.
