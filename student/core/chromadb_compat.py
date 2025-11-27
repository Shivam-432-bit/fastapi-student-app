"""
Monkey patch for chromadb to work with Pydantic v2.
This must be imported before chromadb.
"""
import sys
import os
from pydantic_settings import BaseSettings

# Save our app's env vars before chromadb loads
_saved_env = {
    'MYSQL_USER': os.environ.get('MYSQL_USER'),
    'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD'),
    'MYSQL_HOST': os.environ.get('MYSQL_HOST'),
    'MYSQL_PORT': os.environ.get('MYSQL_PORT'),
    'MYSQL_DATABASE': os.environ.get('MYSQL_DATABASE'),
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'ALGORITHM': os.environ.get('ALGORITHM'),
    'ACCESS_TOKEN_EXPIRE_MINUTES': os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES'),
}

# Temporarily clear app env vars to prevent chromadb Settings validation errors
for key in _saved_env.keys():
    if key in os.environ:
        del os.environ[key]

# Set required chromadb env vars
os.environ['CHROMA_SERVER_HOST'] = 'localhost'
os.environ['CHROMA_SERVER_HTTP_PORT'] = '8000'
os.environ['CHROMA_SERVER_GRPC_PORT'] = '50051'
os.environ['CLICKHOUSE_HOST'] = 'localhost'
os.environ['CLICKHOUSE_PORT'] = '8123'

# Inject BaseSettings into pydantic module for chromadb compatibility
if 'pydantic' in sys.modules:
    sys.modules['pydantic'].BaseSettings = BaseSettings
else:
    import pydantic
    pydantic.BaseSettings = BaseSettings

# After chromadb import, restore our app's env vars (will be done after chromadb init)
def restore_env():
    for key, value in _saved_env.items():
        if value is not None:
            os.environ[key] = value
