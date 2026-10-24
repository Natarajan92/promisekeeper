"""Explicit LIVE browser measurement child; configuration is never printed."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
import threading

import uvicorn
from promisekeeper.api.app import create_app
from promisekeeper.config import load_settings

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    database = Path(args.database).resolve()
    if not database.is_relative_to(root / '.runtime' / 'live-browser'):
        parser.error('LIVE measurement requires isolated runtime storage')
    settings = replace(load_settings(), agent_mode='LIVE', model='zai-org/GLM-5.3-Flash', db_path=database)
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host='127.0.0.1', port=args.port, workers=1, log_level='error'))
    # The Windows venv launcher may have a Python child; stop the owned server
    # through its stdin rather than leaving that child behind by killing a wrapper.
    def shutdown():
        sys.stdin.readline()
        server.should_exit = True
    threading.Thread(target=shutdown, daemon=True).start()
    server.run()
