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
1. **Fetch (수집)**: `paper_fetcher.py`가 [Semantic Scholar API](https://www.semanticscholar.org/product/api)를 호출합니다. 지정된 학회 이름과 현재 연도를 기반으로 검색하며, API의 Rate Limit 방지를 위해 지수 백오프(Exponential Backoff) 로직이 적용되어 있습니다.
2. **Filter & Deduplicate (필터링 및 중복제거)**: 수집된 논문이 타겟 학회 논문인지 검증하고, `database.py` 시스템을 통해 이미 Slack에 업로드된 적이 있는 논문인지 (DB 기반) 검사합니다.
3. **Summarize (요약)**: `summarizer.py`가 OpenAI 호환 API (OpenAI 본가, vLLM, Ollama 등)를 사용하여 논문을 비전문가도 10초 만에 파악할 수 있도록 요약합니다. 결과는 **한 줄 요약 (ONE_LINE)**과 **문제/해결/효과 세 가지로 구성된 빠른 요약 (QUICK_SUMMARY)**으로 파싱됩니다.
4. **Publish (발행)**: `slack_bot.py`가 요약된 데이터를 가장 안전하고 깔끔한 형태인 **Slack Block Kit**을 이용하여 포스팅합니다. 메인 채널에는 직관적인 한 줄 요약 메세지들을 모아서 전송하고, 각 논문의 자세한 분석(문제, 해결, 효과)은 **스레드 내부에 구조화된 블록 리스트** 형태로 안전하게 발송됩니다. 메시지가 정상적으로 전송되면 DB에 논문 ID가 추가됩니다.

---

## 📂 Project Structure

- `main.py`: 전체 파이프라인을 제어하고 스케줄링(기본 24시간)하는 오케스트레이션 스크립트입니다.
- `config.py`: `.env` 파일로부터 환경 변수를 로드하고 전역 설정값을 관리합니다.
- `paper_fetcher.py`: Semantic Scholar API와 통신하여 논문 데이터를 수집합니다.
- `database.py`: 로컬 SQLite DB(`papers.db`)를 관리하여 중복 발송을 제어합니다.
- `summarizer.py`: OpenAI 호환 LLM API와 통신하여 요약본을 생성합니다.
- `slack_bot.py`: 요약된 데이터를 Slack 메시지 템플릿(Block Kit)으로 변환 후 전송합니다.
- `Dockerfile` & `docker-compose.yml`: 시스템 의존성 없이 독립적이고 안정적으로 서버를 띄우기 위한 컨테이너라이제이션 설정 파일입니다.

---

## 🚀 Getting Started

프로젝트를 실행하려면 `Docker`와 `docker-compose`가 설치되어 있어야 합니다.

1. **환경 변수 템플릿 복사 및 수정**
   ```bash
   cp .env.example .env
   # .env 파일을 열어 Slack Token, Channel ID, OpenAI API Key 등을 입력하세요.
   ```

2. **Docker Compose를 통한 백그라운드 실행**
   ```bash
   docker-compose up -d --build
   ```

3. **작동 확인 및 로그 보기**
   ```bash
   docker-compose logs -f
   ```

> **Note**: 데이터베이스 파일인 `papers.db`는 호스트의 `./data/` 디렉토리에 마운트되므로, Docker 컨테이너가 재시작되어도 기존 처리 내역(중복 방지 데이터)이 안전하게 보존됩니다.
