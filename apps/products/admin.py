from django.contrib import admin
from .models import Categories, Brands, Suppliers, Products, Inventory

# ОСТАВЬ ТОЛЬКО @admin.register ДЛЯ ВСЕХ

@admin.register(Brands)
class BrandsAdmin(admin.ModelAdmin):
    list_display = ['brand_name', 'logo_url']
    search_fields = ['brand_name']
    list_editable = ['logo_url']
    ordering = ['brand_name']

    def save_model(self, request, obj, form, change):
        """Логирование изменений брендов"""
        print(f"[ADMIN AUDIT] Brands save_model called: change={change}, obj={obj.brand_name}")

        # Логируем изменения перед сохранением
        if change:
            # Получаем старые данные
            old_obj = Brands.objects.get(pk=obj.pk)
            old_data = {
                'brand_name': old_obj.brand_name,
                'logo_url': old_obj.logo_url or 'Нет логотипа'
            }
            action_type = 'UPDATE'
            print(f"[ADMIN AUDIT] Updating brand: {old_obj.brand_name} -> {obj.brand_name}")
        else:
            old_data = None
            action_type = 'CREATE'
            print(f"[ADMIN AUDIT] Creating brand: {obj.brand_name}")

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

            # Собираем новые данные
            new_data = {
                'brand_name': obj.brand_name,
                'logo_url': obj.logo_url or 'Нет логотипа'
            }

            # Создаем лог только если есть изменения (для UPDATE)
            if action_type == 'CREATE':
                new_value = f"Создан бренд: {new_data.get('brand_name', 'N/A')}"
                old_value = ""
                audit_log = AuditLog.objects.create(
                    user=audit_user,
                    action_type=action_type,
                    table_name='brands',
                    record_id=obj.brand_id,
                    old_value=old_value,
                    new_value=new_value
                )
                print(f"[ADMIN AUDIT] Brand CREATE log created: id={audit_log.log_id}, user={audit_user}")
            elif action_type == 'UPDATE':
                # Проверяем, что изменилось
                changes = []
                for field in ['brand_name', 'logo_url']:
                    old_val = old_data.get(field, '')
                    new_val = new_data.get(field, '')
                    if str(old_val) != str(new_val):
                        field_names = {
                            'brand_name': 'Название бренда',
                            'logo_url': 'URL логотипа'
                        }
                        changes.append(f"{field_names[field]}: '{old_val}' → '{new_val}'")

                if changes:
                    old_value = "Было: " + "; ".join(changes)
                    new_value = "Стало: " + "; ".join(changes)
                    audit_log = AuditLog.objects.create(
                        user=audit_user,
                        action_type=action_type,
                        table_name='brands',
                        record_id=obj.brand_id,
                        old_value=old_value,
                        new_value=new_value
                    )
                    print(f"[ADMIN AUDIT] Brand UPDATE log created: id={audit_log.log_id}, changes={len(changes)}")
                else:
                    print(f"[ADMIN AUDIT] No changes detected for brand update")
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение
            print(f"Error logging brand change in admin: {e}")

@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'parent']
    list_filter = ['parent']
    search_fields = ['category_name']
    ordering = ['category_name']

    def save_model(self, request, obj, form, change):
        """Логирование изменений категорий"""
        print(f"[ADMIN AUDIT] Categories save_model called: change={change}, obj={obj.category_name}")

        # Логируем изменения перед сохранением
        if change:
            # Получаем старые данные
            old_obj = Categories.objects.get(pk=obj.pk)
            old_data = {
                'category_name': old_obj.category_name,
                'parent_name': old_obj.parent.category_name if old_obj.parent else 'Нет',
                'description': old_obj.description or 'Нет описания'
            }
            action_type = 'UPDATE'
            print(f"[ADMIN AUDIT] Updating category: {old_obj.category_name} -> {obj.category_name}")
        else:
            old_data = None
            action_type = 'CREATE'
            print(f"[ADMIN AUDIT] Creating category: {obj.category_name}")

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

            # Собираем новые данные
            new_data = {
                'category_name': obj.category_name,
                'parent_name': obj.parent.category_name if obj.parent else 'Нет',
                'description': obj.description or 'Нет описания'
            }

            # Создаем лог только если есть изменения (для UPDATE)
            if action_type == 'CREATE':
                new_value = f"Создана категория: {new_data.get('category_name', 'N/A')}"
                old_value = ""
                audit_log = AuditLog.objects.create(
                    user=audit_user,
                    action_type=action_type,
                    table_name='categories',
                    record_id=obj.category_id,
                    old_value=old_value,
                    new_value=new_value
                )
                print(f"[ADMIN AUDIT] Category CREATE log created: id={audit_log.log_id}, user={audit_user}")
            elif action_type == 'UPDATE':
                # Проверяем, что изменилось
                changes = []
                for field in ['category_name', 'parent_name', 'description']:
                    old_val = old_data.get(field, '')
                    new_val = new_data.get(field, '')
                    if str(old_val) != str(new_val):
                        field_names = {
                            'category_name': 'Название категории',
                            'parent_name': 'Родительская категория',
                            'description': 'Описание'
                        }
                        changes.append(f"{field_names[field]}: '{old_val}' → '{new_val}'")

                if changes:
                    old_value = "Было: " + "; ".join(changes)
                    new_value = "Стало: " + "; ".join(changes)
                    audit_log = AuditLog.objects.create(
                        user=audit_user,
                        action_type=action_type,
                        table_name='categories',
                        record_id=obj.category_id,
                        old_value=old_value,
                        new_value=new_value
                    )
                    print(f"[ADMIN AUDIT] Category UPDATE log created: id={audit_log.log_id}, changes={len(changes)}")
                else:
                    print(f"[ADMIN AUDIT] No changes detected for category update")
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение
            print(f"Error logging category change in admin: {e}")


