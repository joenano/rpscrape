from lxml.html import HtmlElement


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
