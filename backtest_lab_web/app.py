"""Backtest Lab: deployable Streamlit web app for US-listed USD securities."""
from datetime import date, timedelta
import re
from html import escape
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data import historical_data
from engine import backtest, common_date_timing
from search import find_tickers, CATALOG

st.set_page_config(page_title='Backtest Lab | 주식 백테스팅', page_icon='📈', layout='wide', initial_sidebar_state='expanded')
st.markdown("""<style>
.block-container {max-width:1400px;padding-top:1.3rem}
.kpi-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:16px 0}
.kpi-grid.three {grid-template-columns:repeat(3,minmax(0,1fr))}
.kpi {background:#172235;border:1px solid #334155;border-radius:14px;padding:16px 18px;min-width:0}
.kpi-label {color:#cbd5e1;font-size:.9rem;margin-bottom:12px}
.kpi-value {color:#f8fafc;font-size:clamp(1.05rem,2vw,1.75rem);font-weight:650;overflow-wrap:anywhere;line-height:1.3;font-variant-numeric:tabular-nums}
.kpi-value.positive {color:#70e3b0}.kpi-value.negative {color:#ff9f9f}
/* Metric cards must remain legible even when Streamlit's theme config is missing. */
[data-testid="stMetric"] {
  background-color:#172235 !important;
  border:1px solid #334155 !important;
  border-radius:14px !important;
  padding:16px 18px !important;
  min-height:108px;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"],
[data-testid="stMetric"] [data-testid="stMetricLabel"] * {
  color:#cbd5e1 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"],
[data-testid="stMetric"] [data-testid="stMetricValue"] * {
  color:#f8fafc !important;
  opacity:1 !important;
}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
  opacity:1 !important;
}
@media(max-width:700px) {
  .block-container {padding:1rem .7rem 2rem}
  .kpi-grid,.kpi-grid.three {grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .kpi {padding:12px}.kpi-value {font-size:clamp(.95rem,3.8vw,1.35rem)}
  [data-testid="stMetric"] {padding:12px !important;min-height:90px}
}
</style>""",unsafe_allow_html=True)

@st.cache_data(ttl=3600,show_spinner=False)
def search_cached(q): return find_tickers(q)

@st.cache_data(ttl=3600,show_spinner=False)
def prices_cached(tickers,end): return historical_data(list(tickers),date(1990,1,1),end)

def krw(n): return f'{n:,.0f}원'
def usd(n): return f'${n:,.2f}'

def kpi_grid(items,three=False):
    cards=[]
    for label,value,tone in items:
        tone = tone if tone in ('positive','negative') else ''
        cards.append(f'<div class="kpi"><div class="kpi-label">{escape(label)}</div><div class="kpi-value {tone}">{escape(str(value))}</div></div>')
    st.markdown(f'<div class="kpi-grid{" three" if three else ""}">{"".join(cards)}</div>',unsafe_allow_html=True)

def money_input(label,key,default):
    if key not in st.session_state: st.session_state[key]=f'{default:,}'
    s=st.text_input(label,key=key,help='숫자와 쉼표 입력 가능')
    if not re.fullmatch(r'\d[\d,]*',s.strip()):
        st.error(f'{label}: 숫자만 입력해 주세요.')
        return None
    return int(s.replace(',',''))

def set_equal():
    names=st.session_state.assets
    if not names:return
    base=round(100/len(names),2)
    for i,t in enumerate(names): st.session_state[f'w_{t}']=base if i<len(names)-1 else round(100-base*(len(names)-1),2)

def normalize():
    names=st.session_state.assets
    total=sum(st.session_state.get(f'w_{t}',0) for t in names)
    if total<=0:return
    sofar=0
    for i,t in enumerate(names):
        val=round(st.session_state[f'w_{t}']/total*100,2) if i<len(names)-1 else round(100-sofar,2)
        st.session_state[f'w_{t}']=val
        sofar+=val

