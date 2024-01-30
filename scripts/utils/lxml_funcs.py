def find(doc, tag, value, property='data-test-selector', **kwargs):
    try:
        element = doc.find(f'.//{tag}[@{property}="{value}"]')
        if 'attrib' in kwargs:
            return element.attrib[kwargs['attrib']]
        return element.text_content().strip()
    except AttributeError:
        return ''


def find_element(doc, tag, value, property='data-test-selector', **kwargs):
    try:
        element = doc.find(f'.//{tag}[@{property}="{value}"]')
        if 'attrib' in kwargs:
            return element.attrib[kwargs['attrib']]
        return element
    except AttributeError:
        return ''



def xpath(doc, tag, value, property='data-test-selector', fn=''):
    elements = doc.xpath(f'.//{tag}[@{property}="{value}"]{fn}')
    if fn == '/text()':
        elements = [element.strip() for element in elements]
    return elements
