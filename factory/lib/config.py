"""Resolve every role to a validated CLI profile."""
import json
from pathlib import Path

ROLES = {'intake', 'spec-writer', 'builder', 'approver'}
REVIEWERS = {'code', 'security', 'ui'}
RISKS = {'low', 'medium', 'high'}
TRACKS = {'simple', 'complex'}


class FactoryError(Exception):
    pass


def load_config(root):
    config = json.loads((Path(root) / 'factory/config.json').read_text())
    for key in ('concurrency', 'max_rounds', 'max_grill_rounds', 'step_timeout_seconds', 'check_timeout_seconds'):
        value = config.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise FactoryError(f'{key} must be a positive integer')
    value = config.get('max_check_rounds')
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
        raise FactoryError('max_check_rounds must be null, 0 (unlimited), or a positive integer')
    value = config.setdefault('max_stalled_rounds', 2)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise FactoryError('max_stalled_rounds must be a positive integer')
    simple = config.get('simple_track_risks')
    if not isinstance(simple, list) or not set(simple) <= RISKS or 'high' in simple:
        raise FactoryError('simple_track_risks must list low and/or medium risk')
    profiles = config.get('profiles', {})
    if not profiles:
        raise FactoryError('configure at least one CLI profile')
    for name, profile in profiles.items():
        if not isinstance(profile, dict) or profile.get('cli') not in {'claude', 'codex'}:
            raise FactoryError(f'profile {name}: cli must be claude or codex')
        if set(profile) - {'cli', 'model', 'reasoning_effort'}:
            raise FactoryError(f'profile {name}: unknown settings')
        for key in ('model', 'reasoning_effort'):
            value = profile.get(key)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise FactoryError(f'profile {name}: {key} must be a nonempty string or null')
        effort = profile.get('reasoning_effort')
        allowed = {'low', 'medium', 'high', 'xhigh', 'max'} if profile['cli'] == 'claude' else {'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'}
        if effort is not None and effort not in allowed:
            raise FactoryError(f'profile {name}: unsupported reasoning_effort {effort}')
    steps = config.get('steps', {})
    if set(steps) != ROLES:
        raise FactoryError('steps must define intake, spec-writer, builder, and approver')
    references = list(steps.values())
    routing = config.get('routing', {})
    if set(routing) != RISKS:
        raise FactoryError('routing must define low, medium, and high risk')
    for mapping in [*routing.values(), *config.get('surface_reviewers', {}).values()]:
        if not isinstance(mapping, dict) or not mapping or set(mapping) - REVIEWERS:
            raise FactoryError('reviewer routing must map known review roles to profiles')
        references.extend(mapping.values())
    for risk, mapping in routing.items():
        if 'code' not in mapping:
            raise FactoryError(f'{risk} risk must include a code reviewer')
    for name in references:
        if not isinstance(name, str) or name not in profiles:
            raise FactoryError(f'unknown profile {name!r}')
    return config


def gate_failure(config, job, head):
    """After a failed gate on commit `head`: the job's new check streak, and why to
    escalate instead of building again, or None.

    Failed checks alone never end a job. It escalates only when the builder stops
    making progress: `max_stalled_rounds` failed gates in a row on a commit the
    previous failed gate already ran, or, when set, `max_check_rounds` failed
    gates in a row."""
    streak = job.get('check_streak') or {'failures': 0, 'unchanged': 0, 'commit': None}
    failures = streak['failures'] + 1
    unchanged = streak['unchanged'] + 1 if streak['commit'] == head else 0
    new = {'failures': failures, 'unchanged': unchanged, 'commit': head}
    if unchanged >= config['max_stalled_rounds']:
        return new, (f'The gate failed on commit {head[:7]} again after {unchanged} builder '
                     f'round{"s" if unchanged > 1 else ""} that changed nothing (max_stalled_rounds is '
                     f'{config["max_stalled_rounds"]}). See round-{job["round"]}/checks.md.')
    if config.get('max_check_rounds') and failures >= config['max_check_rounds']:
        return new, (f'The gate failed {failures} rounds in a row, the max_check_rounds limit. '
                     f'See round-{job["round"]}/checks.md.')
    return new, None


def agent_set(config, intake):
    reviewers = dict(config['routing'][intake['risk']])
    for surface in intake['surfaces']:
        if surface not in config['surface_reviewers']:
            raise FactoryError(f'unknown intake surface {surface!r}')
        reviewers.update(config['surface_reviewers'][surface])
    return {**config['steps'], 'reviewers': reviewers}


def profile_for(config, job, role):
    agents = job.get('agents') or {}
    name = agents.get('reviewers', {}).get(role.removeprefix('reviewer-')) if role.startswith('reviewer-') else agents.get(role, config['steps'].get(role))
    if name not in config['profiles']:
        raise FactoryError(f'{role}: unknown profile {name!r}; reroute legacy jobs before resuming')
    return name, dict(config['profiles'][name])
