# uvicorn api:app --reload --port 5000
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import ollama

app = FastAPI()

origins = [
    "http://localhost",  # 허용할 도메인
    "http://localhost:3000",  # React 개발 서버
    "http://localhost:9000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 출처들
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


@app.get("/")
def hello_fastAPI():
    return {"message": "Hello, FastAPI!"}


@app.post("/c/chat")
async def chat(message: str = Form(...)):
    print(f'요청 받은 메시지 : {message}')

    # ollama API 호출
    res = ollama.chat(
        model='deepseek-r1:8b',
        messages=[
            {
                'role': 'user',
                'content': message
            }
        ]
    )

    # 서버 응답
    return JSONResponse(content={'response': res['message']['content']})