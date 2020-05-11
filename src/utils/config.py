import os

try:
    import configuration
except ImportError:
    configuration = {}


def get_attribute(attribute_name, fail_if_not_found=True, accepts=None):
    """Get credentials attribute required in the project. First
    check the environment variables, then the configuration file
    """
    if os.environ.get(attribute_name) is None:
        print(f'{attribute_name} is not specified as an environment variable')
        if hasattr(configuration, attribute_name):
            print(f'Retrieving {attribute_name} from configuration file')
            return getattr(configuration, attribute_name)
        else:
            if fail_if_not_found:
                raise AttributeError(f'Cannot get {attribute_name} from environment or configuration file')
            else:
                print(f'Cannot get {attribute_name} from the environment or '
                      f'configuration file, returning None')
                return None
    else:
        attribute = os.environ.get(attribute_name)
        if attribute.lower() == 'true':
            attribute = True
        elif attribute.lower() == 'false':
            attribute = False
        if accepts is not None:
            if attribute in accepts:
                return attribute
            else:
                raise Exception(f'{attribute_name} only accepts the following: {str(accepts)}')
        else:
            return attribute
