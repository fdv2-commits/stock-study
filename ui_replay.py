"""🕯️ 복기 탭 화면: 과거 차트를 보고 판단을 연습한다.

- 한 번 판단형: 앞부분 차트만 보고 매수(손절·목표 설정) 또는 관망 → 이후 봉 공개, 손익(R) 채점
- 한 봉씩 넘기기형: 하루씩 넘기며 원할 때 종가에 사고팔기 → 끝나면 그냥 보유했을 때와 비교
종목 이름과 날짜는 끝날 때까지 가린다.
"""
import random

import streamlit as st

import config
from data.prices import PriceError, detect_market, fetch_daily, normalize_symbol
from indicators.core import add_indicators
from quiz import progress as prog
from replay import engine
from replay.chart import INDICATORS, build_chart

MODES = {"one": "한 번 판단", "step": "한 봉씩 넘기기"}
MARKET_CHOICES = {"US": "미국", "KR": "한국", "ALL": "둘 다"}


@st.cache_data(ttl=config.REPLAY_CACHE_HOURS * 3600, show_spinner="시세를 불러오는 중…")
def load_prices(symbol: str, market: str):
    """일봉 + 지표. (데이터, 오류 메시지) — 실패해도 앱이 멈추지 않게 오류는 글자로 돌려준다."""
    try:
        return add_indicators(fetch_daily(symbol, market)), None
    except PriceError as e:
        return None, str(e)


def fmt_price(market: str, value: float) -> str:
    """가격 표시: 한국은 원(정수), 미국은 달러(소수 둘째 자리)."""
    return f"{value:,.0f}원" if market == "KR" else f"${value:,.2f}"


def stock_name(symbol: str, market: str) -> str:
    pool = config.REPLAY_POOL_KR if market == "KR" else config.REPLAY_POOL_US
    return f"{pool[symbol]} ({symbol})" if symbol in pool else symbol


def _period_text(df, start: int, end: int) -> str:
    return f"{df.index[start]:%Y.%m.%d} ~ {df.index[end]:%Y.%m.%d}"


