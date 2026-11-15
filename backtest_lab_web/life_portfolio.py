"""Life Portfolio v1.5: input validation and independent questionnaire scoring.
No personal financial data is sent to an external API by this module.
Scores are descriptive and NOT validated psychometric or investment suitability assessments.
"""
from dataclasses import dataclass
from typing import Mapping

QUESTIONS = [('risk', '10년 뒤 사용할 투자금이 1년 만에 25% 줄었다면, 나는 당장 팔기보다 계획을 다시 확인할 것이다.'), ('risk', '안정적인 연 3%와 손실 가능성이 있지만 더 높은 수익 기회 중 후자에 더 끌린다.'), ('risk', '주변 사람들이 주식시장이 위험하다고 말해도 내 투자 기간에 맞춰 판단할 수 있다.'), ('risk', '내가 가진 주식이 며칠 사이 크게 흔들려도 잠을 설치지는 않을 것 같다.'), ('discipline', '좋아하는 종목이 급등할 때도 사전에 정한 투자 비중을 지키는 편이다.'), ('discipline', '친구가 큰돈을 벌었다는 소식을 들어도 바로 따라 사지는 않는다.'), ('discipline', '주가가 떨어지면 뉴스만 보고 즉시 행동하기보다 투자 이유가 달라졌는지 살펴본다.'), ('discipline', '투자 결과가 예상과 다를 때 감정보다 기록과 근거를 먼저 확인한다.'), ('horizon', '지금 당장 보상이 작더라도 10년 뒤 더 큰 결과를 얻는 선택이 마음에 든다.'), ('horizon', '내가 투자한 자산이 2~3년 제자리여도 장기 계획을 유지할 수 있다.'), ('horizon', '1년 뒤 쓸 돈과 10년 뒤 쓸 돈은 서로 다르게 운용해야 한다고 생각한다.'), ('horizon', '투자 성과를 볼 때 이번 달보다 지난 몇 년간의 흐름이 더 중요하다.'), ('knowledge', '주식 여러 종목에 나누어 투자해도 시장 전체가 하락하면 손실을 볼 수 있음을 안다.'), ('knowledge', '채권도 금리 변화에 따라 가격이 하락할 수 있음을 알고 있다.'), ('knowledge', '미국 주식이 달러로 올라도 원화 환산 수익률은 환율 때문에 낮아질 수 있음을 안다.'), ('knowledge', '레버리지 ETF는 지수의 장기 누적 수익률을 단순히 배수로 따라가지 않을 수 있음을 안다.')]
AXES = {'risk':'심리적 위험 수용도','discipline':'투자 원칙 유지','horizon':'장기 투자 선호','knowledge':'투자 이해도(자가평가)'}


def validate_profile(p: Mapping) -> list[str]:
    errors=[]
    for key, label in [('age','나이'),('income','본인 월 실수령액'),('expenses','월 생활·고정지출'),('cash','현금성 자산'),('investments','기존 투자자산'),('debt','총 부채'),('debt_payment','월 대출상환액'),('support','월 부양비'),('insurance','월 보험료'),('taxes','월 별도 세금'),('irregular','월 환산 비정기 지출'),('goal_years','목표 기간')]:
        try: v=float(p.get(key,0) if key in ("insurance","taxes","irregular") else p[key])
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
    outflow=sum(float(p.get(k,0)) for k in ('expenses','debt_payment','support','insurance','taxes','irregular'))
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


def portfolio_candidates(profile, scores):
    """Educational asset-class examples, not personalized securities advice."""
    snap=finance_snapshot(profile)
    reasons=[]
    if snap['monthly_surplus']<=0:reasons.append('월 잉여현금이 0원 이하입니다. 신규 투자보다 현금흐름 점검이 우선입니다.')
    if snap['reserve_months'] is None:reasons.append('월 지출이 0원으로 입력되어 비상자금 개월 수를 계산할 수 없습니다.')
    elif snap['reserve_months']<6:reasons.append('비상자금이 월 지출 6개월분 미만입니다. 예시 기준으로 우선 확보를 검토하세요.')
    if profile['goal_years']<=3:reasons.append('목표 기간이 3년 이하입니다. 목표자금은 변동성이 큰 자산과 분리해 검토하세요.')
    if profile.get('goal_amount',0)>snap['monthly_surplus']*12*profile['goal_years']+profile['cash']:
        reasons.append('단순 적립만으로 목표 금액이 부족할 수 있어 지출·기간·저축액을 재검토해야 합니다.')
    if profile.get('debt',0)>0:reasons.append('대출 금리와 상환 부담을 투자 기대수익과 별도로 비교해야 합니다.')
    # Conservative guardrails: profile capacity overrides psychological willingness.
    constrained=(snap['monthly_surplus']<=0 or (snap['reserve_months'] is not None and snap['reserve_months']<3) or profile['goal_years']<=3)
    if constrained:
        model='자금 안전성 우선 검토'
        examples=[('안정 우선 비교안',20,30,50),('균형 비교안',40,40,20)]
    elif scores['risk']<35:
        model='안정 선호 비교'
        examples=[('안정 우선 비교안',20,50,30),('균형 비교안',40,40,20)]
    elif scores['risk']<70:
        model='균형 선호 비교'
        examples=[('균형 비교안',50,40,10),('성장 비교안',70,25,5)]
    else:
        model='성장 선호 비교'
        examples=[('균형 비교안',50,40,10),('성장 비교안',70,25,5)]
    return {'model':model,'constrained':constrained,'reasons':reasons,
            'examples':[{'name':name,'주식':equity,'채권':bonds,'현금성':cash} for name,equity,bonds,cash in examples],
            'monthly_surplus':snap['monthly_surplus']}