# ДОБАВЬ ДЛЯ ОСТАЛЬНЫХ (Suppliers, Products, Inventory)

@admin.register(Suppliers)
class SuppliersAdmin(admin.ModelAdmin):
    list_display = ['supplier_name', 'email', 'phone']
    search_fields = ['supplier_name', 'email']
    ordering = ['supplier_name']


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'brand', 'category', 'price']
    list_filter = ['brand', 'category']
    search_fields = ['product_name']
    ordering = ['product_name']
    
    def get_exclude(self, request, obj=None):
        """Скрыть поле `supplier` при создании нового товара в админке."""
        excludes = super().get_exclude(request, obj) or []
        if obj is None:
            # при добавлении нового объекта скрываем поле поставщика
            return list(excludes) + ['supplier']
        return excludes

    def save_model(self, request, obj, form, change):
        """Если при создании не указан поставщик, подставим первый доступный (если есть)."""
        # Логируем изменения перед сохранением
        if change:
            # Получаем старые данные
            old_obj = Products.objects.get(pk=obj.pk)
            old_data = {
                'product_name': old_obj.product_name,
                'price': str(old_obj.price),
                'stock_quantity': str(old_obj.stock_quantity) if old_obj.stock_quantity else '0',
                'brand_name': old_obj.brand.brand_name if old_obj.brand else 'N/A',
                'category_name': old_obj.category.category_name if old_obj.category else 'N/A',
            }

            action_type = 'UPDATE'
        else:
            old_data = None
            action_type = 'CREATE'

        if not change and not getattr(obj, 'supplier', None):
            default_supplier = Suppliers.objects.first()
            if default_supplier:
                obj.supplier = default_supplier

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
                        # Django admin пользователи могут иметь username как email
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

            # Собираем новые данные
            new_data = {
                'product_name': obj.product_name,
                'price': str(obj.price),
                'stock_quantity': str(obj.stock_quantity) if obj.stock_quantity else '0',
                'brand_name': obj.brand.brand_name if obj.brand else 'N/A',
                'category_name': obj.category.category_name if obj.category else 'N/A',
            }

            # Создаем лог только если есть изменения
            if action_type == 'CREATE':
                new_value = f"Создан товар: {new_data.get('product_name', 'N/A')} (Цена: {new_data.get('price', 'N/A')}, Кол-во: {new_data.get('stock_quantity', 'N/A')})"
                old_value = ""
                AuditLog.objects.create(
                    user=audit_user,
                    action_type=action_type,
                    table_name='products',
                    record_id=obj.product_id,
                    old_value=old_value,
                    new_value=new_value
                )
            elif action_type == 'UPDATE':
                # Проверяем, что изменилось
                changes = []
                for field in ['product_name', 'price', 'stock_quantity', 'brand_name', 'category_name']:
                    old_val = old_data.get(field, '')
                    new_val = new_data.get(field, '')
                    if str(old_val) != str(new_val):
                        changes.append(f"{field}: '{old_val}' → '{new_val}'")

                if changes:
                    old_value = "Было: " + "; ".join(changes)
                    new_value = "Стало: " + "; ".join(changes)
                    AuditLog.objects.create(
                        user=audit_user,
                        action_type=action_type,
                        table_name='products',
                        record_id=obj.product_id,
                        old_value=old_value,
                        new_value=new_value
                    )
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение
            print(f"Error logging product change in admin: {e}")


# apps/products/admin.py
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'warehouse_id', 'updated_at']
    list_filter = ['warehouse_id', 'updated_at']
    search_fields = ['product__product_name', 'product__sku']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']