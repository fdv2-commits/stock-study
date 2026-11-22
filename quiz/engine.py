"""퀴즈 출제(문제 고르기·보기 섞기)와 채점."""
import random

import config


def filter_questions(questions: list[dict], categories=None, levels=None, ids=None) -> list[dict]:
    """조건에 맞는 문제만 골라낸다. 조건이 None이면 그 조건은 따지지 않는다."""
    result = []
    for q in questions:
        if categories is not None and q["category"] not in categories:
            continue
        if levels is not None and q["level"] not in levels:
            continue
        if ids is not None and q["id"] not in ids:
            continue
        result.append(q)
    return result


def prepare_question(q: dict, rng: random.Random, shuffle: bool = config.SHUFFLE_CHOICES) -> dict:
    """화면에 낼 문제 하나를 만든다. 보기 순서를 섞고, 섞인 뒤의 정답 위치(0부터)를 기록한다."""
    order = list(range(len(q["choices"])))
    if shuffle:
        rng.shuffle(order)
    choices = [q["choices"][i] for i in order]
    # 파일의 answer는 1부터 시작하는 번호 → 0부터 시작하는 위치로 바꾼 뒤, 섞인 순서에서 찾는다
    correct_index = order.index(q["answer"] - 1)
    return {
        "id": q["id"],
        "category": q["category"],
        "level": q["level"],
        "concept": q.get("concept"),
        "question": q["question"],
        "choices": choices,
        "correct_index": correct_index,
        "explanation": q["explanation"],
    }


def build_quiz(questions: list[dict], count: int, seed=None, shuffle: bool = config.SHUFFLE_CHOICES) -> list[dict]:
    """문제 목록에서 count개를 무작위로 뽑아 퀴즈를 만든다. 문제가 모자라면 있는 만큼만 낸다.

    seed를 주면 항상 같은 퀴즈가 나온다(테스트용).
    """
    rng = random.Random(seed)
    picked = rng.sample(questions, min(count, len(questions)))
    return [prepare_question(q, rng, shuffle) for q in picked]


def is_correct(prepared: dict, chosen_index: int) -> bool:
    """고른 보기 위치(0부터)가 정답인지."""
    return chosen_index == prepared["correct_index"]


def score(results: list[bool]) -> tuple[int, int, float]:
    """채점 결과 목록 → (맞힌 수, 전체 수, 정답률 %)."""
    total = len(results)
    correct = sum(1 for r in results if r)
    rate = correct / total * 100 if total else 0.0
    return correct, total, rate
