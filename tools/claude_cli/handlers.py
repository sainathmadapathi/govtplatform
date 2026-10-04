"""The job handlers: one per allow-listed job operation.

A handler turns a sanitised job input into a `JobOutcome`. It may call the gateway, and it may
read the exam store; it never writes a fact. What a handler returns is data for a human or for
the candidate's page: discovery candidates (checked, never auto-official), proposed field values
(each with a quotation the server verified verbatim), a build's gate outcome, a validated answer
or practice set. Anything that changes canonical exam information still goes through the
existing publication gate and human review.

Every normaliser here is the only door a request's values pass through: it whitelists keys,
bounds sizes, checks types and refuses everything else. Prompt text, CLI flags, tool permissions
and working directories are not inputs and cannot become inputs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .context import (ExamStore, answer_verification, build_fact_sheet, citations, clean_text, syllabus_topics, validate_answer,
                      MAX_QUESTION_CHARS)
from .discovery import DiscoveryUnavailable, classify_url, discover
from .jobs import JobContext, JobOutcome, JobSpec
from .client import get_gateway
from .schemas import EXTRACTABLE_FIELDS, InfraStatus, Operation, SAFE_MESSAGES

_ID = re.compile(r'^[A-Za-z0-9._:-]{1,120}$')
_YEAR = re.compile(r'^(?:[0-9]{4}(?:-[0-9]{2,4})?)?$')

ENGINE = 'claude-cli'
LABEL_ASSISTED = 'CLAUDE_ASSISTED'
LABEL_GENERATED = 'GOVOS_AUTHORED'
PRACTICE_LABEL = ('GovOS practice question — written by Claude for this syllabus topic; '
                  'not an official previous-year question.')
#: Every served question's key was confirmed by a second, independent solve (see generate_practice).
ANSWER_CHECK = 'INDEPENDENT_SOLVE_AGREED'


@dataclass
class AppHooks:
    """What the app supplies to the handlers: its database-backed pieces, so this package never
    imports `app.py`."""

    exam_store: ExamStore
    #: URL -> OFFICIAL | TRUSTED_PUBLIC | UNVERIFIED (the app's statutory-host list).
    classify_trust: Callable[[str], str] = classify_url
    #: (manifest dict, mode, exam_id, job_id) -> research run id
    persist_discovery: Optional[Callable[[dict, str, str, str], int]] = None
    #: finding id -> {'id','url','title','text','trust','examId','examName'} or None
    load_finding: Optional[Callable[[int], Optional[dict]]] = None
    #: (finding id, accepted proposals) -> a summary dict
    ingest_facts: Optional[Callable[[int, list], dict]] = None
    #: Replaced in tests; the real gateway is used when None.
    gateway: Any = None

    def claude(self):
        return self.gateway or get_gateway()


def _fail(status: InfraStatus, *, message: str = '', retryable: Optional[bool] = None, **kw: Any) -> JobOutcome:
    return JobOutcome('FAILED', error_category=status.value, error_message=message or SAFE_MESSAGES.get(status, ''),
                      retryable=status.retryable if retryable is None else retryable, **kw)


def _failed_result(res) -> JobOutcome:
    if res.status is InfraStatus.CANCELLED:
        return JobOutcome('CANCELLED', error_category='CANCELLED', error_message=SAFE_MESSAGES[InfraStatus.CANCELLED])
    return _fail(res.status, template_version=res.template_version, audit={'inputFingerprint': res.input_fingerprint})


# ================================================================================ normalisers
def _need_id(inp: dict, key: str) -> str:
    value = str(inp.get(key) or '').strip()
    if not _ID.match(value):
        raise ValueError(f'{key} is required and must be a plain identifier')
    return value


def norm_discover(inp: dict) -> dict:
    query = clean_text(inp.get('query'), 300)
    if not query:
        raise ValueError('query is required')
    mode = 'OFFICIAL' if str(inp.get('mode') or 'OFFICIAL').upper() == 'OFFICIAL' else 'ANY'
    try:
        n = max(1, min(int(inp.get('maxResults', inp.get('max_results', 8))), 12))
    except (TypeError, ValueError):
        n = 8
    out = {'query': query, 'mode': mode, 'maxResults': n}
    if inp.get('examId') or inp.get('exam_id'):
        out['examId'] = _need_id({'examId': inp.get('examId') or inp.get('exam_id')}, 'examId')
    return out


def norm_extract(inp: dict) -> dict:
    try:
        fid = int(inp.get('findingId', inp.get('finding_id')))
    except (TypeError, ValueError):
        raise ValueError('findingId is required')
    if fid <= 0:
        raise ValueError('findingId is required')
    wanted = inp.get('fields') or []
    if not isinstance(wanted, (list, tuple)):
        raise ValueError('fields must be a list')
    fields = [f for f in wanted if f in EXTRACTABLE_FIELDS]
    return {'findingId': fid, 'fields': fields or list(EXTRACTABLE_FIELDS)}


def norm_build(inp: dict) -> dict:
    query = clean_text(inp.get('query') or inp.get('exam'), 160)
    if not query:
        raise ValueError('query (the exam name) is required')
    year = str(inp.get('year') or inp.get('cycle') or '').strip()
    if not _YEAR.match(year):
        raise ValueError('year must look like 2026 or 2026-27')
    use = inp.get('useClaude', inp.get('claude', False))
    if isinstance(use, str):
        use = use.strip().lower() in ('1', 'true', 'yes', 'on')
    out = {'query': query, 'year': year, 'useClaude': bool(use)}
    deep = inp.get('authorityDiscovery', False)
    if isinstance(deep, str):
        deep = deep.strip().lower() in ('1', 'true', 'yes', 'on')
    if deep:
        # Opt-in, and only present when asked for, so a plain build's input (and its dedupe key)
        # is exactly what it always was.
        out['authorityDiscovery'] = True
    return out


def norm_authority(inp: dict) -> dict:
    """Authority source discovery starts only from an exam GovOS already holds: its root is that
    exam's verified official address, never an address a request supplies."""
    out = {'examId': _need_id(inp, 'examId')}
    use = inp.get('useClaude', inp.get('claude', False))
    if isinstance(use, str):
        use = use.strip().lower() in ('1', 'true', 'yes', 'on')
    if use:
        out['useClaude'] = True
    return out


