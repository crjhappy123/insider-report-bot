import requests
import pandas as pd
from bs4 import BeautifulSoup
import openai
import yagmail
from config import OPENAI_API_KEY, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO

def fetch_insider_data_from_finviz(min_value=50000):
    url = "https://finviz.com/insidertrading.ashx"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="body-table")

    if not table:
        print("[错误] 未能找到 Finviz insider 表格")
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]  # skip header
    data = []
    for row in rows:
        cols = [col.text.strip() for col in row.find_all("td")]
        if len(cols) < 10:
            continue
        try:
            value_str = cols[9].replace("$", "").replace(",", "")
            value = float(value_str)
            if value >= min_value and "Buy" in cols[6]:
                data.append({
                    "Ticker": cols[0],
                    "Owner": cols[1],
                    "Relationship": cols[2],
                    "Date": cols[3],
                    "Transaction": cols[6],
                    "Cost": cols[7],
                    "Shares": cols[8],
                    "Value ($)": value
                })
        except ValueError:
            continue

    return pd.DataFrame(data)

def generate_report(df):
    openai.api_key = OPENAI_API_KEY
    sample_text = df.head(10).to_string(index=False)
    prompt = f"请根据以下 insider 买入数据生成一份中文分析报告：\n{sample_text}\n请写出重点个股、高管、金额，并加入简要点评。"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    return response.choices[0].message["content"]

def send_email(subject, body):
    print("[调试] 准备发送邮件...")
    yag = yagmail.SMTP(EMAIL_USERNAME, EMAIL_PASSWORD)
    yag.send(to=EMAIL_TO, subject=subject, contents=body)
    print("[成功] 邮件已发送。")

if __name__ == "__main__":
    df = fetch_insider_data_from_finviz()
    if df.empty:
        print("无有效 insider buy 数据。")
        send_email("Insider Buy 报告：无数据", "今日未发现有效的 insider 买入记录。")
    else:
        report = generate_report(df)
        send_email("每日 Insider Buy 中文报告", report)
        print("已发送邮件。")
