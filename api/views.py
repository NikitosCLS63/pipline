# api/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from api.permissions import IsAdmin, IsAdminOrEmployee
import random
import string
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import F

# Products
from apps.products.models import (
    Categories, Brands, Suppliers, Products
)
from apps.products.serializers import (
    CategorySerializer, BrandSerializer, SupplierSerializer, ProductSerializer,
    
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Categories.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brands.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Suppliers.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        """Для создания и изменения товаров требуется роль admin или employee"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrEmployee()]
        return [IsAuthenticatedOrReadOnly()]

    def _log_product_change(self, customer, action, product, old_data=None, new_data=None):
        """Логирование изменений товара"""
        try:
            if action == 'UPDATE':
                # Собираем только изменившиеся поля
                changes = []
                fields_to_check = [
                    ('product_name', 'Название'),
                    ('price', 'Цена'),
                    ('stock_quantity', 'Количество'),
                    ('brand_name', 'Бренд'),
                    ('category_name', 'Категория'),
                    ('description', 'Описание')
                ]

                for field_key, field_name in fields_to_check:
                    old_val = old_data.get(field_key, '') if old_data else ''
                    new_val = new_data.get(field_key, '') if new_data else ''
                    if str(old_val) != str(new_val):
                        changes.append(f"{field_name}: '{old_val}' → '{new_val}'")

                if changes:
                    old_value = "Было: " + "; ".join(changes)
                    new_value = "Стало: " + "; ".join(changes)
                else:
                    old_value = "Изменений нет"
                    new_value = "Изменений нет"

            elif action == 'CREATE':
                new_value = f"Создан товар: {new_data.get('product_name', 'N/A')} (Цена: {new_data.get('price', 'N/A')}, Кол-во: {new_data.get('stock_quantity', 'N/A')})" if new_data else ""
                old_value = ""
            elif action == 'DELETE':
                old_value = f"Удален товар: {old_data.get('product_name', 'N/A')} (Цена: {old_data.get('price', 'N/A')}, Кол-во: {old_data.get('stock_quantity', 'N/A')})" if old_data else ""
                new_value = ""

            # audit_user должен быть объектом Customer из таблицы customers
            audit_user = customer if customer and hasattr(customer, 'customer_id') else None

            # Создаем лог только если есть реальные изменения (для UPDATE)
            if action != 'UPDATE' or (action == 'UPDATE' and old_value != "Изменений нет"):
                audit_log = AuditLog.objects.create(
                    user=audit_user,
                    action_type=action,
                    table_name='products',
                    record_id=product.product_id if product else None,
                    old_value=old_value,
                    new_value=new_value
                )
                print(f"[API AUDIT] Product audit log created: log_id={audit_log.log_id}, action={action}, product_id={product.product_id if product else None}")
        except Exception as e:
            print(f"Error logging product change: {e}")

    def perform_update(self, serializer):
        """Переопределение для логирования изменений"""
        print(f"[API AUDIT] perform_update called for product")

        # Получаем старые данные
        old_instance = self.get_object()
        old_data = {
            'product_name': old_instance.product_name,
            'price': str(old_instance.price),
            'stock_quantity': str(old_instance.stock_quantity) if old_instance.stock_quantity else '0',
            'brand_name': old_instance.brand.brand_name if old_instance.brand else 'N/A',
            'category_name': old_instance.category.category_name if old_instance.category else 'N/A',
            'description': old_instance.description[:50] + '...' if old_instance.description and len(old_instance.description) > 50 else (old_instance.description or 'N/A')
        }

        # Сохраняем изменения
        super().perform_update(serializer)

        # Получаем пользователя
        user, customer = get_user_from_request(self.request)

        # Если не нашли через JWT, пробуем через Django auth (для админ-панели)
        if not customer and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                # Ищем customer по email пользователя Django
                customer = Customers.objects.get(email=self.request.user.email)
                print(f"[API AUDIT] Found customer via Django auth: {customer.email}")
            except Customers.DoesNotExist:
                print(f"[API AUDIT] No customer found for Django user: {self.request.user.email}")

        print(f"[API AUDIT] Final user determination: user={user}, customer={customer}")

        # Получаем новые данные
        new_instance = serializer.instance
        new_data = {
            'product_name': new_instance.product_name,
            'price': str(new_instance.price),
            'stock_quantity': str(new_instance.stock_quantity) if new_instance.stock_quantity else '0',
            'brand_name': new_instance.brand.brand_name if new_instance.brand else 'N/A',
            'category_name': new_instance.category.category_name if new_instance.category else 'N/A',
            'description': new_instance.description[:50] + '...' if new_instance.description and len(new_instance.description) > 50 else (new_instance.description or 'N/A')
        }

        # Логируем изменение
        print(f"[API AUDIT] About to log product change with customer: {customer}")
        self._log_product_change(customer, 'UPDATE', new_instance, old_data, new_data)
        print(f"[API AUDIT] Product update logged: {new_instance.product_id}")

    def perform_create(self, serializer):
        """Переопределение для логирования создания"""
        print(f"[API AUDIT] perform_create called for product")

        # Сохраняем новый товар
        super().perform_create(serializer)

        # Получаем пользователя
        user, customer = get_user_from_request(self.request)

        # Если не нашли через JWT, пробуем через Django auth (для админ-панели)
        if not customer and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                # Ищем customer по email пользователя Django
                customer = Customers.objects.get(email=self.request.user.email)
                print(f"[API AUDIT] Found customer via Django auth: {customer.email}")
            except Customers.DoesNotExist:
                print(f"[API AUDIT] No customer found for Django user: {self.request.user.email}")

        print(f"[API AUDIT] Final user determination: user={user}, customer={customer}")

        # Получаем данные нового товара
        new_instance = serializer.instance
        new_data = {
            'product_name': new_instance.product_name,
            'price': str(new_instance.price),
            'stock_quantity': str(new_instance.stock_quantity) if new_instance.stock_quantity else '0',
            'brand_name': new_instance.brand.brand_name if new_instance.brand else 'N/A',
            'category_name': new_instance.category.category_name if new_instance.category else 'N/A',
            'description': new_instance.description[:50] + '...' if new_instance.description and len(new_instance.description) > 50 else (new_instance.description or 'N/A')
        }

        # Логируем создание
        self._log_product_change(customer, 'CREATE', new_instance, None, new_data)
        print(f"[API AUDIT] Product create logged: {new_instance.product_id}")

    def perform_destroy(self, instance):
        """Переопределение для логирования удаления"""
        print(f"[API AUDIT] perform_destroy called for product {instance.product_id}")

        # Получаем пользователя
        user, customer = get_user_from_request(self.request)

        # Если не нашли через JWT, пробуем через Django auth (для админ-панели)
        if not customer and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                # Ищем customer по email пользователя Django
                customer = Customers.objects.get(email=self.request.user.email)
                print(f"[API AUDIT] Found customer via Django auth: {customer.email}")
            except Customers.DoesNotExist:
                print(f"[API AUDIT] No customer found for Django user: {self.request.user.email}")

        print(f"[API AUDIT] Final user determination: user={user}, customer={customer}")

        # Получаем данные удаляемого товара
        old_data = {
            'product_name': instance.product_name,
            'price': str(instance.price),
            'stock_quantity': str(instance.stock_quantity) if instance.stock_quantity else '0',
            'brand_name': instance.brand.brand_name if instance.brand else 'N/A',
            'category_name': instance.category.category_name if instance.category else 'N/A',
            'description': instance.description[:50] + '...' if instance.description and len(instance.description) > 50 else (instance.description or 'N/A')
        }

        # Логируем удаление
        self._log_product_change(customer, 'DELETE', instance, old_data, None)
        print(f"[API AUDIT] Product delete logged: {instance.product_id}")

        # Удаляем товар
        super().perform_destroy(instance)



# Users
from apps.users.models import Customers, Roles, Users, Addresses
from apps.users.serializers import CustomerSerializer, RoleSerializer, UserSerializer, AddressSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customers.objects.all()
    serializer_class = CustomerSerializer
    
    def get_permissions(self):
        """Allow read access for all users, but only admin/employee can modify"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminOrEmployee()]

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Roles.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdmin]
    
    
from rest_framework.permissions import IsAuthenticated


