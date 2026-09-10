"""
스톤에이지 환각 계산기 - 원본계수 역산 공통 라이브러리

klaking.tistory.com/3 분석 공식 + 서버 확인 사항을 반영한다:
  - 성장률: 등급오프셋(+2, S급) + 보너스포인트 평균 2.5 로 계산된 이론값
  - 초기치: 등급오프셋(+2, S급) + 보너스포인트 "2.5 고정"(균등분배)으로 계산된 이론값
  - 표기값은 반올림이 아니라 "내림"(floor) 처리된다 (서버 확인)

원본계수(체/공/방/순)는 성장률만으로 RANK 1~6 전 구간을 대입해 역산한다 — 각
후보 원본계수로 "계산 성장률"을 다시 만들어 실제 표기 성장률과 직접 비교했을 때
잔차가 가장 작은 RANK를 채택한다(원본계수 자체가 정수에서 얼마나 벗어났는지만
보면, 개별 원본계수의 반올림 오차가 보너스공식 가중치를 거치며 서로 상쇄/증폭될
수 있어 오판할 수 있다). 초기치계수(k)는 그 원본계수 + D=2.5 고정 + 내림 조건을
만족하는 정수를 찾는다.

실제 개체의 등급 확률을 구할 때는(178,750가지 전수조사) 개별 펫의 진짜 10포인트
분배는 정수 랜덤값이므로 D를 고정하지 않고 전부 탐색하되, 표기값 매칭은 동일하게
"내림" 기준으로 판정한다.
"""
from itertools import product

# 보너스 스탯 공식 (체/공/방/순 순서)
#   표기체력 = 체*4 + 공 + 방 + 순
#   표기공격 = 체*0.1 + 공 + 방*0.1 + 순*0.05
#   표기방어 = 체*0.1 + 공*0.1 + 방 + 순*0.05
#   표기순발 = 순
M = [
    [4.0, 1.0, 1.0, 1.0],
    [0.1, 1.0, 0.1, 0.05],
    [0.1, 0.1, 1.0, 0.05],
    [0.0, 0.0, 0.0, 1.0],
]

# RANK: (원본계수합 하한, 상한, 보정계수 하한, 상한, 보정계수 중앙값)
RANKS = {
    1: (100, None, 450, 500, 475),
    2: (95, 99, 470, 520, 495),
    3: (90, 94, 490, 540, 515),
    4: (85, 89, 510, 560, 535),
    5: (80, 84, 530, 580, 555),
    6: (None, 80, 550, 600, 575),
}

# "세분화" RANK 테이블 (가설) — 우리는 ohrsa.net 서버 소스코드를 직접 확인할
# 방법이 없어서, 원본계수합 100 이상 구간을 RANKS처럼 하나로 뭉뚱그려도 되는지
# 아니면 더 잘게 나뉘어 있는지 알 수 없다. 다른(독립적으로 튜닝된) 사설서버인
# milk-sa.pages.dev를 역공학해서 나온 RANK 표가 100 미만 구간은 RANKS와 완전히
# 동일하면서 100 이상만 3단계로 더 세분화된 구조였기에, 그 패턴을 그대로 가져와
# "만약 ohrsa.net도 이렇게 세분화되어 있다면"을 계산해보는 참고용 대안이다.
# **검증된 사실이 아니라 가설** — RANKS(기존)보다 구조적 신뢰도를 낮게 잡는다
# (CONFIDENCE_STRUCT_WEIGHT 참고).
RANKS_EXT = {
    0: (110, None, 410, 460, 435),
    1: (105, 109, 430, 480, 455),
    2: (100, 104, 450, 500, 475),
    3: (95, 99, 470, 520, 495),
    4: (90, 94, 490, 540, 515),
    5: (85, 89, 510, 560, 535),
    6: (80, 84, 530, 580, 555),
    7: (None, 80, 550, 600, 575),
}

# 신뢰도(%) 계산: 오직 "성장률 재현 오차"(growth_resid) 하나만 근거로 쓴다
# (2026-09-10 3차 재설계 — 1차는 main/ext 임의 구조가중치, 2차는
# growth_resid×fit_resid 조합이었는데, 사용자가 "fit_resid 섞지 말고 성장률
# 오차만 기준으로 삼아라, 변별력이 없어도 상관없다 — 대부분 99%대여야
# 정상이고, 제일 오차 작은 펫 기준으로 스케일을 잡으면 된다"고 명확히
# 정정해서 재설계함).
#
# 실측(142마리, RANKS 기준): growth_resid는 거의 전부 0에 가깝고(최소 0,
# "정상" 펫 중 가장 나쁜 값도 5.77e-7), 베로포리 딱 하나만 3.91e-4로
# 정상 최대치의 677배에 달하는 압도적 이상치다(과거 RANK 오판 사례였던 그
# 펫). 이 극단적인 gap 덕분에 스케일 하나만 잘 잡으면 "정상 펫은 전부
# 99%대, 베로포리만 확 떨어짐"이 자연스럽게 나온다 — 아래 SCALE은 "정상 펫
# 중 가장 오차가 큰 값"(≈5.8e-7)이 그래도 99% 근처에 나오도록 여유를 두고
# 잡은 값이다.
GROWTH_RESID_SCALE = 5e-5   # 이 값 근처 오차까지는 신뢰도가 크게 안 깎이도록 하는 기준선
CONFIDENCE_HARD_CAP = 99.99  # 서버 소스코드를 직접 볼 수 없으므로 계산상 100이 나와도 여기서 막는다

