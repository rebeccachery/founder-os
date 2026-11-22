"""Shared domain lists for search-layer filtering.

Lives under lib/search (not lib/opportunities) because it's used by the
generic multi-provider search client itself — every agent that searches
benefits from never seeing these back, not just funding_scout's intake flow.
"""

# Social-feed/post hosts — never a program's own application page, and never
# useful as a search result regardless of which agent is searching.
SOCIAL_HOSTS = (
    "twitter.com",
    "x.com",
    "t.co",
    "mobile.twitter.com",
    "instagram.com",
    "facebook.com",
    "m.facebook.com",
    "tiktok.com",
)
