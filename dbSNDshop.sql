-- ==========================
-- Основная таблица пользователей
-- ==========================
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    reset_token VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- Таблица ролей
-- ==========================
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

-- ==========================
-- Таблица назначения ролей (M:M)
-- ==========================
CREATE TABLE users (
    users_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    role_id INT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
);
-----------------------------------------------------------------------------------------------------------------------
-- 1. Роль admin
INSERT INTO roles (role_name) 
VALUES ('admin')
ON CONFLICT (role_name) DO NOTHING;

-- 2. Покупатель
INSERT INTO customers (
    first_name, last_name, email, password_hash, phone
) VALUES (
    'Иван', 'Иванов', 'ivan@example.com',
    'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
    '+79991234567'
);

-- 3. Администратор
INSERT INTO customers (
    first_name, last_name, email, password_hash, phone
) VALUES (
    'Админ', 'Системы', 'admin@snd.ru',
    'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
    '+79990000000'
);

-- 4. Назначение роли админа
WITH admin_user AS (
    SELECT customer_id FROM customers WHERE email = 'admin@snd.ru'
),
admin_role AS (
    SELECT role_id FROM roles WHERE role_name = 'admin'
)
INSERT INTO users (customer_id, role_id)
SELECT au.customer_id, ar.role_id
FROM admin_user au, admin_role ar
ON CONFLICT DO NOTHING;
------------------------------------------------------------------------------------------------------------------------
-- 1. Роль сотрудника
INSERT INTO roles (role_name) 
VALUES ('employee')
ON CONFLICT (role_name) DO NOTHING;

-- 2. Сотрудник
INSERT INTO customers (
    first_name, last_name, email, password_hash, phone
) VALUES (
    'Анна', 'Сотрудник', 'employee@snd.ru',
    'c7f7e8d8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
    '+79998887766'
);

-- 3. Назначение роли
WITH emp_user AS (
    SELECT customer_id FROM customers WHERE email = 'employee@snd.ru'
),
emp_role AS (
    SELECT role_id FROM roles WHERE role_name = 'employee'
)
INSERT INTO users (customer_id, role_id)
SELECT eu.customer_id, er.role_id
FROM emp_user eu, emp_role er
ON CONFLICT DO NOTHING;
----------------------------------------------------------------------------------------------------------------------




-- ==========================
-- Таблица адресов
-- ==========================
CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    country VARCHAR(50),
    region VARCHAR(50),
    city VARCHAR(50),
    street VARCHAR(100),
    house VARCHAR(20),
    apartment VARCHAR(20),
    type VARCHAR(10) CHECK (type IN ('shipping', 'billing')) NOT NULL,
    full_address TEXT,
    UNIQUE (customer_id, type),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_addresses_customer_id ON addresses(customer_id);

-- ==========================
-- Таблица категорий
-- ==========================
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,
    description TEXT,
    parent_id INT,
    FOREIGN KEY (parent_id) REFERENCES categories(category_id) ON DELETE SET NULL
);
ALTER TABLE categories
    ADD CONSTRAINT unique_category_name UNIQUE (category_name);
ALTER TABLE categories 
ADD COLUMN IF NOT EXISTS template VARCHAR(50);

-- 3. Вставляем/обновляем категории
INSERT INTO categories (category_name, template)
VALUES
    ('Ноутбуки',    'laptop'),
    ('Компьютеры',  'pc'),
    ('Мыши',        'mouse'),
    ('Клавиатуры',  'keyboard'),
    ('Мониторы',    'monitor')
ON CONFLICT (category_name) DO UPDATE
    SET template = EXCLUDED.template;

-- ==========================
-- Таблица брендов
-- ==========================
CREATE TABLE brands (
    brand_id SERIAL PRIMARY KEY,
    brand_name VARCHAR(50) UNIQUE NOT NULL,
    logo_url VARCHAR(255)
);

-- ==========================
-- Таблица поставщиков
-- ==========================
CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20)
);

