"""Redis connectivity for short-lived application data."""

from redis import Redis

from app.config.settings import get_settings


def main() -> None:
    with Redis.from_url(get_settings().redis_url, socket_timeout=3) as client:
        if not client.ping():
            raise SystemExit("Redis did not acknowledge PING")
    print("Redis connection verified.")


if __name__ == "__main__":
    main()