def add_asset(t):
    if t not in st.session_state.assets and len(st.session_state.assets)<10:
        st.session_state.assets.append(t)
        st.session_state[f'w_{t}']=0.0
        st.session_state.pop('result',None)

def remove_asset(t):
    st.session_state.assets.remove(t)
    st.session_state.pop(f'w_{t}',None)
    st.session_state.pop('result',None)

if 'assets' not in st.session_state: st.session_state.assets=['VOO','QQQ','SCHD']
for t,w in [('VOO',40.),('QQQ',40.),('SCHD',20.)]:
    st.session_state.setdefault(f'w_{t}',w)

st.title('📈 Backtest Lab')
st.caption('실제 과거 데이터로 비교하는 미국 주식·ETF 투자 시뮬레이터 | PC·모바일 웹서비스')
st.warning('연구·교육용 도구입니다. 과거 수익률은 미래 성과를 보장하지 않습니다. 데이터 제공처의 정확성·가용성에 따라 결과가 달라질 수 있습니다.',icon='ℹ️')

with st.sidebar:
    st.header('① 종목 선택')
    q=st.text_input('티커 또는 종목명 검색',placeholder='VOO, Apple, NVIDIA...')
    if q:
        matches=search_cached(q)
        if matches:
            pick=st.selectbox('검색 결과',range(len(matches)),format_func=lambda i:f'{matches[i][0]} — {matches[i][1]}')
            if st.button('＋ 선택 종목 추가',use_container_width=True):
                add_asset(matches[pick][0]); st.rerun()
        else: st.info('검색 결과가 없습니다. 다른 이름 또는 티커로 검색하세요.')
    for t in st.session_state.assets.copy():
        a,b=st.columns([5,1]); a.write(f'**{t}** · {CATALOG.get(t,"선택한 종목")}')
        if b.button('✕',key=f'remove_{t}',help=f'{t} 삭제'):
            remove_asset(t);st.rerun()
    st.caption('미국 거래소에 상장된 USD 표시 주식·ETF 중심. 최대 10종목.')
    st.header('② 투자 비중')
    a,b=st.columns(2)
    a.button('균등 배분',on_click=set_equal,use_container_width=True,disabled=not st.session_state.assets)
    b.button('100% 정규화',on_click=normalize,use_container_width=True,disabled=not st.session_state.assets)
    weights={}
    for t in st.session_state.assets:
        st.session_state.setdefault(f'w_{t}',0.)
        weights[t]=st.number_input(f'{t} (%)',min_value=0.,max_value=100.,step=1.,key=f'w_{t}')
    total=sum(weights.values())
    if abs(total-100)<0.001:st.success(f'비중 합계 {total:.2f}%')
    else:st.error(f'비중 합계 {total:.2f}% — 100%로 조정해 주세요.')
    st.header('③ 투자 설정')
    currency=st.radio('투자금 입력 통화',['KRW (원)','USD ($)'],horizontal=True)
    in_krw=currency.startswith('KRW')
    initial=money_input('초기 투자금',f'initial_{currency}',10_000_000 if in_krw else 10_000)
    monthly=money_input('월 적립금',f'monthly_{currency}',500_000 if in_krw else 500)
    end=st.date_input('조회 종료일',date.today(),max_value=date.today())
    rebalance_label=st.selectbox('리밸런싱',['없음','매년','매월'])
    fee=st.number_input('거래 수수료 (편도, %)',min_value=0.,max_value=5.,value=0.05,step=0.05)
    spread=st.number_input('환전 비용 (편도, %)',min_value=0.,max_value=5.,value=0.1 if in_krw else 0.,step=0.05,disabled=not in_krw)
    apply_tax=st.checkbox('최종 매도 시 세금 간이 추정',value=False)
    if apply_tax:
        tax_rate=st.number_input('차익 세율 (%)',min_value=0.,max_value=60.,value=22.)
        deduction=st.number_input('차익 기본공제 (원)',min_value=0,value=2_500_000,step=500_000)
    else:tax_rate=22.;deduction=2_500_000
    run=st.button('🚀 실제 데이터 조회 및 분석',type='primary',use_container_width=True)

