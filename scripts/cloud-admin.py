"""Load only this project's ignored cloud credentials, then run an admin command."""
import os
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
values = dotenv_values(root / '.env.cloud')
for name in ('DATABASE_URL', 'DATABASE_URL_UNPOOLED', 'BLOB_READ_WRITE_TOKEN', 'SH_STORAGE_SIGNING_KEY'):
    if values.get(name):
        os.environ[name] = values[name]
os.environ['SH_DATABASE_URL'] = values['DATABASE_URL']
os.environ['SH_STORAGE'] = 'blob'
sys.exit(subprocess.call([sys.executable, *sys.argv[1:]], cwd=root))
