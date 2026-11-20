# Kapabilitas Provider

Profil provider OpenMinion menyatakan fitur-fitur yang mereka dukung. Permintaan runtime dapat membutuhkan fitur-fitur tersebut sebelum panggilan provider dimulai, yang menjaga perutean tetap deterministik dan menghindari pengujian provider dengan permintaan yang tidak didukung.

## Fakta Profil

Sebuah profil dapat menyatakan kapabilitas transport berikut:

- `supports_json`
- `supports_tools`
- `supports_vision`
- `supports_streaming`
- `supports_prompt_caching`

Matriks kapabilitas runtime juga melaporkan apakah profil menyertakan metadata biaya dan referensi autentikasi. Ini adalah fakta konfigurasi, bukan klaim bahwa kredensial valid atau bahwa endpoint saat ini dapat dijangkau.

```yaml
profiles:
  - id: primary
    provider: openai-compatible
    model: example-model
    auth_ref: env:PROVIDER_API_KEY
    capabilities:
      supports_json: true
      supports_tools: true
      supports_streaming: true
    cost_hint:
      input_per_1k: 0.001
      output_per_1k: 0.002
```

## Persyaratan Permintaan

`RuntimeLLMRequest.required_capabilities` menerima nama kapabilitas secara eksplisit:

```python
from openminion.modules.llm.orchestration import RuntimeLLMRequest

request = RuntimeLLMRequest(
    purpose="act",
    required_capabilities=["tools", "streaming"],
)
```

Permintaan output terstruktur secara otomatis membutuhkan `json`. Profil yang tidak memiliki kapabilitas yang diperlukan akan ditolak dengan `INVALID_ARGUMENT` sebelum transport provider-nya dipanggil. Perutean agent kemudian dapat menggunakan profil fallback yang dikonfigurasikan tanpa terlebih dahulu mengirim permintaan yang tidak kompatibel ke profil utama.

Runtime tidak melakukan inferensi kapabilitas dari nama provider, nama model, respons, atau panggilan yang gagal. Perbarui konfigurasi profil saat fakta provider berubah.

## Memeriksa Matriks

Pemanggil library dapat membangun matriks yang dapat direproduksi dari katalog yang dimuat:

```python
from openminion.modules.llm.orchestration import provider_capability_matrix

for row in provider_capability_matrix(catalog):
    print(row.as_dict())
```

Matriks ini menggambarkan fakta konfigurasi. Sertifikasi provider tetap merupakan latihan terpisah yang membuktikan akses endpoint dan perilaku dengan bukti langsung.

## Penggunaan Kembali Koneksi HTTP

OpenMinion menggunakan kembali koneksi HTTP provider secara default untuk OpenAI, OpenRouter, Anthropic, Cerebras, Groq, Ollama, dan Cortensor. Penggunaan kembali dimiliki oleh setiap instansi provider dan tidak mengubah perutean, pengulangan, prompt, atau parsing respons.

Tetapkan `http_connection_reuse_enabled: false` pada sebuah provider untuk mengembalikan provider tersebut ke satu koneksi HTTP per permintaan:

```yaml
providers:
  openrouter:
    http_connection_reuse_enabled: false
```

Klien provider akan ditutup saat runtime agent-nya dikeluarkan atau runtime API dimatikan.