if run:
    if not weights or abs(total-100)>0.001 or initial is None or monthly is None or initial+monthly<=0:
        st.error('종목, 비중 합계 100%, 투자금을 확인하세요.')
    else:
        try:
            with st.spinner('Yahoo Finance에서 종목별 실제 가격과 환율을 조회하는 중...'):
                usd_prices,fx=prices_cached(tuple(weights),end)
            st.session_state.result={'usd_prices':usd_prices,'fx':fx,'weights':{t:w/100 for t,w in weights.items()},
                'initial':initial,'monthly':monthly,'rebalance':{'없음':'none','매년':'yearly','매월':'monthly'}[rebalance_label],
                'fee':fee,'spread':spread,'currency':currency,'tax':apply_tax,'tax_rate':tax_rate,'deduction':deduction}
        except Exception as e:
            st.session_state.pop('result',None)
            st.error(f'실제 데이터 조회 실패: {e}. 임의의 가격으로 대체하지 않습니다.')

if 'result' not in st.session_state:
    st.subheader('시작하기')
    st.write('왼쪽에서 종목과 비중을 선택하고 **실제 데이터 조회 및 분석**을 누르세요. 조회한 실제 공통 기간 내에서 시작일을 자유롭게 선택할 수 있습니다.')
    st.info('기본 포트폴리오: VOO 40% · QQQ 40% · SCHD 20% / 초기 1,000만 원 / 월 50만 원')
    st.stop()

r=st.session_state.result
stocks,fx=r['usd_prices'],r['fx']
first,last=stocks.index[0].date(),stocks.index[-1].date()
st.success(f'실제 데이터 공통 구간: {first} ~ {last} · {len(stocks):,}거래일')
st.caption('설정 변경 후에는 왼쪽 분석 버튼을 다시 눌러야 결과에 반영됩니다. 아래 시작일 변경은 즉시 계산됩니다.')
start_default=max(first,last-timedelta(days=3652))
start=st.date_input('백테스트 시작일 (공통 데이터 내 자유 선택)',value=start_default,min_value=first,max_value=last,key='analysis_start')
sub=stocks.loc[stocks.index.date>=start]
fx_sub=fx.reindex(sub.index)
if len(sub)<2:st.error('분석 기간에 거래일이 2일 이상 필요합니다.');st.stop()

# USD mode models investments and returns in USD. KRW mode converts adjusted USD prices at each historical FX observation.
price_basis=sub.mul(fx_sub,axis=0) if r['currency'].startswith('KRW') else sub
cost_bps=r['fee']*100 + (r['spread']*100 if r['currency'].startswith('KRW') else 0)
try:
    daily,m=backtest(price_basis,r['weights'],r['initial'],r['monthly'],rebalance=r['rebalance'],fee_bps=cost_bps)
    timing=common_date_timing(price_basis,r['weights'],r['initial'])
except Exception as e:
    st.error(f'계산 실패: {e}');st.stop()
format_money=krw if r['currency'].startswith('KRW') else usd
kpi_grid([
    ('최종 평가액',format_money(m['final']),''),
    ('총 납입원금',format_money(m['principal']),''),
    ('총 손익',format_money(m['profit']),'positive' if m['profit']>=0 else 'negative'),
    ('원금 대비 수익률',f'{m["roi"]*100:+.2f}%','positive' if m['roi']>=0 else 'negative'),
])
kpi_grid([
    ('시간가중 CAGR',f'{m["twr_cagr"]*100:+.2f}%' if pd.notna(m['twr_cagr']) else 'N/A',''),
    ('최대 낙폭 MDD',f'{m["mdd"]*100:.2f}%',''),
    ('누적 거래비용 (근사)',format_money(m['fees']),''),
],three=True)

