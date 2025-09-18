import os
from dateutil import parser 
import time
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, abort
import requests
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from newspaper import Article



load_dotenv()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Config - read your API keys from environment variables
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')   # https://newsapi.org/
GNEWS_KEY = os.getenv('GNEWS_KEY')       # https://gnews.io/

# In-memory cache: simple dict storing {'articles': [...], 'ts': timestamp}
CACHE = {}
articles_cache = []
CACHE_TTL = int(os.getenv('CACHE_TTL_SEC', 300))  # 5 min default

QUERY = "Jamshedpur Jharkhand"

def cache_get():
    entry = CACHE.get('articles')
    if not entry:
        return None
    ts = entry.get('ts', 0)
    if time.time() - ts > CACHE_TTL:
        return None
    return entry.get('data')

def cache_set(data):
    CACHE['articles'] = {'data': data, 'ts': time.time()}

def safe_excerpt(text, length=180):
    if not text:
        return ""
    s = BeautifulSoup(text, "html.parser").get_text()
    return (s[:length].rsplit(' ', 1)[0] + '...') if len(s) > length else s

def fetch_from_newsapi(q=QUERY):
    # Using NewsAPI everything endpoint (sortBy=popularity) to attempt to get top by popularity
    if not NEWSAPI_KEY:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": q,
        "pageSize": 10,
        "sortBy": "popularity",  # popularity ranking
        "language": "en",
        "apiKey": NEWSAPI_KEY,
    }
    r = requests.get(url, params=params, timeout=8)
    r.raise_for_status()
    js = r.json()
    articles = js.get('articles', [])
    result = []
    for a in articles:
        result.append({
            "id": hashlib.sha1((a.get('url','') or a.get('title','')).encode()).hexdigest(),
            "title": a.get('title'),
            "source": a.get('source', {}).get('name'),
            "url": a.get('url'),
            "image": a.get('urlToImage'),
            "publishedAt": a.get('publishedAt'),
            "content": a.get('content') or a.get('description'),
            "description": a.get('description'),
        })
    return result

def fetch_from_gnews(q=QUERY):
    # GNews API fallback
    if not GNEWS_KEY:
        return []
    url = "https://gnews.io/api/v4/search"
    params = {"q": q, "lang":"en", "max":10, "token": GNEWS_KEY}
    r = requests.get(url, params=params, timeout=8)
    r.raise_for_status()
    js = r.json()
    articles = js.get('articles', [])
    result = []
    for a in articles:
        result.append({
            "id": hashlib.sha1((a.get('url','') or a.get('title','')).encode()).hexdigest(),
            "title": a.get('title'),
            "source": a.get('source', {}).get('name'),
            "url": a.get('url'),
            "image": a.get('image'),
            "publishedAt": a.get('publishedAt'),
            "content": a.get('content') or a.get('description'),
            "description": a.get('description'),
        })
    return result

def fetch_from_google_rss(q=QUERY):
    # Google News RSS search (no API key)
    # Construct a Google News search RSS feed URL for the query and India region
    q_encoded = q.replace(' ', '+')
    rss_url = f"https://news.google.com/rss/search?q={q_encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    d = feedparser.parse(rss_url)
    result = []
    for entry in d.entries[:15]:
        published = getattr(entry, 'published', None) or getattr(entry, 'updated', None)
        content = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
        result.append({
            "id": hashlib.sha1((entry.link or entry.title).encode()).hexdigest(),
            "title": entry.title,
            "source": getattr(entry, 'source', {}).get('title') if getattr(entry, 'source', None) else None,
            "url": entry.link,
            "image": None,
            "publishedAt": published,
            "content": content,
            "description": content
        })
    return result

