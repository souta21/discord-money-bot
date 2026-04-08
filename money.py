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

# worksheet.acell('B1').value : # セルB1の値を取得

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
            cols=7
        )

        newsheet = workbook.worksheet(today)

        newsheet.update('A1', [['日付']])
        newsheet.update('B1', [['名目']])
        newsheet.update('C1', [['支出']])
        newsheet.update('D1', [['支払者']])
        newsheet.update('E1', [['そうた']])
        newsheet.update('E2', [['こはく']])
        newsheet.update('E3', [['差額']])
        newsheet.update('E4', [['精算額']])
        newsheet.update('F1', [['合計']])
        newsheet.update("F2", '=SUMIF(D:D,"そうた",C:C)')
        newsheet.update("F3", '=SUMIF(D:D,"こはく",C:C)')
        newsheet.update("F4", "=ABS(F2-F3)/2")
        newsheet.update("F5", "=F4 - F10")
        newsheet.update("F6", '=IF(F5 <> 0, IF(F5 > 0, E2,E3), "なし")')
        newsheet.update("F5", "=F4 - F10")
        newsheet.update("E8", "そうただけ（こはくのかし）")
        newsheet.update("E9", "こはくだけ(そうたのかし)")
        newsheet.update("F8", '=SUMIF(D:D, "そうただけ", C:C)')
        newsheet.update("F9", '=SUMIF(D:D, "こはくだけ", C:C)')
        newsheet.update("F10", '=F9 - F8')

    print("worksheet取得:", today)

    return workbook.worksheet(today)

def add_spending(worksheet, name, amount,user):#引数で受け取ったシートに引数で受け取った支出を記録する関数
    lists = worksheet.get_all_values()  #シートの内容を配列で取得
    rows = len(lists) + 1               #入力されているデータの数を取得し、末端に書き込むときのインデックスとして利用する為+1する
    worksheet.update_cell(rows,1,datetime.date.today().strftime('%Y/%m/%d'))  #日付をセルに入力
    worksheet.update_cell(rows,2,name)  #引数で受け取った名前をセルに入力
    worksheet.update_cell(rows,3,amount)#引数で受け取った金額をセルに入力
    worksheet.update_cell(rows,4,user)#記入者の名前を入力

@client.event
async def on_message(message):          #メッセージを受け取ったときの挙動

    print("メッセージ受信:", message.content)
    print("チャンネル:", type(message.channel))

    if message.author.bot :             #拾ったメッセージがBotからのメッセージだったら(=Bot自身の発言だったら弾く)
        return
    
    worksheet = monthcheck()

    if message.content == '支払' or message.content == '支払い' or message.content == 'しはらい':
        await message.channel.send(now_check(worksheet))
        return 

    # -----------------------------
    # 支出入力処理
    # 形式: 支出,昼食,1200
    # -----------------------------

    receipt = re.split(r'[,\s]+', message.content.strip())

    # 入力形式チェック
    if len(receipt) < 1 or len(receipt) > 3:
        await message.channel.send(
            '入力形式が違います。\n例: 支出,昼食,1200'
        )
        return

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

    # -----------------------------
    # 支出処理
    # -----------------------------

    name = receipt[0]
    user = message.author.display_name

    if len(receipt) == 3:
        user = receipt[2]

        if user in ['そうただけ', 'こはくだけ']:
            # 完了メッセージ
            await message.channel.send(
                f'{user} の {name} の支出 {amount}円 を記録しました。'
            )
        
        else :
            add_spending(
                worksheet,
                name,
                amount,
                user
            )

            # 完了メッセージ
            await message.channel.send(
                f'{user} による {name} の支出 {amount}円 を記録しました。'
            )

    return


client.run(TOKEN)