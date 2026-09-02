"""data/pets.json + template.html -> index.html (배포용 단일 정적 파일 생성)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rank_compare  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build():
    rank_compare.build()  # data/rank_compare.json 항상 최신화

    with open(os.path.join(ROOT, "data", "pets.json"), encoding="utf-8") as f:
        pets_json_safe = f.read().replace("</script", "<\\/script")
    with open(os.path.join(ROOT, "data", "rank_compare.json"), encoding="utf-8") as f:
        rank_compare_safe = f.read().replace("</script", "<\\/script")

    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as f:
        tpl = f.read()

    out = tpl.replace("__PET_DATA__", pets_json_safe)
    out = out.replace("__RANK_COMPARE_DATA__", rank_compare_safe)

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)

    print(f"index.html 생성 완료 ({os.path.getsize(os.path.join(ROOT, 'index.html'))} bytes)")


if __name__ == "__main__":
    build()
