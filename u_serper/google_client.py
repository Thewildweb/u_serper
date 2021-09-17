from typing import Optional
import random
from http.cookies import BaseCookie
from urllib.parse import quote_plus
import string
import logging

import aiohttp
from selectolax.parser import HTMLParser
from tenacity import retry, stop_after_attempt

from .models import SEResult, SERP, OrganicResult
from .exceptions import BlockedError


class GoogleScraper:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    base_url = "https://www.google.com/search?q="
    google_detect_strings = [
        "Onze systemen hebben ongebruikelijk verkeer van uw computernetwerk vastgesteld."
    ]

    def __init__(self, proxy: str = None):
        self._proxy = proxy
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent}, trust_env=True
        )
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._session.close()

    async def clean_cookie_jar(self):
        """This empties the cookie jar and places a CONSENT cookie"""

        self._session._cookie_jar.clear()
        # create consent cookie
        random_str = "".join([random.choice(string.ascii_lowercase) for _ in range(3)])
        cookie = BaseCookie({"CONSENT": f"YES+{random_str}"})
        cookie["CONSENT"]["path"] = "/"
        cookie["CONSENT"]["domain"] = ".google.com"
        cookie["CONSENT"]["expires"] = "Mon, 12 May 2031 15:15:02 GMT"
        cookie["CONSENT"]["secure"] = True
        # add consent cookie to jar
        self._session._cookie_jar.update_cookies(cookie)

    @retry(reraise=True, stop=stop_after_attempt(5))
    async def get_page(self, url, lang: Optional[str] = "nl-NL"):
        """Gets a page from Google"""
        await self.clean_cookie_jar()

        resp = await self._session.get(
            url,
            proxy=self._proxy,
            raise_for_status=True,
            headers={"Accept-Language": lang},
        )
        html = await resp.text()

        if any([string in html for string in self.google_detect_strings]):
            raise BlockedError("Google detected a bot")

        return html

    async def run_query(
        self,
        query: str,
        nr_pages: Optional[int] = 1,
        uule: Optional[str] = None,
        lang: Optional[str] = "nl-NL",
    ) -> SEResult:
        url = self.base_url + quote_plus(query)
        if uule:
            url += f"&uule={uule}"

        results = []
        for i in range(nr_pages):
            if i > 0:
                url += f"&start={i * 10}"

            try:
                html = await self.get_page(url, lang)
            except Exception as e:
                logging.warning(f"Error getting page with url: {url} Error: {e}")
                break

            try:
                serp = self.parse_serp(html, url)
            except Exception as e:
                logging.warning(f"Error parsing response for url: {url}")
                break
            else:
                results.append(serp)

        return SEResult(
            query=query,
            nr_pages=len(results),
            pages=results,
        )

    def parse_serp(self, html, url) -> SERP:
        tree = HTMLParser(html)
        data = {}
        data["organic_results"] = self.parse_organic(tree)

        return SERP.parse_obj(data)

    def parse_organic(self, tree: HTMLParser) -> OrganicResult:
        organic_results = []

        for count, item in enumerate(tree.css("div#search div.g"), start=1):
            res_dict = {"position": count}
            if title_elem := item.css_first("h3"):
                res_dict["title"] = title_elem.text(separator=" ").strip()
            else:
                print(item.html)
                continue
            res_dict["displayed_link"] = (
                item.css_first("cite").text(separator=" ").strip()
            )
            res_dict["link"] = item.css_first("a[href]").attributes.get("href")
            res_dict["snippet"] = (
                item.css_first("div.IsZvec").text(separator=" ").strip()
            )
            organic_results.append(res_dict)

        items = [OrganicResult.parse_obj(item) for item in organic_results]
        return items
