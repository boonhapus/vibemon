import pytest

from app.providers.helpers import Signal


def test_signal_linear_normal_and_center() -> None:
    signal = Signal(name="demo", attr="demo", raw=50.0, min=0.0, med=50.0, max=100.0)
    assert signal.normal == 0.5
    assert signal.center == 0.5


def test_signal_log10_axis_matches_log_population_binding() -> None:
    signal = Signal(
        name="pop",
        attr="population",
        raw=1_000_000,
        min=50,
        med=100_000,
        max=30_000_000,
        axis="log10",
    )
    low = Signal(name="pop", attr="population", raw=1_000, min=50, med=100_000, max=30_000_000, axis="log10")
    high = Signal(name="pop", attr="population", raw=8_000_000, min=50, med=100_000, max=30_000_000, axis="log10")
    assert 0.0 < low.normal < signal.normal < high.normal <= 1.0


def test_signal_log10_center_anchors_at_median_population() -> None:
    signal = Signal(
        name="pop",
        attr="population",
        raw=100_000,
        min=50,
        med=100_000,
        max=30_000_000,
        axis="log10",
    )
    assert signal.center == pytest.approx(0.5)


def test_signal_log10_requires_positive_min() -> None:
    with pytest.raises(ValueError, match="axis='log10' requires min > 0"):
        Signal(name="pop", attr="population", raw=100.0, min=0.0, med=50.0, max=100.0, axis="log10")


def test_signal_weighted_pairs_for_mix() -> None:
    signal = Signal(name="demo", attr="demo", raw=10.0, min=0.0, med=5.0, max=20.0)
    paired = signal.weighted(0.5)
    assert paired == (signal, 0.5)
    assert signal * 0.5 == (signal, 0.5)


def test_signal_ramp_normal_uses_axis() -> None:
    linear = Signal(name="demo", attr="demo", raw=75.0, min=0.0, med=50.0, max=100.0)
    assert linear.ramp("N", thresh=0.5, reach=0.5) == pytest.approx(0.5)

    log_signal = Signal(name="pop", attr="population", raw=1_000_000, min=50, med=100_000, max=30_000_000, axis="log10")
    assert log_signal.ramp("N", thresh=0.0, reach=1.0) == pytest.approx(log_signal.normal)