def norm_roadmap(inp: dict) -> dict:
    return {'examId': _need_id(inp, 'examId')}


def norm_answer(inp: dict) -> dict:
    question = clean_text(inp.get('question'), MAX_QUESTION_CHARS)
    if not question:
        raise ValueError('question is required')
    history = []
    raw_history = inp.get('history') or []
    if not isinstance(raw_history, list):
        raise ValueError('history must be a list')
    for turn in raw_history[-6:]:
        if isinstance(turn, dict) and turn.get('role') in ('user', 'assistant'):
            text = clean_text(turn.get('text'), 500)
            if text:
                history.append({'role': turn['role'], 'text': text})
    return {'examId': _need_id(inp, 'examId'), 'question': question, 'history': history}


def norm_practice(inp: dict) -> dict:
    topic = clean_text(inp.get('topic'), 300)
    if not topic:
        raise ValueError('topic is required')
    try:
        count = max(1, min(int(inp.get('count', 3)), 5))
    except (TypeError, ValueError):
        count = 3
    difficulty = str(inp.get('difficulty') or 'MEDIUM').upper()
    if difficulty not in ('EASY', 'MEDIUM', 'HARD'):
        difficulty = 'MEDIUM'
    return {'examId': _need_id(inp, 'examId'), 'topic': topic, 'count': count, 'difficulty': difficulty}


# ================================================================================== discovery
def discover_sources(ctx: JobContext) -> JobOutcome:
    inp, hooks = ctx.job.input, ctx.hooks
    ctx.stage('DISCOVERING')
    try:
        manifest = discover(inp['query'], max_results=inp.get('maxResults', 8),
                            official_only=inp.get('mode') == 'OFFICIAL', gateway=hooks.claude(),
                            job_id=ctx.job.id, classify=hooks.classify_trust)
    except DiscoveryUnavailable as exc:
        return _fail(exc.status)
    if ctx.cancelled:
        return JobOutcome('CANCELLED')
    ctx.stage('RECORDING')
    data = manifest.as_dict()
    run_id = hooks.persist_discovery(data, inp.get('mode', 'OFFICIAL'), inp.get('examId', ''), ctx.job.id) \
        if hooks.persist_discovery else None
    links = [{'kind': 'RESEARCH_RUN', 'runId': run_id}] if run_id else []
    return JobOutcome('SUCCEEDED', result={'runId': run_id, 'manifest': data}, evidence_links=links,
                      template_version=manifest.template_version,
                      audit={'candidates': len(manifest.candidates), 'rejected': len(manifest.rejected),
                             'webActivity': manifest.web_activity})


