import sys

from app.core.config import Settings
from app.core.security import create_access_token


def main() -> None:
    subject = sys.argv[1] if len(sys.argv) > 1 else "test-user"
    settings = Settings()
    token, expires_in = create_access_token(subject, settings)
    print(token)
    print(f"# subject={subject} expires_in={expires_in}s", file=sys.stderr)


if __name__ == "__main__":
    main()