# Reference model portfolios. All percentages are of the investable long-term sleeve,
# AFTER segregating emergency reserves and near-term goal funds.
# SHV is short-term US Treasury exposure, not an insured KRW deposit.
MODEL_PORTFOLIOS = [
    {'name':'안정 우선 ETF', 'style':'stable', 'holdings':{'VOO':20,'SCHD':10,'IEF':20,'SHV':50}, 'note':'단기 국채 ETF도 환율·가격 변동 위험이 있습니다.'},
    {'name':'균형 분산 ETF', 'style':'balanced', 'holdings':{'VOO':40,'SCHD':15,'QQQM':10,'IEF':20,'SHV':15}, 'note':'미국 주식·채권을 혼합한 비교안입니다.'},
    {'name':'장기 성장 ETF', 'style':'growth', 'holdings':{'VOO':45,'QQQM':30,'SCHD':15,'SHV':10}, 'note':'VOO와 QQQM의 대형 기술주 중복 노출에 주의하세요.'},
    {'name':'인컴 중심 ETF', 'style':'income', 'holdings':{'VOO':30,'SCHD':30,'JEPI':15,'JEPQ':10,'SHV':15}, 'note':'옵션 프리미엄 분배금은 확정 수익이나 예금 이자가 아닙니다.'},
    {'name':'버핏 90/10 참고', 'style':'growth', 'holdings':{'VOO':90,'SHV':10}, 'note':'버핏의 원칙을 ETF로 근사한 교육용 예시입니다. SHV는 단기 미국 국채 ETF이며 정확한 동일 상품은 아닙니다.'},
    {'name':'금리 민감 분산', 'style':'balanced', 'holdings':{'VOO':40,'SCHD':15,'TLT':15,'IEF':15,'SHV':15}, 'note':'TLT는 장기채로 금리 상승 시 큰 가격 손실이 발생할 수 있습니다.'},
]

PRODUCT_WARNINGS = {
    'QLD':'나스닥100 일일 2배 레버리지 상품으로 장기 누적 수익률이 단순 2배가 아닙니다. 기본 후보에서 제외합니다.',
    'QQQ':'QQQM과 같은 나스닥100 지수 노출이므로 둘을 함께 보유해도 분산 효과가 제한적입니다.',
    'QQQI':'옵션 인컴 전략은 분배금이 높아도 원금 손실 및 상승 제한 가능성이 있습니다.',
    'O':'개별 리츠 주식으로 금리·부동산·개별기업 위험이 있어 기본 분산 ETF 모델에서 제외합니다.',
    'JEPQ':'옵션 인컴 전략은 상승 참여가 제한될 수 있고 분배금은 보장되지 않습니다.',
    'JEPI':'옵션 인컴 전략은 상승 참여가 제한될 수 있고 분배금은 보장되지 않습니다.',
    'TLT':'장기 미국 국채 ETF는 금리 변화에 매우 민감하며 원화 기준 환율 위험도 있습니다.',
}


def product_portfolios(profile, scores):
    """Return ranked, non-transactional ETF model comparisons with safety constraints."""
    analysis=portfolio_candidates(profile,scores)
    snap=finance_snapshot(profile)
    reserve_target=6*snap['monthly_outflow']
    reserve_gap=max(0,reserve_target-float(profile['cash']))
    # Goals are not assumed funded: subtract them from immediately available cash.
    available=max(0,float(profile['cash'])-reserve_target-float(profile.get('goal_amount',0)))
    constrained=analysis['constrained'] or reserve_gap>0
    preferred='stable' if constrained or scores['risk']<35 else ('balanced' if scores['risk']<70 else 'growth')
    ranked=[]
    for model in MODEL_PORTFOLIOS:
        match = model['style']==preferred
        ranked.append({**model,'match':match,'sum_weight':sum(model['holdings'].values())})
    ranked.sort(key=lambda m:(not m['match'],m['name']))
    return {'preferred':preferred,'models':ranked,'reserve_target':reserve_target,'reserve_gap':reserve_gap,
            'cash_after_reserve_and_goal':available,'constrained':constrained,'reasons':analysis['reasons'],
            'warnings':PRODUCT_WARNINGS}
