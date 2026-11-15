import unittest
import sys
import types
# Data alignment tests mock the network client; live Yahoo calls require deployed dependencies.
try:
    import yfinance
except ImportError:
    sys.modules["yfinance"] = types.ModuleType("yfinance")
import numpy as np
import pandas as pd
from engine import backtest, common_date_timing
from data import historical_data
from unittest.mock import patch

class TestBacktest(unittest.TestCase):
    def setUp(self):
        self.idx=pd.to_datetime(['2024-01-02','2024-01-03','2024-02-01','2024-02-02'])
        self.p=pd.DataFrame({'AAA':[100.,110.,120.,120.],'BBB':[100.,100.,100.,100.]},index=self.idx)
    def test_initial_and_monthly(self):
        df,m=backtest(self.p,{'AAA':1.,'BBB':0.},1000,100)
        self.assertEqual(m['principal'],1100)
        self.assertAlmostEqual(m['final'],1300)
        self.assertEqual(list(df.contribution),[1000,0,100,0])
    def test_zero_fees_flat(self):
        p=pd.DataFrame({'AAA':[100]*4},index=self.idx)
        _,m=backtest(p,{'AAA':1.},1000,100)
        self.assertAlmostEqual(m['final'],1100)
        self.assertAlmostEqual(m['mdd'],0)
    def test_fee_reduces_value(self):
        _,free=backtest(self.p,{'AAA':1.,'BBB':0.},1000,100)
        _,charged=backtest(self.p,{'AAA':1.,'BBB':0.},1000,100,fee_bps=100)
        self.assertLess(charged['final'],free['final'])
        self.assertGreater(charged['fees'],0)
    def test_invalid_weights(self):
        with self.assertRaises(ValueError):backtest(self.p,{'AAA':0.4,'BBB':0.4},1000,0)
    def test_common_timing(self):
        t=common_date_timing(self.p,{'AAA':1.,'BBB':0.},1000)
        self.assertEqual(t['best_date'],self.idx[0])
        self.assertEqual(t['worst_date'],self.idx[2])
    @patch('data.close_series')
    def test_fx_alignment_never_uses_future(self,mock):
        def fake(t,s,e):
            if t=='KRW=X':return pd.Series([1300.,1400.],index=pd.to_datetime(['2024-01-03','2024-02-01']),name=t)
            return self.p[t]
        mock.side_effect=fake
        stocks,fx=historical_data(['AAA','BBB'],self.idx[0].date(),self.idx[-1].date())
        self.assertEqual(stocks.index[0],self.idx[1])
        self.assertEqual(fx.iloc[0],1300)
        self.assertEqual(fx.iloc[-1],1400)

if __name__=='__main__':unittest.main()
