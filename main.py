from keep_alive import keep_alive
import pytz
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os

# connection_string = os.environ.get("connection_string")
client = MongoClient(connection_string)

db = client['chelsea_news']
collection = db['cfclatest']

HEADER = {
    "User-Agent":
        "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
}

BOT_TOKEN = os.environ.get("bot_token")
CHAT_ID = os.environ.get("chat_id")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

keep_alive()
nigerian_tz = pytz.timezone("Africa/Lagos")


def scrape_cfc_latest_news():
    url = "https://chelseafclatestnews.com/"

    response = requests.get(url, headers=HEADER, timeout=(10, 27))
    response.raise_for_status()  # Check for HTTP status code errors

    soup = BeautifulSoup(response.content, "html.parser")

    cards = soup.find("div", class_="td-big-grid-wrapper").find_all("div", class_="td-module-thumb")
    news_items = []
    no_news = ['chelsea vs', 'live streaming chelsea vs', 'prediction, betting tips, odds & preview', 'predicted line up', 'where to watch, tv channel, kick-off time, date']

    for card in cards:
        itm_title = card.a.get("title", "")
        itm_link = card.a.get("href", "")

        if not itm_title or not itm_link:
            continue

        if any(no_new in itm_title.lower() for no_new in no_news):
            continue

        resp = requests.get(itm_link, headers=HEADER, timeout=(10, 27))
        resp.raise_for_status()  # Check for HTTP status code errors

        soup = BeautifulSoup(resp.content, "html.parser")

        try:
            itm_img = soup.article.find("figure").a.get('href', "")
        except AttributeError:
            itm_img = soup.article.find("div", class_="td-post-featured-image").a.get('href', "")

        contents = soup.article.find("div", class_="td-post-content td-pb-padding-side").find_all("p")
        itm_story = "".join([content.get_text() + "\n\n" for content in contents[:2] if content.get_text(strip=True) != 'See More:'])

        news_items.append({"title": itm_title, "image": itm_img, "contents": itm_story})

    return news_items


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
                  f"*🔗 CFCLatest*\n\n" \
                  f"📲 @JustCFC"
        # print(message)

        saved_titles = collection.find_one({"text": title_})
        if not saved_titles:
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

                # Insert the text into the collection
                collection.insert_one({"text": title_})
            else:
                print(
                    f"Message sending failed. Status code: {response.status_code}"
                )


def main():
    news_items = scrape_cfc_latest_news()
    send_news_to_telegram(news_items)


scheduler = BlockingScheduler(timezone=nigerian_tz)
scheduler.add_job(main, "interval", minutes=30)

scheduler.start()
# main()
