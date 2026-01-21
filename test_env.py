import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

env = environ.Env()
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)
    print("✓ .env file found and loaded")
else:
    print("✗ .env file not found")

print(f"\nDB_NAME: {env('DB_NAME', default='NOT SET')}")
print(f"DB_USER: {env('DB_USER', default='NOT SET')}")
print(f"DB_PASSWORD: {env('DB_PASSWORD', default='NOT SET')}")
print(f"DB_HOST: {env('DB_HOST', default='NOT SET')}")
print(f"DB_PORT: {env('DB_PORT', default='NOT SET')}")
