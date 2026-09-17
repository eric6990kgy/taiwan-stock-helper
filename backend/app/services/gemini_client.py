"""Gemini API wrapper for the multi-agent research team (Phase 12,
confirmed with the user 2026-09-17 -- Gemini over Claude). Same resilience
shape as app.services.line_notifier.LineNotifier: `enabled` reflects
whether a key is configured, a no-op/error is raised rather than silently
faked, and a dedicated exception type lets callers treat any failure as a
best-effort warning, never a crash.

Uses `client.models.generate_content` with `response_schema` for
structured output -- NOT the `client.interactions` surface, which is a
different, session/agent-oriented API (persisted Agents, webhooks,
triggers) that doesn't fit a stateless one-shot call per role. Verified
directly against the installed google-genai SDK (2.24.0), not recalled
from training.
"""

import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.config import GEMINI_API_KEY

DEFAULT_MODEL = "gemini-3.8-flash"

# 429 (quota/rate limit) and 503 (transient overload) are worth a short
# retry -- discovered live 2026-09-17: the free tier caps gemini-3.8-flash
# at 5 requests/minute, and a scan with several changed tickers x 3 roles
# blows straight through that in one burst. Anything else (400 malformed
# request, 401/403 auth) retrying would just fail again identically.
RETRYABLE_CODES = (429, 503)
RETRY_BACKOFF_SECONDS = (5, 15)


class GeminiAnalysisError(Exception):
    """A Gemini call failed (auth, quota, malformed response, ...) or the
    client is disabled -- callers catch this and skip that one role, same
    best-effort convention as LineNotifyError."""


class GeminiClient:
    def __init__(self, api_key: str | None = None):
        self._api_key = GEMINI_API_KEY if api_key is None else api_key
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def structured_call(
        self, *, system_instruction: str, input: str, schema: type[BaseModel], model: str = DEFAULT_MODEL
    ) -> BaseModel:
        """Raises GeminiAnalysisError if disabled, if the API call fails,
        or if the response can't be parsed into `schema` -- never returns
        a fabricated/default instance."""
        if self._client is None:
            raise GeminiAnalysisError("Gemini not configured (GEMINI_API_KEY unset).")

        response = None
        for backoff in (*RETRY_BACKOFF_SECONDS, None):
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=input,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
                break
            except genai_errors.APIError as exc:
                is_last_attempt = backoff is None
                if getattr(exc, "code", None) not in RETRYABLE_CODES or is_last_attempt:
                    raise GeminiAnalysisError(f"Gemini call failed: {exc}") from exc
                time.sleep(backoff)

        if response.parsed is not None:
            return response.parsed
        if not response.text:
            raise GeminiAnalysisError("Gemini returned an empty response.")
        try:
            return schema.model_validate_json(response.text)
        except Exception as exc:  # pydantic ValidationError / json errors
            raise GeminiAnalysisError(f"Gemini response didn't match the expected schema: {exc}") from exc
