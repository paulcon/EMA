"""Uniform and convergent designs (designs.md, Generators, Convergent, Samplers; G1, G7, G8, G17, G18)."""

import itertools

import numpy as np
import pytest

from ema.designs import generators
from ema.types.errors import RequestError
from tests.support.designs import CONTRACT, CONTRACT_SPACE, D20, D20_SPACE, identity, with_identity
from tests.support.fakes import FAKE_NESTED, FAKE_NOT_NESTED, FAKE_RATE_TWO_THIRDS, registered

UNIFORM = generators.get("uniform")
CONVERGENT = generators.get("convergent")
LINEAR = {"a": [0, 2], "b": [-1, 1]}


def test_g1_uniform_same_request_same_points_and_seeds_differ():
    ident = identity(CONTRACT, "uniform", CONTRACT_SPACE, n=20, seed=1)
    assert np.array_equal(UNIFORM.build(ident, CONTRACT).points, UNIFORM.build(ident, CONTRACT).points)
    other = UNIFORM.build(identity(CONTRACT, "uniform", CONTRACT_SPACE, n=20, seed=2), CONTRACT)
    assert not np.array_equal(UNIFORM.build(ident, CONTRACT).points, other.points)


def test_uniform_linear_points_are_lo_plus_width_times_u():
    """designs.md, Determinism: points in linear ranges are lo + (hi - lo) u, bit for bit."""
    design = UNIFORM.build(identity(CONTRACT, "uniform", LINEAR, n=30, seed=4), CONTRACT)
    u = np.random.default_rng(4).random((30, 2))
    assert np.array_equal(design.points[:, 0], 0.0 + (2.0 - 0.0) * u[:, 0])
    assert np.array_equal(design.points[:, 1], -1.0 + (1.0 - -1.0) * u[:, 1])
    assert np.all(design.points[:, 2] == 1.0) and np.all(design.points[:, 3] == 0.5)
    assert design.replicates.tolist() == [0] * 30


@pytest.mark.parametrize(
    ("n_min", "alpha", "level", "sizes"),
    [
        (18, "0.7072", 3, (18, 36, 72, 144)),
        (18, 0.7072, 3, (18, 36, 72, 144)),
        (18, "0.7072", 6, (18, 36, 72, 144, 288, 576, 1151)),
        (18, "0.7071", 3, (18, 37, 73, 145)),
        (18, "0.70710678", 3, (18, 37, 73, 145)),
        (18, "0.5", 2, (18, 72, 288)),
        (18, "0.9", 0, (18,)),
    ],
)
def test_g7_sizes_in_exact_arithmetic_and_the_points_are_uniforms(n_min, alpha, level, sizes):
    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=n_min, alpha=alpha, level=level, seed=3)
    design = CONVERGENT.build(ident, CONTRACT)
    assert design.levels == sizes and len(design) == sizes[-1] == CONVERGENT.size(ident, CONTRACT)
    whole = UNIFORM.build(identity(CONTRACT, "uniform", CONTRACT_SPACE, n=sizes[-1], seed=3), CONTRACT)
    assert np.array_equal(design.points, whole.points)


@pytest.mark.parametrize(
    ("params", "named"),
    [
        ({"n_min": 18, "alpha": "1", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": "0", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": "1.5", "level": 2}, "alpha"),
        ({"n_min": 2, "alpha": "0.95", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": "abc", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": True, "level": 2}, "alpha"),
        ({"n_min": 0, "alpha": "0.5", "level": 2}, "n_min"),
        ({"n_min": 18, "alpha": "0.5", "level": -1}, "level"),
        ({"n_min": 18, "alpha": "0.5"}, "level"),
    ],
)
def test_g8_g18_convergent_refusals(params, named):
    with pytest.raises(RequestError, match=named):
        CONVERGENT.build(identity(CONTRACT, "convergent", CONTRACT_SPACE, **params), CONTRACT)


