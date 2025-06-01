import yagmail
import pandas as pd
from pathlib import Path

def send_email():
    data_path = Path("data/insider.csv")
    if not data_path.exists():
        print("[错误] insider.csv 不存在")
        return

    df = pd.read_csv(data_path)
    if df.empty:
        body = "今日未发现有效的 insider 买入记录。"
    else:
        body = df.to_markdown(index=False)

    yag = yagmail.SMTP(user='${{ secrets.EMAIL_USERNAME }}', password='${{ secrets.EMAIL_PASSWORD }}')
    yag.send(to='${{ secrets.EMAIL_TO }}',
             subject='每日 Insider 买入报告',
             contents=[body])
