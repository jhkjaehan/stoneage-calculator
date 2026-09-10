# 스톤에이지 환각 계산기 — 프로젝트 메모

새 세션에서 이 폴더로 들어오면 이 문서를 먼저 읽고 시작할 것. 아래 내용은
전부 실제 대화를 통해 검증/확정된 사실이며, 다시 처음부터 재검증할 필요 없음.

## 이게 뭔가

ohrsa.net(스톤에이지 사설서버, `/petinfo` 게시판)에 표기되는 펫의 **초기치·성장률**
(눈에 보이는 값)만으로, 그 펫의 **숨겨진 등급(-8~+8등급)**을 178,750가지 경우의 수
전수조사로 역산하는 웹 계산기. 정적 HTML 한 장(`index.html`)으로 동작하고
Cloudflare Pages(Workers 아님!)에 배포되어 있음.

## 확정된 계산 모델 (전부 사용자가 직접 확인/정정한 사실)

- **표기값은 반올림이 아니라 "내림"(floor)** — 서버 쪽에서 공식 확인된 사항.
- **초기치 계산의 보너스분배(D)는 2.5로 고정**(균등분배 가정) — 단, 이건 "S급
  참고 초기치"(species 기준값)를 구할 때 쓰는 이론치 계산법이고, **실제
  개체(등급표 결과)의 성장률 범위를 구할 때는 그 개체가 실제로 가진 구체적인
  D값을 그대로 재사용**해야 함(아래 "성장률 범위" 항목 참고).
- **원본계수(체/공/방/순, 정수)**: 표기 성장률만으로 RANK 1~6 전체를 대입해
  후보 원본계수를 만들고, **각 후보로 "계산 성장률"을 다시 만들어 실제 표기
  성장률과 직접 비교(잔차 최소)해서 채택**한다. "원본계수 개별 성분이 정수에서
  얼마나 벗어났는지(max 편차)"만 보는 방식은 틀릴 수 있음(베로포리 사례로
  실제 확인됨 — 편차 기준으론 RANK1이 나왔지만 실제로는 RANK2가 맞았음).
- **초기치계수(k, 정수)**: 확정한 원본계수 + D=2.5 고정으로, S급 초기치를
  내림 기준 정확히 재현하는 정수 k를 탐색. 못 찾으면 최소자승 근사치(approx).
- **등급 확률(178,750가지 전수조사, 실제 입력 스탯 대상)**: 등급오프셋
  (-2~+2, 5^4=625가지) × 개체별 실제 정수 D(10포인트분배, 286가지) 전부
  대입, **내림** 기준으로 입력 초기치와 일치하는 조합만 집계.
- **RANK별 보정계수(B) 범위**: 1:450~500(원본계수합≥100), 2:470~520(95~99),
  3:490~540(90~94), 4:510~560(85~89), 5:530~580(80~84), 6:550~600(<80).
  B는 레벨업마다 이 범위 안에서 새로 랜덤 결정됨(고정값 아님).
- **보너스공식**(체/공/방/순 순서 고정):
  ```
  표기체력 = 체×4 + 공 + 방 + 순
  표기공격 = 체×0.1 + 공 + 방×0.1 + 순×0.05
  표기방어 = 체×0.1 + 공×0.1 + 방 + 순×0.05
  표기순발 = 순
  ```
- **성장률의 진짜 랜덤 요소는 B 하나뿐**: 등급오프셋과 보너스분배(D)는 이미
  일치 건마다 확정된 값이고, 레벨업마다 다시 랜덤하게 정해지는 건 RANK
  보정계수(B)뿐. B는 계산식에 선형이라 범위 양끝(Blo/Bhi)만 보면 최소/최대를
  다 잡을 수 있음(중간값 검사 불필요).

## 파일 구조

