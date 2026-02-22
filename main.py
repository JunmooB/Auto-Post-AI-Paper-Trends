import time
import schedule
import logging
from config import RUN_INTERVAL_SECONDS
from database import init_db, is_paper_processed, mark_paper_processed
from paper_fetcher import fetch_recent_papers
from summarizer import summarize_paper
from slack_bot import post_papers_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def job():
    logger.info("Starting scheduled paper fetch job...")
    
    # 1. Ensure DB is ready
    init_db()
    
    # 2. Fetch recent papers from targeted venues
    papers = fetch_recent_papers(days_back=365, limit_per_venue=50)
    logger.info(f"Fetched {len(papers)} candidate papers.")
    
    processed_count = 0
    papers_to_post = []
    
    for paper in papers:
        paper_id = paper.get('paperId')
        title = paper.get('title')
        
        if not paper_id:
            logger.warning(f"Paper '{title}' has no ID. Skipping.")
            continue
            
        # 3. Check if we already processed it
        if is_paper_processed(paper_id):
            logger.debug(f"Paper '{title}' already processed. Skipping.")
            continue
            
        logger.info(f"Processing new paper: {title}")
        
        # 4. Summarize via LLM
        summary_dict = summarize_paper(paper)
        
        if summary_dict:
            paper['summary_dict'] = summary_dict
            papers_to_post.append(paper)
        else:
            logger.error(f"Failed to generate summary for '{title}'.")
            
    # 5. Post to Slack in batches
    batch_size = 5
    for i in range(0, len(papers_to_post), batch_size):
        batch = papers_to_post[i:i + batch_size]
        success = post_papers_batch(batch)
        
        if success:
            # 6. Mark as processed in DB
            for p in batch:
                mark_paper_processed(p.get('paperId'), p.get('title'))
                processed_count += 1
        else:
            logger.error(f"Failed to post batch of {len(batch)} papers to Slack. Not marking as processed.")
            
    logger.info(f"Job completed. Successfully processed and pushed {processed_count} new papers.")

def main():
    logger.info("Starting AI Paper Slack Bot service...")
    
    # Run once at startup
    job()
    
    # Schedule future runs
    logger.info(f"Scheduling job to run every {RUN_INTERVAL_SECONDS} seconds.")
    schedule.every(RUN_INTERVAL_SECONDS).seconds.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
