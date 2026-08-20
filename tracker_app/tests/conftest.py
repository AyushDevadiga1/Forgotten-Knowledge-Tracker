import os

os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('DEBUG', 'true')

# Import config before pinning the auth state so first-run SECRET_KEY/API_KEY
# auto-generation happens exactly once and deterministically.
import tracker_app.config  # noqa: F401

# The API tests exercise endpoints without credentials. Force an empty API_KEY
# for this process (load_dotenv never overrides existing vars), which disables
# both auth gates regardless of what a developer's real .env contains.
os.environ['API_KEY'] = ''
