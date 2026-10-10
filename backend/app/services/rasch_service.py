"""
Rasch modeli (1PL IRT) asosida milliy sertifikat uslubida ball hisoblash.

Bilim va malakalarni baholash agentligi (BMBA) metodikasi:
  1. Har bir topshiriq uchun javoblar 0/1 (dixotomik) ko'rinishda olinadi.
  2. Rasch modeli:  P(x=1) = exp(θ - b) / (1 + exp(θ - b))
     θ - talabgor qobiliyati, b - topshiriq qiyinligi (logit).
  3. Qobiliyat standartlashtiriladi:  Z = (θ - μ) / σ
  4. Standart ball:  T = 50 + 10·Z. Maksimal natija "shartli ravishda" 75 ball:
     A+ oralig'i rasmiy hujjatda "70 – 75 va undan yuqori" deb berilgan, ya'ni
     75 qat'iy chegara emas (matematikada 90.14 kabi sertifikatlar bor).
     Shu sababli ball sukut bo'yicha 75 da kesilmaydi (max_score bilan cheklash mumkin).
  5. Darajalar: A+ (70+), A (65-69.9), B+ (60-64.9), B (55-59.9),
     C+ (50-54.9), C (46-49.9). 46 dan past - sertifikat berilmaydi.
  6. OTMga kirishda: A+ va A - 100%, qolganlari ball/65 proporsional.
     1-fan maksimal 93 ball, 2-fan maksimal 63 ball; majburiy fan bo'yicha
     (10 savol x 1.1 = 11 ball) barcha darajalarda maksimal ball beriladi.

Baholash usuli:
  - Topshiriq qiyinliklari: shartli maksimal ehtimollik (CML) - Rasch
    modelining eng aniq (bias'siz) usuli. Faqat yetarli statistikalar
    (har bir savolga to'g'ri javoblar soni va xom ball taqsimoti) ishlatiladi.
  - Talabgor qobiliyati: Warm'ning vaznli ehtimollik bahosi (WLE). 0 va
    maksimal xom ball uchun ham chekli qiymat beradi.

Modul faqat standart kutubxonadan foydalanadi (numpy talab qilinmaydi).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Sequence
import math


# ---------------------------------------------------------------------------
# Milliy sertifikat konstantalari
# ---------------------------------------------------------------------------
T_MEAN = 50.0
T_SD = 10.0
NOMINAL_MAX_SCORE = 75.0  # shartli maksimal (kesilmaydi)
MIN_SCORE = 0.0

# A va A+ darajalar uchun 100% beriladi; qolganlari ball / 65
FULL_PERCENT_SCORE = 65.0

FAN1_MAX = 93.0      # 1-mutaxassislik fani (30 savol x 3.1)
FAN2_MAX = 63.0      # 2-mutaxassislik fani (30 savol x 2.1)
MAJBURIY_MAX = 11.0  # Majburiy fan (10 savol x 1.1)

GRADE_THRESHOLDS = [
    (70.0, "A+"),
    (65.0, "A"),
    (60.0, "B+"),
    (55.0, "B"),
    (50.0, "C+"),
    (46.0, "C"),
]

# Extreme (hamma to'g'ri / hech kim to'g'ri) topshiriqlar uchun
# Winsteps uslubidagi 0.3 ball tuzatma
EXTREME_ADJUSTMENT = 0.3

THETA_BOUND = 15.0


def round2(x: float) -> float:
    """Ikki xonagacha "matematik" yaxlitlash (0.005 -> 0.01)."""
    return float(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def grade_for(score: float) -> Optional[str]:
    """Ball bo'yicha sertifikat darajasi. 46 dan past bo'lsa None."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return None


def percent_for(score: float) -> Optional[float]:
    """
    OTMga kirishda hisoblanadigan foiz.
    A+/A -> 100%, B+..C -> ball/65*100, sertifikatsiz -> None.
    """
    if grade_for(score) is None:
        return None
    if score >= FULL_PERCENT_SCORE:
        return 100.0
    return round2(score / FULL_PERCENT_SCORE * 100.0)


def subject_points(percent: Optional[float]):
    """
    (1-fan, 2-fan) ballari: mutaxassislik fani foizga proporsional +
    majburiy fan uchun to'liq 11 ball.
    """
    if percent is None:
        return None, None
    p = percent / 100.0
    return round2(p * FAN1_MAX + MAJBURIY_MAX), round2(p * FAN2_MAX + MAJBURIY_MAX)


