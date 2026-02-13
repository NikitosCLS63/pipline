"""
API Views для PDF отчетов и предпросмотров
"""
from rest_framework.decorators import api_view, permission_classes, authentication_classes, renderer_classes
from rest_framework.renderers import BaseRenderer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from api.authentication import CustomJWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, HttpResponse
from django.core.files.base import ContentFile
import logging

from .models import Orders
from .pdf_service import OrderPDFGenerator, ReportPDFGenerator

logger = logging.getLogger(__name__)


class PDFRenderer(BaseRenderer):
    """Simple renderer that declares support for application/pdf so DRF
    content negotiation doesn't return 406 when the client requests PDF.
    The view returns a Django HttpResponse containing raw PDF bytes,
    so this renderer's render method can just passthrough bytes.
    """
    media_type = 'application/pdf'
    format = 'pdf'

    def render(self, data, media_type=None, renderer_context=None):
        # If data is already bytes (PDF buffer), return it unchanged.
        if isinstance(data, (bytes, bytearray)):
            return data
        # If caller used DRF Response with bytes payload, return as-is.
        return data


@api_view(['GET'])
@renderer_classes([PDFRenderer])
@authentication_classes([SessionAuthentication, CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def order_pdf_preview(request, order_id):
    """
    GET /api/orders/{order_id}/pdf-preview/
    Предпросмотр PDF заказа (inline в браузер)
    """
    try:
        # Проверяем доступ - только собственные заказы или админ
        order = Orders.objects.get(order_id=order_id)
        
        if order.customer_id != request.user.id and not request.user.is_staff:
            return Response(
                {'error': 'У вас нет доступа к этому заказу'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Генерируем PDF
        pdf_gen = OrderPDFGenerator()
        pdf_buffer = pdf_gen.generate_order_pdf(order)
        
        # Возвращаем PDF в браузер
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="order_{order_id}.pdf"'
        
        logger.info(f"PDF preview requested for order {order_id} by user {request.user}")
        return response
        
    except Orders.DoesNotExist:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error generating PDF preview: {e}")
        return Response(
            {'error': 'Ошибка при генерации PDF'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@renderer_classes([PDFRenderer])
@authentication_classes([SessionAuthentication, CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def order_pdf_download(request, order_id):
    """
    GET /api/orders/{order_id}/pdf-download/
    Скачивание PDF заказа
    """
    try:
        order = Orders.objects.get(order_id=order_id)
        
        # Проверяем доступ
        if order.customer_id != request.user.id and not request.user.is_staff:
            return Response(
                {'error': 'У вас нет доступа к этому заказу'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pdf_gen = OrderPDFGenerator()
        pdf_buffer = pdf_gen.generate_order_pdf(order)
        
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="order_{order_id}_{order.order_date.strftime("%Y%m%d")}.pdf"'
        
        logger.info(f"PDF downloaded for order {order_id} by user {request.user}")
        return response
        
    except Orders.DoesNotExist:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return Response(
            {'error': 'Ошибка при скачивании PDF'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@renderer_classes([PDFRenderer])
@authentication_classes([SessionAuthentication, CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def sales_report_pdf_preview(request):
    """
    GET /api/reports/sales/pdf-preview/?start_date=2025-01-01&end_date=2025-01-31
    Предпросмотр PDF отчета о продажах
    """
    try:
        from datetime import datetime
        from apps.users.models import Customers, Users

        # Проверяем доступ - только для администраторов
        is_admin = False
        
        # 1. Пытаемся получить customer_id из JWT (если используется JWT)
        customer_id = getattr(request, 'jwt_customer_id', None)
        
        # 2. Если нет JWT customer_id, пытаемся извлечь из email
        if not customer_id and hasattr(request.user, 'email'):
            try:
                customer = Customers.objects.filter(email=request.user.email).first()
                if customer:
                    customer_id = customer.customer_id
            except Exception:
                pass
        
        # 3. Проверяем роль через Users
        if customer_id:
            try:
                user_record = Users.objects.select_related('role').filter(customer_id=customer_id).first()
                if user_record and user_record.role and user_record.role.role_name == 'admin':
                    is_admin = True
            except Exception:
                pass

        # Fallback на is_staff (для Django superuser)
        if not is_admin and not request.user.is_staff:
            logger.warning(f"Unauthorized PDF access attempt by user {getattr(request.user, 'email', request.user)}")
            return Response(
                {'error': 'Только администраторы могут просматривать отчеты'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем параметры
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if not start_date_str or not end_date_str:
            return Response(
                {'error': 'Требуются параметры start_date и end_date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Некорректный формат даты (используйте YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем данные из БД
        from django.db.models import Sum, Count, F, DecimalField
        from apps.products.models import Products
        from apps.orders.models import OrderItems, Orders

        # Per-product sales: product id, sku, name, category, total quantity and revenue
        data_qs = OrderItems.objects.filter(
            order__order_date__date__gte=start_date,
            order__order_date__date__lte=end_date,
            order__status__in=['delivered', 'shipped']
        ).values(
            'product_id',
            'product__sku',
            'product__product_name',
            'product__category__category_name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price_at_purchase'), output_field=DecimalField())
        ).order_by('-total_revenue')

        report_data = [
            {
                'product_id': item.get('product_id'),
                'sku': item.get('product__sku') or '',
                'product_name': item.get('product__product_name') or '',
                'category': item.get('product__category__category_name') or '',
                'quantity': int(item.get('total_quantity') or 0),
                'revenue': float(item.get('total_revenue') or 0),
            }
            for item in data_qs
        ]
        
        # Генерируем PDF
        pdf_gen = ReportPDFGenerator()
        pdf_buffer = pdf_gen.generate_sales_report_pdf(start_date, end_date, report_data)
        
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="sales_report_{start_date}_{end_date}.pdf"'
        
        logger.info(f"Sales report PDF preview generated for {start_date} to {end_date}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating sales report PDF: {e}")
        return Response(
            {'error': f'Ошибка при генерации отчета: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([SessionAuthentication, CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def inventory_report_pdf_preview(request):
    """
    GET /api/reports/inventory/pdf-preview/
    Предпросмотр PDF отчета об инвентаре
    """
    try:
        from apps.users.models import Customers, Users

        # Проверяем доступ - только для администраторов
        is_admin = False
        
        # 1. Пытаемся получить customer_id из JWT (если используется JWT)
        customer_id = getattr(request, 'jwt_customer_id', None)
        
        # 2. Если нет JWT customer_id, пытаемся извлечь из email
        if not customer_id and hasattr(request.user, 'email'):
            try:
                customer = Customers.objects.filter(email=request.user.email).first()
                if customer:
                    customer_id = customer.customer_id
            except Exception:
                pass
        
        # 3. Проверяем роль через Users
        if customer_id:
            try:
                user_record = Users.objects.select_related('role').filter(customer_id=customer_id).first()
                if user_record and user_record.role and user_record.role.role_name == 'admin':
                    is_admin = True
            except Exception:
                pass

        # Fallback на is_staff (для Django superuser)
        if not is_admin and not request.user.is_staff:
            logger.warning(f"Unauthorized inventory PDF access attempt by user {getattr(request.user, 'email', request.user)}")
            return Response(
                {'error': 'Только администраторы могут просматривать отчеты'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from apps.products.models import Products
        
        # Получаем данные об инвентаре
        inventory_data = Products.objects.values(
            'product_id',
            'sku',
            'product_name',
            'category__category_name',
            'stock_quantity'
        ).order_by('-stock_quantity')[:100]  # Top 100 items
        
        data = [
            {
                'sku': item.get('sku', ''),
                'name': item.get('product_name', ''),
                'category': item.get('category__category_name', ''),
                'quantity': item.get('stock_quantity', 0),
            }
            for item in inventory_data
        ]
        
        # Генерируем PDF
        pdf_gen = ReportPDFGenerator()
        pdf_buffer = pdf_gen.generate_inventory_report_pdf(data)
        
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="inventory_report.pdf"'
        
        logger.info(f"Inventory report PDF preview generated")
        return response
        
    except Exception as e:
        logger.error(f"Error generating inventory report PDF: {e}")
        return Response(
            {'error': 'Ошибка при генерации отчета'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
