"""
ohrsa.net/petinfo 에 로그인해서 펫 목록 원본 데이터를 긁어온다.

로그인 계정은 환경변수 OHRSA_ID / OHRSA_PW 로 전달한다 (절대 코드에 하드코딩하지 않음).
GitHub Actions에서는 리포지토리 Secrets 로 등록해서 사용한다.
"""
import os
import re
import sys
import requests

BASE = "https://ohrsa.net"
UA = "Mozilla/5.0 (compatible; StoneAgeCalcSync/1.0; +https://github.com/)"

CARD_RE = re.compile(
    r'data-wr-id="(\d+)" data-name="([^"]+)" data-img="([^"]+)" '
    r'data-atk="([^"]+)" data-def="([^"]+)" data-agi="([^"]+)" data-hp="([^"]+)" '
    r'data-total="([^"]+)" data-attr="([^"]*)" data-obtain="([^"]*)"'
)
# 카드 블록 안에서 초기치 4개 숫자 (공 방 순 체 순서로 표시됨)
INIT_RE = re.compile(
    r'<td class="val_red">[^<]+</td><td>\d+</td><td>[^<]*</td><td>([\d\s]+)</td>'
)
# 속성 게이지(예: "화 (8)") - 1~2개, 두 값의 합은 항상 10
ATTR_RE = re.compile(r'<div class="attr_label_tag ([가-힣])">[가-힣]\s*\((\d+)\)</div>')


def login(session):
    mb_id = os.environ.get("OHRSA_ID")
    mb_password = os.environ.get("OHRSA_PW")
    if not mb_id or not mb_password:
        print("OHRSA_ID / OHRSA_PW 환경변수가 설정되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)
    session.get(f"{BASE}/bbs/login.php", headers={"User-Agent": UA}, timeout=20)
    resp = session.post(
        f"{BASE}/bbs/login_check.php",
        data={"mb_id": mb_id, "mb_password": mb_password, "url": f"{BASE}/"},
        headers={"User-Agent": UA},
        timeout=20,
        allow_redirects=True,
    )
    # 로그인 실패 시 login.php?error=... 로 리다이렉트됨
    if "login.php" in resp.url:
        print("로그인 실패: 계정 정보를 확인해주세요.", file=sys.stderr)
        sys.exit(1)


def fetch_pets():
    session = requests.Session()
    login(session)
    resp = session.get(f"{BASE}/petinfo", headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # 펫 카드 블록 단위로 분리해서 각각 파싱 (오르펫.txt 파싱 로직과 동일)
    blocks = re.split(r'(?=<div class="pet_card_item)', html)
    pets = []
    for b in blocks:
        m = CARD_RE.search(b)
        if not m:
            continue
        wrid, name, img, atk, defe, agi, hp, total, attr, obtain = m.groups()
        m2 = INIT_RE.search(b)
        if not m2:
            continue
        nums = m2.group(1).split()
        if len(nums) != 4:
            continue
        init_gbst = [int(x) for x in nums]  # 공 방 순 체 순서
        attrs = [[name_, int(val)] for name_, val in ATTR_RE.findall(b)]
        pets.append({
            "id": wrid,
            "name": name,
            "img": img,
            "attr": attr,
            "attrs": attrs,
            "obtain": obtain,
            "growth_S": [float(hp), float(atk), float(defe), float(agi)],  # 체공방순
            "init_S": [init_gbst[3], init_gbst[0], init_gbst[1], init_gbst[2]],  # 체공방순
        })
    return pets


if __name__ == "__main__":
    import json
    pets = fetch_pets()
    print(f"{len(pets)}마리 확인", file=sys.stderr)
    json.dump(pets, sys.stdout, ensure_ascii=False)
