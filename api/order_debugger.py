"""
Утилиты для отладки и мониторинга заказов
"""
import logging
from datetime import timedelta
from django.utils import timezone
from apps.orders.models import Orders, OrderItems
from apps.users.models import Customers

logger = logging.getLogger(__name__)


class OrderDebugger:
    """Класс для отладки и мониторинга заказов"""
    
    @staticmethod
    def check_duplicate_orders(customer_id, minutes=5):
        """
        Проверяет, не было ли создано двойных заказов для клиента
        Смотрит заказы, созданные за последние N минут
        
        Args:
            customer_id: ID клиента
            minutes: Временной диапазон в минутах (по умолчанию 5)
            
        Returns:
            dict с информацией о дублях
        """
        try:
            time_threshold = timezone.now() - timedelta(minutes=minutes)
            
            orders = Orders.objects.filter(
                customer_id=customer_id,
                order_date__gte=time_threshold
            ).order_by('-order_date')
            
            result = {
                'customer_id': customer_id,
                'time_window_minutes': minutes,
                'orders_found': orders.count(),
                'orders': []
            }
            
            for order in orders:
                order_info = {
                    'order_id': order.order_id,
                    'order_date': order.order_date.isoformat(),
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'items_count': order.order_items.count(),
                    'items': [
                        {
                            'product_id': item.product_id,
                            'product_name': item.product.product_name,
                            'quantity': item.quantity,
                            'price': float(item.price_at_purchase)
                        }
                        for item in order.order_items.all()
                    ]
                }
                result['orders'].append(order_info)
            
            if orders.count() > 1:
                logger.warning(
                    f"[DUPLICATE_ORDERS] Customer {customer_id}: "
                    f"found {orders.count()} orders in last {minutes} minutes"
                )
                result['status'] = 'DUPLICATE_DETECTED'
                
                # Проверяем идентичность заказов
                if orders.count() >= 2:
                    order_1 = orders[0]
                    order_2 = orders[1]
                    
                    items_1 = set((item.product_id, item.quantity) for item in order_1.order_items.all())
                    items_2 = set((item.product_id, item.quantity) for item in order_2.order_items.all())
                    
                    if items_1 == items_2 and abs((order_1.total_amount - order_2.total_amount)) < 0.01:
                        result['identical'] = True
                        logger.critical(
                            f"[DUPLICATE_IDENTICAL] Orders {order_1.order_id} and {order_2.order_id} "
                            f"are IDENTICAL - possible double charge!"
                        )
                    else:
                        result['identical'] = False
            else:
                result['status'] = 'OK'
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking duplicate orders: {e}")
            return {
                'error': str(e),
                'customer_id': customer_id
            }
    
    @staticmethod
    def check_duplicate_addresses(customer_id, hours=1):
        """
        Проверяет, не было ли создано дублей адресов
        """
        try:
            from apps.users.models import Addresses
            
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            addresses = Addresses.objects.filter(
                customer_id=customer_id,
                created_at__gte=time_threshold
            ).order_by('-created_at')
            
            result = {
                'customer_id': customer_id,
                'time_window_hours': hours,
                'addresses_found': addresses.count(),
                'addresses': []
            }
            
            for addr in addresses:
                result['addresses'].append({
                    'address_id': addr.address_id,
                    'full_address': addr.full_address,
                    'type': addr.type,
                    'created_at': addr.created_at.isoformat(),
                })
            
            if addresses.count() > 1:
                # Проверяем идентичность
                if addresses.count() >= 2:
                    addr_1 = addresses[0]
                    addr_2 = addresses[1]
                    
                    if (addr_1.full_address == addr_2.full_address and 
                        addr_1.type == addr_2.type):
                        result['status'] = 'DUPLICATE_DETECTED'
                        result['identical'] = True
                        logger.warning(
                            f"[DUPLICATE_ADDRESS] Customer {customer_id}: "
                            f"found identical addresses {addr_1.address_id} and {addr_2.address_id}"
                        )
                    else:
                        result['status'] = 'MULTIPLE_DIFFERENT'
                        result['identical'] = False
                else:
                    result['status'] = 'MULTIPLE_FOUND'
            else:
                result['status'] = 'OK'
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking duplicate addresses: {e}")
            return {
                'error': str(e),
                'customer_id': customer_id
            }
    
    @staticmethod
    def get_order_creation_log(order_id):
        """
        Получает лог создания заказа из audit_log
        """
        try:
            from apps.analytics.models import AuditLog
            
            logs = AuditLog.objects.filter(
                table_name='orders',
                record_id=order_id,
                action_type='CREATE'
            ).order_by('-timestamp')[:5]
            
            result = {
                'order_id': order_id,
                'logs': []
            }
            
            for log in logs:
                result['logs'].append({
                    'log_id': log.log_id,
                    'user': log.user.email if log.user else 'System',
                    'action_type': log.action_type,
                    'timestamp': log.timestamp.isoformat(),
                    'new_value': log.new_value
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting order creation log: {e}")
            return {'error': str(e), 'order_id': order_id}


class PasswordResetDebugger:
    """Класс для отладки восстановления пароля"""
    
    @staticmethod
    def check_reset_tokens(email):
        """
        Проверяет, есть ли активные токены восстановления пароля
        """
        try:
            customer = Customers.objects.get(email__iexact=email)
            
            result = {
                'email': email,
                'customer_id': customer.customer_id,
                'has_token': customer.password_reset_token is not None,
                'token_created_at': None,
                'token_expires_at': None,
                'token_expired': False,
                'time_remaining': None
            }
            
            if customer.password_reset_token:
                result['token_created_at'] = customer.updated_at.isoformat()
                
                if customer.password_reset_expires:
                    result['token_expires_at'] = customer.password_reset_expires.isoformat()
                    
                    if timezone.now() > customer.password_reset_expires:
                        result['token_expired'] = True
                        logger.warning(
                            f"[PASSWORD_RESET_EXPIRED] Token for {email} has expired"
                        )
                    else:
                        remaining = customer.password_reset_expires - timezone.now()
                        result['time_remaining'] = {
                            'seconds': int(remaining.total_seconds()),
                            'minutes': int(remaining.total_seconds() / 60),
                            'display': f"{int(remaining.total_seconds() / 60)} мин"
                        }
                        logger.info(
                            f"[PASSWORD_RESET_VALID] Token for {email} valid for {result['time_remaining']['display']}"
                        )
            
            return result
            
        except Customers.DoesNotExist:
            logger.warning(f"[PASSWORD_RESET_NOT_FOUND] Customer with email {email} not found")
            return {
                'email': email,
                'error': 'Customer not found',
                'status': 'NOT_FOUND'
            }
        except Exception as e:
            logger.error(f"Error checking reset tokens: {e}")
            return {
                'email': email,
                'error': str(e)
            }
    
    @staticmethod
    def clear_expired_tokens():
        """
        Удаляет истекшие токены восстановления пароля
        """
        try:
            expired_count = Customers.objects.filter(
                password_reset_token__isnull=False,
                password_reset_expires__lt=timezone.now()
            ).update(
                password_reset_token=None,
                password_reset_expires=None
            )
            
            logger.info(f"[CLEANUP] Cleared {expired_count} expired password reset tokens")
            return {
                'status': 'success',
                'expired_tokens_cleared': expired_count
            }
            
        except Exception as e:
            logger.error(f"Error clearing expired tokens: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
