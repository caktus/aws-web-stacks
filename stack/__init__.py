import os

from . import assets  # noqa: F401
from . import cache  # noqa: F401
from . import database  # noqa: F401
from . import logs  # noqa: F401
from . import vpc  # noqa: F401
from . import template

if os.environ.get('USE_ECS') == 'on':
    from . import cluster  # noqa: F401
elif os.environ.get('USE_GOVCLOUD') == 'on':
    from . import instances  # noqa: F401
else:
    from . import eb  # noqa: F401

print(template.template.to_json())
