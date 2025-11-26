-- Создание базы данных (выполнить отдельно)
-- CREATE DATABASE electronics_store ENCODING 'UTF8' LC_COLLATE 'ru_RU.UTF-8' LC_CTYPE 'ru_RU.UTF-8' TEMPLATE template0;

-- Подключение к базе
-- \c electronics_store

-- Расширения для полнотекстового поиска
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Таблица пользователей системы
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'customer' CHECK (role IN ('customer', 'admin', 'manager')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Таблица профилей клиентов
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица категорий товаров
CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_category_id INTEGER REFERENCES categories(category_id) ON DELETE SET NULL,
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица товаров
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    cost_price DECIMAL(10,2) CHECK (cost_price >= 0),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    sku VARCHAR(100) UNIQUE NOT NULL,
    weight DECIMAL(8,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица атрибутов товаров
CREATE TABLE IF NOT EXISTS product_attributes (
    attribute_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    data_type VARCHAR(50) DEFAULT 'text'
);

-- Таблица значений атрибутов (связь M:M)
CREATE TABLE IF NOT EXISTS product_attribute_values (
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    attribute_id INTEGER NOT NULL REFERENCES product_attributes(attribute_id) ON DELETE CASCADE,
    value VARCHAR(500) NOT NULL,
    PRIMARY KEY (product_id, attribute_id)
);

-- Таблица складских остатков
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id INTEGER UNIQUE NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    low_stock_threshold INTEGER DEFAULT 5,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица адресов доставки
CREATE TABLE IF NOT EXISTS addresses (
    address_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    address_type VARCHAR(50) DEFAULT 'home' CHECK (address_type IN ('home', 'work', 'other')),
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) DEFAULT 'Russia',
    is_default BOOLEAN DEFAULT FALSE
);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    shipping_address_id INTEGER NOT NULL REFERENCES addresses(address_id),
    payment_method VARCHAR(50) CHECK (payment_method IN ('card', 'cash', 'online')),
    payment_status VARCHAR(50) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')),
    shipping_cost DECIMAL(8,2) DEFAULT 0,
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица позиций заказа
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    subtotal DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Таблица отзывов
CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_approved BOOLEAN DEFAULT FALSE,
    UNIQUE(product_id, customer_id)
);

