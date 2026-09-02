# 스톤에이지 환각 계산기

ohrsa.net/petinfo 의 표기 스탯(성장률·초기치)만으로, 178,750가지 경우의 수를 대조해
펫의 숨겨진 등급(-8 ~ +8) 확률을 계산합니다. 신펫이 올라오면 매주 자동으로 감지해서
계산을 추가하고 배포까지 스스로 갱신합니다.

## 구조

```
template.html          앱 껍데기 (검색/스탯입력/등급표) + __PET_DATA__ 자리표시자
data/pets.json          펫별 계산 결과 DB (원본계수 · k · 등급판정 근거)
data/overrides.json     사이트 원본 데이터가 틀린 경우의 수동 보정값
scripts/common.py       원본계수 역산 핵심 로직 (RANK 6구간 대입 + 178,750 전수조사)
scripts/scrape.py       ohrsa.net 로그인 + 펫 목록 파싱
scripts/sync.py         신펫 감지 -> 계산 -> 이미지 압축 -> data/pets.json 갱신
scripts/build.py        data/pets.json + template.html -> index.html
.github/workflows/sync.yml   매주 월요일 자동 실행 (수동 실행도 가능)
```

`index.html`은 완전히 독립된 정적 파일입니다 (백엔드 없음, 외부 호출은 구글 폰트뿐).
`scripts/sync.py`가 실행될 때마다 `data/pets.json`을 갱신하고 `index.html`을 새로
만들어 커밋합니다.

## 처음 설정하는 법

### 1. 이 폴더를 GitHub 저장소로 올리기

```bash
cd stoneage-calculator
git init
git add .
git commit -m "init: 스톤에이지 환각 계산기"
git branch -M main
git remote add origin https://github.com/<your-id>/<repo-name>.git
git push -u origin main
```

### 2. 로그인 계정을 GitHub Secrets로 등록

저장소 **Settings → Secrets and variables → Actions → New repository secret** 에서:

- `OHRSA_ID` — ohrsa.net 로그인 아이디
- `OHRSA_PW` — ohrsa.net 로그인 비밀번호

(비밀번호를 코드나 커밋에 절대 직접 넣지 마세요. 이 값은 Actions 로그에도 출력되지
않도록 스크립트가 짜여 있습니다.)

### 3. Actions에 쓰기 권한 주기

**Settings → Actions → General → Workflow permissions**에서
"Read and write permissions"를 선택하세요. (자동으로 커밋·이슈 등록을 하려면 필요합니다.)

### 4. Cloudflare Pages 연결

1. [pages.cloudflare.com](https://pages.cloudflare.com) → "Connect to Git" → 방금 만든 저장소 선택
2. Build 설정: **Framework preset: None**, **Build command: (비워둠)**, **Build output directory: `/`**
3. 배포 완료 후 `프로젝트명.pages.dev` 주소로 접속 가능

이후로는 `main` 브랜치에 새 커밋이 올라올 때마다(=신펫이 자동 반영될 때마다)
Cloudflare Pages가 알아서 재배포합니다.

## 동작 방식 / 정책

- 매주 월요일 00:00 UTC에 자동 실행됩니다. **Actions 탭 → 신펫 자동 동기화 → Run workflow**로
  수동 실행도 가능합니다 (신펫이 떴는지 바로 확인하고 싶을 때).
- 새 펫을 찾으면: 성장률을 RANK 1~6에 전부 대입해 원본계수가 정수로 떨어지는 지점을
  찾고, 그 원본계수에 보너스포인트를 2.5로 고정(균등분배)했을 때 S급 초기치를
  **내림**(반올림 아님, 서버 확인 사항) 기준으로 정확히 재현하는 정수 초기치계수가
  있으면 **정밀(ok)**로 즉시 반영합니다.
- 정확히 안 맞으면 6개 RANK 전체에서 D=2.5 고정 최소자승 최적해를 **근사치(approx)**로
  반영하고, GitHub 이슈를 열어 알려줍니다 — 계산기에는 바로 뜨되 "근사" 배지가 붙습니다.
- 등급 확률을 구하는 178,750가지 전수조사(개체별 실제 10포인트 분배)도 동일하게
  **내림** 기준으로 매칭합니다.
- 기존에 있던 펫의 수치가 사이트에서 바뀐 게 감지되면(오타 정정 등), 자동으로
  덮어쓰지 않고 이슈로만 알립니다. 확인 후 맞으면 `data/overrides.json`에 보정값을
  넣거나, `data/pets.json`에서 해당 항목을 지우고 다시 실행하면 재계산됩니다.
- `data/overrides.json`은 사이트 원본 표기 오류를 수동으로 바로잡는 곳입니다
  (예: 만모 순발력 22 → 2 오타 수정 사례가 이미 들어있습니다).

## 로컬에서 수동 실행

```bash
pip install -r requirements.txt
OHRSA_ID=xxx OHRSA_PW=xxx python scripts/sync.py
```