# =================================================================================== extraction
def _norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def value_supported_by_quote(value: str, quote: str) -> bool:
    """Is the proposed value stated in the quotation? Every run of digits in the value, and every
    word of three or more letters, must be in the quote (a date may be reformatted; nothing may be
    added)."""
    v, q = _norm(value).lower(), _norm(quote).lower()
    if not v or not q:
        return False
    if re.search(r'(?<![a-z0-9])' + re.escape(v) + r'(?![a-z0-9])', q):   # not "42" inside "4217"
        return True
    q_digits = {g.lstrip('0') or '0' for g in re.findall(r'\d+', q)}
    v_digits = [g.lstrip('0') or '0' for g in re.findall(r'\d+', v)]
    if v_digits and not all(g in q_digits for g in v_digits):
        return False
    q_words = set(re.findall(r'[a-z]{3,}', q))
    v_words = re.findall(r'[a-z]{3,}', v)
    return bool(v_digits or v_words) and all(w in q_words for w in v_words)


def verify_proposals(proposals: list, source_text: str, wanted: Optional[list] = None) -> list:
    """Each proposal with `verified` and the reasons. A value is accepted only when its quotation
    is verbatim in the supplied source text (whitespace aside) and the value is stated in it, and
    (when `wanted` is given) the field is one that was asked for."""
    haystack = _norm(source_text)
    out = []
    for p in proposals:
        quote = _norm(p.get('quote', ''))
        reasons = []
        if wanted is not None and p.get('field') not in wanted:
            reasons.append('the field was not requested')
        elif len(quote) < 8:
            reasons.append('the quotation is too short to be evidence')
        elif quote not in haystack:
            reasons.append('the quotation is not printed in the source text')
        if not reasons and not value_supported_by_quote(p.get('value', ''), quote):
            reasons.append('the quotation does not state the proposed value')
        out.append({**p, 'quote': quote, 'verified': not reasons, 'reasons': reasons})
    return out


def extract_fields(ctx: JobContext) -> JobOutcome:
    inp, hooks = ctx.job.input, ctx.hooks
    if hooks.load_finding is None:
        return _fail(InfraStatus.CLAUDE_CLI_FAILED, message='Extraction is not configured.', retryable=False)
    finding = hooks.load_finding(inp['findingId'])
    if not finding:
        return JobOutcome('FAILED', error_category='FINDING_NOT_FOUND', error_message='No such finding.')
    text = finding.get('text') or ''
    if not text.strip():
        return JobOutcome('FAILED', error_category='NO_SOURCE_TEXT',
                          error_message='Fetch the page text first; there is nothing to read yet.')
    ctx.stage('EXTRACTING')
    res = hooks.claude().run(Operation.EXTRACT_FIELDS, {
        'exam': finding.get('examName') or finding.get('examId') or finding.get('title') or '',
        'cycle': '', 'authority': '', 'source_title': finding.get('title') or '', 'source_url': finding.get('url') or '',
        'source_text': text[:40_000], 'fields': inp['fields']})
    if not res.ok:
        return _failed_result(res)
    ctx.stage('VERIFYING_QUOTES')
    checked = verify_proposals(res.output.get('fields', []), text[:40_000], inp['fields'])
    accepted = [p for p in checked if p['verified']]
    summary = hooks.ingest_facts(inp['findingId'], accepted) if (hooks.ingest_facts and accepted) else None
    return JobOutcome('SUCCEEDED', result={
        'proposed': len(checked), 'verified': len(accepted),
        'rejected': [{'field': p['field'], 'reasons': p['reasons']} for p in checked if not p['verified']],
        'ingest': summary,
        'note': 'Every stored value has a quotation the server found verbatim in the page text. '
                'Each is pending human review; none is published.'},
        evidence_links=[{'kind': 'RESEARCH_FINDING', 'findingId': inp['findingId']}],
        template_version=res.template_version, audit={'inputFingerprint': res.input_fingerprint})


