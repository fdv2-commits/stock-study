"""문제 은행·개념 카드 파일 검사 테스트."""
import json

import pytest

import config
from quiz import bank


def test_실제_개념카드_파일이_정상():
    concepts = bank.load_concepts()
    assert len(concepts) > 0


def test_실제_문제은행_파일이_정상():
    concepts = bank.load_concepts()
    questions = bank.load_questions(concept_ids={c["id"] for c in concepts})
    assert len(questions) > 0


def test_모든_분류에_문제가_있음():
    questions = bank.load_questions()
    cats = {q["category"] for q in questions}
    assert cats == set(config.CATEGORIES)


def test_정답_위치가_한쪽에_몰리지_않음():
    # 보기 섞기를 끄더라도 정답이 늘 1번이면 안 됨
    questions = bank.load_questions()
    positions = {q["answer"] for q in questions}
    assert positions == set(range(1, config.CHOICES_PER_QUESTION + 1))


def _good_question(**override):
    q = {
        "id": "t1", "category": "basic", "level": 1, "concept": "market_cap",
        "question": "질문", "choices": ["가", "나", "다", "라"], "answer": 2, "explanation": "해설",
    }
    q.update(override)
    return q


def test_정상_문제는_오류없음():
    assert bank.validate_questions([_good_question()]) == []


@pytest.mark.parametrize("override, word", [
    ({"choices": ["가", "나", "다"]}, "보기는"),
    ({"choices": ["가", "가", "다", "라"]}, "똑같은 보기"),
    ({"answer": 0}, "정답 번호"),
    ({"answer": 5}, "정답 번호"),
    ({"answer": "2"}, "정답 번호"),
    ({"answer": True}, "정답 번호"),
    ({"category": "없는분류"}, "분류"),
    ({"level": 9}, "난이도"),
    ({"explanation": " "}, "explanation"),
])
def test_잘못된_문제를_잡아냄(override, word):
    errors = bank.validate_questions([_good_question(**override)])
    assert any(word in e for e in errors)


def test_id_중복을_잡아냄():
    errors = bank.validate_questions([_good_question(), _good_question()])
    assert any("중복" in e for e in errors)


def test_없는_개념_연결을_잡아냄():
    errors = bank.validate_questions([_good_question(concept="없는개념")], concept_ids={"market_cap"})
    assert any("개념" in e for e in errors)


def test_JSON_문법오류는_줄번호와_함께_안내(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text('[\n  {"id": "a",}\n]', encoding="utf-8")
    with pytest.raises(bank.BankError, match="2번째 줄"):
        bank.load_questions(path)


def test_파일이_없으면_안내(tmp_path):
    with pytest.raises(bank.BankError, match="찾을 수 없습니다"):
        bank.load_questions(tmp_path / "없음.json")


def test_목록이_아니면_안내(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    with pytest.raises(bank.BankError, match="목록"):
        bank.load_questions(path)
