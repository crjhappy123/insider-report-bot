# Updated version of main.py with improved data fetching, fallback email, and updated read_html usage.

from io import StringIO
import requests
import pandas as pd
import openai
import yagmail
from config import OPENAI_API_KEY, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO

def fetch_insider_data(min_value=50000):
    url = f"http://openinsider.com/screener?s=&o=&vl={min_value}&cnt=100"
    response = requests.get(url)
    
    try:
        tables = pd.read_html(StringIO(response.text))
    except Exception as e:
        print(f"[错误] 无法解析网页表格: {e}")
        return pd.DataFrame()

    # 查找包含 Trade Type 的表
    df = None
    for table in tables:
        if "Trade Type" in table.columns:
            df = table
            break

    if df is None:
        print("[警告] 未找到包含 'Trade Type' 的表格，网页结构可能已变")
        return pd.DataFrame()

    # 精选真实 insider 买入数据
    df = df[df["Trade Type"].str.contains("P - Purchase", na=False)]
    df = df[df["Price"].apply(lambda x: isinstance(x, float) and x > 0)]
    df = df[df["Value ($)"].apply(lambda x: isinstance(x, float) and x > min_value)]
    df = df[df["Title"].str.contains("CEO|Pres|CFO|COO|10%", na=False)]
    return df

def generate_report(df):
    openai.api_key = OPENAI_API_KEY
    sample_text = df.head(10).to_string(index=False)
    prompt = f"请根据以下 insider 买入数据生成一份中文分析报告：\n{sample_text}\n请写出重点个股、高管、金额，并加入简要点评。"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )
    return response.choices[0].message["content"]

def send_email(subject, body):
    print("[调试] 准备发送邮件...")
    yag = yagmail.SMTP(EMAIL_USERNAME, EMAIL_PASSWORD)
    yag.send(to=EMAIL_TO, subject=subject, contents=body)
    print("[成功] 邮件已发送。")

if __name__ == "__main__":
    df = fetch_insider_data()
    if df.empty:
        print("无有效 insider buy 数据。")
        send_email("Insider Buy 报告：无数据", "今日未发现有效的 insider 买入记录。")
    else:
        report = generate_report(df)
        send_email("每日 Insider Buy 中文报告", report)
        print("已发送邮件。")
