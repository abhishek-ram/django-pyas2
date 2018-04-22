version = (1, 0, 0)

__version__ = '.'.join(map(str, version))

default_app_config = 'pyas2.apps.Pyas2Config'

__all__ = [
    'default_app_config',
    'version',
]