class UserViewSet(viewsets.ModelViewSet):
    queryset = Users.objects.select_related('customer', 'role').all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        # Use a lightweight public serializer for listing/retrieving users
        if self.action in ['list', 'retrieve']:
            from apps.users.serializers import UserListSerializer
            return UserListSerializer
        return super().get_serializer_class()

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Addresses.objects.all()
    serializer_class = AddressSerializer

    def get_permissions(self):
        """Allow read access for all, create for anonymous (checkout), modify only for authenticated"""
        if self.action in ['list', 'retrieve', 'create']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter addresses: show only for specific customer if customer_id provided"""
        queryset = Addresses.objects.all()
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            try:
                return queryset.filter(customer_id=int(customer_id))
            except (ValueError, TypeError):
                pass
        return queryset


# Cart
from apps.cart.models import Carts, CartItems, Wishlists
from apps.cart.serializers import CartSerializer, CartItemSerializer, WishlistSerializer

class CartViewSet(viewsets.ModelViewSet):
    queryset = Carts.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItems.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

class WishlistViewSet(viewsets.ModelViewSet):
    queryset = Wishlists.objects.all()
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_customer_from_token(self):
        """Получает customer_id из JWT токена"""
        try:
            # Попытаемся получить из токена
            from rest_framework_simplejwt.settings import api_settings
            # Prefer DRF-authenticated token (request.auth) but fall back to
            # middleware-provided jwt_token / jwt_customer_id when DRF didn't set request.auth
            if hasattr(self.request, 'auth') and self.request.auth:
                user_id = self.request.auth.get(api_settings.USER_ID_CLAIM)
                if user_id:
                    return user_id

            # Middleware (api.auth_middleware.JWTAuthMiddleware) may have validated
            # the token and stored it on request as `jwt_token` / `jwt_customer_id`.
            if hasattr(self.request, 'jwt_customer_id') and self.request.jwt_customer_id:
                return self.request.jwt_customer_id
            if hasattr(self.request, 'jwt_token') and self.request.jwt_token:
                return self.request.jwt_token.get(api_settings.USER_ID_CLAIM)
        except:
            pass
        return None
    
    def get_customer(self):
        """Получает customer object для текущего пользователя"""
        from apps.users.models import Customers
        import logging
        logger = logging.getLogger(__name__)
        
        # Сначала пытаемся из токена
        customer_id = self.get_customer_from_token()
        if customer_id:
            try:
                customer = Customers.objects.get(customer_id=customer_id)
                logger.info(f'[WISHLIST] Got customer {customer.customer_id} from token')
                return customer
            except Customers.DoesNotExist:
                logger.warning(f'[WISHLIST] Token has customer_id {customer_id} but not found in DB')
        
        # Потом пытаемся по email
        if hasattr(self.request.user, 'email') and self.request.user.email:
            customer = Customers.objects.filter(email=self.request.user.email).first()
            if customer:
                logger.info(f'[WISHLIST] Got customer {customer.customer_id} from email {self.request.user.email}')
                return customer
        
        logger.error(f'[WISHLIST] Could not get customer for request.user={self.request.user}')
        return None
    
    def get_queryset(self):
        """Возвращаем только избранное текущего пользователя"""
        customer = self.get_customer()
        if customer:
            return Wishlists.objects.filter(customer=customer).select_related('product')
        return Wishlists.objects.none()
    
    @action(detail=False, methods=['post'])
    def add_to_wishlist(self, request):
        """Добавить товар в избранное"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id required'}, status=400)
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            customer = self.get_customer()
            if not customer:
                logger.error(f'[WISHLIST] No customer found')
                return Response({'error': 'Customer not found'}, status=401)
            
            logger.info(f'[WISHLIST] Adding product {product_id} to wishlist for customer {customer.customer_id}')
            
            product = Products.objects.get(product_id=product_id)
            
            # Проверяем, не добавлен ли уже в избранное
            existing = Wishlists.objects.filter(customer=customer, product=product).first()
            if existing:
                logger.warning(f'[WISHLIST] Already exists')
                return Response({'error': 'Already in wishlist'}, status=400)
            
            wishlist = Wishlists.objects.create(customer=customer, product=product)
            logger.info(f'[WISHLIST] Success! Created wishlist {wishlist.wishlist_id}')
            serializer = WishlistSerializer(wishlist)
            return Response(serializer.data, status=201)
        except Products.DoesNotExist:
            logger.error(f'[WISHLIST] Product {product_id} not found')
            return Response({'error': 'Product not found'}, status=404)
        except Exception as e:
            logger.error(f'[WISHLIST] Error: {str(e)}', exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def remove_from_wishlist(self, request):
        """Удалить товар из избранного"""
        import logging
        logger = logging.getLogger(__name__)
        
        product_id = request.data.get('product_id')
        if not product_id:
            logger.error(f'[WISHLIST] No product_id provided')
            return Response({'error': 'product_id required'}, status=400)
        
        try:
            # Конвертируем product_id в число 
            try:
                product_id = int(product_id)
            except (ValueError, TypeError):
                logger.error(f'[WISHLIST] Invalid product_id type: {type(product_id)}, value: {product_id}')
                return Response({'error': 'Invalid product_id format'}, status=400)
            
            customer = self.get_customer()
            if not customer:
                logger.error(f'[WISHLIST] No customer found')
                return Response({'error': 'Customer not found'}, status=401)
            
            logger.info(f'[WISHLIST] Removing product {product_id} from wishlist for customer {customer.customer_id}')
            
            # Проверяем существование товара
            from apps.products.models import Products
            try:
                product = Products.objects.get(product_id=product_id)
            except Products.DoesNotExist:
                logger.error(f'[WISHLIST] Product {product_id} not found')
                return Response({'error': 'Product not found'}, status=404)
            
            wishlist = Wishlists.objects.filter(customer=customer, product_id=product_id).first()
            if not wishlist:
                logger.warning(f'[WISHLIST] Product {product_id} not in wishlist for customer {customer.customer_id}')
                return Response({'error': 'Not in wishlist'}, status=404)
            
            wishlist_id = wishlist.wishlist_id
            wishlist.delete()
            logger.info(f'[WISHLIST] Successfully deleted wishlist {wishlist_id}')
            return Response({'message': 'Removed from wishlist', 'success': True}, status=200)
        except Exception as e:
            logger.error(f'[WISHLIST] Error removing from wishlist: {str(e)}', exc_info=True)
            return Response({'error': str(e)}, status=500)


# Orders
from apps.orders.models import Orders, OrderItems, Payments, Shipments, ProductReturns
from apps.orders.serializers import OrderSerializer, OrderItemSerializer, PaymentSerializer, ShipmentSerializer, ProductReturnSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Orders.objects.select_related('customer', 'shipping_address')
    serializer_class = OrderSerializer

    def get_permissions(self):
        """Allow anonymous users to create orders via the API (checkout flow),
        allow viewing by customer_id for list action,
        but require authentication for other operations."""
        if self.action in ['create', 'list']:
            # Allow anonymous for create and list (list will be filtered by customer_id in get_queryset)
            return [AllowAny()]
        return [IsAuthenticated()]

    def _log_order_change(self, customer, action, order, old_data=None, new_data=None):
        """Логирование изменений заказа"""
        try:
            if action == 'UPDATE':
                # Собираем только изменившиеся поля
                changes = []
                fields_to_check = [
                    ('status', 'Статус'),
                    ('total_amount', 'Сумма'),
                    ('payment_method', 'Метод оплаты'),
                    ('payment_status', 'Статус оплаты'),
                    ('customer_email', 'Email клиента')
                ]

                for field_key, field_name in fields_to_check:
                    old_val = old_data.get(field_key, '') if old_data else ''
                    new_val = new_data.get(field_key, '') if new_data else ''
                    if str(old_val) != str(new_val):
                        changes.append(f"{field_name}: '{old_val}' → '{new_val}'")

                if changes:
                    old_value = "Было: " + "; ".join(changes)
                    new_value = "Стало: " + "; ".join(changes)
                else:
                    old_value = "Изменений нет"
                    new_value = "Изменений нет"

            elif action == 'CREATE':
                new_value = f"Создан заказ для клиента: {new_data.get('customer_email', 'N/A')} (Сумма: {new_data.get('total_amount', 'N/A')})" if new_data else ""
                old_value = ""
            elif action == 'DELETE':
                old_value = f"Удален заказ клиента: {old_data.get('customer_email', 'N/A')} (Сумма: {old_data.get('total_amount', 'N/A')})" if old_data else ""
                new_value = ""

            # audit_user должен быть объектом Customer из таблицы customers
            audit_user = customer if customer and hasattr(customer, 'customer_id') else None

            # Создаем лог только если есть реальные изменения (для UPDATE)
            if action != 'UPDATE' or (action == 'UPDATE' and old_value != "Изменений нет"):
                audit_log = AuditLog.objects.create(
                    user=audit_user,
                    action_type=action,
                    table_name='orders',
                    record_id=order.order_id if order else None,
                    old_value=old_value,
                    new_value=new_value
                )
                print(f"[API AUDIT] Order audit log created: log_id={audit_log.log_id}, action={action}, order_id={order.order_id if order else None}")
        except Exception as e:
            print(f"Error logging order change: {e}")

    def perform_update(self, serializer):
        """Переопределение для логирования изменений заказа"""
        print(f"[API AUDIT] perform_update called for order")

        # Получаем старые данные
        old_instance = self.get_object()
        old_data = {
            'status': old_instance.status,
            'total_amount': str(old_instance.total_amount),
            'payment_method': old_instance.payment_method or 'N/A',
            'payment_status': old_instance.payment_status or 'N/A',
            'customer_email': old_instance.customer.email if old_instance.customer else 'N/A'
        }

        # Сохраняем изменения
        super().perform_update(serializer)

        # Получаем пользователя
        user, customer = get_user_from_request(self.request)

        # Если не нашли через JWT, пробуем через Django auth (для админ-панели)
        if not customer and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                # Ищем customer по email пользователя Django
                customer = Customers.objects.get(email=self.request.user.email)
                print(f"[API AUDIT] Found customer via Django auth: {customer.email}")
            except Customers.DoesNotExist:
                print(f"[API AUDIT] No customer found for Django user: {self.request.user.email}")

        print(f"[API AUDIT] Final user determination: user={user}, customer={customer}")

        # Получаем новые данные
        new_instance = serializer.instance
        new_data = {
            'status': new_instance.status,
            'total_amount': str(new_instance.total_amount),
            'payment_method': new_instance.payment_method or 'N/A',
            'payment_status': new_instance.payment_status or 'N/A',
            'customer_email': new_instance.customer.email if new_instance.customer else 'N/A'
        }

        # Логируем изменение
        self._log_order_change(customer, 'UPDATE', new_instance, old_data, new_data)
        print(f"[API AUDIT] Order update logged: {new_instance.order_id}")

    def perform_destroy(self, instance):
        """Переопределение для логирования удаления заказа"""
        print(f"[API AUDIT] perform_destroy called for order {instance.order_id}")

        # Получаем пользователя
        user, customer = get_user_from_request(self.request)

        # Если не нашли через JWT, пробуем через Django auth (для админ-панели)
        if not customer and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                # Ищем customer по email пользователя Django
                customer = Customers.objects.get(email=self.request.user.email)
                print(f"[API AUDIT] Found customer via Django auth: {customer.email}")
            except Customers.DoesNotExist:
                print(f"[API AUDIT] No customer found for Django user: {self.request.user.email}")

        print(f"[API AUDIT] Final user determination: user={user}, customer={customer}")

        # Получаем данные удаляемого заказа
        old_data = {
            'status': instance.status,
            'total_amount': str(instance.total_amount),
            'payment_method': instance.payment_method or 'N/A',
            'payment_status': instance.payment_status or 'N/A',
            'customer_email': instance.customer.email if instance.customer else 'N/A'
        }

        # Логируем удаление
        self._log_order_change(customer, 'DELETE', instance, old_data, None)
        print(f"[API AUDIT] Order delete logged: {instance.order_id}")

        # Удаляем заказ
        super().perform_destroy(instance)

    def get_queryset(self):
        
        from apps.users.models import Users
        from apps.users.decorators import get_user_from_request
        from rest_framework_simplejwt.authentication import JWTAuthentication
        
        queryset = Orders.objects.select_related('customer', 'shipping_address')
        
        # Пытаемся получить пользователя из JWT токена
        user = None
        customer = None
        
        try:
            # Используем helper функцию для получения пользователя
            user, customer = get_user_from_request(self.request)
        except Exception as e:
            print(f"[ORDER_VIEWSET] Error getting user from request: {e}")
        
        # Если не получили через helper, пытаемся через JWT напрямую
        if not user:
            try:
                auth = JWTAuthentication()
                header = auth.get_header(self.request)
                if header:
                    raw_token = auth.get_raw_token(header)
                    if raw_token:
                        validated_token = auth.get_validated_token(raw_token)
                        customer_id = validated_token.get('customer_id')
                        if customer_id:
                            from apps.users.models import Customers
                            customer = Customers.objects.get(customer_id=customer_id)
                            try:
                                user = Users.objects.get(customer=customer)
                            except Users.DoesNotExist:
                                pass
            except Exception as e:
                print(f"[ORDER_VIEWSET] Error in JWT auth: {e}")
        
        
        if user and user.role:
            if user.role.role_name == 'admin':
                print(f"[ORDER_VIEWSET] Admin: returning all orders")
                return queryset.order_by('-order_date')
            elif user.role.role_name == 'employee':
                print(f"[ORDER_VIEWSET] Employee (customer_id={customer.customer_id}): returning their orders")
                return queryset.filter(customer=customer).order_by('-order_date')

        # Authenticated user: see only their orders
        if customer:
            print(f"[ORDER_VIEWSET] Authenticated user (customer_id={customer.customer_id}): returning their orders")
            return queryset.filter(customer=customer).order_by('-order_date')

        # Guest: allow viewing by customer_id query parameter (for post-checkout)
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            try:
                print(f"[ORDER_VIEWSET] Guest with customer_id={customer_id}: returning their orders")
                return queryset.filter(customer_id=int(customer_id)).order_by('-order_date')
            except (ValueError, TypeError):
                pass

        # Default: no orders for anonymous users without customer_id
        print(f"[ORDER_VIEWSET] Anonymous user without customer_id: returning empty queryset")
        return queryset.none()

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItems.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdminOrEmployee]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payments.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminOrEmployee]