```
template.html         SPA 원본 소스 — 항상 여기를 수정. index.html은 빌드 산출물(직접 수정 금지)
scripts/common.py     핵심 계산 로직 (calibrate_pet, compute_grade_dist) — 파이썬 참조 구현
scripts/scrape.py     ohrsa.net 로그인+스크래핑. OHRSA_ID/OHRSA_PW 환경변수 필요(코드에 절대 하드코딩 금지)
scripts/sync.py       신펫 자동감지+계산+이미지압축. 사이트에 없는 수동등록 펫은 안 지워짐(live_ids 밖은 뒤에 유지)
scripts/rank_compare.py  RANK 1~6 전체 비교 데이터 생성 (현재 UI에서 숨겨진 비교탭용 데이터)
scripts/build.py      rank_compare.build() 호출 후 template.html + data/pets.json → index.html 생성
data/pets.json         전체 펫 데이터(원본계수/k/초기치/성장률/이미지 base64/attrs 등)
data/overrides.json    사이트 원본 오타 수동 보정(예: 만모 순발력 22→2)
data/rank_compare.json build.py가 매번 재생성(직접 수정 금지)
.github/workflows/sync.yml  매주 월요일 자동 실행 + Actions 탭에서 수동 실행 가능.
                       **runs-on: self-hosted (확정)** — ohrsa.net이 GitHub 호스팅
                       러너(Azure 데이터센터 IP)를 Cloudflare/WAF로 막아서 /petinfo가
                       403 남. User-Agent를 일반 브라우저로 바꿔서 ubuntu-latest로
                       재테스트까지 해봤지만 **여전히 403** — UA 문제가 아니라 IP
                       평판/대역 차단으로 확정. 그래서 사용자 WSL 머신을
                       self-hosted 러너로 등록해서 씀(`~/actions-runner`,
                       `sudo ./svc.sh start`로 서비스 등록됨). **사용자 WSL이
                       켜져 있고 러너 서비스가 돌고 있어야만** 워크플로가 실행됨
                       (꺼져있으면 큐에 걸린 채 대기). 이 머신엔 pip가 원래 없어서
                       `sudo apt install -y python3-pip` 필요했음. 앞으로 "로컬 없이
                       자동화"를 다시 시도한다면 유료 프록시 서비스(주거용 IP로
                       릴레이) 또는 Azure 아닌 다른 CI 제공자 시도가 후보이지만
                       둘 다 검증 안 됨 — 사용자가 원할 때 다시 논의할 것.
wrangler.toml          Cloudflare **Pages** 배포용 (한때 Workers로 잘못 잡혔던 걸 Pages로 재설정 완료)
```

## 작업 방식 (반드시 지킬 것)

1. `template.html`이나 `scripts/*.py`, `data/*.json`을 고친 뒤 **항상**
   `python3 scripts/build.py`로 `index.html`을 재생성한다.
2. JS를 고쳤으면 문법체크: template.html에서 `<script>...</script>` 안쪽
   IIFE를 정규식으로 뽑아 `node --check`로 확인 (이 세션들에서 계속 써온
   패턴, 스크래치패드에 스크립트 예시 있음— 매번 새로 만들어도 됨).
3. 가능하면 최소한의 DOM 스텁(FakeEl/getElementById 정도)으로 `selectPet`,
   `runCalc` 등을 실제 호출해서 예외 없이 도는지 확인하고 커밋한다 (헤드리스
   브라우저 없음, 스크린샷 불가능한 환경).
4. 커밋만 하고 **push는 하지 않는다** — 이 환경엔 GitHub 인증정보가 없어서
   push는 항상 사용자가 직접 한다(사용자 쪽 `credential.helper store` 설정
   되어 있어서 보통 바로 됨). 커밋 후 "git push 해주시면 반영됩니다"라고
   안내할 것.
5. Claude 아티팩트(claude.ai/code/artifact/...)는 **더 이상 쓰지 않음** —
   Cloudflare Pages가 유일한 실배포처. 아티팩트 관련 작업 요청받지 않는 한
   건드리지 말 것.

## 신규(수동) 펫 등록 방법

