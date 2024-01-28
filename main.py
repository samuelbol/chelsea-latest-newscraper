import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import utc
import os
from keep_alive import keep_alive

HEADER = {
    "User-Agent":
    "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
}

keep_alive()

BOT_TOKEN = os.environ.get('bot_token')
# CHAT_ID = os.environ.get('chat_id')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"


def scrape_cfc_latest_news():
    url = "https://chelseafclatestnews.com/"

    try:
        response = requests.get(url, headers=HEADER, timeout=(10, 27))
        response.raise_for_status()  # Check for HTTP status code errors

        soup = BeautifulSoup(response.content, "html.parser")

        cards = soup.find("div", class_="td-big-grid-wrapper").find_all(
            "div", class_="td-module-thumb")
        news_items = []
        no_news = [
            'chelsea vs', 'live streaming chelsea vs',
            'prediction, betting tips, odds & preview', 'predicted line up',
            'where to watch, tv channel, kick-off time, date'
        ]

        for card in cards:
            itm_title = card.a.get("title", "")
            itm_link = card.a.get("href", "")

            if not itm_title or not itm_link:
                continue

            if any(no_new in itm_title.lower() for no_new in no_news):
                continue

            try:
                with open("../logfile.txt", "r") as file:
                    saved_titles = [
                        line.rstrip("\n") for line in file.readlines()
                    ]
                    if itm_title in saved_titles:
                        continue
            except FileNotFoundError:
                pass

            resp = requests.get(itm_link, headers=HEADER, timeout=(10, 27))
            resp.raise_for_status()  # Check for HTTP status code errors

            soup = BeautifulSoup(resp.content, "html.parser")

            try:
                itm_img = soup.article.find("figure").a.get('href', "")
            except AttributeError:
                itm_img = soup.article.find(
                    "div", class_="td-post-featured-image").a.get('href', "")

            contents = soup.article.find(
                "div",
                class_="td-post-content td-pb-padding-side").find_all("p")
            itm_story = "".join([
                content.get_text(strip=True) + "\n\n" for content in contents[:3]
                if content.get_text(strip=True) != 'See More:'
            ])

            news_items.append({
                "title": itm_title,
                "image": itm_img,
                "contents": itm_story
            })

        return news_items

    except requests.exceptions.RequestException as e:
        print("Error during the request:", e)

    except Exception as ex:
        print("An error occurred:", ex)

    return []


# Function to send news to Telegram
def send_news_to_telegram(article_items):
    for item in article_items:
        title_ = item.get("title", "")
        story_ = item.get("contents", "")
        img_ = item.get("image", "")

        # Check if any of the required data is missing
        if not title_ or not story_:
            print("Skipping item due to missing data.")
            continue

        message = f"🚨 *{title_}*\n\n{story_}\n" \
                  f"🔗 *CFCLatest*\n\n" \
                  f"📲 @JustCFC"
        # print(message)

        try:
            with open("logfile.txt", "r", encoding='utf-8') as file:
                saved_titles = [line.rstrip("\n") for line in file.readlines()]
        except FileNotFoundError:
            saved_titles = []

        if title_ not in saved_titles:
            response = requests.post(BASE_URL + "sendPhoto",
                                     json={
                                         "chat_id": CHAT_ID,
                                         "disable_web_page_preview": False,
                                         "parse_mode": "Markdown",
                                         "caption": message,
                                         "photo": img_
                                     })
            # Check the response status
            if response.status_code == 200:
                print("Message sent successfully.")

                with open("logfile.txt", "a", encoding='utf-8') as file:
                    file.write(f"{title_}\n")

            else:
                print(
                    f"Message sending failed. Status code: {response.status_code}"
                )


def main():
    news_items = scrape_cfc_latest_news()
    send_news_to_telegram(news_items)


scheduler = BlockingScheduler(timezone=utc)
scheduler.add_job(main, "interval", minutes=10)

# scheduler.start()
main()
