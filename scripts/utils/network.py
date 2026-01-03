from collections.abc import Sequence
from curl_cffi import Session, Response, BrowserTypeLiteral
from random import choice
from time import sleep
from urllib.parse import quote


class Persistent406Error(Exception):
    pass


BROWSERS: Sequence[BrowserTypeLiteral] = (
    'edge',
    'chrome',
    'firefox',
    'safari',
)


COGNITO_POOL = '3fii107m4bmtggnm21pud2es21'


def construct_cookies(
    email: str | None, auth_state: str | None, access_token: str | None
) -> dict[str, str]:
    if email is None or auth_state is None or access_token is None:
        return {}

    key = f'CognitoIdentityServiceProvider.{COGNITO_POOL}.{quote(email, safe="")}.accessToken'

    return {
        'auth_state': auth_state,
        key: access_token,
    }


class NetworkClient:
    def __init__(
        self,
        *,
        email: str | None = None,
        auth_state: str | None = None,
        access_token: str | None = None,
        timeout: int = 14,
    ) -> None:
        cookies = construct_cookies(email, auth_state, access_token)

        self.session: Session = Session(impersonate=choice(BROWSERS), cookies=cookies)
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
