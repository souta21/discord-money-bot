import discord
import gspread
import datetime
import re
import os
from dotenv import load_dotenv
from gspread.worksheet import CellFormat
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")
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

    payer = checksheet.acell('I6').value
    pay = checksheet.acell('K6').value
    get_person = checksheet.acell('J6').value

    sentence = f"清算: {payer} が {get_person} に {pay}円 を支払う"

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

        newsheet.update(headers, "A1")
        newsheet.update(functions_list, "H1", value_input_option="USER_ENTERED")

    print("worksheet取得:", today)

    return workbook.worksheet(today)

def add_expense(worksheet, item, sota, kohaku, total, payer):

    today = datetime.date.today()

    # A列の値を全部取得
    colA = worksheet.col_values(1)

    # 次に書く行番号
    next_row = len(colA) + 1

    row = [[
        str(today),
        item,
        sota,
        kohaku,
        total,
        payer
    ]]

    worksheet.update(row, f"A{next_row}")

user_list = ["そうた", "こはく"]
functions_list = [
    ["", "支払合計", "負担合計", "さ"],
    ["そうた",'=SUMIF(F:F,"そうた",E:E)', '=SUM(C:C)', '=I2-J2'],
    ["こはく",'=SUMIF(F:F,"こはく",E:E)', '=SUM(D:D)', '=I3-J3'],
    ["","","",""],
    ["","はらうひと","もらうひと","金額"],
    ["",'=IF(K2<K3,"そうた","こはく")','=IF(K2>K3,"そうた","こはく")',"=ABS(K3)"]
]

def parse_input(text, payer):

    # 全角スペース対応
    parts = re.split(r"[ 　]+", text)

    if len(parts) == 2:
        # 均等負担

        item = parts[0]

        pay_total = parts[1].replace('円', '')
        total = int(pay_total)

        half = total // 2

        if payer == "そうた":
            sota = half
            kohaku = total - half
        else:
            sota = total - half
            kohaku = half

    elif len(parts) == 3:

        item = parts[0]

        sota = int(parts[1])
        kohaku = int(parts[2])

        total = sota + kohaku

    else:
        return None

    return item, sota, kohaku, total

def cancel_last_expense(worksheet):

    # A列のデータ取得（A1はヘッダー）
    colA = worksheet.col_values(1)

    # ヘッダーしかない場合
    if len(colA) <= 1:
        return "取り消せる支出がありません。"

    # 最後のデータ行
    last_row = len(colA)

    row = worksheet.row_values(last_row)

    # 内容取り出し
    item = row[1]
    total = row[4]
    payer = row[5]

    # 最終行削除　A〜Fだけ空にする
    worksheet.batch_clear([
        f"A{last_row}:F{last_row}"
    ])

    return f"{payer} の {item} {total}円 の入力を取り消しました。"

@client.event
async def on_message(message):          #メッセージを受け取ったときの挙動

    print("メッセージ受信:", message.content)
    print("チャンネル:", type(message.channel))
    print("チャンネルID:", message.channel.id)
    print("許可されたチャンネルID:", ALLOWED_CHANNEL_ID)

    if message.author.bot :             #拾ったメッセージがBotからのメッセージだったら(=Bot自身の発言だったら弾く)
        return

    # 指定チャンネル以外は無視
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return
    
    payer = message.author.display_name
    worksheet = monthcheck()

    if message.content in ['取り消し', '取消', 'とりけし']:
        msg = cancel_last_expense(worksheet)
        await message.channel.send(msg)
        return
    
    if message.content in ['支払', '支払い', 'しはらい']:
        msg = now_check(worksheet)
        await message.channel.send(msg)
        return

    result = parse_input(
        message.content,
        payer
    )

    if result is None:
        await message.channel.send(
            "入力形式が正しくありません。\n\n例1: スーパー 1000(円)\n例2: 食費 500 500"
        )
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

    await message.channel.send(
        f'{payer} による {item} の支出 {total}円 を記録しました。'
    )

    return


client.run(TOKEN)