-- ==========================
-- Таблица продуктов
-- ==========================
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) CHECK (price > 0) NOT NULL,
    stock_quantity INT CHECK (stock_quantity >= 0) DEFAULT 0,
    image_url VARCHAR(255),
    category_id INT,
    brand_id INT,
    supplier_id INT,
    status VARCHAR(20) CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    specifications JSONB,
    row_version BIGINT DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE products
    ADD COLUMN images JSONB DEFAULT '[]';

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_brand_id ON products(brand_id);
CREATE INDEX idx_products_specifications ON products USING GIN(specifications);

CREATE OR REPLACE FUNCTION update_product_row_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.row_version = OLD.row_version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_product_row_version
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_product_row_version();

-- ==========================
-- Таблица заказов
-- ==========================
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    total_amount NUMERIC(10,2) CHECK (total_amount >= 0),
    status VARCHAR(20) CHECK (status IN ('new', 'processing', 'shipped', 'delivered', 'cancelled', 'returned')) NOT NULL DEFAULT 'new',
    payment_method VARCHAR(20) CHECK (payment_method IN ('card', 'cash', 'sberpay')),
    payment_status VARCHAR(20) CHECK (payment_status IN ('pending', 'completed', 'failed')) DEFAULT 'pending',
    shipping_address_id INT,
    tracking_number VARCHAR(50),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (shipping_address_id) REFERENCES addresses(address_id) ON DELETE SET NULL
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);

-- ==========================
-- Таблица элементов заказа
-- ==========================
CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT CHECK (quantity > 0) NOT NULL,
    price_at_purchase NUMERIC(10,2) CHECK (price_at_purchase > 0) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- ==========================
-- Таблица платежей
-- ==========================
CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    amount NUMERIC(10,2) CHECK (amount > 0) NOT NULL,
    method VARCHAR(50) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- ==========================
-- Таблица доставок
-- ==========================
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    shipment_date TIMESTAMP,
    shipping_address_id INT,
    tracking VARCHAR(50),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (shipping_address_id) REFERENCES addresses(address_id) ON DELETE SET NULL
);

-- ==========================
-- Таблица отзывов
-- ==========================
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INT,
    customer_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5) NOT NULL,
    reviews_comment TEXT,
    publication_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status VARCHAR(20) CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_reviews_product_id ON reviews(product_id);

