"""
Rasch algoritmining aniqligi:
  - girth kutubxonasining CML natijalari bilan solishtirish
  - CML tenglamalari mustaqil (numpy) hisob bilan bajarilishi
  - simulyatsiya qilingan ma'lumotlardan haqiqiy parametrlarni tiklash
  - WLE qobiliyatlarini scipy optimizatori bilan solishtirish
  - T-ball "oracle" (haqiqiy qiyinliklar bilan) natijaga yaqinligi
  - Rasch xossalari (monotonlik, invariantlik, chegaralar) va chekka holatlar
"""
import math

import pytest

np = pytest.importorskip("numpy")

from app.services.rasch_service import (  # noqa: E402
    compute_rasch, estimate_item_difficulties, wle_theta, grade_for,
    MAX_SCORE, MIN_SCORE,
)


def simulate(seed, n_persons=None, n_items=None, b_mean=None, b_sd=None, th_mean=None, th_sd=None):
    rng = np.random.default_rng(seed)
    N = n_persons or int(rng.integers(80, 700))
    L = n_items or int(rng.integers(10, 56))
    b = rng.normal(b_mean if b_mean is not None else rng.uniform(-0.5, 1.0),
                   b_sd if b_sd is not None else rng.uniform(0.7, 1.6), L)
    th = rng.normal(th_mean if th_mean is not None else 0.0,
                    th_sd if th_sd is not None else rng.uniform(0.7, 1.5), N)
    prob = 1.0 / (1.0 + np.exp(-(th[:, None] - b[None, :])))
    X = (rng.random((N, L)) < prob).astype(int)
    return X, b, th


def strip_extremes(X):
    """Extreme talabgor va topshiriqlarni ketma-ket olib tashlash."""
    rows = np.arange(X.shape[0])
    cols = np.arange(X.shape[1])
    while True:
        sub = X[np.ix_(rows, cols)]
        r = sub.sum(1)
        keep_r = rows[(r > 0) & (r < len(cols))]
        sub = X[np.ix_(keep_r, cols)]
        s = sub.sum(0)
        keep_c = cols[(s > 0) & (s < len(keep_r))]
        if len(keep_r) == len(rows) and len(keep_c) == len(cols):
            return rows, cols
        rows, cols = keep_r, keep_c
        if len(rows) == 0 or len(cols) == 0:
            return rows, cols


def esf_numpy(eps):
    g = np.zeros(len(eps) + 1)
    g[0] = 1.0
    for e in eps:
        g[1:] = g[1:] + e * g[:-1]
    return g


# ---------------------------------------------------------------------------
# 1. girth CML bilan solishtirish
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(200))
def test_matches_girth_conditional_ml(seed):
    girth = pytest.importorskip("girth")
    X, _, _ = simulate(seed)
    rows, cols = strip_extremes(X)
    if len(cols) < 3:
        pytest.skip("ma'lumot yetarli emas")
    Xs = X[np.ix_(rows, cols)]

    ours, extreme, converged, _ = estimate_item_difficulties(Xs.tolist(), tol=1e-9)
    assert converged
    assert not any(extreme)
    ours = np.array(ours)

    ref = np.asarray(girth.rasch_conditional(Xs.T, options={"max_iteration": 200})["Difficulty"], dtype=float)
    if np.any(np.abs(ref) > 4.95):
        # girth qiyinliklarni [-5, 5] oralig'i bilan cheklaydi - bunday holatda
        # solishtirish ma'nosiz (bizning natija test_cml_score_equations_hold bilan tekshiriladi)
        pytest.skip("girth [-5, 5] chegarasiga yetdi")
    ref = ref - ref.mean()
    assert np.max(np.abs(ours - ref)) < 2e-3


# ---------------------------------------------------------------------------
# 2. CML tenglamalari: Σ_r n_r π_i(r) = s_i (mustaqil numpy hisob)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(1000, 1100))
def test_cml_score_equations_hold(seed):
    X, _, _ = simulate(seed)
    rows, cols = strip_extremes(X)
    if len(cols) < 3:
        pytest.skip("ma'lumot yetarli emas")
    Xs = X[np.ix_(rows, cols)]
    b, _, converged, _ = estimate_item_difficulties(Xs.tolist(), tol=1e-9)
    assert converged
    b = np.array(b)
    assert abs(b.mean()) < 1e-9

    L = Xs.shape[1]
    eps = np.exp(-b)
    g = esf_numpy(eps)
    n_r = np.bincount(Xs.sum(1), minlength=L + 1)
    s = Xs.sum(0)
    for i in range(L):
        gi = esf_numpy(np.delete(eps, i))
        expected = sum(n_r[r] * eps[i] * gi[r - 1] / g[r] for r in range(1, L))
        assert expected == pytest.approx(s[i], abs=1e-5)


