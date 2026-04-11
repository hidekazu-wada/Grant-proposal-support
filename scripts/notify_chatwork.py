"""
月次助成金リサーチ結果を ChatWork に投稿するスクリプト。

使い方:
    python scripts/notify_chatwork.py data/grants/2026-05.md

環境変数:
    CHATWORK_API_TOKEN  ChatWork APIトークン
    CHATWORK_ROOM_ID    投稿先ルームID
"""

import os
import re
import sys
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CHATWORK_API_BASE = "https://api.chatwork.com/v2"


# ---------------------------------------------------------------------------
# ChatWork API
# ---------------------------------------------------------------------------

def post_message(token: str, room_id: str, body: str) -> str | None:
    """ChatWork にメッセージを投稿し、message_id を返す。"""
    url = f"{CHATWORK_API_BASE}/rooms/{room_id}/messages"
    headers = {"X-ChatWorkToken": token}
    data = {"body": body, "self_unread": "1"}

    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    message_id = result.get("message_id")
    logger.info("投稿成功 message_id=%s", message_id)
    return str(message_id) if message_id else None


def post_error_notice(token: str, room_id: str, file_path: str, error: str) -> None:
    """パース失敗時にエラー通知を投稿する。"""
    body = (
        "[info][title]【助成金BOT】処理エラー[/title]"
        f"ファイル: {file_path}\n"
        f"エラー: {error}\n\n"
        "リサーチ結果ファイルの読み取りに失敗しました。\n"
        "ファイルの形式を確認してください。[/info]"
    )
    post_message(token, room_id, body)


# ---------------------------------------------------------------------------
# Markdown パーサー
# ---------------------------------------------------------------------------

def parse_header(content: str) -> dict:
    """ヘッダーから年月とメタ情報を抽出する。"""
    header = {}
    m = re.search(r"月次助成金スキャン[｜|](\d{4})年(\d{1,2})月", content)
    if m:
        header["year"] = m.group(1)
        header["month"] = m.group(2).zfill(2)
    else:
        header["year"] = "?????"
        header["month"] = "??"
    return header


def parse_candidates(content: str) -> list[dict]:
    """区分1（採否候補）の各候補をパースする。"""
    candidates = []

    section1_match = re.search(
        r"##\s*区分1[：:]?\s*今月の採否候補(.*?)(?=##\s*区分[2-5]|\Z)",
        content,
        re.DOTALL,
    )
    if not section1_match:
        return candidates

    section1 = section1_match.group(1)

    if re.search(r"今月の採否候補[：:]\s*0件", section1):
        return candidates

    candidate_blocks = re.split(r"\n(?=###\s)", section1)

    current = {}
    for block in candidate_blocks:
        fields = {
            "制度名": r"制度名[：:]\s*(.+)",
            "想定使途": r"想定使途[（(].*?[）)][：:]\s*(.+)|想定使途[：:]\s*(.+)",
            "締切": r"締切[（(].*?[）)][：:]\s*(.+)|締切[：:]\s*(.+)",
            "準備余裕": r"準備余裕[（(].*?[）)][：:]\s*(.+)|準備余裕[：:]\s*(.+)",
            "金額感": r"金額感[（(].*?[）)][：:]\s*(.+)|金額感[：:]\s*(.+)",
            "事業適合": r"事業適合[（(].*?[）)][：:]\s*(.+)|事業適合[：:]\s*(.+)",
            "仮判断ラベル": r"仮判断ラベル[（(].*?[）)][：:]\s*(.+)|仮判断ラベル[：:]\s*(.+)",
            "一言でいうと": r"一言でいうと[：:]\s*(.+)",
        }

        for key, pattern in fields.items():
            m = re.search(pattern, block)
            if m:
                value = next((g for g in m.groups() if g), None)
                if value:
                    current[key] = value.strip()

        list_stop = r"(?=[-\-]\s*(?:採る理由|実行条件|主な負担・制約|罠チェック|不明点)[：:]|###|【|\Z)"
        list_fields = {
            "採る理由": rf"採る理由[：:]?(.*?){list_stop}",
            "実行条件": rf"実行条件[：:]?(.*?){list_stop}",
            "主な負担・制約": rf"主な負担・制約[：:]?(.*?){list_stop}",
        }

        for key, pattern in list_fields.items():
            m = re.search(pattern, block, re.DOTALL)
            if m:
                raw = m.group(1)
                items = [
                    line.strip()
                    for line in re.findall(r"[-・]\s*(.+)", raw)
                    if not re.match(r"(?:採る理由|実行条件|主な負担・制約)[：:]", line.strip())
                ]
                if items:
                    current[key] = items

        if "制度名" in current and current not in candidates:
            existing = next(
                (c for c in candidates if c.get("制度名") == current["制度名"]),
                None,
            )
            if existing:
                existing.update(current)
            else:
                candidates.append(current)
                current = {}

    if current and current not in candidates:
        existing = next(
            (c for c in candidates if c.get("制度名") == current.get("制度名")),
            None,
        )
        if existing:
            existing.update(current)
        elif current.get("制度名"):
            candidates.append(current)

    return candidates


