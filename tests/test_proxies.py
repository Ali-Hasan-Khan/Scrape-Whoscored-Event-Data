"""Tests for the proxy pool and proxy-aware transport (all offline)."""

from __future__ import annotations

import pytest

from whoscored.exceptions import ProxyError
from whoscored.proxies import ProxyRotator, normalize_proxy
from whoscored.transports import HttpTransport


def test_normalize_proxy_forms():
    assert normalize_proxy("123.4.5.6:8080") == "http://123.4.5.6:8080"
    assert normalize_proxy("  http://123.4.5.6:8080  ") == "http://123.4.5.6:8080"
    assert normalize_proxy("socks5://1.2.3.4:1080") == "socks5://1.2.3.4:1080"
    with pytest.raises(ValueError):
        normalize_proxy("   ")


def test_rotator_uses_provided_proxies_without_validation():
    pool = ProxyRotator(proxies=["a:1", "b:2"], validate=False, seed=1)
    assert len(pool) == 2
    seen = [pool.next() for _ in range(4)]
    assert set(seen) == {"http://a:1", "http://b:2"}
    # rotation keeps alternating between the two
    assert seen[0] != seen[1] == seen[2] != seen[3]


def test_rotator_validates_and_filters(monkeypatch):
    import whoscored.proxies as proxies_module

    def fake_validate(proxy, url, timeout):
        return proxy == "http://good:1"

    monkeypatch.setattr(proxies_module, "_validate_proxy", fake_validate)
    pool = ProxyRotator(proxies=["good:1", "bad:2"], validate=True, seed=2)
    assert len(pool) == 1
    assert pool.next() == "http://good:1"


def test_rotator_empty_pool_raises():
    pool = ProxyRotator(validate=False)
    with pytest.raises(ProxyError):
        pool.next()


def test_rotator_request_proxies_shape():
    pool = ProxyRotator(proxies=["1.2.3.4:9999"], validate=False)
    assert pool.request_proxies() == {
        "http": "http://1.2.3.4:9999",
        "https": "http://1.2.3.4:9999",
    }


def test_rotator_refresh_parses_plain_text_sources(monkeypatch):
    import requests

    class FakeResponse:
        text = "1.1.1.1:80\n2.2.2.2:8080\n\n3.3.3.3:3128\n"
        status_code = 200

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        requests, "get", lambda url, timeout=None: FakeResponse()
    )
    pool = ProxyRotator(fetch_sources=True, sources={"x": "https://example.invalid/list"}, validate=False)
    assert len(pool) == 3
    assert "http://2.2.2.2:8080" in {pool.next() for _ in range(3)}


def test_http_transport_sends_static_proxy():
    transport = HttpTransport(request_delay=0.0, jitter=0.0, proxy="9.9.9.9:8080")
    captured: dict = {}

    def fake_get(url, timeout=None, proxies=None):
        captured["proxies"] = proxies
        response = type("R", (), {"status_code": 200, "text": "<html/>", "url": url})()
        return response

    transport.session.get = fake_get
    assert transport.get("https://x/1") == "<html/>"
    assert captured["proxies"] == {"http": "http://9.9.9.9:8080", "https": "http://9.9.9.9:8080"}
    transport.close()


def test_http_transport_rotates_proxy_per_request():
    pool = ProxyRotator(proxies=["a:1", "b:2"], validate=False, seed=3)
    transport = HttpTransport(request_delay=0.0, jitter=0.0, proxy_pool=pool)
    seen = []

    def fake_get(url, timeout=None, proxies=None):
        seen.append(proxies["https"])
        response = type("R", (), {"status_code": 200, "text": "<html/>", "url": url})()
        return response

    transport.session.get = fake_get
    transport.get("https://x/1")
    transport.get("https://x/2")
    assert seen[0] != seen[1]
    assert set(seen) == {"http://a:1", "http://b:2"}
    transport.close()


def test_http_transport_rotates_on_failure():
    pool = ProxyRotator(proxies=["a:1", "b:2"], validate=False, seed=4)
    transport = HttpTransport(request_delay=0.0, jitter=0.0, retries=2, proxy_pool=pool)
    seen = []

    def fake_get(url, timeout=None, proxies=None):
        seen.append(proxies["https"])
        response = type("R", (), {"status_code": 500, "text": "", "url": url})()
        return response

    transport.session.get = fake_get
    with pytest.raises(Exception):
        transport.get("https://x/1")
    # failure triggered a retry, so more than one proxy was used
    assert len(seen) >= 2
    transport.close()


def test_client_free_proxies_flag(monkeypatch):
    import whoscored.proxies as proxies_module

    class FakeRotator:
        def __init__(self, fetch_sources=False):
            self.fetch_sources = fetch_sources

    monkeypatch.setattr(proxies_module, "ProxyRotator", FakeRotator)
    from whoscored import WhoscoredClient

    with WhoscoredClient(free_proxies=True) as client:
        assert isinstance(client.transport.proxy_pool, FakeRotator)
