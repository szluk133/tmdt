import mysql.connector
from typing import List, Dict, Any, Optional
import logging
import os

# Database class for handling all database operations
logger = logging.getLogger('chatbot')
class Database:
    def __init__(self, host: str, user: str, password: str, database: str):
        """
        Khởi tạo kết nối đến database MySQL
        """
        try:
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("Đã kết nối thành công đến MySQL database")
        except Exception as e:
            logger.error(f"Lỗi kết nối database: {str(e)}")
            raise

    def get_products_by_price(self, max_price: float) -> List[Dict[str, Any]]:
        """
        Lấy danh sách sản phẩm có giá thấp hơn max_price
        """
        try:
            query = "SELECT * FROM products WHERE price < %s"
            logger.info(f"Thực thi truy vấn: {query} với giá: {max_price}")
            self.cursor.execute(query, (max_price,))
            results = self.cursor.fetchall()
            logger.info(f"Tìm thấy {len(results)} sản phẩm có giá dưới {max_price}")
            return results
        except Exception as e:
            logger.error(f"Lỗi khi truy vấn sản phẩm theo giá: {str(e)}")
            return []

    def get_products_by_brand_name(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Lấy danh sách sản phẩm theo brand_name
        """
        try:
            brand_query = "SELECT id FROM brands WHERE name LIKE %s"
            self.cursor.execute(brand_query, (f"%{brand_name}%",))
            brand_result = self.cursor.fetchone()
            logger.info(f"Kết quả tìm kiếm thương hiệu: {brand_result}")

            if not brand_result:
                return []
            brand_id = brand_result['id']  # Sử dụng dictionary cursor

            product_query = """
                SELECT p.id, p.name, p.price, p.description, p.specification, p.image, p.sale, b.name as brand
                FROM products p
                JOIN brands b ON p.brand_id = b.id
                WHERE p.brand_id = %s
            """
            self.cursor.execute(product_query, (brand_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Lỗi khi lấy sản phẩm theo tên thương hiệu: {str(e)}")
            return []

    def search_products(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm sản phẩm theo từ khóa trong tên hoặc mô tả
        """
        try:
            keywords = keyword.split()
            conditions = []
            params = []

            for word in keywords:
                conditions.append("name LIKE %s")
                params.append(f"%{word}%")

            # tất cả từ khóa đều có mặt
            query = f"SELECT * FROM products WHERE {' AND '.join(conditions)}"

            logger.info(f"Thực thi truy vấn tìm kiếm với từ khóa: {keyword}")
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()

            # tìm với OR
            if not results:
                or_conditions = []
                or_params = []

                for word in keywords:
                    or_conditions.append("name LIKE %s")
                    or_params.append(f"%{word}%")
                    or_conditions.append("description LIKE %s")
                    or_params.append(f"%{word}%")

                or_query = f"SELECT * FROM products WHERE {' OR '.join(or_conditions)}"
                logger.info(f"Thử lại với truy vấn OR: {or_query}")
                self.cursor.execute(or_query, or_params)
                results = self.cursor.fetchall()

            logger.info(f"Tìm thấy {len(results)} sản phẩm phù hợp với từ khóa '{keyword}'")
            return results
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm sản phẩm: {str(e)}")
            return []

    def get_product_by_exact_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin sản phẩm theo tên chính xác
        """
        try:
            query = "SELECT * FROM products WHERE LOWER(name) = LOWER(%s)"
            logger.info(f"Thực thi truy vấn tìm theo tên chính xác: {name}")
            self.cursor.execute(query, (name,))
            result = self.cursor.fetchone()
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tìm sản phẩm theo tên chính xác: {str(e)}")
            return None

    def close(self):
        try:
            self.cursor.close()
            self.connection.close()
            logger.info("Đã đóng kết nối database")
        except Exception as e:
            logger.error(f"Lỗi khi đóng kết nối database: {str(e)}")