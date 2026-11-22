# 휴대폰에서 쓰기 (Streamlit Cloud 배포)

스윙 대시보드와 같은 방법입니다. 한 번만 해 두면 PC를 꺼도 휴대폰에서 열 수 있습니다.

## 1. GitHub에 코드 저장소 만들기 (직접)
1. https://github.com/new 접속
2. Repository name: `stock-study`
3. **Public** 선택 (Streamlit 무료 계정은 비공개 앱이 1개뿐이고, 그 자리는 스윙 대시보드가 사용 중)
   - 코드에는 비밀값이 없습니다. 토큰·비밀번호는 Streamlit Secrets에, 학습 기록은 비공개 swing-data 저장소에 있습니다.
4. README·.gitignore·license는 **체크하지 않기** (빈 저장소여야 함)
5. **Create repository**

## 2. 코드 올리기
저장소를 만들었다고 알려 주시면 Claude가 올립니다. 직접 하려면:

```powershell
cd C:\stock_study
```

```powershell
git remote add origin https://github.com/fdv2-commits/stock-study.git
```

```powershell
git push -u origin main
```

## 3. Streamlit Cloud에 앱 만들기 (직접)
1. https://share.streamlit.io 접속 → 오른쪽 위 **Create app**
2. **Deploy a public app from GitHub** (또는 비슷한 이름) 선택
   - 'You can only have one private app' 오류가 나오면 저장소가 아직 비공개인 것 → GitHub 저장소 Settings에서 Public으로 변경
3. Repository: `fdv2-commits/stock-study` / Branch: `main` / Main file path: `app.py`
   - 저장소가 목록에 안 보이면: GitHub 권한 화면에서 Streamlit이 이 저장소를 볼 수 있게 허용
4. **Advanced settings**
   - Python version: 3.14 (없으면 가장 높은 버전)
   - Secrets: 아래 내용을 붙여 넣고 값 채우기

```toml
GITHUB_DATA_TOKEN = "스윙 대시보드 Secrets에 있는 값 그대로"
GITHUB_DATA_REPO = "fdv2-commits/swing-data"
APP_PASSWORD = "내가 정한 비밀번호"
```

   - `GITHUB_DATA_TOKEN` 값은 Streamlit Cloud에서 스윙 대시보드 앱 → ⋮ → Settings → Secrets 에서 복사하면 됩니다.
5. **Deploy** → 1~3분 기다리면 앱 주소가 생깁니다.

## 4. 공개/비공개
- 이 앱은 공개(public) 앱이라 주소를 아는 사람은 누구나 들어올 수 있습니다. 그래서 **APP_PASSWORD는 꼭 넣어 주세요.**
  비밀번호를 맞혀야 화면이 열리고, 학습 기록도 보거나 바꿀 수 없습니다.

## 5. 휴대폰
- 앱 주소를 휴대폰 브라우저로 열고 → 공유(또는 ⋮) → **홈 화면에 추가** 하면 앱처럼 쓸 수 있습니다.

## 학습 기록은 어떻게 보관되나요?
- `swing-data` 저장소 안 `stock_study/progress.json` 에 저장됩니다. (스윙 대시보드 파일과 섞이지 않음)
- 앱을 열 때 내려받고, 퀴즈를 끝내거나 그만둘 때, 그리고 5문제마다 올립니다. (`config.py`의 `REMOTE_PUSH_EVERY`)
- 올릴 때마다 저장소에 `[주식공부] ...` 커밋이 하나씩 생깁니다 = 자동 백업 기록.
- 보관이 실패하면 화면 위에 노란 안내가 나오고, 앱은 그대로 쓸 수 있습니다.
- PC에서 실행할 때는 이 기능이 꺼져 있고 `C:\stock_study\progress.json`만 씁니다.
  (PC 기록과 휴대폰 기록은 따로입니다)

## 코드를 고친 뒤
- 코드는 `git push` 해야 휴대폰 앱에 반영됩니다. (Streamlit Cloud가 자동으로 다시 배포)
