"""Ticker/name search with a deterministic fallback for commonly used US assets."""
import re
import yfinance as yf

CATALOG = {
 'VOO':'Vanguard S&P 500 ETF','QQQ':'Invesco Nasdaq 100 ETF','SCHD':'Schwab US Dividend Equity ETF',
 'SPY':'SPDR S&P 500 ETF','IVV':'iShares Core S&P 500 ETF','VTI':'Vanguard Total Stock Market ETF',
 'QLD':'ProShares Ultra QQQ','TQQQ':'ProShares UltraPro QQQ','AAPL':'Apple',
 'MSFT':'Microsoft','NVDA':'NVIDIA','GOOGL':'Alphabet','AMZN':'Amazon',
 'TSLA':'Tesla','BRK-B':'Berkshire Hathaway Class B','JEPI':'JPMorgan Equity Premium Income ETF',
 'JEPQ':'JPMorgan Nasdaq Equity Premium Income ETF','VT':'Vanguard Total World Stock ETF',
 'VXUS':'Vanguard Total International Stock ETF','TLT':'iShares 20+ Year Treasury Bond ETF',
 'SOXX':'iShares Semiconductor ETF','IWM':'iShares Russell 2000 ETF',
}

def find_tickers(query):
    query = query.strip()
    if not query:
        return []
    found = {t:n for t,n in CATALOG.items() if query.casefold() in (t+' '+n).casefold()}
    try:
        for item in yf.Search(query, max_results=15).quotes:
            t = str(item.get('symbol','')).upper()
            exchange = str(item.get('exchange','')).upper()
            if (re.fullmatch(r'[A-Z0-9.-]{1,12}', t) and item.get('quoteType') in ('ETF','EQUITY')
                    and exchange not in ('KSC','KOE','NMS?') and not t.endswith(('.KS','.KQ'))):
                found.setdefault(t, item.get('shortname') or item.get('longname') or t)
    except Exception:
        pass  # Catalog still works during search API outages.
    return list(found.items())[:20]
