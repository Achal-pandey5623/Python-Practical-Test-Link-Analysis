import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import Settings


class WebsiteFetchError(Exception):
    """A website could not be safely fetched or did not return usable HTML."""


def _is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
        return address.is_global
    except ValueError:
        return False


async def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WebsiteFetchError("Only valid HTTP or HTTPS website URLs are accepted.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise WebsiteFetchError("Private or local network addresses cannot be analyzed.")
    try:
        results = await asyncio.get_running_loop().getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        raise WebsiteFetchError("The website hostname could not be resolved.") from None
    addresses = {record[4][0] for record in results}
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise WebsiteFetchError("Private or local network addresses cannot be analyzed.")


def extract_page(html: str, url: str, max_chars: int) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "svg", "iframe", "form", "nav", "footer"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""
    headings = [tag.get_text(" ", strip=True) for tag in soup.find_all(["h1", "h2", "h3"]) if tag.get_text(strip=True)]
    canonical = soup.find("link", rel="canonical")
    text = " ".join(soup.stripped_strings)
    return {
        "url": url,
        "title": title[:500],
        "meta_description": description[:1000],
        "headings": headings[:50],
        "content": text[:max_chars],
    }


async def fetch_website(url: str, settings: Settings) -> dict:
    current = url
    headers = {"User-Agent": "LinkAnalysisBot/1.0 (+website content analysis)"}
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, headers=headers) as client:
        for _ in range(6):
            await validate_public_url(current)
            try:
                async with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise WebsiteFetchError("The website redirected without a destination.")
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise WebsiteFetchError(f"The website returned HTTP {response.status_code}.")
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        raise WebsiteFetchError("The URL did not return an HTML page.")
                    chunks = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > settings.max_page_bytes:
                            raise WebsiteFetchError("The website page is larger than the allowed limit.")
                        chunks.append(chunk)
                    html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                    page = extract_page(html, str(response.url), settings.max_content_chars)
                    if not page["content"]:
                        raise WebsiteFetchError("No readable text content was found on the page.")
                    return page
            except WebsiteFetchError:
                raise
            except (httpx.HTTPError, UnicodeError) as exc:
                raise WebsiteFetchError(f"Could not access the website: {type(exc).__name__}.") from None
        raise WebsiteFetchError("The website redirected too many times.")
