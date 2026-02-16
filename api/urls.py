# api/urls.py
from django.urls import path, include
from rest_framework import routers
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = routers.DefaultRouter()

# Products
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'products', ProductViewSet)

# Users - убираем UserViewSet из router
# Используем только custom users_api view
router.register(r'customers', CustomerViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'addresses', AddressViewSet)

# Cart
router.register(r'carts', CartViewSet)
router.register(r'cart-items', CartItemViewSet)
router.register(r'wishlists', WishlistViewSet)

# Orders
router.register(r'orders', OrderViewSet)
router.register(r'order-items', OrderItemViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'shipments', ShipmentViewSet)
router.register(r'product-returns', ProductReturnViewSet)

# Reviews
router.register(r'reviews', ReviewViewSet)

# Promotions
router.register(r'promotions', PromotionViewSet)

# Analytics
router.register(r'audit-logs', AuditLogViewSet)
router.register(r'reports', ReportViewSet)
router.register(r'report-items', ReportItemViewSet)
router.register(r'analytics-snapshots', AnalyticsSnapshotViewSet)
router.register(r'analytics-metrics', AnalyticsMetricViewSet)
router.register(r'backup-logs', BackupLogViewSet)

from apps.users.views import users_api
from apps.orders.pdf_views import (
    order_pdf_preview, 
    order_pdf_download,
    sales_report_pdf_preview,
    inventory_report_pdf_preview
)
from .debug_views import (
    check_duplicate_orders_api,
    check_duplicate_addresses_api,
    get_order_creation_log_api,
    check_password_reset_token_api,
    clear_expired_tokens_api,
    system_health_check,
    debug_current_user_setting
)
from .sql_views import (
    sql_revenue_by_category,
    sql_sales_by_brand,
    sql_order_statistics,
    sql_product_ratings,
    sql_sales_report,
    sql_process_product_return,
    sql_create_monthly_snapshot,
    sql_dashboard_stats,
    sql_trigger_price_changes,
    sql_trigger_order_status_changes,
    sql_trigger_review_creations,
    sql_trigger_payment_records
)

urlpatterns = [
    # === АВТОРИЗАЦИЯ ===
    path('login/', views.LoginView.as_view(), name='api_login'),
    path('register/', views.RegisterView.as_view(), name='api_register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password_reset/', views.PasswordResetView.as_view()),
    path('password_reset_confirm/', views.PasswordResetConfirmView.as_view()),
    
    # JWT токены
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # === PAYMENT PROCESSING ===
    path('payment/create/', views.create_payment, name='create_payment'),
    path('payment/status/', views.check_payment_status, name='check_payment_status'),
    
    # === ORDERS (specific paths before router) ===
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/<int:order_id>/receipt/', views.order_receipt, name='order_receipt'),
    path('orders/<int:order_id>/pdf-preview/', order_pdf_preview, name='order_pdf_preview'),
    path('orders/<int:order_id>/pdf-download/', order_pdf_download, name='order_pdf_download'),
    
    
    path('reports/sales/pdf-preview/', sales_report_pdf_preview, name='sales_report_pdf_preview'),
    path('reports/inventory/pdf-preview/', inventory_report_pdf_preview, name='inventory_report_pdf_preview'),
    
   
    path('', include(router.urls)),
    
   
    path('users/', users_api, name='users_api'),
    path('users/<int:user_id>/', users_api, name='users_api_detail'),
    path('users/me/', views.user_me, name='user_me'),
    
    
    path('debug/health/', system_health_check, name='system_health_check'),
    path('debug/orders/duplicates/', check_duplicate_orders_api, name='check_duplicate_orders'),
    path('debug/addresses/duplicates/', check_duplicate_addresses_api, name='check_duplicate_addresses'),
    path('debug/orders/log/', get_order_creation_log_api, name='get_order_creation_log'),
    path('debug/current-setting/', debug_current_user_setting, name='debug_current_user_setting'),
    path('debug/password-reset/check/', check_password_reset_token_api, name='check_password_reset_token'),
    path('debug/password-reset/clear-expired/', clear_expired_tokens_api, name='clear_expired_tokens'),
    
   
    path('sql/views/revenue-by-category/', sql_revenue_by_category, name='sql_revenue_by_category'),
    path('sql/views/sales-by-brand/', sql_sales_by_brand, name='sql_sales_by_brand'),
    path('sql/views/order-statistics/', sql_order_statistics, name='sql_order_statistics'),
    path('sql/views/product-ratings/', sql_product_ratings, name='sql_product_ratings'),
    
  
    path('sql/procedures/sales-report/', sql_sales_report, name='sql_sales_report'),
    path('sql/procedures/process-return/', sql_process_product_return, name='sql_process_product_return'),
    path('sql/procedures/create-monthly-snapshot/', sql_create_monthly_snapshot, name='sql_create_monthly_snapshot'),
    

    path('sql/functions/dashboard-stats/', sql_dashboard_stats, name='sql_dashboard_stats'),
    
   
    path('sql/triggers/price-changes/', sql_trigger_price_changes, name='sql_trigger_price_changes'),
    path('sql/triggers/order-status-changes/', sql_trigger_order_status_changes, name='sql_trigger_order_status_changes'),
    path('sql/triggers/review-creations/', sql_trigger_review_creations, name='sql_trigger_review_creations'),
    path('sql/triggers/payment-records/', sql_trigger_payment_records, name='sql_trigger_payment_records'),
]