-- ==========================
-- Таблица корзин
-- ==========================
CREATE TABLE carts (
    cart_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Таблица элементов корзины
CREATE TABLE cart_items (
    item_id SERIAL PRIMARY KEY,
    cart_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT CHECK (quantity > 0) NOT NULL,
    FOREIGN KEY (cart_id) REFERENCES carts(cart_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);

-- Таблица списков желаемого
CREATE TABLE wishlists (
    wishlist_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    product_id INT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- ==========================
-- Таблица акций
-- ==========================
CREATE TABLE promotions (
    promotion_id SERIAL PRIMARY KEY,
    promotion_name VARCHAR(100) NOT NULL,
    discount NUMERIC(5,2) CHECK (discount BETWEEN 0 AND 100),
    start_date DATE,
    end_date DATE CHECK (end_date >= start_date),
    product_id INT,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL
);

-- ==========================
-- Таблица инвентаря
-- ==========================
CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    quantity INT CHECK (quantity >= 0) NOT NULL,
    warehouse_id INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE analytics_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    snapshot_type VARCHAR(50) NOT NULL,
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB
);


-- ==========================
-- Таблица возвратов
-- ==========================
CREATE TABLE product_returns (
    product_return_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    reason TEXT NOT NULL,
    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status VARCHAR(10) CHECK (status IN ('pending', 'approved', 'rejected', 'processed')) DEFAULT 'pending',
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES order_items(item_id) ON DELETE CASCADE
);



-- ==========================
-- AUDIT, REPORTS, ANALYTICS
-- ==========================
CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES customers(customer_id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INT,
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION update_inventory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_inventory_timestamp
BEFORE UPDATE ON inventory
FOR EACH ROW
EXECUTE FUNCTION update_inventory_timestamp();



CREATE OR REPLACE FUNCTION audit_order_update()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (user_id, action_type, table_name, record_id, old_value, new_value, timestamp)
    VALUES (COALESCE(
                (CASE WHEN current_setting('app.current_user_id', true) ~ '^[0-9]+$'
                      THEN current_setting('app.current_user_id', true)::INT ELSE NULL END),
                NEW.customer_id,
                (SELECT customer_id FROM orders WHERE order_id = NEW.order_id)
            ), 
            'ORDER_CHANGED', 
            'orders', 
            NEW.order_id,
            JSONB_BUILD_OBJECT(
                'old_status', OLD.status,
                'old_total', OLD.total_amount,
                'old_payment_status', OLD.payment_status
            )::TEXT,
            JSONB_BUILD_OBJECT(
                'new_status', NEW.status,
                'new_total', NEW.total_amount,
                'new_payment_status', NEW.payment_status,
                'customer_email', (SELECT email FROM customers WHERE customer_id = NEW.customer_id),
                'changed_at', TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Moscow', 'DD.MM.YYYY HH24:MI:SS')
            )::TEXT,
            CURRENT_TIMESTAMP);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_order_update
AFTER UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION audit_order_update();

-- Таблицы отчетов и аналитики
CREATE TABLE reports (
    report_id SERIAL PRIMARY KEY,
    report_name VARCHAR(100) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    created_by INT REFERENCES customers(customer_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) CHECK(status IN ('pending','ready','failed')) DEFAULT 'pending'
);

CREATE TABLE report_items (
    item_id SERIAL PRIMARY KEY,
    report_id INT REFERENCES reports(report_id) ON DELETE CASCADE,
    entity_type VARCHAR(50),
    entity_id INT,
    metric_name VARCHAR(50),
    metric_value NUMERIC(12,2),
    additional_info JSONB
);
ALTER TABLE report_items
ADD COLUMN product_id INT NULL;



CREATE INDEX idx_analytics_snapshots_data ON analytics_snapshots USING GIN(data);
CREATE INDEX idx_snapshot_date ON analytics_snapshots(snapshot_date);

CREATE TABLE backup_logs (
    backup_id SERIAL PRIMARY KEY,
    backup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    initiated_by INT REFERENCES customers(customer_id) ON DELETE SET NULL,
    backup_type VARCHAR(50) CHECK (backup_type IN ('full', 'incremental')),
    file_path VARCHAR(255),
    status VARCHAR(20) CHECK (status IN ('success', 'failed', 'in_progress')) DEFAULT 'success'
);

CREATE TABLE analytics_metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(15,2),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================================================
-- РАЗДЕЛ 1: SQL ПРЕДСТАВЛЕНИЯ (VIEWS) ДЛЯ ОТЧЕТНОСТИ
-- ========================================================================

-- VIEW 1: Сводный отчет о доходах по категориям
CREATE OR REPLACE VIEW vw_revenue_by_category AS
SELECT 
    c.category_id,
    c.category_name,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT p.product_id) AS products_sold,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.quantity * oi.price_at_purchase) AS total_revenue,
    AVG(oi.price_at_purchase) AS avg_price,
    MAX(o.order_date) AS last_order_date
FROM categories c
LEFT JOIN products p ON c.category_id = p.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status = 'delivered'
GROUP BY c.category_id, c.category_name
ORDER BY total_revenue DESC;

-- VIEW 2: Анализ продаж по брендам
CREATE OR REPLACE VIEW vw_sales_by_brand AS
SELECT 
    b.brand_id,
    b.brand_name,
    COUNT(DISTINCT p.product_id) AS total_products,
    COUNT(DISTINCT o.order_id) AS orders_count,
    SUM(oi.quantity) AS items_sold,
    SUM(oi.quantity * oi.price_at_purchase) AS total_sales,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    COUNT(DISTINCT r.review_id) AS review_count
FROM brands b
LEFT JOIN products p ON b.brand_id = p.brand_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status = 'delivered'
LEFT JOIN reviews r ON p.product_id = r.product_id AND r.status = 'approved'
GROUP BY b.brand_id, b.brand_name
ORDER BY total_sales DESC;

-- VIEW 3: Статистика заказов по статусам
CREATE OR REPLACE VIEW vw_order_statistics AS
SELECT 
    DATE(o.order_date) AS order_date,
    o.status,
    COUNT(*) AS count_orders,
    SUM(o.total_amount) AS total_amount,
    AVG(o.total_amount) AS avg_order_amount,
    MIN(o.total_amount) AS min_order_amount,
    MAX(o.total_amount) AS max_order_amount
FROM orders o
GROUP BY DATE(o.order_date), o.status
ORDER BY order_date DESC, status;

-- VIEW 4: Рейтинг товаров по отзывам
CREATE OR REPLACE VIEW vw_product_ratings AS
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    b.brand_name,
    COUNT(r.review_id) AS review_count,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) AS five_star_count,
    SUM(CASE WHEN r.rating = 4 THEN 1 ELSE 0 END) AS four_star_count,
    SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END) AS three_star_count,
    SUM(CASE WHEN r.rating = 2 THEN 1 ELSE 0 END) AS two_star_count,
    SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) AS one_star_count,
    MAX(r.publication_date) AS last_review_date
