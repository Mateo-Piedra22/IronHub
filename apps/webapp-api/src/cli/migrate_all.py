import argparse

from dotenv import load_dotenv

load_dotenv()

from src.cli.migrate import main as migrate_tenants_main
from src.cli.migrate_admin import main as migrate_admin_main


def main() -> None:
    parser = argparse.ArgumentParser(prog="webapp-api-migrate-all")
    parser.add_argument("--skip-admin", action="store_true")
    args, rest = parser.parse_known_args()

    if not bool(args.skip_admin):
        migrate_admin_main()

    import sys

    sys.argv = [sys.argv[0]] + list(rest)
    migrate_tenants_main()


if __name__ == "__main__":
    main()
