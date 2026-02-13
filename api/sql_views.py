"""
API Views для SQL компонентов (Views, Triggers, Procedures)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from api.sql_services import (
    SQLViewsService,
    SQLProceduresService,
    SQLFunctionsService,
    TriggersLogger
)
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ===============================================================================
# SQL VIEWS API
# ===============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sql_revenue_by_category(request):
    """
    GET /api/sql/views/revenue-by-category/
    Получить доход по категориям (VIEW: vw_revenue_by_category)
    """
    try:
        data = SQLViewsService.get_revenue_by_category()
        return Response({
            'view': 'vw_revenue_by_category',
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in revenue_by_category: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sql_sales_by_brand(request):
    """
    GET /api/sql/views/sales-by-brand/
    Получить продажи по брендам (VIEW: vw_sales_by_brand)
    """
    try:
        data = SQLViewsService.get_sales_by_brand()
        return Response({
            'view': 'vw_sales_by_brand',
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in sales_by_brand: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sql_order_statistics(request):
    """
    GET /api/sql/views/order-statistics/?days=30
    Получить статистику заказов (VIEW: vw_order_statistics)
    """
    try:
        days = int(request.query_params.get('days', 30))
        data = SQLViewsService.get_order_statistics(days)
        return Response({
            'view': 'vw_order_statistics',
            'days': days,
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in order_statistics: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sql_product_ratings(request):
    """
    GET /api/sql/views/product-ratings/
    Получить рейтинги продуктов (VIEW: vw_product_ratings)
    """
    try:
        data = SQLViewsService.get_product_ratings()
        return Response({
            'view': 'vw_product_ratings',
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in product_ratings: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===============================================================================
# SQL STORED PROCEDURES API
# ===============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_sales_report(request):
    """
    GET /api/sql/procedures/sales-report/?start_date=2025-01-01&end_date=2025-01-31
    Получить отчет о продажах (PROCEDURE: sp_get_sales_report)
    """
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'Required parameters: start_date, end_date (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Валидация формата даты
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return Response(
                {'error': 'Date format must be YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = SQLProceduresService.get_sales_report(start_date, end_date)
        
        return Response({
            'procedure': 'sp_get_sales_report',
            'start_date': start_date,
            'end_date': end_date,
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in sales_report: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_process_product_return(request):
    """
    POST /api/sql/procedures/process-return/
    Body: {"return_id": 1, "approval_status": "approved"}
    Обработать возврат товара (PROCEDURE: sp_process_product_return)
    """
    try:
        return_id = request.data.get('return_id')
        approval_status = request.data.get('approval_status')
        
        if not return_id or not approval_status:
            return Response(
                {'error': 'Required fields: return_id, approval_status (approved|rejected)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if approval_status not in ['approved', 'rejected']:
            return Response(
                {'error': 'approval_status must be "approved" or "rejected"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = SQLProceduresService.process_product_return(return_id, approval_status)
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'procedure': 'sp_process_product_return',
            'result': result,
            'status': 'success'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in process_product_return: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_create_monthly_snapshot(request):
    """
    POST /api/sql/procedures/create-monthly-snapshot/
    Создать ежемесячный снимок аналитики (PROCEDURE: sp_create_monthly_analytics_snapshot)
    """
    try:
        result = SQLProceduresService.create_monthly_analytics_snapshot()
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'procedure': 'sp_create_monthly_analytics_snapshot',
            'result': result,
            'status': 'success'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in create_monthly_snapshot: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===============================================================================
# SQL FUNCTIONS API
# ===============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sql_dashboard_stats(request):
    """
    GET /api/sql/functions/dashboard-stats/
    Получить статистику дашборда (FUNCTION: fn_get_dashboard_stats)
    """
    try:
        stats = SQLFunctionsService.get_dashboard_stats()
        
        return Response({
            'function': 'fn_get_dashboard_stats',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in dashboard_stats: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===============================================================================
# TRIGGERS LOGS API
# ===============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_trigger_price_changes(request):
    """
    GET /api/sql/triggers/price-changes/?product_id=1&limit=50
    Получить логи изменения цен (TRIGGER: fn_audit_product_price_change)
    """
    try:
        product_id = request.query_params.get('product_id')
        limit = int(request.query_params.get('limit', 50))
        
        product_id = int(product_id) if product_id else None
        
        data = TriggersLogger.get_price_changes(product_id, limit)
        
        return Response({
            'trigger': 'fn_audit_product_price_change',
            'product_id': product_id,
            'limit': limit,
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in price_changes: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_trigger_order_status_changes(request):
    """
    GET /api/sql/triggers/order-status-changes/?order_id=1&limit=50
    Получить логи изменения статуса заказов (TRIGGER: fn_audit_order_status_change)
    """
    try:
        order_id = request.query_params.get('order_id')
        limit = int(request.query_params.get('limit', 50))
        
        order_id = int(order_id) if order_id else None
        
        data = TriggersLogger.get_order_status_changes(order_id, limit)
        
        return Response({
            'trigger': 'fn_audit_order_status_change',
            'order_id': order_id,
            'limit': limit,
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in order_status_changes: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_trigger_review_creations(request):
    """
    GET /api/sql/triggers/review-creations/?product_id=1&limit=50
    Получить логи создания отзывов (TRIGGER: fn_audit_review_creation)
    """
    try:
        product_id = request.query_params.get('product_id')
        limit = int(request.query_params.get('limit', 50))
        
        product_id = int(product_id) if product_id else None
        
        data = TriggersLogger.get_review_creations(product_id, limit)
        
        return Response({
            'trigger': 'fn_audit_review_creation',
            'product_id': product_id,
            'limit': limit,
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in review_creations: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def sql_trigger_payment_records(request):
    """
    GET /api/sql/triggers/payment-records/?order_id=1&limit=50
    Получить логи платежей (TRIGGER: fn_audit_payment_status_change)
    """
    try:
        order_id = request.query_params.get('order_id')
        limit = int(request.query_params.get('limit', 50))
        
        order_id = int(order_id) if order_id else None
        
        data = TriggersLogger.get_payment_records(order_id, limit)
        
        return Response({
            'trigger': 'fn_audit_payment_status_change',
            'limit': limit,
            'data': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in payment_records: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
