"""
동기화 결과(summary.json)를 GitHub 이슈로 등록한다.

원래는 `gh issue create` CLI를 썼는데, self-hosted 러너(사용자 WSL 머신)에는
GitHub CLI(`gh`)가 설치되어 있지 않아 "gh: command not found"로 이 스텝만
실패했다(신펫 계산·커밋·푸시 자체는 정상 완료됨 — 이 스크립트는 그 이후의
알림 단계만 담당). `gh` CLI 설치는 self-hosted 러너에 sudo 권한이 필요해서
매번 사람이 손대야 하므로, 대신 어차피 requirements.txt에 이미 있는
`requests`로 GitHub REST API를 직접 호출해 외부 CLI 의존성을 없앴다.

필요한 환경변수(둘 다 GitHub Actions가 기본 제공/워크플로에서 이미 설정함):
  GH_TOKEN         - 이슈 생성 권한이 있는 토큰 (워크플로의 github.token)
  GITHUB_REPOSITORY - "owner/repo" 형식 (Actions가 자동으로 세팅)
"""
import json
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMARY_PATH = os.path.join(ROOT, "summary.json")


def build_body(s):
    lines = [f"전체 확인 {s['checked_total']}마리 기준 동기화 결과입니다.", ""]

    if s["added"]:
        lines.append(f"### 신규 추가 {len(s['added'])}마리")
        for p in s["added"]:
            status = "근사치" if p["approx"] else ("미지원" if not p["ok"] else "정밀")
            lines.append(f"- {p['name']} (id {p['id']}) — {status}")
        lines.append("")

    if s["needs_review"]:
        lines.append("### ⚠ 확인 필요 (원본계수 역산이 깔끔하지 않음)")
        for p in s["needs_review"]:
            lines.append(f"- **{p['name']}** (id {p['id']}) — {p['status']} · 성장률 {p['growth_S']} · 초기치 {p['init_S']}")
        lines.append("")

    if s["changed_existing"]:
        lines.append("### ⚠ 기존 펫 표기값 변경 감지 (자동 반영 안 함, 수동 확인 필요)")
        for p in s["changed_existing"]:
            lines.append(f"- {p['name']} (id {p['id']})")
        lines.append("")

    if s.get("replaced_manual"):
        lines.append("### 수동 등록 펫 정식 전환")
        for p in s["replaced_manual"]:
            lines.append(f"- {p['name']} ({p['old_id']} -> {p['new_id']})")
        lines.append("")

    if s.get("attrs_refreshed_names"):
        names = s["attrs_refreshed_names"]
        lines.append(f"### 속성(지수화풍) 수치 갱신 {len(names)}마리")
        lines.append(", ".join(names))
        lines.append("")

    if s.get("order_changed") and not (s["added"] or s.get("replaced_manual")):
        lines.append("### 목록 순서만 사이트 기준으로 재정렬됨")

    return "\n".join(lines)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GH_TOKEN/GITHUB_REPOSITORY 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    with open(SUMMARY_PATH, encoding="utf-8") as f:
        summary = json.load(f)

    from datetime import date
    title = f"펫 데이터 동기화 결과 ({date.today().isoformat()})"
    body = build_body(summary)

    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"title": title, "body": body},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"이슈 생성 완료: {resp.json().get('html_url')}")


if __name__ == "__main__":
    main()
