"""Public CLI: JSON output, explicit execution grants, offline discovery by default."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from . import engine, model
from .model import ComputeError
from .providers import CONSOLES, console_status, endpoint
from .worker import capabilities, safe_text
from ..storage import StorageError


def emit(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def parser():
    p = argparse.ArgumentParser(description='iSH compute control plane. No resources are provisioned. Execution is opt-in.')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status', help='offline capability/configuration discovery')
    sub.add_parser('init', help='create private compute config; never touches vault')
    config_parser = sub.add_parser('config')
    config = config_parser.add_subparsers(dest='action')
    config_parser.set_defaults(action='show')
    config.add_parser('show')
    priorities = config.add_parser('priorities'); priorities.add_argument('order', help='comma-separated local,ssh,github')
    gh = config.add_parser('github', help='register reviewed Actions workflow at immutable revision')
    gh.add_argument('--repo', required=True); gh.add_argument('--ref', required=True)
    gh.add_argument('--commit', required=True, help='reviewed full commit SHA; ref must currently resolve to it')
    gh.add_argument('--token-ref', help='vault:name; otherwise official gh auth credential store')
    cloud = sub.add_parser('cloud'); cloud.add_argument('provider', choices=CONSOLES)
    cloud.add_argument('action', choices=['status','open','doctor','setup'])
    hosts = sub.add_parser('hosts').add_subparsers(dest='action', required=True)
    hosts.add_parser('list')
    add = hosts.add_parser('add'); add.add_argument('name'); add.add_argument('--address', required=True)
    add.add_argument('--user', required=True); add.add_argument('--port', type=int, default=22)
    add.add_argument('--identity', required=True); add.add_argument('--known-hosts', required=True)
    add.add_argument('--existing-host', action='store_true', help='attest this existing host is within your approved cost budget')
    remove = hosts.add_parser('remove'); remove.add_argument('name')
    test = hosts.add_parser('test'); test.add_argument('name'); test.add_argument('--docker', action='store_true')
    compute = sub.add_parser('compute'); compute.add_argument('action', choices=['status','providers','doctor','local','remote','docker','colab'], nargs='?', default='status')
    run = sub.add_parser('run', help='plan by default; --execute grants execution of the reviewed command')
    run.add_argument('--spec', type=Path); run.add_argument('--backend', default=None)
    run.add_argument('--timeout', type=int, default=None); run.add_argument('--cwd')
    run.add_argument('--execute', action='store_true'); run.add_argument('--allow-remote', action='store_true')
    run.add_argument('--allow-secrets', action='store_true'); run.add_argument('--allow-cost', action='store_true')
    run.add_argument('argv', nargs=argparse.REMAINDER)
    jobs = sub.add_parser('jobs').add_subparsers(dest='action', required=True)
    jobs.add_parser('list')
    for name in ('inspect','logs','artifacts','cancel'):
        q = jobs.add_parser(name); q.add_argument('id')
        if name == 'inspect': q.add_argument('--refresh', action='store_true')
        if name == 'cancel': q.add_argument('--confirm', action='store_true')
        if name == 'artifacts':
            q.add_argument('--destination'); q.add_argument('--artifact-id', type=int)
    return p


def status():
    c = model.config()
    return {'local': capabilities(), 'configured_hosts': sorted(c['hosts']),
            'github_configured': bool(c['github']), 'priorities': c['priorities'],
            'consoles': [console_status(n) for n in CONSOLES],
            'remote_status': 'not probed; use hosts test NAME',
            'executors': [
                {'provider': 'local', 'types': ['command'], 'auth': 'current account',
                 'persistence': 'foreground; no daemon', 'quota': 'local resources', 'cost': 'no provider charge'},
                {'provider': 'ssh', 'types': ['command', 'docker'], 'auth': 'explicit key and verified host',
                 'persistence': 'foreground worker; terminal receipts persist', 'quota': 'probe required', 'cost': 'host policy required'},
                {'provider': 'github', 'types': ['workflow'], 'auth': 'official gh login or vault token',
                 'persistence': 'bounded workflow; retention applies', 'quota': 'unknown', 'cost': 'explicit review required'}],
            'security': {'host_verification': 'strict', 'implicit_execution': False,
                         'automatic_retries': False, 'provisioning': False}}


def main(argv=None):
    p = parser(); args = p.parse_args(argv)
    try:
        if args.command == 'init':
            model.mutate(lambda c: None)
            emit({'initialized': str(model.root()), 'vault_changed': False})
        elif args.command == 'config':
            if args.action == 'show': emit(model.config())
            elif args.action == 'priorities':
                order = args.order.split(',')
                if sorted(order) != ['github','local','ssh']: raise ComputeError('specify local,ssh,github exactly once')
                model.mutate(lambda c: c.update(priorities=order)); emit(model.config())
            else:
                profile = {'repo': args.repo, 'ref': args.ref, 'commit': args.commit, 'workflow': 'ish-job.yml', 'token_ref': args.token_ref, 'cost': 'unknown'}
                model.github_validate(profile)
                model.mutate(lambda c: c.update(github=profile)); emit({'github': profile, 'authentication': 'not checked'})
        elif args.command == 'status': emit(status())
        elif args.command == 'cloud':
            if args.action == 'open':
                print(CONSOLES[args.provider]['url'])
                print('Open this official URL in your browser. No remote execution connection was created.')
            elif args.action == 'setup':
                emit({'provider': args.provider, 'console': CONSOLES[args.provider]['url'],
                      'steps': ['Open the official console and sign in using provider MFA.',
                                'Review provider storage/billing/session choices yourself.',
                                'Clone the trusted repository in that console; inspect scripts/bootstrap-cloud.sh.',
                                'Run sh scripts/bootstrap-cloud.sh from the reviewed checkout.'],
                      'provisioning': False, 'guide': 'docs/CLOUD_COMPUTE.md'})
            else: emit(console_status(args.provider, args.action == 'doctor'))
        elif args.command == 'hosts':
            if args.action == 'list': emit(model.config()['hosts'])
            elif args.action == 'add':
                h = {'address': args.address, 'user': args.user, 'port': args.port,
                     'identity': str(Path(args.identity).expanduser().absolute()),
                     'known_hosts': str(Path(args.known_hosts).expanduser().absolute()),
                     'cost': 'existing' if args.existing_host else 'unknown'}
                model.host_validate(args.name, h)
                from .providers import ssh_argv
                ssh_argv(h)  # verify safe trust/key files before registering
                def register(c):
                    if args.name in c['hosts']: raise ComputeError('host exists; remove profile explicitly before replacing')
                    c['hosts'][args.name] = h
                model.mutate(register); emit({'registered': args.name, 'connected': False})
            elif args.action == 'remove':
                def remove(c):
                    if args.name not in c['hosts']: raise ComputeError('host not configured')
                    del c['hosts'][args.name]
                model.mutate(remove); emit({'removed_profile': args.name, 'keys_deleted': False})
            else:
                h = model.config()['hosts'].get(args.name)
                if h is None: raise ComputeError('host not configured')
                emit(endpoint(h, {'action': 'probe', 'docker': args.docker}))
        elif args.command == 'compute':
            if args.action in ('status','providers','doctor'):
                result = status()
                if args.action == 'doctor':
                    result['checks'] = {'configuration_schema': 'valid', 'state_permissions': 'private',
                                        'ssh_cli': bool(shutil.which('ssh')), 'git_cli': bool(shutil.which('git')),
                                        'remote_authentication': 'not tested; use hosts test or cloud doctor explicitly'}
                emit(result)
            elif args.action == 'local': emit(capabilities())
            elif args.action == 'remote': emit({'hosts': model.config()['hosts'], 'state': 'not probed'})
            elif args.action == 'docker': emit({'local_cli': bool(shutil.which('docker')), 'engine': 'not probed; use hosts test NAME --docker', 'note': 'Docker daemon is not assumed available inside iSH'})
            else: emit({'provider': 'colab', 'mode': 'discovery-only', 'url': 'https://colab.research.google.com/', 'unattended_execution': False})
        elif args.command == 'run':
            spec = {}
            if args.spec:
                if args.spec.stat().st_size > 24000: raise ComputeError('job specification too large')
                spec = json.loads(args.spec.read_text())
                if args.argv: raise ComputeError('use a specification or argv, not both')
            else:
                spec['command'] = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
            for field in ('backend','timeout','cwd'):
                if getattr(args, field) is not None: spec[field] = getattr(args, field)
            result = engine.submit(spec, execute=args.execute, allow_remote=args.allow_remote,
                                   allow_secrets=args.allow_secrets, allow_cost=args.allow_cost)
            emit(result)
            return 0 if result.get('dry_run') or result.get('state') in ('completed','submitted','running') else 1
        elif args.command == 'jobs':
            if args.action == 'list':
                base = model.root() / 'jobs'
                emit([{'id': j['id'], 'backend': j['backend'], 'state': j['state'], 'evidence': j['evidence']}
                      for j in (engine.read_job(d.name) for d in sorted(base.iterdir()) if model.ID.fullmatch(d.name))] if base.exists() else [])
            elif args.action == 'inspect': emit(engine.refresh(args.id) if args.refresh else engine.read_job(args.id))
            elif args.action == 'cancel':
                if not args.confirm: raise ComputeError('cancellation requires --confirm; it cannot undo effects already performed')
                emit(engine.refresh(args.id, 'cancel'))
            elif args.action == 'logs': emit(engine.logs(args.id))
            else: emit(engine.artifacts(args.id, args.destination, args.artifact_id))
        return 0
    except (ComputeError, StorageError) as exc:
        print('ish: ' + safe_text(str(exc)), file=sys.stderr); return 2
    except (OSError, ValueError, KeyError, TypeError):
        print('ish: invalid input, inaccessible path, authentication or provider failure; no automatic retry', file=sys.stderr); return 2
    except KeyboardInterrupt:
        return 130

if __name__ == '__main__':
    raise SystemExit(main())
