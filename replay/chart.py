"""차트 복기용 차트 그리기 (plotly, 어두운 테마).

가로축은 날짜 대신 봉 순서(0, 1, 2 …)를 써서 주말·휴일 빈칸이 생기지 않게 하고,
종목을 가릴 때는 날짜 글자도 숨긴다.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config

# 지표 선택지 (화면 이름 → 내부 이름)
INDICATORS = {"ma": "이동평균 20·60일", "bb": "볼린저밴드", "volume": "거래량", "rsi": "RSI"}


def build_chart(df: pd.DataFrame, market: str, show: set, hide_dates: bool,
                split_pos: int | None = None, lines: dict | None = None,
                markers: list[dict] | None = None) -> go.Figure:
    """차트를 만든다.

    df: 보여줄 봉들(지표 열 포함)
    show: 보여줄 지표 이름 집합 (INDICATORS의 키)
    split_pos: 이 위치(0부터) 뒤로는 '판단 후 공개된 봉' → 세로 점선으로 구분
    lines: {"매수가": 값, "손절가": 값, "목표가": 값} 가로선
    markers: [{"pos": 위치, "price": 가격, "text": "매수", "color": 색, "symbol": "triangle-up"}]
    """
    x = list(range(len(df)))
    rows = [("price", 0.6)]
    if "volume" in show:
        rows.append(("volume", 0.15))
    if "rsi" in show:
        rows.append(("rsi", 0.25))
    total = sum(h for _, h in rows)
    fig = make_subplots(rows=len(rows), cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[h / total for _, h in rows])
    row_of = {name: i + 1 for i, (name, _) in enumerate(rows)}
    colors = config.CANDLE_COLORS[market]

    # 캔들
    fig.add_trace(go.Candlestick(
        x=x, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="가격",
        increasing=dict(line=dict(color=colors["up"]), fillcolor=colors["up"]),
        decreasing=dict(line=dict(color=colors["down"]), fillcolor=colors["down"]),
        showlegend=False,
    ), row=1, col=1)

    if "ma" in show:
        fig.add_trace(go.Scatter(x=x, y=df["ma_short"], name=f"{config.MA_SHORT}일선",
                                 line=dict(color=config.COLOR_MA_SHORT, width=1.3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=x, y=df["ma_long"], name=f"{config.MA_LONG}일선",
                                 line=dict(color=config.COLOR_MA_LONG, width=1.3)), row=1, col=1)
    if "bb" in show:
        for col, label in (("bb_upper", "볼린저 상단"), ("bb_lower", "볼린저 하단")):
            fig.add_trace(go.Scatter(x=x, y=df[col], name=label, showlegend=False,
                                     line=dict(color=config.COLOR_BB, width=1, dash="dot")), row=1, col=1)

    if "volume" in show:
        up = df["Close"] >= df["Open"]
        fig.add_trace(go.Bar(x=x, y=df["Volume"], name="거래량", showlegend=False,
                             marker_color=[colors["up"] if u else colors["down"] for u in up]),
                      row=row_of["volume"], col=1)
    if "rsi" in show:
        r = row_of["rsi"]
        fig.add_trace(go.Scatter(x=x, y=df["rsi"], name="RSI", showlegend=False,
                                 line=dict(color=config.COLOR_RSI, width=1.3)), row=r, col=1)
        for level in (config.RSI_OVERSOLD, config.RSI_OVERBOUGHT):
            fig.add_hline(y=level, line=dict(color=config.COLOR_GUIDE, width=1, dash="dot"), row=r, col=1)
        fig.update_yaxes(range=[0, 100], row=r, col=1)

    # 판단 시점 구분선 + 공개 구간 배경
    if split_pos is not None and split_pos < len(df) - 1:
        fig.add_vrect(x0=split_pos + 0.5, x1=len(df) - 0.5, fillcolor=config.COLOR_REVEAL, opacity=0.08, line_width=0)
        fig.add_vline(x=split_pos + 0.5, line=dict(color=config.COLOR_REVEAL, width=1, dash="dash"))

    line_colors = {"매수가": config.COLOR_ENTRY, "손절가": config.COLOR_STOP, "목표가": config.COLOR_TARGET}
    for label, value in (lines or {}).items():
        fig.add_hline(y=value, line=dict(color=line_colors.get(label, config.COLOR_ENTRY), width=1, dash="dash"),
                      annotation_text=label, annotation_position="top left", row=1, col=1)

    for m in markers or []:
        fig.add_trace(go.Scatter(x=[m["pos"]], y=[m["price"]], mode="markers+text", text=[m["text"]],
                                 textposition="bottom center" if m.get("below") else "top center",
                                 marker=dict(color=m["color"], size=11, symbol=m.get("symbol", "circle")),
                                 textfont=dict(color=m["color"]), showlegend=False), row=1, col=1)

    # 가로축 글자: 숨길 때는 없음, 보일 때는 날짜 몇 개만
    if hide_dates:
        fig.update_xaxes(showticklabels=False)
    else:
        step = max(1, len(df) // 5)
        ticks = x[::step]
        fig.update_xaxes(tickvals=ticks, ticktext=[df.index[i].strftime("%y.%m.%d") for i in ticks],
                         row=len(rows), col=1)
    fig.update_xaxes(rangeslider_visible=False)
    fig.update_layout(
        template=config.CHART_TEMPLATE, height=config.CHART_HEIGHT,
        margin=dict(l=5, r=5, t=10, b=10), dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    return fig