# origin_dev(원본계수를 정수로 반올림하기 전 실수값이 정수에서 벗어난 정도,
# 4개 성분 중 최댓값) 이상치 판정 기준. 142마리 중 141마리는 0.011 이하인데
# 베로포리 하나만 0.399로 압도적으로 튀었다(과거 RANK 오판 사례였던 바로 그
# 펫) — confidence_score의 growth_factor가 이 신호를 이미 반영은 하지만
# (베로포리만 growth_factor<1), 신뢰도 %는 fit_resid 등 다른 요인과 섞여서
# "이 펫은 원본계수 자체가 유독 불확실하다"는 원인이 묻힐 수 있어 별도로
# 노출한다. 0.05는 관측된 정상 범위(≤0.011)의 5배 이상 여유를 둔 값.
ORIGIN_DEV_OUTLIER_THRESHOLD = 0.05


def is_origin_dev_outlier(calib):
    """calib['origin_dev']가 정상 범위를 벗어난 이상치인지(=이 펫은 성장률만으로
    원본계수를 정수로 특정하기 유독 애매했다는 뜻) 여부."""
    return bool(calib.get("ok")) and calib.get("origin_dev", 0) > ORIGIN_DEV_OUTLIER_THRESHOLD


def confidence_score(calib):
    """calib: calibrate_pet()의 반환값(어느 ranks 표로 계산했든 동일하게 적용).
    growth_resid(성장률 재현 오차) 하나만으로 1/(1+resid/GROWTH_RESID_SCALE)
    꼴 팩터를 만들어 신뢰도(%)를 낸다. 그래서 실제로는 142마리 중 135마리가
    99% 이상, 141마리가 95% 이상으로 나온다 — 의도된 결과다(성장률로 원본
    계수를 특정하는 과정 자체는 거의 모든 펫이 똑같이 깔끔하기 때문에 변별력이
    없는 게 정상이고, 그래서 대부분 99%대로 몰린다). CONFIDENCE_HARD_CAP
    때문에 아무리 깨끗해도 100.00은 나오지 않는다. 근사치(approx) 여부나
    초기치 재현 오차(fit_resid)는 이 신뢰도 %에는 반영하지 않고, UI에서
    별도의 경고 칩("⚠ 근사치")으로만 보여준다(신뢰도 자체를 흐리지 않기
    위함)."""
    if not calib.get("ok"):
        return 0
    factor = 1 / (1 + calib.get("growth_resid", 0) / GROWTH_RESID_SCALE)
    return round(min(CONFIDENCE_HARD_CAP, 100 * factor), 2)

# 10포인트를 체/공/방/순 4개 스탯에 분배하는 모든 조합 (286가지) - 개체별 실제 랜덤값용
Ds = [d for d in product(range(11), repeat=4) if sum(d) == 10]

# 등급 오프셋: 각 스탯 -2~+2 (5^4 = 625가지, 오프셋 합 = 등급 -8~+8)
OFFSETS = [-2, -1, 0, 1, 2]

# S급 초기치/성장률 계산에 쓰는 고정 보너스포인트 평균값
BONUS_AVG = 2.5


def matvec(mat, v):
    return [sum(mat[i][j] * v[j] for j in range(4)) for i in range(4)]


def solve4(mat, b):
    """4x4 연립방정식을 가우스 소거법으로 정확히 푼다."""
    A = [row[:] + [b[i]] for i, row in enumerate(mat)]
    n = 4
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        A[col], A[piv] = A[piv], A[col]
        pv = A[col][col]
        A[col] = [x / pv for x in A[col]]
        for r in range(n):
            if r != col:
                f = A[r][col]
                A[r] = [A[r][j] - f * A[col][j] for j in range(n + 1)]
    return [A[i][4] for i in range(4)]


def floor_list(v):
    import math
    return [math.floor(x) for x in v]


def best_k_fixed_D(origin, init_S, kmax=300):
    """원본계수가 주어졌을 때, 보너스포인트를 2.5로 고정하고(균등분배),
    init_S를 정확히(내림 기준) 재현하는 정수 k 중 잔차가 가장 작은 것을 찾는다."""
    G = [origin[i] + 2 for i in range(4)]
    vec = [G[i] + BONUS_AVG for i in range(4)]
    unscaled = matvec(M, vec)  # k=100 기준 표기값

    best = None
    for k in range(1, kmax + 1):
        disp = [k / 100 * u for u in unscaled]
        if floor_list(disp) == init_S:
            resid = sum((disp[i] - init_S[i]) ** 2 for i in range(4))
            if best is None or resid < best[0]:
                best = (resid, k, disp)
    return best


