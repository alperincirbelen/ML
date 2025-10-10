from moonlight.indicators.basic import ema, rsi


def test_ema_basic():
    vals = [1, 2, 3, 4, 5, 6]
    out = ema(vals, 3)
    # First two are None, then values
    assert out[0] is None and out[1] is None
    assert out[-1] is not None


def test_rsi_bounds():
    vals = [i for i in range(1, 50)]
    out = rsi(vals, 14)
    last = out[-1]
    assert last is not None
    assert 0.0 <= last <= 100.0