def test_g17_a_sampler_other_than_random_comes_later():
    for gen, params in ((UNIFORM, {"n": 5}), (CONVERGENT, {"n_min": 2, "alpha": "0.5", "level": 1})):
        ident = identity(CONTRACT, gen.name, CONTRACT_SPACE, sampler="sobol", sampler_version="1", **params)
        with pytest.raises(RequestError, match="sampler sobol comes in a later version"):
            gen.build(ident, CONTRACT)


def test_g17_a_registered_sampler_works_with_uniform_and_convergent_refuses_one_not_nested():
    with registered(FAKE_NESTED), registered(FAKE_NOT_NESTED):
        for fake in (FAKE_NESTED, FAKE_NOT_NESTED):
            ident = identity(CONTRACT, "uniform", LINEAR, n=6, sampler=fake.name, seed=2)
            u = fake.unit_rows(2, 2, 0, 6)
            assert np.array_equal(UNIFORM.build(ident, CONTRACT).points[:, 0], 0.0 + 2.0 * u[:, 0])
        nested = identity(CONTRACT, "convergent", LINEAR, n_min=2, alpha="0.5", level=1, sampler="fake_nested")
        assert CONVERGENT.build(nested, CONTRACT).levels == (2, 8)
        not_nested = identity(CONTRACT, "convergent", LINEAR, n_min=2, alpha="0.5", level=1, sampler="fake_not_nested")
        with pytest.raises(RequestError, match="fake_not_nested"):
            CONVERGENT.build(not_nested, CONTRACT)


def test_g18_a_sampler_whose_one_over_r_isnt_an_integer():
    with registered(FAKE_RATE_TWO_THIRDS):
        ident = identity(CONTRACT, "convergent", LINEAR, n_min=2, alpha="0.5", level=1, sampler="fake_two_thirds")
        with pytest.raises(RequestError, match="fake_two_thirds"):
            CONVERGENT.build(ident, CONTRACT)


def test_uniform_and_convergent_need_a_sampler():
    ident = identity(CONTRACT, "uniform", LINEAR, n=3)
    with pytest.raises(RequestError, match="sampler"):
        UNIFORM.build(with_identity(ident, sampler=None, sampler_version=None), CONTRACT)


def test_d20():
    design = UNIFORM.build(identity(D20, "uniform", D20_SPACE, n=100), D20)
    assert design.points.shape == (100, 20) and np.all(np.abs(design.points) <= 1.0)


def test_g5_convergent_far_over_the_cap_is_refused_quickly():
    from ema.types.errors import DesignTooLarge

    for alpha, level in (("1e-300", 3), ("0.5", 10**9)):
        ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha=alpha, level=level)
        with pytest.raises(DesignTooLarge):
            CONVERGENT.build(ident, CONTRACT)