fig=go.Figure()
fig.add_trace(go.Scatter(x=daily.index,y=daily.value,name='포트폴리오 평가액',line=dict(color='#2563eb',width=2)))
fig.add_trace(go.Scatter(x=daily.index,y=daily.principal,name='누적 납입원금',line=dict(color='#64748b',dash='dash')))
fig.update_layout(title='자산 성장 추이',height=430,margin=dict(l=10,r=10,t=50,b=15),hovermode='x unified',legend=dict(orientation='h'))
st.plotly_chart(fig,use_container_width=True)

st.subheader('📊 종목별 차트')
st.caption('표시할 티커를 선택하세요. 종목마다 색상이 고정됩니다. 포트폴리오 평가액에는 종목별 보유 수량과 현금이 반영됩니다.')
tickers=list(r['weights'])
colors=['#60a5fa','#f59e0b','#34d399','#f472b6','#a78bfa','#22d3ee','#f87171','#a3e635','#fb923c','#c084fc']
color_map={t:colors[i%len(colors)] for i,t in enumerate(tickers)}
if 'chart_selected' not in st.session_state or st.session_state.get('chart_assets')!=tuple(tickers):
    st.session_state.chart_selected=tickers.copy()
    st.session_state.chart_assets=tuple(tickers)
selected=st.multiselect('차트에 표시할 티커',tickers,key='chart_selected',placeholder='종목을 선택하세요')
chart_mode=st.radio('종목별 표시 기준',['종목별 평가액','주가 수익률 비교 (시작=100)','실제 주가 (USD)'],horizontal=True)
if selected:
    detail=go.Figure()
    for t in selected:
        if chart_mode=='종목별 평가액':
            series=daily[f'asset_{t}']; label=f'{t} 보유 평가액'; unit='원' if r['currency'].startswith('KRW') else 'USD'
        elif chart_mode=='주가 수익률 비교 (시작=100)':
            series=sub[t]/float(sub[t].iloc[0])*100;label=t;unit='지수'
        else:
            series=sub[t];label=t;unit='USD'
        detail.add_trace(go.Scatter(x=series.index,y=series,name=label,mode='lines',line=dict(color=color_map[t],width=2),hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.2f} '+unit+'<extra>'+t+'</extra>'))
    detail.update_layout(height=440,margin=dict(l=10,r=10,t=20,b=20),hovermode='x unified',legend=dict(orientation='h',y=-.18),uirevision='ticker-chart')
    st.plotly_chart(detail,use_container_width=True)
    if chart_mode=='종목별 평가액':
        st.caption('종목별 평가액은 선택한 투자 통화 기준입니다. 초기 매수·월 적립·리밸런싱·거래비용을 반영한 보유 평가액이며, 미투자 현금은 제외됩니다.')
    elif chart_mode=='주가 수익률 비교 (시작=100)':
        st.caption('배당·분할 수정 USD 종가를 시작일 100으로 정규화한 비교입니다. 투자금·수수료·환율 변동은 포함하지 않습니다.')
    else:
        st.caption('Yahoo Finance에서 조회한 종목별 USD 수정종가입니다. 배당·분할 조정치이므로 당시 실제 체결가격과 다를 수 있습니다.')
else:
    st.info('표시할 종목을 하나 이상 선택하세요.')


left,right=st.columns(2)
with left:
    st.subheader('📅 매수 시점 비교')
    st.write(f'**최적 공통 매수일:** {timing["best_date"].date()} → {format_money(timing["best_value"])}')
    st.write(f'**최악 공통 매수일:** {timing["worst_date"].date()} → {format_money(timing["worst_value"])}')
    st.caption('최초 투자금만 일시 매수하는 사후 비교이며 월 적립금·거래비용·세금은 포함하지 않습니다.')
with right:
    st.subheader('💱 달러·원화 환산')
    last_fx=float(fx_sub.iloc[-1]);st.write(f'분석 종료일 기준 1 USD ≈ **{last_fx:,.2f} KRW**')
    if r['currency'].startswith('KRW'):
        st.write(f'최종 평가액 ≈ **{usd(m["final"]/last_fx)}**')
    else:
        st.write(f'최종 평가액 ≈ **{krw(m["final"]*last_fx)}**')
    st.caption('환율은 Yahoo Finance의 KRW=X 일별 관측값을 자동 사용합니다. 주식 거래일에 환율 관측이 없으면 가장 최근 과거 관측값을 적용합니다.')
    fx_date=st.select_slider('환산 기준일 (실제 조회된 거래일)',options=list(fx_sub.index.date),value=fx_sub.index[-1].date(),format_func=lambda d:d.strftime('%Y-%m-%d'))
    selected_fx=float(fx_sub.loc[pd.Timestamp(fx_date)])
    st.write(f'선택한 날짜의 1 USD = **{selected_fx:,.2f}원**')
    usd_to_convert=st.number_input('환산할 USD',min_value=0.,value=1000.,step=100.)
    st.write(f'**{usd(usd_to_convert)} = {krw(usd_to_convert*selected_fx)}**')

if r['tax']:
    # USD portfolio tax is converted at final FX only; not a legal filing computation.
    gross_profit_krw=m['profit'] if r['currency'].startswith('KRW') else m['profit']*float(fx_sub.iloc[-1])
    tax_krw=max(0,gross_profit_krw-r['deduction'])*r['tax_rate']/100
    tax_in_currency=tax_krw if r['currency'].startswith('KRW') else tax_krw/float(fx_sub.iloc[-1])
    kpi_grid([('최종 매도 시 세금 간이 추정 후 평가액',format_money(m['final']-tax_in_currency),'')],three=True)
    st.warning('세금은 전체 손익에서 공제액을 뺀 단순 가정입니다. 연도별 실현손익·손익통산·배당원천징수·과세 환율·국가별 세법을 반영하지 않습니다. 실제 신고·투자 판단에 사용하지 마세요.')

st.download_button('⬇️ 일별 백테스트 결과 CSV',daily.to_csv().encode('utf-8-sig'),file_name='backtest_lab_results.csv',mime='text/csv')
with st.expander('데이터·계산 방식 및 한계'):
    st.markdown('''- **출처:** Yahoo Finance (`yfinance`). 주식은 배당·분할 수정종가(`auto_adjust=True`), 환율은 `KRW=X` 일별 종가를 사용합니다. 수정종가는 배당 재투자에 대한 근사치입니다.
- **공통 기간:** 모든 선택 종목과 환율의 유효한 공통 거래일만 사용합니다. 환율은 과거 관측치만 전방 채움합니다.
- **매수:** 최초 거래일에 초기 투자금을 매수하고, 이후 각 달의 첫 공통 거래일에 월 적립금을 매수합니다. 소수점 주식 허용, 매수·매도 비용 근사.
- **통화:** KRW 분석은 일별 수정종가 × 당시 원/달러 환율, USD 분석은 USD 수정종가를 사용합니다. 환전 비용은 매매 비용에 단순 합산하므로 실제 환전 시점과 차이가 있습니다.
- **리밸런싱:** 월별·연별 첫 거래일에 전체 매도 후 재매수하는 근사 방식입니다.
- **수익률:** 원금 대비 수익률과 시간가중 CAGR은 서로 다릅니다. MDD는 현금 유입을 제거한 전략 지수를 사용합니다.
- **제약:** 미국 거래소 USD 자산 중심. 한국 주식, 전 세계 거래소, 거래세·배당원천징수의 정밀 계산, 벤치마크·복수 시나리오 동시 비교는 후속 개발 대상입니다.
- **운영:** Yahoo Finance 비공식 데이터 인터페이스는 변경·속도 제한·접속 실패가 발생할 수 있으며 상업적 사용에 대한 데이터 이용 권한 검토가 필요합니다.''')
