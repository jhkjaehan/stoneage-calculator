"""
신펫 자동 반영 파이프라인.

1. ohrsa.net/petinfo 로그인 후 전체 펫 목록을 긁어온다 (scrape.py)
2. data/overrides.json 의 수동 보정값을 덮어씌운다
3. data/pets.json 에 없는 id(신펫)만 골라 원본계수를 역산한다 (common.calibrate_pet)
4. 신펫 이미지를 96x96 WebP로 압축해 base64로 내장한다
5. 속성 게이지(attrs)는 계산 결과와 무관하므로 기존 펫이라도 항상 최신값으로 갱신한다
6. data/pets.json 을 갱신하고, index.html 을 재빌드한다
7. 결과 요약을 summary.json 으로 남긴다 (GitHub Actions가 이슈/커밋 여부 판단에 사용)

"애매한 경우만 알림" 정책: 신펫은 계산 가능(ok=true)이면 정밀/근사 상관없이 즉시
반영하되, approx=true(근사치)이거나 완전히 계산 실패한 신펫만 summary의
needs_review 목록에 담아 GitHub Actions가 이슈로 알린다.
"""
import io
import json
import os
import sys

import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import scrape  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PETS_PATH = os.path.join(ROOT, "data", "pets.json")
OVERRIDES_PATH = os.path.join(ROOT, "data", "overrides.json")
SUMMARY_PATH = os.path.join(ROOT, "summary.json")

UA = "Mozilla/5.0 (compatible; StoneAgeCalcSync/1.0; +https://github.com/)"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def fetch_image_b64(url):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    im = Image.open(io.BytesIO(resp.content))
    im.seek(0)
    im = im.convert("RGBA").resize((96, 96), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=85, method=6)
    return __import__("base64").b64encode(buf.getvalue()).decode("ascii")


def main():
    existing = load_json(PETS_PATH, [])
    existing_by_id = {p["id"]: p for p in existing}
    overrides = load_json(OVERRIDES_PATH, {})

    live_pets = scrape.fetch_pets()

    # overrides 적용 (사이트 원본 오류 수동 보정)
    for p in live_pets:
        if p["id"] in overrides:
            ov = overrides[p["id"]]
            for key in ("init_S", "growth_S", "attr", "obtain", "name"):
                if key in ov:
                    p[key] = ov[key]

    new_pets = [p for p in live_pets if p["id"] not in existing_by_id]

    # 기존 펫인데 사이트 수치가 바뀐 경우 감지(자동 반영은 안 하고 알림만)
    changed = []
    for p in live_pets:
        old = existing_by_id.get(p["id"])
        if old and (old.get("growthS") != p["growth_S"] or old.get("initS") != p["init_S"]):
            changed.append({"id": p["id"], "name": p["name"]})

    # 속성 게이지(attrs)는 계산 결과와 무관한 메타데이터라 감지 없이 항상 최신화
    attrs_refreshed = False
    for p in live_pets:
        old = existing_by_id.get(p["id"])
        if old is not None and old.get("attrs") != p["attrs"]:
            old["attrs"] = p["attrs"]
            attrs_refreshed = True

    needs_review = []
    added = []

    for p in new_pets:
        calib = common.calibrate_pet(p["growth_S"], p["init_S"])
        img_b64 = ""
        try:
            img_b64 = fetch_image_b64(p["img"])
        except Exception as e:  # noqa: BLE001
            print(f"이미지 다운로드 실패: {p['name']} ({e})", file=sys.stderr)

        entry = {
            "id": p["id"], "name": p["name"], "attr": p["attr"], "attrs": p["attrs"],
            "obtain": p["obtain"],
            "origin": calib.get("origin"), "k": calib.get("k"),
            "ok": calib["ok"], "approx": calib["approx"],
            "initS": p["init_S"], "growthS": p["growth_S"], "img": img_b64,
        }
        existing_by_id[p["id"]] = entry
        added.append({"id": p["id"], "name": p["name"], "ok": calib["ok"], "approx": calib["approx"]})
        if not calib["ok"] or calib["approx"]:
            needs_review.append({
                "id": p["id"], "name": p["name"],
                "status": "미지원" if not calib["ok"] else "근사치",
                "growth_S": p["growth_S"], "init_S": p["init_S"],
            })

    # 항상 ohrsa.net 표시 순서(live_pets 순서) 그대로 정렬해서 저장한다 -
    # 신펫을 dict 뒤에 그냥 얹기만 하면 사이트 순서와 어긋나기 때문에,
    # 매번 live_pets 순서를 기준으로 다시 나열한다.
    merged = [existing_by_id[p["id"]] for p in live_pets if p["id"] in existing_by_id]
    order_changed = [p["id"] for p in existing] != [p["id"] for p in merged]

    if new_pets or attrs_refreshed or order_changed:
        with open(PETS_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import build  # noqa: E402
        build.build()

    summary = {
        "checked_total": len(live_pets),
        "added": added,
        "needs_review": needs_review,
        "changed_existing": changed,
    }
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # GitHub Actions 후속 스텝에서 쓸 출력값
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"has_new={'true' if (new_pets or attrs_refreshed or order_changed) else 'false'}\n")
            f.write(f"needs_review={'true' if needs_review else 'false'}\n")
            f.write(f"added_count={len(added)}\n")


if __name__ == "__main__":
    main()