def exact_sizes(n_min, alpha, level):
    """designs.md, Convergent: n_l = ceil(n_min alpha^(-2l)) in exact rational arithmetic, levels 0 ... level,
    stopping one level past the first over the cap (the rule itself, written plainly, with the integers
    n_min num^l and den^l; random's r = 1/2)."""
    from fractions import Fraction

    from ema.designs.generators import MAX_DESIGN_POINTS

    factor = (1 / Fraction(alpha)) ** 2
    num, den, sizes = n_min, 1, []
    for _ in range(level + 1):
        sizes.append(-(-num // den))
        if len(sizes) > 1 and sizes[-2] > MAX_DESIGN_POINTS:
            break
        num, den = num * factor.numerator, den * factor.denominator
    return tuple(sizes)


@pytest.mark.parametrize(
    "alpha",
    ["0.5", "0.25", "0.2", "0.1", "0.6", "0.7072", "0.7071", "0.75", "0.8", "0.9", "0.99", "0.999", "0.123456789"]
    + ["0.3333333333", "0.70710678", "0.9999", "0.31622776601683794"],
)
def test_g7_the_sizes_equal_the_exact_rule_for_many_alphas_and_levels(alpha):
    """M1 (review round 1, 0067): the float estimate with its guard gives the exact rule's sizes, near integers
    (alpha = 0.5, 0.1: every size an integer) included; the levels stop at the first over the cap, and n_L, one
    level past it, is exact."""
    from ema.designs.generators import MAX_DESIGN_POINTS

    for n_min in (1, 2, 3, 7, 18, 100, 999, 12345, 10**6):
        expected = exact_sizes(n_min, alpha, 3000)
        over = [lv for lv, n in enumerate(expected) if n > MAX_DESIGN_POINTS]
        level = min(over[0] + 1, 3000) if over else 3000
        ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=n_min, alpha=alpha, level=level)
        shown = expected[: over[0] + 1] if over else expected
        if any(a >= b for a, b in itertools.pairwise(shown)):
            with pytest.raises(RequestError, match="strictly increasing"):
                CONVERGENT.levels(ident, CONTRACT)
            continue
        assert CONVERGENT.levels(ident, CONTRACT) == (shown, expected[level]), (n_min, alpha)


def test_g5_c24_a_large_level_near_alpha_one_is_answered_at_once():
    """M1 (review round 1): n_min + L over the cap is refused before any size is computed (strictly increasing
    sizes give n_L >= n_min + L); a long run of levels costs a float estimate each; n_L is exact."""
    import time

    from ema.types.errors import DesignTooLarge

    t0 = time.perf_counter()
    big = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=10_000_000, alpha="0.9999999", level=3_000_000)
    with pytest.raises(DesignTooLarge, match="13,000,000"):
        CONVERGENT.size(big, CONTRACT)
    with pytest.raises(DesignTooLarge, match="13,000,000"):
        CONVERGENT.build(big, CONTRACT)
    long = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=5_000_000, alpha="0.9999999", level=20_000)
    assert CONVERGENT.size(long, CONTRACT) == 5_020_041
    sizes, _ = CONVERGENT.levels(long, CONTRACT)
    assert len(sizes) == 20_001 and sizes[:3] == (5_000_000, 5_000_002, 5_000_003)
    # Over the cap at level 1, and n_L (level 900,000) computed exactly without the power's full integers.
    over = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=9_000_000, alpha="0.9999999", level=900_000)
    assert CONVERGENT.size(over, CONTRACT) == 10_774_957
    with pytest.raises(DesignTooLarge, match="10,774,957"):
        CONVERGENT.build(over, CONTRACT)
    assert time.perf_counter() - t0 < 2.0


def test_g5_the_refusal_over_two_to_the_62_names_a_size():
    """n2 (review round 1): the refusal names the first size over the cap, and its level."""
    from ema.types.errors import DesignTooLarge

    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=10, alpha="0.5", level=40)
    with pytest.raises(DesignTooLarge, match=r"level 10 alone has 10,485,760, over the cap of 10,000,000"):
        CONVERGENT.size(ident, CONTRACT)
    tiny = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha="1e-300", level=3)
    with pytest.raises(DesignTooLarge, match=r"level 1 alone has more than 2\^1994"):
        CONVERGENT.size(tiny, CONTRACT)


@pytest.mark.parametrize(
    ("alpha", "level"), [("0.9999999", 500), ("0.9999999", 20_000), ("0.99999", 3000), ("0.999", 900)]
)
def test_a_size_at_a_large_level_is_exact_by_its_bounds(alpha, level):
    """M1: n_min factor^L rounded up, from fixed-point bounds refined until they agree, equals the exact rule."""
    from fractions import Fraction

    from ema.designs.convergent import _ceil_size

    factor = (1 / Fraction(alpha)) ** 2
    for n_min in (1, 5, 12345):
        exact = -(-n_min * factor.numerator**level // factor.denominator**level)
        assert _ceil_size(n_min, factor, level) == exact


@pytest.mark.parametrize("alpha", ["1/3", " 0.5 ", "0.5\n", "1_0", "0x0.8", "nan", "-0.5", ""])
def test_alpha_text_must_be_a_decimal_number(alpha):
    """m2 (review round 1; 0047): alpha's text is a decimal number as written; not a fraction, nor padded."""
    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha=alpha, level=1)
    with pytest.raises(RequestError, match="alpha"):
        CONVERGENT.size(ident, CONTRACT)


