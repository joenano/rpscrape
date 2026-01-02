from time import sleep
from random import choice
from collections.abc import Sequence
from curl_cffi import Session, Response, BrowserTypeLiteral


class Persistent406Error(Exception):
    pass


browsers: Sequence[BrowserTypeLiteral] = (
    'edge',
    'chrome',
    'firefox',
    'safari',
)


class NetworkClient:
    def __init__(
        self,
        timeout: int = 14,
    ) -> None:
        self.session: Session = Session(impersonate=choice(browsers))
        self.timeout: int = timeout

    def get(
        self,
        url: str,
        allow_redirects: bool = True,
        retries: int = 7,
        delay: float = 1.4,
    ) -> tuple[int, Response]:
        for attempt in range(1, retries):
            response = self.session.get(
                url,
                allow_redirects=allow_redirects,
                timeout=self.timeout,
            )

            if response.status_code != 406:
                return response.status_code, response

            if attempt < retries:
                sleep(delay)

        raise Persistent406Error(f'received 406 for {retries} attempts on {url}')
