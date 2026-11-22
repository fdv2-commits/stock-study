# 📚 주식 공부 프로그램

주식 투자 공부를 돕는 Streamlit 웹앱입니다. 학습용이며, 투자 판단과 책임은 사용자에게 있습니다.

## 단계
- **1단계 (완료)**: 개념 카드 + 개념·용어 퀴즈 + 오답 노트 + 학습 기록
- 2단계 (예정): 차트 복기 연습
- 3단계 (예정): 전략 백테스트

## 실행 방법 (PowerShell)

```powershell
cd C:\stock_study
```

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

브라우저가 열리지 않으면 주소창에 `http://localhost:8501` 을 입력하세요. 끝낼 때는 PowerShell 창에서 `Ctrl + C`.

테스트 실행:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 화면 구성
| 탭 | 하는 일 |
|---|---|
| 📖 개념 | 분류·검색으로 개념 카드 보기. 개념별 내 정답률 표시 |
| 📝 퀴즈 | 분류·난이도·문제 수를 골라 4지선다 퀴즈. 한 문제씩 풀고 바로 해설 확인 |
| ❌ 오답 노트 | 틀린 문제 모음. 같은 문제를 2번 연속 맞히면 빠짐 (횟수는 config.py) |
| 📊 기록 | 전체·분류별 정답률, 최근 퀴즈 기록 |

## 문제·개념 직접 추가하기
- 개념 카드: `content/concepts.json`
- 퀴즈 문제: `content/questions.json`

문제 하나의 모양:
```json
{
  "id": "b09",
  "category": "basic",
  "level": 1,
  "concept": "market_cap",
  "question": "질문 내용",
  "choices": ["보기1", "보기2", "보기3", "보기4"],
  "answer": 2,
  "explanation": "해설"
}
```
- `id`: 겹치지 않는 이름
- `category`: basic(기초 용어) / chart(캔들·차트) / indicator(기술적 지표) / valuation(가치평가) / risk(리스크 관리) / market(시장 제도)
- `level`: 1 기초 / 2 중급 / 3 심화
- `concept`: 연결할 개념 카드의 id
- `answer`: 정답 보기 번호 (**1부터** 셉니다)
- 보기는 퀴즈 때마다 순서가 섞입니다.

파일을 고친 뒤 테스트(`pytest`)를 돌리면 형식 오류(쉼표 빠짐, 정답 번호 잘못 등)를 찾아 줍니다. 앱 화면에서도 몇 번째 줄이 틀렸는지 알려 줍니다.

## 학습 기록
- `progress.json`에 저장됩니다 (내 컴퓨터에만, git에 올라가지 않음).
- 처음부터 다시 하고 싶으면 이 파일을 지우면 됩니다.

## 폴더 구조
```
app.py            화면
config.py         기준값·설정 (문제 수, 오답 노트 졸업 횟수, 정답률 색 기준 등)
content/          개념 카드·문제 은행 (JSON)
quiz/bank.py      파일 불러오기·형식 검사
quiz/engine.py    출제(보기 섞기)·채점
quiz/progress.py  학습 기록·오답 노트
tests/            pytest 테스트
```
