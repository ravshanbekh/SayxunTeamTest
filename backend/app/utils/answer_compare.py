"""
Answer comparison utilities for grading written answers.
Handles normalization, degree/radian equivalence, and LaTeX variations.
"""
import re


# Degree-radian equivalence table (15° and 18° increments)
DEGREE_TO_RADIAN = {
    '0': '0',
    '15': '\\frac{\\pi}{12}',
    '18': '\\frac{\\pi}{10}',
    '30': '\\frac{\\pi}{6}',
    '36': '\\frac{\\pi}{5}',
    '45': '\\frac{\\pi}{4}',
    '54': '\\frac{3\\pi}{10}',
    '60': '\\frac{\\pi}{3}',
    '72': '\\frac{2\\pi}{5}',
    '75': '\\frac{5\\pi}{12}',
    '90': '\\frac{\\pi}{2}',
    '105': '\\frac{7\\pi}{12}',
    '108': '\\frac{3\\pi}{5}',
    '120': '\\frac{2\\pi}{3}',
    '126': '\\frac{7\\pi}{10}',
    '135': '\\frac{3\\pi}{4}',
    '144': '\\frac{4\\pi}{5}',
    '150': '\\frac{5\\pi}{6}',
    '162': '\\frac{9\\pi}{10}',
    '165': '\\frac{11\\pi}{12}',
    '180': '\\pi',
    '195': '\\frac{13\\pi}{12}',
    '198': '\\frac{11\\pi}{10}',
    '210': '\\frac{7\\pi}{6}',
    '216': '\\frac{6\\pi}{5}',
    '225': '\\frac{5\\pi}{4}',
    '234': '\\frac{13\\pi}{10}',
    '240': '\\frac{4\\pi}{3}',
    '252': '\\frac{7\\pi}{5}',
    '255': '\\frac{17\\pi}{12}',
    '270': '\\frac{3\\pi}{2}',
    '285': '\\frac{19\\pi}{12}',
    '288': '\\frac{8\\pi}{5}',
    '300': '\\frac{5\\pi}{3}',
    '306': '\\frac{17\\pi}{10}',
    '315': '\\frac{7\\pi}{4}',
    '324': '\\frac{9\\pi}{5}',
    '330': '\\frac{11\\pi}{6}',
    '342': '\\frac{19\\pi}{10}',
    '345': '\\frac{23\\pi}{12}',
    '360': '2\\pi',
}


def normalize(s):
    """Normalize answer string for comparison."""
    if not s:
        return ''
    s = str(s).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('\\left(', '(').replace('\\right)', ')')
    s = s.replace('\\left[', '[').replace('\\right]', ']')
    s = s.replace('\\cdot', '*').replace('\\times', '*')
    return s


def _extract_degrees(s):
    """Extract degree value from strings like '90°', '90\\degree', '90^\\circ'."""
    m = re.match(r'^(-?\d+(?:\.\d+)?)\s*(?:°|\\degree|\\circ|\^\\circ|\^\{\\circ\})\s*$', s)
    return m.group(1) if m else None


def _normalize_radian(s):
    """Normalize radian expression for comparison."""
    s = s.replace(' ', '')
    s = re.sub(r'\\frac\{?\\pi\}?\{?(\d+)\}?', r'\\frac{\\pi}{\1}', s)
    s = re.sub(r'\\frac\{?(\d+)\\pi\}?\{?(\d+)\}?', r'\\frac{\1\\pi}{\2}', s)
    s = re.sub(r'\\pi\s*/\s*(\d+)', r'\\frac{\\pi}{\1}', s)
    s = re.sub(r'(\d+)\\pi\s*/\s*(\d+)', r'\\frac{\1\\pi}{\2}', s)
    return s


def answers_match(student, correct):
    """
    Check if answers match, including degree/radian equivalence.
    Both student and correct should already be normalized.
    """
    if not student or not correct:
        return False
    # Direct match
    if student == correct or correct in student:
        return True
    # Case 1: student writes degrees, correct is radian
    deg = _extract_degrees(student)
    if deg and deg in DEGREE_TO_RADIAN:
        equiv = _normalize_radian(DEGREE_TO_RADIAN[deg])
        if equiv == _normalize_radian(correct):
            return True
    # Case 2: correct is degrees, student writes radian
    deg = _extract_degrees(correct)
    if deg and deg in DEGREE_TO_RADIAN:
        equiv = _normalize_radian(DEGREE_TO_RADIAN[deg])
        if equiv == _normalize_radian(student):
            return True
    return False
