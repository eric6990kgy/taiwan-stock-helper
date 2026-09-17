"""GeminiClient tests (Phase 12) -- mocks google.genai.Client entirely, no
real network calls, same "no live external calls in the test suite"
convention as FinMindProvider/LineNotifier's own tests. Verifies the
LineNotifier-style resilience shape: disabled when unconfigured, a
successful call parses into the requested schema, and any APIError is
translated into GeminiAnalysisError rather than propagating raw.
"""

from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.services.gemini_client import DEFAULT_MODEL, GeminiAnalysisError, GeminiClient


class DummySchema(BaseModel):
    call: str
    confidence: int
    rationale: str


class FakeModels:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.exception is not None:
            raise self.exception
        return self.response


class FakeGenaiClient:
    def __init__(self, models: FakeModels):
        self.models = models


@pytest.fixture()
def patch_genai_client(monkeypatch):
    def _patch(models: FakeModels):
        monkeypatch.setattr("app.services.gemini_client.genai.Client", lambda api_key: FakeGenaiClient(models))

    return _patch


def test_disabled_when_no_api_key_configured():
    # "" (not None) to force disabled regardless of whatever
    # GEMINI_API_KEY happens to be set to in the local .env -- passing
    # None falls back to that real config value, same convention as
    # LineNotifier(token=None).
    client = GeminiClient(api_key="")
    assert client.enabled is False


def test_structured_call_raises_when_disabled():
    client = GeminiClient(api_key="")
    with pytest.raises(GeminiAnalysisError):
        client.structured_call(system_instruction="sys", input="in", schema=DummySchema)


def test_successful_call_parses_response_into_schema(patch_genai_client):
    parsed = DummySchema(call="BULLISH", confidence=80, rationale="looks good")
    models = FakeModels(response=SimpleNamespace(parsed=parsed, text=parsed.model_dump_json()))
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    result = client.structured_call(system_instruction="sys", input="in", schema=DummySchema)

    assert result == parsed
    assert models.calls[0]["model"] == DEFAULT_MODEL


def test_falls_back_to_parsing_raw_text_when_parsed_is_none(patch_genai_client):
    """The SDK's `.parsed` convenience field can be None even on a 200
    response (e.g. a minor schema mismatch it couldn't auto-coerce) --
    structured_call must still recover by parsing `.text` itself rather
    than treating that as an unconditional failure."""
    raw = DummySchema(call="NEUTRAL", confidence=50, rationale="mixed signals").model_dump_json()
    models = FakeModels(response=SimpleNamespace(parsed=None, text=raw))
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    result = client.structured_call(system_instruction="sys", input="in", schema=DummySchema)

    assert result.call == "NEUTRAL"


def test_api_error_raises_gemini_analysis_error(patch_genai_client):
    error = genai_errors.ClientError(400, {"error": {"message": "bad request", "status": "INVALID_ARGUMENT"}})
    models = FakeModels(exception=error)
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    with pytest.raises(GeminiAnalysisError):
        client.structured_call(system_instruction="sys", input="in", schema=DummySchema)


def test_non_retryable_error_fails_immediately_without_retrying(patch_genai_client, monkeypatch):
    """A 400 (malformed request) would just fail identically again --
    retrying it is pure wasted latency, so structured_call must give up
    on the first attempt."""
    slept = []
    monkeypatch.setattr("app.services.gemini_client.time.sleep", lambda s: slept.append(s))
    error = genai_errors.ClientError(400, {"error": {"message": "bad request", "status": "INVALID_ARGUMENT"}})
    models = FakeModels(exception=error)
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    with pytest.raises(GeminiAnalysisError):
        client.structured_call(system_instruction="sys", input="in", schema=DummySchema)

    assert len(models.calls) == 1
    assert slept == []


class FlakyModels:
    """Fails with a retryable error a fixed number of times, then
    succeeds -- lets a test control exactly how many attempts it takes."""

    def __init__(self, fail_times: int, code: int = 429):
        self.fail_times = fail_times
        self.code = code
        self.calls = 0

    def generate_content(self, *, model, contents, config):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise genai_errors.ClientError(self.code, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
        parsed = DummySchema(call="BULLISH", confidence=60, rationale="recovered after retry")
        return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json())


def test_retries_a_rate_limited_call_and_eventually_succeeds(patch_genai_client, monkeypatch):
    slept = []
    monkeypatch.setattr("app.services.gemini_client.time.sleep", lambda s: slept.append(s))
    models = FlakyModels(fail_times=1, code=429)
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    result = client.structured_call(system_instruction="sys", input="in", schema=DummySchema)

    assert result.call == "BULLISH"
    assert models.calls == 2
    assert slept == [5]


def test_gives_up_after_exhausting_all_retries(patch_genai_client, monkeypatch):
    slept = []
    monkeypatch.setattr("app.services.gemini_client.time.sleep", lambda s: slept.append(s))
    models = FlakyModels(fail_times=99, code=503)  # never recovers
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    with pytest.raises(GeminiAnalysisError):
        client.structured_call(system_instruction="sys", input="in", schema=DummySchema)

    assert models.calls == 3  # initial attempt + 2 retries
    assert slept == [5, 15]


def test_malformed_response_raises_gemini_analysis_error_not_a_validation_error(patch_genai_client):
    models = FakeModels(response=SimpleNamespace(parsed=None, text="not json"))
    patch_genai_client(models)

    client = GeminiClient(api_key="fake-key")
    with pytest.raises(GeminiAnalysisError):
        client.structured_call(system_instruction="sys", input="in", schema=DummySchema)
