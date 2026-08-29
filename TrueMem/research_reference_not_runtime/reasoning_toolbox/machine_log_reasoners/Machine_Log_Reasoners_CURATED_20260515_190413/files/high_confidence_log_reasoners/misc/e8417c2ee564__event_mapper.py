# ONE-SHOT BUILD ADDENDUM - FILE 12

## FILE 12: workers/event_mapper.py

### COPILOT INSTRUCTIONS:
**Create a worker that maps external news events to pattern breaks.**

**PSEUDOCODE:**

```python
"""
Event Mapper Worker
Scrapes news for each pattern break and identifies the causal event.
"""

import requests
from datetime import timedelta
from typing import List, Dict, Any

# You will need a news API key. NewsAPI.org is a good free option.
# Store it in config/default.yaml
# NEWS_API_KEY: "your_api_key_here"

class EventMapper:
    def __init__(self, config):
        """
        INITIALIZE:
        - config: Configuration dictionary with NEWS_API_KEY
        """
        self.api_key = config.get("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2/everything"

    def find_events_for_breaks(self, pattern_breaks: List[Dict[str, Any]], ticker: str) -> List[Dict[str, Any]]:
        """
        FIND CAUSAL EVENTS FOR A LIST OF PATTERN BREAKS:

        INPUT:
            pattern_breaks: List of pattern break dictionaries from patterns.py
            ticker: The stock ticker (e.g., 'MSFT')

        OUTPUT:
            Enriched list of pattern breaks, each with a new 'causal_event' key.

        ALGORITHM:
            enriched_breaks = []
            FOR each p_break in pattern_breaks:
                1. DEFINE search window: timestamp ± 2 days
                2. SEARCH news for ticker within that window
                3. FIND the most relevant article (highest relevance score or closest to timestamp)
                4. CATEGORIZE the article (earnings, product, M&A, legal, etc.)
                5. CREATE causal_event dictionary
                6. ADD causal_event to the pattern break dictionary
                7. APPEND to enriched_breaks

            RETURN enriched_breaks
        """
        enriched_breaks = []
        for p_break in pattern_breaks:
            event = self.search_news_for_break(p_break, ticker)
            p_break['causal_event'] = event
            enriched_breaks.append(p_break)
        return enriched_breaks

    def search_news_for_break(self, pattern_break: Dict[str, Any], ticker: str) -> Dict[str, Any]:
        """
        SEARCH NEWS API FOR A SINGLE PATTERN BREAK:

        ALGORITHM:
            1. GET timestamp from pattern_break
            2. CALCULATE from_date = timestamp - 2 days
            3. CALCULATE to_date = timestamp + 2 days
            4. BUILD query string (e.g., 'MSFT OR Microsoft')
            5. CALL NewsAPI with query, date range, ticker
            6. IF articles are returned:
                   best_article = find_best_article(articles, pattern_break['timestamp'])
                   category = self.categorize_article(best_article['title'], best_article['description'])
                   RETURN {
                       'source': best_article['source']['name'],
                       'headline': best_article['title'],
                       'url': best_article['url'],
                       'timestamp': best_article['publishedAt'],
                       'category': category,
                       'relevance_score': best_article.get('relevance', 0) # Placeholder
                   }
            ELSE:
                RETURN None
        """
        if not self.api_key:
            return None

        # ... (Implementation details for calling NewsAPI)
        pass

    def categorize_article(self, title: str, description: str) -> str:
        """
        CATEGORIZE NEWS ARTICLE BASED ON KEYWORDS:

        ALGORITHM:
            text = (title + ' ' + description).lower()
            IF 'earnings' or 'quarter' or 'revenue' or 'profit' in text:
                RETURN 'Earnings'
            IF 'launches' or 'releases' or 'announces' or 'product' in text:
                RETURN 'Product'
            IF 'acquires' or 'merger' or 'acquisition' or 'buys' in text:
                RETURN 'M&A'
            IF 'lawsuit' or 'sec' or 'doj' or 'investigation' or 'sues' in text:
                RETURN 'Legal'
            IF 'partnership' or 'deal' or 'collaboration' in text:
                RETURN 'Partnership'
            IF 'ceo' or 'cto' or 'cfo' or 'executive' or 'resigns' in text:
                RETURN 'Executive'
            ELSE:
                RETURN 'General'
        """
        # ... (Implementation with more robust keyword matching)
        pass

    def find_best_article(self, articles: List[Dict[str, Any]], break_timestamp: datetime) -> Dict[str, Any]:
        """
        Find the most relevant article from a list.
        For now, just return the first one. A better implementation would score them.
        """
        return articles[0]

```

**COPILOT: Implement using the `requests` library to call the NewsAPI. Add robust error handling for API calls. Use a real news API like NewsAPI.org, and guide the user to get a free developer key.**
