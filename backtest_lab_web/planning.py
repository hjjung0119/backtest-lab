"""Deterministic planning helpers; estimates, not tax/legal advice."""
from datetime import date
import math
import pandas as pd


def fx_asof(dates, fx):
    """Use last observed KRW/USD quote at or before each requested date."""
    series = pd.Series(fx, dtype=float).sort_index()
    series.index = pd.to_datetime(series.index).normalize()
    if series.empty or (series <= 0).any():
        raise ValueError('유효한 환율 데이터가 없습니다.')
    out = []
    for d in dates:
        dt = pd.Timestamp(d).normalize()
        valid = series.loc[series.index <= dt]
        if valid.empty or (dt - valid.index[-1]).days > 10:
            raise ValueError(f'{dt.date()} 환율 자료가 없거나 너무 오래되었습니다.')
        out.append(float(valid.iloc[-1]))
    return out


def tax_scenarios(lots, sale_date, sale_price_usd, fx_buy, fx_sell, ratios=(0.25,0.5,1.0),
                  fee_rate=0.0005, deduction=2_500_000, tax_rate=0.22, other_realized_krw=0):
    """Simple Korea overseas stock gains model for ONE selected tax year.
    Each lot is (purchase date, shares, purchase price USD). Proportional sale of all lots.
    Existing realized gains in same year supplied explicitly. Not a tax return calculator.
    """
    if not lots or len(lots) != len(fx_buy) or sale_price_usd <= 0 or fx_sell <= 0:
        raise ValueError('매수 내역·매도가·환율을 확인하세요.')
    if not 0 <= fee_rate < 1 or deduction < 0 or not 0 <= tax_rate <= 1:
        raise ValueError('수수료·공제액·세율을 확인하세요.')
    for row in lots:
        if row['shares'] <= 0 or row['buy_price_usd'] <= 0 or pd.Timestamp(row['buy_date']).date() > sale_date:
            raise ValueError('매수일·수량·매수가를 확인하세요.')
    results=[]
    for ratio in ratios:
        if not 0 < ratio <= 1: raise ValueError('매도 비율은 0~100% 범위여야 합니다.')
        gross = sum(row['shares'] * ratio * sale_price_usd * fx_sell for row in lots)
        basis = sum(row['shares'] * ratio * row['buy_price_usd'] * rate for row,rate in zip(lots,fx_buy))
        purchase_fees = basis * fee_rate
        sale_fees = gross * fee_rate
        gain = gross - basis - purchase_fees - sale_fees
        # Incremental tax versus already-realized same-year gain; not whole tax bill.
        baseline_tax = max(0., other_realized_krw-deduction)*tax_rate
        total_tax = max(0., other_realized_krw+gain-deduction)*tax_rate
        incremental_tax = total_tax-baseline_tax
        results.append({'매도 비율':f'{ratio:.0%}','매도 수량':sum(row['shares']*ratio for row in lots),
                        '매도대금(원)':gross,'취득원가(원)':basis,'매매비용(원)':purchase_fees+sale_fees,
                        '이번 매도 손익(원)':gain,'추가 예상세액(원)':incremental_tax,
                        '세후 매도현금(원)':gross-sale_fees-incremental_tax})
    return pd.DataFrame(results)


def rebalance_orders(holdings, target, prices, cash=0, fee_rate=0):
    """Fractional-share target orders, excluding taxes and FX conversion."""
    if set(holdings)!=set(target) or set(target)!=set(prices) or abs(sum(target.values())-1)>1e-8:
        raise ValueError('종목과 목표 비중 합계를 확인하세요.')
    if cash < 0 or not 0<=fee_rate<1 or any(x<0 for x in holdings.values()) or any(x<=0 for x in prices.values()):
        raise ValueError('수량·가격·수수료를 확인하세요.')
    total = cash+sum(holdings[t]*prices[t] for t in target)
    # Without fees exact target. Fees cause slight residual differences; mark estimate.
    rows=[]
    for t in target:
        before=holdings[t]*prices[t]
        desired=total*target[t]
        delta=(desired-before)/prices[t]
        rows.append({'티커':t,'현재 비중':before/total if total else 0,'목표 비중':target[t],
                     '거래 방향':'매수' if delta>1e-9 else ('매도' if delta< -1e-9 else '유지'),
                     '거래 수량(소수점 허용)':abs(delta),'거래 금액':abs(delta)*prices[t],
                     '예상 수수료':abs(delta)*prices[t]*fee_rate})
    return pd.DataFrame(rows)


def goal_scenarios(initial, monthly, years, target, annual_returns=(-0.1,0.0,0.05,0.1)):
    """Illustrative constant-return scenarios, NOT probability forecasts."""
    if min(initial,monthly,years,target)<0 or years<=0:raise ValueError('입력 금액·기간을 확인하세요.')
    rows=[]
    months=round(years*12)
    for annual in annual_returns:
        r=(1+annual)**(1/12)-1
        value=float(initial)
        for _ in range(months):value=value*(1+r)+monthly
        rows.append({'연간 수익률 가정':f'{annual:+.0%}','기간 종료 자산':value,
                     '목표 대비 차이':value-target,'목표 달성':value>=target})
    return pd.DataFrame(rows)
