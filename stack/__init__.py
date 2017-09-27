import os

from . import assets  # noqa: F401
from . import cache  # noqa: F401
from . import database  # noqa: F401
from . import logs  # noqa: F401
from . import vpc  # noqa: F401
from . import template

if os.environ.get('USE_GOVCLOUD') != 'on':
    # make sure this isn't added to the template for GovCloud, as it's not
    # supported in this region
    from . import search  # noqa: F401

if os.environ.get('USE_ECS') == 'on':
    from . import repository  # noqa: F401
    from . import cluster  # noqa: F401
elif os.environ.get('USE_EB') == 'on':
    from . import repository  # noqa: F401
    from . import eb  # noqa: F401
elif os.environ.get('USE_DOKKU') == 'on':
    from . import dokku  # noqa: F401
else:  # USE_GOVCLOUD and USE_EC2 both provide EC2 instances
    from . import instances  # noqa: F401

print(template.template.to_json())
