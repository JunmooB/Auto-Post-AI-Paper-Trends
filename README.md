# 🤖 AI Paper Slack Bot

AI Paper Slack Bot은 최신 AI 기술 트렌드를 놓치지 않기 위해, 지정된 톱 티어(Top-tier) 학회 및 저널의 논문들을 자동으로 수집하고, 대규모 언어 모델(LLM)을 통해 핵심 기술을 요약하여 Slack 채널로 배달해 주는 자동화 파이프라인입니다.

## 🎯 Target Venues (모니터링 대상)
- **Computer Vision (CV)**: CVPR, ICCV, ECCV
- **Machine Learning**: NeurIPS, ICML, ICLR
- **Natural Language Processing (NLP)**: ACL, EMNLP, NAACL

---

## 🔄 Workflow Architecture

이 애플리케이션의 핵심 워크플로우는 다음과 같습니다. 메인 오케스트레이터(`main.py`)가 정해진 간격마다 이 프로세스를 무한히 반복합니다.

```mermaid
graph TD
    A([스케줄러 시작<br/>지정된 시간 간격]) --> B[Semantic Scholar API 호출<br/>최신 논문 검색 및 필터링]
    B --> C{가져온 논문 목록 순회<br/>SQLite DB 존재 여부 확인}
    
    C -- "이미 처리됨 (중복)" --> D[스킵 (건너뛰기)]
    C -- "새로운 논문" --> E[LLM API 호출<br/>논문 초록 기반 핵심 기술 요약]
    
    E --> F[Slack API 호출<br/>Block Kit을 활용한 메시지 포스팅]
    
    F -- "전송 성공" --> G[(SQLite DB에<br/>해당 Paper ID 저장)]
    F -- "전송 실패" --> H[에러 로깅 후 DB 저장 생략]
    
    D --> I[다음 논문으로 이동]
    G --> I
    H --> I
    
    I --> J{다음 논문이<br/>남아있는가?}
    J -- "Yes" --> C
    J -- "No" --> K([루프 종료<br/>다음 스케줄까지 대기])
```

### 상세 워크플로우 설명
1. **Fetch (수집)**: `paper_fetcher.py`가 [Semantic Scholar API](https://www.semanticscholar.org/product/api)를 호출합니다. 지정된 학회 이름과 동적으로 계산된 연도 범위(기본 최근 ?일)를 기반으로 검색하며, API의 Rate Limit 방지를 위해 지수 백오프(Exponential Backoff) 로직이 적용되어 있습니다. 수집 시, AI 요약본인 `tldr` 필드도 함께 가져와 요약 품질을 높입니다.
2. **Filter & Deduplicate (필터링 및 중복제거)**: 수집된 논문이 타겟 학회 논문인지 다년간의 연도에 걸쳐 유연하게 검증하고, `database.py` 시스템을 통해 이미 Slack에 업로드된 적이 있는 논문인지 (DB 기반) 검사합니다.
3. **Summarize (요약)**: `summarizer.py`가 OpenAI 호환 API (OpenAI 본가, vLLM, Ollama 등)를 사용하여 논문을 비전문가도 10초 만에 파악할 수 있도록 요약합니다. 초록(Abstract)이 없어도 `tldr`이나 제목을 기반으로 추론하며, 과도한 Bold 처리를 방지하여 가독성을 높였습니다.
4. **Publish (발행)**: `slack_bot.py`가 요약된 데이터를 가장 안전하고 깔끔한 형태인 **Slack Block Kit**을 이용하여 포스팅합니다. 
   - 메인 채널: 직관적인 한 줄 요약과 **DOI 기반 원문 링크**를 제공
   - 스레드(Thread): 각 논문의 자세한 분석(문제, 해결, 효과)을 **가독성 높은 헤더 및 구분선 블록** 형태로 발송
   - 전송 성공 시에만 DB(`processed_papers`)에 논문 ID를 안전하게 기록하여 재시도를 보장합니다.

---

## 📂 Project Structure

- `main.py`: 전체 파이프라인을 제어하고 스케줄링(기본 24시간)하는 메인 오케스트레이션 스크립트입니다.
- `config.py`: `.env` 파일로부터 환경 변수를 로드하고 전역 설정값을 관리합니다.
- `paper_fetcher.py`: Semantic Scholar API와 통신하여 논문 데이터를 수집합니다.
- `database.py`: 로컬 SQLite DB(`papers.db`)를 관리하여 중복 발송을 제어합니다.
- `summarizer.py`: OpenAI 호환 LLM API와 통신하여 요약본을 생성합니다.
- `slack_bot.py`: 요약된 데이터를 Slack 메시지 템플릿(Block Kit)으로 변환 후 전송합니다.
- `Dockerfile` & `docker-compose.yml`: 백엔드 봇 컨테이너 및 DB 뷰어(`sqlite-web`)를 띄우기 위한 설정 파일입니다.

---

## 🚀 Getting Started

프로젝트를 실행하려면 `Docker`와 `docker-compose`가 설치되어 있어야 합니다.

1. **환경 변수 템플릿 복사 및 설정**
   ```bash
   cp .env.example .env
   # .env 파일을 열어 Slack Token, Channel ID, OpenAI API Key 등 필수 정보를 입력하세요.
   ```

2. **Docker Compose를 통한 백그라운드 서버 실행**
   ```bash
   docker compose up --build -d
   ```
   > 💡 코드 변경 사항이 있을 시 재실행을 위해 항상 `--build` 플래그를 사용하는 것을 권장합니다.

3. **작동 확인 및 로그 모니터링**
   ```bash
   docker logs -f ai-paper-bot
   ```

4. **처리된 논문 DB GUI 확인 (sqlite-web)**
   - 컨테이너가 실행된 후, 브라우저에서 `http://localhost:8080` 에 접속하세요.
   - `processed_papers` 테이블에서 지금까지 성공적으로 슬랙에 배달도 완료되고 중복 처리 방지용으로 저장된 논문들의 목록을 직관적으로 확인하고 검색할 수 있습니다.
   > **Note**: 데이터베이스 파일인 `papers.db`는 호스트의 `./data/` 디렉토리에 마운트되므로, Docker 컨테이너가 갱신되어도 기존 처리 내역이 안전하게 보존됩니다.
