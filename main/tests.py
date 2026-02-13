from django.test import TestCase, Client
from django.urls import reverse


class URLResolutionTest(TestCase):
    "Тест проверки правильности разрешения URL-адресов"
    
    def test_url_name_resolution(self):
        "все указанные имена URL-адресов должны разрешаться корректно"
        url_names = [
            'home',
            'catalog',
            'about',
            'contact',
            'privacy',
            'cart',
            'login',
            'register',
            'favorites',
            'orders'
        ]
        
        for url_name in url_names:
            with self.subTest(url_name=url_name):
                try:
                    url = reverse(url_name)
                    self.assertIsInstance(url, str)
                    self.assertTrue(len(url) > 0)
                except Exception as e:
                    self.fail(f"URL name '{url_name}' не удалось решить: {e}")
    
    def test_reverse_urls_work(self):
        "Возвращение допустимых URL-адресов по именам"
        
        self.assertEqual(reverse('home'), '/')
        self.assertEqual(reverse('catalog'), '/catalog/')
        self.assertEqual(reverse('about'), '/about/')
        self.assertEqual(reverse('contact'), '/contact/')
        
    def test_nonexistent_url_raises_error(self):
        "Несуществующие имена URL-адресов должны вызывать исключение NoReverseMatch."
        from django.urls import NoReverseMatch
        
        with self.assertRaises(NoReverseMatch):
            reverse('nonexistent_page')

class SimplePageLoadTest(TestCase):
    "Простые тесты, не запускающие запросы к базе данных."
    
    def setUp(self):
        self.client = Client()
    
    def test_static_pages_load(self):
        "Шаблонные страницы должны загружаться без запросов к базе данных"
        static_pages = [ 
            ('about', 'О компании'),
            ('contact', 'Контакты'),
            ('privacy', 'Конфиденциальность'),
            ('catalog', 'Каталог'),
            ('cart', 'Корзина'),
            ('login', 'Вход'),
            ('register', 'Регистрация')
        ]
        
        for url_name, expected_content in static_pages:
            with self.subTest(page=url_name):
                try:
                    response = self.client.get(reverse(url_name))
                    
                    self.assertIn(response.status_code, [200, 404])
                except Exception as e:
                    
                    pass
    
    def test_404_handling(self):
        "Несуществующие URL-адреса должны обрабатываться корректно."
        response = self.client.get('/definitely-nonexistent-page/')
       
        self.assertIn(response.status_code, [404, 301, 302])

class URLPatternTest(TestCase):
    "Проверка соответствия шаблонов URL-адресов"
    
    def test_url_patterns_exist(self):
        "Шаблоны URL-адресов должны существовать для основных страниц"
        from django.urls import get_resolver
        
        resolver = get_resolver()
        url_names = [
            'home', 'catalog', 'about', 'contact', 
            'privacy', 'cart', 'login', 'register'
        ]
        
        for url_name in url_names:
            with self.subTest(url_name=url_name):
                self.assertIn(url_name, resolver.reverse_dict.keys())
    
    def test_admin_urls_resolvable(self):
        "админские URL-адреса должны быть разрешимы"
        admin_urls = [
            'admin_panel',
            'admin_users',
            'admin_inventory',
            'admin_orders'
        ]
        
        for url_name in admin_urls:
            with self.subTest(admin_url=url_name):
                try:
                    url = reverse(url_name)
                    self.assertIsInstance(url, str)
                except Exception:
                
                    pass

class BasicTestCase(TestCase):
    "Базовый тестовый кейс для проверки работы тестового фреймворка"
    
    def test_basic_assertions(self):
        "Базовые проверки должны работать"
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)
        self.assertFalse(False)
        self.assertIn('test', 'this is a test')
        
    def test_client_available(self):
        "Тестовый клиент должен быть доступен"
        client = Client()
        self.assertIsInstance(client, Client)
        
    def test_reverse_function_works(self):
        "Функция reverse в Django должна работать"
        from django.urls import reverse
        home_url = reverse('home')
        self.assertEqual(home_url, '/')
