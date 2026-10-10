"""
Milliy sertifikat formulalari: daraja, foiz, 1-fan / 2-fan ballari.

IMAGE_ROWS - tashkilotchining (ona tili) natijalar jadvalidan olingan haqiqiy
qatorlar: (yakuniy ball, foiz, daraja, 1-fan, 2-fan). Bizning formulalar
aynan shu qiymatlarni berishi kerak.
"""
import pytest

from app.services.rasch_service import (
    grade_for, percent_for, subject_points, round2,
    FAN1_MAX, FAN2_MAX, MAJBURIY_MAX,
)

IMAGE_ROWS = [
    (74.88, 100.0, "A+", 104.0, 74.0),
    (73.73, 100.0, "A+", 104.0, 74.0),
    (72.62, 100.0, "A+", 104.0, 74.0),
    (72.38, 100.0, "A+", 104.0, 74.0),
    (71.24, 100.0, "A+", 104.0, 74.0),
    (69.88, 100.0, "A", 104.0, 74.0),
    (69.28, 100.0, "A", 104.0, 74.0),
    (69.22, 100.0, "A", 104.0, 74.0),
    (68.77, 100.0, "A", 104.0, 74.0),
    (68.59, 100.0, "A", 104.0, 74.0),
    (67.92, 100.0, "A", 104.0, 74.0),
    (67.87, 100.0, "A", 104.0, 74.0),
    (67.67, 100.0, "A", 104.0, 74.0),
    (67.07, 100.0, "A", 104.0, 74.0),
    (66.91, 100.0, "A", 104.0, 74.0),
    (66.62, 100.0, "A", 104.0, 74.0),
    (66.6, 100.0, "A", 104.0, 74.0),
    (66.56, 100.0, "A", 104.0, 74.0),
    (66.44, 100.0, "A", 104.0, 74.0),
    (66.26, 100.0, "A", 104.0, 74.0),
    (66.13, 100.0, "A", 104.0, 74.0),
    (66.07, 100.0, "A", 104.0, 74.0),
    (65.97, 100.0, "A", 104.0, 74.0),
    (65.81, 100.0, "A", 104.0, 74.0),
    (65.64, 100.0, "A", 104.0, 74.0),
    (65.58, 100.0, "A", 104.0, 74.0),
    (65.56, 100.0, "A", 104.0, 74.0),
    (65.44, 100.0, "A", 104.0, 74.0),
    (65.27, 100.0, "A", 104.0, 74.0),
    (65.25, 100.0, "A", 104.0, 74.0),
    (64.73, 99.58, "B+", 103.61, 73.74),
    (64.69, 99.52, "B+", 103.55, 73.7),
    (64.17, 98.72, "B+", 102.81, 73.19),
    (64.1, 98.62, "B+", 102.72, 73.13),
]


@pytest.mark.parametrize("score,percent,grade,fan1,fan2", IMAGE_ROWS)
def test_image_rows_match(score, percent, grade, fan1, fan2):
    assert grade_for(score) == grade
    assert percent_for(score) == pytest.approx(percent, abs=1e-9)
    f1, f2 = subject_points(percent_for(score))
    assert f1 == pytest.approx(fan1, abs=1e-9)
    assert f2 == pytest.approx(fan2, abs=1e-9)


def _reference_grade(score):
    if score >= 70:
        return "A+"
    if score >= 65:
        return "A"
    if score >= 60:
        return "B+"
    if score >= 55:
        return "B"
    if score >= 50:
        return "C+"
    if score >= 46:
        return "C"
    return None


@pytest.mark.parametrize("score", [round(i * 0.25, 2) for i in range(0, 301)])
def test_grade_thresholds(score):
    assert grade_for(score) == _reference_grade(score)


@pytest.mark.parametrize("score", [45.99, 46.0, 49.99, 50.0, 54.99, 55.0, 59.99, 60.0,
                                   64.99, 65.0, 69.99, 70.0, 75.0])
def test_grade_exact_boundaries(score):
    assert grade_for(score) == _reference_grade(score)


@pytest.mark.parametrize("score", [round(46 + i * 0.1, 1) for i in range(0, 191)])
def test_percent_and_subject_points(score):
    percent = percent_for(score)
    assert percent is not None
    if score >= 65:
        assert percent == 100.0
    else:
        assert percent == round2(score / 65 * 100)
        assert 70.0 <= percent < 100.0
    f1, f2 = subject_points(percent)
    assert f1 == round2(percent / 100 * FAN1_MAX + MAJBURIY_MAX)
    assert f2 == round2(percent / 100 * FAN2_MAX + MAJBURIY_MAX)
    assert MAJBURIY_MAX < f2 < f1 <= FAN1_MAX + MAJBURIY_MAX


@pytest.mark.parametrize("score", [0.0, 10.0, 30.0, 45.0, 45.99])
def test_no_certificate_below_46(score):
    assert grade_for(score) is None
    assert percent_for(score) is None
    assert subject_points(None) == (None, None)


@pytest.mark.parametrize("value,expected", [
    (0.005, 0.01), (0.015, 0.02), (1.005, 1.01), (2.675, 2.68), (99.585, 99.59),
    (64.725, 64.73), (73.6976, 73.7), (102.8096, 102.81), (-1.005, -1.01), (74.875, 74.88),
])
def test_round_half_up(value, expected):
    assert round2(value) == expected
