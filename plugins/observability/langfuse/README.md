# Langfuse Observability Plugin

This plugin ships bundled with Atlas but is **opt-in** — it only loads when
you explicitly enable it.

## Enable

Pick one:

```bash
# Interactive: walks you through credentials + SDK install + enable
atlas tools  # → Langfuse Observability

# Manual
pip install langfuse
atlas plugins enable observability/langfuse
```

## Required credentials

Set these in `~/.atlas/.env` (or via `atlas tools`):

```bash
ATLAS_LANGFUSE_PUBLIC_KEY=pk-lf-...
ATLAS_LANGFUSE_SECRET_KEY=sk-lf-...
ATLAS_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

Without the SDK or credentials the hooks no-op silently — the plugin fails
open.

## Verify

```bash
atlas plugins list                 # observability/langfuse should show "enabled"
atlas chat -q "hello"              # then check Langfuse for a "Atlas turn" trace
```

## Optional tuning

```bash
ATLAS_LANGFUSE_ENV=production       # environment tag
ATLAS_LANGFUSE_RELEASE=v1.0.0       # release tag
ATLAS_LANGFUSE_SAMPLE_RATE=0.5      # sample 50% of traces
ATLAS_LANGFUSE_MAX_CHARS=12000      # max chars per field (default: 12000)
ATLAS_LANGFUSE_DEBUG=true           # verbose plugin logging
```

## Disable

```bash
atlas plugins disable observability/langfuse
```
