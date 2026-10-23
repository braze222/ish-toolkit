#!/usr/bin/env python3
"""One bounded daily research batch; artifacts contain public/demo data only."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.elmatrix import cli


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if not args.demo and not os.environ.get('YOUTUBE_API_KEY'):
        p.error('YOUTUBE_API_KEY secret is missing; no live research performed')
    output = cli.private_dir(args.output)
    queries = {'cleaning': 'cleaning business South Africa',
               'repairs': 'home repair tutorials', 'digital-services': 'web design small business tutorials'}
    for niche, query in queries.items():
        command = ['scan', '--niche', niche, '--query', query, '--order', 'viewCount', '--limit', '10']
        if args.demo:
            command += ['--input', str(Path(__file__).resolve().parents[1]/'examples/elmatrix/demo-videos.json')]
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            result = cli.main(command)
        if result:
            return result
        snapshot = json.loads(captured.getvalue())
        cli.write_json_new(output/(niche+'.json'), snapshot)
        report_args = argparse.Namespace(niche=niche, query=query, format='markdown')
        with (output/(niche+'.md')).open('x', encoding='utf-8') as handle:
            handle.write(cli.report(report_args))
    cli.write_json_new(output/'STATUS.json', {'mode': 'DEMO' if args.demo else 'LIVE',
                                               'completed_at': cli.stamp(), 'niches': list(queries),
                                               'video_generation': False, 'publishing': False})
    print('Completed ' + ('DEMO' if args.demo else 'LIVE') + ' research batch: 3 niches.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