ohrsa.net petinfo에 아직 없는 펫을 사용자가 gif+수치로 직접 줄 때:
1. id는 `m1`, `m2`... 형식으로 부여(사이트 wr-id 숫자와 안 겹치게).
2. `common.calibrate_pet(growth_S, init_S)`로 origin/k/ok/approx 계산
   (growth_S, init_S 둘 다 [체,공,방,순] 순서). 이어서
   `common.calibrate_pet(growth_S, init_S, ranks=common.RANKS_EXT)`로 세분화
   가설 결과도 계산해서 `originAlt`/`kAlt`/`approxAlt`로 담고,
   `common.confidence_score(...)`로 `confMain`/`confAlt`도 채운다(아래
   "기존/세분화 계산방식 탭" 항목 참고 — `sync.py`는 이미 이 과정을 자동으로
   함, 수동 등록 때만 사람이 직접 해줘야 함).
3. gif는 PIL로 96×96 WebP(quality=85) 변환 후 base64 인코딩.
4. `data/pets.json`에 append. `attr`/`attrs`/`obtain`은 정보 없으면 빈 값(`""`,
   `[]`) + `"직접 등록"` 정도로 채운다.
5. 정보가 불확실한 펫은 억지로 계산하지 말고 `growthS`/`initS`를 `[0,0,0,0]`,
   `ok:false`로 비워서 "계산 미지원"으로 표시한다(꼬비가 이 케이스).

## 현재 데이터 상태 (2026-09-10 기준)

- 전체 143마리 (ohrsa.net 스크레이핑 136 + 수동등록 7: 꼬미/꼬비/꼬꼬비/꼬비오/만모로스/보르비스/도라비스)
- 근사치(approx) 펫: 없음 (전부 정밀 매칭 — "기존 방식" 기준. "세분화 방식"으론
  일부 근사치 있음, 아래 항목 참고)
- 미지원(ok=false): **꼬비** — 능력치 정보를 아직 확인 못해서 비워둔 상태.
  나중에 실제 초기치/성장률 받으면 `common.calibrate_pet`으로 채울 것.

## 기존/세분화 계산방식 탭 + 신뢰도 % (2026-09-10 추가)

