"""백테스트 계산: 신호 → 거래 목록 → 성적(R·승률) → 내 자금 기준 곡선·최대 낙폭.

거래 규칙
- 신호가 난 날(t) 다음 날(t+1) 시가에 매수
- 손절 = 매수가 − (신호일 ATR × 배수), 목표 = 매수가 + 손절폭 × 목표 R
- 손절·목표 판정은 2단계 차트 복기와 같은 규칙(replay/engine.simulate_trade)
- 최대 보유일이 지나면 그날 종가에 정리
- 한 종목은 한 번에 하나만 보유 (정리한 날 신호가 나면 다음 날 다시 매수 가능)
- 데이터 끝까지 결과가 나지 않은 마지막 거래는 '진행 중'이라 빼고 계산
- 거래 비용(왕복 %)은 수익률에서 빼고, R에도 반영
"""
import math

import pandas as pd

from replay.engine import simulate_trade


def run_symbol(df: pd.DataFrame, signal: pd.Series, stop_mult: float, target_r: float,
               max_hold: int, cost_pct: float, start_idx: int = 0) -> list[dict]:
    """한 종목 백테스트. 거래 목록을 돌려준다."""
    trades = []
    opens, atrs = df["Open"].to_numpy(), df["atr"].to_numpy()
    sig = signal.to_numpy()
    n = len(df)
    t = max(start_idx, 0)
    while t < n - 1:
        if not sig[t] or math.isnan(atrs[t]):
            t += 1
            continue
        e = t + 1                              # 매수일
        entry = float(opens[e])
        risk = float(atrs[t]) * stop_mult      # 손절폭(가격)
        if risk <= 0 or risk >= entry:
            t += 1
            continue
        stop, target = entry - risk, entry + risk * target_r
        future = df.iloc[e: e + max_hold]
        res = simulate_trade(future, entry, stop, target)
        if res["reason"] == "time" and len(future) < max_hold:
            break                              # 데이터 끝: 아직 진행 중인 거래는 제외
        exit_idx = e + res["exit_pos"]
        cost = entry * cost_pct / 100
        trades.append({
            "signal_date": df.index[t],
            "entry_date": df.index[e],
            "exit_date": df.index[exit_idx],
            "entry": entry,
            "exit": res["exit_price"],
            "stop": stop,
            "target": target,
            "reason": res["reason"],
            "bars_held": res["bars_held"],
            "stop_pct": risk / entry * 100,                       # 손절폭(%)
            "ret_pct": res["ret_pct"] - cost_pct,                 # 비용 뺀 수익률(%)
            "r": (res["exit_price"] - entry - cost) / risk,       # 비용 뺀 R
        })
        t = exit_idx                           # 정리한 날 종가에 다시 신호를 볼 수 있음
    return trades


def summarize(trades: list[dict]) -> dict:
    """거래 목록 → 성적 요약."""
    rs = [t["r"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    loss_sum = -sum(losses)
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    return {
        "count": len(rs),
        "wins": len(wins),
        "win_rate": len(wins) / len(rs) * 100 if rs else 0.0,
        "avg_r": sum(rs) / len(rs) if rs else 0.0,
        "total_r": sum(rs),
        # 이익 합 ÷ 손실 합. 1보다 크면 번 돈이 잃은 돈보다 많음. 손실이 없으면 무한대
        "profit_factor": (sum(wins) / loss_sum) if loss_sum > 0 else (math.inf if wins else 0.0),
        "avg_hold": sum(t["bars_held"] for t in trades) / len(trades) if trades else 0.0,
        "reasons": reasons,
    }


def breakeven_win_rate(target_r: float) -> float:
    """목표 R 거래만 한다고 할 때, 본전이 되는 승률(%) = 1 ÷ (1 + 목표 R). (비용·기간 만료 제외한 대략값)"""
    return 100 / (1 + target_r)


def position_fraction(stop_pct: float, risk_pct: float, max_weight_pct: float) -> float:
    """총자금 중 이 거래에 넣는 비율(0~1).

    1회 최대 손실 규칙: 손절폭이 stop_pct%일 때 손실을 risk_pct%로 맞추려면 risk_pct ÷ stop_pct 만큼 산다.
    단, 종목당 최대 비중(max_weight_pct%)을 넘지 않는다.
    """
    if stop_pct <= 0:
        return 0.0
    return min(risk_pct / stop_pct, max_weight_pct / 100)


def equity_curve(trades: list[dict], capital: float, risk_pct: float, max_weight_pct: float) -> pd.DataFrame:
    """내 자금 기준 곡선. 거래를 정리한 날짜 순서로 손익을 더한다(복리).

    단순화: 1주 단위가 아니라 금액 비율로 계산하고, 여러 종목을 동시에 들고 있을 때의 자금 부족은 따지지 않는다.
    """
    rows = [{"date": None, "equity": capital, "pnl": 0.0}]
    eq = capital
    for t in sorted(trades, key=lambda x: x["exit_date"]):
        frac = position_fraction(t["stop_pct"], risk_pct, max_weight_pct)
        pnl = eq * frac * t["ret_pct"] / 100
        eq += pnl
        rows.append({"date": t["exit_date"], "equity": eq, "pnl": pnl})
    return pd.DataFrame(rows)


def max_drawdown_pct(equity: pd.Series) -> float:
    """최대 낙폭(%): 자금이 최고점에서 가장 많이 줄어든 비율. 예: 100 → 80이면 −20."""
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    return float(((equity / peak) - 1).min() * 100)