# ---------------------------------------------------------------------------
# Elementar simmetrik funksiyalar (log-masshtab bilan, overflow'siz)
# ---------------------------------------------------------------------------
def _esf(eps: Sequence[float]):
    """
    γ_0..γ_L elementar simmetrik funksiyalar.
    Qaytaradi (g, log_scale): haqiqiy γ_r = g[r] * exp(log_scale).
    """
    g = [1.0] + [0.0] * len(eps)
    log_scale = 0.0
    for k, e in enumerate(eps, 1):
        for r in range(k, 0, -1):
            g[r] += e * g[r - 1]
        top = max(g)
        if top > 1e150:
            g = [v / top for v in g]
            log_scale += math.log(top)
    return g, log_scale


def _cml_expectations(b: Sequence[float], n_r: Sequence[int]):
    """
    Har bir topshiriq uchun CML kutilgan to'g'ri javoblar soni va dispersiyasi.
    n_r[r] - xom bali r bo'lgan (extreme bo'lmagan) talabgorlar soni.
    """
    L = len(b)
    eps = [math.exp(-bi) for bi in b]
    g, ls = _esf(eps)
    expected = [0.0] * L
    variance = [0.0] * L
    for i in range(L):
        gi, lsi = _esf(eps[:i] + eps[i + 1:])
        factor = eps[i] * math.exp(lsi - ls)
        e_sum = 0.0
        v_sum = 0.0
        for r in range(1, L):
            if n_r[r] == 0:
                continue
            pi = factor * gi[r - 1] / g[r]
            e_sum += n_r[r] * pi
            v_sum += n_r[r] * pi * (1.0 - pi)
        expected[i] = e_sum
        variance[i] = v_sum
    return expected, variance


def _cml_estimate(s: Sequence[int], n_r: Sequence[int], max_iter: int, tol: float):
    """
    CML tenglamalarini Nyuton (diagonal) usulida yechish.
    s[i] - i-topshiriqqa to'g'ri javoblar soni (extreme bo'lmagan talabgorlar).
    """
    L = len(s)
    n = sum(n_r)
    b = [math.log((n - si) / si) for si in s]
    mean = sum(b) / L
    b = [bi - mean for bi in b]

    # Hamma qiyinliklar bir vaqtda yangilanganda diagonal Nyuton qadami
    # ~L/(L-1) marta oshib ketadi (Gessian qator yig'indisi 0), shu sababli
    # qadam (L-1)/L ga ko'paytiriladi va log-ehtimollik kamaysa yarimlanadi.
    shrink = (L - 1) / L
    loglik = _cml_loglik(b, s, n_r)
    converged = False
    iterations = 0
    for iterations in range(1, max_iter + 1):
        expected, variance = _cml_expectations(b, n_r)
        max_resid = max(abs(e - si) for e, si in zip(expected, s))
        if max_resid < tol:
            converged = True
            break
        steps = []
        for e, v, si in zip(expected, variance, s):
            step = shrink * (e - si) / v if v > 1e-12 else 0.0
            steps.append(max(-1.0, min(1.0, step)))
        factor = 1.0
        while True:
            new_b = [bi + factor * st for bi, st in zip(b, steps)]
            mean = sum(new_b) / L
            new_b = [bi - mean for bi in new_b]
            new_loglik = _cml_loglik(new_b, s, n_r)
            if new_loglik >= loglik - 1e-12 or factor < 1e-4:
                break
            factor *= 0.5
        b, loglik = new_b, new_loglik
    return b, converged, iterations


def _cml_loglik(b: Sequence[float], s: Sequence[int], n_r: Sequence[int]) -> float:
    """Shartli log-ehtimollik: -Σ s_i b_i - Σ_r n_r log γ_r."""
    eps = [math.exp(-bi) for bi in b]
    g, ls = _esf(eps)
    total = -sum(si * bi for si, bi in zip(s, b))
    for r, cnt in enumerate(n_r):
        if cnt:
            if g[r] <= 0:
                return float("-inf")
            total -= cnt * (math.log(g[r]) + ls)
    return total


# ---------------------------------------------------------------------------
# Talabgor qobiliyati (WLE)
# ---------------------------------------------------------------------------
def _p(theta: float, b: float) -> float:
    x = theta - b
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def _wle_equation(theta: float, r: float, b: Sequence[float]) -> float:
    """Warm WLE baholash tenglamasi: r - ΣP + J/(2I) = 0."""
    sum_p = 0.0
    info = 0.0
    j = 0.0
    for bi in b:
        p = _p(theta, bi)
        q = p * (1.0 - p)
        sum_p += p
        info += q
        j += q * (1.0 - 2.0 * p)
    if info <= 0:
        return r - sum_p
    return r - sum_p + j / (2.0 * info)


