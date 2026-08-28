# ONE-SHOT BUILD ADDENDUM - FILE 13

## FILE 13: workers/social_tracker.py

### COPILOT INSTRUCTIONS:
**Create a worker that tracks social media for early signals.**

**PSEUDOCODE:**

```python
"""
Social Tracker Worker
Monitors Twitter/Reddit for early signals from identified leaders.
"""

# You will need Twitter API v2 (or other social media API) keys.
# Store them in config/default.yaml
# TWITTER_BEARER_TOKEN: "your_bearer_token"

import requests
from typing import List, Dict, Any

class SocialTracker:
    def __init__(self, config):
        """
        INITIALIZE:
        - config: Configuration dictionary with TWITTER_BEARER_TOKEN
        - social_leaders: List of Twitter user IDs to track
        """
        self.bearer_token = config.get("TWITTER_BEARER_TOKEN")
        self.base_url = "https://api.twitter.com/2/"
        self.social_leaders = config.get("SOCIAL_LEADERS", []) # e.g., ["JohnEDeaton1", "attorneyjeremy"]

    def find_early_signals(self, causal_event: Dict[str, Any], ticker: str) -> List[Dict[str, Any]]:
        """
        FIND EARLY SOCIAL SIGNALS FOR A CAUSAL EVENT:

        INPUT:
            causal_event: A causal event dictionary from EventMapper
            ticker: The stock ticker

        OUTPUT:
            List of social media posts (tweets) that preceded the event.

        ALGORITHM:
            1. GET timestamp from causal_event
            2. DEFINE search window: timestamp - 7 days to timestamp
            3. FOR each leader in self.social_leaders:
                   SEARCH for tweets from that leader mentioning the ticker in the search window
                   ADD any found tweets to a list
            4. RETURN the list of tweets
        """
        if not self.bearer_token or not causal_event:
            return []

        # ... (Implementation for calling Twitter API v2)
        pass

    def monitor_live_feed(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        MONITOR LIVE SOCIAL MEDIA FEED FOR KEYWORDS:

        INPUT:
            keywords: List of keywords to track (e.g., ["XRP", "SEC", "Ripple"])

        OUTPUT:
            Stream of real-time tweets matching the keywords.
            (For a real implementation, this would be a generator or callback)

        ALGORITHM:
            1. USE Twitter API v2 filtered stream endpoint
            2. SET up rules to track keywords from social leaders
            3. YIELD tweets as they arrive
        """
        # ... (Implementation for Twitter filtered stream)
        pass

```

**COPILOT: Implement using the `requests` library to call the Twitter API v2. Focus on the `find_early_signals` function for now. The live feed is a more advanced feature for later.**
