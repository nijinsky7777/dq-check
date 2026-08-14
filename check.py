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

# 監視対象アイテムの設定（商品キーワードと定価 MSRP）
WATCH_ITEMS = [
    {
        "keyword": "メタリックモンスターズギャラリー",
        "msrp": 9000
    },
    {
        "keyword": "メタリックアイテムズギャラリー",
        "msrp": 4500
    }
]

# ---------------------------------------------------------
# 0. 価格履歴データ（JSON）管理 ＆ Discord送信関数
# ---------------------------------------------------------

def load_price_history():
    """保存された価格履歴をロード"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"履歴読み込みエラー: {e}")
    return {}

def save_price_history(data):
    """最新の価格履歴を保存"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"履歴保存エラー: {e}")

def send_discord(msg, target_url=None):
    """Discordへのテキスト送信（2000文字制限対策付き）"""
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
    """保存されている価格リストをテキストメッセージとしてDiscordへ送信"""
    if not price_history:
        send_discord("📊 **【現在の保存価格リスト】**\n現在保存されている価格データはありません。", target_url=target_url)
        return

    now_str = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timedelta(hours=9)).strftime('%Y/%m/%d %H:%M')
    
    header = f"📊 **【取得価格リスト ({now_str} 時点)】**\n```\n"
    footer = "\n```"
    
    lines = []
    for name, price in price_history.items():
        lines.append(f"{name}: {price:,}円")

    content_body = "\n".join(lines)
    full_message = header + content_body + footer

    if len(full_message) <= 1900:
        send_discord(full_message, target_url=target_url)
    else:
        send_discord(f"📊 **【取得価格リスト ({now_str} 時点)】**", target_url=target_url)
        chunk_lines = []
        for line in lines:
            chunk_lines.append(line)
            if len(chunk_lines) >= 15:
                send_discord("```\n" + "\n".join(chunk_lines) + "\n```", target_url=target_url)
                chunk_lines = []
        if chunk_lines:
            send_discord("```\n" + "\n".join(chunk_lines) + "\n