# ---------------------------------------------------------------------------
# 準備余裕ラベルの読み替え
# ---------------------------------------------------------------------------

READINESS_DISPLAY = {
    "高": "余裕あり",
    "中": "ふつう",
    "低": "あまりない",
}


def format_readiness(raw: str) -> str:
    """準備余裕の値を読みやすい表現に変換する。補足説明があればそのまま残す。"""
    for key, display in READINESS_DISPLAY.items():
        if raw.startswith(key):
            rest = raw[len(key):].strip()
            if rest.startswith("（") or rest.startswith("("):
                return f"{display}{rest}"
            return display
    return raw


# ---------------------------------------------------------------------------
# ChatWork メッセージ組み立て
# ---------------------------------------------------------------------------

def build_individual_message(index: int, candidate: dict) -> str:
    """個別通知を組み立てる。"""
    number = chr(0x2460 + index)  # ①②③...
    title_name = candidate.get("制度名", "不明な制度")

    deadline = candidate.get("締切", "未確認")
    readiness = format_readiness(candidate.get("準備余裕", "未確認"))
    money = candidate.get("金額感", "未確認")
    usage = candidate.get("想定使途", "未確認")
    summary = candidate.get("一言でいうと", "")

    lines = [
        f"[info][title]{number} {title_name}[/title]",
        f"■ 例えばこんな使い方: {usage} など",
        f"■ 締切: {deadline}",
        f"■ 準備にかかる時間の目安: {readiness}",
        f"■ 金額感: {money}",
        "",
    ]

    if summary:
        lines.append(f"【一言でいうと】\n上記のような使い方をする場合、{summary}")
        lines.append("")

    # メリット
    reasons = candidate.get("採る理由", [])
    if reasons:
        lines.append("【この制度を使うメリット】")
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")

    # 申請に必要なこと
    conditions = candidate.get("実行条件", [])
    if conditions:
        lines.append("【申請するために必要なこと】")
        for c in conditions:
            lines.append(f"- {c}")
        lines.append("")

    # 申請〜運用の負担
    burdens = candidate.get("主な負担・制約", [])
    if burdens:
        lines.append("【申請〜運用で発生する負担】")
        for b in burdens:
            lines.append(f"- {b}")
        lines.append("")

    lines.extend([
        "【この場で決めていただきたいこと】",
        "以下のうち、どれにしますか？",
        "□ 採用 → 担当と期限を決めて申請準備に入る",
        "□ 条件付き採用 → 追加情報を確認してから最終判断",
        "□ 持越し → 来月以降にあらためて検討",
        "□ 見送り → 今回は対象外",
        "",
        "→ 採用または条件付きの場合:",
        "　担当: （この場で決定）",
        "　いつまでに次のアクション: （この場で決定）",
        "[/info]",
    ])

    return "\n".join(lines)


