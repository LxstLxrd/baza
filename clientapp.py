import sys
import psycopg2
from psycopg2 import sql
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QMessageBox, QComboBox, QSpinBox, QTextEdit,
                             QFormLayout, QGroupBox, QHeaderView, QDialog,
                             QDialogButtonBox, QDateEdit, QCheckBox, QGridLayout,
                             QScrollArea, QFrame, QListWidget, QListWidgetItem,
                             QSplitter, QToolBar, QAction, QStatusBar, QInputDialog)
from PyQt5.QtCore import Qt, QDate, QSize, QEvent
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPainter
from PyQt5.QtChart import (QChart, QChartView, QLineSeries, QBarSeries,
                           QBarSet, QValueAxis, QBarCategoryAxis, QPieSeries,
                           QPieSlice)
import hashlib
from datetime import datetime, timedelta
import random
from urllib.request import urlopen
from io import BytesIO
import urllib.request
from urllib.parse import urlparse


class ImageLoadedEvent(QEvent):
    """Событие загрузки изображения"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, pixmap):
        super().__init__(self.EVENT_TYPE)
        self.pixmap = pixmap


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.current_user = None

    def connect(self, host="localhost", database="electronics_store",
                user="postgres", password="ilya04062004", port="5432"):
        try:
            self.connection = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def authenticate(self, email, password):
        try:
            cursor = self.connection.cursor()

            # Для демонстрации используем простую проверку
            password_hash_md5 = hashlib.md5(password.encode()).hexdigest()

            query = """
            SELECT u.user_id, u.role, u.email, c.customer_id, c.first_name, c.last_name
            FROM users u 
            LEFT JOIN customers c ON u.user_id = c.user_id 
            WHERE u.email = %s AND u.is_active = TRUE
            AND (u.password_hash = %s OR u.password_hash = %s)
            """

            cursor.execute(query, (email, password_hash_md5, password))
            result = cursor.fetchone()
            cursor.close()

            if result:
                self.current_user = {
                    'user_id': result[0],
                    'role': result[1],
                    'email': result[2],
                    'customer_id': result[3],
                    'first_name': result[4],
                    'last_name': result[5]
                }
                return True
            return False
        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def get_products(self, category_id=None, search_text=None):
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT p.product_id, p.name, p.description, p.price, c.name as category_name,
                   i.quantity - i.reserved_quantity as available_quantity,
                   pi.image_url as image_url
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            JOIN inventory i ON p.product_id = i.product_id
            LEFT JOIN product_images pi ON p.product_id = pi.product_id AND pi.is_primary = TRUE
            WHERE p.is_active = TRUE
            """
            params = []

            if category_id:
                query += " AND p.category_id = %s"
                params.append(category_id)

            if search_text:
                query += " AND (p.name ILIKE %s OR p.description ILIKE %s)"
                params.extend([f'%{search_text}%', f'%{search_text}%'])

            query += " ORDER BY p.created_at DESC"

            cursor.execute(query, params)
            products = cursor.fetchall()
            cursor.close()
            return products
        except Exception as e:
            print(f"Error getting products: {e}")
            return []

    def get_categories(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT category_id, name FROM categories WHERE parent_category_id IS NULL")
            categories = cursor.fetchall()
            cursor.close()
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

    def get_all_products(self):
        """Получить все товары для админки"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT p.product_id, p.name, p.description, p.price, p.cost_price, 
                   c.name as category_name, p.sku, p.is_active,
                   i.quantity - i.reserved_quantity as available_quantity,
                   pi.image_url as image_url
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN inventory i ON p.product_id = i.product_id
            LEFT JOIN product_images pi ON p.product_id = pi.product_id AND pi.is_primary = TRUE
            ORDER BY p.created_at DESC
            """
            cursor.execute(query)
            products = cursor.fetchall()
            cursor.close()
            return products
        except Exception as e:
            print(f"Error getting all products: {e}")
            return []

    def get_all_users(self):
        """Получить всех пользователей для админки"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT u.user_id, u.email, u.role, u.created_at, u.last_login, u.is_active,
                   c.first_name, c.last_name, c.phone
            FROM users u
            LEFT JOIN customers c ON u.user_id = c.user_id
            ORDER BY u.created_at DESC
            """
            cursor.execute(query)
            users = cursor.fetchall()
            cursor.close()
            return users
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    def get_all_categories_with_parents(self):
        """Получить все категории с информацией о родительских категориях"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT c1.category_id, c1.name, c1.description, 
                   c2.name as parent_category, c1.created_at, c1.parent_category_id
            FROM categories c1
            LEFT JOIN categories c2 ON c1.parent_category_id = c2.category_id
            ORDER BY c1.created_at DESC
            """
            cursor.execute(query)
            categories = cursor.fetchall()
            cursor.close()
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

    def get_all_parent_categories(self):
        """Получить все родительские категории"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT category_id, name FROM categories WHERE parent_category_id IS NULL")
            categories = cursor.fetchall()
            cursor.close()
            return categories
        except Exception as e:
            print(f"Error getting parent categories: {e}")
            return []

    def create_order(self, customer_id, items, shipping_address_id, payment_method='card'):
        try:
            cursor = self.connection.cursor()

            # Calculate total amount
            total_amount = sum(item['price'] * item['quantity'] for item in items)

            # Create order
            order_query = """
            INSERT INTO orders (customer_id, total_amount, shipping_address_id, payment_method)
            VALUES (%s, %s, %s, %s) RETURNING order_id
            """
            cursor.execute(order_query, (customer_id, total_amount, shipping_address_id, payment_method))
            order_id = cursor.fetchone()[0]

            # Add order items
            for item in items:
                item_query = """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(item_query, (order_id, item['product_id'], item['quantity'], item['price']))

                # Update inventory
                update_inventory = """
                UPDATE inventory SET reserved_quantity = reserved_quantity + %s
                WHERE product_id = %s
                """
                cursor.execute(update_inventory, (item['quantity'], item['product_id']))

            self.connection.commit()
            cursor.close()
            return order_id
        except Exception as e:
            self.connection.rollback()
            print(f"Error creating order: {e}")
            return None

    def get_user_orders(self, customer_id):
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT o.order_id, o.order_date, o.status, o.total_amount, 
                   COUNT(oi.order_item_id) as items_count
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.customer_id = %s
            GROUP BY o.order_id
            ORDER BY o.order_date DESC
            """
            cursor.execute(query, (customer_id,))
            orders = cursor.fetchall()
            cursor.close()
            return orders
        except Exception as e:
            print(f"Error getting user orders: {e}")
            return []

    def get_all_orders(self):
        """Получить все заказы для администратора/менеджера"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT o.order_id, o.order_date, o.status, o.total_amount, 
                   COUNT(oi.order_item_id) as items_count,
                   c.first_name || ' ' || c.last_name as customer_name
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY o.order_id, c.customer_id
            ORDER BY o.order_date DESC
            """
            cursor.execute(query)
            orders = cursor.fetchall()
            cursor.close()
            return orders
        except Exception as e:
            print(f"Error getting all orders: {e}")
            return []

    def get_sales_report(self):
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT 
                DATE(o.order_date) as order_day,
                COUNT(o.order_id) as order_count,
                SUM(o.total_amount) as total_sales,
                AVG(o.total_amount) as avg_order_value
            FROM orders o
            WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(o.order_date)
            ORDER BY order_day
            """
            cursor.execute(query)
            report = cursor.fetchall()
            cursor.close()
            return report
        except Exception as e:
            print(f"Error getting sales report: {e}")
            return []

    def get_category_sales(self):
        """Получить продажи по категориям"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT 
                c.name as category,
                SUM(oi.quantity) as total_sold,
                SUM(oi.quantity * oi.unit_price) as revenue
            FROM categories c
            JOIN products p ON c.category_id = p.category_id
            JOIN order_items oi ON p.product_id = oi.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status != 'cancelled'
            GROUP BY c.category_id, c.name
            ORDER BY revenue DESC
            """
            cursor.execute(query)
            report = cursor.fetchall()
            cursor.close()
            return report
        except Exception as e:
            print(f"Error getting category sales: {e}")
            return []

    def update_product(self, product_id, name, description, price, cost_price, category_id, sku, is_active):
        """Обновить товар"""
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE products 
            SET name = %s, description = %s, price = %s, cost_price = %s, 
                category_id = %s, sku = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = %s
            """
            cursor.execute(query, (name, description, price, cost_price, category_id, sku, is_active, product_id))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"Error updating product: {e}")
            return False

    def add_product(self, name, description, price, cost_price, category_id, sku, image_url=None):
        """Добавить новый товар"""
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO products (name, description, price, cost_price, category_id, sku)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING product_id
            """
            cursor.execute(query, (name, description, price, cost_price, category_id, sku))
            product_id = cursor.fetchone()[0]

            # Добавляем изображение если указано
            if image_url:
                image_query = """
                INSERT INTO product_images (product_id, image_url, is_primary)
                VALUES (%s, %s, TRUE)
                """
                cursor.execute(image_query, (product_id, image_url))

            self.connection.commit()
            cursor.close()
            return product_id
        except Exception as e:
            self.connection.rollback()
            print(f"Error adding product: {e}")
            return None

    def update_product_images(self, product_id, image_url):
        """Обновить изображение товара"""
        try:
            cursor = self.connection.cursor()

            # Проверяем есть ли уже основное изображение
            cursor.execute("""
                SELECT image_id FROM product_images 
                WHERE product_id = %s AND is_primary = TRUE
            """, (product_id,))
            existing_image = cursor.fetchone()

            if existing_image:
                # Обновляем существующее изображение
                cursor.execute("""
                    UPDATE product_images 
                    SET image_url = %s 
                    WHERE image_id = %s
                """, (image_url, existing_image[0]))
            else:
                # Добавляем новое изображение
                cursor.execute("""
                    INSERT INTO product_images (product_id, image_url, is_primary)
                    VALUES (%s, %s, TRUE)
                """, (product_id, image_url))

            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"Error updating product images: {e}")
            return False

    def delete_product(self, product_id):
        """Удалить товар"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"Error deleting product: {e}")
            return False

    def add_category(self, name, description, parent_category_id=None, image_url=None):
        """Добавить новую категорию"""
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO categories (name, description, parent_category_id, image_url)
            VALUES (%s, %s, %s, %s) RETURNING category_id
            """
            cursor.execute(query, (name, description, parent_category_id, image_url))
            category_id = cursor.fetchone()[0]
            self.connection.commit()
            cursor.close()
            return category_id
        except Exception as e:
            self.connection.rollback()
            print(f"Error adding category: {e}")
            return None

    def update_category(self, category_id, name, description, parent_category_id=None, image_url=None):
        """Обновить категорию"""
        try:
            cursor = self.connection.cursor()
            query = """
            UPDATE categories 
            SET name = %s, description = %s, parent_category_id = %s, image_url = %s
            WHERE category_id = %s
            """
            cursor.execute(query, (name, description, parent_category_id, image_url, category_id))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"Error updating category: {e}")
            return False

    def delete_category(self, category_id):
        """Удалить категорию"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"Error deleting category: {e}")
            return False

    def get_dashboard_stats(self):
        """Получить статистику для дашборда"""
        try:
            cursor = self.connection.cursor()

            # Общее количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            # Общее количество товаров
            cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = TRUE")
            total_products = cursor.fetchone()[0]

            # Общее количество заказов
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]

            # Общая выручка
            cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status != 'cancelled'")
            total_revenue = cursor.fetchone()[0]

            # Продажи за последние 30 дней
            cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM orders 
            WHERE order_date >= CURRENT_DATE - INTERVAL '30 days' AND status != 'cancelled'
            """)
            monthly_revenue = cursor.fetchone()[0]

            cursor.close()

            return {
                'total_users': total_users,
                'total_products': total_products,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'monthly_revenue': float(monthly_revenue)
            }
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return None


