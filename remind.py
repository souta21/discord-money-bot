import requests

WEBHOOK_URL = "https://discordapp.com/api/webhooks/1490321719276077078/szjlGU_jcqZN5Zx8MH8zkJy1AuoEvzpy8KdSkyRcTQa8Skxx6JeFzBVLAi7wWVg1hF-v"

message = {
    "content": """
🧹 今週の家事リマインド！

・ゴミ出し
・お風呂掃除
・洗濯槽チェック
"""
}

requests.post(WEBHOOK_URL, json=message)