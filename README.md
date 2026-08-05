# 일본 신입사원 규정 안내 RAG - AI Service

일본 신입사원을 위한 사내 규정 안내 RAG 서비스의 Python AI 서버입니다.

현재 초기 버전은 Flask 기반 상태 확인 API만 제공합니다.

## 기술 구성

- Python 3.12
- Flask
- Python venv

## 요구 환경

Python 3.12를 사용합니다.

버전 확인:

    python3.12 --version

## 최초 설치

가상환경 생성:

    python3.12 -m venv .venv

가상환경 활성화:

    source .venv/bin/activate

패키지 설치:

    python -m pip install -r requirements.txt

## 실행

    source .venv/bin/activate
    python -m flask --app app run --port 5001

기본 주소:

    http://127.0.0.1:5001

## 상태 확인

    curl http://127.0.0.1:5001/health

정상 응답:

    {
      "service": "japan-newhire-rag-ai",
      "status": "ok"
    }

## 종료

서버 실행 터미널에서 Control + C를 누릅니다.

가상환경 종료:

    deactivate

## 환경변수

`.env.example`을 참고하여 각자 로컬 `.env`를 만듭니다.

    cp .env.example .env

실제 API 키, 비밀번호, 사내 문서 및 개인정보는 GitHub에 올리지 않습니다.

## 저장소에 포함하지 않는 항목

- `.venv/`
- `.env`
- API 키 및 비밀번호
- 사내 규정 원문
- 벡터 데이터베이스 파일
- 로그 파일
