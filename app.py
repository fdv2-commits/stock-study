"""주식 공부 프로그램 화면 (개념 카드 + 퀴즈 + 오답 노트 + 차트 복기 + 전략 백테스트 + 학습 기록).

실행: .venv\\Scripts\\streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import hmac

import config
from quiz import bank, engine, progress as prog
from storage import remote
from storage.keys import get_secret
import ui_backtest
import ui_replay

st.set_page_config(page_title="주식 공부", page_icon="📚", layout="centered")
st.title(config.APP_TITLE)


def password_gate() -> None:
    """APP_PASSWORD가 설정돼 있으면 비밀번호를 맞혀야 화면이 열린다 (설정 안 하면 그냥 통과).

    배포한 앱 주소를 다른 사람이 알더라도 학습 기록을 보거나 바꾸지 못하게 잠그는 용도.
    """
    pw = get_secret("APP_PASSWORD")
    if not pw or st.session_state.get("_auth_ok"):
        return
    entered = st.text_input("🔒 비밀번호", type="password")
    if entered and hmac.compare_digest(entered.encode(), pw.encode()):
        st.session_state["_auth_ok"] = True
        st.rerun()
    if entered:
        st.error("비밀번호가 틀렸습니다.")
    st.caption(f"⚠️ {config.DISCLAIMER}")
    st.stop()


password_gate()

# 색 등급 → 실제 색·이름
LEVEL_COLOR = {"good": config.COLOR_GOOD, "ok": config.COLOR_OK, "bad": config.COLOR_BAD}
LEVEL_EMOJI = {"good": "🟢", "ok": "🟡", "bad": "🔴"}
COLOR_RULE = (
    f"🟢 {config.ACCURACY_GOOD}% 이상 · 🟡 {config.ACCURACY_OK}~{config.ACCURACY_GOOD}% · "
    f"🔴 {config.ACCURACY_OK}% 미만"
)


# ── 데이터 불러오기 ─────────────────────────────────────
@st.cache_data
def load_content(concepts_mtime: float, questions_mtime: float):
    """개념 카드와 문제 은행을 불러온다.

    파일 수정 시각을 인자로 받으므로, JSON 파일을 고치면 자동으로 다시 읽는다.
    """
    concepts = bank.load_concepts()
    questions = bank.load_questions(concept_ids={c["id"] for c in concepts})
    return [_md_safe(c) for c in concepts], [_md_safe(q) for q in questions]


def _md_safe(item: dict) -> dict:
    """화면 글자에서 물결표(~)를 그대로 보이게 바꾼다.

    Streamlit은 '09:00~15:30 ... 09:30~16:00'처럼 ~가 두 번 나오면 그 사이를 취소선으로 그리기 때문.
    """
    keep = {"id", "category", "concept", "level", "answer"}
    out = {}
    for key, value in item.items():
        if key in keep:
            out[key] = value
        elif isinstance(value, str):
            out[key] = value.replace("~", r"\~")
        elif isinstance(value, list):
            out[key] = [v.replace("~", r"\~") if isinstance(v, str) else v for v in value]
        else:
            out[key] = value
    return out


def _mtime(path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


try:
    CONCEPTS, QUESTIONS = load_content(_mtime(config.CONCEPTS_FILE), _mtime(config.QUESTIONS_FILE))
except bank.BankError as e:
    st.error(str(e))
    st.info("content 폴더의 JSON 파일을 고친 뒤 새로고침하세요.")
    st.stop()

CONCEPT_BY_ID = {c["id"]: c for c in CONCEPTS}
QUESTION_BY_ID = {q["id"]: q for q in QUESTIONS}

# 학습 기록은 처음 한 번만 파일에서 읽고, 이후엔 session_state에서 고쳐 가며 저장한다
if "progress" not in st.session_state:
    # 배포 환경이면 GitHub에 보관된 최신 기록을 먼저 내려받는다 (꺼져 있으면 아무 일도 안 함)
    remote.safe_pull(config.PROGRESS_FILE)
    data, warning = prog.load_progress()
    st.session_state.progress = data
    st.session_state.progress_warning = warning
    st.session_state.unsynced = 0          # 아직 GitHub에 올리지 않은 풀이 수
PROGRESS = st.session_state.progress


def sync(message: str = "학습 기록 저장"):
    """GitHub 보관이 켜져 있으면 지금 기록을 올린다."""
    if remote.enabled() and st.session_state.unsynced:
        remote.safe_push(config.PROGRESS_FILE, message)
        if remote.last_error is None:
            st.session_state.unsynced = 0


def save():
    """학습 기록을 이 컴퓨터(서버)에 저장하고, 몇 문제마다 GitHub에도 올린다."""
    warning = prog.save_progress(PROGRESS)
    if warning:
        st.session_state.progress_warning = warning
        return
    st.session_state.unsynced += 1
    if st.session_state.unsynced >= config.REMOTE_PUSH_EVERY:
        sync()


# ── 화면 머리 ─────────────────────────────────────────
st.caption(f"⚠️ {config.DISCLAIMER}")
if st.session_state.get("progress_warning"):
    st.warning(st.session_state.progress_warning)
if remote.last_error:
    st.warning(f"학습 기록 GitHub 보관 실패 (이 기기에는 저장됨): {remote.last_error}")

tab_concept, tab_quiz, tab_wrong, tab_replay, tab_bt, tab_stats = st.tabs(
    ["개념", "퀴즈", "오답", "복기", "전략", "기록"])   # 휴대폰 한 줄에 다 보이도록 짧게


# ── 1) 개념 카드 ──────────────────────────────────────
with tab_concept:
    cat_options = ["전체"] + list(config.CATEGORIES)
    cat = st.selectbox(
        "분류",
        cat_options,
        format_func=lambda c: "전체" if c == "전체" else config.CATEGORIES[c],
        key="concept_cat",
    )
    keyword = st.text_input("검색 (예: RSI, 손절)", key="concept_search").strip().lower()

    shown = 0
    for c in CONCEPTS:
        if cat != "전체" and c["category"] != cat:
            continue
        text = " ".join([c["title"], c["summary"], c["detail"]]).lower()
        if keyword and keyword not in text:
            continue
        shown += 1
        with st.expander(f"**{c['title']}** — {c['summary']}"):
            st.write(c["detail"])
            st.info(f"예시: {c['example']}")
            # 이 개념과 연결된 문제 수, 내 정답률
            related = [q["id"] for q in QUESTIONS if q.get("concept") == c["id"]]
            seen = sum(PROGRESS["questions"].get(qid, {}).get("seen", 0) for qid in related)
            correct = sum(PROGRESS["questions"].get(qid, {}).get("correct", 0) for qid in related)
            if seen:
                rate = correct / seen * 100
                st.caption(
                    f"{LEVEL_EMOJI[prog.accuracy_level(rate)]} 관련 문제 {len(related)}개 · "
                    f"내 정답률 {rate:.0f}% ({correct}/{seen}) → {COLOR_RULE}"
                )
            else:
                st.caption(f"관련 문제 {len(related)}개 · 아직 풀지 않음")
    if shown == 0:
        st.info("조건에 맞는 개념이 없습니다.")
    st.caption(f"개념 카드 {len(CONCEPTS)}개 · 문제 {len(QUESTIONS)}개")


# ── 2) 퀴즈 ──────────────────────────────────────────
def start_quiz(mode: str, cats: list, levels: list, count: int):
    """'퀴즈 시작' 버튼을 눌렀을 때: 문제를 골라 퀴즈를 만든다."""
    if mode == "wrong":
        pool = engine.filter_questions(QUESTIONS, ids=set(prog.wrong_note_ids(PROGRESS)))
        label = "오답 노트"
    else:
        pool = engine.filter_questions(QUESTIONS, categories=set(cats), levels=set(levels))
        label = "전체" if len(cats) == len(config.CATEGORIES) else ", ".join(config.CATEGORIES[c] for c in cats)
    if not pool:
        st.session_state.quiz_notice = "조건에 맞는 문제가 없습니다. 분류나 난이도를 바꿔 보세요."
        return
    st.session_state.quiz_notice = None
    st.session_state.quiz = engine.build_quiz(pool, count)
    st.session_state.quiz_label = label
    st.session_state.quiz_idx = 0          # 지금 풀고 있는 문제 번호(0부터)
    st.session_state.quiz_results = []     # 문제별 맞힘(True)/틀림(False)
    st.session_state.quiz_checked = False  # 지금 문제의 정답을 확인했는지
    st.session_state.quiz_run = st.session_state.get("quiz_run", 0) + 1  # 보기 선택 상자 초기화용


def check_answer(prepared: dict, radio_key: str):
    """'정답 확인' 버튼: 채점하고 바로 학습 기록에 저장한다."""
    chosen = st.session_state.get(radio_key)
    if chosen is None:
        return
    ok = engine.is_correct(prepared, chosen)
    st.session_state.quiz_results.append(ok)
    st.session_state.quiz_checked = True
    prog.record_answer(PROGRESS, prepared["id"], ok)
    save()


def next_question():
    """'다음 문제' / '결과 보기' 버튼.

    마지막 문제였다면 여기서 퀴즈 기록을 한 번만 남긴다.
    (화면 그리는 코드에서 저장하면, 저장 도중 화면이 다시 그려질 때 두 번 저장될 수 있음)
    """
    st.session_state.quiz_idx += 1
    st.session_state.quiz_checked = False
    if st.session_state.quiz_idx == len(st.session_state.quiz):
        correct, total, _ = engine.score(st.session_state.quiz_results)
        prog.record_session(PROGRESS, st.session_state.quiz_label, total, correct)
        save()
        sync(f"퀴즈 완료 {correct}/{total}")


def quit_quiz():
    """퀴즈 그만두기 / 새 퀴즈. 남은 기록을 GitHub에 올린다."""
    st.session_state.quiz = None
    sync("퀴즈 중단")


with tab_quiz:
    quiz = st.session_state.get("quiz")

    if not quiz:
        # 퀴즈 설정 화면
        wrong_count = len(prog.wrong_note_ids(PROGRESS))
        mode = st.radio(
            "문제 범위",
            ["new", "wrong"],
            format_func=lambda m: "새 퀴즈" if m == "new" else f"오답 노트 문제만 ({wrong_count}개)",
            horizontal=True,
            key="quiz_mode",
        )
        cats, levels = list(config.CATEGORIES), list(config.LEVELS)
        if mode == "new":
            cats = st.multiselect(
                "분류", list(config.CATEGORIES), default=list(config.CATEGORIES),
                format_func=lambda c: config.CATEGORIES[c], key="quiz_cats",
            )
            levels = st.multiselect(
                "난이도", list(config.LEVELS), default=list(config.LEVELS),
                format_func=lambda lv: config.LEVELS[lv], key="quiz_levels",
            )
        count = st.select_slider(
            "문제 수", options=config.QUIZ_COUNT_OPTIONS, value=config.QUIZ_DEFAULT_COUNT, key="quiz_count"
        )
        st.button(
            "퀴즈 시작", type="primary", width="stretch",
            on_click=start_quiz, args=(mode, cats, levels, count),
            disabled=(mode == "wrong" and wrong_count == 0) or (mode == "new" and (not cats or not levels)),
        )
        if mode == "wrong" and wrong_count == 0:
            st.caption("오답 노트가 비어 있습니다. 먼저 새 퀴즈를 풀어 보세요.")
        if st.session_state.get("quiz_notice"):
            st.warning(st.session_state.quiz_notice)

    elif st.session_state.quiz_idx < len(quiz):
        # 문제 풀이 화면
        idx = st.session_state.quiz_idx
        q = quiz[idx]
        st.progress(idx / len(quiz), text=f"{idx + 1} / {len(quiz)} 문제 · {st.session_state.quiz_label}")
        st.caption(f"{config.CATEGORIES[q['category']]} · {config.LEVELS[q['level']]}")
        st.markdown(f"##### {q['question']}")

        radio_key = f"answer_{st.session_state.quiz_run}_{idx}"
        st.radio(
            "보기",
            list(range(len(q["choices"]))),
            format_func=lambda i: f"{i + 1}. {q['choices'][i]}",
            index=None,
            key=radio_key,
            label_visibility="collapsed",
            disabled=st.session_state.quiz_checked,
        )

        if not st.session_state.quiz_checked:
            st.button(
                "정답 확인", type="primary", width="stretch",
                on_click=check_answer, args=(q, radio_key),
                disabled=st.session_state.get(radio_key) is None,
            )
        else:
            correct_text = f"{q['correct_index'] + 1}. {q['choices'][q['correct_index']]}"
            if st.session_state.quiz_results[-1]:
                st.success(f"⭕ 정답! {correct_text}")
            else:
                chosen = st.session_state[radio_key]
                st.error(f"❌ 오답 — 고른 답: {chosen + 1}번 / 정답: {correct_text}")
            st.write(f"💡 {q['explanation']}")
            concept = CONCEPT_BY_ID.get(q.get("concept"))
            if concept:
                st.caption(f"관련 개념: {concept['title']} — {concept['summary']}")
            last = idx == len(quiz) - 1
            st.button(
                "결과 보기" if last else "다음 문제", type="primary", width="stretch",
                on_click=next_question,
            )
        st.button("그만두기", on_click=quit_quiz, key="quit_quiz")

    else:
        # 결과 화면
        results = st.session_state.quiz_results
        correct, total, rate = engine.score(results)
        level = prog.accuracy_level(rate)
        st.markdown(f"### {LEVEL_EMOJI[level]} {correct} / {total} 맞힘 ({rate:.0f}%)")
        st.caption(f"정답률 {rate:.0f}% → {COLOR_RULE}")
        wrong = [q for q, ok in zip(quiz, results) if not ok]
        if wrong:
            st.markdown("**틀린 문제** (오답 노트에 저장됨)")
            for q in wrong:
                with st.expander(q["question"]):
                    st.write(f"정답: {q['choices'][q['correct_index']]}")
                    st.write(f"💡 {q['explanation']}")
        else:
            st.balloons()
            st.success("모두 맞혔습니다!")
        st.button("새 퀴즈", type="primary", width="stretch", on_click=quit_quiz)


# ── 3) 오답 노트 ─────────────────────────────────────
with tab_wrong:
    ids = [qid for qid in prog.wrong_note_ids(PROGRESS) if qid in QUESTION_BY_ID]
    st.caption(
        f"틀린 문제가 모입니다. 같은 문제를 {config.MASTERY_STREAK}번 연속 맞히면 오답 노트에서 빠집니다. "
        "퀴즈 탭에서 '오답 노트 문제만'을 골라 다시 풀 수 있어요."
    )
    if not ids:
        st.info("오답 노트가 비어 있습니다. 👍")
    # 많이 틀린 문제부터
    ids.sort(key=lambda qid: PROGRESS["questions"][qid]["wrong"], reverse=True)
    for qid in ids:
        q = QUESTION_BY_ID[qid]
        s = PROGRESS["questions"][qid]
        with st.expander(f"{q['question']}"):
            st.write(f"정답: **{q['choices'][q['answer'] - 1]}**")
            st.write(f"💡 {q['explanation']}")
            st.caption(
                f"{config.CATEGORIES[q['category']]} · 틀림 {s['wrong']}번 · "
                f"연속 정답 {s['streak']}/{config.MASTERY_STREAK} · 마지막 풀이 {s['last']}"
            )


# ── 4) 차트 복기 ─────────────────────────────────────
with tab_replay:
    ui_replay.render(PROGRESS, save, sync)


# ── 5) 전략 백테스트 ──────────────────────────────────
with tab_bt:
    ui_backtest.render()


# ── 6) 학습 기록 ─────────────────────────────────────
with tab_stats:
    # 기록이 어디에 보관되는지 표시 (배포 앱에서 보관이 꺼져 있으면 재시작 때 기록이 사라짐)
    if remote.enabled():
        st.caption(f"☁️ 기록 보관: GitHub 켜짐 ({config.REMOTE_DIR}/{config.PROGRESS_FILE.name})")
    else:
        st.caption("💾 기록 보관: 이 기기에만 저장 (GitHub 보관 꺼짐 — 배포 앱이라면 Secrets 확인)")
    qstats = PROGRESS["questions"]
    answered = sum(s.get("seen", 0) for s in qstats.values())
    correct_all = sum(s.get("correct", 0) for s in qstats.values())
    covered = len([qid for qid in qstats if qid in QUESTION_BY_ID])

    if answered == 0:
        st.info("아직 푼 문제가 없습니다. 퀴즈 탭에서 시작해 보세요.")
    else:
        rate_all = correct_all / answered * 100
        c1, c2 = st.columns(2)
        c1.metric("전체 정답률", f"{rate_all:.0f}%", help=f"{correct_all} / {answered}")
        c2.metric("풀어 본 문제", f"{covered} / {len(QUESTIONS)}")
        c3, c4 = st.columns(2)
        c3.metric("오답 노트", f"{len(prog.wrong_note_ids(PROGRESS))}개")
        c4.metric("푼 퀴즈", f"{len(PROGRESS['sessions'])}회")

        # 분류별 정답률 막대 그래프
        st.markdown("**분류별 정답률**")
        cstats = prog.category_stats(PROGRESS, QUESTIONS)
        names, rates, colors, texts = [], [], [], []
        for cat, s in cstats.items():
            if s["answered"] == 0:
                continue
            names.append(config.CATEGORIES[cat])
            rates.append(s["rate"])
            colors.append(LEVEL_COLOR[prog.accuracy_level(s["rate"])])
            texts.append(f"{s['rate']:.0f}% ({s['correct']}/{s['answered']})")
        # 막대가 짧으면(정답률 낮음) 글자를 막대 밖에 써야 보인다
        positions = ["inside" if r >= config.CHART_TEXT_INSIDE_MIN else "outside" for r in rates]
        fig = go.Figure(go.Bar(x=rates, y=names, orientation="h", marker_color=colors,
                               text=texts, textposition=positions, cliponaxis=False))
        fig.update_layout(
            template=config.CHART_TEMPLATE, height=60 + 45 * len(names),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(range=[0, 100], title="정답률(%)"), yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption(COLOR_RULE)

        # 최근 퀴즈 기록
        if PROGRESS["sessions"]:
            st.markdown("**최근 퀴즈**")
            recent = list(reversed(PROGRESS["sessions"]))[: config.RECENT_SESSIONS_SHOWN]
            df = pd.DataFrame(recent)
            df["정답률"] = (df["correct"] / df["total"] * 100).round(0).astype(int).astype(str) + "%"
            df = df.rename(columns={"time": "시간", "label": "범위", "total": "문제", "correct": "맞힘"})
            st.dataframe(df[["시간", "범위", "맞힘", "문제", "정답률"]], hide_index=True, width="stretch")

    # 차트 복기 성적
    st.markdown("---")
    st.markdown("**🕯️ 차트 복기 성적**")
    rs = prog.replay_stats(PROGRESS)
    if not PROGRESS.get("replays"):
        st.info("아직 복기한 차트가 없습니다. 복기 탭에서 시작해 보세요.")
    else:
        r1, r2 = st.columns(2)
        r1.metric("매수 판단", f"{rs['buys']}번", help="한 번 판단형에서 매수한 횟수")
        win_rate = rs["wins"] / rs["buys"] * 100 if rs["buys"] else 0
        r2.metric("승률", f"{win_rate:.0f}%", help=f"이익으로 끝난 판 {rs['wins']} / {rs['buys']}")
        r3, r4 = st.columns(2)
        r3.metric("평균 R", f"{rs['avg_r']:+.2f}R", help=f"합계 {rs['total_r']:+.2f}R (0보다 크면 길게 보면 이익)")
        r4.metric("관망 성공", f"{rs['good_passes']} / {rs['passes']}", help="관망했는데 샀다면 손해였던 판")
        if rs["buys"]:
            st.caption(f"평균 {rs['avg_r']:+.2f}R → {'0보다 커서 길게 보면 이익인 판단' if rs['avg_r'] > 0 else '0 이하라 아직은 손해인 판단'}")
        if rs["steps"]:
            st.caption(f"한 봉씩 넘기기 {rs['steps']}판 · 평균 수익률 {rs['step_avg_ret']:+.1f}% · "
                       f"그냥 보유보다 나았던 판 {rs['step_beat']}번")
        recent = list(reversed(PROGRESS["replays"]))[: config.RECENT_SESSIONS_SHOWN]
        rows = []
        for r in recent:
            if r.get("mode") == "step":
                result = f"{r['ret_pct']:+.1f}% (보유 {r['hold_ret_pct']:+.1f}%)"
                kind = "한 봉씩"
            elif r.get("decision") == "buy":
                result, kind = f"{r['r']:+.2f}R ({r['ret_pct']:+.1f}%)", "매수"
            else:
                result, kind = f"샀다면 {r['would_r']:+.2f}R", "관망"
            rows.append({"시간": r["time"], "종목": r.get("name", r.get("symbol", "")), "판단": kind, "결과": result})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.divider()
st.caption(f"⚠️ {config.DISCLAIMER}")
