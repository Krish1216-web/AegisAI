# 11. AI Provider & Model Abstraction Layer

AegisAI integrates an abstract, provider-independent model execution layer allowing seamless failover routing and caching configurations.

## Architecture Pipeline

```text
Application Client (API Router)
       ↓
   AIService (Caching, Retries, Fallbacks)
       ↓
ProviderFactory (API Key Resolution & Mock fallbacks)
       ↓
AIProviderInterface (Contract interface)
       ↓
  ┌────┼──────────────┐
  ↓    ↓              ↓
OpenAI Gemini   Anthropic
```

---

## Configuration & Environment Settings

Add the following keys to your local `.env` configuration file:

```bash
# Default Execution
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o-mini

# Provider Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...
```

### Dev Mode Fallback
If `ENVIRONMENT=dev`, missing API keys will not crash startup. Instead, the `ProviderFactory` will automatically bind a local `MockProvider` that generates local token replies. This is ideal for CI runs and air-gapped development.

---

## REST Endpoint Examples

### 1. Chat Completion
* **Path**: `POST /api/v1/ai/chat`
* **Payload**:
```json
{
  "messages": [
    {"role": "user", "content": "How does gravity work?"}
  ],
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 1000,
  "bypass_cache": false
}
```

### 2. Stream Tokens
* **Path**: `POST /api/v1/ai/stream`
* **Response**: Server-Sent Events (SSE) stream (`data: [TOKEN]`).

---

## Testing Guidelines

Run tests using the following command:
```bash
python -m pytest backend/tests/unit/test_ai_provider.py
```
* **Mocks**: No real API keys are needed to run tests; mock integrations verify retry backoffs and failover scenarios automatically.
