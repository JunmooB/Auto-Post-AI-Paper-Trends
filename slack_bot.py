import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Initialize a Web API client
if SLACK_BOT_TOKEN and SLACK_BOT_TOKEN != "dummy_key":
    client = WebClient(token=SLACK_BOT_TOKEN)
else:
    client = None
    logger.warning("SLACK_BOT_TOKEN is not set properly. Slack postings will fail.")

def post_papers_batch(papers_batch: List[Dict[str, Any]]) -> bool:
    """
    Formats the paper data and summaries into Slack Block Kit and posts them.
    A main message is posted to the channel, and detailed summaries are posted in threads.
    """
    if not client:
        logger.error("Slack client is not initialized. Cannot post.")
        return False
        
    if not SLACK_CHANNEL_ID:
        logger.error("SLACK_CHANNEL_ID is not configured.")
        return False

    if not papers_batch:
        return True

    # 1. Build Slack Message Blocks for the Main Channel
    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📚 AI 논문 요약 (총 {len(papers_batch)}건)",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]

    for i, paper in enumerate(papers_batch):
        external_ids = paper.get('externalIds', {})
        doi = external_ids.get('DOI')
        if doi:
            url = f"https://doi.org/{doi}"
        else:
            url = paper.get('url') or f"https://api.semanticscholar.org/CorpusID:{paper.get('paperId')}"
        
        summary_dict = paper.get('summary_dict', {"one_line": "요약 실패", "details": "상세 내용 없음"})
        one_line = summary_dict.get('one_line', '')
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i+1}.* {one_line}\n👉 <{url}|원문 링크(DOI등)>"
            }
        })

    try:
        # Post the main message
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            blocks=blocks,
            text=f"새로운 AI 논문 {len(papers_batch)}건이 도착했습니다."
        )
        ts = response['ts']
        logger.info(f"Successfully posted main message to Slack (ts: {ts}).")
        
        # 2. Post detailed summaries as thread replies
        for i, paper in enumerate(papers_batch):
            title = paper.get('title', 'Unknown Title')
            
            summary_dict = paper.get('summary_dict', {})
            details = summary_dict.get('details', {})
            
            problem = details.get('problem', 'N/A')
            solution = details.get('solution', 'N/A')
            effect = details.get('effect', 'N/A')
            
            safe_title = title[:140] + "..." if len(title) > 140 else title
            
            thread_blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📄 {i+1}. {safe_title}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*문제:* {problem}\n\n*해결:* {solution}\n\n*효과:* {effect}"
                    }
                },
                {"type": "divider"}
            ]
            
            client.chat_postMessage(
                channel=SLACK_CHANNEL_ID,
                thread_ts=ts,
                blocks=thread_blocks,
                text=f"{title} 상세 요약"
            )
            logger.info(f"Posted thread reply for '{title}'.")
            
        return True
    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e.response['error']}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Run main.py for full integration. This script contains Slack posting logic.")