FROM products p
LEFT JOIN categories c ON p.category_id = c.category_id
LEFT JOIN brands b ON p.brand_id = b.brand_id
LEFT JOIN reviews r ON p.product_id = r.product_id AND r.status = 'approved'
GROUP BY p.product_id, p.product_name, c.category_name, b.brand_name
ORDER BY avg_rating DESC;



-- ========================================================================
-- РАЗДЕЛ 2: ТРИГГЕРЫ ДЛЯ АУДИТА (AUDIT TRIGGERS)
-- ========================================================================

-- ТРИГГЕР 1: Аудит изменений цен товаров
CREATE OR REPLACE FUNCTION fn_audit_product_price_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.price IS DISTINCT FROM NEW.price THEN
        INSERT INTO audit_log (
            user_id, 
            action_type, 
            table_name, 
            record_id, 
            old_value, 
            new_value, 
            timestamp
        ) VALUES (
            (CASE WHEN current_setting('app.current_user_id', true) ~ '^[0-9]+$' 
                  THEN current_setting('app.current_user_id', true)::INT ELSE NULL END),
            'PRICE_CHANGE',
            'products',
            NEW.product_id,
            JSONB_BUILD_OBJECT(
                'product_id', OLD.product_id,
                'product_name', OLD.product_name,
                'old_price', OLD.price,
                'change_amount', NEW.price - OLD.price
            )::TEXT,
            JSONB_BUILD_OBJECT(
                'product_id', NEW.product_id,
                'product_name', NEW.product_name,
                'new_price', NEW.price
            )::TEXT,
            CURRENT_TIMESTAMP
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_product_price_change
AFTER UPDATE OF price ON products
FOR EACH ROW
EXECUTE FUNCTION fn_audit_product_price_change();

-- ТРИГГЕР 3: Аудит создания отзывов
CREATE OR REPLACE FUNCTION fn_audit_review_creation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id, 
        action_type, 
        table_name, 
        record_id, 
        old_value, 
        new_value, 
        timestamp
    ) VALUES (
        NEW.customer_id,
        'REVIEW_CREATED',
        'reviews',
        NEW.review_id,
        NULL,
        JSONB_BUILD_OBJECT(
            'product_id', NEW.product_id,
            'rating', NEW.rating,
            'status', NEW.status,
            'comment_length', LENGTH(NEW.reviews_comment)
        )::TEXT,
        CURRENT_TIMESTAMP
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_review_creation
AFTER INSERT ON reviews
FOR EACH ROW
EXECUTE FUNCTION fn_audit_review_creation();

-- ТРИГГЕР 4: Аудит записи платежа
CREATE OR REPLACE FUNCTION fn_audit_payment_status_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id, 
        action_type, 
        table_name, 
        record_id, 
        old_value, 
        new_value, 
        timestamp
    ) VALUES (
        COALESCE(
            (CASE WHEN current_setting('app.current_user_id', true) ~ '^[0-9]+$'
                  THEN current_setting('app.current_user_id', true)::INT ELSE NULL END),
            (SELECT customer_id FROM orders WHERE order_id = NEW.order_id)
        ),
        'PAYMENT_RECORDED',
        'payments',
        NEW.payment_id,
        NULL,
        JSONB_BUILD_OBJECT(
            'payment_id', NEW.payment_id,
            'order_id', NEW.order_id,
            'amount', NEW.amount,
            'method', NEW.method
        )::TEXT,
        CURRENT_TIMESTAMP
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_payment_recorded
AFTER INSERT ON payments
FOR EACH ROW
EXECUTE FUNCTION fn_audit_payment_status_change();



-- ========================================================================
-- РАЗДЕЛ 3: ХРАНИМЫЕ ПРОЦЕДУРЫ (STORED PROCEDURES)
-- ========================================================================

-- ПРОЦЕДУРА 1: Получить детальный отчет о продажах за период
CREATE OR REPLACE FUNCTION sp_get_sales_report(
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    report_date DATE,
    category_name VARCHAR,
    brand_name VARCHAR,
    total_orders INT,
    items_sold INT,
    total_revenue NUMERIC,
    avg_order_value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(o.order_date) AS report_date,
        c.category_name,
        b.brand_name,
        COUNT(DISTINCT o.order_id)::INT AS total_orders,
        SUM(oi.quantity)::INT AS items_sold,
        ROUND(SUM(oi.quantity * oi.price_at_purchase), 2) AS total_revenue,
        ROUND(AVG(o.total_amount), 2) AS avg_order_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN categories c ON p.category_id = c.category_id
    JOIN brands b ON p.brand_id = b.brand_id
    WHERE o.order_date::DATE BETWEEN p_start_date AND p_end_date
      AND o.status IN ('delivered', 'shipped')
    GROUP BY DATE(o.order_date), c.category_name, b.brand_name
    ORDER BY report_date DESC, total_revenue DESC;
END;
$$ LANGUAGE plpgsql;

-- ПРОЦЕДУРА 2: Обработка возврата товара с обновлением инвентаря
CREATE OR REPLACE FUNCTION sp_process_product_return(
    p_product_return_id INT,
    p_approval_status VARCHAR
)
RETURNS TABLE (
    return_id INT,
    order_id INT,
    product_id INT,
    product_name VARCHAR,
    quantity_restored INT,
    message VARCHAR
) AS $$
DECLARE
    v_order_id INT;
    v_item_id INT;
    v_product_id INT;
    v_quantity INT;
    v_product_name VARCHAR;
BEGIN
    -- Получить информацию о возврате
    SELECT pr.order_id, pr.item_id, oi.product_id, oi.quantity, p.product_name
    INTO v_order_id, v_item_id, v_product_id, v_quantity, v_product_name
    FROM product_returns pr
    JOIN order_items oi ON pr.item_id = oi.item_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE pr.product_return_id = p_product_return_id;

    IF v_product_id IS NULL THEN
        RETURN QUERY SELECT 
            p_product_return_id, 
            NULL::INT, 
            NULL::INT, 
            NULL::VARCHAR,
            0,
            'Возврат не найден'::VARCHAR;
        RETURN;
    END IF;

    -- Обновить статус возврата
    UPDATE product_returns
    SET status = p_approval_status
    WHERE product_return_id = p_product_return_id;

    -- Если одобрено, восстановить товар на складе
    IF p_approval_status = 'approved' THEN
        UPDATE inventory
        SET quantity = quantity + v_quantity
        WHERE product_id = v_product_id;

        RETURN QUERY SELECT 
            p_product_return_id,
            v_order_id,
            v_product_id,
            v_product_name,
            v_quantity,
            CONCAT('Возврат одобрен. Восстановлено ', v_quantity, ' единиц товара.')::VARCHAR;
    ELSE
        RETURN QUERY SELECT 
            p_product_return_id,
            v_order_id,
            v_product_id,
            v_product_name,
            0,
            'Возврат отклонен.'::VARCHAR;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ПРОЦЕДУРА 3: Создание ежемесячного снимка аналитики
CREATE OR REPLACE FUNCTION sp_create_monthly_analytics_snapshot()
RETURNS TABLE (
    snapshot_id INT,
    snapshot_date TIMESTAMP,
    category_count INT,
    total_revenue NUMERIC,
    order_count INT,
    message VARCHAR
) AS $$
DECLARE
    v_snapshot_id INT;
    v_total_revenue NUMERIC;
    v_order_count INT;
    v_category_count INT;
    v_snapshot_data JSONB;
BEGIN
    -- Получить статистику за месяц
    SELECT 
        COUNT(DISTINCT c.category_id),
        SUM(oi.quantity * oi.price_at_purchase),
        COUNT(DISTINCT o.order_id)
    INTO v_category_count, v_total_revenue, v_order_count
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN categories c ON p.category_id = c.category_id
    WHERE DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', CURRENT_DATE)
      AND o.status IN ('delivered', 'shipped');

    -- Подготовить данные снимка
    SELECT JSONB_BUILD_OBJECT(
        'period', TO_CHAR(CURRENT_DATE, 'YYYY-MM'),
        'total_revenue', COALESCE(v_total_revenue, 0),
        'order_count', COALESCE(v_order_count, 0),
        'category_count', v_category_count,
        'timestamp', CURRENT_TIMESTAMP,
        'top_products', (
            SELECT JSONB_AGG(
                JSONB_BUILD_OBJECT(
                    'product_id', p.product_id,
                    'product_name', p.product_name,
                    'quantity_sold', SUM(oi.quantity)
                ) ORDER BY SUM(oi.quantity) DESC
            )
            FROM products p
            JOIN order_items oi ON p.product_id = oi.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY p.product_id, p.product_name
            LIMIT 5
        )
    ) INTO v_snapshot_data;

    -- Создать снимок
    INSERT INTO analytics_snapshots (snapshot_type, snapshot_date, data)
    VALUES ('monthly_summary', CURRENT_TIMESTAMP, v_snapshot_data)
    RETURNING analytics_snapshots.snapshot_id INTO v_snapshot_id;

    RETURN QUERY SELECT 
        v_snapshot_id,
        CURRENT_TIMESTAMP,
        v_category_count,
        COALESCE(v_total_revenue, 0),
        COALESCE(v_order_count, 0),
        'Ежемесячный снимок аналитики успешно создан'::VARCHAR;
END;
$$ LANGUAGE plpgsql;



-- ========================================================================
-- ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ
-- ========================================================================

-- Функция для быстрого получения статистики в JSON формате
CREATE OR REPLACE FUNCTION fn_get_dashboard_stats()
RETURNS JSONB AS $$
DECLARE
    v_stats JSONB;
BEGIN
    SELECT JSONB_BUILD_OBJECT(
        'total_revenue', (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status IN ('delivered', 'shipped')),
        'total_orders', (SELECT COUNT(*) FROM orders),
        'total_customers', (SELECT COUNT(*) FROM customers),
        'total_products', (SELECT COUNT(*) FROM products),
        'pending_returns', (SELECT COUNT(*) FROM product_returns WHERE status = 'pending'),
        'low_stock_items', (SELECT COUNT(*) FROM inventory WHERE quantity < 20),
        'pending_reviews', (SELECT COUNT(*) FROM reviews WHERE status = 'pending'),
        'today_sales', (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE DATE(order_date) = CURRENT_DATE),
        'today_orders', (SELECT COUNT(*) FROM orders WHERE DATE(order_date) = CURRENT_DATE),
        'average_order_value', (SELECT ROUND(AVG(total_amount), 2) FROM orders WHERE status IN ('delivered', 'shipped'))
    ) INTO v_stats;
    
    RETURN v_stats;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ
-- ========================================================================

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action_type ON audit_log(action_type);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(order_date DESC);
CREATE INDEX IF NOT EXISTS idx_products_category_status ON products(category_id, status);
CREATE INDEX IF NOT EXISTS idx_inventory_quantity ON inventory(quantity);
CREATE INDEX IF NOT EXISTS idx_reviews_product_status ON reviews(product_id, status);