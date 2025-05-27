import os
import re
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

from data import Database

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='chatbot.log'
)
logger = logging.getLogger('chatbot')
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ChatBot:
    def __init__(self, db: Database):
        """
        Khởi tạo chatbot với kết nối database
        """
        self.db = db
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("Đã khởi tạo mô hình Gemini AI thành công")
            
            self.scenarios = {
                "price_filter": " sản phẩm có giá dưới X đồng",
                "brand_filter": "sản phẩm thương hiệu  là X",
                "search_products": "sản phẩm  X",
                "product_info": "Thông tin chi tiết về sản phẩm  X"
            }
            logger.info("Đã khởi tạo các kịch bản câu hỏi mẫu")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo mô hình Gemini AI: {str(e)}")
            raise
    
    def format_product_info(self, product: Dict[str, Any]) -> str:
        """
        Format thông tin sản phẩm để hiển thị
        """
        try:
            formatted = f"Tên: {product['name']}\n"
            formatted += f"Giá: {format(product['price'], ',d')} VND"
            
            if product.get('sale'):
                formatted += f" (Giảm giá: {product['sale']})\n"
            else:
                formatted += "\n"
            if product.get('brand'):
                formatted += f"Thương hiệu: {product['brand']}\n"
            formatted += f"Mô tả: {product.get('description', 'Không có mô tả')}\n"
            formatted += f"Thông số kỹ thuật: {product.get('specification', 'Không có thông số')}\n"
            
            if product.get('image'):
                formatted += f"Hình ảnh: {product['image']}"
            
            return formatted
        except Exception as e:
            logger.error(f"Lỗi khi format thông tin sản phẩm: {str(e)}")
            return "Không thể hiển thị thông tin sản phẩm"
    
    async def get_semantic_similarity(self, query: str, scenario: str) -> float:
        """
        Sử dụng Gemini để đánh giá mức độ tương đồng ngữ nghĩa giữa câu hỏi và kịch bản
        """
        try:
            prompt = f"""
            Đánh giá độ tương đồng ngữ nghĩa giữa hai câu dưới đây trên thang điểm từ 0 đến 1, 
            trong đó 0 là hoàn toàn khác nhau và 1 là hoàn toàn giống nhau về ý nghĩa.
            Chỉ trả về một số duy nhất.
            
            Câu 1: "{query}"
            Câu 2: "{scenario}"
            """
            
            response = await self.model.generate_content_async(prompt)
            
            result_text = response.text.strip()
            match = re.search(r'([0-9]*[.])?[0-9]+', result_text)
            if match:
                similarity = float(match.group())
                similarity = max(0, min(similarity, 1))
                return similarity
            else:
                logger.warning(f"Không thể trích xuất điểm số từ phản hồi: {result_text}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Lỗi khi đánh giá độ tương đồng ngữ nghĩa: {str(e)}")
            return 0.0
    
    async def identify_scenario(self, user_query: str) -> Tuple[str, float]:
        """
        Xác định kịch bản phù hợp nhất với câu hỏi của người dùng
        """
        try:
            best_scenario = None
            best_score = 0.0
            
            for scenario_name, scenario_query in self.scenarios.items():
                similarity = await self.get_semantic_similarity(user_query, scenario_query)
                logger.info(f"Độ tương đồng với kịch bản {scenario_name}: {similarity}")
                
                if similarity > best_score:
                    best_score = similarity
                    best_scenario = scenario_name
            
            logger.info(f"Kịch bản được chọn: {best_scenario} với điểm số: {best_score}")
            return best_scenario, best_score
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định kịch bản: {str(e)}")
            return None, 0.0
    
    def extract_price_from_query(self, query: str) -> Optional[int]:
        """
        Trích xuất giá trị giá từ câu hỏi
        """
        try:
            clean_query = query.replace(",", "")
            
            price_pattern = r'\d+'
            matches = re.findall(price_pattern, clean_query)
            
            if matches:
                return int(matches[0])
            return None
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất giá: {str(e)}")
            return None

    def extract_brand_name_from_query(self, query: str) -> Optional[str]:
        """
        Trích xuất brand_name từ câu hỏi
        """
        try:
            prompt = f"""
            Từ câu hỏi sau đây, hãy trích xuất tên thương hiệu giày mà người dùng đang hỏi.
            Chỉ trả về tên thương hiệu chính xác, không kèm theo diễn giải hay bất kỳ từ nào khác.

            Câu hỏi: "{query}"
            """

            response = self.model.generate_content(prompt)
            brand_name = response.text.strip()

            logger.info(f"Đã trích xuất tên thương hiệu: {brand_name}")
            return brand_name

        except Exception as e:
            logger.error(f"Lỗi khi trích xuất tên thương hiệu: {str(e)}")
            return None

    def extract_product_name_from_query(self, query: str) -> str:
        """
        Trích xuất tên sản phẩm từ câu hỏi
        """
        try:
            query = query.lower()
            words_to_remove = [
                "thông tin", "chi tiết", "về", "sản phẩm", "có", "tên", "là", 
                "cho", "tôi", "xem", "giày", "dép", "thể thao"
            ]
            
            for word in words_to_remove:
                query = query.replace(f" {word} ", " ")
            
            query = query.strip()
            
            if len(query.split()) > 2:
                prompt = f"""
                Từ câu hỏi sau đây, hãy trích xuất tên sản phẩm giày mà người dùng đang hỏi thông tin.
                Chỉ trả về tên sản phẩm chính xác, không kèm theo diễn giải hay bất kỳ từ nào khác.
                
                Câu hỏi: "{query}"
                """
                
                response = self.model.generate_content(prompt)
                product_name = response.text.strip()
                
                logger.info(f"Đã trích xuất tên sản phẩm: {product_name}")
                return product_name
            else:
                logger.info(f"Sử dụng trực tiếp làm tên sản phẩm: {query}")
                return query
                
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất tên sản phẩm: {str(e)}")
            return query.strip()
    
    def extract_search_keyword(self, query: str) -> str:
        """
        Trích xuất từ khóa tìm kiếm từ câu hỏi
        """
        try:
            prompt = f"""
            Từ câu hỏi tìm kiếm sau, hãy trích xuất các từ khóa quan trọng để tìm kiếm sản phẩm.
            Chỉ trả về các từ khóa, không kèm theo diễn giải.
            
            Câu hỏi: "{query}"
            """
            
            response = self.model.generate_content(prompt)
            keywords = response.text.strip()
            
            logger.info(f"Đã trích xuất từ khóa tìm kiếm: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất từ khóa tìm kiếm: {str(e)}")
            # Fallback: trả về từ đầu tiên có ít nhất 3 ký tự
            words = [w for w in query.split() if len(w) >= 3]
            return words[0] if words else query
    
    async def get_ai_response(self, user_query: str) -> str:
        """
        Lấy câu trả lời từ Gemini AI cho các câu hỏi không xác định
        """
        try:
            # Thiết lập ngữ cảnh cho AI
            prompt = """Bạn là trợ lý bán hàng cửa hàng bán giày, giúp trả lời câu hỏi khách hàng về sản phẩm giày.
            Hãy trả lời ngắn gọn câu hỏi của khách hàng và lái sang giới thiệu cho khách hàng về các thương hiệu giày mà cửa hàng bán : Nike, Adidas, Puma, Converse, Vans
            Hãy trả lời ngắn gọn và thân thiện. Trả lời bằng tiếng Việt.
            """
            
            chat = self.model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [prompt]
                },
                {
                    "role": "model",
                    "parts": ["Tôi sẽ trả lời câu hỏi của bạn về sản phẩm một cách ngắn gọn và thân thiện."]
                }
            ])
            
            response = await chat.send_message_async(user_query)
            return response.text
            
        except Exception as e:
            logger.error(f"Lỗi khi gọi API Gemini: {str(e)}")
            return f"Xin lỗi, tôi không thể kết nối với AI để trả lời câu hỏi của bạn. Lỗi: {str(e)}"
    
    async def process_query(self, user_query: str) -> str:
        """
        Xử lý câu hỏi của người dùng và trả về câu trả lời
        """
        try:
            user_query = user_query.lower().strip()
            logger.info(f"Đang xử lý câu hỏi: {user_query}")
            
            scenario, confidence = await self.identify_scenario(user_query)
            
            # Ngưỡng độ tin cậy
            CONFIDENCE_THRESHOLD = 0.5
            
            if confidence < CONFIDENCE_THRESHOLD:
                logger.info(f"Độ tin cậy ({confidence}) thấp hơn ngưỡng, chuyển cho AI")
                return await self.get_ai_response(user_query)
            
            # Xử lý theo kịch bản được xác định
            if scenario == "price_filter":
                max_price = self.extract_price_from_query(user_query)
                
                logger.info(f"Tìm sản phẩm có giá dưới: {max_price}")
                products = self.db.get_products_by_price(max_price)
                
                if products and len(products) > 0:
                    response = f"Tìm thấy {len(products)} sản phẩm có giá dưới {format(max_price, ',d')} VND:\n\n"
                    for product in products:
                        response += self.format_product_info(product) + "\n\n"
                    return response
                else:
                    logger.warning(f"Không tìm thấy sản phẩm nào có giá dưới {max_price}")
                    return f"Không tìm thấy sản phẩm nào có giá dưới {format(max_price, ',d')} VND."

            elif scenario == "brand_filter":
                brand_name = self.extract_brand_name_from_query(user_query)

                if brand_name is not None:
                    logger.info(f"Tìm sản phẩm theo tên thương hiệu: {brand_name}")
                    products = self.db.get_products_by_brand_name(brand_name)

                    if products and len(products) > 0:
                        response = f"Tìm thấy {len(products)} sản phẩm của thương hiệu '{brand_name}':\n\n"
                        for product in products:
                            response += self.format_product_info(product) + "\n\n"
                        return response

                    else:
                        logger.warning(f"Không tìm thấy sản phẩm nào của thương hiệu: {brand_name}")
                        return f"Không tìm thấy sản phẩm nào của thương hiệu '{brand_name}'."

                else:
                    return "Vui lòng cung cấp tên của thương hiệu bạn muốn tìm (ví dụ: sản phẩm của thương hiệu Nike)"
            
            elif scenario == "search_products":
                keywords = self.extract_search_keyword(user_query)
                
                logger.info(f"Tìm kiếm sản phẩm với từ khóa: {keywords}")
                products = self.db.search_products(keywords)
                
                if products and len(products) > 0:
                    response = f"Tìm thấy {len(products)} sản phẩm phù hợp với từ khóa '{keywords}':\n\n"
                    for product in products:
                        response += self.format_product_info(product) + "\n\n"
                    return response
                else:
                    logger.warning(f"Không tìm thấy sản phẩm nào với từ khóa: {keywords}")
                    return f"Không tìm thấy sản phẩm nào phù hợp với từ khóa '{keywords}'."
            
            elif scenario == "product_info":
                product_name = self.extract_product_name_from_query(user_query)
                
                if product_name:
                    logger.info(f"Tìm thông tin sản phẩm theo tên: {product_name}")
                    
                    exact_product = self.db.get_product_by_exact_name(product_name)
                    if exact_product:
                        return f"Thông tin chi tiết về sản phẩm:\n\n{self.format_product_info(exact_product)}"
                    
                    products = self.db.search_products(product_name)
                    
                    if products and len(products) > 0:
                        if len(products) == 1:
                            return f"Thông tin chi tiết về sản phẩm:\n\n{self.format_product_info(products[0])}"
                        else:
                            response = f"Tìm thấy {len(products)} sản phẩm có tên tương tự '{product_name}':\n\n"
                            for product in products:
                                response += self.format_product_info(product) + "\n\n"
                            return response
                    else:
                        logger.warning(f"Không tìm thấy sản phẩm nào với tên: {product_name}")
                        return f"Không tìm thấy sản phẩm nào có tên là '{product_name}'. Bạn có thể thử cung cấp tên chính xác hoặc dùng chức năng tìm kiếm sản phẩm."
                else:
                    return "Vui lòng cung cấp tên của sản phẩm bạn muốn xem thông tin chi tiết."
            
            logger.info("Chuyển câu hỏi cho Gemini AI xử lý")
            return await self.get_ai_response(user_query)
                
        except Exception as e:
            logger.error(f"Lỗi không xác định khi xử lý câu hỏi: {str(e)}")
            return f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn: {str(e)}"