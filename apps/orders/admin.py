from django.contrib import admin
from .models import Orders, OrderItems, Shipments, ProductReturns, Payments

@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer', 'order_date', 'status', 'total_amount', 'payment_method']
    list_filter = ['status', 'payment_method', 'order_date']
    search_fields = ['order_id', 'customer__email', 'customer__first_name', 'customer__last_name']
    ordering = ['-order_date']

    def save_model(self, request, obj, form, change):
        """Логирование изменений заказов в админке"""
        # Логируем изменения перед сохранением
        if change:
            # Получаем старые данные
            old_obj = Orders.objects.get(pk=obj.pk)
            old_data = {
                'status': old_obj.status,
                'total_amount': str(old_obj.total_amount),
                'payment_method': old_obj.payment_method or 'N/A',
                'payment_status': old_obj.payment_status or 'N/A',
                'customer_email': old_obj.customer.email if old_obj.customer else 'N/A'
            }
            action_type = 'UPDATE'
        else:
            old_data = None
            action_type = 'CREATE'

        super().save_model(request, obj, form, change)

        # Логируем изменения после сохранения
        try:
            from apps.analytics.models import AuditLog
            from apps.users.models import Customers

            # Определяем пользователя
            audit_user = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Пробуем найти по email
                try:
                    audit_user = Customers.objects.get(email=request.user.email)
                    print(f"[ADMIN AUDIT] Found user by email: {request.user.email}")
                except Customers.DoesNotExist:
                    # Если не нашли по email, пробуем по username (для admin пользователей)
                    try:
                        audit_user = Customers.objects.get(email=request.user.username)
                        print(f"[ADMIN AUDIT] Found user by username: {request.user.username}")
                    except Customers.DoesNotExist:
                        print(f"[ADMIN AUDIT] User not found in customers table: email={request.user.email}, username={request.user.username}")
                        # Создаем системного пользователя для админских действий
                        try:
                            audit_user = Customers.objects.get_or_create(
                                email='system@admin.local',
                                defaults={
                                    'first_name': 'Системный',
                                    'last_name': 'Администратор',
                                    'password_hash': 'system_admin_hash',
                                    'phone': '0000000000'
                                }
                            )[0]
                            print(f"[ADMIN AUDIT] Created/Found system admin user: {audit_user.email}")
                        except Exception as e:
                            print(f"[ADMIN AUDIT] Error with system user: {e}")
                            audit_user = None

            if action_type == 'CREATE':
                new_value = f"Создан заказ для клиента: {obj.customer.email if obj.customer else 'N/A'} (Сумма: {obj.total_amount})"
                old_value = ""
                AuditLog.objects.create(
                    user=audit_user,
                    action_type=action_type,
                    table_name='orders',
                    record_id=obj.order_id,
                    old_value=old_value,
                    new_value=new_value
                )
            elif action_type == 'UPDATE':
                # Собираем новые данные
                new_data = {
                    'status': obj.status,
                    'total_amount': str(obj.total_amount),
                    'payment_method': obj.payment_method or 'N/A',
                    'payment_status': obj.payment_status or 'N/A',
                    'customer_email': obj.customer.email if obj.customer else 'N/A'
                }

                # Проверяем, что изменилось
                changes = []
                for field in ['status', 'total_amount', 'payment_method', 'payment_status']:
                    old_val = old_data.get(field, '')
                    new_val = new_data.get(field, '')
                    if str(old_val) != str(new_val):
                        field_names = {
                            'status': 'Статус',
                            'total_amount': 'Сумма',
                            'payment_method': 'Метод оплаты',
                            'payment_status': 'Статус оплаты'
                        }
                        changes.append(f"{field_names[field]}: '{old_val}' → '{new_val}'")

                if changes:
                    old_value = "Было: " + "; ".join(changes)
                    new_value = "Стало: " + "; ".join(changes)
                    AuditLog.objects.create(
                        user=audit_user,
                        action_type=action_type,
                        table_name='orders',
                        record_id=obj.order_id,
                        old_value=old_value,
                        new_value=new_value
                    )
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение
            print(f"Error logging order change in admin: {e}")

admin.site.register(OrderItems)
admin.site.register(Shipments)
admin.site.register(ProductReturns)
admin.site.register(Payments)