"""
스톤에이지 환각 계산기 - 원본계수 역산 공통 라이브러리

klaking.tistory.com/3 (소스: github.com/chenmingbiao/stone-age enemybase.txt 분석)의
공식을 그대로 구현한다. 표기 성장률(S급, 평균 A=2.5 · B=RANK 중앙값 가정)로부터
RANK 1~6 전 구간을 대입해 원본계수(체/공/방/순, 정수)가 가장 정수에 가깝게 떨어지는
지점을 찾고, 그 원본계수 + 정수 초기치계수(k)가 실제 S급 초기치를 재현하는지
178,750가지 조합(등급 오프셋 5^4 x 10포인트분배 286)으로 재검증한다.
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

# 10포인트를 체/공/방/순 4개 스탯에 분배하는 모든 조합 (286가지)
Ds = [d for d in product(range(11), repeat=4) if sum(d) == 10]

# 등급 오프셋: 각 스탯 -2~+2 (5^4 = 625가지, 오프셋 합 = 등급 -8~+8)
OFFSETS = [-2, -1, 0, 1, 2]


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


def best_exact_k_and_D(origin, init_S, kmax=600):
    """origin(정수 4개)이 주어졌을 때, init_S를 정확히(반올림 기준) 재현하는
    정수 k와 10포인트분배 D 중 잔차가 가장 작은 조합을 찾는다."""
    G = [origin[i] + 2 for i in range(4)]
    best = None
    for k in range(1, kmax + 1):
        for D in Ds:
            vec = [G[i] + D[i] for i in range(4)]
            ability = [k * v / 100 for v in vec]
            disp = matvec(M, ability)
            if [round(x) for x in disp] == init_S:
                resid = sum((disp[i] - init_S[i]) ** 2 for i in range(4))
                if best is None or resid < best[0]:
                    best = (resid, k, D, disp)
    return best


def best_approx_k_and_D(origin, init_S):
    """정확히 반올림 일치하는 조합이 없을 때, 최소자승으로 가장 근접한
    (k, D) 조합을 근사치로 찾는다 (정수 k 반올림)."""
    G = [origin[i] + 2 for i in range(4)]
    best = None
    for D in Ds:
        vec = [G[i] + D[i] for i in range(4)]
        unscaled = matvec(M, vec)
        den = sum(u * u for u in unscaled)
        if den == 0:
            continue
        s = sum(unscaled[i] * init_S[i] for i in range(4)) / den
        k = round(s * 100)
        if k < 1:
            continue
        ability = [k * v / 100 for v in vec]
        disp = matvec(M, ability)
        resid = sum((disp[i] - init_S[i]) ** 2 for i in range(4))
        if best is None or resid < best[0]:
            best = (resid, k, D, disp)
    return best


def calibrate_pet(growth_S, init_S):
    """growth_S, init_S (둘 다 [체,공,방,순] 순서) 로부터
    {'rank','origin','k','ok','approx','fit_resid'} 를 계산한다.

    1) 성장률 4개 방정식을 풀어 raw growth(before-bonus) r을 구한다.
    2) RANK 1~6 각각의 보정계수 중앙값으로 원본계수를 역산, 정수와의
       편차가 가장 작은 RANK를 채택한다 (편차 < 0.05일 때만 '정밀' 후보).
    3) 그 원본계수로 초기치를 정확히 재현하는 정수 k/D가 있는지 검색한다.
    4) 실패하면 6개 RANK 전체에서 초기치 기준 최소자승 근사해를 찾아
       'approx'로 표시한다.
    """
    r = solve4(M, growth_S)

    devs_by_rank = {}
    for rank, (lo, hi, Blo, Bhi, Bmid) in RANKS.items():
        origin = [r[i] * 10000 / Bmid - 4.5 for i in range(4)]
        origin_int = [round(x) for x in origin]
        dev = max(abs(origin[i] - origin_int[i]) for i in range(4))
        s = sum(origin_int)
        ok_bracket = (lo is None or s >= lo) and (hi is None or s <= hi)
        devs_by_rank[rank] = (dev, origin_int, ok_bracket)

    bracket_candidates = [
        (dev, rank, oi) for rank, (dev, oi, okb) in devs_by_rank.items() if okb
    ]

    result = {"ok": False, "approx": False}

    if bracket_candidates:
        bracket_candidates.sort()
        dev, rank, origin_int = bracket_candidates[0]
        result.update(rank=rank, origin_dev=dev, origin=origin_int)
        if dev < 0.05:
            res = best_exact_k_and_D(origin_int, init_S, kmax=600)
            if res:
                resid, k, D, disp = res
                result.update(k=k, ok=True, fit_resid=round(resid, 5))

    if not result["ok"]:
        # 근사치 폴백: 6개 RANK 전체에서 초기치 최소자승 최적해 탐색
        cand = []
        for rank, (dev, origin_int, okb) in devs_by_rank.items():
            res = best_approx_k_and_D(origin_int, init_S)
            if res:
                resid, k, D, disp = res
                cand.append((resid, rank, origin_int, k))
        if cand:
            cand.sort(key=lambda x: x[0])
            resid, rank, origin_int, k = cand[0]
            result.update(rank=rank, origin=origin_int, k=k, ok=True,
                           approx=True, fit_resid=round(resid, 5))

    return result


def compute_grade_dist(origin, k, target):
    """검증/디버그용 파이썬 참조 구현 (실제 계산기는 이 로직을 JS로 포팅해
    브라우저에서 직접 실행한다). 178,750가지 조합 중 target과 일치하는
    경우를 등급별로 집계한다."""
    counts = {}
    total = 0
    for delta in product(OFFSETS, repeat=4):
        grade = sum(delta)
        G = [origin[i] + delta[i] for i in range(4)]
        for D in Ds:
            vec = [G[i] + D[i] for i in range(4)]
            ability = [k * v / 100 for v in vec]
            disp = matvec(M, ability)
            if [round(x) for x in disp] == target:
                counts[grade] = counts.get(grade, 0) + 1
                total += 1
    return counts, total
