"""Delivery evidence is separate from a usable preview or a successful build."""
import hashlib
import json
from pathlib import Path
from local_app import web_builder
from local_app.atomic_storage import atomic_write


def revision(site):
    digest=hashlib.sha256()
    for path in sorted(Path(site).rglob('*')):
        rel=path.relative_to(site)
        if any(part in web_builder.IGNORED_DIRS for part in rel.parts) or path.name in web_builder.PRIVATE_NAMES:
            continue
        if path.is_symlink():raise ValueError('Lien symbolique non vérifiable dans la livraison.')
        if path.is_file():
            digest.update(rel.as_posix().encode()+b'\x00')
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            digest.update(b'\x00')
    return digest.hexdigest()


def assess(site, technical, visual, *, functional_checks=None):
    reasons=[]
    if technical.get('ok') is not True:reasons.append('technical_checks_failed')
    if visual.get('status')!='passed' or visual.get('reviewed') is not True or visual.get('issues'):
        reasons.append('visual_checks_'+str(visual.get('status') or 'not_run'))
    screenshots=visual.get('screenshots') or []
    modes={row.get('mode') for row in screenshots}
    if not {'ordinateur','tablette','telephone'}<=modes:reasons.append('missing_viewports')
    for row in screenshots:
        path=Path(site)/str(row.get('path') or '')
        if not path.resolve().is_relative_to(Path(site).resolve()) or not path.is_file():
            reasons.append('missing_screenshot');break
    current=revision(site)
    checks=functional_checks or {}
    # A bare submit button or an agent's assertion is not a business receipt.
    if checks.get('revision')!=current or checks.get('verified') is not True:
        reasons.append('business_acceptance_not_verified')
    return {'schema':1,'ready_to_deliver':not reasons,'revision':current,
            'technical':technical,'visual':visual,'functional_checks':checks,
            'blocking_reasons':list(dict.fromkeys(reasons)),
            'artistic_quality':'operator_review_required'}


def save(store,project_id,technical,visual):
    root=store.project_dir(project_id)
    # This file is owned by the app/operator, outside the agent's site workspace.
    path=root/'functional_checks.json'
    try:checks=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):checks={}
    report=assess(root/'site',technical,visual,functional_checks=checks)
    atomic_write(root/'delivery_report.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
    return report


def current(store,project_id):
    root=store.project_dir(project_id)
    try:report=json.loads((root/'delivery_report.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return {'ready_to_deliver':False,'blocking_reasons':['delivery_checks_not_run']}
    if report.get('revision')!=revision(root/'site'):
        return {**report,'ready_to_deliver':False,'blocking_reasons':['project_changed_since_review']}
    return report
