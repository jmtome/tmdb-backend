# Cache TTL Configuration (in seconds)
# This file centralizes all cache time-to-live settings for easy management

# List endpoints - these change frequently and need different refresh rates
LIST_ENDPOINTS_TTL = {
    "popular": 1800,        # 30 minutes - moderate freshness needed
    "now_playing": 3600,    # 1 hour - fairly stable content
    "upcoming": 21600,      # 6 hours - stable, planned releases
    "trending": 600,        # 10 minutes - highly dynamic content
}

# Detail endpoints - these change less frequently
DETAIL_ENDPOINTS_TTL = {
    "movie_detail": 7200,   # 2 hours - movie info rarely changes
    "actor_detail": 21600,  # 6 hours - actor bios/filmography update slowly
    "movie_images": 86400,  # 24 hours - images rarely change once uploaded
    "movie_reviews": 7200,  # 2 hours - reviews don't change very frequently
}

# Search endpoints - balance between freshness and performance
SEARCH_ENDPOINTS_TTL = {
    "movie_search": 3600,   # 1 hour - search relevance can change
    "tv_search": 3600,      # 1 hour - search relevance can change
}

# Utility function to get TTL by endpoint type and key
def get_ttl(endpoint_type, key=None):
    """
    Get TTL for a specific endpoint
    
    Args:
        endpoint_type: 'list', 'detail', or 'search'
        key: specific endpoint key (e.g., 'popular', 'movie_detail')
    
    Returns:
        TTL in seconds, or None if not found
    """
    ttl_maps = {
        'list': LIST_ENDPOINTS_TTL,
        'detail': DETAIL_ENDPOINTS_TTL,
        'search': SEARCH_ENDPOINTS_TTL,
    }
    
    if endpoint_type in ttl_maps and key in ttl_maps[endpoint_type]:
        return ttl_maps[endpoint_type][key]
    
    return None

# Default TTL fallback (1 hour)
DEFAULT_TTL = 3600 