"""data/pets.json + template.html -> index.html (배포용 단일 정적 파일 생성)"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build():
    with open(os.path.join(ROOT, "data", "pets.json"), encoding="utf-8") as f:
        pets_json_text = f.read()
    pets_json_safe = pets_json_text.replace("</script", "<\\/script")

    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as f:
        tpl = f.read()

    out = tpl.replace("__PET_DATA__", pets_json_safe)

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)

    print(f"index.html 생성 완료 ({os.path.getsize(os.path.join(ROOT, 'index.html'))} bytes)")


if __name__ == "__main__":
    build()
