from fastapi import FastAPI, Form, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import ollama
from sqlalchemy.orm import Session
from models import User
from database import engine, get_db
import json
from fastapi.responses import StreamingResponse
import uvicorn
import os
import logging
from typing import Optional
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ollama-chat")

# FastAPI 앱 생성
app = FastAPI(
    title="Ollama Chat API",
    description="Ollama 모델과 연동하는 채팅 API",
    version="1.0.0"
)

# 데이터베이스 엔진
e = engine

# CORS 설정
origins = [
    "http://localhost",
    "http://localhost:5000",
    "http://localhost:9000",
    "http://localhost:9000/ollamachat"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 현재 디렉토리와 static 폴더 경로 설정
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# static 폴더가 없으면 생성
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True)

# static 파일 서빙 설정
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 사용 가능한 모델 목록
AVAILABLE_MODELS = {
    "exaone3.5": "Exaone 3.5",
    "llama3": "Llama 3",
    "mistral": "Mistral",
}

# 기본 모델 설정
DEFAULT_MODEL = "exaone3.5"

# index.html 파일 경로 확인 및 생성
def ensure_index_html_exists():
    index_path = STATIC_DIR / "index.html"
    
    # index.html 파일이 없으면 생성
    if not index_path.exists():
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="refresh" content="0;url=http://localhost:5000/" />
    <title>리디렉션 중...</title>
</head>
<body>
    <p>리디렉션 중입니다...</p>
</body>
</html>""")
    
    return index_path

# 메인 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def serve_html():
    index_path = ensure_index_html_exists()
    
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return HTMLResponse(content=content)

# API 상태 확인
@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "api_version": "1.0.0",
        "available_models": AVAILABLE_MODELS
    }

# 올라마 모델 목록 가져오기
@app.get("/api/models")
async def get_models():
    try:
        models = ollama.list()
        return {"models": models["models"]}
    except Exception as e:
        logger.error(f"모델 목록 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"모델 목록을 가져오는 중 오류 발생: {str(e)}")

# 채팅 API 엔드포인트
@app.post("/c/chat")
async def chat(message: str = Form(...), model: Optional[str] = Form(DEFAULT_MODEL)):
    logger.info(f'요청 받은 메시지: "{message[:50]}{"..." if len(message) > 50 else ""}" (모델: {model})')
    
    # 메시지 길이 제한
    if len(message) > 2000:
        return JSONResponse(
            status_code=400,
            content={"error": "메시지 길이는 2000자를 초과할 수 없습니다."}
        )
    
    # 요청한 모델이 사용 가능한지 확인
    if model not in AVAILABLE_MODELS:
        logger.warning(f"요청된 모델 '{model}'이 사용 불가능합니다. 기본 모델 '{DEFAULT_MODEL}'로 대체합니다.")
        model = DEFAULT_MODEL
    
    # 스트리밍 응답을 위한 함수
    async def generate_response():
        try:
            # ollama API 스트리밍 호출
            stream = ollama.chat(
                model=model,
                messages=[
                    {
                        'role': 'user',
                        'content': message
                    }
                ],
                stream=True  # 스트리밍 활성화
            )
            
            # 첫 번째 청크는 SSE 이벤트 형식으로 시작
            yield "data: " + json.dumps({"response": ""}) + "\n\n"
            
            # 누적된 응답을 저장
            full_response = "" 
            
            # 스트림의 각 청크를 처리
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    # SSE 형식으로 청크 전송
                    yield "data: " + json.dumps({"response": full_response}) + "\n\n"
            
            # 스트림 종료
            yield "data: [DONE]\n\n"
            
            # 로그 기록
            logger.info(f"응답 완료: {len(full_response)} 글자")
            
        except Exception as e:
            logger.error(f"스트리밍 오류: {str(e)}")
            error_msg = {"error": f"처리 중 오류가 발생했습니다: {str(e)}"}
            yield "data: " + json.dumps(error_msg) + "\n\n"
            yield "data: [DONE]\n\n"
    
    # StreamingResponse 반환
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )

# 사용자 조회 API
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()  # 모든 사용자 조회
        return JSONResponse(content={"users": [{"id": u.id, "username": u.username, "useremail": u.useremail} for u in users]})
    except Exception as e:
        logger.error(f"사용자 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 조회 중 오류 발생: {str(e)}")

# 마리아DB 연결 상태 확인
@app.get("/maria")
def maria():
    try:
        # 간단한 쿼리로 DB 연결 확인
        with Session(engine) as session:
            session.execute("SELECT 1")
        return {"message": "MariaDB 연결 성공"}
    except Exception as e:
        logger.error(f"MariaDB 연결 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"MariaDB 연결 오류: {str(e)}")

# 헬스 체크 엔드포인트
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": import_time()}

# 현재 시간 반환 (import_time 함수가 없다면 추가 필요)
def import_time():
    from datetime import datetime
    return datetime.now().isoformat()

if __name__ == "__main__":
    logger.info("Ollama Chat 서버 시작 중...")
    uvicorn.run(app, host="0.0.0.0", port=5000)