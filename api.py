# uvicorn api:app --reload --host 0.0.0.0 --port 5000
from fastapi import FastAPI, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import ollama
from sqlalchemy.orm import Session
from models import User
from database import engine, get_db

app = FastAPI()
e = engine

origins = [
    "http://localhost"
    "http://localhost:9000",
    "http://localhost:9000/ollamachat"
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

    return JSONResponse(content={'response': res['message']['content']})


@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()  # 모든 사용자 조회
    return JSONResponse(content={"users": [{"id": u.id, "username": u.username, "useremail": u.useremail} for u in users]})


@app.get("/maria")
def maria():
    return {"message": "MariaDB 연결 성공"}