class ProductCard(QFrame):
    def __init__(self, product, add_to_cart_callback):
        super().__init__()
        self.product = product
        self.add_to_cart_callback = add_to_cart_callback
        self.image_loaded = False
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setFixedSize(250, 400)
        self.setStyleSheet("""
            ProductCard {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
            }
            ProductCard:hover {
                border-color: #007bff;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
        """)

        layout = QVBoxLayout()

        # Product image
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 150)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            border: 1px solid #eee;
            background-color: #f8f9fa;
        """)

        # Загружаем изображение асинхронно
        self.load_product_image()

        layout.addWidget(self.image_label)

        # Product name
        name_label = QLabel(self.product[1])
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 5px;")
        layout.addWidget(name_label)

        # Product description (shortened)
        description = self.product[2] or "Описание отсутствует"
        if len(description) > 100:
            description = description[:100] + "..."
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc_label)

        # Price and availability
        price_layout = QHBoxLayout()
        price_label = QLabel(f"{self.product[3]:.2f} руб.")
        price_label.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 16px;")
        price_layout.addWidget(price_label)

        available = self.product[5]
        available_label = QLabel(f"В наличии: {available}")
        available_color = "#27ae60" if available > 0 else "#e74c3c"
        available_label.setStyleSheet(f"color: {available_color}; font-size: 12px;")
        price_layout.addWidget(available_label)
        layout.addLayout(price_layout)

        # Add to cart button
        add_button = QPushButton("В корзину")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        add_button.clicked.connect(self.add_to_cart)
        if available <= 0:
            add_button.setEnabled(False)
            add_button.setText("Нет в наличии")

        layout.addWidget(add_button)
        self.setLayout(layout)

    def load_product_image(self):
        """Загружает изображение товара из URL"""
        image_url = self.product[6]  # image_url из результата запроса

        if not image_url:
            self.set_placeholder_image("🖼️ Нет изображения")
            return

        # Загружаем изображение в отдельном потоке чтобы не блокировать UI
        import threading
        thread = threading.Thread(target=self.download_image, args=(image_url,))
        thread.daemon = True
        thread.start()

    def download_image(self, image_url):
        """Загружает изображение по URL"""
        try:
            # Проверяем валидность URL
            parsed_url = urlparse(image_url)
            if not parsed_url.scheme in ('http', 'https'):
                self.set_placeholder_image("❌ Неверный URL")
                return

            with urllib.request.urlopen(image_url, timeout=10) as response:
                image_data = response.read()

            # Создаем QPixmap из загруженных данных
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if not pixmap.isNull():
                # Масштабируем изображение
                pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # Обновляем UI в главном потоке
                QApplication.instance().postEvent(self, ImageLoadedEvent(pixmap))
            else:
                self.set_placeholder_image("❌ Ошибка загрузки")

        except Exception as e:
            print(f"Error loading image from {image_url}: {e}")
            self.set_placeholder_image("❌ Ошибка загрузки")

    def set_placeholder_image(self, text):
        """Устанавливает placeholder вместо изображения"""
        self.image_label.setText(text)
        self.image_label.setStyleSheet("""
            border: 1px solid #eee;
            background-color: #f8f9fa;
            color: #666;
            font-size: 12px;
        """)

    def set_product_image(self, pixmap):
        """Устанавливает загруженное изображение"""
        self.image_label.setPixmap(pixmap)
        self.image_loaded = True

    def add_to_cart(self):
        self.add_to_cart_callback(self.product)

    def customEvent(self, event):
        """Обрабатывает пользовательские события"""
        if isinstance(event, ImageLoadedEvent):
            self.set_product_image(event.pixmap)


class CategoryChartWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_chart()

    def init_ui(self):
        layout = QVBoxLayout()

        # Chart title
        title = QLabel("Продажи по категориям")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Create chart view
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.chart_view)

        self.setLayout(layout)

    def load_chart(self):
        category_data = self.db_manager.get_category_sales()

        # Create chart
        chart = QChart()
        chart.setTitle("Продажи по категориям")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        if category_data:
            categories = [row[0] for row in category_data]
            revenues = [float(row[2]) for row in category_data]

            # Create bar series
            series = QBarSeries()
            bar_set = QBarSet("Выручка")
            for revenue in revenues:
                bar_set.append(revenue)

            series.append(bar_set)
            chart.addSeries(series)

            # Set categories for x-axis
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)

            # Create axes
            axis_y = QValueAxis()
            axis_y.setTitleText("Выручка (руб.)")
            axis_y.setLabelFormat("%.0f")

            chart.addAxis(axis_x, Qt.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignLeft)

            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        else:
            # Если нет данных, показываем сообщение
            no_data_label = QLabel("Нет данных о продажах по категориям")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout = QVBoxLayout()
            layout.addWidget(no_data_label)
            self.setLayout(layout)
            return

        self.chart_view.setChart(chart)


class ProductCatalogWidget(QWidget):
    def __init__(self, db_manager, user_role):
        super().__init__()
        self.db_manager = db_manager
        self.user_role = user_role
        self.cart = []
        self.init_ui()
        self.load_categories()
        self.load_products()

    def init_ui(self):
        main_layout = QHBoxLayout()

        # Left sidebar with categories
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout()

        categories_label = QLabel("Категории")
        categories_label.setStyleSheet("font-weight: bold; font-size: 16px; padding: 10px;")
        sidebar_layout.addWidget(categories_label)

        self.categories_list = QListWidget()
        self.categories_list.currentItemChanged.connect(self.on_category_changed)
        sidebar_layout.addWidget(self.categories_list)

        sidebar.setLayout(sidebar_layout)
        main_layout.addWidget(sidebar)

        # Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout()

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск товаров...")
        self.search_input.textChanged.connect(self.load_products)
        search_layout.addWidget(self.search_input)

        content_layout.addLayout(search_layout)

        # Products grid
        self.products_scroll = QScrollArea()
        self.products_widget = QWidget()
        self.products_layout = QGridLayout()
        self.products_widget.setLayout(self.products_layout)
        self.products_scroll.setWidget(self.products_widget)
        self.products_scroll.setWidgetResizable(True)
        content_layout.addWidget(self.products_scroll)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        # Cart sidebar for customers
        if self.user_role == 'customer':
            cart_widget = QWidget()
            cart_widget.setFixedWidth(300)
            cart_layout = QVBoxLayout()

            cart_label = QLabel("Корзина")
            cart_label.setStyleSheet("font-weight: bold; font-size: 16px; padding: 10px;")
            cart_layout.addWidget(cart_label)

            self.cart_list = QListWidget()
            cart_layout.addWidget(self.cart_list)

            self.total_label = QLabel("Итого: 0.00 руб.")
            self.total_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
            cart_layout.addWidget(self.total_label)

            checkout_button = QPushButton("Оформить заказ")
            checkout_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """)
            checkout_button.clicked.connect(self.checkout)
            cart_layout.addWidget(checkout_button)

            clear_button = QPushButton("Очистить корзину")
            clear_button.clicked.connect(self.clear_cart)
            cart_layout.addWidget(clear_button)

            cart_widget.setLayout(cart_layout)
            main_layout.addWidget(cart_widget)

        self.setLayout(main_layout)

    def load_categories(self):
        categories = self.db_manager.get_categories()
        self.categories_list.clear()

        # Add "All categories" item
        all_item = QListWidgetItem("Все категории")
        all_item.setData(Qt.UserRole, None)
        self.categories_list.addItem(all_item)

        for category_id, name in categories:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, category_id)
            self.categories_list.addItem(item)

    def on_category_changed(self, current, previous):
        self.load_products()

    def load_products(self):
        # Clear existing products
        for i in reversed(range(self.products_layout.count())):
            widget = self.products_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Get selected category and search text
        current_item = self.categories_list.currentItem()
        category_id = current_item.data(Qt.UserRole) if current_item else None
        search_text = self.search_input.text() or None

        products = self.db_manager.get_products(category_id, search_text)

        # Add products to grid
        row, col = 0, 0
        max_cols = 3

        for product in products:
            product_card = ProductCard(product, self.add_to_cart)
            self.products_layout.addWidget(product_card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Add stretch to push products to top
        self.products_layout.setRowStretch(row + 1, 1)

    def add_to_cart(self, product):
        product_id, name, description, price, category_name, available, image_url = product

        # Check if product already in cart
        for i in range(self.cart_list.count()):
            item = self.cart_list.item(i)
            if item.data(Qt.UserRole) == product_id:
                # Update quantity
                quantity = item.data(Qt.UserRole + 1) + 1
                item.setText(f"{name} - {quantity} шт. × {price:.2f} руб.")
                item.setData(Qt.UserRole + 1, quantity)
                self.update_total()
                return

        # Add new item to cart
        quantity = 1
        item = QListWidgetItem(f"{name} - {quantity} шт. × {price:.2f} руб.")
        item.setData(Qt.UserRole, product_id)
        item.setData(Qt.UserRole + 1, quantity)
        item.setData(Qt.UserRole + 2, float(price))
        self.cart_list.addItem(item)
        self.update_total()

    def update_total(self):
        total = 0.0
        for i in range(self.cart_list.count()):
            item = self.cart_list.item(i)
            quantity = item.data(Qt.UserRole + 1)
            price = item.data(Qt.UserRole + 2)
            total += quantity * price

        self.total_label.setText(f"Итого: {total:.2f} руб.")

    def clear_cart(self):
        self.cart_list.clear()
        self.update_total()

    def checkout(self):
        if self.cart_list.count() == 0:
            QMessageBox.warning(self, "Ошибка", "Корзина пуста")
            return

        # Prepare items for order
        items = []
        for i in range(self.cart_list.count()):
            item = self.cart_list.item(i)
            product_id = item.data(Qt.UserRole)
            quantity = item.data(Qt.UserRole + 1)
            price = item.data(Qt.UserRole + 2)

            items.append({
                'product_id': product_id,
                'quantity': quantity,
                'price': price
            })

        customer_id = self.db_manager.current_user['customer_id']

        # Get or create default address
        try:
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "SELECT address_id FROM addresses WHERE customer_id = %s LIMIT 1",
                (customer_id,)
            )
            result = cursor.fetchone()

            if not result:
                # Create default address
                cursor.execute("""
                INSERT INTO addresses (customer_id, address_type, street, city, postal_code, country)
                VALUES (%s, 'home', 'ул. Примерная, д. 1', 'Москва', '101000', 'Russia')
                RETURNING address_id
                """, (customer_id,))
                result = cursor.fetchone()

            address_id = result[0]
            cursor.close()

            # Create order
            order_id = self.db_manager.create_order(customer_id, items, address_id)

            if order_id:
                QMessageBox.information(self, "Успех", f"Заказ #{order_id} успешно создан!")
                self.clear_cart()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать заказ")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании заказа: {str(e)}")


