import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from data import Database
from chatbot import ChatBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='chatbot_api.log'
)
logger = logging.getLogger('chatbot_api')
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "web_tmdt")

logger.info(f"Kết nối đến database: {DB_NAME} trên host: {DB_HOST}")
db = Database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
chatbot = ChatBot(db)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Chatbot API đã khởi động và sẵn sàng phục vụ")
    yield
    db.close()
    logger.info("Đã đóng kết nối database.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def run_async(coro):
    return await coro


@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get('message', '')

        if not user_message:
            raise HTTPException(status_code=400, detail="Không có tin nhắn được cung cấp")

        logger.info(f"Nhận được tin nhắn: {user_message}")
        response = await chatbot.process_query(user_message)
        logger.info(f"Trả lời: {response}")
        return JSONResponse(content={
            'status': 'success',
            'response': response
        })
    except Exception as e:
        logger.error(f"Lỗi xử lý tin nhắn: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@app.get("/api/health")
async def health_check():
    return JSONResponse(content={
        'status': 'online',
        'message': 'Chatbot API đang hoạt động'
    })