def build_summary_message(
    header: dict,
    candidates: list[dict],
) -> str:
    """サマリ通知（一覧）を組み立てる。2件以上のときのみ使用。"""
    year = header.get("year", "????")
    month = header.get("month", "??")
    count = len(candidates)

    lines = [
        f"[info][title]【月次助成金スキャン｜{year}年{month}月｜今月は{count}件】[/title]",
        f"今月、HAMAYOUリゾートに関係しそうな助成金が{count}件見つかりました。",
        "この後に1件ずつ詳細を投稿しますので、以下の一覧を参考に",
        "気になるものから読んでみてください。",
        "",
    ]

    # 仮判断ラベルでグルーピング
    groups = {
        "すぐ判断できそうな候補": [],
        "今日判断したいが条件あり": [],
        "もう少し情報が必要": [],
        "参考（見送り寄り）": [],
    }

    label_to_group = {
        "採用候補": "すぐ判断できそうな候補",
        "条件付き採用": "今日判断したいが条件あり",
        "要確認": "今日判断したいが条件あり",
        "持越し候補": "もう少し情報が必要",
        "見送り候補": "参考（見送り寄り）",
    }

    for i, c in enumerate(candidates):
        label = c.get("仮判断ラベル", "要確認")
        group_key = label_to_group.get(label, "参考（見送り寄り）")
        groups[group_key].append((i, c))

    for group_name, items in groups.items():
        if not items:
            continue
        lines.append(f"── {group_name} ──")
        for i, c in items:
            number = chr(0x2460 + i)
            name = c.get("制度名", "不明")
            usage = c.get("想定使途", "")
            readiness = format_readiness(c.get("準備余裕", "未確認"))

            display_name = f"{name}｜{usage} など" if usage else name
            lines.append(f"{number} {display_name}")
            lines.append(f"　準備にかかる時間: {readiness}")
            lines.append("")

    lines.extend([
        "この後の詳細メッセージで、それぞれの中身を確認してください。",
        "",
        "今日この場で決めること",
        "1. 各候補について: 採用 / 条件付き / 持越し / 見送り",
        "2. 採用する場合の担当",
        "3. 次のアクション期限",
        "[/info]",
    ])

    return "\n".join(lines)


def build_zero_message(header: dict) -> str:
    """0件月の通知メッセージを組み立てる。"""
    year = header.get("year", "????")
    month = header.get("month", "??")
    return (
        f"[info][title]【月次助成金スキャン｜{year}年{month}月｜今月は0件】[/title]"
        "今月はHAMAYOUリゾートに合いそうな助成金は見つかりませんでした。\n\n"
        "主要な情報源はすべて確認済みです。\n"
        "監視を続けている制度については、リサーチ結果ファイルをご確認ください。\n\n"
        "今月の会議では、新規の助成金議題はありません。\n"
        "前月までに採用した案件の進捗確認のみお願いします。[/info]"
    )


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        logger.error("使い方: python notify_chatwork.py <data/grants/YYYY-MM.md>")
        sys.exit(1)

    file_path = sys.argv[1]
    token = os.environ.get("CHATWORK_API_TOKEN", "")
    room_id = os.environ.get("CHATWORK_ROOM_ID", "")

    if not token or not room_id:
        logger.error("CHATWORK_API_TOKEN と CHATWORK_ROOM_ID を設定してください")
        sys.exit(1)

    # ファイル読み込み
    path = Path(file_path)
    if not path.exists():
        logger.error("ファイルが見つかりません: %s", file_path)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    # パース
    try:
        header = parse_header(content)
        candidates = parse_candidates(content)
    except Exception as e:
        logger.error("パースエラー: %s", e)
        post_error_notice(token, room_id, file_path, str(e))
        sys.exit(1)

    # 0件月
    if not candidates:
        msg = build_zero_message(header)
        post_message(token, room_id, msg)
        logger.info("0件月の通知を投稿しました")
        return

    # 2件以上ならサマリを先に投稿
    if len(candidates) >= 2:
        summary = build_summary_message(header, candidates)
        post_message(token, room_id, summary)
        time.sleep(1)

    # 個別通知を投稿
    for i, candidate in enumerate(candidates):
        msg = build_individual_message(i, candidate)
        post_message(token, room_id, msg)
        if i < len(candidates) - 1:
            time.sleep(1)

    logger.info("全%d件の投稿が完了しました", len(candidates))


if __name__ == "__main__":
    main()
