"""Streamlit UI for Life Portfolio. Profile and psychology are separate forms."""
import streamlit as st
import pandas as pd
import re
from life_portfolio import QUESTIONS, AXES, validate_profile, finance_snapshot, score_answers, interpret, portfolio_candidates


def amount(label,key,default):
    if key not in st.session_state:
        st.session_state[key]=f'{default:,}'
    raw=st.text_input(label,key=key,help='원 단위 · 쉼표로 구분하여 입력')
    if not re.fullmatch(r'\d[\d,]*',raw.strip()):
        st.error(f'{label}: 숫자를 입력해 주세요.')
        return None
    return int(raw.replace(',',''))


def render():
    st.title('🧠 Life Portfolio | 나의 투자 성향과 재무 상황')
    st.caption('Backtest Lab v1.5 · 재무정보와 투자 성향 검사를 독립적으로 진행합니다. 현재 결과는 교육·자가점검용이며 금융상품 추천이 아닙니다.')
    st.info('입력값과 설문 답변은 이 앱의 현재 Streamlit 세션에만 보관하도록 구현했습니다. 서버 DB에 저장하거나 외부 AI에 전송하지 않습니다. 공유 기기 사용 시 세션을 종료하세요.')
    tab1,tab2,tab3=st.tabs(['① 필수 재무정보','② 투자 성향 검사','③ 통합 결과'])
    with tab1:
        st.subheader('기본 정보와 가족 구성')
        with st.form('life_finance_form'):
            a,b=st.columns(2)
            with a:
                age=st.number_input('나이 (만)',18,100,30)
                marital=st.selectbox('혼인 상태',['미혼','기혼','기타/응답하지 않음'])
                dependents=st.number_input('부양가족 수 (배우자 제외)',0,30,0)
                goal_years=st.number_input('주요 투자 목표까지 남은 기간 (년)',1,60,10)
                income=amount('본인 월 실수령액 (원)','life_income',3500000)
                partner_income=amount('배우자 월 실수령액 (원, 해당 없으면 0)','life_partner_income',0)
            with b:
                expenses=amount('월 생활비·고정지출 (대출·부양비 제외, 원)','life_expenses',1500000)
                debt_payment=amount('월 대출 원리금 상환액 (원)','life_debt_payment',0)
                support=amount('월 가족·부모 부양비 (원)','life_support',0)
                cash=amount('현금성 자산 (원)','life_cash',10000000)
                investments=amount('기존 금융투자 자산 (원)','life_investments',0)
                debt=amount('총 부채 잔액 (원)','life_debt',0)
            goals=st.multiselect('향후 주요 계획 (선택)', ['결혼','출산·육아','주택 구매·이사','자녀 교육','부모 부양','이직·휴직','은퇴','기타'])
            goal_amount=amount('목표에 필요한 금액 (원, 모르면 0)','life_goal_amount',0)
            submitted=st.form_submit_button('재무정보 검증 및 저장',type='primary')
        if submitted:
            if any(x is None for x in (income,partner_income,expenses,debt_payment,support,cash,investments,debt,goal_amount)):
                st.error('금액 입력값을 확인하세요.')
                st.stop()
            profile=dict(age=age,marital=marital,dependents=dependents,goal_years=goal_years,income=income,partner_income=partner_income if marital=='기혼' else 0,
                         expenses=expenses,debt_payment=debt_payment,support=support,cash=cash,investments=investments,debt=debt,goals=goals,goal_amount=goal_amount)
            errors=validate_profile(profile)
            if errors:
                for e in errors:st.error(e)
            else:
                st.session_state['life_profile']=profile
                st.success('재무정보 저장 완료. 투자 성향 검사는 별도 탭에서 진행하세요.')
        if 'life_profile' in st.session_state:
            snap=finance_snapshot(st.session_state['life_profile'])
            c1,c2,c3=st.columns(3)
            c1.metric('월 가구 소득',f'{snap["monthly_income"]:,.0f}원')
            c2.metric('월 잉여현금',f'{snap["monthly_surplus"]:,.0f}원')
            c3.metric('현금성 자산 유지 가능 기간',f'{snap["reserve_months"]:.1f}개월' if snap['reserve_months'] is not None else '계산 불가')
            st.caption('잉여현금은 입력된 월 소득에서 지출·대출상환·부양비를 뺀 값이며 실제 투자 가능액을 보장하지 않습니다.')
    with tab2:
        st.subheader('독립적인 투자 성향 검사')
        st.write('총 16문항 · 일상 상황을 상상하면서 답해 보세요. 1점은 전혀 그렇지 않다, 5점은 매우 그렇다입니다.')
        st.caption('재무정보는 이 검사 점수에 반영하지 않습니다. 이 검사는 자체 제작한 자가평가 설문으로 심리측정학적 타당성이 검증되지 않았습니다.')
        with st.form('life_psych_form'):
            answers={}
            for i,(axis,q) in enumerate(QUESTIONS):
                answers[i]=st.radio(f'{i+1}. {q}',[1,2,3,4,5],horizontal=True,index=None,key=f'life_q_{i}',format_func=lambda n: f'{n}점')
            done=st.form_submit_button('검사 결과 계산',type='primary')
        if done:
            if any(v is None for v in answers.values()):st.error('모든 문항에 답변해 주세요.')
            else:
                scores=score_answers(answers)
                st.session_state['life_scores']=scores
                st.success(f'검사 완료: {interpret(scores)}')
        if 'life_scores' in st.session_state:
            for axis,label in AXES.items():
                score=st.session_state['life_scores'][axis]
                st.write(f'**{label}** · {score:.1f}/100')
                st.progress(score/100)
    with tab3:
        if 'life_profile' not in st.session_state or 'life_scores' not in st.session_state:
            missing=[]
            if 'life_profile' not in st.session_state:missing.append('재무정보')
            if 'life_scores' not in st.session_state:missing.append('투자 성향 검사')
            st.warning('통합 분석을 보려면 '+', '.join(missing)+'를 완료하세요.')
            return
        p=st.session_state['life_profile']; scores=st.session_state['life_scores']; snap=finance_snapshot(p)
        st.subheader(f'검사 유형: {interpret(scores)}')
        a,b,c=st.columns(3)
        a.metric('심리적 위험 수용도',f'{scores["risk"]:.0f}/100')
        b.metric('월 잉여현금',f'{snap["monthly_surplus"]:,.0f}원')
        c.metric('현금성 자산 유지 가능 기간',f'{snap["reserve_months"]:.1f}개월' if snap['reserve_months'] is not None else '계산 불가')
        st.subheader('재무 제약 점검')
        if snap['monthly_surplus']<=0:st.error('현재 입력값 기준 월 잉여현금이 없습니다. 신규 투자보다 지출·부채 현금흐름 점검이 우선입니다.')
        elif snap['reserve_months'] is not None and snap['reserve_months']<3:st.warning('현금성 자산이 월 지출 3개월 미만입니다. 비상자금 확보를 우선 검토하세요. 3개월은 예시 기준이며 개인별 필요액은 다릅니다.')
        else:st.info('현금흐름과 비상자금은 입력값 기준으로 계산되었습니다. 보험·세금·비정기 지출 등을 추가 검토해야 합니다.')
        if p['goal_years']<=3 or p['goal_amount']>0:
            st.warning('가까운 목표 또는 목돈 계획이 있습니다. 사용 시점이 정해진 자금은 장기 위험자산과 분리해 검토하세요.')
        st.subheader('자산배분 후보 비교 (교육용 예시)')
        candidates=portfolio_candidates(p,scores)
        st.info(f"분석 방향: **{candidates['model']}** · 실제 상품 매수 추천이 아닌 자산군 배분 예시입니다.")
        for reason in candidates['reasons']:
            st.warning(reason)
        st.dataframe(pd.DataFrame(candidates['examples']).style.format({'주식':'{}%','채권':'{}%','현금성':'{}%'}),hide_index=True,use_container_width=True)
        st.caption('위 비중은 검증된 개인별 최적 비중이 아닙니다. 주식·채권·현금성 자산의 교육용 비교안이며, 단기 목표자금과 비상자금은 별도로 확보해야 합니다. 특정 ETF 자동 매수 권유는 제공하지 않습니다.')
        st.subheader('검사 결과와 재무정보를 함께 보는 방법')
        st.write('심리적 위험 수용도와 실제 재무적 손실 감내 능력은 별개입니다. 지금은 두 결과를 나란히 보여주며 특정 ETF·주식 비중을 자동 추천하지 않습니다.')
        st.dataframe(pd.DataFrame([{'평가 항목':'심리적 위험 수용도','결과':f'{scores["risk"]:.0f}/100'},
                                  {'평가 항목':'월 잉여현금','결과':f'{snap["monthly_surplus"]:,.0f}원'},
                                  {'평가 항목':'주요 목표까지','결과':f'{p["goal_years"]}년'},
                                  {'평가 항목':'목표 필요금액','결과':f'{p["goal_amount"]:,.0f}원'}]),hide_index=True,use_container_width=True)
        st.caption('v1.6: 자산군 비교 후보 추가. 실제 투자 상품 추천·기존 백테스트 자동 연결은 추후 검증 후 구현 예정입니다.')
        if st.button('현재 Life Portfolio 세션 데이터 삭제'):
            for k in list(st.session_state):
                if k.startswith('life_'):del st.session_state[k]
            st.rerun()