def best_approx_k_fixed_D(origin, init_S):
    """정확히 내림 일치하는 정수 k가 없을 때, 최소자승으로 가장 근접한 k를
    근사치로 찾는다 (D=2.5 고정)."""
    G = [origin[i] + 2 for i in range(4)]
    vec = [G[i] + BONUS_AVG for i in range(4)]
    unscaled = matvec(M, vec)
    den = sum(u * u for u in unscaled)
    if den == 0:
        return None
    s = sum(unscaled[i] * init_S[i] for i in range(4)) / den
    k = round(s * 100)
    if k < 1:
        return None
    disp = [k / 100 * u for u in unscaled]
    resid = sum((disp[i] - init_S[i]) ** 2 for i in range(4))
    return (resid, k, disp)


def calibrate_pet(growth_S, init_S, ranks=None):
    """growth_S, init_S (둘 다 [체,공,방,순] 순서) 로부터
    {'rank','origin','k','ok','approx','fit_resid','growth_resid'} 를 계산한다.
    ranks를 생략하면 RANKS(기존, 서버 데이터로 검증된 표)를 쓴다. RANKS_EXT를
    넘기면 "세분화 가설" 표로 계산한다 — 결과 dict의 'rank' 키는 그 표의 키를
    그대로 반영하므로, 어느 표를 썼는지에 따라 의미가 달라짐에 유의.

    1) 성장률 4개 방정식을 풀어 raw growth(before-bonus) r을 구한다.
    2) RANK 1~6 각각의 보정계수 중앙값으로 원본계수(정수)를 역산한다 (자기
       RANK 구간에 부합하는 것만 후보로 삼는다).
    3) 각 후보 원본계수로 "계산 성장률"(보너스공식까지 통과시킨 값)을 만들어
       실제 표기 성장률과 직접 비교한 잔차가 가장 작은 RANK를 채택한다.
       (원본계수 자체가 정수에서 얼마나 벗어났는지를 보는 것보다, 보너스공식을
       거친 뒤의 실제 재현 오차를 직접 비교하는 게 더 정확한 지표다 — 원본계수
       하나의 반올림 오차가 보너스공식의 가중치를 거치며 서로 상쇄/증폭될 수
       있기 때문에, 개별 원본계수 편차만 보면 오판할 수 있다.)
    4) 그 원본계수 + D=2.5 고정으로 초기치를 정확히(내림 기준) 재현하는
       정수 k를 찾는다. 정확히 맞는 게 없으면 최소자승 근사 k를 쓰고
       'approx'로 표시한다.
    """
    ranks = RANKS if ranks is None else ranks
    r = solve4(M, growth_S)

    candidates = []
    for rank, (lo, hi, Blo, Bhi, Bmid) in ranks.items():
        origin_real = [r[i] * 10000 / Bmid - 4.5 for i in range(4)]
        origin_int = [round(x) for x in origin_real]
        dev = max(abs(origin_real[i] - origin_int[i]) for i in range(4))
        s = sum(origin_int)
        ok_bracket = (lo is None or s >= lo) and (hi is None or s <= hi)
        if not ok_bracket:
            continue

        G = [origin_int[i] + 2 for i in range(4)]
        growth_raw = [(G[i] + BONUS_AVG) * Bmid / 10000 for i in range(4)]
        growth_calc = matvec(M, growth_raw)
        growth_resid = sum((growth_calc[i] - growth_S[i]) ** 2 for i in range(4))
        candidates.append((growth_resid, rank, origin_int, dev))

    result = {"ok": False, "approx": False}
    if not candidates:
        return result

    candidates.sort(key=lambda x: x[0])
    growth_resid, rank, origin_int, dev = candidates[0]
    result.update(rank=rank, origin=origin_int, origin_dev=round(dev, 5),
                   growth_resid=round(growth_resid, 6))

    res = best_k_fixed_D(origin_int, init_S, kmax=300)
    if res:
        resid, k, disp = res
        result.update(k=k, ok=True, approx=False, fit_resid=round(resid, 5))
    else:
        approx = best_approx_k_fixed_D(origin_int, init_S)
        if approx:
            resid, k, disp = approx
            result.update(k=k, ok=True, approx=True, fit_resid=round(resid, 5))

    return result


def compute_grade_dist(origin, k, target):
    """검증/디버그용 파이썬 참조 구현 (실제 계산기는 이 로직을 JS로 포팅해
    브라우저에서 직접 실행한다). 178,750가지 조합(개체별 실제 정수 D 전부 탐색)
    중 target과 "내림" 기준으로 일치하는 경우를 등급별로 집계한다."""
    counts = {}
    total = 0
    for delta in product(OFFSETS, repeat=4):
        grade = sum(delta)
        G = [origin[i] + delta[i] for i in range(4)]
        for D in Ds:
            vec = [G[i] + D[i] for i in range(4)]
            ability = [k * v / 100 for v in vec]
            disp = matvec(M, ability)
            if floor_list(disp) == target:
                counts[grade] = counts.get(grade, 0) + 1
                total += 1
    return counts, total