class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipments.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [IsAdminOrEmployee]

class ProductReturnViewSet(viewsets.ModelViewSet):
    queryset = ProductReturns.objects.all()
    serializer_class = ProductReturnSerializer
    permission_classes = [IsAuthenticated]


# Reviews
from apps.reviews.models import Reviews
from apps.reviews.serializers import ReviewSerializer
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Reviews.objects.all().select_related('product', 'customer')
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


    def get_queryset(self):
        """Filter reviews by product_id parameter"""
        queryset = Reviews.objects.all().select_related('product', 'customer')
        product_id = self.request.query_params.get('product', None)
        if product_id is not None:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def get_permissions(self):
        """Allow read for everyone, but create/update/delete only for authenticated"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        """Update review - only owner can update"""
        review = self.get_object()
        
        # Check if user is the owner
        if not request.user or not hasattr(request.user, 'customer') or request.user.customer != review.customer:
            raise PermissionDenied("Вы можете редактировать только свои отзывы")
        
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete review - only owner can delete"""
        review = self.get_object()
        
        # Check if user is the owner
        if not request.user or not hasattr(request.user, 'customer') or request.user.customer != review.customer:
            raise PermissionDenied("Вы можете удалять только свои отзывы")
        
        return super().destroy(request, *args, **kwargs)


