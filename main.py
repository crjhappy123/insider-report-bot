import requests
import pandas as pd
import openai
import yagmail
from config import OPENAI_API_KEY, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO

def fetch_insider_data_from_openinsider(min_value=50000):
    url = (
        "http://openinsider.com/screener?"
        "s=&o=&pl=&ph=&ll=&lh=&fd=1&td=0&xp=1"
        "&vl=50000&vh=&oc=buy&sic1=&sic2=&sortcol=0"
        "&maxresults=1000&numresults=1000&typ=1&del=1&fmt=csv"
    )
    try:
        df = pd.read_csv(url)
        df = df[df['Transaction Type'].str.contains("P - Purchase", na=False)]
        df = df[df['Value ($)'] >= min_value]
        return df
    except Exception as e:
        print(f"[错误] 获取或解析数据失败: {e}")
        return pd.DataFrame()

def generate_report(df):
    openai.api_key = OPENAI_API_KEY
    sample_text = df[['Ticker', 'Owner', 'Title', 'Trade Date', 'Price', 'Qty', 'Value ($)']].head(10).to_string(index=False)
    prompt = (
        f"请根据以下 insider 买入数据生成一份简明中文分析报告：\n\n{sample_text}\n\n"
        f"请写出重点股票、职位、买入金额，并用简洁的口吻总结可能影响市场的动向。"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"[错误] 调用 ChatGPT 失败：{e}"

def send_email(subject, body):
    print("[调试] 准备发送邮件...")
    yag = yagmail.SMTP(EMAIL_USERNAME, EMAIL_PASSWORD)
    yag.send(to=EMAIL_TO, subject=subject, contents=body)
    print("[成功] 邮件已发送。")

if __name__ == "__main__":
    df = fetch_insider_data_from_openinsider()
    if df.empty:
        print("无有效 insider buy 数据。")
        send_email("Insider Buy 报告：无数据", "今日未发现有效的 insider 买入记录。")
    else:
        report = generate_report(df)
        send_email("每日 Insider Buy 中文报告", report)
        print("已发送邮件。")
