"""
Сервис для работы с SQL Views, Triggers и Stored Procedures
"""
from django.db import connection
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SQLViewsService:
    """Сервис для работы с SQL представлениями (Views)"""
    
    @staticmethod
    def get_revenue_by_category() -> List[Dict[str, Any]]:
        """
        Получить доход по категориям из VIEW vw_revenue_by_category
        
        Returns:
            Список словарей с доходом по категориям
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        category_id,
                        category_name,
                        total_orders,
                        products_sold,
                        total_quantity_sold,
                        total_revenue,
                        avg_price,
                        last_order_date
                    FROM vw_revenue_by_category
                    ORDER BY total_revenue DESC
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching revenue by category: {e}")
            return []
    
    @staticmethod
    def get_sales_by_brand() -> List[Dict[str, Any]]:
        """
        Получить продажи по брендам из VIEW vw_sales_by_brand
        
        Returns:
            Список словарей с продажами по брендам
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        brand_id,
                        brand_name,
                        total_products,
                        orders_count,
                        items_sold,
                        total_sales,
                        avg_rating,
                        review_count
                    FROM vw_sales_by_brand
                    ORDER BY total_sales DESC
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching sales by brand: {e}")
            return []
    
    @staticmethod
    def get_order_statistics(days: int = 30) -> List[Dict[str, Any]]:
        """
        Получить статистику заказов из VIEW vw_order_statistics
        
        Args:
            days: Количество дней для фильтрации
            
        Returns:
            Список словарей со статистикой заказов
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        order_date,
                        status,
                        count_orders,
                        total_amount,
                        avg_order_amount,
                        min_order_amount,
                        max_order_amount
                    FROM vw_order_statistics
                    WHERE order_date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY order_date DESC
                """, [days])
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching order statistics: {e}")
            return []
    
    @staticmethod
    def get_product_ratings() -> List[Dict[str, Any]]:
        """
        Получить рейтинги продуктов из VIEW vw_product_ratings
        
        Returns:
            Список словарей с рейтингами продуктов
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        product_id,
                        product_name,
                        category_name,
                        brand_name,
                        review_count,
                        avg_rating,
                        five_star_count,
                        four_star_count,
                        three_star_count,
                        two_star_count,
                        one_star_count,
                        last_review_date
                    FROM vw_product_ratings
                    WHERE review_count > 0
                    ORDER BY avg_rating DESC, review_count DESC
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching product ratings: {e}")
            return []


class SQLProceduresService:
    """Сервис для работы с хранимыми процедурами (Stored Procedures)"""
    
    @staticmethod
    def get_sales_report(start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Вызвать процедуру sp_get_sales_report для получения отчета о продажах
        
        Args:
            start_date: Начальная дата (YYYY-MM-DD)
            end_date: Конечная дата (YYYY-MM-DD)
            
        Returns:
            Список словарей с данными отчета
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM sp_get_sales_report(%s::DATE, %s::DATE)
                """, [start_date, end_date])
                columns = [col[0] for col in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                logger.info(f"Sales report generated for {start_date} to {end_date}: {len(result)} rows")
                return result
        except Exception as e:
            logger.error(f"Error executing sales report procedure: {e}")
            return []
    
    @staticmethod
    def process_product_return(return_id: int, approval_status: str) -> Dict[str, Any]:
        """
        Вызвать процедуру sp_process_product_return для обработки возврата
        
        Args:
            return_id: ID возврата
            approval_status: Статус ('approved' или 'rejected')
            
        Returns:
            Результат обработки возврата
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM sp_process_product_return(%s, %s)
                """, [return_id, approval_status])
                columns = [col[0] for col in cursor.description]
                result = cursor.fetchone()
                
                if result:
                    data = dict(zip(columns, result))
                    logger.info(
                        f"Product return {return_id} processed with status '{approval_status}': {data.get('message')}"
                    )
                    return data
                else:
                    logger.warning(f"No result from process_product_return for return_id {return_id}")
                    return {'error': 'Возврат не найден'}
        except Exception as e:
            logger.error(f"Error processing product return: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def create_monthly_analytics_snapshot() -> Dict[str, Any]:
        """
        Вызвать процедуру sp_create_monthly_analytics_snapshot для создания снимка аналитики
        
        Returns:
            Результат создания снимка
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM sp_create_monthly_analytics_snapshot()
                """)
                columns = [col[0] for col in cursor.description]
                result = cursor.fetchone()
                
                if result:
                    data = dict(zip(columns, result))
                    logger.info(
                        f"Monthly analytics snapshot created: ID={data.get('snapshot_id')}, "
                        f"revenue={data.get('total_revenue')}, orders={data.get('order_count')}"
                    )
                    return data
                else:
                    logger.warning("No result from create_monthly_analytics_snapshot")
                    return {'error': 'Не удалось создать снимок'}
        except Exception as e:
            logger.error(f"Error creating monthly analytics snapshot: {e}")
            return {'error': str(e)}