def get_articles():
    # 1) Check cache
    cached = cache_get()
   

    if cached:
        return cached

    # 2) Try APIs in preferred order
    articles = []
    try:
        articles = fetch_from_newsapi()
    except Exception:
        articles = []
    if not articles:
        try:
            articles = fetch_from_gnews()
        except Exception:
            articles = []
    if not articles:
        try:
            articles = fetch_from_google_rss()
        except Exception:
            articles = []

    # Normalize publishedAt -> datetime
    for a in articles:
        try:
            if a.get('publishedAt'):
                a['_dt'] = datetime.fromisoformat(a['publishedAt'].replace('Z','+00:00'))
            else:
                a['_dt'] = datetime.utcnow()
        except Exception:
            try:
                a['_dt'] = datetime.strptime(a.get('publishedAt',''), "%a, %d %b %Y %H:%M:%S %Z")
            except Exception:
                a['_dt'] = datetime.utcnow()

        a['publishedFormatted'] = format_datetime(a.get('publishedAt'))

    # Sort by datetime desc (most recent) but we originally tried to request by popularity.
    # Since the user asked top 3 popular, we keep the server-provided order when possible.
    # If API didn't provide popularity ordering, fallback to most recent.
    # We'll trust the provider order when it's non-empty (we preserve the current order).
    # Deduplicate by URL/title
    unique = {}
    filtered = []
    for a in articles:
        key = (a.get('url') or a.get('title') or '')[:180]
        if key in unique:
            continue
        unique[key] = True
        filtered.append(a)

    # Keep top 10 items
    filtered = filtered[:10]

    cache_set(filtered)
    return filtered

def find_article_by_id(article_id):
    arts = get_articles()
    for a in arts:
        if a['id'] == article_id:
            # try fetch full content by scraping the url (best-effort)
            if a.get('content') and len(BeautifulSoup(str(a['content']), "html.parser").get_text()) > 80:
                return a
            # otherwise attempt to scrape the article url for more content
            try:
                r = requests.get(a['url'], timeout=8, headers={"User-Agent":"Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")
                # common article selectors
                article_body = soup.find('article') or soup.find('div', {"class":"article-body"}) or soup.body
                txt = article_body.get_text(separator="\n\n").strip()
                a['content'] = txt[:4000]
            except Exception:
                pass
            return a
    return None

@app.context_processor
def inject_now():
    return {'datetime': datetime}

def estimate_reading_time(text):
    if not text:
        return "1 min"
    words = len(BeautifulSoup(str(text), "html.parser").get_text().split())
    mins = max(1, int(words / 200))
    return f"{mins} min read"



def format_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        # Parse any kind of date string (ISO, RFC822, etc.)
        dt = parser.parse(dt_str)
        # Convert to local time if you want, or keep UTC
        return dt.strftime("%b %d, %Y %I:%M %p")  # Example: Aug 25, 2025 06:19 PM
    except Exception:
        return dt_str

@app.route("/")
def index():
    global articles_cache
    q = request.args.get("q", QUERY)

    # Use your unified fetcher
    articles = get_articles()

    # Keep top 3 only
    articles_cache = articles[:3]

    return render_template("index.html", articles=articles_cache, title="Home")



@app.route("/article/<int:index>")
def article(index):
    global articles_cache
    if index < len(articles_cache):
        article = articles_cache[index]

        try:
            # Use newspaper3k to extract clean article
            news_article = Article(article["url"])
            news_article.download()
            news_article.parse()

            # Update the content with clean extracted text
            article["content"] = news_article.text if news_article.text else article.get("description", "Content unavailable")

            # Also grab image if available
            if news_article.top_image:
                article["image"] = news_article.top_image

        except Exception as e:
            print("Article extraction failed:", e)
            article["content"] = article.get("description", "Content unavailable")

        return render_template("article.html", article=article, title=article["title"])
    return "Article not found", 404




@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('index'))
    # Basic search: fetch articles and filter locally by query
    arts = get_articles()
    qlow = q.lower()
    matched = [a for a in arts if (a.get('title','').lower().find(qlow) != -1) or (a.get('description','') and a.get('description','').lower().find(qlow) != -1)]
    # show top 10 matched
    for a in matched:
        a['excerpt'] = safe_excerpt(a.get('description') or a.get('content'), 200)
    return render_template('search.html', articles=matched[:10], q=q)

if __name__ == '__main__':
    app.run(debug=True, port=int(os.getenv('PORT', 5000)))
