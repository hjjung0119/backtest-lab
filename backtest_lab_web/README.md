# Backtest Lab — 배포 가능한 웹서비스

종목 검색, 실제 Yahoo Finance 과거 수정주가, 원/달러 환율, 포트폴리오 거치식/적립식 백테스트를 제공하는 Streamlit 웹앱입니다.

## 가장 쉬운 배포 (최초 1회)

1. GitHub에서 새 저장소(예: `backtest-lab`)를 만듭니다.
2. 이 폴더의 **내용물**(`app.py`, `engine.py`, `data.py`, `search.py`, `requirements.txt`, `.streamlit/config.toml`)을 저장소 최상위에 업로드합니다. `.streamlit` 폴더도 포함합니다.
3. https://share.streamlit.io 에 GitHub로 로그인하고 **Create app**에서 해당 저장소를 선택합니다.
4. Branch는 `main`, Main file path는 `app.py`로 지정한 뒤 Deploy합니다.
5. 발급된 `https://...streamlit.app` 주소를 PC와 아이폰 Safari에서 사용합니다. 이후 GitHub `main`에 코드를 반영하면 앱이 다시 배포됩니다.

**중요:** 배포 계정 로그인과 저장소 권한 승인은 소유자가 직접 해야 합니다. ZIP 파일은 개발 프로젝트를 전달하기 위한 것이며, 배포 후 최종 사용자는 ZIP/Python 설치가 필요 없습니다.

## 개발자 로컬 실행 (선택 사항)

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 자동 테스트

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

## 데이터 및 한계

- 미국 상장 USD 표시 종목 중심. `yfinance` 검색 및 가격은 비공식 Yahoo Finance 연동이므로 일시적으로 실패할 수 있습니다.
- 가격은 배당/분할 수정종가를 사용하며 실제 현금배당 및 배당원천징수의 정밀 계산은 지원하지 않습니다.
- 환율은 Yahoo Finance `KRW=X` 종가. 과거 데이터가 없는 날짜에 미래 환율을 역으로 채우지 않습니다.
- 수수료 및 환전비용은 매매 금액에 단순 합산한 근사치이며, 매도세는 최종 평가차익 기준의 단순 추정입니다.
- 실제 투자 권유, 세무신고 도구가 아닙니다. 상업 공개 전 데이터 제공업체의 이용약관과 라이선스를 확인하세요.

## 기능 상태

- 구현: 검색·종목 선택, 비중 균등/정규화, 공통 가격 기간, KRW/USD, 거치식·적립식, 월/년 리밸런싱, 수수료 근사, 간이 매도세, 성장 차트, CAGR/MDD, 매수 시점 비교, CSV 내보내기.
- 후속: 국내/세계 주식, 정밀 배당세·양도세, 복수 시나리오 동시 비교, 벤치마크, 사용자별 저장, 데이터 라이선스 검토.
