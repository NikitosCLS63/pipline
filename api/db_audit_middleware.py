from django.db import connection
from apps.users.decorators import get_user_from_request
from apps.users.models import Customers

try:
    from django.contrib.auth import get_user_model
    DjangoUser = get_user_model()
except Exception:
    DjangoUser = None


class DBAuditMiddleware:
    """
    Middleware устанавливает переменную сессии PostgreSQL `app.current_user_id`
    чтобы триггеры в базе могли записать ID изменившего пользователя.

    Поведение:
    - Если в запросе есть JWT (middleware `JWTAuthMiddleware`), используется `request.jwt_customer_id`.
    - Иначе пытается извлечь пользователя через `get_user_from_request`.
    - В конце запроса значение сбрасывается в пустую строку.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Определяем текущего customer_id
        customer_id = None
        try:
            if hasattr(request, 'jwt_customer_id') and request.jwt_customer_id:
                customer_id = str(request.jwt_customer_id)
            else:
                # 1) Попробуем извлечь через get_user_from_request (JWT / cookies)
                try:
                    user, customer = get_user_from_request(request)
                    if customer and hasattr(customer, 'customer_id'):
                        customer_id = str(customer.customer_id)
                except Exception:
                    customer_id = None

                # 2) Если не нашли и есть Django session user, попробуем сопоставить по email
                if not customer_id and hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
                    try:
                        user_email = getattr(request.user, 'email', None)
                        if user_email:
                            cust = Customers.objects.filter(email=user_email).first()
                            if cust:
                                customer_id = str(cust.customer_id)
                    except Exception:
                        # не критично, продолжаем
                        pass

            # Установим параметр в сессии БД для текущего соединения
            with connection.cursor() as cur:
                # установим пустую строку если аноним
                val = customer_id if customer_id else ''
                cur.execute("SELECT set_config('app.current_user_id', %s, false);", [val])
        except Exception:
            # На любые ошибки - игнорируем, audit продолжит писать NULL
            pass

        response = self.get_response(request)

        # Сбросим переменную, чтобы уменьшить риск протекания между сессиями
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.current_user_id', %s, false);", [''])
        except Exception:
            pass

        return response