# ---------------------------------------------------------------------------
# 3. Haqiqiy parametrlarni tiklash (matematika: 55 topshiriq)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(2000, 2150))
def test_item_parameter_recovery(seed):
    X, b_true, _ = simulate(seed, n_persons=800, n_items=55, b_mean=0.8, b_sd=1.2, th_mean=0.0, th_sd=1.0)
    res = compute_rasch(X.tolist())
    est = np.array(res.item_difficulties)
    bt = b_true - b_true.mean()
    rmse = math.sqrt(float(np.mean((est - bt) ** 2)))
    corr = float(np.corrcoef(est, bt)[0, 1])
    assert rmse < 0.2
    assert corr > 0.98


# ---------------------------------------------------------------------------
# 4. WLE: penalized log-likelihood maksimumi scipy bilan
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(3000, 3100))
def test_wle_matches_scipy_optimizer(seed):
    optimize = pytest.importorskip("scipy.optimize")
    rng = np.random.default_rng(seed)
    L = int(rng.integers(5, 56))
    b = rng.normal(0.3, 1.2, L)

    def neg_penalized(theta, r):
        p = 1.0 / (1.0 + np.exp(-(theta - b)))
        loglik = r * theta - np.sum(np.log1p(np.exp(theta - b)))
        info = np.sum(p * (1 - p))
        return -(loglik + 0.5 * math.log(info))

    for r in range(L + 1):
        ours = wle_theta(r, b.tolist())
        ref = optimize.minimize_scalar(lambda t: neg_penalized(t, r), bounds=(-15, 15),
                                       method="bounded", options={"xatol": 1e-10}).x
        assert ours == pytest.approx(ref, abs=1e-4)


# ---------------------------------------------------------------------------
# 5. T-ball: haqiqiy qiyinliklar bilan hisoblangan "oracle" natijaga yaqinlik
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(4000, 4100))
def test_scores_close_to_oracle(seed):
    X, b_true, _ = simulate(seed, n_persons=600, n_items=55, b_mean=0.8, b_sd=1.2, th_mean=0.0, th_sd=1.0)
    res = compute_rasch(X.tolist())
    table = [wle_theta(k, b_true.tolist()) for k in range(56)]
    th_oracle = np.array([table[k] for k in X.sum(1)])
    t_oracle = np.clip(50 + 10 * (th_oracle - th_oracle.mean()) / th_oracle.std(), 0, 75)
    t_ours = np.array(res.scores)
    assert np.mean(np.abs(t_ours - t_oracle)) < 0.25
    assert np.max(np.abs(t_ours - t_oracle)) < 1.0
    agree = np.mean([grade_for(a) == g for a, g in zip(t_oracle, res.grades)])
    assert agree > 0.93


# ---------------------------------------------------------------------------
# 6. Xossalar
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(5000, 5050))
def test_monotonic_in_raw_score_and_same_raw_same_score(seed):
    X, _, _ = simulate(seed)
    res = compute_rasch(X.tolist())
    by_raw = {}
    for raw, score, theta in zip(res.raw_scores, res.scores, res.thetas):
        by_raw.setdefault(raw, set()).add((score, theta))
    for raw, values in by_raw.items():
        assert len(values) == 1  # Rasch: xom ball yetarli statistika
    raws = sorted(by_raw)
    thetas = [next(iter(by_raw[r]))[1] for r in raws]
    scores = [next(iter(by_raw[r]))[0] for r in raws]
    assert all(a < b for a, b in zip(thetas, thetas[1:]))
    assert all(a <= b for a, b in zip(scores, scores[1:]))


@pytest.mark.parametrize("seed", range(5100, 5150))
def test_scores_within_bounds_and_standardized(seed):
    X, _, _ = simulate(seed)
    res = compute_rasch(X.tolist())
    scores = np.array(res.scores)
    assert scores.min() >= MIN_SCORE and scores.max() <= MAX_SCORE
    z = np.array(res.z_scores)
    assert abs(z.mean()) < 1e-9
    assert z.std() == pytest.approx(1.0, abs=1e-9)
    unclamped = 50 + 10 * z
    for s, u in zip(scores, unclamped):
        expected = min(MAX_SCORE, max(MIN_SCORE, u))
        assert s == pytest.approx(expected, abs=0.006)


@pytest.mark.parametrize("seed", range(5200, 5250))
def test_person_order_invariance(seed):
    X, _, _ = simulate(seed)
    res = compute_rasch(X.tolist())
    perm = np.random.default_rng(seed).permutation(X.shape[0])
    res_p = compute_rasch(X[perm].tolist())
    assert np.allclose(np.array(res.scores)[perm], res_p.scores, atol=1e-9)
    assert np.allclose(res.item_difficulties, res_p.item_difficulties, atol=1e-9)


