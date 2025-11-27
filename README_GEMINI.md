Gemini integration — Quick notes

Environment variables:

- GEMINI_API_KEY: the API key for Google Generative Language (or other configured Gemini endpoint). If not set, the bot will fallback and not call the model.
- GEMINI_MODEL: optional (default: `text-bison-001`) — the model name to use.

Usage:

- GEMINI_BEARER_TOKEN: optional, if you prefer to pass a `Bearer` OAuth token rather than an API key. If set, this header will be used. This is recommended for production (service account tokens) and for premium models.
- GEMINI_BEARER_TOKEN: optional, if you prefer to pass a `Bearer` OAuth token rather than an API key. If set, this header will be used. This is recommended for production (service account tokens) and for premium models.
- Note: If your API key is invalid (typo, pasted extra text), requests will fail and the bot will return your submitted text unchanged. Use `/settings` to run a diagnostic test and check logs for details.

1. Add your API key to `.env`: `GEMINI_API_KEY=...` and optionally `GEMINI_MODEL=text-bison-001`.
2. Start the bot and use `/post` to compose a text. The bot will use the configured model to refine the text according to your `/preference` settings.

Notes:

- The `src/lib/gemini.ts` wrapper is a basic example. You may need to fine-tune request payload depending on the exact Gemini endpoint and model you use.
- Ensure your project has the necessary Node runtime and dependencies (Node 18+ for built-in fetch is recommended) or install a fetch polyfill (e.g., `node-fetch`).
- The wrapper includes a fallback that returns the original input if the API key is missing or if the service fails.
- The wrapper now supports either `GEMINI_API_KEY` (query parameter usage) or `GEMINI_BEARER_TOKEN` (Authorization: Bearer <token>). If you set a bearer token, it will be preferred over the API key.

Testing with the in-bot settings command:

- Start your bot with the env vars in place.
- Send `/settings` in a private chat with the bot to test the model and credentials; the bot will respond with sample output if the call succeeds.
- If `/settings` reports a missing credential or returns an error (HTTP 401/403/429), update `.env` accordingly. If the wrapper falls back (no token/key), the bot returns the original text unchanged and logs a warning message.

Security & auth:

- Generative Language API may accept API keys or OAuth Bearer tokens for authentication. Follow Google Cloud documentation if you need to use OAuth or service accounts.
- Do not commit API keys to source control. Use `.env` or a secrets manager.
