from moonlight.connector.mock import MockConnector


def test_mock_candles_len():
    cx = MockConnector(account_id="acc1", seed=123)
    candles = cx.get_candles("EURUSD", timeframe=1, n=120)
    assert len(candles) == 120
    assert set(["ts","open","high","low","close","volume"]).issubset(candles[-1].keys())
