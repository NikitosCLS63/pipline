"""
API endpoints для мониторинга и отладки (только для админов)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from api.order_debugger import OrderDebugger, PasswordResetDebugger
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def check_duplicate_orders_api(request):
    """
    GET /api/debug/orders/duplicates/?customer_id=1&minutes=5
    Проверяет дублирование заказов для клиента
    """
    customer_id = request.query_params.get('customer_id')
    minutes = request.query_params.get('minutes', 5)
    
    if not customer_id:
        return Response(
            {'error': 'Required parameter: customer_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        minutes = int(minutes)
    except (ValueError, TypeError):
        minutes = 5
    
    result = OrderDebugger.check_duplicate_orders(int(customer_id), minutes)
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def check_duplicate_addresses_api(request):
    """
    GET /api/debug/addresses/duplicates/?customer_id=1&hours=1
    Проверяет дублирование адресов для клиента
    """
    customer_id = request.query_params.get('customer_id')
    hours = request.query_params.get('hours', 1)
    
    if not customer_id:
        return Response(
            {'error': 'Required parameter: customer_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        hours = int(hours)
    except (ValueError, TypeError):
        hours = 1
    
    result = OrderDebugger.check_duplicate_addresses(int(customer_id), hours)
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_order_creation_log_api(request):
    """
    GET /api/debug/orders/{order_id}/log/
    Получает лог создания заказа
    """
    order_id = request.query_params.get('order_id')
    
    if not order_id:
        return Response(
            {'error': 'Required parameter: order_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = OrderDebugger.get_order_creation_log(int(order_id))
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def check_password_reset_token_api(request):
    """
    GET /api/debug/password-reset/check/?email=user@example.com
    Проверяет статус токена восстановления пароля
    """
    email = request.query_params.get('email')
    
    if not email:
        return Response(
            {'error': 'Required parameter: email'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = PasswordResetDebugger.check_reset_tokens(email)
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def clear_expired_tokens_api(request):
    """
    POST /api/debug/password-reset/clear-expired/
    Удаляет истекшие токены восстановления пароля
    """
    result = PasswordResetDebugger.clear_expired_tokens()
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health_check(request):
    """
    GET /api/debug/health/
    Проверяет здоровье системы
    """
    try:
        from django.db import connection
        from apps.users.models import Customers
        from apps.orders.models import Orders
        from apps.products.models import Products
        
        # Проверяем БД
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        result = {
            'status': 'OK',
            'database': 'connected',
            'statistics': {
                'total_customers': Customers.objects.count(),
                'total_orders': Orders.objects.count(),
                'total_products': Products.objects.count(),
            }
        }
        
        # Проверяем письма (если возможно)
        try:
            from django.core.mail import get_connection
            conn = get_connection()
            conn.open()
            conn.close()
            result['email'] = 'connected'
        except Exception as e:
            result['email'] = f'error: {str(e)}'
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {'status': 'ERROR', 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_current_user_setting(request):
    """Возвращает значение session-настройки PostgreSQL `app.current_user_id` для текущего соединения.
    Полезно для проверки, выставляет ли middleware значение в текущей DB-сессии.
    """
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT current_setting('app.current_user_id', true) as setting, current_user;")
            row = cur.fetchone()

        result = {
            'request_user': getattr(request.user, 'email', None),
            'jwt_customer_id': getattr(request, 'jwt_customer_id', None) if hasattr(request, 'jwt_customer_id') else None,
            'current_customer_in_request': getattr(request, 'current_customer', None).customer_id if getattr(request, 'current_customer', None) else None,
            'db_current_setting': row[0],
            'db_role': row[1]
        }
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"debug_current_user_setting failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
