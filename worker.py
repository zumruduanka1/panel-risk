import requests, random, os
from redis import Redis
from rq import Queue
from db import get_conn
from model import ai_score

redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=redis_conn)

def fetch_data():
    data = [
        "SON DAKİKA: deprem hakkında şok iddia!",
        "aşı ile ilgili gizli gerçek ortaya çıktı",
        "herkes bunu konuşuyor dikkat edin"
    ]

    conn = get_conn()
    cur = conn.cursor()

    for text in data:
        risk = ai_score(text)

        cur.execute(
            "INSERT INTO news(text,risk,source,link) VALUES(%s,%s,%s,%s)",
            (text, risk, "Sosyal", "#")
        )

    conn.commit()
    cur.close()
    conn.close()

def start_worker():
    while True:
        q.enqueue(fetch_data)