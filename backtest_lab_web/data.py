"""Historical USD adjusted-close and KRW/USD prices. Never fabricate observations."""
from datetime import timedelta
import pandas as pd
import yfinance as yf


def close_series(ticker, start, end):
    frame = yf.download(ticker, start=start, end=end + timedelta(days=1), auto_adjust=True,
                        progress=False, threads=False, timeout=25)
    if frame is None or frame.empty:
        raise ValueError(f'{ticker}: 조회된 가격이 없습니다. 티커/상장일을 확인하세요.')
    if isinstance(frame.columns, pd.MultiIndex):
        close = frame['Close']
        s = close[ticker] if ticker in close else close.iloc[:, 0]
    else:
        s = frame['Close']
    s = pd.to_numeric(s, errors='coerce').dropna()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    s = s[~s.index.duplicated(keep='last')].sort_index()
    s = s[s > 0]
    if s.empty:
        raise ValueError(f'{ticker}: 유효한 종가가 없습니다.')
    return s.rename(ticker)


def historical_data(tickers, start, end):
    """Return (USD adjusted prices, KRW per USD FX) on common stock sessions.
    FX only forward-filled from earlier observations, never backfilled from future.
    """
    if not 1 <= len(tickers) <= 10 or len(set(tickers)) != len(tickers):
        raise ValueError('서로 다른 종목을 1~10개 선택하세요.')
    stocks = pd.concat([close_series(t, start, end) for t in tickers], axis=1).dropna()
    stocks = stocks.loc[(stocks.index.date >= start) & (stocks.index.date <= end)]
    if stocks.empty:
        raise ValueError('선택한 종목의 공통 거래일이 없습니다.')
    fx = close_series('KRW=X', start - timedelta(days=20), end)
    fx = fx.reindex(stocks.index, method='ffill')
    valid = fx.notna() & (fx > 0)
    stocks, fx = stocks.loc[valid], fx.loc[valid]
    if len(stocks) < 2:
        raise ValueError('종목·환율 공통 데이터가 2거래일 미만입니다.')
    return stocks, fx