-- Таблица для логов статусов заказов
CREATE TABLE IF NOT EXISTS order_status_log (
    log_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    changed_by VARCHAR(100) DEFAULT 'system',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Таблица изображений товаров
CREATE TABLE IF NOT EXISTS product_images (
    image_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- ОПТИМИЗИРОВАННЫЕ ИНДЕКСЫ

-- 1. ПОЛЬЗОВАТЕЛИ (2 индекса)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_customers_user_id ON customers(user_id);

-- 2. ТОВАРЫ (4 индекса)
CREATE INDEX IF NOT EXISTS idx_products_category_active ON products(category_id, is_active);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_name_search ON products USING gin(to_tsvector('russian', name));

-- 3. СКЛАД (2 индекса)
CREATE INDEX IF NOT EXISTS idx_inventory_product_id ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_low_stock ON inventory(quantity) WHERE quantity < low_stock_threshold;

-- 4. ЗАКАЗЫ (3 индекса)
CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON orders(customer_id, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status);

-- 5. ПОЗИЦИИ ЗАКАЗА (2 индекса)
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- 6. ОТЗЫВЫ (1 индекс)
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);

-- Индексы для изображений товаров
CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_product_images_primary ON product_images(product_id, is_primary);

-- ФУНКЦИИ И ТРИГГЕРЫ

-- Функция для обновления поля updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Функция для создания записи в inventory
CREATE OR REPLACE FUNCTION create_inventory_record()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO inventory (product_id, quantity) 
    VALUES (NEW.product_id, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Функция для логирования изменений статуса заказа
CREATE OR REPLACE FUNCTION log_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO order_status_log (order_id, old_status, new_status)
        VALUES (NEW.order_id, OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для автообновления updated_at
CREATE TRIGGER update_products_updated_at 
    BEFORE UPDATE ON products 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Триггер для создания записи в inventory при добавлении товара
CREATE TRIGGER create_inventory_after_product
    AFTER INSERT ON products
    FOR EACH ROW EXECUTE FUNCTION create_inventory_record();

-- Триггер для логирования изменений статуса заказа
CREATE TRIGGER log_order_status_changes
    AFTER UPDATE OF status ON orders
    FOR EACH ROW EXECUTE FUNCTION log_order_status_change();

-- ПОЛЕЗНЫЕ ПРЕДСТАВЛЕНИЯ

-- Представление для товаров с информацией о категории и остатках
CREATE OR REPLACE VIEW v_products_with_inventory AS
SELECT 
    p.product_id,
    p.name,
    p.description,
    p.price,
    p.cost_price,
    p.sku,
    c.name as category_name,
    c.category_id,
    i.quantity,
    i.reserved_quantity,
    (i.quantity - i.reserved_quantity) as available_quantity,
    p.is_active,
    p.created_at
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN inventory i ON p.product_id = i.product_id;

-- Представление для заказов с детальной информацией
CREATE OR REPLACE VIEW v_order_details AS
SELECT 
    o.order_id,
    o.order_date,
    o.status,
    o.total_amount,
    o.payment_method,
    o.payment_status,
    c.customer_id,
    c.first_name || ' ' || c.last_name as customer_name,
    a.street || ', ' || a.city || ', ' || a.postal_code as shipping_address,
    COUNT(oi.order_item_id) as items_count,
    SUM(oi.quantity) as total_quantity
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN addresses a ON o.shipping_address_id = a.address_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, c.customer_id, a.address_id;

-- ДАННЫЕ ДЛЯ ТЕСТИРОВАНИЯ

-- Вставка тестовых пользователей
INSERT INTO users (email, password_hash, role, created_at, last_login, is_active) VALUES
('admin@electroshop.ru', 'hashed_password_123', 'admin', '2023-01-15 10:00:00', '2024-01-20 14:30:00', true),
('manager@electroshop.ru', 'hashed_password_123', 'manager', '2023-01-16 09:15:00', '2024-01-19 16:45:00', true),
('ivanov@mail.ru', 'hashed_password_123', 'customer', '2023-02-10 11:20:00', '2024-01-18 12:15:00', true),
('petrov@gmail.com', 'hashed_password_123', 'customer', '2023-02-15 14:30:00', '2024-01-17 09:45:00', true),
('sidorova@yandex.ru', 'hashed_password_123', 'customer', '2023-03-05 16:45:00', '2024-01-16 18:20:00', true);

-- Вставка профилей клиентов
INSERT INTO customers (user_id, first_name, last_name, phone, date_of_birth, registration_date)
SELECT 
    user_id,
    (ARRAY['Александр', 'Мария', 'Сергей', 'Елена', 'Дмитрий'])[user_id],
    (ARRAY['Иванов', 'Петрова', 'Сидоров', 'Кузнецова', 'Попов'])[user_id],
    '+7-9' || lpad((user_id * 123456789)::text, 9, '0'),
    DATE '1980-01-01' + (user_id * 1000 || ' days')::interval,
    created_at
FROM users;

-- Вставка категорий
INSERT INTO categories (name, description, parent_category_id, image_url) VALUES
('Электроника', 'Все виды электронных устройств', NULL, '/images/electronics.jpg'),
('Бытовая техника', 'Техника для дома и кухни', NULL, '/images/appliances.jpg'),
('Смартфоны', 'Мобильные телефоны и коммуникаторы', 1, '/images/smartphones.jpg'),
('Ноутбуки', 'Портативные компьютеры', 1, '/images/laptops.jpg'),
('Телевизоры', 'Телевизоры и домашние кинотеатры', 1, '/images/tv.jpg'),
('Наушники', 'Наушники и аудиотехника', 1, '/images/headphones.jpg'),
('Холодильники', 'Холодильное оборудование', 2, '/images/refrigerators.jpg'),
('Стиральные машины', 'Стиральная техника', 2, '/images/washing-machines.jpg');

-- Вставка товаров
INSERT INTO products (name, description, price, cost_price, category_id, sku, weight, is_active) VALUES
('iPhone 15 Pro', 'Флагманский смартфон Apple с процессором A17 Pro', 99990.00, 75000.00, 3, 'APL-IP15P-256', 187.00, true),
('Samsung Galaxy S24', 'Смартфон Samsung с AI-функциями', 89990.00, 68000.00, 3, 'SAM-GS24-256', 167.00, true),
('MacBook Air M2', 'Ультрабук Apple с чипом M2', 129990.00, 95000.00, 4, 'APL-MBA-M2-13', 1240.00, true),
('Sony WH-1000XM5', 'Беспроводные наушники с шумоподавлением', 29990.00, 22000.00, 6, 'SON-WH-XM5', 250.00, true),
('Xiaomi Robot Vacuum', 'Робот-пылесос с навигацией LIDAR', 34990.00, 26000.00, 2, 'XIA-ROBO-S10', 3500.00, true),
('Samsung QLED 55"', 'Телевизор 4K с квантовыми точками', 89990.00, 65000.00, 5, 'SAM-QLED-55', 18500.00, true),
('LG Refrigerator', 'Холодильник с системой No Frost', 65990.00, 48000.00, 7, 'LG-FRIDGE-400', 85000.00, true);

-- Вставка адресов
INSERT INTO addresses (customer_id, address_type, street, city, state, postal_code, country, is_default) VALUES
(1, 'home', 'ул. Ленина, д. 10', 'Москва', NULL, '101000', 'Russia', true),
(2, 'home', 'пр. Мира, д. 25', 'Санкт-Петербург', NULL, '190000', 'Russia', true),
(3, 'home', 'ул. Пушкина, д. 30', 'Новосибирск', NULL, '630000', 'Russia', true);

-- Вставка заказов
INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_address_id, payment_method, payment_status, shipping_cost) VALUES
(1, '2024-01-10 14:30:00', 'delivered', 129990.00, 1, 'card', 'paid', 500.00),
(2, '2024-01-15 10:15:00', 'processing', 89990.00, 2, 'online', 'paid', 300.00),
(3, '2024-01-20 16:45:00', 'pending', 29990.00, 3, 'cash', 'pending', 200.00);

-- Вставка позиций заказов
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 3, 1, 129990.00), -- MacBook Air
(2, 2, 1, 89990.00),  -- Samsung Galaxy
(3, 4, 1, 29990.00);  -- Sony Headphones

-- Вставка отзывов
INSERT INTO reviews (product_id, customer_id, rating, comment, created_at, is_approved) VALUES
(3, 1, 5, 'Отличный ноутбук! Работает быстро, батарея держит долго.', '2024-01-12 09:00:00', true),
(2, 2, 4, 'Хороший смартфон, но цена завышена.', '2024-01-18 14:20:00', true);

-- ПРОВЕРОЧНЫЕ ЗАПРОСЫ

-- Проверка пользователей
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'categories', COUNT(*) FROM categories
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'addresses', COUNT(*) FROM addresses
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'order_status_log', COUNT(*) FROM order_status_log;

-- Проверка представлений
SELECT * FROM v_products_with_inventory LIMIT 5;
SELECT * FROM v_order_details LIMIT 5;