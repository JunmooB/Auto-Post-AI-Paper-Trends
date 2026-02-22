import logging
from openai import OpenAI
from typing import Dict, Any, Optional
from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# Initialize OpenAI client with base URL for compatibility with other providers like vLLM, Ollama, etc.
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

def summarize_paper(paper_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Takes paper metadata (title, abstract) and requests an LLM
    to summarize the key technologies.
    """
    title = paper_data.get('title', 'Unknown Title')
    abstract = paper_data.get('abstract', '')
    venue = paper_data.get('venue', 'Unknown Venue')
    
    tldr_data = paper_data.get('tldr', {})
    tldr_text = tldr_data.get('text', '') if isinstance(tldr_data, dict) else ''
    
    if not abstract and not tldr_text:
        logger.warning(f"Paper '{title}' has no abstract or tldr. Will attempt to summarize based on title only.")
        abstract = "(초록 제공되지 않음. 제목을 바탕으로 추론하여 작성할 것)"
        
    doi = paper_data.get('externalIds', {}).get('DOI', 'N/A')
    url = paper_data.get('url', '')
    link_info = f" (DOI: {doi})" if doi != 'N/A' else (f" (URL: {url})" if url else "")
    
    prompt = f"""
당신은 바쁜 개발자들을 위해 AI 논문의 핵심만 10초 만에 파악할 수 있도록 요약해주는 봇입니다.
독자들은 긴 글을 읽지 않으므로, 최대한 짧은 단어와 개조식 문장(~함, ~임)으로 직관적으로 요약하세요.
반드시 한국어로 작성하세요.

[중요: Slack mrkdwn 포맷팅 규칙]
Slack API를 통해 전송되므로 일반 마크다운 대신 아래 규칙만 절대적으로 지키세요:
1. 굵은 글씨(Bold): 반드시 별표 한 개 사용 (*단어*) - 절대 별표 두 개(**)를 쓰지 마세요.
   - 단, 문장 전체를 굵게 처리하면 절대 안 됩니다! 핵심이 되는 1~2개 키워드에만 굵은 글씨를 적용하세요.
2. 글머리 기호(List): 하이픈과 띄어쓰기 사용 (- 텍스트)
3. 헤딩(Heading): # 기호를 쓰지 마세요.

출력 형식은 정확히 다음을 따르세요:

ONE_LINE:
[논문의 가장 핵심적인 가치를 비유나 직관적인 표현을 써서 아주 짧은 한 줄로 작성하되, 핵심 키워드 1~2개만 *강조* 할 것]

QUICK_SUMMARY:
- 문제: [기존의 한계나 풀고자 한 문제 (문장 전체 볼드 금지, 핵심 단어만 *볼드*)]
- 해결: [어떤 기술을 썼는지 (문장 전체 볼드 금지, 핵심 단어만 *볼드*)]
- 효과: [이로 인해 얻게 된 결과나 실질적인 이점 (문장 전체 볼드 금지, 핵심 단어만 *볼드*)]

Paper Title: {title}
TLDR (Author/AI Summary): {tldr_text}
Abstract: {abstract}
"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful and expert AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse output
        one_line = ""
        details = ""
        if "ONE_LINE:" in content and "QUICK_SUMMARY:" in content:
            parts = content.split("QUICK_SUMMARY:")
            one_line = parts[0].replace("ONE_LINE:", "").strip()
            
            # parse the problem, solution, effect
            details_str = parts[1].strip()
            problem, solution, effect = "", "", ""
            for line in details_str.split('\n'):
                line = line.strip()
                if "문제" in line:
                    problem = line.split(":", 1)[1].strip() if ":" in line else line
                elif "해결" in line:
                    solution = line.split(":", 1)[1].strip() if ":" in line else line
                elif "효과" in line:
                    effect = line.split(":", 1)[1].strip() if ":" in line else line
            details = {"problem": problem, "solution": solution, "effect": effect}
        else:
            # Fallback
            one_line = content[:100] + "..."
            details = {"problem": "N/A", "solution": "N/A", "effect": "N/A"}
            
        return {"one_line": one_line, "details": details}
        
    except Exception as e:
        logger.error(f"Error summarizing paper '{title}': {e}")
        return None

if __name__ == "__main__":
    # Test execution
    logging.basicConfig(level=logging.INFO)
    test_paper = {
        "title": "Attention Is All You Need",
        "venue": "NeurIPS",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train."
    }
    
    logger.info("Testing summarizer (Make sure OPENAI_API_KEY is set in your environment)...")
    res = summarize_paper(test_paper)
    if res:
        print(f"\nSummary:\n{res}")
