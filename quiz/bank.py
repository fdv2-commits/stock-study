"""개념 카드와 문제 은행(JSON 파일)을 불러오고 형식이 맞는지 검사한다."""
import json
from pathlib import Path

import config


class BankError(Exception):
    """파일이 없거나 형식이 틀렸을 때 쓰는 오류. 화면에 그대로 안내할 수 있는 한국어 메시지를 담는다."""


def _read_json_list(path: Path) -> list:
    """JSON 파일을 읽어 리스트로 돌려준다. 문제가 있으면 BankError."""
    if not path.exists():
        raise BankError(f"파일을 찾을 수 없습니다: {path.name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        # 쉼표 빠짐 등 JSON 문법 오류 → 몇 번째 줄인지 알려준다
        raise BankError(f"{path.name} {e.lineno}번째 줄 근처에 문법 오류가 있습니다. ({e.msg})") from e
    if not isinstance(data, list):
        raise BankError(f"{path.name}은 [ ... ] 목록 형태여야 합니다.")
    return data


def validate_concepts(concepts: list) -> list[str]:
    """개념 카드 형식을 검사해 문제점 목록(한국어)을 돌려준다. 빈 목록이면 정상."""
    errors = []
    seen = set()
    required = ["id", "category", "title", "summary", "detail", "example"]
    for i, c in enumerate(concepts, start=1):
        label = f"개념 {i}번째({c.get('id', '?')})"
        for key in required:
            if not str(c.get(key, "")).strip():
                errors.append(f"{label}: '{key}' 값이 비어 있습니다.")
        if c.get("id") in seen:
            errors.append(f"{label}: id가 중복됩니다.")
        seen.add(c.get("id"))
        if c.get("category") not in config.CATEGORIES:
            errors.append(f"{label}: 분류 '{c.get('category')}'가 config.CATEGORIES에 없습니다.")
    return errors


def validate_questions(questions: list, concept_ids: set | None = None) -> list[str]:
    """문제 형식을 검사해 문제점 목록(한국어)을 돌려준다. 빈 목록이면 정상.

    concept_ids를 주면, 문제의 concept 값이 실제 개념 카드에 있는지도 확인한다.
    """
    errors = []
    seen = set()
    n = config.CHOICES_PER_QUESTION
    for i, q in enumerate(questions, start=1):
        label = f"문제 {i}번째({q.get('id', '?')})"
        for key in ["id", "question", "explanation"]:
            if not str(q.get(key, "")).strip():
                errors.append(f"{label}: '{key}' 값이 비어 있습니다.")
        if q.get("id") in seen:
            errors.append(f"{label}: id가 중복됩니다.")
        seen.add(q.get("id"))
        if q.get("category") not in config.CATEGORIES:
            errors.append(f"{label}: 분류 '{q.get('category')}'가 config.CATEGORIES에 없습니다.")
        if q.get("level") not in config.LEVELS:
            errors.append(f"{label}: 난이도 '{q.get('level')}'가 config.LEVELS에 없습니다.")
        choices = q.get("choices")
        if not isinstance(choices, list) or len(choices) != n:
            errors.append(f"{label}: 보기는 {n}개여야 합니다.")
        else:
            if any(not str(ch).strip() for ch in choices):
                errors.append(f"{label}: 비어 있는 보기가 있습니다.")
            if len(set(choices)) != len(choices):
                errors.append(f"{label}: 똑같은 보기가 있습니다.")
        answer = q.get("answer")
        # 정답은 1부터 시작하는 번호 (bool은 숫자로 치지 않음)
        if not isinstance(answer, int) or isinstance(answer, bool) or not 1 <= answer <= n:
            errors.append(f"{label}: 정답 번호는 1~{n} 사이 숫자여야 합니다.")
        if concept_ids is not None and q.get("concept") not in concept_ids:
            errors.append(f"{label}: 연결된 개념 '{q.get('concept')}'가 개념 카드에 없습니다.")
    return errors


def load_concepts(path: Path = config.CONCEPTS_FILE) -> list[dict]:
    """개념 카드를 불러온다. 형식이 틀리면 BankError."""
    concepts = _read_json_list(path)
    errors = validate_concepts(concepts)
    if errors:
        raise BankError("개념 카드 파일에 문제가 있습니다:\n- " + "\n- ".join(errors))
    return concepts


def load_questions(path: Path = config.QUESTIONS_FILE, concept_ids: set | None = None) -> list[dict]:
    """문제 은행을 불러온다. 형식이 틀리면 BankError."""
    questions = _read_json_list(path)
    errors = validate_questions(questions, concept_ids)
    if errors:
        raise BankError("문제 은행 파일에 문제가 있습니다:\n- " + "\n- ".join(errors))
    return questions