class SQLFunctionsService:
    """Сервис для работы с SQL функциями"""
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """
        Вызвать функцию fn_get_dashboard_stats для получения статистики дашборда
        
        Returns:
            JSONB с статистикой
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT fn_get_dashboard_stats()::json AS stats
                """)
                result = cursor.fetchone()
                
                if result and result[0]:
                    import json
                    stats = json.loads(result[0])
                    logger.info(f"Dashboard stats retrieved: {len(stats)} metrics")
                    return stats
                else:
                    logger.warning("No result from fn_get_dashboard_stats")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {e}")
            return {}


class TriggersLogger:
    """Класс для отслеживания работы триггеров через audit_log"""
    
    @staticmethod
    def get_price_changes(product_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получить логи изменения цен (триггер: fn_audit_product_price_change)
        
        Args:
            product_id: ID продукта (опционально)
            limit: Количество записей
            
        Returns:
            Список логов изменения цен
        """
        try:
            with connection.cursor() as cursor:
                if product_id:
                    cursor.execute("""
                        SELECT 
                            log_id,
                            user_id,
                            action_type,
                            record_id,
                            old_value,
                            new_value,
                            timestamp
                        FROM audit_log
                        WHERE action_type = 'PRICE_CHANGE' 
                            AND record_id = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, [product_id, limit])
                else:
                    cursor.execute("""
                        SELECT 
                            log_id,
                            user_id,
                            action_type,
                            record_id,
                            old_value,
                            new_value,
                            timestamp
                        FROM audit_log
                        WHERE action_type = 'PRICE_CHANGE'
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, [limit])
                
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching price changes: {e}")
            return []
    
    @staticmethod
    def get_order_status_changes(order_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получить логи изменения статуса заказов (триггер: fn_audit_order_status_change)
        
        Args:
            order_id: ID заказа (опционально)
            limit: Количество записей
            
        Returns:
            Список логов изменения статуса
        """
        try:
            with connection.cursor() as cursor:
                if order_id:
                    cursor.execute("""
                        SELECT 
                            log_id,
                            user_id,
                            action_type,
                            record_id,
                            old_value,
                            new_value,
                            timestamp
                        FROM audit_log
                        WHERE action_type = 'ORDER_STATUS_CHANGE' 
                            AND record_id = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, [order_id, limit])
                else:
                    cursor.execute("""
                        SELECT 
                            log_id,
                            user_id,
                            action_type,
                            record_id,
                            old_value,
                            new_value,
                            timestamp
                        FROM audit_log
                        WHERE action_type = 'ORDER_STATUS_CHANGE'
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, [limit])
                
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching order status changes: {e}")
            return []
    
    @staticmethod
    def get_review_creations(product_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получить логи создания отзывов (триггер: fn_audit_review_creation)
        
        Args:
            product_id: ID продукта (опционально)
            limit: Количество записей
            
        Returns:
            Список логов создания отзывов
        """
        try:
            with connection.cursor() as cursor:
                if product_id:
                    cursor.execute("""
                        SELECT 
                            log_id,
                            user_id,
                            action_type,
                            record_id,
                            old_value,
                            new_value,
                            timestamp
                        FROM audit_log
                        WHERE action_type = 'REVIEW_CREATED'
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, [limit])
                else:
                    cursor.execute("""
                        SELECT 
                            log_id,
                            user_id,
                            action_type,
                            record_id,
                            old_value,
                            new_value,
                            timestamp
                        FROM audit_log
                        WHERE action_type = 'REVIEW_CREATED'
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, [limit])
                
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching review creations: {e}")
            return []
    
    @staticmethod
    def get_payment_records(order_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получить логи платежей (триггер: fn_audit_payment_status_change)
        
        Args:
            order_id: ID заказа (опционально)
            limit: Количество записей
            
        Returns:
            Список логов платежей
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        log_id,
                        user_id,
                        action_type,
                        record_id,
                        old_value,
                        new_value,
                        timestamp
                    FROM audit_log
                    WHERE action_type = 'PAYMENT_RECORDED'
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, [limit])
                
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching payment records: {e}")
            return []