def render(progress: dict, save, sync):
    """복기 탭 전체를 그린다. save·sync는 학습 기록 저장 함수(app.py에서 받음)."""
    ss = st.session_state

    # ── 새 판 시작 ───────────────────────────────────
    def new_game(mode: str, market_choice: str, pick: str, typed: str):
        rng = random.Random()
        if pick == "random":
            market = rng.choice(list(config.MARKETS)) if market_choice == "ALL" else market_choice
            pool = config.REPLAY_POOL_KR if market == "KR" else config.REPLAY_POOL_US
            symbol = rng.choice(list(pool))
        else:
            symbol = normalize_symbol(typed)
            if not symbol:
                ss.rp_notice = "종목 코드를 입력해 주세요. (미국: AAPL, 한국: 005930)"
                return
            market = detect_market(symbol)
        df, err = load_prices(symbol, market)
        if err:
            ss.rp_notice = err
            return
        after = config.REPLAY_FUTURE_BARS if mode == "one" else config.REPLAY_STEP_BARS
        try:
            d = engine.pick_decision_index(len(df), rng, config.REPLAY_HISTORY_BARS, after)
        except ValueError as e:
            ss.rp_notice = f"{symbol}: {e}"
            return
        ss.rp_notice = None
        ss.rp = {"mode": mode, "symbol": symbol, "market": market, "d": d, "cur": d,
                 "done": False, "position": None, "trades": [], "result": None}
        # 손절·목표 입력칸의 처음 값 = 추천값
        stop, target = engine.suggest_plan(float(df["Close"].iloc[d]), float(df["atr"].iloc[d]))
        digits = 0 if market == "KR" else 2
        ss.rp_stop, ss.rp_target = round(stop, digits), round(target, digits)

    def quit_game():
        ss.rp = None

    rp = ss.get("rp")

    # ── 설정 화면 (진행 중인 판이 없을 때) ─────────────
    if not rp:
        mode = st.radio("연습 방식", list(MODES), format_func=MODES.get, horizontal=True, key="rp_mode")
        pick = st.radio("종목", ["random", "typed"], horizontal=True, key="rp_pick",
                        format_func=lambda p: "대표 종목 무작위" if p == "random" else "직접 입력")
        market_choice, typed = config.DEFAULT_MARKET, ""
        if pick == "random":
            market_choice = st.radio("시장", list(MARKET_CHOICES), format_func=MARKET_CHOICES.get,
                                     horizontal=True, key="rp_market")
        else:
            typed = st.text_input("종목 코드 (미국: AAPL / 한국: 005930)", key="rp_symbol")
        st.multiselect("차트에 보여줄 지표", list(INDICATORS), default=list(INDICATORS),
                       format_func=INDICATORS.get, key="rp_show")
        st.button("차트 시작", type="primary", width="stretch", on_click=new_game,
                  args=(mode, market_choice, pick, typed))
        if ss.get("rp_notice"):
            st.warning(ss.rp_notice)
        if mode == "one":
            st.caption(f"최근 {config.REPLAY_HISTORY_BARS}봉을 보고 매수·관망을 정하면, 이후 "
                       f"{config.REPLAY_FUTURE_BARS}봉을 공개해 손절·목표 중 무엇이 먼저 왔는지 채점합니다.")
        else:
            st.caption(f"하루씩 넘기며 원할 때 종가에 사고팝니다. {config.REPLAY_STEP_BARS}봉이 지나면 끝나고, "
                       "그냥 계속 보유했을 때와 비교합니다.")
        st.caption("종목 이름과 날짜는 끝날 때까지 가립니다.")
        return

    df, err = load_prices(rp["symbol"], rp["market"])
    if err:
        st.error(err)
        st.button("처음으로", on_click=quit_game)
        return
    market, d = rp["market"], rp["d"]
    show = set(ss.get("rp_show", list(INDICATORS)))
    fmt = lambda v: fmt_price(market, v)   # noqa: E731 (짧은 도우미)
    start = d - config.REPLAY_HISTORY_BARS + 1        # 화면에 보이는 첫 봉 위치

    if rp["mode"] == "one":
        _render_one(df, rp, start, show, fmt, progress, save, sync)
    else:
        _render_step(df, rp, start, show, fmt, progress, save, sync)

    if ss.get("rp_notice"):
        st.warning(ss.rp_notice)
    st.button("다른 차트로" if rp["done"] else "그만두기", width="stretch", on_click=quit_game, key="rp_quit")