@pytest.mark.parametrize("seed", range(5300, 5350))
def test_item_order_equivariance(seed):
    X, _, _ = simulate(seed)
    res = compute_rasch(X.tolist())
    perm = np.random.default_rng(seed).permutation(X.shape[1])
    res_p = compute_rasch(X[:, perm].tolist())
    assert np.allclose(np.array(res.item_difficulties)[perm], res_p.item_difficulties, atol=1e-5)
    assert np.allclose(res.scores, res_p.scores, atol=0.011)


@pytest.mark.parametrize("seed", range(5400, 5450))
def test_duplicating_data_keeps_estimates(seed):
    X, _, _ = simulate(seed)
    res = compute_rasch(X.tolist())
    res_d = compute_rasch(np.vstack([X, X]).tolist())
    assert np.allclose(res.item_difficulties, res_d.item_difficulties, atol=1e-4)
    assert np.allclose(res.scores + res.scores, res_d.scores, atol=0.011)


@pytest.mark.parametrize("seed", range(5500, 5550))
def test_harder_items_get_higher_difficulty(seed):
    X, _, _ = simulate(seed)
    res = compute_rasch(X.tolist())
    rows, _ = strip_extremes(X)
    counts = X[rows].sum(0)
    b = np.array(res.item_difficulties)
    for i in range(X.shape[1]):
        for j in range(X.shape[1]):
            if res.items[i].extreme or res.items[j].extreme:
                continue
            if counts[i] > counts[j]:
                assert b[i] < b[j]


# ---------------------------------------------------------------------------
# 7. Chekka holatlar
# ---------------------------------------------------------------------------
def test_empty_input():
    res = compute_rasch([])
    assert res.scores == [] and res.items == []


def test_single_participant_gets_mean_score():
    res = compute_rasch([[1, 0, 1, 1, 0]])
    assert res.scores == [50.0]
    assert any("2 ta" in w for w in res.warnings)


def test_all_zero_and_all_one_rows():
    rows = [[0] * 10, [1] * 10, [1, 0] * 5, [0, 1] * 5, [1, 1, 1, 0, 0, 0, 1, 0, 1, 0]]
    res = compute_rasch(rows)
    assert res.scores[1] == max(res.scores)
    assert res.scores[0] == min(res.scores)
    assert all(math.isfinite(t) for t in res.thetas)


def test_everyone_same_answers():
    res = compute_rasch([[1, 0, 1, 0]] * 20)
    assert res.scores == [50.0] * 20


def test_all_wrong_everyone():
    res = compute_rasch([[0] * 55] * 30)
    assert res.scores == [50.0] * 30
    assert all(math.isfinite(it.difficulty) for it in res.items)


def test_all_correct_everyone():
    res = compute_rasch([[1] * 55] * 30)
    assert res.scores == [50.0] * 30


def test_item_nobody_solved_is_hardest():
    X, _, _ = simulate(7, n_persons=300, n_items=20)
    X[:, 5] = 0
    res = compute_rasch(X.tolist())
    assert res.items[5].extreme
    assert res.items[5].difficulty == max(res.item_difficulties)


def test_item_everybody_solved_is_easiest():
    X, _, _ = simulate(8, n_persons=300, n_items=20)
    X[:, 3] = 1
    res = compute_rasch(X.tolist())
    assert res.items[3].extreme
    assert res.items[3].difficulty == min(res.item_difficulties)


def test_ragged_rows_raise():
    with pytest.raises(ValueError):
        compute_rasch([[1, 0], [1]])


def test_boolean_and_int_input_equivalent():
    X, _, _ = simulate(9, n_persons=100, n_items=15)
    a = compute_rasch(X.tolist())
    b = compute_rasch(X.astype(bool).tolist())
    assert a.scores == b.scores


def test_small_group_warning():
    X, _, _ = simulate(10, n_persons=20, n_items=15)
    res = compute_rasch(X.tolist())
    assert any("kam" in w for w in res.warnings)


def test_reliability_reasonable_for_55_items():
    X, _, _ = simulate(11, n_persons=800, n_items=55, b_mean=0.5, b_sd=1.2, th_mean=0, th_sd=1.0)
    res = compute_rasch(X.tolist())
    assert 0.8 < res.reliability < 0.95


def test_large_group_performance():
    import time
    X, _, _ = simulate(12, n_persons=5000, n_items=55)
    t0 = time.time()
    res = compute_rasch(X.tolist())
    assert time.time() - t0 < 10
    assert res.converged


def test_two_items_minimum():
    res = compute_rasch([[1, 0], [0, 1], [1, 1], [0, 0], [1, 0]])
    assert len(res.scores) == 5
    assert res.converged


def test_high_score_capped_at_75():
    # bitta juda kuchli talabgor, qolganlar past -> Z katta, 75 bilan cheklanadi
    rows = [[1] * 30] + [[1] * 3 + [0] * 27] * 40 + [[1] * 4 + [0] * 26] * 40
    res = compute_rasch(rows)
    assert res.scores[0] == 75.0
