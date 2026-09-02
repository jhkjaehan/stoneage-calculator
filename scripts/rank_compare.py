"""
data/pets.json -> data/rank_compare.json

각 펫의 RANK 1~6 전체에 대해 "표기값 vs 계산값"을 미리 계산해둔다
(성장률·초기치 비교 페이지에서 그대로 읽어 씀). build.py가 index.html을
만들기 전에 항상 이 파일을 최신 상태로 재생성한다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def analyze(growth_S, init_S, kmax=300):
    r = common.solve4(common.M, growth_S)
    out = {}
    for rank, (lo, hi, Blo, Bhi, Bmid) in common.RANKS.items():
        origin_real = [r[i] * 10000 / Bmid - 4.5 for i in range(4)]
        origin_int = [round(x) for x in origin_real]
        dev = max(abs(origin_real[i] - origin_int[i]) for i in range(4))
        s = sum(origin_int)
        bracket_ok = (lo is None or s >= lo) and (hi is None or s <= hi)

        Gg = [origin_int[i] + 2 for i in range(4)]
        growth_raw = [(Gg[i] + common.BONUS_AVG) * Bmid / 10000 for i in range(4)]
        growth_calc = common.matvec(common.M, growth_raw)

        vec = [Gg[i] + common.BONUS_AVG for i in range(4)]
        unscaled = common.matvec(common.M, vec)
        best_exact = None
        for k in range(1, kmax + 1):
            disp = [k / 100 * u for u in unscaled]
            if common.floor_list(disp) == init_S:
                resid = sum((disp[i] - init_S[i]) ** 2 for i in range(4))
                if best_exact is None or resid < best_exact[0]:
                    best_exact = (resid, k, disp)
        if best_exact:
            resid, k, init_calc = best_exact
            exact = True
        else:
            approx = common.best_approx_k_fixed_D(origin_int, init_S)
            if approx:
                resid, k, init_calc = approx
            else:
                k, init_calc, resid = None, None, None
            exact = False

        out[rank] = {
            "origin": origin_int, "growth_dev": round(dev, 5), "bracket_ok": bracket_ok,
            "growth_calc": [round(x, 4) for x in growth_calc],
            "k": k, "k_exact": exact,
            "initCalc": [round(x, 3) for x in init_calc] if init_calc else None,
            "resid": round(resid, 4) if resid is not None else None,
        }
    return out


def build():
    with open(os.path.join(ROOT, "data", "pets.json"), encoding="utf-8") as f:
        pets = json.load(f)

    doc = {}
    for p in pets:
        doc[p["id"]] = {
            "name": p["name"],
            "growthS": p["growthS"], "initS": p["initS"],
            "prodOrigin": p["origin"], "prodK": p["k"], "prodApprox": p["approx"],
            "ranks": analyze(p["growthS"], p["initS"]),
        }

    out_path = os.path.join(ROOT, "data", "rank_compare.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    print(f"rank_compare.json 생성 완료 ({os.path.getsize(out_path)} bytes)")


if __name__ == "__main__":
    build()
