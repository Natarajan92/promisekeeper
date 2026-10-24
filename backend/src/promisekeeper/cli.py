"""One owned service and explicit fresh copies; no implicit creation or reset."""

import argparse
import json
from uuid import uuid4

from promisekeeper.application.cases import create_demonstration
from promisekeeper.application.operations import CommandError
from promisekeeper.config import load_settings
from promisekeeper.persistence.ownership import OwnershipError
from promisekeeper.persistence.sqlite import Database


def main(argv=None):
    parser = argparse.ArgumentParser(prog="promisekeeper")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init-demo")
    init.add_argument("--catalogue", required=True, choices=["release-0.1"])
    init.add_argument("--variant", default=None)
    init.add_argument("--clock", required=True, choices=["REFERENCE", "REAL"])
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost", "::1"])
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--workers", type=int, default=1, choices=[1])
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        if args.command == "init-demo":
            with Database(settings.db_path) as db:
                response = create_demonstration(db, dict(schema_version="1", operation_id=str(uuid4()),
                    catalogue_version=args.catalogue, variant_id=args.variant, clock_mode=args.clock))
                print(json.dumps(response))
        else:
            if not 1 <= args.port <= 65535:
                parser.error("port must be between 1 and 65535")
            import uvicorn
            from promisekeeper.api.app import create_app
            uvicorn.run(create_app(settings), host=args.host, port=args.port, workers=1)
    except (ValueError, CommandError, OwnershipError):
        parser.exit(1, "The command could not complete. Check configuration, catalogue selection, and database ownership.\n")


if __name__ == "__main__":
    main()