# ── 한 번 판단형 ───────────────────────────────────────
def _render_one(df, rp, start, show, fmt, progress, save, sync):
    ss = st.session_state
    d, market = rp["d"], rp["market"]
    entry = float(df["Close"].iloc[d])

    def decide(decision: str):
        future = df.iloc[d + 1: d + 1 + config.REPLAY_FUTURE_BARS]
        stop, target = float(ss.rp_stop), float(ss.rp_target)
        if decision == "buy":
            problem = engine.validate_plan(entry, stop, target)
            if problem:
                ss.rp_notice = problem
                return
        else:   # 관망: 추천 계획대로 샀다면 어땠을지 계산
            stop, target = engine.suggest_plan(entry, float(df["atr"].iloc[d]))
        res = engine.simulate_trade(future, entry, stop, target)
        ss.rp_notice = None
        rp.update(done=True, result={"decision": decision, "stop": stop, "target": target, **res})
        item = {"mode": "one", "symbol": rp["symbol"], "name": stock_name(rp["symbol"], market),
                "period": _period_text(df, start, d + config.REPLAY_FUTURE_BARS), "decision": decision,
                "reason": res["reason"]}
        if decision == "buy":
            item.update(r=round(res["r"], 2), ret_pct=round(res["ret_pct"], 2))
        else:
            item.update(would_r=round(res["r"], 2))
        prog.record_replay(progress, item)
        save()
        sync(f"차트 복기 {stock_name(rp['symbol'], market)}")

    if not rp["done"]:
        view = df.iloc[start: d + 1]
        st.caption(f"마지막 봉 종가 {fmt(entry)} · 이 가격에 산다고 가정")
        st.plotly_chart(build_chart(view, market, show, hide_dates=True), width="stretch",
                        config={"displayModeBar": False})
        with st.expander("지표 읽기 도움말 (마지막 봉 기준)"):
            for line in engine.indicator_notes(df.iloc[d]):
                st.write(f"- {line}")
        st.markdown("**매수한다면 손절가·목표가**")
        step = 1.0 if market == "KR" else 0.01
        num_fmt = "%.0f" if market == "KR" else "%.2f"
        st.number_input("손절가", min_value=0.0, step=step, format=num_fmt, key="rp_stop")
        st.number_input("목표가", min_value=0.0, step=step, format=num_fmt, key="rp_target")
        stop, target = float(ss.rp_stop), float(ss.rp_target)
        if engine.validate_plan(entry, stop, target) is None:
            st.caption(f"손절폭 {(stop / entry - 1) * 100:.1f}% · 목표 +{(target / entry - 1) * 100:.1f}% · "
                       f"손익비 {engine.plan_rr(entry, stop, target):.1f} "
                       f"(추천값: 손절 = 종가 − ATR×{config.REPLAY_STOP_ATR_MULT:g}, 손익비 {config.REPLAY_DEFAULT_RR:g})")
        st.button("📈 매수", type="primary", width="stretch", on_click=decide, args=("buy",))
        st.button("👀 관망 (사지 않음)", width="stretch", on_click=decide, args=("pass",))
        return

    # 결과 화면
    res = rp["result"]
    end = d + config.REPLAY_FUTURE_BARS
    view = df.iloc[start: end + 1]
    split = d - start
    exit_pos = split + 1 + res["exit_pos"]
    win = res["r"] > 0
    lines = {"매수가": entry, "손절가": res["stop"], "목표가": res["target"]}
    markers = [{"pos": split, "price": entry, "text": "판단", "color": config.COLOR_ENTRY, "symbol": "circle"},
               {"pos": exit_pos, "price": res["exit_price"], "text": "청산",
                "color": config.COLOR_TARGET if win else config.COLOR_STOP, "symbol": "x"}]
    st.markdown(f"**{stock_name(rp['symbol'], market)}** · {_period_text(df, start, end)}")
    if res["decision"] == "buy":
        msg = engine.explain_result(res, fmt)
        (st.success if win else st.error)(f"{'⭕' if win else '❌'} {msg}")
    else:
        would = engine.explain_result(res, fmt)
        if res["r"] < 0:
            st.success(f"👀 관망 → 잘 피했어요. 추천 계획대로 샀다면: {would}")
        else:
            st.info(f"👀 관망 → 추천 계획대로 샀다면: {would}")
    st.plotly_chart(build_chart(view, market, show, hide_dates=False, split_pos=split, lines=lines,
                                markers=markers), width="stretch", config={"displayModeBar": False})
    st.caption("점선 오른쪽(밝은 배경)이 판단 뒤 공개된 봉입니다. R = 손절폭 1개를 기준으로 잰 손익.")