# ======================================================================================= build
_INFRA_BUILD_STATES = ('INFRASTRUCTURE_FAILURE', 'SOURCE_FETCH_FAILURE')


def _authority_run_for(ctx: JobContext) -> Callable:
    """A build's authority walk: from the address the resolver verified, saved as its own run."""
    def run_for(resolved):
        from tools.exam_builder.authority_discovery import discover_authority
        from tools.exam_builder.source_graph import SourceGraphStore
        ctx.stage('DISCOVERING_AUTHORITY')
        run = discover_authority([resolved.authority.domain], authority_name=resolved.authority.name,
                                 should_continue=lambda: not ctx.cancelled)
        SourceGraphStore(ctx.db_path).save(run, job_id=ctx.job.id)
        ctx.stage('BUILDING')
        return run
    return run_for


def build_exam_job(ctx: JobContext) -> JobOutcome:
    from tools.exam_builder.materialize import EngineState, ExamRegistry, build_exam
    inp = ctx.job.input
    ctx.stage('BUILDING')
    extra = {}
    if inp.get('authorityDiscovery'):
        extra['authority_discovery'] = _authority_run_for(ctx)
    result = build_exam(inp['query'], inp['year'], registry=ExamRegistry(ctx.db_path),
                        use_claude=inp['useClaude'], gateway=ctx.hooks.claude() if ctx.hooks else None,
                        should_continue=lambda: not ctx.cancelled, **extra)
    data = result.to_dict()
    if result.state is EngineState.CANCELLED:
        return JobOutcome('CANCELLED', error_category='CANCELLED', result=data)
    links = []
    if result.registered:
        links = [{'kind': 'REGISTRY', 'examId': (result.registry or {}).get('examId'),
                  'cycle': (result.registry or {}).get('cycle'), 'version': (result.registry or {}).get('version')}]
    if result.state.value in _INFRA_BUILD_STATES:
        return JobOutcome('FAILED', result=data, error_category=result.state.value, retryable=True,
                          error_message='A source or the discovery service was unavailable; the build is unfinished '
                                        'and registered nothing.')
    # A gate BLOCK is a finished, honest result (nothing was published), not a failed job.
    return JobOutcome('SUCCEEDED', result=data, evidence_links=links,
                      audit={'state': result.state.value, 'registered': result.registered})


_CYCLE_IN_ID = re.compile(r'-(20[0-9]{2})(?:-[0-9]{2,4})?$')


def discover_authority_job(ctx: JobContext) -> JobOutcome:
    """Walk the exam's authority from its official address and keep the run as an audit record.

    Deterministic: links are read from the pages themselves. Claude is asked only when the job
    asks for it, only to classify links whose own words say nothing, and its answer never makes
    anything official -- see authority_discovery.classify_ambiguous."""
    from tools.exam_builder.authority_discovery import discover_authority, project_for_exam
    from tools.exam_builder.source_graph import SourceGraphStore, coverage_report
    from .discovery import validate_url_syntax
    inp = ctx.job.input
    exam = ctx.hooks.exam_store.get(inp['examId']) if ctx.hooks else None
    if exam is None:
        return JobOutcome('FAILED', error_category='EXAM_NOT_FOUND', error_message='No such exam.')
    root = str(exam.get('officialDomain') or '').strip()
    ok, _why = validate_url_syntax(root)
    if not ok:
        return JobOutcome('FAILED', error_category='NO_OFFICIAL_ADDRESS',
                          error_message='This exam has no official address to start from.')
    ctx.stage('DISCOVERING')
    gateway = ctx.hooks.claude() if inp.get('useClaude') else None
    run = discover_authority([root], authority_name=str(exam.get('authorityName') or ''), gateway=gateway,
                             should_continue=lambda: not ctx.cancelled)
    if run.cancelled:
        return JobOutcome('CANCELLED', error_category='CANCELLED', error_message=SAFE_MESSAGES[InfraStatus.CANCELLED])
    m = _CYCLE_IN_ID.search(inp['examId'])
    projection = project_for_exam(run, exam_id=inp['examId'], title=str(exam.get('title') or ''),
                                  authority_name=str(exam.get('authorityName') or ''), authority_domain=root,
                                  cycle=str(exam.get('cycle') or (m.group(1) if m else '')))
    ctx.stage('SAVING')
    SourceGraphStore(ctx.db_path).save(run, job_id=ctx.job.id, coverage=coverage_report(run))
    data = {'runId': run.id, 'examId': inp['examId'], 'estate': (run.estates or [''])[0],
            'coverage': projection['coverage'], 'searchStates': projection['searchStates'],
            'repositories': [{'title': r['title'], 'role': r['role'], 'itemsForThisExam': r['itemsForThisExam'],
                              'itemCount': r['itemCount']} for r in projection['repositories']],
            'claude': dict(run.claude)}
    return JobOutcome('SUCCEEDED', result=data, evidence_links=[{'kind': 'SOURCE_RUN', 'runId': run.id}],
                      audit={'pages': run.pages_fetched, 'documents': run.documents_fetched, 'nodes': len(run.graph)})


