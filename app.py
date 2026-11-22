"""주식 공부 프로그램 화면 (1단계: 개념 카드 + 퀴즈 + 오답 노트 + 학습 기록).

실행: .venv\\Scripts\\streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from quiz import bank, engine, progress as prog

st.set_page_config(page_title="주식 공부", page_icon="📚", layout="centered")

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
    return concepts, questions


def _mtime(path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


try:
    CONCEPTS, QUESTIONS = load_content(_mtime(config.CONCEPTS_FILE), _mtime(config.QUESTIONS_FILE))
except bank.BankError as e:
    st.title(config.APP_TITLE)
    st.error(str(e))
    st.info("content 폴더의 JSON 파일을 고친 뒤 새로고침하세요.")
    st.stop()

CONCEPT_BY_ID = {c["id"]: c for c in CONCEPTS}
QUESTION_BY_ID = {q["id"]: q for q in QUESTIONS}

# 학습 기록은 처음 한 번만 파일에서 읽고, 이후엔 session_state에서 고쳐 가며 저장한다
if "progress" not in st.session_state:
    data, warning = prog.load_progress()
    st.session_state.progress = data
    st.session_state.progress_warning = warning
PROGRESS = st.session_state.progress


def save():
    """학습 기록 저장. 실패하면 경고를 띄운다."""
    warning = prog.save_progress(PROGRESS)
    if warning:
        st.session_state.progress_warning = warning


# ── 화면 머리 ─────────────────────────────────────────
st.title(config.APP_TITLE)
st.caption(f"⚠️ {config.DISCLAIMER}")
if st.session_state.get("progress_warning"):
    st.warning(st.session_state.progress_warning)

tab_concept, tab_quiz, tab_wrong, tab_stats = st.tabs(["📖 개념", "📝 퀴즈", "❌ 오답 노트", "📊 기록"])


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
    st.session_state.quiz_saved = False    # 퀴즈 기록을 저장했는지


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
    """'다음 문제' 버튼."""
    st.session_state.quiz_idx += 1
    st.session_state.quiz_checked = False


def quit_quiz():
    """퀴즈 그만두기 / 새 퀴즈."""
    st.session_state.quiz = None


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
        if not st.session_state.quiz_saved:
            prog.record_session(PROGRESS, st.session_state.quiz_label, total, correct)
            save()
            st.session_state.quiz_saved = True
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


# ── 4) 학습 기록 ─────────────────────────────────────
with tab_stats:
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

st.divider()
st.caption(f"⚠️ {config.DISCLAIMER}")
