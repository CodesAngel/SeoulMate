# Settings shared by the scrape steps.

# Which dramas Step 1 downloads and refreshes, by the origin word MyDramaList shows in
# listing pages ("Korean Drama - 2026, 16 episodes" -> "Korean"). Add more to include them
# later, e.g. ["Korean", "Chinese", "Japanese"]; None downloads every country. Listing rows
# without that info are kept, so a drama is never skipped just because the listing was odd.
INCLUDE_ORIGINS = ["Korean"]

# Nightly refresh (run_pipeline.py --refresh) defaults.
REFRESH_LISTING_PAGES = 5  # first N pages of each listing source
REFRESH_MAX_FETCH = 300  # drama pages per run, new ones first

# How often an already-saved drama page is re-downloaded, in days, by its air state.
REFRESH_DAYS = {
    "airing": 1,
    "upcoming": 7,
    "recently_ended": 7,  # ended within RECENTLY_ENDED_DAYS; ratings still settling
    "broken": 7,  # saved page Step 2 couldn't parse
    "completed": 90,
}
RECENTLY_ENDED_DAYS = 60
# "Jul 11, 2010 - ?" has no end date; after this many days it's treated as completed.
OPEN_ENDED_AIRING_DAYS = 365


def origin_of(media_info):
    """'Korean Drama - 2026, 16 episodes' -> 'Korean'; '' when the listing had no info."""
    text = str(media_info or "").strip()
    if not text or text.upper() == "N/A":
        return ""
    return text.split()[0]


def is_included(media_info):
    if INCLUDE_ORIGINS is None:
        return True
    origin = origin_of(media_info)
    return origin == "" or origin in INCLUDE_ORIGINS
