"""One owned service and explicit fresh copies; no implicit creation or reset."""

import argparse
import json
import os
from uuid import uuid4

from promisekeeper.application.cases import create_demonstration
from promisekeeper.application.operations import CommandError
from promisekeeper.config import load_settings
from promisekeeper.persistence.ownership import OwnershipError
from promisekeeper.persistence.sqlite import Database


def export_tracing(settings):
    """LangSmith reads its configuration from the process environment; only LANGSMITH_* entries are exported."""
    os.environ.update(settings.tracing)


def run_agent_suite(settings, suite, *, repeats):
    """Offline in STUB (proves the harness only); real provider calls in LIVE."""
    from promisekeeper.agents.roster import build_agents
    from promisekeeper.application import agent_evaluation as evaluation
    if suite == 'agents':
        agents = build_agents(settings)
        judge = evaluation.ScriptedJudge() if settings.agent_mode == 'STUB' else (
            evaluation.LlmToneJudge(settings) if settings.api_key or settings.fireworks_api_key else None)
        report = evaluation.evaluate_agents(agents, repeats=repeats, judge=judge)
    else:
        if settings.agent_mode != 'STUB' and not settings.api_key:
            raise ValueError('LIVE Hinglish evaluation requires the Nebius key')
        classifier = evaluation.ScriptedHinglishClassifier() if settings.agent_mode == 'STUB' else evaluation.LiveHinglishClassifier(settings)
        report = evaluation.evaluate_hinglish(classifier)
    report['langsmith_uploaded'] = evaluation.upload_to_langsmith(report, f'promisekeeper-{suite}')
    return report


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
    evaluate = sub.add_parser('evaluate')
    evaluate.add_argument('--suite', required=True, choices=['live', 'fixtures', 'agents', 'hinglish'])
    evaluate.add_argument('--catalogue', required=True, choices=['release-0.1'])
    evaluate.add_argument('--repeats', type=int, default=3)
    evaluate.add_argument('--output', default=None)
    measure = sub.add_parser('measure')
    measure.add_argument('--suite', required=True, choices=['responsiveness', 'preservation'])
    measure.add_argument('--trials-per-case', type=int, default=10, choices=[10])
    measure.add_argument('--cycles', type=int, default=10, choices=[10])
    measure.add_argument('--report', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'evaluate' and args.suite == 'fixtures':
            from promisekeeper.application.fixture_evaluation import evaluate_fixtures
            report = evaluate_fixtures(catalogue=args.catalogue, output=args.output or 'reports/fixture-evaluation.json')
            print(json.dumps(dict(status=report['status'], passed=report['passed'], runs=len(report['runs']), live_qualified=False)))
            if not report['passed']:
                parser.exit(1, 'Scripted catalogue evaluation did not pass. See the report.\n')
            return
        settings = load_settings()
        if args.command == 'evaluate' and args.suite in {'agents', 'hinglish'}:
            report = run_agent_suite(settings, args.suite, repeats=args.repeats)
            output = args.output or f'reports/{args.suite}-evaluation.json'
            with open(output, 'w', encoding='utf-8') as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
            print(json.dumps(dict(suite=report['suite'], mode=report['mode'], live_qualified=False, metrics=report['metrics'],
                                  langsmith_uploaded=report['langsmith_uploaded'])))
            return
        if args.command == "init-demo":
            with Database(settings.db_path) as db:
                response = create_demonstration(db, dict(schema_version="1", operation_id=str(uuid4()),
                    catalogue_version=args.catalogue, variant_id=args.variant, clock_mode=args.clock))
                print(json.dumps(response))
        elif args.command == 'measure':
            from promisekeeper.application.measurements import measure as run_measurement
            report = run_measurement(settings, suite=args.suite, report=args.report,
                trials_per_case=args.trials_per_case, cycles=args.cycles)
            print(json.dumps(dict(status=report['status'], passed=report['passed'], runs=len(report['runs']))))
            if not report['passed']:
                parser.exit(1, 'Release measurements did not pass. See the report.\n')
        elif args.command == 'evaluate':
            from promisekeeper.application.evaluations import evaluate as run_evaluation
            report=run_evaluation(settings,catalogue=args.catalogue,repeats=args.repeats,output=args.output or 'reports/live-evaluation.json')
            print(json.dumps(dict(status=report['status'],qualification_scope=report['qualification_scope'],qualified=report['qualified'],requested_model=report['requested_model'],runs=len(report['runs']))))
            if not report['qualified']:parser.exit(1,'LIVE release acceptance did not qualify. See the evaluation report.\n')
        else:
            if not 1 <= args.port <= 65535:
                parser.error("port must be between 1 and 65535")
            import uvicorn
            from promisekeeper.api.app import create_app
            export_tracing(settings)
            uvicorn.run(create_app(settings), host=args.host, port=args.port, workers=1)
    except (ValueError, CommandError, OwnershipError):
        parser.exit(1, "The command could not complete. Check configuration, catalogue selection, and database ownership.\n")


if __name__ == "__main__":
    main()
