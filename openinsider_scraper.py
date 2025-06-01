import csv
import os
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import pandas as pd
import requests
from retry import retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENINSIDER_URL = "http://openinsider.com/screener.csv"

class OpenInsiderScraper:
    def __init__(self):
        self.today = datetime.today().strftime('%Y-%m-%d')
        self.email_config = {
            "sender": os.getenv("EMAIL_USERNAME"),
            "password": os.getenv("EMAIL_PASSWORD"),
            "recipient": os.getenv("EMAIL_TO")
        }
        self.filename = f"insider_trades_{self.today}.csv"

    @retry(tries=3, delay=5)
    def download_csv(self):
        logger.info("Downloading insider trade data from OpenInsider...")
        response = requests.get(OPENINSIDER_URL)
        if response.status_code != 200:
            raise Exception(f"Failed to download data. Status code: {response.status_code}")

        with open(self.filename, 'w', newline='', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"Saved insider trades to {self.filename}")

    def filter_buys(self) -> pd.DataFrame:
        logger.info("Filtering for BUY transactions...")
        df = pd.read_csv(self.filename)
        df = df[df['Transaction'].str.strip().str.lower() == 'buy']
        df = df.sort_values(by='Value ($)', ascending=False)
        df = df.reset_index(drop=True)
        return df

    def format_report(self, df: pd.DataFrame) -> str:
        logger.info("Formatting email report...")
        if df.empty:
            return "今天没有发现 insider 买入交易。"

        lines = [
            f"日期: {self.today}",
            f"发现 {len(df)} 笔 insider 买入交易:",
            ""
        ]
        for _, row in df.iterrows():
            lines.append(
                f"{row['Ticker']} | {row['Owner']} ({row['Relationship']}) | {row['Date']} | 买入 {row['#Shares']} 股 @ ${row['Cost']} | 价值 ${row['Value ($)']}"
            )
        return "\n".join(lines)

    def send_email(self, content: str):
        logger.info("Sending email report...")
        sender = self.email_config["sender"]
        recipient = self.email_config["recipient"]
        password = self.email_config["password"]

        if not all([sender, recipient, password]):
            raise ValueError("Missing email credentials in environment variables.")

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"每日Insider买入报告 - {self.today}"

        msg.attach(MIMEText(content, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            logger.info("Email sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")

    def run(self):
        try:
            self.download_csv()
            df_buys = self.filter_buys()
            report = self.format_report(df_buys)
            self.send_email(report)
        except Exception as e:
            logger.error(f"Critical error: {e}")

if __name__ == '__main__':
    scraper = OpenInsiderScraper()
    scraper.run()