# ── 한 봉씩 넘기기형 ───────────────────────────────────
def _render_step(df, rp, start, show, fmt, progress, save, sync):
    d, market = rp["d"], rp["market"]
    last = d + config.REPLAY_STEP_BARS
    cur = rp["cur"]
    close = float(df["Close"].iloc[cur])

    def finish():
        end = rp["cur"]
        if rp["position"]:   # 들고 있으면 마지막 종가에 정리
            rp["trades"].append({"entry": rp["position"]["entry"], "entry_pos": rp["position"]["pos"],
                                 "exit": float(df["Close"].iloc[end]), "exit_pos": end})
            rp["position"] = None
        s = engine.summarize_trades(rp["trades"])
        hold = (float(df["Close"].iloc[end]) / float(df["Close"].iloc[d]) - 1) * 100
        rp.update(done=True, result={**s, "hold_ret_pct": hold, "end": end})
        prog.record_replay(progress, {
            "mode": "step", "symbol": rp["symbol"], "name": stock_name(rp["symbol"], market),
            "period": _period_text(df, start, end), "trades": s["count"],
            "win_rate": round(s["win_rate"], 1), "ret_pct": round(s["total_ret_pct"], 2),
            "hold_ret_pct": round(hold, 2)})
        save()
        sync(f"차트 복기(한 봉씩) {stock_name(rp['symbol'], market)}")

    def buy():
        rp["position"] = {"entry": float(df["Close"].iloc[rp["cur"]]), "pos": rp["cur"]}

    def sell():
        p = rp["position"]
        rp["trades"].append({"entry": p["entry"], "entry_pos": p["pos"],
                             "exit": float(df["Close"].iloc[rp["cur"]]), "exit_pos": rp["cur"]})
        rp["position"] = None

    def next_bar():
        rp["cur"] += 1
        if rp["cur"] >= last:
            finish()

    # 매매 표시
    end_pos = rp["result"]["end"] if rp["done"] else cur
    markers = []
    for t in rp["trades"]:
        markers.append({"pos": t["entry_pos"] - start, "price": t["entry"], "text": "매수",
                        "color": config.COLOR_TARGET, "symbol": "triangle-up", "below": True})
        markers.append({"pos": t["exit_pos"] - start, "price": t["exit"], "text": "매도",
                        "color": config.COLOR_STOP, "symbol": "triangle-down"})
    if rp["position"]:
        markers.append({"pos": rp["position"]["pos"] - start, "price": rp["position"]["entry"], "text": "매수",
                        "color": config.COLOR_TARGET, "symbol": "triangle-up", "below": True})
    view = df.iloc[start: end_pos + 1]
    split = d - start

    if rp["done"]:
        r = rp["result"]
        st.markdown(f"**{stock_name(rp['symbol'], market)}** · {_period_text(df, start, r['end'])}")
        beat = r["total_ret_pct"] > r["hold_ret_pct"]
        (st.success if beat else st.info)(
            f"내 매매 {r['total_ret_pct']:+.1f}% (거래 {r['count']}번, 승률 {r['win_rate']:.0f}%) vs "
            f"그냥 보유 {r['hold_ret_pct']:+.1f}% → {'보유보다 나았어요' if beat else '보유가 더 나았어요'}")
    else:
        st.caption(f"{cur - d} / {config.REPLAY_STEP_BARS} 봉 · 오늘 종가 {fmt(close)}")
        if rp["position"]:
            pnl = (close / rp["position"]["entry"] - 1) * 100
            st.markdown(f"보유 중: 매수가 {fmt(rp['position']['entry'])} → 평가 **{pnl:+.1f}%**")
        else:
            st.markdown("보유 없음 (현금)")
    st.plotly_chart(build_chart(view, market, show, hide_dates=not rp["done"], split_pos=split, markers=markers),
                    width="stretch", config={"displayModeBar": False})

    if not rp["done"]:
        with st.expander("지표 읽기 도움말 (오늘 봉 기준)"):
            for line in engine.indicator_notes(df.iloc[cur]):
                st.write(f"- {line}")
        if rp["position"]:
            st.button("📉 매도 (오늘 종가)", type="primary", width="stretch", on_click=sell)
        else:
            st.button("📈 매수 (오늘 종가)", type="primary", width="stretch", on_click=buy)
        st.button("다음 봉 ▶", width="stretch", on_click=next_bar)
        st.button("여기서 끝내기", width="stretch", on_click=finish)
    if rp["trades"]:
        with st.expander(f"매매 내역 ({len(rp['trades'])}번)"):
            for i, t in enumerate(rp["trades"], 1):
                st.write(f"{i}. {fmt(t['entry'])} → {fmt(t['exit'])} ({(t['exit'] / t['entry'] - 1) * 100:+.1f}%)")
