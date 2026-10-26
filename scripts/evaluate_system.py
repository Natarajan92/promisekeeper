"""Run from the repository root with the existing backend dev environment."""
import argparse
from pathlib import Path
from system_eval.runner import evaluate, exit_code


def main():
    parser=argparse.ArgumentParser(description='Fictional offline PromiseKeeper system evals; no LIVE/config/credential loading')
    parser.add_argument('--dataset',type=Path,default=Path('evals/system/cases.json'))
    parser.add_argument('--output',type=Path,required=True,help='New directory; existing evidence is never overwritten')
    args=parser.parse_args()
    report=evaluate(args.dataset,args.output)
    print(report['summary'])
    return exit_code(report['rows'])


if __name__=='__main__':
    raise SystemExit(main())
