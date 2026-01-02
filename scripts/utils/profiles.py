import sys

from typing import Any, NoReturn
from orjson import loads
from lxml import html

from utils.network import NetworkClient


def get_profiles(client: NetworkClient, urls: list[str]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}

    for url in urls:
        profile = _extract_profile_from_url(client, url)
        split = url.split('/')

        profile['profile']['profile'] = f'{split[5]}/{split[6]}'
        profile['profile']['quotes'] = profile['quotes']
        profile['profile']['stable_quotes'] = profile['stableTourQuotes']
        profiles[profile['profile']['horseUid']] = profile['profile']

    return profiles


def _extract_profile_from_url(client: NetworkClient, url: str) -> dict[str, Any] | NoReturn:
    status, response = client.get(url)

    if status != 200:
        _exit_with_error(f'Failed to get profiles.\nStatus: {status}, URL: {url}')

    doc = html.fromstring(response.content)

    try:
        script_elements = doc.xpath('//body/script')
        if not script_elements:
            raise IndexError('No script elements found')

        json_str = _extract_json_string(script_elements[0].text)
        profile_data = loads(json_str)

        return profile_data

    except IndexError:
        _exit_with_error(f'Failed to get profiles.\nNo script element found at URL: {url}')
    except ValueError:
        _exit_with_error(f'Failed to get profiles.\nInvalid JSON at URL: {url}')
    except KeyError:
        _exit_with_error(f'Failed to get profiles.\nNo "profile" key found at URL: {url}')


def _extract_json_string(script_text: str) -> str:
    return script_text.split('window.PRELOADED_STATE =')[1].split('\n')[0].strip().strip(';')


def _exit_with_error(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(1)
