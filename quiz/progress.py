"""학습 기록(문제별 맞힘/틀림, 오답 노트, 퀴즈 기록)을 progress.json에 저장하고 불러온다.

progress.json 모양:
{
  "questions": {"b01": {"seen": 3, "correct": 2, "wrong": 1, "streak": 2, "last": "2026-11-23 08:10"}},
  "sessions":  [{"time": "2026-11-23 08:10", "label": "기초 용어", "total": 10, "correct": 8}],
  "replays":   [{"time": "...", "mode": "one", "symbol": "AAPL", "decision": "buy", "r": 1.8, "ret_pct": 5.2, ...}]
}
"""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config


def empty_progress() -> dict:
    """아직 공부 기록이 없을 때의 빈 기록."""
    return {"questions": {}, "sessions": [], "replays": []}


def _now() -> str:
    """지금 시각 (config.TIMEZONE 기준, 기본 한국 시간)."""
    return datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d %H:%M")


def load_progress(path: Path = config.PROGRESS_FILE) -> tuple[dict, str | None]:
    """학습 기록을 불러온다. (기록, 경고 메시지) — 파일이 깨졌으면 빈 기록과 경고를 돌려준다."""
    if not path.exists():
        return empty_progress(), None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("형식 오류")
        data.setdefault("questions", {})
        data.setdefault("sessions", [])
        data.setdefault("replays", [])   # 2단계(차트 복기) 전에 만든 기록에도 칸을 만들어 줌
        return data, None
    except (json.JSONDecodeError, ValueError, OSError):
        return empty_progress(), f"학습 기록 파일({path.name})을 읽지 못해 빈 기록으로 시작합니다."


def save_progress(progress: dict, path: Path = config.PROGRESS_FILE) -> str | None:
    """학습 기록을 저장한다. 실패하면 경고 메시지를 돌려준다(앱은 멈추지 않음)."""
    try:
        # 임시 파일에 먼저 쓰고 바꿔치기 → 저장 도중 꺼져도 기존 파일이 깨지지 않음
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return None
    except OSError as e:
        return f"학습 기록을 저장하지 못했습니다: {e}"


def record_answer(progress: dict, question_id: str, correct: bool, when: str | None = None) -> dict:
    """문제 하나를 풀었을 때 기록을 갱신한다. (progress를 직접 고치고 그대로 돌려준다)"""
    stat = progress["questions"].setdefault(
        question_id, {"seen": 0, "correct": 0, "wrong": 0, "streak": 0, "last": ""}
    )
    stat["seen"] += 1
    if correct:
        stat["correct"] += 1
        stat["streak"] += 1      # 연속으로 맞힌 횟수
    else:
        stat["wrong"] += 1
        stat["streak"] = 0       # 틀리면 연속 기록 초기화
    stat["last"] = when or _now()
    return progress


def record_session(progress: dict, label: str, total: int, correct: int, when: str | None = None) -> dict:
    """퀴즈 한 번을 끝냈을 때 기록을 남긴다."""
    progress["sessions"].append({"time": when or _now(), "label": label, "total": total, "correct": correct})
    return progress


def wrong_note_ids(progress: dict, streak_needed: int = config.MASTERY_STREAK) -> list[str]:
    """오답 노트에 있는 문제 id 목록.

    한 번이라도 틀렸고, 그 뒤로 streak_needed번 연속 맞히지 못한 문제가 오답 노트에 남는다.
    """
    return [
        qid for qid, s in progress["questions"].items()
        if s.get("wrong", 0) > 0 and s.get("streak", 0) < streak_needed
    ]


def accuracy_level(rate: float) -> str:
    """정답률(%) → 색 등급. 'good'(초록) / 'ok'(노랑) / 'bad'(빨강). 기준은 config."""
    if rate >= config.ACCURACY_GOOD:
        return "good"
    if rate >= config.ACCURACY_OK:
        return "ok"
    return "bad"


def category_stats(progress: dict, questions: list[dict]) -> dict[str, dict]:
    """분류별 풀이 수·맞힌 수·정답률. {분류: {"answered": n, "correct": n, "rate": %}}"""
    cat_of = {q["id"]: q["category"] for q in questions}
    stats = {cat: {"answered": 0, "correct": 0, "rate": 0.0} for cat in config.CATEGORIES}
    for qid, s in progress["questions"].items():
        cat = cat_of.get(qid)
        if cat is None:   # 문제 은행에서 지워진 문제는 건너뜀
            continue
        stats[cat]["answered"] += s.get("seen", 0)
        stats[cat]["correct"] += s.get("correct", 0)
    for s in stats.values():
        s["rate"] = s["correct"] / s["answered"] * 100 if s["answered"] else 0.0
    return stats


# ── 차트 복기 기록 ─────────────────────────────────────
def record_replay(progress: dict, item: dict, when: str | None = None) -> dict:
    """차트 복기 한 판의 결과를 남긴다. item 예:
    한 번 판단형: {"mode": "one", "symbol", "name", "period", "decision": "buy"/"pass", "r", "ret_pct", "reason", "would_r"}
    한 봉씩:      {"mode": "step", "symbol", "name", "period", "trades", "win_rate", "ret_pct", "hold_ret_pct"}
    """
    progress.setdefault("replays", []).append({"time": when or _now(), **item})
    return progress


def replay_stats(progress: dict) -> dict:
    """차트 복기 성적 요약.

    - buys: 한 번 판단형에서 매수한 판 수, wins: 그중 이익(R>0), avg_r·total_r: 평균·합계 R
    - passes: 관망한 판 수, good_passes: 관망했는데 '매수했다면 손해'였던 판 수
    - steps: 한 봉씩 넘기기 판 수, step_avg_ret: 평균 수익률(%), step_beat: 그냥 보유보다 나았던 판 수
    """
    reps = progress.get("replays", [])
    buys = [r for r in reps if r.get("mode") == "one" and r.get("decision") == "buy"]
    passes = [r for r in reps if r.get("mode") == "one" and r.get("decision") == "pass"]
    steps = [r for r in reps if r.get("mode") == "step"]
    total_r = sum(r["r"] for r in buys)
    return {
        "buys": len(buys),
        "wins": sum(1 for r in buys if r["r"] > 0),
        "avg_r": total_r / len(buys) if buys else 0.0,
        "total_r": total_r,
        "passes": len(passes),
        "good_passes": sum(1 for r in passes if r.get("would_r", 0) < 0),
        "steps": len(steps),
        "step_avg_ret": sum(r["ret_pct"] for r in steps) / len(steps) if steps else 0.0,
        "step_beat": sum(1 for r in steps if r["ret_pct"] > r.get("hold_ret_pct", 0)),
    }
