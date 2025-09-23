from typing import Any
from lxml.html import HtmlElement


# def find(doc: HtmlElement, tag: str, value: str, property: str = 'data-test-selector', **kwargs) -> str:
#     try:
#         element = doc.find(f'.//{tag}[@{property}="{value}"]')
#         if 'attrib' in kwargs:
#             return element.attrib[kwargs['attrib']]
#         return element.text_content().strip()
#     except AttributeError:
#         return ''
#
#
# def find_element(
#     doc: HtmlElement,
#     tag: str,
#     value: str,
#     property: str = 'data-test-selector',
#     **kwargs,
# ) -> str | HtmlElement | None:
#     try:
#         element = doc.find(f'.//{tag}[@{property}="{value}"]')
#         if 'attrib' in kwargs:
#             return element.attrib[kwargs['attrib']]
#         return element
#     except AttributeError:
#         return ''
#
#
# def xpath(
#     doc: HtmlElement, tag: str, value: str, property: str = 'data-test-selector', fn: str = ''
# ) -> list[Any]:
#     elements = doc.xpath(f'.//{tag}[@{property}="{value}"]{fn}')
#     if fn == '/text()':
#         elements = [element.strip() for element in elements]
#     return elements
#


def find(
    doc: HtmlElement,
    tag: str,
    value: str,
    property: str = 'data-test-selector',
    attrib: str | None = None,
) -> str:
    element = doc.find(f'.//{tag}[@{property}="{value}"]')
    if element is None:
        return ''
    if attrib:
        return element.attrib.get(attrib, '')
    return (element.text_content() or '').strip()


def find_element(
    doc: HtmlElement,
    tag: str,
    value: str,
    property: str = 'data-test-selector',
) -> HtmlElement | None:
    return doc.find(f'.//{tag}[@{property}="{value}"]')


def xpath(
    doc: HtmlElement,
    tag: str,
    value: str,
    property: str = 'data-test-selector',
    fn: str = '',
) -> list[Any]:
    elements = doc.xpath(f'.//{tag}[@{property}="{value}"]{fn}')
    if fn == '/text()':
        return [e.strip() for e in elements if isinstance(e, str)]
    return elements
