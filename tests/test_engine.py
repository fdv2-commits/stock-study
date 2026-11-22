"""퀴즈 출제·채점 테스트."""
import random

from quiz import engine

SAMPLE = [
    {"id": f"q{i}", "category": "basic" if i < 3 else "risk", "level": 1 if i % 2 else 2,
     "concept": "c", "question": f"질문{i}", "choices": ["A", "B", "C", "D"], "answer": (i % 4) + 1,
     "explanation": "해설"}
    for i in range(6)
]


def test_분류로_거르기():
    got = engine.filter_questions(SAMPLE, categories={"risk"})
    assert [q["id"] for q in got] == ["q3", "q4", "q5"]


def test_분류와_난이도_함께_거르기():
    got = engine.filter_questions(SAMPLE, categories={"basic"}, levels={1})
    assert [q["id"] for q in got] == ["q1"]


def test_id로_거르기():
    got = engine.filter_questions(SAMPLE, ids={"q0", "q5"})
    assert [q["id"] for q in got] == ["q0", "q5"]


def test_보기를_섞어도_정답_내용은_그대로():
    rng = random.Random(1)
    for q in SAMPLE:
        for _ in range(20):
            p = engine.prepare_question(q, rng, shuffle=True)
            original_answer = q["choices"][q["answer"] - 1]
            assert p["choices"][p["correct_index"]] == original_answer
            assert sorted(p["choices"]) == sorted(q["choices"])


def test_섞지_않으면_파일_순서_그대로():
    p = engine.prepare_question(SAMPLE[2], random.Random(0), shuffle=False)
    assert p["choices"] == ["A", "B", "C", "D"]
    assert p["correct_index"] == 2   # answer 3번 → 위치 2


def test_문제_수만큼_중복없이_출제():
    quiz = engine.build_quiz(SAMPLE, 4, seed=7)
    ids = [q["id"] for q in quiz]
    assert len(ids) == 4 and len(set(ids)) == 4


def test_문제가_모자라면_있는_만큼만():
    assert len(engine.build_quiz(SAMPLE, 100, seed=1)) == len(SAMPLE)


def test_같은_seed면_같은_퀴즈():
    a = engine.build_quiz(SAMPLE, 3, seed=42)
    b = engine.build_quiz(SAMPLE, 3, seed=42)
    assert a == b


def test_채점():
    p = engine.prepare_question(SAMPLE[1], random.Random(0), shuffle=False)  # answer 2 → 위치 1
    assert engine.is_correct(p, 1)
    assert not engine.is_correct(p, 0)


def test_점수_계산():
    assert engine.score([True, False, True, True]) == (3, 4, 75.0)
    assert engine.score([]) == (0, 0, 0.0)
