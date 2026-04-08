import discord
import gspread
import datetime
import re
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if credentials_json:
    with open("credentials.json", "w") as f:
        f.write(credentials_json)


from google.oauth2.service_account import Credentials

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# スコープ設定
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 認証（oauth2clientを使わない）
credentials = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES
)
gc = gspread.authorize(credentials)

# スプレッドシートを開く
SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
workbook = gc.open_by_key(SPREADSHEET_KEY)
worksheet = workbook.sheet1

def now_check(checksheet):
    print("now_check開始")

    pay_s = checksheet.acell('F2').value
    pay_k = checksheet.acell('F3').value

    payer = checksheet.acell('F6').value
    pay = checksheet.acell('F5').value

    sentence = f"現在の支払状況\n\nそうた: {pay_s}円\nこはく: {pay_k}円\n\n清算: {payer} が {pay}円 を支払う"

    return sentence

def monthcheck():
    print("monthcheck開始")

    worksheet_list = workbook.worksheets()
    today = datetime.date.today().strftime('%Y%m')

    exist = False

    for current in worksheet_list:
        if current.title == today:
            exist = True

    if exist == False:
        print("新しい月シート作成")

        workbook.add_worksheet(
            title=today,
            rows=100,
            cols=10
        )

        newsheet = workbook.worksheet(today)

        headers = [[
            "日付",
            "名目",
            "そうた負担",
            "こはく負担",
            "支払総額",
            "支払者"
        ]]

        newsheet.update("A1", headers)

        setup_summary(newsheet)
        setup_formula(newsheet)

    print("worksheet取得:", today)

    return workbook.worksheet(today)

def setup_summary(sheet):

    formulas = [

        ["そうた負担合計",
        "=SUM(C2:C)"],

        ["こはく負担合計",
        "=SUM(D2:D)"],

        ["そうた支払合計",
        '=SUMIF(F:F,"そうた",E:E)'],

        ["こはく支払合計",
        '=SUMIF(F:F,"こはく",E:E)'],

        ["そうた清算額",
        "=H4-H2"],

        ["こはく清算額",
        "=H5-H3"]

    ]

    sheet.update("H1:I6", formulas)

def setup_formula(sheet):

    formulas = [

        # 実際支払額
        ["=SUMIF(F:F,\"そうた\",E:E)"],
        ["=SUMIF(F:F,\"こはく\",E:E)"],

        # 負担額
        ["=SUM(C:C)"],
        ["=SUM(D:D)"],

        # 清算額
        ["=H2-H4"]

    ]

    sheet.update("J2:J6", formulas)

def add_expense(worksheet, item, sota, kohaku, total, payer):

    today = datetime.date.today()

    row = [
        str(today),
        item,
        sota,
        kohaku,
        total,
        payer
    ]

    worksheet.append_row(row)

user_list = ["そうた", "こはく"]

def parse_input(text, payer):

    # 全角スペース対応
    parts = re.split(r"[ 　]+", text)

    if len(parts) == 2:
        # 均等負担

        item = parts[0]
        total = int(parts[1])

        half = total // 2

        if payer == "そうた":
            sota = half
            kohaku = total - half
        else:
            sota = total - half
            kohaku = half

    elif len(parts) == 3:
        # 個別負担

        item = parts[0]

        sota = int(parts[1])
        kohaku = int(parts[2])

        total = sota + kohaku

    else:
        return None

    return item, sota, kohaku, total

@client.event
async def on_message(message):          #メッセージを受け取ったときの挙動

    print("メッセージ受信:", message.content)
    print("チャンネル:", type(message.channel))

    if message.author.bot :             #拾ったメッセージがBotからのメッセージだったら(=Bot自身の発言だったら弾く)
        return
    
    payer = message.author.display_name
    worksheet = monthcheck()

    if message.content == '支払' or message.content == '支払い' or message.content == 'しはらい':
        await message.channel.send(now_check(worksheet))
        return 

    result = parse_input(
        message.content,
        payer
    )

    if result is None:
        return

    item, sota, kohaku, total = result

    add_expense(
        worksheet,
        item,
        sota,
        kohaku,
        total,
        payer
    )

    # 入力形式チェック
    # 円を削除（例: 1200円 → 1200）
    receipt[1] = receipt[1].replace('円', '')

    # 金額チェック
    try:
        amount = int(receipt[1])
    except ValueError:
        await message.channel.send(
            '金額は数字で入力してください。'
        )
        return


        if user in ['そうただけ', 'こはくだけ']:
            # 完了メッセージ
            await message.channel.send(
                f'{user} の {name} の支出 {amount}円 を記録しました。'
            )
        
        else :
            # 完了メッセージ
            await message.channel.send(
                f'{user} による {name} の支出 {amount}円 を記録しました。'
            )

    await message.channel.send(
        f'{payer} による {item} の支出 {total}円 を記録しました。'
    )

    return


client.run(TOKEN)