def test_alpha_as_a_numpy_float_is_its_double():
    """m2: np.float64(0.5) reads as the float 0.5 does (0047)."""
    a = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=18, alpha=np.float64(0.7072), level=3)
    assert CONVERGENT.levels(a, CONTRACT)[0] == (18, 36, 72, 144)


# --------------------------------------------------------------------------------------------------------------
# Review round 2 (0067): huge exponents, the float path's precision, the exact path's bounds


@pytest.mark.parametrize(
    ("alpha", "level", "outcome"),
    [
        ("1e-10000000", 0, (5,)),
        ("1e-10000000", 1, "DesignTooLarge"),
        ("1e-99999999999", 0, (5,)),
        ("1e-99999999999", 3, "DesignTooLarge"),
        ("1e+10000000", 0, "RequestError"),
        ("1e+10000000", 1, "RequestError"),
        ("0e10000000", 1, "RequestError"),
        ("-1e-10000000", 1, "RequestError"),
        ("1e-9999999999999999999999", 1, "RequestError"),
        ("5e-1001", 1, "DesignTooLarge"),
    ],
)
def test_g5_c24_an_alpha_with_a_huge_exponent_is_answered_at_once(alpha, level, outcome):
    """0067 review round 2: the exponent isn't expanded (``Fraction("1e-10000000")`` builds 10^(10^7)). Below
    10^-1000, level 0 is n_min and level >= 1 is too large (n_1 > 10^2000); 1 or more, 0 or less, and an exponent
    past Decimal's are refused as alpha; no MemoryError."""
    import time

    from ema.types.errors import DesignTooLarge

    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=5, alpha=alpha, level=level)
    t0 = time.perf_counter()
    if isinstance(outcome, tuple):
        assert CONVERGENT.levels(ident, CONTRACT) == (outcome, outcome[-1])
    elif outcome == "DesignTooLarge":
        with pytest.raises(DesignTooLarge, match=r"more than 10\^2000 points"):
            CONVERGENT.size(ident, CONTRACT)
    else:
        with pytest.raises(RequestError, match="alpha"):
            CONVERGENT.size(ident, CONTRACT)
    assert time.perf_counter() - t0 < 0.5


def test_alpha_at_ten_to_the_minus_1000_is_still_read_exactly():
    """The boundary: 10^-1000 itself is read as its fraction: n_1 = 2 10^2000 exactly, and at level 2 the refusal
    names level 1's size."""
    from ema.types.errors import DesignTooLarge

    one = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha="1e-1000", level=1)
    assert CONVERGENT.size(one, CONTRACT) == 2 * 10**2000
    two = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha="1e-1000", level=2)
    with pytest.raises(DesignTooLarge, match=r"level 1 alone has more than 2\^6644"):
        CONVERGENT.size(two, CONTRACT)


def test_an_echoed_alpha_text_is_cut_to_40_characters():
    """n (0067 review round 2): a long alpha text isn't echoed whole."""
    text = "0." + "9" * 200 + "x"
    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha=text, level=1)
    with pytest.raises(RequestError) as caught:
        CONVERGENT.size(ident, CONTRACT)
    assert "9" * 60 not in str(caught.value) and "…" in str(caught.value)


