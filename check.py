import os
import re
import json
import time
import random
import datetime
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")
DISCORD_LOG_URL = os.environ.get("DISCORD_WEBHOOK_URL_LOG") or DISCORD_URL
DATA_FILE = "data/prices.json"

WATCH_ITEMS = [
    {
        "keyword": "メタリックモンスターズギャラリー"
    },
    {
        "keyword": "メタリックアイテムズギャラリー"
    }
]

def load_price_history():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"履歴読み込みエラー: {e}")
    return {}

def save_price_history(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"価格履歴を保存しました（件数: {len(data)}件）")
    except Exception as e:
        print(f"履歴保存エラー: {e}")

def send_discord(msg, target_url=None):
    url = target_url or DISCORD_URL
    if not url:
        print("Webhook URLが設定されていません")
        print(msg)
        return

    max_len = 1900
    chunks = [msg[i:i+max_len] for i in range(0, len(msg), max_len)]

    for chunk in chunks:
        req = urllib.request.Request(
            url,
            data=json.dumps({"content": chunk}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        try:
            with urllib.request.urlopen(req) as res:
                print(f"送信成功 (Status: {res.status})")
        except Exception as e:
            print(f"Discord送信エラー: {e}")
        time.sleep(1)

def send_price_list_text(price_history, target_url=None):
    if not price_history:
        send_discord("📊 **【現在の保存価格リスト】**\n現在保存されている価格データはありません。", target_url=target_url)
        return

    now_jst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    date_str = now_jst.strftime('%Y年%m月%d日 %H:%M')
    
    header = f"📊 **【取得価格リスト ({date_str} 時点)】**\n```\n"
    footer = "\n```"
    
    lines = []
    for name, price in price_history.items():
        lines.append(f"{name}: {price:,}円")

    content_body = "\n".join(lines)
    full_message = header + content_body + footer

    if len(full_message) <= 1900:
        send_discord(full_message, target_url=target_url)
    else:
        send_discord(f"📊 **【取得価格リスト ({date_str} 時点)】**", target_url=target_url)
        chunk_lines = []
        for line in lines:
            chunk_lines.append(line)
            if len(chunk_lines) >= 15:
                send_discord("```\n" + "\n".join(chunk_lines) + "\n```", target_url=target_url)
                chunk_lines = []
        if chunk_lines:
            send_discord("```\n" + "\n".join(chunk_lines) + "\n```", target_url=target_url)

def send_daily_links():
    """巡回リンク集送信（ソフマップ追加・ビックカメラのエンコード修正版）"""
    now_jst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    date_str = now_jst.strftime('%Y年%m月%d日')
    
    send_discord(f"🔔 **【ドラクエメタリックシリーズ 本日の巡回リンク】**\n📅 配信日: **{date_str}**", target_url=DISCORD_URL)
    time.sleep(1)

    for item in WATCH_ITEMS:
        kw = item["keyword"]
        encoded_utf8 = urllib.parse.quote(kw)
        
        # ビックカメラもUTF-8のquoteで安全に検索できるように修正
        lines = [
            f"**【{kw}】**",
            f"・[あみあみ](<https://slist.amiami.jp/top/search/list?s_keywords={encoded_utf8}&pagemax=30>)",
            f"・[Amazon](<https://www.amazon.co.jp/s?k={encoded_utf8}>)",
            f"・[ビックカメラ](<https://www.biccamera.com/bc/category/?q={encoded_utf8}>)",
            f"・[ヨドバシカメラ](<https://www.yodobashi.com/?word={encoded_utf8}>)",
            f"・[ソフマップ](<https://a.sofmap.com/search_result.aspx?gid=&keyword={encoded_utf8}>)"
        ]
        send_discord("\n".join(lines), target_url=DISCORD_URL)
        time.sleep(1)

    common_links = [
        "**【トップページ（直検索不可サイト）】**",
        "・[スクエニ e-STORE](<https://store.jp.square-enix.com/>)",
        "・[Joshin web](<https://joshinweb.jp/>)"
    ]
    send_discord("\n".join(common_links), target_url=DISCORD_URL)

def main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_jst = now_utc + datetime.timedelta(hours=9)
    
    hour = now_jst.hour
    minute = now_jst.minute
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    print(f"--- 実行開始 (JST: {now_jst.strftime('%Y-%m-%d %H:%M:%S')}) ---")

    is_manual_run = (event_name == "workflow_dispatch")
    is_daily_time = (hour == 7 and minute >= 30)

    if is_daily_time or is_manual_run:
        send_daily_links()

    price_history = load_price_history()
    save_price_history(price_history)

    if is_manual_run:
        send_price_list_text(price_history, target_url=DISCORD_LOG_URL)

if __name__ == "__main__":
    main()