# ===================================================================================== roadmap
def order_roadmap(ctx: JobContext) -> JobOutcome:
    from tools.exam_builder.verification.roadmap_guidance import generate
    exam = ctx.hooks.exam_store.get(ctx.job.input['examId'])
    if exam is None:
        return JobOutcome('FAILED', error_category='EXAM_NOT_FOUND', error_message='No such exam.')
    topics = [{'id': t.get('id'), 'topicName': t.get('topicName'), 'subject': t.get('subject'),
               'weightagePercentage': t.get('weightagePercentage') or 0, 'isHighYield': t.get('isHighYield')}
              for t in exam.get('syllabus') or []]
    ctx.stage('ORDERING')
    g = generate(exam['id'], topics, authority=exam.get('authorityName', ''), exam_label=exam.get('title', ''),
                 gateway=ctx.hooks.claude())
    return JobOutcome('SUCCEEDED', result=g.as_dict(), audit={'generatedBy': g.generated_by})


# ====================================================================================== answer
def answer_question(ctx: JobContext) -> JobOutcome:
    """A candidate's question, answered only from the selected exam's own record."""
    inp, hooks = ctx.job.input, ctx.hooks
    exam = hooks.exam_store.get(inp['examId'])
    if exam is None:
        return JobOutcome('FAILED', error_category='EXAM_NOT_FOUND', error_message='No such exam.')
    sheet = build_fact_sheet(exam, inp['question'])
    ctx.stage('ASKING')
    res = hooks.claude().run(Operation.ANSWER_QUESTION, {
        'exam_title': sheet.title, 'authority': sheet.authority,
        'facts': [f.as_prompt() for f in sheet.facts], 'question': inp['question'], 'history': inp['history']})
    if not res.ok:
        return _failed_result(res)
    problems = validate_answer(res.output, sheet, inp['question'], hooks.exam_store.other_exam_names(inp['examId']))
    if problems:
        return JobOutcome('FAILED', error_category='ANSWER_REJECTED',
                          error_message='The answer could not be checked against the exam record, so it was not used.',
                          template_version=res.template_version, audit={'problems': problems[:6]})
    out = res.output
    cited = citations(out, sheet) if out['basis'] == 'VERIFIED_DATA' else []
    # `basis` is what Claude says it answered from; `verification` is what GovOS can prove: VERIFIED only
    # when every fact the answer cites is officially verified and states what it is cited for. A fact with
    # no source, one under verification, or one whose quoted words do not state it never makes an answer
    # "verified" -- the badge used to follow `basis` alone.
    return JobOutcome('SUCCEEDED', result={
        'answer': out['answer'], 'basis': out['basis'], 'uncertainty': out['uncertainty'],
        'verification': answer_verification(cited),
        'navigateTo': out['navigate_to'], 'followUp': out['follow_up'], 'citations': cited,
        'label': LABEL_ASSISTED, 'engine': ENGINE, 'examId': inp['examId'],
        'factsSupplied': len(sheet.facts), 'factsTruncated': sheet.truncated},
        template_version=res.template_version, audit={'inputFingerprint': res.input_fingerprint})


