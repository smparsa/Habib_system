import os
import uuid
from pathlib import Path

_PATH_HERE = Path(__file__).resolve().parent

os.environ.setdefault('FARM_KEYS_SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'habib_system.settings')

from habib_system.settings import *  # noqa: F401,F403

# Override database to use SQLite for testing
_test_db_name = str(_PATH_HERE / ('t_%s.sqlite3' % uuid.uuid4().hex[:12]))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _test_db_name,
    }
}



