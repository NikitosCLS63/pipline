from faker import Faker
from locust import task, TaskSet, SequentialTaskSet, HttpUser, constant_throughput
import random

fake = Faker("ru_RU")


class CustomersRegTest(SequentialTaskSet):  # последовательная регистрация
    def on_start(self):
        self.client.get("/register")

    @task(1)
    def register_user(self):
        gen_password = fake.password(length=11)
        phone_number = f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}"

        register_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"{fake.user_name()}{random.randint(1000,9999)}@gmail.com",
            "password": gen_password,
            "confirm_password": gen_password,
            "phone": phone_number,
            "role": "client"
        }

        self.client.post("/api/register/", json=register_data)
        
    @task(12)
    def view_home(self):
        self.client.get("/")


class ProductViewTest(TaskSet):

    @task(8)
    def view_catalog(self):
        self.client.get("/catalog/")

    @task(6)
    def view_homepage(self):
        self.client.get("/")

    @task(5)
    def view_about(self):
        self.client.get("/about/")


class CustomerReviewsTest(TaskSet):
    def on_start(self):
        response = self.client.post("/api/login/", json={
            "email": "sirex.xumuk@gmail.com",
            "password": "nikita123!"
        })

        if response.status_code == 200:
            try:
                token = response.json().get("access")
                if token:
                    self.client.headers.update({
                        "Authorization": f"Bearer {token}"
                    })
            except:
                pass

    @task(5)
    def view_catalog(self):
        self.client.get("/catalog/")

    @task(1)
    def create_review(self):

        review_data = {
            "product_id": random.choice([3, 4, 7]),
            "rating": random.randint(1, 5),
            "reviews_comment": fake.text(max_nb_chars=150)
        }

        self.client.post("/api/reviews/", json=review_data)

    @task(5)
    def view_about(self):
        self.client.get("/about/")


class WebsiteUser(HttpUser):
    wait_time = constant_throughput(2)

    tasks = {
        ProductViewTest: 5,
        CustomerReviewsTest: 3,
        CustomersRegTest: 2
    }
