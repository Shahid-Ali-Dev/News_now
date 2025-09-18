# 📰 NewsNow – Smart News Aggregator

NewsNow is a **Flask-based news aggregator** that fetches and displays the latest headlines from multiple sources:
- [NewsAPI](https://newsapi.org/)
- [GNews API](https://gnews.io/)
- Google News RSS (no API key required)

It supports:
- 🔍 **Search** by keywords
- ⚡ **Caching** for performance (configurable TTL)
- 📰 **Full article view** with text extraction (using Newspaper3k)
- 🖼️ **Images & metadata** from multiple APIs
- 📱 Simple, lightweight frontend with Flask + Jinja2 templates

---

## 🚀 Features
- (Note⚠️: more features and updates are to be added soon)
- Aggregates top 3 popular or recent news articles on homepage.
- Search news articles by keywords.
- Caches results for faster browsing and fewer API calls.
- Estimates reading time for each article.
- Extracts full content of articles (best effort scraping).
- Clean and simple code structure for easy debugging.


---

## 🛠️ Tech Stack
- **Backend:** Flask, Requests, Feedparser, Newspaper3k, BeautifulSoup
- **Frontend:** HTML + Jinja2 templates
- **Database:** (Optional) In-memory cache
- **Other Tools:** dotenv for environment variables

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Shahid-Ali-Dev/News_now.git
cd News_now
