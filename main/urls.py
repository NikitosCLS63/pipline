# C:\WebsiteDjSND\main\urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import home, catalog, promotions, register, login, admin_panel, admin_users, admin_user_edit, admin_backup_db, admin_inventory, admin_orders_manage, admin_analytics, admin_export_orders_csv, admin_import_reports, admin_export_products_csv, admin_sales_report, admin_export_sales_report_csv, admin_export_sales_report_excel, admin_export_sales_report_pdf, admin_moderate_reviews, admin_audit_log, favorites, orders
from apps.reviews import views as reviews_views
from django.views.generic import TemplateView

urlpatterns = [
    path('', include('apps.products.urls')),
    
    # Админ-панель с защитой
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('admin-panel/users/', admin_users, name='admin_users'),
    path('admin-panel/users/edit/<int:user_id>/', admin_user_edit, name='admin_user_edit'),
    path('admin-panel/backup/', admin_backup_db, name='admin_backup'),
    path('admin-panel/inventory/', admin_inventory, name='admin_inventory'),
    path('admin-panel/orders/', admin_orders_manage, name='admin_orders'),
    path('admin-panel/analytics/', admin_analytics, name='admin_analytics'),
    path('admin-panel/export-orders/', admin_export_orders_csv, name='admin_export_orders'),
    path('admin-panel/import-reports/', admin_import_reports, name='admin_import_reports'),
    path('admin-panel/export-products/', admin_export_products_csv, name='admin_export_products'),
    path('admin-panel/sales-report/', admin_sales_report, name='admin_sales_report'),
    path('admin-panel/export-sales-report/', admin_export_sales_report_csv, name='admin_export_sales_report'),
    path('admin-panel/export-sales-report-excel/', admin_export_sales_report_excel, name='admin_export_sales_report_excel'),
    path('admin-panel/export-sales-report-pdf/', admin_export_sales_report_pdf, name='admin_export_sales_report_pdf'),
    path('admin-panel/reviews/', admin_moderate_reviews, name='admin_moderate_reviews'),
    path('admin-panel/audit/', admin_audit_log, name='admin_audit'),

    path('', home, name='home'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('compony/', TemplateView.as_view(template_name='compony.html'), name='compony'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('for-customers/', TemplateView.as_view(template_name='for_customers.html'), name='for_customers'),
    path('how-to-order/', TemplateView.as_view(template_name='how_to_order.html'), name='how_to_order'),
    path('payment-methods/', TemplateView.as_view(template_name='payment_methods.html'), name='payment_methods'),
    path('delivery/', TemplateView.as_view(template_name='delivery.html'), name='delivery'),
    path('order-status/', TemplateView.as_view(template_name='order_status.html'), name='order_status'),
    path('exchange-return/', TemplateView.as_view(template_name='exchange_return.html'), name='exchange_return'),
    path('help/', TemplateView.as_view(template_name='help.html'), name='help'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    
    path('register/', TemplateView.as_view(template_name='register.html'), name='register'),
    path('catalog/', TemplateView.as_view(template_name='catalog.html'), name='catalog'),
    path('promotions/', TemplateView.as_view(template_name='promotions.html'), name='promotions'),
    path('favorites/', favorites, name='favorites'),
    path('cart/', TemplateView.as_view(template_name='cart.html'), name='cart'),
    path('orders/', orders, name='orders'),
    path('reviews/', reviews_views.reviews_page, name='reviews'),
    path('reviews/submit/', reviews_views.submit_review, name='reviews_submit'),
    path('reviews/edit/<int:review_id>/', reviews_views.edit_review, name='reviews_edit'),
    path('reviews/delete/<int:review_id>/', reviews_views.delete_review, name='reviews_delete'),
    path('decoration/', TemplateView.as_view(template_name='decoration.html'), name='decoration'),
    path('decoration-success/', TemplateView.as_view(template_name='decoration-success.html'), name='decoration_success'),
    path('password_reset/', TemplateView.as_view(template_name='auth/password_reset.html')),
    path('reset-password-confirm/', TemplateView.as_view(template_name='auth/reset_password_confirm.html')),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)