def wle_theta(r: float, b: Sequence[float], lo: float = -THETA_BOUND, hi: float = THETA_BOUND) -> float:
    """Xom ball r uchun WLE qobiliyat (bisection; tenglama θ bo'yicha kamayuvchi)."""
    f_lo = _wle_equation(lo, r, b)
    f_hi = _wle_equation(hi, r, b)
    if f_lo <= 0:
        return lo
    if f_hi >= 0:
        return hi
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        f_mid = _wle_equation(mid, r, b)
        if f_mid > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return 0.5 * (lo + hi)


def _theta_se(theta: float, b: Sequence[float]) -> float:
    info = sum(_p(theta, bi) * (1.0 - _p(theta, bi)) for bi in b)
    return 1.0 / math.sqrt(info) if info > 0 else float("inf")


def _solve_extreme_item(target: float, thetas: Sequence[float]) -> float:
    """Σ_v P(θ_v - b) = target tenglamasini b bo'yicha yechish."""
    lo, hi = -2 * THETA_BOUND, 2 * THETA_BOUND
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        exp_score = sum(_p(t, mid) for t in thetas)
        if exp_score > target:
            lo = mid  # topshiriq juda oson -> qiyinlikni oshirish
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Asosiy API
# ---------------------------------------------------------------------------
@dataclass
class ItemEstimate:
    index: int
    correct_count: int
    difficulty: float
    extreme: bool = False


@dataclass
class RaschResult:
    raw_scores: List[int]
    thetas: List[float]
    theta_se: List[float]
    z_scores: List[float]
    scores: List[float]                 # T-ball (>= 0), 2 xonali
    grades: List[Optional[str]]
    percents: List[Optional[float]]
    fan1: List[Optional[float]]
    fan2: List[Optional[float]]
    items: List[ItemEstimate]
    theta_by_raw: List[float]
    theta_mean: float
    theta_sd: float
    reliability: Optional[float]
    converged: bool
    iterations: int
    warnings: List[str] = field(default_factory=list)

    @property
    def item_difficulties(self) -> List[float]:
        return [it.difficulty for it in self.items]


def estimate_item_difficulties(matrix: Sequence[Sequence[int]], max_iter: int = 500, tol: float = 1e-6):
    """
    Topshiriq qiyinliklarini CML usulida baholash.

    Qaytaradi: (difficulties, extreme_flags, converged, iterations)
    Qiyinliklar o'rtachasi (baholanadigan topshiriqlar bo'yicha) 0 ga teng.
    """
    N = len(matrix)
    L = len(matrix[0]) if N else 0
    if L == 0:
        return [], [], True, 0

    items = list(range(L))
    persons = list(range(N))

    # Extreme talabgor/topshiriqlarni ketma-ket ajratish (Winsteps kabi)
    while True:
        changed = False
        raw = {v: sum(matrix[v][i] for i in items) for v in persons}
        kept_persons = [v for v in persons if 0 < raw[v] < len(items)]
        if len(kept_persons) != len(persons):
            changed = True
        persons = kept_persons
        if not persons:
            items_ok = []
        else:
            items_ok = [i for i in items
                        if 0 < sum(matrix[v][i] for v in persons) < len(persons)]
        if len(items_ok) != len(items):
            changed = True
        items = items_ok
        if not changed or not items or not persons:
            break

    difficulties = [0.0] * L
    extreme = [True] * L
    converged = True
    iterations = 0

    if len(items) >= 2 and persons:
        Lk = len(items)
        s = [sum(matrix[v][i] for v in persons) for i in items]
        n_r = [0] * (Lk + 1)
        for v in persons:
            n_r[sum(matrix[v][i] for i in items)] += 1
        b, converged, iterations = _cml_estimate(s, n_r, max_iter, tol)
        for k, i in enumerate(items):
            difficulties[i] = b[k]
            extreme[i] = False

    return difficulties, extreme, converged, iterations