# ===================================================================================== practice
_OFFICIAL_CLAIM = re.compile(
    r'previous[- ]year|past[- ]paper|\bPYQ\b|question paper|actual exam|as asked in|was asked in|'
    r'official (?:question|paper|exam|previous|pyq)|\b(?:SSC|UPSC|IBPS|APPSC|TGPSC|RBI)\b[^.?]{0,24}\b20\d\d\b|'
    # Any "<year> paper/exam/shift" or "paper/exam of <year>", whichever authority it names: a question that
    # dates itself to an examination is claiming a provenance GovOS-authored practice does not have.
    r'\b(?:19|20)\d\d\s+(?:question\s+)?(?:paper|exam(?:ination)?|shift|tier\b|pyq)|'
    r'\b(?:paper|exam(?:ination)?|shift)\s+(?:of\s+|in\s+|held\s+in\s+)?(?:19|20)\d\d\b|'
    r'https?://|www\.', re.I)

#: Wording that shows the writer changed their mind inside the explanation. Found with the real CLI: a
#: question keyed C whose explanation worked out A and then said "Correction: ... option A". An answer key
#: that contradicts its own explanation is a wrong key, so such a question is never served.
_SELF_CORRECTION = re.compile(
    r'\bcorrection\b|\bcorrected\b|\bwait[,.!:]|\boops\b|\bmy mistake\b|\blet me (?:re|try|check)|'
    r're-?calculat|re-?comput|\bon second thought\b|\bactually,? (?:the|it|this)\b', re.I)


def validate_practice(questions: list, topic: str, allowed: list, count: int) -> tuple[list, list]:
    """(accepted questions, reasons for each dropped one). Every question must be on the requested,
    verified topic, have four distinct options and claim no official origin."""
    accepted, dropped, seen = [], [], set()
    for i, q in enumerate(questions[:count]):
        why = None
        index = q.get('correct_index')
        stem, explanation = _norm(str(q.get('stem') or '')), _norm(str(q.get('explanation') or ''))
        if q.get('topic') != topic or topic not in allowed:
            why = 'not on the requested verified syllabus topic'
        elif len({_norm(o).lower() for o in q.get('options', [])}) != 4 or not all(_norm(o) for o in q['options']):
            why = 'options are not four distinct answers'
        elif isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= 3:
            why = 'there is no single correct option'
        elif _OFFICIAL_CLAIM.search(' '.join([stem, explanation] + list(q['options']))):
            why = 'claims or implies an official origin, or contains a link'
        elif not stem or not explanation:
            why = 'missing stem or explanation'
        elif _SELF_CORRECTION.search(explanation):
            why = 'the explanation corrects itself, so its answer key cannot be trusted'
        elif stem.lower() in seen:
            why = 'duplicate of an earlier question'
        if why:
            dropped.append(f'question {i + 1}: {why}')
        else:
            seen.add(stem.lower())
            accepted.append(q)
    return accepted, dropped


