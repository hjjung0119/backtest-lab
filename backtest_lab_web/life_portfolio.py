"""Life Portfolio v1.5: input validation and independent questionnaire scoring.
No personal financial data is sent to an external API by this module.
Scores are descriptive and NOT validated psychometric or investment suitability assessments.
"""
from dataclasses import dataclass
from typing import Mapping

QUESTIONS = [
 ('risk','보유 투자자산이 20% 하락해도 계획을 유지할 수 있다.'),
 ('risk','단기간 손실 가능성이 있어도 장기 수익 기회를 추구한다.'),
 ('risk','자산가격의 큰 변동을 감정적으로 견딜 수 있다.'),
 ('risk','투자 원금의 일시적인 감소를 받아들일 수 있다.'),
 ('discipline','투자 전 정한 매수·매도 기준을 지킨다.'),
 ('discipline','급격한 뉴스에도 즉흥적인 매매를 자제한다.'),
 ('discipline','투자 성과를 정기적으로 점검하되 잦은 매매는 피한다.'),
 ('discipline','투자 실패 원인을 기록하고 계획을 수정한다.'),
 ('horizon','단기 수익보다 장기적인 자산 성장을 중시한다.'),
 ('horizon','몇 년간 성과가 부진해도 투자 원칙을 유지할 수 있다.'),
 ('horizon','장기 목표를 위해 단기 소비를 미룰 수 있다.'),
 ('horizon','자산을 평가할 때 1개월보다 5년 이상의 성과를 중시한다.'),
 ('knowledge','분산투자가 개별 종목 위험을 줄이는 원리를 설명할 수 있다.'),
 ('knowledge','채권과 주식의 가격 변동 특성을 구분할 수 있다.'),
 ('knowledge','환율 변동이 해외투자 원화 수익률에 미치는 영향을 이해한다.'),
 ('knowledge','레버리지 ETF의 장기 보유 위험을 이해한다.'),
]
AXES = {'risk':'심리적 위험 수용도','discipline':'투자 원칙 유지','horizon':'장기 투자 선호','knowledge':'투자 이해도(자가평가)'}


def validate_profile(p: Mapping) -> list[str]:
    errors=[]
    for key, label in [('age','나이'),('income','본인 월 실수령액'),('expenses','월 생활·고정지출'),('cash','현금성 자산'),('investments','기존 투자자산'),('debt','총 부채'),('debt_payment','월 대출상환액'),('support','월 부양비'),('goal_years','목표 기간')]:
        try: v=float(p[key])
        except (KeyError, TypeError, ValueError):
            errors.append(f'{label}을 입력하세요.');continue
        if v < 0: errors.append(f'{label}은 음수일 수 없습니다.')
    if not errors:
        if not 18 <= p['age'] <= 100:errors.append('나이는 18~100세로 입력하세요.')
        if not 1 <= p['goal_years'] <= 60:errors.append('목표 기간은 1~60년이어야 합니다.')
        if p.get('marital') == '기혼' and p.get('partner_income',0)<0:errors.append('배우자 소득은 음수일 수 없습니다.')
        if p.get('dependents',0)<0:errors.append('부양가족 수는 음수일 수 없습니다.')
    return errors


def finance_snapshot(p: Mapping) -> dict:
    errors=validate_profile(p)
    if errors:raise ValueError('; '.join(errors))
    income=float(p['income'])+float(p.get('partner_income',0))
    outflow=float(p['expenses'])+float(p['debt_payment'])+float(p['support'])
    surplus=income-outflow
    liquid=float(p['cash'])
    reserve_months=liquid/outflow if outflow>0 else None
    return {'monthly_income':income,'monthly_outflow':outflow,'monthly_surplus':surplus,
            'reserve_months':reserve_months,'monthly_investable_ceiling':max(0,surplus),
            'net_financial_assets':liquid+float(p['investments'])-float(p['debt'])}


def score_answers(answers: Mapping[int,int]) -> dict[str,float]:
    if set(answers) != set(range(len(QUESTIONS))):raise ValueError('모든 문항에 응답해야 합니다.')
    result={}
    for axis in AXES:
        values=[answers[i] for i,(a,_) in enumerate(QUESTIONS) if a==axis]
        if any(not isinstance(v,int) or not 1<=v<=5 for v in values):raise ValueError('답변은 1~5점이어야 합니다.')
        result[axis]=round((sum(values)/len(values)-1)*25,1)
    return result


def interpret(scores: Mapping) -> str:
    risk=scores['risk']
    if risk < 35:return '안정 선호형'
    if risk < 70:return '균형 탐색형'
    return '성장 선호형'