def compute_rasch(
    matrix: Sequence[Sequence[int]],
    max_iter: int = 500,
    tol: float = 1e-6,
    max_score: Optional[float] = None,
) -> RaschResult:
    """
    To'liq Rasch tahlili: topshiriq qiyinliklari, qobiliyatlar, T-ball,
    darajalar, foiz va OTM ballari.

    matrix - N x L ro'yxat (talabgor x topshiriq), qiymatlar 0/1.
    max_score - T-ballni yuqoridan cheklash (None - cheklanmaydi, BMBA kabi).
    """
    matrix = [[1 if x else 0 for x in row] for row in matrix]
    N = len(matrix)
    if N == 0:
        return RaschResult(
            raw_scores=[], thetas=[], theta_se=[], z_scores=[], scores=[], grades=[],
            percents=[], fan1=[], fan2=[], items=[], theta_by_raw=[], theta_mean=0.0,
            theta_sd=0.0, reliability=None, converged=True, iterations=0,
        )
    L = len(matrix[0])
    if any(len(row) != L for row in matrix):
        raise ValueError("Barcha qatorlarda topshiriqlar soni bir xil bo'lishi kerak")

    warnings: List[str] = []
    raw_scores = [sum(row) for row in matrix]

    b, extreme, converged, iterations = estimate_item_difficulties(matrix, max_iter, tol)
    estimable = [i for i in range(L) if not extreme[i]]

    if L == 0:
        theta_by_raw = [0.0]
    else:
        if not estimable:
            warnings.append("Topshiriq qiyinliklarini baholash uchun ma'lumot yetarli emas")

        # Extreme topshiriqlarga 0.3 tuzatma bilan qiyinlik berish
        if estimable and len(estimable) < L:
            b_est = [b[i] for i in estimable]
            theta_est_table = [wle_theta(r, b_est) for r in range(len(estimable) + 1)]
            person_thetas = [theta_est_table[sum(row[i] for i in estimable)] for row in matrix]
            for i in range(L):
                if extreme[i]:
                    correct = sum(row[i] for row in matrix)
                    if correct == 0:
                        target = EXTREME_ADJUSTMENT
                    elif correct == N:
                        target = N - EXTREME_ADJUSTMENT
                    else:
                        target = min(max(correct, EXTREME_ADJUSTMENT), N - EXTREME_ADJUSTMENT)
                    b[i] = _solve_extreme_item(target, person_thetas)
        elif not estimable:
            # Ma'lumot yo'q: qiyinlikni to'g'ri javob ulushidan (logit) olish
            for i in range(L):
                correct = sum(row[i] for row in matrix)
                p = (correct + 0.5) / (N + 1.0)
                b[i] = math.log((1 - p) / p)

        theta_by_raw = [wle_theta(r, b) for r in range(L + 1)]

    thetas = [theta_by_raw[r] for r in raw_scores]
    se = [_theta_se(t, b) for t in thetas] if L else [float("inf")] * N

    mean = sum(thetas) / N
    var = sum((t - mean) ** 2 for t in thetas) / N
    sd = math.sqrt(var)

    if N < 2 or sd < 1e-12:
        if N < 2:
            warnings.append("Standartlashtirish uchun kamida 2 ta ishtirokchi kerak")
        z_scores = [0.0] * N
    else:
        z_scores = [(t - mean) / sd for t in thetas]

    scores = []
    for z in z_scores:
        t = max(MIN_SCORE, T_MEAN + T_SD * z)
        if max_score is not None:
            t = min(max_score, t)
        scores.append(round2(t))
    grades = [grade_for(s) for s in scores]
    percents = [percent_for(s) for s in scores]
    fans = [subject_points(p) for p in percents]

    # Talabgorlar ajratish ishonchliligi (person separation reliability)
    reliability = None
    if N >= 2 and var > 0:
        finite_se = [x for x in se if math.isfinite(x)]
        if finite_se:
            mse = sum(x * x for x in finite_se) / len(finite_se)
            reliability = max(0.0, min(1.0, (var - mse) / var))

    if N < 30:
        warnings.append(
            f"Ishtirokchilar soni kam ({N} ta). Rasch natijalari ishonchliligi uchun kamida 30 ta tavsiya etiladi"
        )
    if not converged:
        warnings.append("CML iteratsiyalari to'liq yaqinlashmadi")

    items = [
        ItemEstimate(index=i, correct_count=sum(row[i] for row in matrix),
                     difficulty=b[i], extreme=extreme[i])
        for i in range(L)
    ]

    return RaschResult(
        raw_scores=raw_scores,
        thetas=thetas,
        theta_se=se,
        z_scores=z_scores,
        scores=scores,
        grades=grades,
        percents=percents,
        fan1=[f[0] for f in fans],
        fan2=[f[1] for f in fans],
        items=items,
        theta_by_raw=theta_by_raw,
        theta_mean=mean,
        theta_sd=sd,
        reliability=reliability,
        converged=converged,
        iterations=iterations,
        warnings=warnings,
    )
