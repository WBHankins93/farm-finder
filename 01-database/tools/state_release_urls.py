"""Shared public URL classification for every state collector and validator."""

from __future__ import annotations

import re
from urllib.parse import urlparse


SOCIAL_HOSTS = {
    "facebook": {"facebook.com"},
    "instagram": {"instagram.com"},
    "tiktok": {"tiktok.com"},
}
NON_WEBSITE_HOSTS = {
    "twitter.com", "x.com", "pinterest.com", "mapquest.com", "goo.gl", "g.page",
    "csaware.com", "imapbuilder.com", "gstatic.com", "googleapis.com",
}


def normalized_url(value: str) -> str:
    text = str(value or "").strip().strip(".,;)")
    if not text or re.search(r"\s", text) or "." not in text:
        return ""
    if not re.match(r"^https?://", text, flags=re.I):
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or not host or "." not in host or parsed.username:
        return ""
    return text


def host_matches(host: str, domains: set[str]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def website_rejection_reason(value: str) -> str:
    url = normalized_url(value)
    if not url:
        return "malformed"
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    if any(host_matches(host, domains) for domains in SOCIAL_HOSTS.values()):
        return "social"
    if host.startswith("lh-images.") or host_matches(host, NON_WEBSITE_HOSTS):
        return "shared_or_nonwebsite_host"
    if host in {"google.com", "www.google.com", "maps.google.com"} or parsed.path.startswith("/maps"):
        return "map_or_search"
    return ""


def is_valid_website(value: str) -> bool:
    return bool(value) and not website_rejection_reason(value)


def classify_public_urls(website: str, facebook: str, instagram: str, tiktok: str
                         ) -> tuple[str, str, str, str]:
    values = {
        "facebook": normalized_url(facebook),
        "instagram": normalized_url(instagram),
        "tiktok": normalized_url(tiktok),
    }
    candidate = normalized_url(website)
    if candidate:
        host = (urlparse(candidate).hostname or "").casefold()
        moved = False
        for kind, domains in SOCIAL_HOSTS.items():
            if host_matches(host, domains):
                values[kind] = values[kind] or candidate
                moved = True
                break
        if moved or website_rejection_reason(candidate):
            candidate = ""
    return candidate, values["facebook"], values["instagram"], values["tiktok"]
