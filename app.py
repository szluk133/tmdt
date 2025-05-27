import os
import logging
import asyncio
from dotenv import load_dotenv

from data import Database
from chatbot import ChatBot

# Thiết lập logging
logger = logging.getLogger('chatbot')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('chatbot.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
load_dotenv()

async def main():
    try:
        # Thông tin kết nối database
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_USER = os.getenv("DB_USER", "admin")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
        DB_NAME = os.getenv("DB_NAME", "web_tmdt")
        
        logger.info(f"Kết nối đến database: {DB_NAME} trên host: {DB_HOST}")
        
        # Khởi tạo kết nối database
        db = Database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
        
        # Khởi tạo chatbot
        chatbot = ChatBot(db)
        
        print("Chatbot đã sẵn sàng.")
        logger.info("Chatbot đã khởi động và sẵn sàng phục vụ")
        
        # Vòng lặp chính
        while True:
            user_input = input("Bạn: ")
            
            if user_input.lower() == "quit":
                logger.info("Người dùng đã đóng chatbot")
                break
            
            response = await chatbot.process_query(user_input)
            print(f"Chatbot: {response}")
        
        # Đóng kết nối database khi kết thúc
        db.close()
        
    except Exception as e:
        logger.critical(f"Lỗi nghiêm trọng: {str(e)}")
        print(f"Đã xảy ra lỗi nghiêm trọng: {str(e)}")
        print("Vui lòng kiểm tra file log để biết thêm chi tiết.")

if __name__ == "__main__":
    asyncio.run(main())