def generate_practice(ctx: JobContext) -> JobOutcome:
    inp, hooks = ctx.job.input, ctx.hooks
    exam = hooks.exam_store.get(inp['examId'])
    if exam is None:
        return JobOutcome('FAILED', error_category='EXAM_NOT_FOUND', error_message='No such exam.')
    allowed = syllabus_topics(exam)
    if not allowed:
        return JobOutcome('FAILED', error_category='NO_VERIFIED_SYLLABUS',
                          error_message='This exam has no verified syllabus on record to write practice questions from.')
    if inp['topic'] not in allowed:
        return JobOutcome('FAILED', error_category='TOPIC_NOT_IN_SYLLABUS',
                          error_message='That topic is not in this exam\'s verified syllabus.')
    stage = (exam.get('stages') or [{}])[0]
    note = '; '.join(str(x) for x in (stage.get('stageName'), stage.get('mode')) if x)
    ctx.stage('WRITING')
    res = hooks.claude().run(Operation.GENERATE_PRACTICE, {
        'exam_title': exam.get('title', ''), 'topic': inp['topic'], 'allowed_topics': allowed,
        'count': inp['count'], 'difficulty': inp['difficulty'], 'pattern_note': note})
    if not res.ok:
        return _failed_result(res)
    accepted, dropped = validate_practice(res.output.get('questions', []), inp['topic'], allowed, inp['count'])
    if not accepted:
        return JobOutcome('FAILED', error_category='PRACTICE_REJECTED',
                          error_message='No question passed the checks, so none was used.',
                          template_version=res.template_version, audit={'dropped': dropped})
    if ctx.cancelled:
        return JobOutcome('CANCELLED')

    # An answer key written by the same call that wrote the question is only a claim. A second, independent
    # call solves each question WITHOUT seeing the key, and a question is kept only where it reaches the same
    # option. If that check cannot run, nothing is served: an unchecked key is not offered as practice.
    ctx.stage('CHECKING')
    solved = hooks.claude().run(Operation.SOLVE_PRACTICE, {
        'questions': [{'stem': q['stem'], 'options': q['options']} for q in accepted]})
    if not solved.ok:
        return _failed_result(solved)
    choices = {s.get('index'): s.get('choice') for s in solved.output.get('solutions', []) if isinstance(s, dict)}
    kept = []
    for i, q in enumerate(accepted):
        got = choices.get(i, -1)
        if got == q['correct_index']:
            kept.append(q)
        else:
            dropped.append(f'"{_norm(q["stem"])[:48]}": an independent solve '
                           + ('could not settle on one answer' if got == -1 else 'chose a different option')
                           + ', so the answer key was not trusted')
    if not kept:
        return JobOutcome('FAILED', error_category='PRACTICE_REJECTED',
                          error_message='No question passed the checks, so none was used.',
                          template_version=res.template_version, audit={'dropped': dropped})
    labelled = [{**q, 'source': LABEL_GENERATED, 'generatedBy': 'CLAUDE_CLI', 'officialSource': False,
                 'label': PRACTICE_LABEL, 'answerCheck': ANSWER_CHECK} for q in kept]
    return JobOutcome('SUCCEEDED', result={
        'questions': labelled, 'dropped': dropped, 'examId': inp['examId'], 'topic': inp['topic'],
        'source': LABEL_GENERATED, 'generatedBy': 'CLAUDE_CLI', 'officialSource': False, 'label': PRACTICE_LABEL,
        'answerCheck': ANSWER_CHECK},
        template_version=res.template_version,
        audit={'inputFingerprint': res.input_fingerprint, 'solveTemplate': solved.template_version})


# ===================================================================================== registry
def _build_exclusive(inp: dict, exam_id: str, cycle: str) -> str:
    return 'build:' + re.sub(r'[^a-z0-9]+', '-', inp['query'].lower()).strip('-') + ':' + inp['year']


def default_specs() -> dict:
    """The allow-listed job operations. Nothing outside this dict can be queued."""
    return {
        'DISCOVER_SOURCES': JobSpec('DISCOVER_SOURCES', discover_sources, norm_discover, max_retries=2),
        'EXTRACT_FIELDS': JobSpec('EXTRACT_FIELDS', extract_fields, norm_extract, max_retries=1),
        'BUILD_EXAM': JobSpec('BUILD_EXAM', build_exam_job, norm_build, max_retries=1, exclusive=_build_exclusive),
        # One walk of an authority at a time per exam: a second would only fetch the same pages again.
        'DISCOVER_AUTHORITY': JobSpec('DISCOVER_AUTHORITY', discover_authority_job, norm_authority, max_retries=1,
                                      exclusive=lambda inp, exam_id, cycle: 'authority:' + inp['examId']),
        'ORDER_ROADMAP': JobSpec('ORDER_ROADMAP', order_roadmap, norm_roadmap, max_retries=1),
        'ANSWER_QUESTION': JobSpec('ANSWER_QUESTION', answer_question, norm_answer, candidate=True, max_retries=0),
        'GENERATE_PRACTICE': JobSpec('GENERATE_PRACTICE', generate_practice, norm_practice, candidate=True,
                                     max_retries=0),
    }