우리는 ohrsa.net 서버 소스코드를 직접 확인할 방법이 없다. 지금 쓰는 RANK표
(`common.RANKS`, 원본계수합≥100은 전부 RANK1으로 뭉뚱그림)는 143마리 데이터로
뒷받침되긴 했지만 "정말 그 이상 세분화가 안 되어 있는지"는 증명된 적 없는
가정이다. 다른(독립 튜닝된) 사설서버 milk-sa.pages.dev를 역공학했을 때, 그
서버는 원본계수합 100 미만 구간은 우리와 완전히 동일하면서 100 이상만
100~104/105~109/110+ 세 단계로 더 세분화되어 있었다(`common.RANKS_EXT`로
그 구조를 그대로 이식해둠 — 실제 milk-sa 튜닝값이 아니라 "구조를 참고한
가설"이라는 점 유의, 절대 milk-sa 전용 수치를 우리 서버 사실로 취급하지 말 것).

- **`common.calibrate_pet(growth_S, init_S, ranks=...)`**: ranks 생략시 기존
  RANKS, `RANKS_EXT` 넘기면 세분화 가설로 계산.
- **`common.confidence_score(calib)`**: (2026-09-10, 3차 재설계, method
  인자 없음) **오직 growth_resid(성장률 재현 오차) 하나만** 근거로 삼는다 —
  `round(min(CONFIDENCE_HARD_CAP, 100/(1+growth_resid/GROWTH_RESID_SCALE)), 2)`,
  `GROWTH_RESID_SCALE=5e-5`, `CONFIDENCE_HARD_CAP=99.99`. fit_resid(초기치
  재현 오차)·approx 여부는 **신뢰도 %에서 완전히 뺐다** — approx는 UI에서
  별도 경고 칩("⚠ 근사치")으로만 표시.
  - **변천사**: 1차는 main/ext 임의 구조가중치(0.85/0.45) → 사용자가 "근거
    있는 수치냐"고 문제 제기해서 폐기. 2차는 growth_resid×fit_resid 조합 →
    사용자가 "fit_resid 섞지 말고 성장률 오차만 기준으로 삼아라, 변별력이
    없어도 상관없다 — 대부분 99%대가 정상이고 오차 가장 작은 펫 기준으로
    스케일을 잡으면 된다"고 명확히 정정해서 지금 형태로 재설계함.
  - 실측(142마리, RANKS 기준): growth_resid는 "정상" 펫 중 가장 나쁜 값도
    5.77e-7인데 베로포리만 3.91e-4로 **정상 최대치의 677배**에 달하는
    압도적 이상치다(과거 RANK 오판 사례였던 그 펫). 이 극단적인 gap 덕분에
    스케일 하나로 "정상 펫은 전부 99%대, 베로포리만 확 떨어짐"이 자연스럽게
    나옴 — 실제로 142마리 중 135마리 99%+, 141마리 95%+, 베로포리만 11.34%.
  - RANKS_EXT(ext, 두 표가 갈리는 21마리 대상)는 이 기준으로 더 뚜렷하게
    갈린다: main 98.04~99.99% vs ext 0.78~13.30% — "구간을 더 쪼개서 생긴
    착시"가 아니라 우리 서버의 실제 성장률 데이터가 main 구조를 직접
    지지한다는 뜻(ext가 후보 구간을 3개(main은 1개) 갖고 있어 유리해 보일
    수 있는데도 여전히 못 맞춘다).
  - 사용자가 제기한 반론("RANK 범위는 보통 서버 튜닝 안 하니 우리 서버도
    milk-sa처럼 세분화되어 있을 수 있다")에 대한 직접 답이기도 함: 만약
    그렇다면 우리 서버 실제 데이터가 그 세분화(같은 경계값 100/105/110,
    같은 B값 435/455/475)에 최소한 기존 방식만큼은 잘 맞아야 하는데 — 위
    검증대로 전부 더 나쁘게 나옴. "RANK 범위가 서버마다 안 바뀐다"는 전제
    자체는 합리적일 수 있어도, milk-sa에서 나온 그 **구체적인 숫자**가
    ohrsa.net에 그대로 적용된다는 가설은 우리 데이터가 직접 반박.
- `data/pets.json`의 각 펫에 `originAlt`/`kAlt`/`approxAlt`/`confMain`/`confAlt`
  필드로 저장되어 있다(원본계수합<105인 펫은 두 방식이 사실상 같아서
  `originAlt===origin`). `sync.py`가 신펫마다 자동 계산해서 채운다.
- **UI**: `template.html`에서 두 방식 결과가 실제로 다른 펫(`hasAltMethod(p)`)
  에 한해서만 등급 감정 결과 위에 "① 기존 방식 / ② 세분화 방식(타서버 참고)"
  탭이 뜬다(`calcMethod` 상태, `bindMethodTabs()`, 상시 노출 — 실제 조작
  가능한 컨트롤이라 접지 않음). 신뢰도·방식설명·이상치경고는 전부
  `<details class="info-details">`(`renderResults`의 `infoHtml`) 안에
  통합되어 있어서, 평소엔 "신뢰도 XX% · ⚠ 근사치 · ⚠ 원본계수 이상치 ·
  ⓘ 근거 보기" 한 줄 요약(`.info-summary`)만 보이고 클릭해야 전체 설명
  문단(`.info-details-body`)이 펼쳐진다(2026-09-10, 예전엔 각각 별도
  문단으로 항상 펼쳐져 있어서 화면을 많이 차지한다는 지적을 받고 네이티브
  `<details>`로 통합함 — 새로 설명 문구를 추가할 땐 반드시 이 안에 넣을 것,
  밖에 별도 상시노출 문단을 또 만들지 말 것).
- **원본계수 반올림 오차(origin_dev) 이상치 경고** (2026-09-10 추가):
  `common.ORIGIN_DEV_OUTLIER_THRESHOLD=0.05`, `is_origin_dev_outlier()`.
  142마리 중 141마리는 origin_dev≤0.011인데 베로포리만 0.399로 압도적 이상치
  (과거 RANK 오판 사례였던 그 펫 — growth_resid 기반 신뢰도가 이 신호를
  일부 반영은 하지만 다른 요인과 섞여 원인이 묻히길래 별도로 뺐다). 세분화
  방식(alt)에서는 두 표가 갈리는 21마리 전부 devFlagAlt=true로 나옴 — 신뢰도
  재설계 때 확인한 "ext가 main보다 못 맞는다" 결론을 한 번 더 뒷받침하는
  독립적 신호. `data/pets.json`엔 `originDevMain`/`originDevAlt`/
  `devFlagMain`/`devFlagAlt`로 저장, UI엔 신뢰도 배지 바로 아래
  `.dev-outlier-note`로 표시(`renderResults`의 devFlag/devVal 참고).
- 현재(143마리 기준) 원본계수합≥105인 21마리만 두 방식이 갈리고, 그중 15마리는
  세분화 방식에서 근사치로 전락. 신뢰도 숫자 자체(스케일 상수 0.002/1.32,
  근사치 감점 0.7, 하드캡 97)는 여전히 휴리스틱이라 사용자가 원하면 언제든
  조정할 것 — `common.py`의 `GROWTH_RESID_SCALE`/`FIT_RESID_SCALE`/
  `APPROX_PENALTY`/`CONFIDENCE_HARD_CAP`와 `confidence_score()` 참고.
- **수동등록 펫(id "m1"~) 자동 승격**: `sync.py`가 매번, 사이트에 새로 뜬
  펫 이름이 기존 수동등록 펫과 같으면 수동 항목을 지우고 정식 사이트
  데이터로 자동 교체한다(요약의 `replaced_manual`에 기록되고 동기화 이슈에도
  같이 알림). 즉 꼬미류가 ohrsa.net에 정식으로 올라오면 사람이 손 안 대도
  자동으로 갱신됨.
- **동기화 이슈 = 히스토리**: `has_new`(뭐라도 바뀌면)일 때마다 GitHub 이슈를
  새로 올려서 날짜별 변경 기록을 남긴다(신규추가 목록+상태, 검수필요,
  기존값변경, 수동펫 정식전환, 속성갱신 마리수 전부 포함). 예전엔 "검수
  필요"할 때만 이슈가 올라와서 깔끔한 신펫 추가는 기록이 안 남았었는데,
  지금은 뭐든 바뀌면 이슈로 남게 고쳐둠 — Actions 탭이 아니라 Issues 탭에서
  변경 히스토리를 확인하면 됨.
- `analysis/rank_candidates.{json,md}`는 예전 스냅샷이라 최신 계산 로직과
  안 맞을 수 있음 — 참고만 하고, 필요하면 재생성할 것(생성 스크립트는 세션
  history에만 있고 저장 안 해뒀음, 필요시 common.calibrate_pet 순회하는
  스크립트를 새로 짜면 됨).

## UI에서 숨겨진(코드는 살아있는) 기능들

- **"성장률·초기치 비교" 탭**: `template.html`의 `.tab-btn[data-tab="compare"]`에
  `hidden` 속성 — 지워지면 재활성화됨.
- **"📈 성장률 범위" 버튼**(등급 감정 결과 헤더 옆, 모달 팝업): `#growthRangeBtn`에
  `hidden` 속성. 계산 로직(`computeGrowthRange`, `growthForOffsetDB` 등)은
  정상 동작 확인됐고, 사용자가 마지막으로 "수치가 이상하다"며 껐음 — 재검토
  필요하면 여기부터 다시 볼 것. 마지막 확정 로직: 등급표의 각 일치 건이
  가진 실제 D를 그대로 쓰고, B만 그 RANK 범위 양끝값으로 대입해서 최소/최대.

## 로그인 계정

ohrsa.net 로그인은 `OHRSA_ID`/`OHRSA_PW` 환경변수로 전달 (그누보드5,
`/bbs/login_check.php`에 `mb_id`/`mb_password`/`url` POST). GitHub Actions
Secrets에도 동일하게 등록되어 있음. **절대 코드나 커밋에 평문으로 남기지 말 것**
(지금까지 한 번도 안 남겼음, 계속 유지).
