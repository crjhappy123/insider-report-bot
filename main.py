import requests
import pandas as pd
import openai
import yagmail
from bs4 import BeautifulSoup
from config import OPENAI_API_KEY, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO

def fetch_insider_data(min_value=50000):
    url = f"http://openinsider.com/screener?s=&o=&vl={min_value}&cnt=100"
    response = requests.get(url)

    try:
        tables = pd.read_html(response.text)
    except Exception as e:
        print(f"[错误] 读取网页失败：{e}")
        return pd.DataFrame()

    # 找包含 "Trade Type" 的表格（更稳健）
    df = None
    for table in tables:
        if "Trade Type" in table.columns:
            df = table
            break

    if df is None:
        print("[警告] 未找到包含 'Trade Type' 的表格，网页结构可能已变")
        return pd.DataFrame()

    # 保留真实买入 + 有价格 + 高管身份 + 金额大
    df = df[df["Trade Type"].str.contains("P - Purchase", na=False)]
    df = df[df["Price"].apply(lambda x: isinstance(x, float) and x > 0)]
    df = df[df["Value ($)"].apply(lambda x: isinstance(x, float) and x > min_value)]
    df = df[df["Title"].str.contains("CEO|Pres|CFO|COO|10%", na=False)]
    return df

def generate_report(df):
    openai.api_key = OPENAI_API_KEY
    sample_text = df.head(10).to_string(index=False)
    prompt = f"请根据以下内部人买入数据生成一份中文分析报告：\n{sample_text}\n请用中文写，包含重点推荐理由和分析。"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )
    return response.choices[0].message["content"]

def send_email(subject, body):
    yag = yagmail.SMTP(EMAIL_USERNAME, EMAIL_PASSWORD)
    yag.send(to=EMAIL_TO, subject=subject, contents=body)

if __name__ == "__main__":
    df = fetch_insider_data()
    if df.empty:
        print("无有效 insider buy 数据。")
        send_email("Insider Buy 报告：无数据", "今日未发现有效的 insider 买入记录。")
    else:
        report = generate_report(df)
        send_email("每日 Insider Buy 中文报告", report)
        print("已发送邮件。")