class AddEditProductDialog(QDialog):
    def __init__(self, db_manager, product=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.product = product
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Редактировать товар" if self.product else "Добавить товар")
        self.setFixedSize(500, 600)

        layout = QVBoxLayout()

        # Form
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setText(self.product[1] if self.product else "")
        form_layout.addRow("Название:", self.name_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(100)
        if self.product:
            self.description_input.setText(self.product[2])
        form_layout.addRow("Описание:", self.description_input)

        self.price_input = QLineEdit()
        self.price_input.setText(str(self.product[3]) if self.product else "")
        form_layout.addRow("Цена:", self.price_input)

        self.cost_price_input = QLineEdit()
        if self.product:
            self.cost_price_input.setText(str(self.product[4]) if self.product[4] else "")
        form_layout.addRow("Себестоимость:", self.cost_price_input)

        # Category combobox
        self.category_combo = QComboBox()
        categories = self.db_manager.get_all_parent_categories()
        for cat_id, name in categories:
            self.category_combo.addItem(name, cat_id)

        if self.product:
            # Find and set current category
            current_category = self.product[5]  # category_name
            for i in range(self.category_combo.count()):
                if self.category_combo.itemText(i) == current_category:
                    self.category_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Категория:", self.category_combo)

        self.sku_input = QLineEdit()
        if self.product:
            self.sku_input.setText(self.product[6])
        form_layout.addRow("SKU:", self.sku_input)

        # Image URL section
        image_group = QGroupBox("Изображение товара")
        image_layout = QVBoxLayout()

        self.image_url_input = QLineEdit()
        if self.product and len(self.product) > 9:  # image_url
            self.image_url_input.setText(self.product[9] or "")
        self.image_url_input.setPlaceholderText("https://example.com/image.jpg")

        image_preview_btn = QPushButton("Предпросмотр изображения")
        image_preview_btn.clicked.connect(self.preview_image)

        self.image_preview_label = QLabel()
        self.image_preview_label.setFixedSize(150, 100)
        self.image_preview_label.setStyleSheet("""
            border: 1px solid #ddd;
            background-color: #f8f9fa;
        """)
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setText("Предпросмотр")

        image_layout.addWidget(QLabel("URL изображения:"))
        image_layout.addWidget(self.image_url_input)
        image_layout.addWidget(image_preview_btn)
        image_layout.addWidget(self.image_preview_label)
        image_group.setLayout(image_layout)

        form_layout.addRow(image_group)

        self.is_active_check = QCheckBox()
        if self.product:
            self.is_active_check.setChecked(self.product[7])
        else:
            self.is_active_check.setChecked(True)
        form_layout.addRow("Активен:", self.is_active_check)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_product)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Загружаем превью если URL уже указан
        if self.image_url_input.text():
            self.preview_image()

    def preview_image(self):
        """Предпросмотр изображения по URL"""
        image_url = self.image_url_input.text().strip()
        if not image_url:
            return

        try:
            with urllib.request.urlopen(image_url, timeout=10) as response:
                image_data = response.read()

            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if not pixmap.isNull():
                pixmap = pixmap.scaled(150, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview_label.setPixmap(pixmap)
            else:
                self.image_preview_label.setText("❌ Ошибка")

        except Exception as e:
            self.image_preview_label.setText("❌ Ошибка")
            print(f"Error previewing image: {e}")

    def save_product(self):
        name = self.name_input.text()
        description = self.description_input.toPlainText()
        price = self.price_input.text()
        cost_price = self.cost_price_input.text() or None
        category_id = self.category_combo.currentData()
        sku = self.sku_input.text()
        image_url = self.image_url_input.text().strip() or None
        is_active = self.is_active_check.isChecked()

        if not all([name, price, category_id, sku]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля")
            return

        try:
            price = float(price)
            if cost_price:
                cost_price = float(cost_price)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        if self.product:
            # Update existing product
            success = self.db_manager.update_product(
                self.product[0], name, description, price, cost_price,
                category_id, sku, is_active
            )
            # Update image separately
            if success and image_url:
                self.db_manager.update_product_images(self.product[0], image_url)

            if success:
                QMessageBox.information(self, "Успех", "Товар обновлен")
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить товар")
        else:
            # Add new product
            product_id = self.db_manager.add_product(
                name, description, price, cost_price, category_id, sku, image_url
            )
            if product_id:
                QMessageBox.information(self, "Успех", f"Товар добавлен (ID: {product_id})")
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить товар")


class AddEditCategoryDialog(QDialog):
    def __init__(self, db_manager, category=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.category = category
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Редактировать категорию" if self.category else "Добавить категорию")
        self.setFixedSize(400, 400)

        layout = QVBoxLayout()

        # Form
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        if self.category:
            self.name_input.setText(self.category[1])
        form_layout.addRow("Название:", self.name_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(100)
        if self.category:
            self.description_input.setText(self.category[2] or "")
        form_layout.addRow("Описание:", self.description_input)

        # Parent category combobox
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("Нет (родительская категория)", None)
        categories = self.db_manager.get_all_parent_categories()
        for cat_id, name in categories:
            self.parent_combo.addItem(name, cat_id)

        if self.category and self.category[5]:  # parent_category_id
            for i in range(self.parent_combo.count()):
                if self.parent_combo.itemData(i) == self.category[5]:
                    self.parent_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Родительская категория:", self.parent_combo)

        self.image_url_input = QLineEdit()
        if self.category and len(self.category) > 5:
            self.image_url_input.setText(self.category[3] or "")
        form_layout.addRow("URL изображения:", self.image_url_input)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_category)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def save_category(self):
        name = self.name_input.text()
        description = self.description_input.toPlainText()
        parent_id = self.parent_combo.currentData()
        image_url = self.image_url_input.text() or None

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название категории")
            return

        if self.category:
            # Update existing category
            success = self.db_manager.update_category(
                self.category[0], name, description, parent_id, image_url
            )
            if success:
                QMessageBox.information(self, "Успех", "Категория обновлена")
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить категорию")
        else:
            # Add new category
            category_id = self.db_manager.add_category(
                name, description, parent_id, image_url
            )
            if category_id:
                QMessageBox.information(self, "Успех", f"Категория добавлена (ID: {category_id})")
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить категорию")


class AdminProductsWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_products()

    def init_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        add_btn = QPushButton("Добавить товар")
        add_btn.clicked.connect(self.add_product)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_product)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_product)
        toolbar.addWidget(delete_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_products)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Products table
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(10)
        self.products_table.setHorizontalHeaderLabels([
            'ID', 'Название', 'Описание', 'Цена', 'Себестоимость', 'Категория', 'SKU', 'В наличии', 'Статус',
            'Изображение'
        ])
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.products_table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.products_table)

        self.setLayout(layout)

    def load_products(self):
        products = self.db_manager.get_all_products()
        self.products_table.setRowCount(len(products))

        for row, product in enumerate(products):
            for col, value in enumerate(product):
                if isinstance(value, float):
                    value = f"{value:.2f} руб." if col in [3, 4] else str(value)
                elif value is None:
                    value = ""
                elif col == 7:  # Status column
                    value = "Активен" if value else "Неактивен"
                elif col == 8:  # Available quantity
                    value = str(value)
                elif col == 9:  # Image URL
                    value = "Есть" if value else "Нет"

                item = QTableWidgetItem(str(value))
                self.products_table.setItem(row, col, item)

        self.products_table.resizeColumnsToContents()

    def add_product(self):
        dialog = AddEditProductDialog(self.db_manager)
        if dialog.exec_() == QDialog.Accepted:
            self.load_products()

    def edit_product(self):
        selected = self.products_table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите товар для редактирования")
            return

        product_id = int(self.products_table.item(selected, 0).text())
        products = self.db_manager.get_all_products()
        product = None
        for p in products:
            if p[0] == product_id:
                product = p
                break

        if product:
            dialog = AddEditProductDialog(self.db_manager, product)
            if dialog.exec_() == QDialog.Accepted:
                self.load_products()

    def delete_product(self):
        selected = self.products_table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите товар для удаления")
            return

        product_id = int(self.products_table.item(selected, 0).text())
        product_name = self.products_table.item(selected, 1).text()

        reply = QMessageBox.question(
            self, 'Подтверждение удаления',
            f'Вы уверены, что хотите удалить товар "{product_name}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db_manager.delete_product(product_id):
                QMessageBox.information(self, "Успех", "Товар удален")
                self.load_products()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить товар")


class AdminCategoriesWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_categories()

    def init_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        add_btn = QPushButton("Добавить категорию")
        add_btn.clicked.connect(self.add_category)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_category)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_category)
        toolbar.addWidget(delete_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_categories)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Categories table
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(6)
        self.categories_table.setHorizontalHeaderLabels([
            'ID', 'Название', 'Описание', 'Родительская категория', 'Дата создания', 'ID родителя'
        ])
        self.categories_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.categories_table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.categories_table)

        self.setLayout(layout)

    def load_categories(self):
        categories = self.db_manager.get_all_categories_with_parents()
        self.categories_table.setRowCount(len(categories))

        for row, category in enumerate(categories):
            for col, value in enumerate(category):
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M')
                elif value is None:
                    value = ""

                item = QTableWidgetItem(str(value))
                self.categories_table.setItem(row, col, item)

        self.categories_table.resizeColumnsToContents()

    def add_category(self):
        dialog = AddEditCategoryDialog(self.db_manager)
        if dialog.exec_() == QDialog.Accepted:
            self.load_categories()

    def edit_category(self):
        selected = self.categories_table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите категорию для редактирования")
            return

        category_id = int(self.categories_table.item(selected, 0).text())
        categories = self.db_manager.get_all_categories_with_parents()
        category = None
        for cat in categories:
            if cat[0] == category_id:
                category = cat
                break

        if category:
            dialog = AddEditCategoryDialog(self.db_manager, category)
            if dialog.exec_() == QDialog.Accepted:
                self.load_categories()

    def delete_category(self):
        selected = self.categories_table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите категорию для удаления")
            return

        category_id = int(self.categories_table.item(selected, 0).text())
        category_name = self.categories_table.item(selected, 1).text()

        reply = QMessageBox.question(
            self, 'Подтверждение удаления',
            f'Вы уверены, что хотите удалить категорию "{category_name}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db_manager.delete_category(category_id):
                QMessageBox.information(self, "Успех", "Категория удалена")
                self.load_categories()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить категорию")


class AdminUsersWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_users()

    def init_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_users)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(8)
        self.users_table.setHorizontalHeaderLabels([
            'ID', 'Email', 'Роль', 'Имя', 'Фамилия', 'Телефон', 'Дата регистрации', 'Статус'
        ])
        layout.addWidget(self.users_table)

        self.setLayout(layout)

    def load_users(self):
        users = self.db_manager.get_all_users()
        self.users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            for col, value in enumerate(user):
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M')
                elif value is None:
                    value = ""
                elif col == 5:  # Status column
                    value = "Активен" if value else "Неактивен"

                item = QTableWidgetItem(str(value))
                self.users_table.setItem(row, col, item)


class AdminOrdersWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_orders()

    def init_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_orders)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            'ID заказа', 'Дата', 'Статус', 'Сумма', 'Товаров', 'Клиент'
        ])
        layout.addWidget(self.orders_table)

        self.setLayout(layout)

    def load_orders(self):
        orders = self.db_manager.get_all_orders()
        self.orders_table.setRowCount(len(orders))

        for row, order in enumerate(orders):
            for col, value in enumerate(order):
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M')
                elif isinstance(value, float):
                    value = f"{value:.2f} руб."

                self.orders_table.setItem(row, col, QTableWidgetItem(str(value)))


class AdminDashboardWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_stats()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Панель управления - Статистика")
        title.setStyleSheet("font-weight: bold; font-size: 18px; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Stats grid
        stats_grid = QGridLayout()

        # Create stat cards
        self.users_card = self.create_stat_card("👥 Пользователи", "0", "Всего зарегистрировано")
        stats_grid.addWidget(self.users_card, 0, 0)

        self.products_card = self.create_stat_card("📦 Товары", "0", "Всего в каталоге")
        stats_grid.addWidget(self.products_card, 0, 1)

        self.orders_card = self.create_stat_card("📋 Заказы", "0", "Всего оформлено")
        stats_grid.addWidget(self.orders_card, 1, 0)

        self.revenue_card = self.create_stat_card("💰 Выручка", "0 руб.", "Общая выручка")
        stats_grid.addWidget(self.revenue_card, 1, 1)

        layout.addLayout(stats_grid)

        # Charts - только график по категориям
        charts_layout = QHBoxLayout()

        # Category chart
        self.category_chart = CategoryChartWidget(self.db_manager)
        charts_layout.addWidget(self.category_chart)

        layout.addLayout(charts_layout)

        self.setLayout(layout)

    def create_stat_card(self, title, value, description):
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                background-color: white;
            }
        """)

        layout = QVBoxLayout()

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("font-weight: bold; font-size: 24px; color: #333;")
        layout.addWidget(value_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #999;")
        layout.addWidget(desc_label)

        card.setLayout(layout)

        # Store reference to value label for updating
        if title == "👥 Пользователи":
            self.users_value = value_label
        elif title == "📦 Товары":
            self.products_value = value_label
        elif title == "📋 Заказы":
            self.orders_value = value_label
        elif title == "💰 Выручка":
            self.revenue_value = value_label

        return card

    def load_stats(self):
        stats = self.db_manager.get_dashboard_stats()
        if stats:
            self.users_value.setText(str(stats['total_users']))
            self.products_value.setText(str(stats['total_products']))
            self.orders_value.setText(str(stats['total_orders']))
            self.revenue_value.setText(f"{stats['total_revenue']:.2f} руб.")


class AdminPanelWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.tabs = QTabWidget()

        # Dashboard tab
        self.dashboard_tab = AdminDashboardWidget(self.db_manager)
        self.tabs.addTab(self.dashboard_tab, "📊 Дашборд")

        # Users tab
        self.users_tab = AdminUsersWidget(self.db_manager)
        self.tabs.addTab(self.users_tab, "👥 Пользователи")

        # Products tab
        self.products_tab = AdminProductsWidget(self.db_manager)
        self.tabs.addTab(self.products_tab, "📦 Товары")

        # Categories tab
        self.categories_tab = AdminCategoriesWidget(self.db_manager)
        self.tabs.addTab(self.categories_tab, "📁 Категории")

        # Orders tab
        self.orders_tab = AdminOrdersWidget(self.db_manager)
        self.tabs.addTab(self.orders_tab, "📋 Заказы")

        layout.addWidget(self.tabs)
        self.setLayout(layout)


class LoginWindow(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Вход в систему - Магазин электроники')
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        layout = QVBoxLayout()

        # Header
        header_label = QLabel('Магазин электроники')
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; padding: 20px;")
        layout.addWidget(header_label)

        # Login form
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('Введите email')
        form_layout.addRow('Email:', self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow('Пароль:', self.password_input)

        layout.addLayout(form_layout)

        # Login button
        self.login_button = QPushButton('Войти в систему')
        self.login_button.clicked.connect(self.authenticate)
        layout.addWidget(self.login_button)

        # Test credentials
        test_label = QLabel(
            'Тестовые данные:\nadmin@electroshop.ru / 123456\nmanager@electroshop.ru / 123456\nivanov@mail.ru / 123456')
        test_label.setStyleSheet("font-size: 12px; color: #666; padding: 10px;")
        test_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(test_label)

        self.setLayout(layout)

    def authenticate(self):
        email = self.email_input.text()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, 'Ошибка', 'Заполните все поля')
            return

        if self.db_manager.authenticate(email, password):
            self.accept()
        else:
            QMessageBox.warning(self, 'Ошибка', 'Неверные учетные данные')


class OrdersWidget(QWidget):
    def __init__(self, db_manager, user_role):
        super().__init__()
        self.db_manager = db_manager
        self.user_role = user_role
        self.init_ui()
        self.load_orders()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("История заказов")
        title.setStyleSheet("font-weight: bold; font-size: 18px; padding: 10px;")
        layout.addWidget(title)

        # Orders table
        self.orders_table = QTableWidget()
        if self.user_role == 'customer':
            self.orders_table.setColumnCount(5)
            self.orders_table.setHorizontalHeaderLabels([
                'ID заказа', 'Дата', 'Статус', 'Сумма', 'Товаров'
            ])
        else:
            self.orders_table.setColumnCount(6)
            self.orders_table.setHorizontalHeaderLabels([
                'ID заказа', 'Дата', 'Статус', 'Сумма', 'Товаров', 'Клиент'
            ])

        layout.addWidget(self.orders_table)
        self.setLayout(layout)

    def load_orders(self):
        if self.user_role == 'customer':
            customer_id = self.db_manager.current_user['customer_id']
            orders = self.db_manager.get_user_orders(customer_id)
        else:
            orders = self.db_manager.get_all_orders()

        self.orders_table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            for col, value in enumerate(order):
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M')
                elif isinstance(value, float):
                    value = f"{value:.2f} руб."

                self.orders_table.setItem(row, col, QTableWidgetItem(str(value)))


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Магазин электроники - Клиентское приложение')
        self.setGeometry(100, 100, 1400, 900)

        # Set window icon and style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
        """)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Welcome message
        user = self.db_manager.current_user
        welcome_text = f"Добро пожаловать, {user['first_name']} {user['last_name']}!"
        role_text = f"Роль: {user['role']}"

        welcome_layout = QHBoxLayout()

        welcome_label = QLabel(welcome_text)
        welcome_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #333;")
        welcome_layout.addWidget(welcome_label)

        role_label = QLabel(role_text)
        role_label.setStyleSheet(
            "font-size: 14px; color: #666; background-color: #e9ecef; padding: 5px 10px; border-radius: 12px;")
        welcome_layout.addWidget(role_label)

        welcome_layout.addStretch()

        logout_button = QPushButton('Выйти')
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        logout_button.clicked.connect(self.logout)
        welcome_layout.addWidget(logout_button)

        layout.addLayout(welcome_layout)

        # Main tabs - ТОЛЬКО ДЛЯ КЛИЕНТОВ
        self.tabs = QTabWidget()

        user_role = user['role']
        if user_role == 'customer':
            # Product catalog for customers only
            self.catalog_tab = ProductCatalogWidget(self.db_manager, user_role)
            self.tabs.addTab(self.catalog_tab, "🛍️ Каталог товаров")

            # Orders tab for customers only
            self.orders_tab = OrdersWidget(self.db_manager, user_role)
            self.tabs.addTab(self.orders_tab, "📋 Мои заказы")
        else:
            # Admin panel for admin/manager - ТОЛЬКО ЭТА ВКЛАДКА
            self.admin_tab = AdminPanelWidget(self.db_manager)
            self.tabs.addTab(self.admin_tab, "⚙️ Панель управления")

        layout.addWidget(self.tabs)

    def logout(self):
        self.close()


def main():
    app = QApplication(sys.argv)

    # Initialize database connection
    db_manager = DatabaseManager()

    # For demonstration, using default connection parameters
    if not db_manager.connect(host="localhost", user="postgres",
                              password="ilya04062004", database="electronics_store"):
        QMessageBox.critical(None, 'Ошибка', 'Не удалось подключиться к базе данных')
        return 1

    # Show login dialog
    login_dialog = LoginWindow(db_manager)
    if login_dialog.exec_() == QDialog.Accepted:
        main_window = MainWindow(db_manager)
        main_window.show()
        return app.exec_()
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())