def reference_sizes(n_min, alpha, level):
    """designs.md, Convergent's sizes to 80 significant digits (``decimal``), levels 0 ... level, stopping at the
    first over the cap, and n_L: an independent reference for long runs, where the plain integers are too slow.
    Each size is checked to be more than 10^-40 (relative) from an integer, unless it is one, so its ceiling is
    the exact rule's."""
    from decimal import ROUND_CEILING, Decimal, localcontext

    from ema.designs.generators import MAX_DESIGN_POINTS

    def ceil(x):
        nearest = x.to_integral_value()
        assert x == nearest or abs(x - nearest) > Decimal("1e-40") * x
        return int(x.to_integral_value(rounding=ROUND_CEILING))

    with localcontext() as ctx:
        ctx.prec = 80
        factor = (1 / Decimal(alpha)) ** 2
        x, sizes = Decimal(n_min), []
        for _ in range(level + 1):
            sizes.append(ceil(x))
            if sizes[-1] > MAX_DESIGN_POINTS:
                break
            x *= factor
        return tuple(sizes), ceil(Decimal(n_min) * factor**level)


@pytest.mark.parametrize(
    ("n_min", "alpha", "level"),
    [(3_401_420, "0.99999284", 188_069), (5_000_000, "0.9999999", 20_000), (1_000_000, "0.99999", 60_000)]
    + [(9_999, "0.9999", 40_000), pytest.param(2_500_000, "0.999999", 700_000, marks=pytest.mark.slow)],
)
def test_g7_long_runs_near_alpha_one_equal_a_high_precision_reference(n_min, alpha, level):
    """B (0067 review round 2): tens of thousands of float estimates near alpha = 1, each checked against
    ``reference_sizes``; their ln f must be log1p's."""
    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=n_min, alpha=alpha, level=level)
    assert CONVERGENT.levels(ident, CONTRACT) == reference_sizes(n_min, alpha, level)


def test_the_float_path_needs_log1p(monkeypatch):
    """The negative control for the test above: with ln f as log(f), the first case's sizes at levels 53,311 and
    70,793 are each one too small (the precision the guard assumes is lost)."""
    import math

    from ema.designs import convergent

    monkeypatch.setattr(convergent, "_log_factor", lambda factor: math.log(float(factor)))
    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=3_401_420, alpha="0.99999284", level=188_069)
    sizes, _ = CONVERGENT.levels(ident, CONTRACT)
    reference, _ = reference_sizes(3_401_420, "0.99999284", 188_069)
    assert [lv for lv, (a, b) in enumerate(zip(sizes, reference, strict=True)) if a != b] == [53_311, 70_793]


def test_power_bounds_bracket_the_exact_power():
    """``_power_bounds``: lo <= (num/den)^level 2^bits <= hi, over random num, den, level, and bits, tiny bits
    included, checked in exact integers."""
    import random

    from ema.designs.convergent import _power_bounds

    rng = random.Random(20261002)
    for trial in range(2000):
        num, den = rng.randint(1, 2**40), rng.randint(1, 2**40)
        level = rng.randint(0, 300)
        bits = rng.choice([1, 2, 3, 5, 8, 13]) if trial % 2 else rng.randint(1, 256)
        lo, hi = _power_bounds(num, den, level, bits)
        exact_num, exact_den = num**level << bits, den**level
        assert 0 <= lo <= hi and lo * exact_den <= exact_num <= hi * exact_den, (num, den, level, bits)


def test_ceil_size_refines_its_bounds(monkeypatch):
    """``_ceil_size`` from 8 bits: the first bounds don't agree, and the doubled ones give the exact size."""
    from fractions import Fraction

    from ema.designs import convergent

    calls = []
    power_bounds = convergent._power_bounds

    def counted(num, den, level, bits):
        calls.append(bits)
        return power_bounds(num, den, level, bits)

    monkeypatch.setattr(convergent, "_power_bounds", counted)
    factor = (1 / Fraction("0.999")) ** 2
    for n_min in (1, 5, 12345):
        calls.clear()
        exact = -(-n_min * factor.numerator**900 // factor.denominator**900)
        assert convergent._ceil_size(n_min, factor, 900, bits=8) == exact
        assert calls[:2] == [8, 16], calls
