"""🧪 전략 탭 화면: 매수 규칙을 정해 과거 데이터로 성적을 확인한다 (백테스트)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from backtest import engine as bt
from backtest.strategies import STRATEGIES, signals
from data.cached import fmt_price, load_prices, stock_name
from data.prices import detect_market, normalize_symbol
from replay.engine import REASON_TEXT

SCOPES = {"one": "한 종목", "pool": "대표 종목 전체"}
MARKET_CHOICES = {"US": "미국", "KR": "한국", "ALL": "둘 다"}
LEVEL_EMOJI = {"good": "🟢", "ok": "🟡", "bad": "🔴"}


def _pool(market_choice: str) -> list[tuple[str, str]]:
    out = []
    if market_choice in ("US", "ALL"):
        out += [(s, "US") for s in config.REPLAY_POOL_US]
    if market_choice in ("KR", "ALL"):
        out += [(s, "KR") for s in config.REPLAY_POOL_KR]
    return out


@st.cache_data(ttl=config.REPLAY_CACHE_HOURS * 3600, show_spinner="백테스트 계산 중…")
def run_backtest(symbols: tuple, strategy: str, params: tuple, stop_mult: float, target_r: float,
                 max_hold: int, years: int, use_cost: bool):
    """여러 종목 백테스트. (거래 목록, 오류 목록, 종목별 그냥 보유 수익률) — 같은 조건이면 캐시를 쓴다."""
    cutoff = pd.Timestamp(datetime.now(ZoneInfo(config.TIMEZONE)).date() - timedelta(days=365 * years))
    trades, errors, hold = [], [], {}
    for symbol, market in symbols:
        df, err = load_prices(symbol, market)
        if err:
            errors.append(err)
            continue
        start_idx = int(df.index.searchsorted(cutoff))
        if start_idx >= len(df) - 1:
            errors.append(f"{symbol}: 테스트 기간에 데이터가 없습니다.")
            continue
        sig = signals(df, strategy, dict(params))
        cost = config.BT_COST_PCT[market] if use_cost else 0.0
        for t in bt.run_symbol(df, sig, stop_mult, target_r, max_hold, cost, start_idx):
            trades.append({**t, "symbol": symbol, "market": market})
        hold[symbol] = (df["Close"].iloc[-1] / df["Close"].iloc[start_idx] - 1) * 100
    return trades, errors, hold


def _avg_r_level(avg_r: float) -> str:
    if avg_r >= config.BT_GOOD_AVG_R:
        return "good"
    return "ok" if avg_r > 0 else "bad"


def render():
    ss = st.session_state
    st.caption("매수 규칙을 정해 과거에 똑같이 거래했다면 어땠을지 계산합니다. 과거 결과가 미래를 보장하지 않습니다.")

    # ── 설정 ─────────────────────────────────────────
    scope = st.radio("범위", list(SCOPES), format_func=SCOPES.get, horizontal=True, key="bt_scope")
    if scope == "one":
        typed = st.text_input("종목 코드 (미국: AAPL / 한국: 005930)", value="AAPL", key="bt_symbol")
        symbol = normalize_symbol(typed)
        symbols = ((symbol, detect_market(symbol)),) if symbol else ()
    else:
        market_choice = st.radio("시장", list(MARKET_CHOICES), format_func=MARKET_CHOICES.get,
                                 horizontal=True, key="bt_market")
        symbols = tuple(_pool(market_choice))
        st.caption(f"{len(symbols)}종목에 같은 규칙을 적용합니다. 처음에는 시세를 불러오느라 시간이 걸립니다.")

    key = st.selectbox("전략", list(STRATEGIES), format_func=lambda k: STRATEGIES[k]["name"], key="bt_strategy")
    st.caption(f"매수 규칙: {STRATEGIES[key]['desc']}")

    with st.expander("숫자 조절"):
        params = {}
        for name, (label, default, lo, hi, step) in STRATEGIES[key]["params"].items():
            params[name] = st.slider(label, lo, hi, default, step, key=f"bt_{key}_{name}")
        st.markdown("**매도 규칙 (공통)**")
        stop_mult = st.slider("손절 = 매수가 − ATR × ", *config.BT_STOP_MULT_RANGE[:2], config.BT_STOP_ATR_MULT,
                              config.BT_STOP_MULT_RANGE[2], key="bt_stop")
        target_r = st.slider("목표 = 손절폭 × (목표 R)", *config.BT_TARGET_R_RANGE[:2], config.BT_TARGET_R,
                             config.BT_TARGET_R_RANGE[2], key="bt_target")
        lo, hi = config.BT_MAX_HOLD_RANGE
        max_hold = st.slider("최대 보유 거래일", lo, hi, config.BT_MAX_HOLD_DAYS, 1, key="bt_hold")
    years = st.select_slider("테스트 기간(년)", options=config.BT_YEARS_OPTIONS, value=config.BT_DEFAULT_YEARS,
                             key="bt_years")
    use_cost = st.checkbox(
        f"거래 비용 빼기 (왕복 한국 {config.BT_COST_PCT['KR']:.2f}% · 미국 {config.BT_COST_PCT['US']:.2f}%)",
        value=True, key="bt_cost")

    if key == "pullback" and params["rsi_low"] >= params["rsi_high"]:
        st.warning("RSI 하단이 상단보다 작아야 합니다.")
        return
    if st.button("백테스트 실행", type="primary", width="stretch", disabled=not symbols):
        ss.bt_run = (symbols, key, tuple(sorted(params.items())), stop_mult, target_r, max_hold, years, use_cost)

    if not ss.get("bt_run"):
        return
    run = ss.bt_run
    trades, errors, hold = run_backtest(*run)
    _render_result(run, trades, errors, hold)


def _render_result(run, trades, errors, hold):
    symbols, key, params, stop_mult, target_r, max_hold, years, use_cost = run
    st.markdown("---")
    who = stock_name(*symbols[0]) if len(symbols) == 1 else f"대표 종목 {len(symbols)}개"
    st.markdown(f"### {STRATEGIES[key]['name']} · {who} · 최근 {years}년")
    st.caption(f"손절 ATR×{stop_mult:g} · 목표 {target_r:g}R · 최대 {max_hold}일 보유 · "
               f"비용 {'뺌' if use_cost else '안 뺌'}")
    for e in errors:
        st.warning(e)
    if not trades:
        st.info("이 조건으로는 거래가 한 번도 없었습니다. 숫자를 바꿔 보세요.")
        return

    s = bt.summarize(trades)
    if s["count"] < config.BT_MIN_TRADES:
        st.warning(f"거래가 {s['count']}번뿐이라 결과가 우연일 수 있습니다. ({config.BT_MIN_TRADES}번 이상 권장 — "
                   "기간을 늘리거나 '대표 종목 전체'로 확인해 보세요)")

    # 핵심 성적 + 왜 그 색인지 한 줄 설명
    be = bt.breakeven_win_rate(target_r)
    level = _avg_r_level(s["avg_r"])
    c1, c2 = st.columns(2)
    c1.metric("거래 수", f"{s['count']}번", help=f"평균 {s['avg_hold']:.1f}일 보유")
    c2.metric("승률", f"{s['win_rate']:.0f}%", help=f"이익으로 끝난 거래 {s['wins']} / {s['count']}")
    c3, c4 = st.columns(2)
    c3.metric("평균 R", f"{s['avg_r']:+.2f}R", help=f"합계 {s['total_r']:+.1f}R")
    pf = "∞" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"
    c4.metric("이익 ÷ 손실", pf, help="이익으로 끝난 거래의 R 합 ÷ 손실 거래의 R 합. 1보다 크면 번 것이 더 많음")
    st.caption(f"{LEVEL_EMOJI[level]} 평균 {s['avg_r']:+.2f}R → "
               + ("길게 보면 이익인 규칙" if level == "good" else
                  "이익이지만 작음 (비용·우연에 흔들릴 수 있음)" if level == "ok" else "길게 보면 손해인 규칙")
               + f" · 기준: {config.BT_GOOD_AVG_R:g}R 이상 🟢, 0 초과 🟡, 0 이하 🔴")
    st.caption(f"승률 {s['win_rate']:.0f}% vs 목표 {target_r:g}R일 때 본전 승률 약 {be:.0f}% → "
               + ("본전 승률보다 높음" if s["win_rate"] > be else "본전 승률보다 낮음")
               + " (기간 만료로 정리된 거래가 있어 대략적인 비교)")
    reasons = " · ".join(f"{REASON_TEXT[r]} {n}번" for r, n in sorted(s["reasons"].items(), key=lambda x: -x[1]))
    st.caption(f"정리 이유: {reasons}")

    # 내 자금 기준
    curve = bt.equity_curve(trades, config.BT_CAPITAL, config.BT_RISK_PCT, config.BT_MAX_WEIGHT_PCT)
    final = curve["equity"].iloc[-1]
    mdd = bt.max_drawdown_pct(curve["equity"])
    st.markdown("**내 자금 기준**")
    m1, m2 = st.columns(2)
    m1.metric("최종 자금", f"{final:,.0f}원", f"{(final / config.BT_CAPITAL - 1) * 100:+.1f}%")
    m2.metric("최대 낙폭", f"{mdd:.1f}%", help="자금이 최고점에서 가장 많이 줄었던 비율")
    st.caption(f"총 {config.BT_CAPITAL:,.0f}원, 1회 최대 손실 {config.BT_RISK_PCT:g}%, 종목당 최대 "
               f"{config.BT_MAX_WEIGHT_PCT:g}% 규칙으로 거래했다면. (1주 단위·동시 보유 자금 한도는 단순화)")
    if len(symbols) == 1 and symbols[0][0] in hold:
        st.caption(f"같은 기간 그냥 계속 보유했다면: {hold[symbols[0][0]]:+.1f}% (전액 투자 기준이라 직접 비교는 참고만)")
    fig = go.Figure(go.Scatter(x=list(range(len(curve))), y=curve["equity"], mode="lines",
                               line=dict(color=config.COLOR_EQUITY, width=2), name="자금"))
    fig.add_hline(y=config.BT_CAPITAL, line=dict(color=config.COLOR_GUIDE, dash="dot"))
    tick_idx = list(range(1, len(curve), max(1, len(curve) // 4)))
    fig.update_layout(template=config.CHART_TEMPLATE, height=config.BT_EQUITY_CHART_HEIGHT, margin=dict(l=5, r=5, t=10, b=10),
                      dragmode=False, showlegend=False, yaxis=dict(tickformat=",.0f"),
                      xaxis=dict(tickvals=tick_idx, ticktext=[f"{curve['date'].iloc[i]:%y.%m}" for i in tick_idx]))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("가로축: 거래를 정리한 순서 (날짜는 대략 위치)")

    # 한 종목: 가격 위에 매매 위치 / 여러 종목: 종목별 성적
    if len(symbols) == 1:
        _price_chart(symbols[0], trades, years)
    else:
        rows = []
        for sym, market in symbols:
            ts = [t for t in trades if t["symbol"] == sym]
            if not ts:
                continue
            ss_ = bt.summarize(ts)
            rows.append({"종목": stock_name(sym, market), "거래": ss_["count"], "승률": f"{ss_['win_rate']:.0f}%",
                         "평균 R": round(ss_["avg_r"], 2), "보유 수익률": f"{hold.get(sym, 0):+.0f}%"})
        st.markdown("**종목별 성적** (평균 R 높은 순)")
        st.dataframe(pd.DataFrame(rows).sort_values("평균 R", ascending=False), hide_index=True, width="stretch")

    # 거래 목록
    with st.expander(f"최근 거래 {min(len(trades), config.BT_TRADES_SHOWN)}개"):
        recent = sorted(trades, key=lambda t: t["entry_date"], reverse=True)[: config.BT_TRADES_SHOWN]
        st.dataframe(pd.DataFrame([{
            "매수일": f"{t['entry_date']:%Y.%m.%d}", "종목": t["symbol"],
            "매수가": fmt_price(t["market"], t["entry"]), "매도가": fmt_price(t["market"], t["exit"]),
            "이유": REASON_TEXT[t["reason"]], "보유일": t["bars_held"], "R": round(t["r"], 2),
            "수익률": f"{t['ret_pct']:+.1f}%"} for t in recent]), hide_index=True, width="stretch")
    st.caption("⚠️ 숫자를 여러 번 바꿔 가장 좋은 결과를 고르면, 과거에만 잘 맞는 규칙(과최적화)이 되기 쉽습니다.")


def _price_chart(sym_market, trades, years):
    """한 종목 가격(종가 선) 위에 매수·매도 위치 표시."""
    symbol, market = sym_market
    df, _ = load_prices(symbol, market)
    cutoff = pd.Timestamp(datetime.now(ZoneInfo(config.TIMEZONE)).date() - timedelta(days=365 * years))
    view = df[df.index >= cutoff]
    colors = config.CANDLE_COLORS[market]
    fig = go.Figure(go.Scatter(x=view.index, y=view["Close"], mode="lines", name="종가",
                               line=dict(color=config.COLOR_REVEAL, width=1)))
    fig.add_trace(go.Scatter(x=[t["entry_date"] for t in trades], y=[t["entry"] for t in trades], mode="markers",
                             name="매수", marker=dict(symbol="triangle-up", size=8, color=config.COLOR_ENTRY)))
    fig.add_trace(go.Scatter(x=[t["exit_date"] for t in trades], y=[t["exit"] for t in trades], mode="markers",
                             name="매도", marker=dict(symbol="x", size=7,
                                                      color=[colors["up"] if t["r"] > 0 else colors["down"]
                                                             for t in trades])))
    fig.update_layout(template=config.CHART_TEMPLATE, height=config.BT_PRICE_CHART_HEIGHT, margin=dict(l=5, r=5, t=10, b=10),
                      dragmode=False, legend=dict(orientation="h", y=1.02, x=0))
    st.markdown("**매매 위치**")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("▲ 매수, ✕ 매도 (이익이면 양봉 색, 손실이면 음봉 색)")
