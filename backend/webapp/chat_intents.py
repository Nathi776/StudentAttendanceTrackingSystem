"""Centralized intent detection for the chatbot.

This module keeps the natural language matching rules in one place so new
intents and synonyms can be added without editing the response logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Iterable


LOW_CONFIDENCE_REPLY = "I am not sure what you mean. Could you rephrase your question?"


@dataclass(frozen=True)
class IntentDefinition:
    name: str
    roles: frozenset[str]
    examples: tuple[str, ...]
    keywords: tuple[str, ...]
    priority: int = 0


@dataclass(frozen=True)
class IntentMatch:
    intent: str | None
    confidence: float
    role: str


ROLE_ALIASES = {
    'student_profile': 'student',
    'lecturer_profile': 'lecturer',
}

STOPWORDS = {
    'a', 'an', 'and', 'are', 'be', 'can', 'for', 'from', 'give', 'got', 'have', 'how', 'i', 'in', 'is', 'it',
    'me', 'my', 'of', 'on', 'or', 'please', 'show', 'tell', 'the', 'this', 'to', 'was', 'what', 'when', 'who',
    'whos', 'whats', 'which', 'with', 'you', 'your', 'do', 'did', 'does', 'am', 'there', 'any', 'if', 'up',
    'today', 'now', 'that', 'this', 'class', 'session', 'course', 'courses', 'subject', 'subjects', 'module',
    'modules', 'lecture', 'lectures', 'student', 'students', 'teacher', 'lecturer', 'lecturers', 'write', 'wrote',
    'writing', 'can', 'could', 'would', 'should', 'qualify', 'qualification', 'eligible', 'eligibility', 'count',
    'counts', 'number', 'many', 'most', 'more', 'less', 'looking', 'looking', 'like', 'please', 'kindly',
}

SYNONYM_REPLACEMENTS = (
    (r"\bwhats\b", 'what is'),
    (r"\bwhos\b", 'who is'),
    (r"\bmaths\b", 'math'),
    (r"\bmath\b", 'math'),
    (r"\blectures?\b", 'lecture'),
    (r"\bteacher\b", 'lecturer'),
    (r"\binstructor\b", 'lecturer'),
    (r"\btimetable\b", 'timetable'),
    (r"\btime table\b", 'timetable'),
    (r"\battendance rate\b", 'attendance percentage'),
    (r"\battendance percent\b", 'attendance percentage'),
    (r"\babsences?\b", 'absence'),
    (r"\bmissed classes?\b", 'missed class'),
    (r"\bqualified\b", 'qualify'),
    (r"\beligible\b", 'qualify'),
    (r"\bcan i write exams?\b", 'qualify for exam'),
)


INTENTS: tuple[IntentDefinition, ...] = (
    IntentDefinition(
        name='next_session',
        roles=frozenset({'student'}),
        examples=(
            'what is my next session',
            'when is my next class',
            'what is my next lecture',
            'which session comes next',
            'do i have any classes today',
            'what class do i attend next',
        ),
        keywords=('next', 'upcoming', 'coming', 'session', 'class', 'lecture', 'today'),
        priority=100,
    ),
    IntentDefinition(
        name='absent_count',
        roles=frozenset({'student'}),
        examples=(
            'how many times was i absent',
            'how many absences do i have',
            'how often did i miss class',
            'what is my absence count',
            'how many classes have i missed',
        ),
        keywords=('absent', 'absence', 'missed', 'miss', 'count', 'missed class'),
    ),
    IntentDefinition(
        name='present_count',
        roles=frozenset({'student'}),
        examples=(
            'how many times was i present',
            'how many classes did i attend',
            'what is my attendance count',
            'how many attendances do i have',
        ),
        keywords=('present', 'attend', 'attendance', 'count'),
    ),
    IntentDefinition(
        name='late_count',
        roles=frozenset({'student'}),
        examples=(
            'how many times was i late',
            'how often was i late',
            'what is my late count',
            'do i have any late arrivals',
        ),
        keywords=('late', 'arrivals', 'late count'),
    ),
    IntentDefinition(
        name='attendance_percentage',
        roles=frozenset({'student'}),
        examples=(
            'what is my attendance percentage',
            'what is my attendance rate',
            'how is my attendance looking',
            'show my attendance stats',
            'what percentage attendance do i have',
        ),
        keywords=('attendance', 'percentage', 'rate', 'stats'),
    ),
    IntentDefinition(
        name='attendance_summary',
        roles=frozenset({'student'}),
        examples=(
            'give me my attendance summary',
            'show my attendance record',
            'summarize my attendance',
            'how have i been attending classes',
        ),
        keywords=('summary', 'record', 'summarize', 'attendance'),
    ),
    IntentDefinition(
        name='exam_qualification_count',
        roles=frozenset({'student', 'lecturer'}),
        examples=(
            'how many modules do i qualify for exam',
            'how many modules can i write exam in',
            'do i qualify for exams',
            'am i qualified for exams',
            'can i write exams',
            'how many students qualify for exam',
            'how many can write exams',
            'number of students eligible for exams',
        ),
        keywords=('exam', 'qualify', 'eligible', 'write', 'write exam', 'write exams'),
        priority=40,
    ),
    IntentDefinition(
        name='attendance_by_module',
        roles=frozenset({'student'}),
        examples=(
            'show my attendance by module',
            'show attendance by module',
            'break down my attendance by module',
            'attendance per module',
            'module attendance',
        ),
        keywords=('attendance', 'module', 'breakdown', 'per module'),
        priority=20,
    ),
    IntentDefinition(
        name='module_lowest_attendance',
        roles=frozenset({'student', 'lecturer'}),
        examples=(
            'which module has the lowest attendance',
            'which subject do i need to improve attendance in',
            'which module should i improve attendance in',
            'where is my attendance lowest',
        ),
        keywords=('lowest', 'improve', 'attendance', 'module', 'subject'),
        priority=35,
    ),
    IntentDefinition(
        name='module_highest_attendance',
        roles=frozenset({'student', 'lecturer'}),
        examples=(
            'which module has the highest attendance',
            'which module is my best attendance in',
            'where is my attendance highest',
            'which subject has the best attendance',
        ),
        keywords=('highest', 'best', 'attendance', 'module', 'subject'),
        priority=34,
    ),
    IntentDefinition(
        name='attendance_this_month',
        roles=frozenset({'student'}),
        examples=(
            'how many classes have i attended this month',
            'how many classes did i attend this month',
            'attendance this month',
            'classes attended this month',
        ),
        keywords=('month', 'attended', 'attendance', 'classes'),
        priority=22,
    ),
    IntentDefinition(
        name='missed_classes_this_week',
        roles=frozenset({'student'}),
        examples=(
            'what classes did i miss this week',
            'which classes did i miss this week',
            'missed classes this week',
            'what did i miss this week',
        ),
        keywords=('week', 'missed', 'miss', 'classes'),
        priority=23,
    ),
    IntentDefinition(
        name='enrolled_courses',
        roles=frozenset({'student'}),
        examples=(
            'what courses am i enrolled in',
            'which modules am i taking',
            'what subjects am i registered for',
            'show my courses',
        ),
        keywords=('enrolled', 'courses', 'modules', 'subjects', 'registered'),
    ),
    IntentDefinition(
        name='lecturer_for_course',
        roles=frozenset({'student'}),
        examples=(
            'who teaches programming',
            'who is the lecturer for mathematics',
            'who teaches this module',
            'who is responsible for this course',
        ),
        keywords=('who', 'teaches', 'lecturer', 'responsible', 'course', 'module'),
        priority=10,
    ),
    IntentDefinition(
        name='attendance_on_specific_date',
        roles=frozenset({'student'}),
        examples=(
            'was i present on 9 may',
            'did i attend class on 9 may',
            'was i absent on 9 may',
            'what was my attendance status on 9 may',
        ),
        keywords=('present', 'absent', 'attend', 'attendance', 'status', 'date', 'on'),
        priority=90,
    ),
    IntentDefinition(
        name='students_most_absent',
        roles=frozenset({'lecturer'}),
        examples=(
            'which students are absent most often',
            'show students with the highest absences',
            'who misses the most classes',
            'list the most absent students',
        ),
        keywords=('absent', 'absence', 'most', 'highest', 'misses'),
    ),
    IntentDefinition(
        name='students_qualify_exam',
        roles=frozenset({'lecturer'}),
        examples=(
            'which students qualify for exams',
            'show exam eligible students',
            'who can write exams',
            'list students eligible for exams',
        ),
        keywords=('students', 'qualify', 'exam', 'eligible', 'write'),
        priority=30,
    ),
    IntentDefinition(
        name='todays_attendance_summary',
        roles=frozenset({'lecturer'}),
        examples=(
            'show todays attendance summary',
            'show today attendance summary',
            'what is todays attendance summary',
            'attendance today',
            'today attendance stats',
        ),
        keywords=('today', 'attendance', 'summary', 'stats'),
        priority=28,
    ),
    IntentDefinition(
        name='students_at_risk_exam',
        roles=frozenset({'lecturer'}),
        examples=(
            'which students are at risk of not qualifying',
            'which students may not qualify for exams',
            'show students at risk of failing attendance',
            'who is at risk of not qualifying',
        ),
        keywords=('risk', 'qualify', 'attendance', 'students', 'fail'),
        priority=29,
    ),
    IntentDefinition(
        name='absent_today_count',
        roles=frozenset({'lecturer'}),
        examples=(
            'how many students were absent today',
            'number of students absent today',
            'how many were absent today',
            'students absent today',
        ),
        keywords=('absent', 'today', 'students', 'count'),
        priority=27,
    ),
    IntentDefinition(
        name='attendance_statistics_for_module',
        roles=frozenset({'lecturer'}),
        examples=(
            'show attendance statistics for programming',
            'attendance statistics for programming',
            'show attendance stats for mathematics',
            'attendance stats for this module',
        ),
        keywords=('statistics', 'stats', 'attendance', 'module', 'subject'),
        priority=33,
    ),
    IntentDefinition(
        name='best_attendance_class',
        roles=frozenset({'lecturer'}),
        examples=(
            'which class has the best attendance',
            'what class has the highest attendance',
            'best attended class',
            'which session has the best attendance',
        ),
        keywords=('best', 'highest', 'attendance', 'class', 'session'),
        priority=26,
    ),
    IntentDefinition(
        name='taught_modules',
        roles=frozenset({'lecturer'}),
        examples=(
            'what modules do i teach',
            'which modules am i teaching',
            'show my taught modules',
            'what courses do i teach',
            'list the modules i handle',
        ),
        keywords=('teach', 'teaching', 'module', 'modules', 'course', 'courses', 'handle'),
    ),
    IntentDefinition(
        name='greeting',
        roles=frozenset({'student', 'lecturer'}),
        examples=('hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'),
        keywords=('hi', 'hello', 'hey', 'morning', 'afternoon', 'evening'),
        priority=200,
    ),
)


def normalize_text(message: str) -> str:
    text = (message or '').lower().strip()
    text = text.replace("'", '')
    for pattern, replacement in SYNONYM_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(message: str) -> list[str]:
    return [token for token in normalize_text(message).split() if token]


def _content_tokens(tokens: Iterable[str]) -> list[str]:
    return [token for token in tokens if token not in STOPWORDS]


def _contains_phrase(normalized_message: str, normalized_phrase: str) -> bool:
    if not normalized_message or not normalized_phrase:
        return False

    phrase_tokens = [token for token in normalized_phrase.split() if token]
    if not phrase_tokens:
        return False

    message_tokens = normalized_message.split()
    if len(phrase_tokens) == 1:
        return phrase_tokens[0] in message_tokens

    pattern = r'(?<!\w)' + re.escape(normalized_phrase) + r'(?!\w)'
    return re.search(pattern, normalized_message) is not None


def _phrase_score(normalized_message: str, normalized_example: str) -> float:
    if not normalized_message or not normalized_example:
        return 0.0
    if normalized_message == normalized_example:
        return 1.0
    if _contains_phrase(normalized_message, normalized_example):
        return 0.96
    ratio = SequenceMatcher(None, normalized_message, normalized_example).ratio()
    message_tokens = set(_content_tokens(normalized_message.split()))
    example_tokens = set(_content_tokens(normalized_example.split()))
    if message_tokens and example_tokens:
        overlap = len(message_tokens & example_tokens) / len(example_tokens)
    else:
        overlap = 0.0
    return max(ratio, overlap)


def _keyword_score(normalized_message: str, keywords: tuple[str, ...]) -> float:
    if not keywords:
        return 0.0

    hits = 0.0
    possible = 0.0
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue
        possible += 1.0
        if _contains_phrase(normalized_message, normalized_keyword):
            hits += 1.0
        else:
            keyword_tokens = [token for token in normalized_keyword.split() if token not in STOPWORDS]
            message_tokens = set(_content_tokens(normalized_message.split()))
            if keyword_tokens and all(token in message_tokens for token in keyword_tokens):
                hits += 0.85

    if possible == 0:
        return 0.0
    return hits / possible


def _intent_specific_bonus(intent: IntentDefinition, normalized_message: str, role: str) -> float:
    bonus = 0.0
    if intent.name == 'attendance_on_specific_date' and re.search(r'\b\d{1,2}\b', normalized_message):
        bonus += 0.18
    if intent.name == 'greeting' and len(normalized_message.split()) <= 3:
        bonus += 0.1
    if intent.name == 'lecturer_for_course' and role == 'student':
        if any(token in normalized_message for token in ('who teaches', 'lecturer for', 'who is responsible')):
            bonus += 0.12
    if intent.name == 'students_qualify_exam' and role == 'lecturer':
        if 'students' in normalized_message and 'exam' in normalized_message:
            bonus += 0.08
    if intent.name == 'exam_qualification_count' and 'qualify' in normalized_message:
        bonus += 0.05
    return bonus


def score_intent(message: str, intent: IntentDefinition, role: str) -> float:
    normalized_message = normalize_text(message)
    if not normalized_message:
        return 0.0

    example_score = 0.0
    for example in intent.examples:
        score = _phrase_score(normalized_message, normalize_text(example))
        if score > example_score:
            example_score = score

    keyword_score = _keyword_score(normalized_message, intent.keywords)
    message_tokens = set(_content_tokens(tokenize(message)))
    intent_tokens = set(
        token
        for text in (*intent.examples, *intent.keywords)
        for token in _content_tokens(normalize_text(text).split())
    )
    token_overlap = 0.0
    if message_tokens and intent_tokens:
        token_overlap = len(message_tokens & intent_tokens) / len(intent_tokens)

    score = (0.52 * example_score) + (0.28 * keyword_score) + (0.20 * token_overlap)
    score += _intent_specific_bonus(intent, normalized_message, role)

    if intent.priority:
        score += intent.priority / 1000.0

    return min(score, 1.0)


def resolve_chat_intent(message: str, role: str) -> IntentMatch:
    normalized_role = ROLE_ALIASES.get((role or '').lower(), (role or '').lower())
    if normalized_role not in {'student', 'lecturer', 'anonymous'}:
        normalized_role = 'anonymous'

    best_intent = None
    best_score = 0.0
    for intent in INTENTS:
        if normalized_role not in intent.roles:
            continue
        score = score_intent(message, intent, normalized_role)
        if score > best_score or (score == best_score and best_intent and intent.priority > best_intent.priority):
            best_intent = intent
            best_score = score

    threshold = 0.48
    if best_intent is None or best_score < threshold:
        return IntentMatch(intent=None, confidence=best_score, role=normalized_role)

    return IntentMatch(intent=best_intent.name, confidence=best_score, role=normalized_role)
