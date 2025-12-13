import curl_cffi
import time


class Persistent406Error(Exception):
    pass


def get_request(
    url: str,
    retries: int = 21,
    delay: float = 1.0,
    timeout: int = 10,
) -> tuple[int, curl_cffi.Response]:
    for attempt in range(retries):
        response = curl_cffi.get(url, impersonate='chrome', allow_redirects=False, timeout=timeout)

        if response.status_code != 406:
            return response.status_code, response

        if attempt < retries:
            time.sleep(delay)

    raise Persistent406Error(f'received 406 for {retries} attempts on {url}')
