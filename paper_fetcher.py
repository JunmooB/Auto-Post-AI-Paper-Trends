import requests
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from config import TARGET_VENUES, S2_API_KEY

logger = logging.getLogger(__name__)

# Semantic Scholar Graph API endpoint
S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

def fetch_recent_papers(days_back: int = 7, limit_per_venue: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches recent papers from the targeted venues using the Semantic Scholar API.
    Note: The Semantic Scholar API does not have an exact "venue" and "date range"
    filter in the standard search endpoint that perfectly guarantees 100% precision.
    We will query by venue string and filter by year, then manually filter dates if needed.
    """
    
    # Calculate target year range based on days_back
    current_date = datetime.now()
    current_year = current_date.year
    start_year = (current_date - timedelta(days=days_back)).year
    
    year_param = f"{start_year}-{current_year}" if start_year != current_year else str(current_year)
    
    all_papers = []
    
    # S2 API has rate limits (100 req/ 5 min without API key)
    # Be gentle with requests.
    
    headers = {
        "User-Agent": "Auto-AI-Paper-Bot/1.0 (mailto:test-bot@example.com)"
    }
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    
    for venue in TARGET_VENUES:
        logger.info(f"Fetching recent papers for venue: {venue}")
        
        # We query the venue specifically.
        params = {
            "query": venue,
            "year": year_param,
            "fields": "paperId,title,abstract,authors,venue,year,url,publicationDate,externalIds,tldr",
            "limit": min(limit_per_venue * 3, 100) # Fetch up to maximum allowed (100) to filter client-side
        }
        
        try:
            # Simple retry loop for 429 errors
            success = False
            for attempt in range(5):
                response = requests.get(S2_API_URL, params=params, headers=headers, timeout=10)
                
                # Handle 403 Forbidden (Invalid or unapproved API Key)
                if response.status_code == 403 and "x-api-key" in headers:
                    logger.warning(f"S2 API Key is invalid or unauthorized (403) for {venue}. Falling back to unauthenticated requests...")
                    del headers["x-api-key"]
                    # Retry immediately without the key
                    response = requests.get(S2_API_URL, params=params, headers=headers, timeout=10)

                if response.status_code == 429:
                    wait_time = 10 * (2 ** attempt) # 10, 20, 40, 80, 160
                    logger.warning(f"Rate limited (429) for {venue}. Sleeping for {wait_time} seconds (Attempt {attempt+1}/5)...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                papers_data = data.get("data", [])
                valid_papers = []
                
                for p in papers_data:
                    # Semantic Scholar sometimes returns papers where 'venue' string doesn't exactly match
                    p_venue = p.get("venue", "") or ""
                    p_title = p.get("title", "") or ""
                    
                    # Strict check: The venue must clearly match our target, 
                    # or the title should explicitly state the conference name + year.
                    is_valid_venue = False
                    
                    if venue.lower() in p_venue.lower():
                        is_valid_venue = True
                    else:
                        # Many ML conferences don't have a clean venue string right away, they might just have it in the title
                        for y in range(start_year, current_year + 1):
                            if f"{venue} {y}" in p_title or f"{venue}{y}" in p_title:
                                is_valid_venue = True
                                break
                        
                    if not is_valid_venue:
                        continue
                        
                    # Check publication date if available (format: YYYY-MM-DD)
                    pub_date_str = p.get("publicationDate")
                    if pub_date_str:
                        try:
                            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
                            diff = datetime.now() - pub_date
                            # Give a grace period.
                            if diff.days <= days_back + 30: # Papers might be published/indexed with a delay
                                valid_papers.append(p)
                        except ValueError:
                            valid_papers.append(p) # Include if date is malformed but year matches
                    else:
                        valid_papers.append(p) # include if no precise date, relying on year filter
                    
                # Sort by publication date descending and take top N
                def date_key(x):
                    d = x.get("publicationDate")
                    return d if d else f"{current_year}-01-01"
                    
                valid_papers.sort(key=date_key, reverse=True)
                all_papers.extend(valid_papers[:limit_per_venue])
                
                # Success, break retry loop
                success = True
                break
                
            if not success:
                logger.error(f"Failed to fetch for {venue} after 5 attempts due to rate limits.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from Semantic Scholar for {venue}: {e}")
            
        # Global sleep between venue queries to respect rate limits
        sleep_time = 1 if S2_API_KEY else 10
        time.sleep(sleep_time)
            
    return all_papers

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    papers = fetch_recent_papers(days_back=7, limit_per_venue=2)
    print(f"Fetched {len(papers)} papers.")
    for p in papers:
        print(f"- {p['title']} ({p.get('venue')}) - {p.get('publicationDate')}")
