import os
os.environ.setdefault('FARM_KEYS_SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'habib_system.settings')
from habib_system.settings import *  # noqa: F401,F403

import uuid
_test_db_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_test_cloudstorage_%s.sqlite3' % uuid.uuid4().hex[:12])
if 'default' in DATABASES and DATABASES['default'].get('ENGINE', '').endswith('.sqlite3'):
    DATABASES['default']['NAME'] = _test_db_name
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _test_db_name,
        }
    }
