"""Deterministic portfolio backtest. Adjusted closes are total-return proxies."""
import numpy as np
import pandas as pd


def validate_prices(prices, weights):
    if prices.empty or not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError('날짜가 있는 가격 데이터가 필요합니다.')
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError('가격 날짜는 중복 없이 오름차순이어야 합니다.')
    if set(weights) != set(prices.columns):
        raise ValueError('종목과 가격 열이 일치하지 않습니다.')
    if prices.isna().any().any() or not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError('가격에 결측값, 무한대 또는 0 이하 값이 있습니다.')
    if any(v < 0 for v in weights.values()) or not np.isclose(sum(weights.values()), 1.0, atol=1e-8):
        raise ValueError('비중 합계는 100%여야 합니다.')


def backtest(prices, weights, initial_krw, monthly_krw, rebalance='none', fee_bps=0.0, fractional=True):
    """Buy on first available session and on first session of each *subsequent* calendar month.
    For rebalance, sell and buy at same day's adjusted close; fees on each side.
    Fractional shares are used; returns based on adjusted close, approximating dividend reinvestment.
    """
    validate_prices(prices, weights)
    if min(initial_krw, monthly_krw, fee_bps) < 0 or initial_krw + monthly_krw <= 0:
        raise ValueError('투자금은 양수, 수수료는 0 이상이어야 합니다.')
    if rebalance not in ('none', 'monthly', 'yearly'):
        raise ValueError('리밸런싱 설정 오류')
    if not fractional:
        raise NotImplementedError('정수 주식 거래는 현재 지원하지 않습니다.')
    tickers = list(weights)
    p = prices[tickers].astype(float)
    w = np.array([weights[t] for t in tickers], dtype=float)
    units = np.zeros(len(tickers))
    cash = float(initial_krw)
    paid = float(initial_krw)
    fee = fee_bps / 10000.0
    rows, flows, fee_total = [], [], 0.0
    last_month, last_period = None, None
    for i, (dt, row) in enumerate(p.iterrows()):
        month = (dt.year, dt.month)
        contribution = 0.0
        if i == 0:
            contribution = float(initial_krw)
        elif month != last_month:
            cash += monthly_krw
            paid += monthly_krw
            contribution = float(monthly_krw)
        current = row.to_numpy(dtype=float)
        period = month if rebalance == 'monthly' else dt.year
        rebalance_now = rebalance != 'none' and i > 0 and period != last_period
        if rebalance_now:
            sell_gross = float(np.dot(units, current))
            sell_fee = sell_gross * fee
            fee_total += sell_fee
            cash += sell_gross - sell_fee
            units[:] = 0
        if i == 0 or rebalance_now:
            allocation = cash * w / (1 + fee)
        elif month != last_month and monthly_krw:
            allocation = monthly_krw * w / (1 + fee)
        else:
            allocation = np.zeros(len(tickers))
        buy_fee = float(allocation.sum() * fee)
        fee_total += buy_fee
        units += allocation / current
        cash -= float(allocation.sum()) + buy_fee
        value = float(np.dot(units, current) + cash)
        rows.append((dt, value, paid, cash, contribution, fee_total, *list(units * current)))
        flows.append((dt, contribution))
        last_month, last_period = month, period
    result = pd.DataFrame(rows, columns=['date','value','principal','cash','contribution','cumulative_fees'] + [f'asset_{t}' for t in tickers]).set_index('date')
    # Daily time-weighted return excludes external deposits at session start.
    prev_value = result.value.shift(1)
    daily_returns = ((result.value - result.contribution) / prev_value - 1).iloc[1:]
    wealth_index = (1 + daily_returns).cumprod()
    wealth_index = pd.concat([pd.Series([1.0], index=result.index[:1]), wealth_index])
    drawdown = wealth_index / wealth_index.cummax() - 1
    result['strategy_index'] = wealth_index
    result['drawdown'] = drawdown
    duration = (result.index[-1] - result.index[0]).days / 365.25
    twr_cagr = float(wealth_index.iloc[-1] ** (1 / duration) - 1) if duration > 0 else np.nan
    metrics = {
        'final':float(result.value.iloc[-1]), 'principal':float(result.principal.iloc[-1]),
        'profit':float(result.value.iloc[-1] - result.principal.iloc[-1]),
        'roi':float(result.value.iloc[-1] / result.principal.iloc[-1] - 1),
        'mdd':float(drawdown.min()), 'twr_cagr':twr_cagr,
        'fees':float(fee_total), 'start':result.index[0], 'end':result.index[-1]
    }
    return result, metrics


def buy_timing_bounds(prices, weights, amount):
    """Asset-wise ex-post oracle bound; NOT a feasible common-date portfolio trade."""
    validate_prices(prices, weights)
    final = prices.iloc[-1]
    best = sum(amount * weights[t] * final[t] / prices[t].min() for t in weights)
    worst = sum(amount * weights[t] * final[t] / prices[t].max() for t in weights)
    return float(best), float(worst)


def common_date_timing(prices, weights, amount):
    """Buy entire portfolio on one of the observed trading days; evaluate at final close."""
    validate_prices(prices, weights)
    terminal = prices.iloc[-1]
    outcomes = sum(amount * weights[t] * terminal[t] / prices[t] for t in weights)
    return {'best_date':outcomes.idxmax(), 'best_value':float(outcomes.max()),
            'worst_date':outcomes.idxmin(), 'worst_value':float(outcomes.min())}