# Promotions
from apps.promotions.models import Promotions
from apps.promotions.serializers import PromotionSerializer

class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotions.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# Analytics
from apps.analytics.models import AuditLog, Reports, ReportItems, AnalyticsSnapshots, AnalyticsMetrics, BackupLogs
from apps.analytics.serializers import (
    AuditLogSerializer, ReportSerializer, ReportItemSerializer,
    AnalyticsSnapshotSerializer, AnalyticsMetricSerializer, BackupLogSerializer
)

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Reports.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAdminOrEmployee]

class ReportItemViewSet(viewsets.ModelViewSet):
    queryset = ReportItems.objects.all()
    serializer_class = ReportItemSerializer
    permission_classes = [IsAdminOrEmployee]

class AnalyticsSnapshotViewSet(viewsets.ModelViewSet):
    queryset = AnalyticsSnapshots.objects.all()
    serializer_class = AnalyticsSnapshotSerializer
    permission_classes = [IsAdminOrEmployee]

class AnalyticsMetricViewSet(viewsets.ModelViewSet):
    queryset = AnalyticsMetrics.objects.all()
    serializer_class = AnalyticsMetricSerializer
    permission_classes = [IsAdminOrEmployee]

class BackupLogViewSet(viewsets.ModelViewSet):
    queryset = BackupLogs.objects.all()
    serializer_class = BackupLogSerializer
    permission_classes = [IsAdmin]



