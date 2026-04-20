import numpy as np

def compute_metrics(df):
    if df is None or len(df) == 0:
        return {}

    results = df['result'].dropna().values
    pnl = df['pnl'].dropna().values

    win_rate = (results > 0).mean() if len(results) else 0
    avg = pnl.mean() if len(pnl) else 0
    std = pnl.std() if len(pnl) else 1e-9
    sharpe = (avg / std) * (len(pnl) ** 0.5) if len(pnl) else 0

    # equity curve + max DD
    eq = np.cumsum(pnl) if len(pnl) else np.array([0])
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    max_dd = dd.min() if len(dd) else 0

    profit_factor = (pnl[pnl>0].sum() / abs(pnl[pnl<0].sum())) if (pnl[pnl<0].sum()!=0) else 0

    return {
        "trades": int(len(pnl)),
        "win_rate": float(win_rate),
        "avg_pnl": float(avg),
        "sharpe": float(sharpe),
        "max_dd": float(max_dd),
        "profit_factor": float(profit_factor)
    }
