import sys

# Set the version
version = (1, 0, '0b2')
__version__ = '.'.join(map(str, version))

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

if is_py2:
    str_cls = unicode  # noqa
    byte_cls = str

elif is_py3:
    str_cls = str
    byte_cls = bytes

default_app_config = 'pyas2.apps.Pyas2Config'

__all__ = [
    'default_app_config',
    'version',
    'is_py2',
    'is_py3'
]
