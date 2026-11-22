"""학습 기록·오답 노트 테스트."""
import config
from quiz import progress as prog


def test_정답_오답_기록():
    p = prog.empty_progress()
    prog.record_answer(p, "a", True, when="t1")
    prog.record_answer(p, "a", False, when="t2")
    prog.record_answer(p, "a", True, when="t3")
    assert p["questions"]["a"] == {"seen": 3, "correct": 2, "wrong": 1, "streak": 1, "last": "t3"}


def test_오답노트_들어가고_졸업하기():
    p = prog.empty_progress()
    prog.record_answer(p, "a", False)
    assert prog.wrong_note_ids(p, streak_needed=2) == ["a"]
    prog.record_answer(p, "a", True)
    assert prog.wrong_note_ids(p, streak_needed=2) == ["a"]   # 1번 맞힘 → 아직 남음
    prog.record_answer(p, "a", True)
    assert prog.wrong_note_ids(p, streak_needed=2) == []      # 2번 연속 → 졸업


def test_다시_틀리면_오답노트로_돌아옴():
    p = prog.empty_progress()
    for ok in [False, True, True, False]:
        prog.record_answer(p, "a", ok)
    assert prog.wrong_note_ids(p, streak_needed=2) == ["a"]


def test_한번도_안_틀린_문제는_오답노트에_없음():
    p = prog.empty_progress()
    prog.record_answer(p, "a", True)
    assert prog.wrong_note_ids(p) == []


def test_저장하고_다시_읽기(tmp_path):
    path = tmp_path / "progress.json"
    p = prog.empty_progress()
    prog.record_answer(p, "a", False, when="t")
    prog.record_session(p, "기초 용어", 10, 7, when="t")
    assert prog.save_progress(p, path) is None
    loaded, warning = prog.load_progress(path)
    assert warning is None
    assert loaded == p


def test_파일이_없으면_빈_기록(tmp_path):
    loaded, warning = prog.load_progress(tmp_path / "없음.json")
    assert loaded == prog.empty_progress() and warning is None


def test_깨진_파일이면_빈_기록과_경고(tmp_path):
    path = tmp_path / "progress.json"
    path.write_text("{깨짐", encoding="utf-8")
    loaded, warning = prog.load_progress(path)
    assert loaded == prog.empty_progress()
    assert "읽지 못해" in warning


def test_정답률_색_등급():
    assert prog.accuracy_level(config.ACCURACY_GOOD) == "good"
    assert prog.accuracy_level(config.ACCURACY_GOOD - 0.1) == "ok"
    assert prog.accuracy_level(config.ACCURACY_OK) == "ok"
    assert prog.accuracy_level(config.ACCURACY_OK - 0.1) == "bad"


def test_분류별_통계():
    questions = [
        {"id": "a", "category": "basic"},
        {"id": "b", "category": "basic"},
        {"id": "c", "category": "risk"},
    ]
    p = prog.empty_progress()
    prog.record_answer(p, "a", True)
    prog.record_answer(p, "b", False)
    prog.record_answer(p, "c", True)
    prog.record_answer(p, "지워진문제", True)   # 문제 은행에 없는 id는 무시
    stats = prog.category_stats(p, questions)
    assert stats["basic"] == {"answered": 2, "correct": 1, "rate": 50.0}
    assert stats["risk"]["rate"] == 100.0
    assert stats["chart"]["answered"] == 0