from django.contrib.auth.hashers import check_password
# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer
from .tokens import CustomRefreshToken
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            return Response({
                "message": "Регистрация успешна",
                "customer_id": customer.customer_id,
                "email": customer.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'detail': 'Введите email и пароль'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customers.objects.get(email__iexact=email)
            user = Users.objects.get(customer=customer)
        except (Customers.DoesNotExist, Users.DoesNotExist):
            return Response({'detail': 'Неверный email или пароль'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка пароля
        if not check_password(password, customer.password_hash):
            return Response({'detail': 'Неверный email или пароль'}, status=status.HTTP_400_BAD_REQUEST)

        role = user.role.role_name

        # ПРОВЕРКА ДЛИНЫ ТОЛЬКО ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
        if role not in ['admin', 'employee']:
            if len(password) < 6:
                return Response({'detail': 'Пароль должен быть не менее 6 символов'}, status=status.HTTP_400_BAD_REQUEST)

        # Генерация токена с customer_id
        refresh = CustomRefreshToken.for_user(customer)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "customer_id": customer.customer_id,
            "role": role,
            "email": customer.email
        })
    



# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from apps.users.models import Customers  
import re
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password

class PasswordResetView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip()

        # Проверка формата email
        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return Response({'error': 'Введите корректный email'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customers.objects.get(email__iexact=email)
        except Customers.DoesNotExist:
            # Безопасность: не говорим, есть ли email
            return Response({'success': 'Если email зарегистрирован, ссылка отправлена'}, status=status.HTTP_200_OK)

        # Генерируем токен
        token = get_random_string(40)
        expires_at = timezone.now() + timedelta(minutes=15)

        customer.password_reset_token = token
        customer.password_reset_expires = expires_at
        customer.save()

        # Ссылка
        reset_url = f"{settings.FRONTEND_URL}/reset-password-confirm/?token={token}&email={email}"
        print("ОТПРАВЛЯЮ ПИСЬМО НА:", email)
        print("ССЫЛКА:", reset_url)
        # Отправляем письмо
        try:
            send_mail(
                subject='Восстановление пароля — SND',
                message=f'''
Здравствуйте!

Вы запросили восстановление пароля.

Перейдите по ссылке, чтобы установить новый пароль:
{reset_url}


Если вы не запрашивали сброс — проигнорируйте это письмо.

С уважением,
Команда SND
                '''.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
               
            )
        except Exception as e:
            print("ОШИБКА SMTP:", e)  # ← Для дебага
            return Response({'error': 'Ошибка отправки email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'success': 'Ссылка отправлена'}, status=status.HTTP_200_OK)
      



import hashlib

class PasswordResetConfirmView(APIView):
    def post(self, request):
        token = request.data.get('token')
        email = request.data.get('email')
        password = request.data.get('password')

        if not all([token, email, password]):
            return Response({'error': 'Заполните все поля'}, status=400)

        try:
            customer = Customers.objects.get(
                email__iexact=email,
                password_reset_token=token
            )
        except Customers.DoesNotExist:
            return Response({'error': 'Неверный токен'}, status=400)

        if customer.password_reset_expires < timezone.now():
            return Response({'error': 'Ссылка истекла'}, status=400)

        # Хешируем пароль используя make_password (PBKDF2)
        customer.password_hash = make_password(password)
        customer.password_reset_token = None
        customer.password_reset_expires = None
        customer.save()

        return Response({'success': 'Пароль изменён'}) 
    

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer



from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import random
import string
import uuid
import os

# YooKassa credentials для SANDBOX (для тестирования)
# Для production замените на реальные учетные данные
YOOKASSA_ACCOUNT_ID = '199347'  # Тестовый shop ID для sandbox
YOOKASSA_SECRET_KEY = 'test_MsLMuEqoKWDEu9o7LLVIQ_k2vRr0Yq1yqr-QBDfMXJk'  # Тестовый ключ для sandbox

# API endpoints
YOOKASSA_SANDBOX_URL = 'https://sandbox.yookassa.ru/api/v3'
YOOKASSA_PRODUCTION_URL = 'https://payment.yookassa.ru/api/v3'

# Используем sandbox по умолчанию, но в режиме MOCK для тестирования без интернета
YOOKASSA_API_URL = YOOKASSA_SANDBOX_URL
USE_MOCK_PAYMENTS = True  # Установите False для реальных платежей с интернетом

@api_view(['POST'])
@permission_classes([AllowAny])
def create_payment(request):
    """
    Create payment in YooKassa and return payment form
    """
    try:
        data = request.data
        
        # Calculate total with delivery
        items_total = float(data.get('total', 0))
        delivery_cost = 349 if data.get('delivery_type') == 'courier' else 0
        total_amount = items_total + delivery_cost
        
        # Validation: минимальная сумма платежа
        if total_amount < 0.01:
            return Response({
                'success': False,
                'error': 'Сумма платежа должна быть больше нуля'
            }, status=400)
        
        if USE_MOCK_PAYMENTS:
            # MOCK режим - симулируем платеж для тестирования
            payment_id = f"mock_{uuid.uuid4().hex[:12]}"
            confirmation_url = f"http://localhost:8000/decoration-success/?payment_id={payment_id}&mock=true"
            
            print(f"[MOCK] Created mock payment: {payment_id}")
            print(f"[MOCK] Confirmation URL: {confirmation_url}")
            
            return Response({
                'success': True,
                'payment_id': payment_id,
                'confirmation_url': confirmation_url,
                'message': 'Переходим на страницу оплаты (ТЕСТОВЫЙ РЕЖИМ)'
            }, status=201)
        else:
            # РЕАЛЬНЫЙ режим - отправляем запрос на YooKassa
            payment_data = {
                "amount": {
                    "value": f"{total_amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "http://localhost:8000/decoration-success/"
                },
                "capture": True,
                "description": f"Заказ от {data.get('first_name')} {data.get('last_name')}",
                "metadata": {
                    "phone": data.get('phone'),
                    "email": data.get('email'),
                    "delivery_type": data.get('delivery_type')
                }
            }
            
            # Create payment using requests directly
            import requests
            from requests.auth import HTTPBasicAuth
            
            print(f"Creating real payment with credentials: {YOOKASSA_ACCOUNT_ID}")
            print(f"Payload: {payment_data}")
            
            response = requests.post(
                f'{YOOKASSA_API_URL}/payments',
                json=payment_data,
                auth=HTTPBasicAuth(YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY),
                headers={
                    'Idempotency-Key': str(uuid.uuid4()),
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                return Response({
                    'success': True,
                    'payment_id': result['id'],
                    'confirmation_url': result['confirmation']['confirmation_url'],
                    'message': 'Переходим на страницу оплаты'
                }, status=201)
            else:
                return Response({
                    'success': False,
                    'error': f'YooKassa error: {response.text}'
                }, status=response.status_code)
        
    except Exception as e:
        import traceback
        print(f"YooKassa Error: {str(e)}")
        print(traceback.format_exc())
        return Response({
            'success': False,
            'error': f'Ошибка при создании платежа: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_payment_status(request):
    """
    Check payment status by payment_id
    """
    try:
        payment_id = request.query_params.get('payment_id')
        is_mock = request.query_params.get('mock') == 'true'
        
        if not payment_id:
            return Response({
                'success': False,
                'error': 'Payment ID not provided'
            }, status=400)
        
        if USE_MOCK_PAYMENTS or is_mock:
            # MOCK режим - автоматически считаем платеж успешным
            print(f"[MOCK] Checking mock payment status: {payment_id}")
            return Response({
                'success': True,
                'payment_id': payment_id,
                'status': 'succeeded',
                'amount': 0,  # Не важно в mock режиме
                'paid': True  # Всегда успешно в mock режиме
            }, status=200)
        else:
            # РЕАЛЬНЫЙ режим - отправляем запрос на YooKassa
            import requests
            from requests.auth import HTTPBasicAuth
            
            response = requests.get(
                f'{YOOKASSA_API_URL}/payments/{payment_id}',
                auth=HTTPBasicAuth(YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                payment = response.json()
                return Response({
                    'success': True,
                    'payment_id': payment['id'],
                    'status': payment['status'],
                    'amount': float(payment['amount']['value']),
                    'paid': payment['status'] == 'succeeded'
                }, status=200)
            else:
                return Response({
                    'success': False,
                    'error': f'Payment not found: {response.text}'
                }, status=response.status_code)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Ошибка при проверке платежа: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    """
    Create order from cart and save to database
    Используется транзакция для атомарности операций
    """
    try:
        from apps.orders.models import Orders, OrderItems
        from apps.users.models import Customers, Addresses, Users
        from apps.products.models import Products
        from apps.users.decorators import get_user_from_request
        from datetime import datetime
        
        order_data = request.data
        
        # Сначала пытаемся получить customer из JWT токена (если пользователь авторизован)
        customer = None
        user = None
        try:
            user, customer = get_user_from_request(request)
            if customer:
                print(f"[CREATE_ORDER] Found authenticated customer {customer.customer_id} from JWT")
        except Exception as e:
            print(f"[CREATE_ORDER] Error getting customer from JWT: {e}")

        # Если не получили из JWT, пытаемся найти по email из order_data
        phone = order_data.get('phone', '')
        email = order_data.get('email', '')
        first_name = order_data.get('first_name', '')
        last_name = order_data.get('last_name', '')

        if not customer and email:
            try:
                customer = Customers.objects.get(email__iexact=email)
                print(f"[CREATE_ORDER] Found existing customer {customer.customer_id} by email {email}")
            except Customers.DoesNotExist:
                pass

        # Initialize address
        address = None

        # If no customer found, create a guest customer
        if not customer:
            import hashlib
            import uuid
            # Create a guest customer with unique email
            if email:
                guest_email = email
            else:
                # Create unique email using phone hash
                phone_hash = hashlib.md5(phone.encode()).hexdigest()[:8]
                guest_email = f"guest_{phone_hash}@store.local"

            try:
                customer = Customers.objects.create(
                    first_name=first_name or 'Guest',
                    last_name=last_name or 'Customer',
                    email=guest_email,
                    password_hash=hashlib.sha256(phone.encode()).hexdigest(),
                    phone=phone,
                    created_at=timezone.now()
                )
            except Exception as customer_error:
                # If email already exists, try with UUID
                try:
                    unique_id = str(uuid.uuid4())[:8]
                    guest_email = f"guest_{unique_id}@store.local"
                    customer = Customers.objects.create(
                        first_name=first_name or 'Guest',
                        last_name=last_name or 'Customer',
                        email=guest_email,
                        password_hash=hashlib.sha256(phone.encode()).hexdigest(),
                        phone=phone,
                        created_at=timezone.now()
                    )
                except Exception as second_error:
                    # If still fails, use first customer as default
                    customer = Customers.objects.first()
                    if not customer:
                        return Response({
                            'success': False,
                            'error': 'Не удалось создать заказ. Попробуйте позже.'
                        }, status=500)

        # Теперь начинаем транзакцию для создания заказа и элементов
        with transaction.atomic():
            
            # Create shipping address — pickup option removed: only delivery by address allowed

            # Разрешённые значения type для addresses (уточните по вашей БД)
            address_type = 'shipping'  # Всегда используем 'shipping' для соответствия constraint

            # Require at least city and street for delivery
            country = order_data.get('country', '').strip()
            region = order_data.get('region', '').strip()
            city = order_data.get('city', '').strip()
            street = order_data.get('street', '').strip()
            house = order_data.get('house', '').strip()
            apartment = order_data.get('apartment', '').strip()
            
            if not city or not street:
                return Response({
                    'success': False,
                    'error': 'Для оформления заказа по адресу укажите город и улицу.'
                }, status=400)

            # Формируем полный адрес из отдельных полей
            address_parts = []
            if country:
                address_parts.append(country)
            if region:
                address_parts.append(region)
            if city:
                address_parts.append(city)
            if street:
                address_parts.append(street)
            if house:
                address_parts.append(f'д. {house}')
            if apartment:
                address_parts.append(f'кв. {apartment}')
            
            full_address = ', '.join(address_parts) if address_parts else ''
            
            # Если full_address передан отдельно, используем его, иначе формируем из полей
            if order_data.get('full_address', '').strip():
                full_address = order_data.get('full_address', '').strip()

            # Проверяем существующий адрес (из-за unique_together constraint)
            address = Addresses.objects.filter(customer=customer, type='shipping').first()
            if address:
                # Обновляем существующий адрес
                try:
                    address.country = country
                    address.region = region
                    address.city = city
                    address.street = street
                    address.house = house
                    address.apartment = apartment
                    address.full_address = full_address
                    address.updated_at = timezone.now()
                    address.save()
                    print(f"[ADDRESS] Обновлен существующий адрес: ID={address.address_id}, customer={customer.customer_id}, {full_address}")
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Ошибка при обновлении адреса: {str(e)}'
                    }, status=400)
            else:
                # Создаем новый адрес
                try:
                    address = Addresses.objects.create(
                        customer=customer,
                        country=country,
                        region=region,
                        city=city,
                        street=street,
                        house=house,
                        apartment=apartment,
                        type='shipping',
                        full_address=full_address,
                        created_at=timezone.now()
                    )
                    print(f"[ADDRESS] Создан новый адрес: ID={address.address_id}, customer={customer.customer_id}, {full_address}")
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'Ошибка при создании адреса: {str(e)}',
                        'address_data': {
                            'customer_id': customer.customer_id,
                            'country': country,
                            'region': region,
                            'city': city,
                            'street': street,
                            'house': house,
                            'apartment': apartment,
                            'type': address_type,
                            'full_address': full_address
                        }
                    }, status=400)
        
            # Calculate total amount
            items = order_data.get('items', [])
            total_amount = 0
            
            # Проверяем наличие всех товаров ПЕРЕД созданием заказа
            if not items:
                return Response({
                    'success': False,
                    'error': 'Корзина пуста. Добавьте товары в корзину перед оформлением заказа.'
                }, status=400)
            
            # Предварительная проверка всех товаров на наличие
            products_to_check = {}
            item_errors = []
            print(f"[CREATE_ORDER] Получено {len(items)} товаров для проверки")
            for idx, item in enumerate(items):
                try:
                    print(f"[CREATE_ORDER] Проверяем товар #{idx}: {item}")
                    product_id = item.get('product_id')
                    quantity = item.get('quantity', 1)

                    if not product_id:
                        item_errors.append(f'Товар #{idx}: отсутствует product_id')
                        continue

                    try:
                        product_id = int(product_id)
                        quantity = int(quantity)
                    except (ValueError, TypeError) as ve:
                        item_errors.append(f'Товар #{idx}: некорректный тип данных - {str(ve)}')
                        print(f"[CREATE_ORDER] Ошибка типа: product_id={product_id} (тип {type(product_id)}), quantity={quantity} (тип {type(quantity)})")
                        continue

                    if quantity <= 0:
                        item_errors.append(f'Товар {product_id}: некорректное количество {quantity}')
                        continue

                    try:
                        product = Products.objects.select_for_update().get(product_id=product_id)
                        # Логируем актуальное значение stock_quantity
                        print(f"[CHECK_STOCK] Товар {product_id} ({product.product_name}): stock_quantity={product.stock_quantity}, запрошено={quantity}")
                        # Проверяем наличие товара (блокируем для обновления)
                        if product.stock_quantity is not None and product.stock_quantity < quantity:
                            item_errors.append(f'Товар {product.product_name}: недостаточно товара на складе (доступно: {product.stock_quantity}, запрошено: {quantity})')
                            print(f"[STOCK_ERROR] Товар {product_id}: недостаточно запасов")
                            continue

                        products_to_check[product_id] = {
                            'product': product,
                            'quantity': quantity,
                            'price': product.price
                        }
                    except Products.DoesNotExist:
                        item_errors.append(f'Товар {product_id}: товар не найден')
                        print(f"[CREATE_ORDER] Товар {product_id} не найден в БД")
                        continue
                except Exception as e:
                    item_errors.append(f'Ошибка при обработке товара #{idx}: {str(e)}')
                    print(f"[CREATE_ORDER] Неожиданная ошибка: {e}")
                    continue

            # Если есть ошибки, возвращаем их с подробностями
            if item_errors:
                error_message = 'Ошибки при проверке товаров: ' + '; '.join(item_errors[:5])
                print(f"[CREATE_ORDER] Ошибки валидации: {item_errors}")
                print(f"[CREATE_ORDER] Request data: {order_data}")
                return Response({
                    'success': False,
                    'error': error_message,
                    'details': item_errors[:5]
                }, status=400)
        
            # Если не найдено ни одного товара, возвращаем ошибку
            if not products_to_check:
                return Response({
                    'success': False,
                    'error': 'Не удалось найти товары для заказа.'
                }, status=400)
            
            # Создаем заказ
            import uuid
            tracking_number = f'TRK-{uuid.uuid4().hex[:8].upper()}'
            # Определяем payment_method и payment_status в зависимости от типа оплаты
            payment_type = order_data.get('payment_type', 'online')
            if payment_type == 'on_delivery':
                payment_method = order_data.get('payment_method', 'cash')
                payment_status = 'pending'  # Оплата ожидается при получении
            else:
                payment_method = order_data.get('payment_method', 'card')
                payment_status = 'completed'  # Для онлайн оплаты статус будет обновлен после оплаты
            
            order = Orders.objects.create(
                customer=customer,
                order_date=timezone.now(),
                total_amount=0,  # Will be calculated from items
                status='new',  # Используем разрешённое значение
                payment_method=payment_method,
                payment_status=payment_status,
                shipping_address=address,
                tracking_number=tracking_number
            )

            # Логируем создание заказа
            try:
                user, current_customer = get_user_from_request(request)

                # Если не нашли через JWT, пробуем через Django auth (для админ-панели)
                if not current_customer and hasattr(request, 'user') and request.user.is_authenticated:
                    try:
                        # Ищем customer по email пользователя Django
                        current_customer = Customers.objects.get(email=request.user.email)
                        print(f"[API AUDIT] Found customer via Django auth for order: {current_customer.email}")
                    except Customers.DoesNotExist:
                        print(f"[API AUDIT] No customer found for Django user: {request.user.email}")

                print(f"[API AUDIT] Creating order audit log. User: {user}, Customer: {current_customer}")

                order_create_data = {
                    'total_amount': '0',  # Пока 0, будет рассчитано позже
                    'customer_email': customer.email,
                    'status': 'new',
                    'payment_method': payment_method
                }
                from apps.analytics.models import AuditLog
                audit_log = AuditLog.objects.create(
                    user=current_customer if current_customer else customer,
                    action_type='CREATE',
                    table_name='orders',
                    record_id=order.order_id,
                    old_value="",
                    new_value=f"Создан заказ: Сумма будет рассчитана, Клиент: {customer.email}, Метод оплаты: {payment_method}"
                )
                print(f"[API AUDIT] Order creation logged in DB: log_id={audit_log.log_id}")
            except Exception as audit_error:
                print(f"Error logging order creation: {audit_error}")

            # Создаем элементы заказа и уменьшаем количество товаров атомарно
            created_items = []
            for item in items:
                product_id = int(item.get('product_id'))
                quantity = int(item.get('quantity', 1))
                if product_id not in products_to_check:
                    continue
                product_data = products_to_check[product_id]
                product = product_data['product']
                price = product_data['price']
                # Сначала уменьшаем stock_quantity, потом создаём OrderItems
                try:
                    # Атомарно уменьшаем количество товара ПЕРЕД созданием элемента заказа
                    # Это избегает срабатывания триггера update_stock_on_order
                    updated = Products.objects.filter(
                        product_id=product_id,
                        stock_quantity__gte=quantity
                    ).update(stock_quantity=F('stock_quantity') - quantity)
                    
                    if updated == 0:
                        # Если не обновилось, значит товара недостаточно
                        product.refresh_from_db()
                        print(f"[STOCK_CHECK_FAIL] Товар {product_id}: запрошено {quantity}, доступно {product.stock_quantity}")
                        return Response({
                            'success': False,
                            'error': f'Недостаточно товара для продукта {product.product_name}. Попробуйте позже.'
                        }, status=400)
                    
                    print(f"[STOCK_DECREASED] Товар {product_id}: уменьшено на {quantity}")
                    
                    # Теперь создаём элемент заказа (без триггера, т.к. stock уже уменьшен)
                    order_item = OrderItems.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price_at_purchase=price
                    )
                    created_items.append(order_item)
                    total_amount += float(price) * quantity
                except Exception as item_error:
                    error_msg = str(item_error)
                    print(f"[ORDER_ITEM_ERROR] Ошибка при создании элемента заказа: {error_msg}")
                    # Не пытаемся делать rollback внутри atomic блока при ошибке
                    # Просто возвращаем ошибку и позволяем atomic() откатить всё
                    return Response({
                        'success': False,
                        'error': f'Ошибка при создании заказа: недостаточно товара или внутренняя ошибка'
                    }, status=400)
        
            # Обновляем итоговую сумму заказа
            order.total_amount = total_amount
            # Если нужна фиксированная стоимость доставки, просто добавьте:
            order.total_amount += 349  # фиксированная доставка
            order.save(update_fields=['total_amount'])

            # Очищаем корзину покупателя (если есть)
            try:
                from apps.cart.models import Carts, CartItems
                cart = Carts.objects.filter(customer=customer).first()
                if cart:
                    deleted_count = CartItems.objects.filter(cart=cart).delete()[0]
                    print(f'[ORDER] Корзина очищена: удалено {deleted_count} товаров из корзины customer={customer.customer_id}')
                else:
                    print(f'[ORDER] Корзина не найдена для customer={customer.customer_id}')
            except Exception as cart_error:
                # не критично, логируем и продолжаем
                print(f'[ORDER] Не удалось очистить корзину автоматически: {cart_error}')
        
        # Генерируем ID заказа для отображения
        order_id = f'ORD_{order.order_id:08d}'
        transaction_id = order_data.get('transaction_id', 'TXN_' + str(order.order_id))
        
        # Логируем успешное создание заказа
        print(f"[ORDER] Заказ успешно создан: ID={order.order_id}, товаров={len(created_items)}, сумма={order.total_amount}")
        
        return Response({
            'success': True,
            'order_id': order_id,
            'order_db_id': order.order_id,
            'customer_id': order.customer.customer_id,
            'transaction_id': transaction_id,
            'total': float(order.total_amount),
            'items_count': len(created_items),
            'message': 'Заказ успешно создан'
        }, status=201)
        
    except Exception as e:
        import traceback
        print(f"Error creating order: {str(e)}")
        print(traceback.format_exc())
        return Response({
            'success': False,
            'error': f'Ошибка при создании заказа: {str(e)}'
        }, status=500)


@api_view(['GET'])
def order_receipt(request, order_id):
    """
    Return HTML receipt for an order. User can download as HTML.
    """
    # Support cookie-based or middleware-provided JWT for browser downloads.
    try:
        from apps.users.decorators import get_user_from_request
        user, customer = get_user_from_request(request)
        if user:
            request.current_user = user
        if customer:
            request.current_customer = customer
    except Exception:
        # If helper not available or fails, continue and allow DRF auth to run
        pass

    # If neither middleware/COOKIE-based nor DRF auth provided identity, reject
    if not getattr(request, 'current_user', None) and not getattr(request, 'current_customer', None):
        return Response({'error': 'Требуется авторизация'}, status=401)
    try:
        order = Orders.objects.get(order_id=order_id)
        # Check permission: only customer or admin can view
        customer = getattr(request, 'current_customer', None)
        if customer and order.customer != customer:
            # Check if user is admin
            user = getattr(request, 'current_user', None)
            if not user or user.role.role_name != 'admin':
                return Response({'error': 'Доступ запрещён'}, status=403)
    except Orders.DoesNotExist:
        return Response({'error': 'Заказ не найден'}, status=404)
    
    # Fetch order items
    items = OrderItems.objects.filter(order=order).select_related('product')
    
    # Функция для перевода статусов на русский
    def translate_status(status):
        status_map = {
            'new': 'Новый',
            'processing': 'В обработке',
            'shipped': 'Отправлен',
            'delivered': 'Доставлен',
            'cancelled': 'Отменен',
            'pending': 'Ожидает оплаты'
        }
        return status_map.get(status, status)
    
    def translate_payment_method(method):
        method_map = {
            'card': 'Банковская карта',
            'cash': 'Наличные',
            'online': 'Онлайн оплата',
            'on_delivery': 'При получении'
        }
        return method_map.get(method, method)
    
    def translate_payment_status(status):
        status_map = {
            'completed': 'Оплачено',
            'pending': 'Ожидает оплаты',
            'failed': 'Ошибка оплаты',
            'refunded': 'Возврат'
        }
        return status_map.get(status, status)
    
    # Generate HTML receipt
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Чек заказа #{order.order_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .receipt {{ max-width: 600px; margin: 0 auto; border: 1px solid #ccc; padding: 20px; }}
            .header {{ text-align: center; font-size: 18px; font-weight: bold; margin-bottom: 20px; }}
            .info {{ margin-bottom: 12px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background: #f5f5f5; }}
            .total {{ font-weight: bold; font-size: 16px; }}
            .footer {{ margin-top: 20px; text-align: center; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">✓ ЧЕК ЗАКАЗА</div>
            <div class="info"><strong>Номер заказа:</strong> ORD_{order.order_id:08d}</div>
            <div class="info"><strong>Дата:</strong> {order.order_date.strftime('%d.%m.%Y %H:%M')}</div>
            <div class="info"><strong>Клиент:</strong> {order.customer.email if order.customer.email else f"Клиент #{order.customer_id}"}</div>
            <div class="info"><strong>Статус:</strong> {translate_status(order.status)}</div>
            
            <table>
                <thead>
                    <tr>
                        <th>Товар</th>
                        <th>Кол-во</th>
                        <th>Цена</th>
                        <th>Сумма</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for item in items:
        product_name = item.product.product_name if item.product else 'Unknown'
        sum_item = item.quantity * item.price_at_purchase
        html_content += f"""
                    <tr>
                        <td>{product_name}</td>
                        <td>{item.quantity}</td>
                        <td>{item.price_at_purchase:.2f} ₽</td>
                        <td>{sum_item:.2f} ₽</td>
                    </tr>
        """
    
    html_content += f"""
                </tbody>
            </table>
            
            <div class="info" style="text-align: right;">
                <div class="total">Итого: {order.total_amount:.2f} ₽</div>
            </div>
            
            <div class="info"><strong>Способ оплаты:</strong> {translate_payment_method(order.payment_method) if order.payment_method else 'Не указан'}</div>
            <div class="info"><strong>Статус платежа:</strong> {translate_payment_status(order.payment_status) if order.payment_status else 'Не указан'}</div>
            
            <div class="footer">
                <p>Спасибо за покупку! SND Shop</p>
                <p>Распечатайте этот чек для личного использования.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    from django.http import HttpResponse
    response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="receipt_ORD_{order.order_id:08d}.html"'
    return response


# api/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from apps.users.models import Users, Customers
from apps.users.serializers import UserSerializer

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_me(request):
    """Get, update, or delete current user profile"""
    try:
        # Get user and customer from JWT
        from apps.users.decorators import get_user_from_request
        user, customer = get_user_from_request(request)
        if not user or not customer:
            return Response({'error': 'Пользователь не найден'}, status=404)
        if request.method == 'GET':
            data = {
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'phone': customer.phone
            }
            return Response(data)
        elif request.method == 'PUT':
            data = request.data
            customer.first_name = data.get('first_name', customer.first_name)
            customer.last_name = data.get('last_name', customer.last_name)
            customer.email = data.get('email', customer.email)
            customer.phone = data.get('phone', customer.phone)
            customer.save()
            return Response({'success': True})
        elif request.method == 'DELETE':
            user.delete()
            customer.delete()
            return Response({'success': True})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


