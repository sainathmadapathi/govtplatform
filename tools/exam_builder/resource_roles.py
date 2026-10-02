"""What role a resource plays, read deterministically from its own words and where it was found.

A PDF is not a resource because it is a PDF, and a YouTube link is not a lesson because it is on
YouTube. The role is what the content is *for*: a notification, a question paper, a registration
portal, study material, a lecture. That decides which of the 17 candidate sections it belongs in,
and only learning material belongs in Resources.

Two classifiers, one vocabulary (discover.DocKind):

  * `classify_link` -- for a link found during discovery: its anchor text, its URL, the heading it
    was listed under, and the role of the repository it sits in. The existing `classify_kind` runs
    first, so an official document is read exactly as exam discovery reads it.
  * `classify_resource_item` -- for a resource card already in an exam record (title, subject,
    type, format, tag). The frontend has the same function (`resourceRoleOf` in ui.tsx); both are
    held to one table of cases (resource_role_cases.json), so they cannot drift apart.

Claude is not used here. Where these rules cannot tell, the role is UNKNOWN, and
authority_discovery may ask Claude to classify a batch of such links -- whose answer can only
name a role from this vocabulary, never a source class.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from .discover import DocKind, classify_kind
from .source_graph import NodeType
from .source_trust import is_social, is_video

#: Roles whose content is learning material. Only these belong in the Resources section.
LEARNING_ROLES = frozenset({DocKind.STUDY_MATERIAL, DocKind.LECTURE_VIDEO, DocKind.PRACTICE_TOOL})

#: Where each role is shown -- the one placement model: the candidate pages (ui.tsx
#: `RESOURCE_SECTION`) mirror it, and resource_role_cases.json pins the two together. None: never
#: shown as a resource (a lead, or something unclassified).
SECTION_FOR_ROLE = {
    DocKind.NOTIFICATION: 'OFFICIAL_LINKS', DocKind.EXAM_PAGE: 'OFFICIAL_LINKS', DocKind.CORRIGENDUM: 'CORRIGENDA',
    DocKind.SYLLABUS: 'SYLLABUS', DocKind.EXAM_PATTERN: 'PATTERN', DocKind.QUESTION_PAPER: 'PRACTICE',
    DocKind.ANSWER_KEY: 'PRACTICE', DocKind.ADMIT_CARD: 'ADMIT_CARD', DocKind.RESULT: 'RESULTS',
    DocKind.CUTOFF: 'CUTOFFS', DocKind.CALENDAR: 'DATES', DocKind.APPLICATION_PORTAL: 'APPLICATION',
    DocKind.OTR_PORTAL: 'APPLICATION', DocKind.APPLICATION_GUIDE: 'APPLICATION', DocKind.EXAM_GUIDE: 'OVERVIEW',
    DocKind.EXAM_DAY_INSTRUCTIONS: 'EXAM_DAY', DocKind.OFFICIAL_PORTAL: 'OFFICIAL_LINKS',
    DocKind.STUDY_MATERIAL: 'RESOURCES', DocKind.LECTURE_VIDEO: 'RESOURCES', DocKind.PRACTICE_TOOL: 'RESOURCES',
    DocKind.DISCOVERY_SIGNAL: None, DocKind.UNKNOWN: None,
}


def is_learning(role: DocKind) -> bool:
    return role in LEARNING_ROLES


_DOC_EXT = re.compile(r'\.(pdf|docx?|xlsx?|pptx?|zip|rar|odt|ods)$', re.I)

#: Ordered rules that run *before* classify_kind, because its vocabulary would read them as
#: something broader ("one time registration" is a portal of its own; "how to apply online" is
#: guidance, not the application portal).
_EARLY: list[tuple[DocKind, re.Pattern]] = [
    (DocKind.OTR_PORTAL, re.compile(r'one[\s-]*time[\s-]*registration|\botr\b', re.I)),
    (DocKind.APPLICATION_GUIDE, re.compile(
        r'how\s+to\s+(apply|fill|register|upload|pay)|user\s*(guide|manual)|instructions?\s+(for|to)\s+(fill|appl|online|candidates\s+applying)|'
        r'step[\s-]+by[\s-]+step|walk\s*-?\s*through|guidelines?\s+for\s+(appl|fill|online)|application\s+(guide|instructions)', re.I)),
    (DocKind.EXAM_DAY_INSTRUCTIONS, re.compile(
        r'instructions?\s+to\s+(the\s+)?candidates|exam(ination)?[\s-]+day|do\'?s\s+(and|&)\s+don\'?ts|prohibited\s+items|'
        r'reporting\s+time|important\s+instructions', re.I)),
]

#: An authority's "Online Mock Exam" is its exam vendor's practice interface. Read only where the link
#: names no document kind ("Notification for Mock Test schedule" is a notice); read from the heading it
#: sat under instead, it once came out a notification.
_PRACTICE_TOOL = re.compile(r'\bmock\s+(tests?|exams?|examination)\b|\bpractice\s+tests?\b', re.I)

#: Read *after* classify_kind, only when it found nothing.
_LATE: list[tuple[DocKind, re.Pattern]] = [
    # Learning roles are the only ones that reach Resources, so their cues are phrases, never a
    # lone word: "Backward Classes" is a caste category, "Notes" heads a notification's fine print,
    # and "Courses" is a qualification. Each of those once read as study material on a live run.
    (DocKind.STUDY_MATERIAL, re.compile(
        r'study\s+(material|notes)|lecture\s+notes|text\s*books?|\be-?books?\b|reading\s+material|'
        r'reference\s+(books?|material)|\b(online|free|video|mooc)\s+courses?\b|\bmoocs?\b|tutorials?|'
        r'learning\s+(resources?|material)|practice\s+sets?', re.I)),
    (DocKind.LECTURE_VIDEO, re.compile(
        r'video\s+(lectures?|lessons?|classes)|lectures?\s+(series|videos?)|recorded\s+(lectures?|classes)|'
        r'online\s+classes|webinars?', re.I)),
    # Never the bare word "services": "GROUP-I SERVICES" is a recruitment, and reading it as a portal
    # once hid an exam's own notification from its exam (found on a live run).
    (DocKind.OFFICIAL_PORTAL, re.compile(
        r'candidate\s+services|know\s+your|download\s+(submitted\s+)?application|\blogin\b|\bportal\b', re.I)),
]

#: A page whose own name says it is a list of many resources of one role.
REPOSITORY_WORDS = re.compile(
    r'\b(old|previous|past)\s+(year\s+)?(question\s+)?papers\b|\barchives?\b|\bdownloads?\b|\brepository\b|'
    r'question\s+papers|answer\s+keys|\bresults\b|\bnotifications\b|\bsyllabus\b|\bcut\s*-?\s*offs?\b|'
    r'selection\s+lists?|\bkeys\b', re.I)

#: Words a link to a useful listing page carries. A link with none of these and no role is site
#: chrome (About us, RTI, Contact) and is counted, not followed.
HUB_WORDS = re.compile(
    r'notification|recruitment|examination|\bexams?\b|results?|\bkeys?\b|answer|question\s*papers?|\bpapers?\b|'
    r'previous|archive|download|syllabus|scheme|hall[\s-]*ticket|admit|\botr\b|registration|application|apply|'
    r'candidate|selection|announcement|what\'?s\s+new|\bnews\b|cut[\s-]*off|calendar|certificate|instructions?|'
    r'guidelines?|verification|interview|merit', re.I)


#: A notice headline rather than a navigation label: a reference number or a date in it.
_HEADLINE = re.compile(r'\b(no|dt|dtd|dated)\b[\s.:]*\d|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', re.I)
_CHANGES_A_DATE = re.compile(r'extension|extended|upto|up\s+to|re-?open|postpone|reschedul|revised', re.I)


def is_headline(text: str) -> bool:
    """A notice title (a sentence, or a reference number or date) rather than a menu label."""
    return len((text or '').split()) > 7 or bool(_HEADLINE.search(text or ''))


def video_kind(text: str) -> tuple[str, DocKind]:
    """(kind, role) of a video from its title and description. Order matters: a video titled
    "Result out — how to check" is news first and a lesson not at all."""
    t = text or ''
    if re.search(r'how\s+to\s+(apply|fill|register)|application\s+form|registration\s+process|\botr\b|one[\s-]*time[\s-]*registration|'
                 r'fill(ing)?\s+(the\s+)?(online\s+)?form|apply\s+online|step[\s-]+by[\s-]+step', t, re.I):
        return 'APPLICATION_WALKTHROUGH', DocKind.APPLICATION_GUIDE
    if re.search(r'\b(released?|out\s+now|is\s+out|declared|breaking|update|announced|notification\s+out|news)\b', t, re.I):
        return 'NEWS_UPDATE', DocKind.DISCOVERY_SIGNAL
    if re.search(r'exam\s+pattern|syllabus\s+(explained|analysis|breakdown)|selection\s+process|eligibility|strategy|'
                 r'exam\s+analysis|cut[\s-]*off\s+analysis|how\s+to\s+prepare|preparation\s+plan', t, re.I):
        return 'EXAM_EXPLANATION', DocKind.EXAM_GUIDE
    if re.search(r'\b(class|lecture|chapter|lesson|revision|marathon|series|concepts?|tricks?|practice|mcqs?|grammar|maths?|'
                 r'reasoning|\bgk\b|general\s+(awareness|studies)|polity|history|geography|economy|science|english|'
                 r'aptitude|vocabulary|current\s+affairs|batch|course|session|topic)\b', t, re.I):
        return 'STUDY_LECTURE', DocKind.LECTURE_VIDEO
    return 'OTHER', DocKind.UNKNOWN


def node_type_hint(url: str, role: DocKind) -> NodeType:
    path = urlparse(url or '').path
    if is_video(url):
        return NodeType.VIDEO
    if is_social(url):
        return NodeType.SOCIAL
    if _DOC_EXT.search(path or ''):
        return NodeType.DOCUMENT
    if role in (DocKind.OTR_PORTAL, DocKind.APPLICATION_PORTAL, DocKind.OFFICIAL_PORTAL):
        return NodeType.PORTAL
    return NodeType.LINK


def classify_link(text: str, url: str, *, context: str = '', parent_role: DocKind = DocKind.UNKNOWN,
                  parent_is_repository: bool = False) -> tuple[DocKind, NodeType, str, str]:
    """(role, node type, reason, video kind) for one discovered link."""
    text = ' '.join((text or '').split())
    if is_video(url):
        kind, role = video_kind(f'{text} {context}')
        return role, NodeType.VIDEO, f'a video; its title reads as {kind.lower().replace("_", " ")}', kind
    if is_social(url):
        return DocKind.DISCOVERY_SIGNAL, NodeType.SOCIAL, 'a social account or post', ''
    for role, pattern in _EARLY:
        if pattern.search(text):
            return role, node_type_hint(url, role), f'its text names {role.value.lower().replace("_", " ")}', ''
    role = classify_kind(text, url)
    if role is DocKind.APPLICATION_PORTAL and is_headline(text):
        # "... EXTENSION OF RECEIPT OF ONLINE APPLICATIONS UPTO 11/09/2026 - WEB NOTE" is a notice about
        # applications, not the place to apply.
        role = DocKind.CORRIGENDUM if _CHANGES_A_DATE.search(text) else DocKind.NOTIFICATION
        return role, node_type_hint(url, role), 'a notice headline about applications, not the portal itself', ''
    if role is not DocKind.UNKNOWN:
        return role, node_type_hint(url, role), 'its text or address names the document kind', ''
    if _PRACTICE_TOOL.search(text):
        return DocKind.PRACTICE_TOOL, node_type_hint(url, DocKind.PRACTICE_TOOL), 'its text names a mock test', ''
    if parent_is_repository and parent_role is not DocKind.UNKNOWN:
        # An item of a repository is what the repository holds, unless its own words say otherwise
        # strongly (above); the weak cues below are for loose links only.
        return (parent_role, node_type_hint(url, parent_role),
                f'an item of a repository of {parent_role.value.lower().replace("_", " ")}', '')
    for role, pattern in _LATE:
        if pattern.search(text):
            return role, node_type_hint(url, role), f'its text names {role.value.lower().replace("_", " ")}', ''
    if context:
        role = classify_kind(context, '')
        if role is not DocKind.UNKNOWN:
            return role, node_type_hint(url, role), f'listed under "{context[:60]}"', ''
    if parent_is_repository and parent_role is not DocKind.UNKNOWN:
        return (parent_role, node_type_hint(url, parent_role),
                f'an item of a repository of {parent_role.value.lower().replace("_", " ")}', '')
    return DocKind.UNKNOWN, node_type_hint(url, DocKind.UNKNOWN), 'its own words do not say what it is', ''


def is_hub_link(text: str, role: DocKind) -> bool:
    return role not in (DocKind.UNKNOWN, DocKind.DISCOVERY_SIGNAL) or bool(HUB_WORDS.search(text or ''))


# ========================================================== existing resource cards
#: Subjects the authored and machine records use for official documents and portals, not learning.
_OFFICIAL_SUBJECTS = {'official gazette', 'official portal', 'official notices', 'previous year papers'}

#: A learning reference that sits under an "Official Gazette" subject: the text of a law is study
#: material for a polity paper, a notification archive is not.
_STUDY_REFERENCE = re.compile(r'constitution|india\s+code|\bcentral\s+acts?\b|statutes?|bare\s+acts?|textbooks?|ncert', re.I)

_ITEM_RULES: list[tuple[DocKind, re.Pattern]] = [
    (DocKind.ANSWER_KEY, re.compile(r'answer\s*keys?|response\s+sheets?', re.I)),
    (DocKind.QUESTION_PAPER, re.compile(r'question\s+papers?|previous\s+year|\bpyqs?\b|question\s+booklet|official\s+question\s+paper', re.I)),
    (DocKind.CUTOFF, re.compile(r'cut[\s-]*off|qualifying\s+marks', re.I)),
    (DocKind.CALENDAR, re.compile(r'\bcalendar\b|exam(ination)?\s+schedule|time\s*table', re.I)),
    (DocKind.RESULT, re.compile(r'\bresults?\b|merit\s+list|selection\s+list|qualified\s+candidates', re.I)),
    (DocKind.ADMIT_CARD, re.compile(r'admit\s*card|hall\s*ticket|call\s*letter', re.I)),
    (DocKind.CORRIGENDUM, re.compile(r'corrigend|addend|re-?open|amendment|extension\s+of', re.I)),
    (DocKind.SYLLABUS, re.compile(r'syllabus|scheme\s+(of|and)\s+exam', re.I)),
    (DocKind.OTR_PORTAL, re.compile(r'one[\s-]*time[\s-]*registration|\botr\b', re.I)),
    (DocKind.APPLICATION_PORTAL, re.compile(r'application\s+portal|apply\s+(online|here)|online\s+application|\bapplication\b.*\bportal', re.I)),
    (DocKind.NOTIFICATION, re.compile(r'notification|notice|advertisement|press\s+note|recruitment', re.I)),
]


_APPLICATION_PORTAL = re.compile(r'application\s+portal|apply\s+(online|here)|online\s+application', re.I)
_ARCHIVE = re.compile(r'gazette|\barchive\b', re.I)
_PORTAL = re.compile(r'\bportal\b|official\s+(web)?site', re.I)


def classify_resource_item(item: dict) -> DocKind:
    """The role of a resource card as the records hold it. Mirrors `resourceRoleOf` in ui.tsx."""
    explicit = str(item.get('role') or '')
    if explicit in DocKind._value2member_map_:
        return DocKind(explicit)
    rtype = str(item.get('type') or '')
    fmt = str(item.get('resourceFormat') or '')
    subject = str(item.get('subject') or '').strip().lower()
    words = ' '.join(str(item.get(k) or '') for k in ('title', 'officialTag'))
    if rtype == 'THIRD_PARTY' or fmt == 'EXTERNAL_PAGE':
        # A third-party page is filed by what it carries; it is never official whatever it carries.
        for role, pattern in _ITEM_RULES:
            if pattern.search(words):
                return role
        return DocKind.QUESTION_PAPER if subject == 'previous year papers' else DocKind.STUDY_MATERIAL
    if rtype == 'VIDEO_LECTURE' or fmt in ('YOUTUBE_COURSE', 'YOUTUBE_CHANNEL'):
        kind, role = video_kind(words)
        return DocKind.LECTURE_VIDEO if role in (DocKind.UNKNOWN, DocKind.EXAM_GUIDE) else role
    if rtype == 'ONLINE_TOOL' or fmt == 'ONLINE_TOOL':
        return DocKind.PRACTICE_TOOL
    if subject == 'previous year papers':
        return DocKind.ANSWER_KEY if _ITEM_RULES[0][1].search(words) else DocKind.QUESTION_PAPER
    if subject in _OFFICIAL_SUBJECTS:
        if _STUDY_REFERENCE.search(words):
            return DocKind.STUDY_MATERIAL
        # A portal that takes applications names that first, even when it also serves admit cards.
        if _APPLICATION_PORTAL.search(words):
            return DocKind.APPLICATION_PORTAL
        # A card naming three or more kinds of document is a general portal, not one of them:
        # "Official Portal — Notices, Admit Cards, Answer Keys & Results".
        named = {role for role, pattern in _ITEM_RULES if pattern.search(words)}
        if len(named) >= 3 or (_PORTAL.search(words) and named <= {DocKind.NOTIFICATION}):
            return DocKind.OFFICIAL_PORTAL
        # A gazette or an archive holds every body's notifications, not this exam's.
        if _ARCHIVE.search(words) and not named & {DocKind.QUESTION_PAPER, DocKind.ANSWER_KEY}:
            return DocKind.OFFICIAL_PORTAL
        for role, pattern in _ITEM_RULES:
            if pattern.search(words):
                return role
        return DocKind.OFFICIAL_PORTAL
    # A learning subject. Still, an official document filed under one by mistake is not study material.
    for role, pattern in _ITEM_RULES[:2]:
        if pattern.search(words):
            return role
    return DocKind.STUDY_MATERIAL


def section_for(role: DocKind) -> Optional[str]:
    return SECTION_FOR_ROLE.get(role)
