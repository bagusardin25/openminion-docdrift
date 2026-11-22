# The section this sync wrote

`docs/provider-capabilities.md`, section `http-connection-reuse`, translated by `oss-20b` on Cortensor Portal.

## English source

## HTTP connection reuse

OpenMinion reuses provider HTTP connections by default for OpenAI, OpenRouter,
Anthropic, Cerebras, Groq, Ollama, and Cortensor. Reuse is owned by each provider
instance and does not change routing, retries, prompts, or response parsing.

Set `http_connection_reuse_enabled: false` on a provider to return that provider
to one HTTP connection per request:

```yaml
providers:
  openrouter:
    http_connection_reuse_enabled: false
```

The provider client is closed when its agent runtime is evicted or the API
runtime shuts down. Reuse never shares a connection between two providers.

## Bahasa Indonesia (as written, unedited)

## Penggunaan Koneksi HTTP

OpenMinion menggunakan kembali koneksi HTTP provider secara default untuk OpenAI, OpenRouter,
Anthropic, Cerebras, Groq, Ollama, dan Cortensor. Penggunaan kembali dimiliki oleh setiap instansi provider dan tidak mengubah perutean, retries, prompts, atau parsing respons.

Set `http_connection_reuse_enabled: false` pada provider untuk mengembalikan provider tersebut ke satu koneksi HTTP per permintaan:

```yaml
providers:
  openrouter:
    http_connection_reuse_enabled: false
```

Klien provider ditutup ketika runtime agent-nya dikeluarkan atau runtime API dimatikan. Penggunaan kembali tidak pernah berbagi koneksi antara dua provider.
