import sys
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QTableWidget,
    QComboBox, QLineEdit, QPushButton, QWidget, QLabel
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from datetime import date, timedelta


DB_NAME = "kursach.db"
AUTH_UI = "auth_window.ui"


def build_stylesheet_dark() -> str:
    bg = "#121212"
    surface = "#1e1e1e"
    text = "#eaeaea"
    primary = "#3a86ff"
    border = "#2a2a2a"
    hover = "#2a2a2a"

    return f"""
        QWidget {{
            color: {text};
            background: {bg};
            font-size: 14px;
        }}
        QMainWindow {{
            background: {bg};
        }}
        QMenuBar {{
            background: {surface};
            color: {text};
            border-bottom: 1px solid {border};
        }}
        QMenuBar::item:selected {{
            background: {hover};
        }}
        QMenu {{
            background: {surface};
            border: 1px solid {border};
        }}
        QTabWidget::pane {{
            border: 1px solid {border};
            border-radius: 10px;
            background: {surface};
        }}
        QTabBar::tab {{
            padding: 8px 14px;
            border: 1px solid {border};
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            background: {surface};
            margin-right: 4px;
        }}
        QTabBar::tab:selected {{
            background: {hover};
        }}
        QTableWidget {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 12px;
            gridline-color: {border};
        }}
        QHeaderView::section {{
            background: {surface};
            color: {text};
            padding: 8px;
            border: none;
            border-right: 1px solid {border};
        }}
        QLineEdit, QComboBox {{
            background: {surface};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 8px 10px;
        }}
        QLineEdit:hover, QComboBox:hover {{
            border-color: {primary};
        }}
        QPushButton {{
            background: {primary};
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 8px 14px;
        }}
        QPushButton:hover {{
            background: #316fd6;
        }}
        QPushButton:disabled {{
            background: #9aa9c7;
        }}
        QLabel#labelMessage {{
            padding: 6px 8px;
            border-radius: 8px;
        }}
    """


def apply_shadows(widgets):
    for w in widgets:
        if not w:
            continue
        try:
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(20)
            effect.setOffset(0, 6)
            effect.setColor(Qt.black)
            w.setGraphicsEffect(effect)
        except Exception:
            pass

class UserWindow(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        loader = QUiLoader()
        ui_file = QFile("user_page.ui")
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError("Не удалось открыть user_window.ui")
        loaded = loader.load(ui_file)
        ui_file.close()

        if loaded is None:
            raise RuntimeError("Ошибка загрузки UI из user_window.ui")

        
        if isinstance(loaded, QMainWindow):
            cw = loaded.centralWidget()
            if cw is None:
                raise RuntimeError("В user_window.ui у QMainWindow отсутствует centralWidget")
            cw.setParent(self)
            self.setCentralWidget(cw)
            try:
                self.setWindowTitle(loaded.windowTitle())
            except Exception:
                pass
            self.ui_root = cw
        elif isinstance(loaded, QWidget):
            self.setCentralWidget(loaded)
            self.ui_root = loaded
        else:
            raise RuntimeError("Неподдерживаемый корневой виджет в user_window.ui")

        self.adjustSize()
        
        self.tableProducts = self.ui_root.findChild(QTableWidget, "tableProducts")
        self.btnBuy = self.ui_root.findChild(QPushButton, "btnBuy")
        self.labelMessage = self.ui_root.findChild(QLabel, "labelMessage")
        # Buy quantity spinbox from user_page.ui
        from PySide6.QtWidgets import QSpinBox
        self.inputBuyQuantityUser = self.ui_root.findChild(QSpinBox, "inputBuyQuantityUser")

        # Add logout button for user window
        self.btnLogoutUser = self.ui_root.findChild(QPushButton, "btnLogoutUser")
        if self.btnLogoutUser:
            self.btnLogoutUser.clicked.connect(self.logout)

        # Add clients table for user window (if present in UI)
        self.tableClients = self.ui_root.findChild(QTableWidget, "tableClients")

        if self.btnBuy:
            self.btnBuy.clicked.connect(self.buy_product)

        self.init_menu_and_theme()
        self.init_db()
        # Load clients before showing the window
        self.load_clients()
        self.refresh_products()
        try:
            self.resize(720, 520)
        except Exception:
            pass
        self.show()

    def init_menu_and_theme(self):
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(build_stylesheet_dark())
        apply_shadows([
            getattr(self, 'tableProducts', None),
            getattr(self, 'tableClients', None),
        ])
        

    def logout(self):
        from main import AuthWindow
        self.auth_window = AuthWindow()
        self.close()

    def load_clients(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT users.id, users.username, clients.phone, clients.email, users.password
            FROM users
            LEFT JOIN clients ON users.username = clients.name
            WHERE users.username != 'admin'
        """)
        rows = cur.fetchall()
        conn.close()

        if self.tableClients:
            self.tableClients.setRowCount(0)
            self.tableClients.setColumnCount(4)
            self.tableClients.setHorizontalHeaderLabels(["Логин", "Телефон", "Email", "Пароль"])
            for i, (uid, username, phone, email, password) in enumerate(rows):
                self.tableClients.insertRow(i)
                item0 = QTableWidgetItem(username)
                item0.setData(Qt.UserRole, uid)
                self.tableClients.setItem(i, 0, item0)
                self.tableClients.setItem(i, 1, QTableWidgetItem(phone if phone else ""))
                self.tableClients.setItem(i, 2, QTableWidgetItem(email if email else ""))
                self.tableClients.setItem(i, 3, QTableWidgetItem(password if password else ""))

    def get_connection(self):
        return sqlite3.connect(DB_NAME)

    def init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()
        # Create products table if not exists, but check for quantity column separately
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL
            )
        """)
        # Check if quantity column exists, add if missing
        cur.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cur.fetchall()]
        if "quantity" not in columns:
            cur.execute("ALTER TABLE products ADD COLUMN quantity INTEGER DEFAULT 0")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                product_id INTEGER,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                date TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """)
        conn.commit()
        conn.close()

    def refresh_products(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, quantity FROM products")
        rows = cur.fetchall()
        conn.close()
        if self.tableProducts:
            self.tableProducts.setRowCount(0)
            self.tableProducts.setColumnCount(3)
            self.tableProducts.setHorizontalHeaderLabels(["Название", "Цена", "Кол-во"])
            for i, (pid, name, price, quantity) in enumerate(rows):
                self.tableProducts.insertRow(i)
                item0 = QTableWidgetItem(name)
                item0.setData(Qt.UserRole, pid)
                self.tableProducts.setItem(i, 0, item0)
                self.tableProducts.setItem(i, 1, QTableWidgetItem(f"{price} ₽"))
                self.tableProducts.setItem(i, 2, QTableWidgetItem(str(quantity)))

    def buy_product(self):
        if not self.tableProducts:
            return
        row = self.tableProducts.currentRow()
        if row < 0:
            if self.labelMessage:
                self.labelMessage.setText("Выберите товар для покупки.")
            return
        item = self.tableProducts.item(row, 0)
        if not item:
            if self.labelMessage:
                self.labelMessage.setText("Ошибка выбора товара.")
            return
        pid = item.data(Qt.UserRole)
        if pid is None:
            if self.labelMessage:
                self.labelMessage.setText("Ошибка товара.")
            return
        # Read quantity to buy from inputBuyQuantityUser
        quantity_to_buy = 1
        if hasattr(self, "inputBuyQuantityUser") and self.inputBuyQuantityUser:
            quantity_to_buy = self.inputBuyQuantityUser.value()
        if quantity_to_buy < 1:
            if self.labelMessage:
                self.labelMessage.setText("Укажите количество больше 0.")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        # Get current quantity
        cur.execute("SELECT quantity FROM products WHERE id = ?", (pid,))
        row_prod = cur.fetchone()
        if not row_prod:
            conn.close()
            if self.labelMessage:
                self.labelMessage.setText("Товар не найден.")
            return
        current_quantity = row_prod[0]
        if quantity_to_buy > current_quantity:
            conn.close()
            if self.labelMessage:
                self.labelMessage.setText("Недостаточно товара на складе.")
            return
        # Insert purchase(s)
        for _ in range(quantity_to_buy):
            cur.execute(
                "INSERT INTO purchases (username, product_id) VALUES (?, ?)",
                (self.username, pid)
            )
        # Deduct quantity or delete product if 0 left
        new_quantity = current_quantity - quantity_to_buy
        if new_quantity > 0:
            cur.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_quantity, pid))
        else:
            cur.execute("DELETE FROM products WHERE id = ?", (pid,))
        # Create order for the current user with delivery date = today + 3 days
        try:
            cur.execute("SELECT id FROM clients WHERE name = ?", (self.username,))
            client_row = cur.fetchone()
            if client_row:
                client_id = client_row[0]
                delivery_date = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
                cur.execute("INSERT INTO orders (client_id, date) VALUES (?, ?)", (client_id, delivery_date))
        except Exception:
            pass
        conn.commit()
        conn.close()
        # Cleanup expired orders after purchase
        try:
            self.cleanup_expired_orders()
        except Exception:
            pass
        self.refresh_products()
        if self.labelMessage:
            self.labelMessage.setText("Покупка успешно совершена!")

    def cleanup_expired_orders(self):
        conn = self.get_connection()
        cur = conn.cursor()
        today_str = date.today().strftime("%Y-%m-%d")
        cur.execute("DELETE FROM orders WHERE date <= ?", (today_str,))
        conn.commit()
        conn.close()


class AuthWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loader = QUiLoader()
        ui_file = QFile("auth.ui")
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Не удалось открыть {"auth.ui"}")
        loaded = loader.load(ui_file)
        ui_file.close()

        if loaded is None:
            raise RuntimeError(f"Ошибка загрузки UI из {"auth.ui"}")

        if isinstance(loaded, QMainWindow):
            cw = loaded.centralWidget()
            if cw is None:
                raise RuntimeError(f"В {"auth.ui"} у QMainWindow отсутствует centralWidget")
            cw.setParent(self)
            self.setCentralWidget(cw)
            try:
                self.setWindowTitle(loaded.windowTitle())
            except Exception:
                pass
            self.ui_root = cw
        elif isinstance(loaded, QWidget):
            self.setCentralWidget(loaded)
            self.ui_root = loaded
        else:
            raise RuntimeError(f"Неподдерживаемый корневой виджет в {AUTH_UI}")

        self.adjustSize()
        self.apply_theme()


        self.inputLogin = self.ui_root.findChild(QLineEdit, "inputLogin")
        self.inputPassword = self.ui_root.findChild(QLineEdit, "inputPassword")
        self.inputPhone = self.ui_root.findChild(QLineEdit, "inputPhone")
        self.inputEmail = self.ui_root.findChild(QLineEdit, "inputEmail")


        self.btnLogin = self.ui_root.findChild(QPushButton, "btnLogin")
        self.btnRegister = self.ui_root.findChild(QPushButton, "btnRegister")


        self.labelError = self.ui_root.findChild(QLabel, "labelError")

        if self.btnLogin:
            self.btnLogin.clicked.connect(self.login)
        if self.btnRegister:
            self.btnRegister.clicked.connect(self.register)

        self.init_db()
        try:
            self.cleanup_expired_orders()
        except Exception:
            pass
        self.ensure_admin()
        self.show()

    def apply_theme(self):
        self.setStyleSheet(build_stylesheet_dark())
        apply_shadows([
            getattr(self, 'tableProducts', None),
            getattr(self, 'tableClients', None),
        ])

    def get_connection(self):
        return sqlite3.connect(DB_NAME)

    def init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT
            )
        """)
        conn.commit()
        conn.close()

    def cleanup_expired_orders(self):
        conn = self.get_connection()
        cur = conn.cursor()
        today_str = date.today().strftime("%Y-%m-%d")
        cur.execute("DELETE FROM orders WHERE date <= ?", (today_str,))
        conn.commit()
        conn.close()

    def ensure_admin(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", ("admin",))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
            conn.commit()
        conn.close()

    def login(self):
        username = self.inputLogin.text() if self.inputLogin else ""
        password = self.inputPassword.text() if self.inputPassword else ""
        if not username or not password:
            if self.labelError:
                self.labelError.setText("Введите логин и пароль")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
        row = cur.fetchone()
        conn.close()
        if row:
            role = row[0]
            if self.labelError:
                self.labelError.setText("")
            if role == "admin":
                self.client_app = ClientApp()
                self.close()
            else:
                self.user_app = UserWindow(username)
                self.close()
        else:
            if self.labelError:
                self.labelError.setText("Неверный логин или пароль")

    def register(self):
        username = self.inputLogin.text() if self.inputLogin else ""
        password = self.inputPassword.text() if self.inputPassword else ""
        phone = self.inputPhone.text() if self.inputPhone else ""
        email = self.inputEmail.text() if self.inputEmail else ""
        if not username or not password:
            if self.labelError:
                self.labelError.setText("Введите логин и пароль")
            return
        if not phone or not email:
            if self.labelError:
                self.labelError.setText("Введите телефон и email")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            if self.labelError:
                self.labelError.setText("Пользователь уже существует")
            conn.close()
            return
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, "user"))
        cur.execute("INSERT INTO clients (name, phone, email) VALUES (?, ?, ?)", (username, phone, email))
        conn.commit()
        conn.close()
        if self.labelError:
            self.labelError.setText("Регистрация успешна. Теперь вы можете войти.")


class ClientApp(QMainWindow):
    def __init__(self):
        super().__init__()
        loader = QUiLoader()
        ui_file = QFile("main_window.ui")
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError("Не удалось открыть main_window.ui")
        loaded = loader.load(ui_file)
        ui_file.close()

        if loaded is None:
            raise RuntimeError("Ошибка загрузки UI из main_window.ui")


        if isinstance(loaded, QMainWindow):
            cw = loaded.centralWidget()
            if cw is None:
                raise RuntimeError("В main_window.ui у QMainWindow отсутствует centralWidget")
            cw.setParent(self)
            self.setCentralWidget(cw)

            try:
                self.setWindowTitle(loaded.windowTitle())
            except Exception:
                pass
            self.ui_root = cw
        elif isinstance(loaded, QWidget):
            self.setCentralWidget(loaded)
            self.ui_root = loaded
        else:
            raise RuntimeError("Неподдерживаемый корневой виджет в main_window.ui")

        self.adjustSize()
        

        self.tableClients = self.ui_root.findChild(QTableWidget, "tableClients")
        self.tableProducts = self.ui_root.findChild(QTableWidget, "tableProducts")
        self.tableOrders = self.ui_root.findChild(QTableWidget, "tableOrders")

        self.comboClient = self.ui_root.findChild(QComboBox, "comboClient")

        self.inputClientName  = self.ui_root.findChild(QLineEdit, "inputClientName")
        self.inputClientPhone = self.ui_root.findChild(QLineEdit, "inputClientPhone")
        self.inputClientEmail = self.ui_root.findChild(QLineEdit, "inputClientEmail")
        # New input for password (assume exists in UI)
        self.inputUserPassword = self.ui_root.findChild(QLineEdit, "inputUserPassword")

        self.inputProductName  = self.ui_root.findChild(QLineEdit, "inputProductName")
        self.inputProductPrice = self.ui_root.findChild(QLineEdit, "inputProductPrice")
        # Add reference to inputProductQuantity
        from PySide6.QtWidgets import QSpinBox
        self.inputProductQuantity = self.ui_root.findChild(QSpinBox, "inputProductQuantity")

        self.inputOrderDate    = self.ui_root.findChild(QLineEdit, "inputOrderDate")

        self.btnAddClient    = self.ui_root.findChild(QPushButton, "btnAddClient")
        self.btnDeleteClient = self.ui_root.findChild(QPushButton, "btnDeleteClient")
        self.btnAddProduct    = self.ui_root.findChild(QPushButton, "btnAddProduct")
        self.btnDeleteProduct = self.ui_root.findChild(QPushButton, "btnDeleteProduct")
        self.btnAddOrder    = self.ui_root.findChild(QPushButton, "btnAddOrder")
        self.btnDeleteOrder = self.ui_root.findChild(QPushButton, "btnDeleteOrder")
        # New button for password change (assume exists in UI)
        self.btnChangePassword = self.ui_root.findChild(QPushButton, "btnChangePassword")
        # Button for logout (assume exists in UI)
        self.btnLogout = self.ui_root.findChild(QPushButton, "btnLogout")

        if self.btnAddClient:    self.btnAddClient.clicked.connect(self.add_client)
        if self.btnDeleteClient: self.btnDeleteClient.clicked.connect(self.delete_client)
        if self.btnAddProduct:    self.btnAddProduct.clicked.connect(self.add_product)
        if self.btnDeleteProduct: self.btnDeleteProduct.clicked.connect(self.delete_product)
        if self.btnAddOrder:    self.btnAddOrder.clicked.connect(self.add_order)
        if self.btnDeleteOrder: self.btnDeleteOrder.clicked.connect(self.delete_order)
        if self.btnChangePassword: self.btnChangePassword.clicked.connect(self.change_user_password)
        if self.btnLogout: self.btnLogout.clicked.connect(self.logout)

        self.apply_theme()
        self.init_db()
        try:
            self.cleanup_expired_orders()
        except Exception:
            pass
        self.refresh_all()
        self.show()

    def get_connection(self):
        return sqlite3.connect(DB_NAME)

    def init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT
            )
        """)
        # Create products table if not exists, but check for quantity column separately
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL
            )
        """)
        # Check if quantity column exists, add if missing
        cur.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cur.fetchall()]
        if "quantity" not in columns:
            cur.execute("ALTER TABLE products ADD COLUMN quantity INTEGER DEFAULT 0")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                date TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """)
        conn.commit()
        conn.close()

    def apply_theme(self):
        self.setStyleSheet(build_stylesheet_dark())
        apply_shadows([
            getattr(self, 'tableClients', None),
            getattr(self, 'tableProducts', None),
            getattr(self, 'tableOrders', None),
        ])
        

    def cleanup_expired_orders(self):
        conn = self.get_connection()
        cur = conn.cursor()
        today_str = date.today().strftime("%Y-%m-%d")
        cur.execute("DELETE FROM orders WHERE date <= ?", (today_str,))
        conn.commit()
        conn.close()

    def refresh_all(self):
        self.load_clients()
        self.load_products()
        self.load_orders()


    def load_clients(self):
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            # LEFT JOIN users and clients, exclude admin, show password
            cur.execute("""
                SELECT users.id, users.username, clients.phone, clients.email, users.password
                FROM users
                LEFT JOIN clients ON users.username = clients.name
                WHERE users.username != 'admin'
            """)
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки клиентов: {e}")
            return

        self.tableClients.setRowCount(0)
        self.tableClients.setColumnCount(4)
        self.tableClients.setHorizontalHeaderLabels(["Логин", "Телефон", "Email", "Пароль"])
        self.comboClient.clear()
        for i, (uid, username, phone, email, password) in enumerate(rows):
            self.tableClients.insertRow(i)
            item0 = QTableWidgetItem(username)
            item0.setData(Qt.UserRole, uid)
            self.tableClients.setItem(i, 0, item0)
            self.tableClients.setItem(i, 1, QTableWidgetItem(phone if phone else ""))
            self.tableClients.setItem(i, 2, QTableWidgetItem(email if email else ""))
            self.tableClients.setItem(i, 3, QTableWidgetItem(password if password else ""))
            self.comboClient.addItem(f"{uid}: {username}", uid)

    def logout(self):
        # Закрыть текущее окно и открыть окно авторизации
        self.auth_window = AuthWindow()
        self.close()

    def add_client(self):
        name  = self.inputClientName.text() if self.inputClientName else ""
        phone = self.inputClientPhone.text() if self.inputClientPhone else ""
        email = self.inputClientEmail.text() if self.inputClientEmail else ""
        password = self.inputUserPassword.text() if self.inputUserPassword else ""
        if not name or not password:
            QMessageBox.warning(self, "Ошибка", "Введите имя и пароль клиента!")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        # Добавить в users и clients
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (name, password, "user"))
        cur.execute("INSERT INTO clients(name, phone, email) VALUES (?, ?, ?)", (name, phone, email))
        conn.commit()
        conn.close()
        self.refresh_all()
        if self.inputClientName:
            self.inputClientName.clear()
        if self.inputClientPhone:
            self.inputClientPhone.clear()
        if self.inputClientEmail:
            self.inputClientEmail.clear()
        if self.inputUserPassword:
            self.inputUserPassword.clear()

    def change_user_password(self):
        row = self.tableClients.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя!")
            return
        item = self.tableClients.item(row, 0)
        if not item:
            QMessageBox.warning(self, "Ошибка", "Ошибка выбора пользователя!")
            return
        cid = item.data(Qt.UserRole)
        if cid is None:
            QMessageBox.warning(self, "Ошибка", "Ошибка идентификатора пользователя!")
            return

        new_pass = self.inputUserPassword.text() if self.inputUserPassword else ""
        if not new_pass:
            QMessageBox.warning(self, "Ошибка", "Введите новый пароль!")
            return

        conn = self.get_connection()
        cur = conn.cursor()
        # Найти username по client_id
        cur.execute("SELECT name FROM clients WHERE id = ?", (cid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            QMessageBox.warning(self, "Ошибка", "Пользователь не найден!")
            return
        username = row[0]
        # Обновить пароль
        cur.execute("UPDATE users SET password = ? WHERE username = ?", (new_pass, username))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Успех", f"Пароль для {username} обновлен!")
        if self.inputUserPassword:
            self.inputUserPassword.clear()

    def delete_client(self):
        row = self.tableClients.currentRow()
        if row < 0:
            return
        item = self.tableClients.item(row, 0)
        if not item:
            return
        uid = item.data(Qt.UserRole)
        if uid is None:
            return

        conn = self.get_connection()
        cur = conn.cursor()
        # Get username from users table
        cur.execute("SELECT username FROM users WHERE id = ?", (uid,))
        row_user = cur.fetchone()
        if not row_user:
            conn.close()
            return
        username = row_user[0]
        if username == "admin":
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить админа!")
            conn.close()
            return
        # Delete from users and clients
        cur.execute("DELETE FROM users WHERE id = ?", (uid,))
        cur.execute("DELETE FROM clients WHERE name = ?", (username,))
        conn.commit()
        conn.close()
        self.refresh_all()

    def load_products(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, quantity FROM products")
        rows = cur.fetchall()
        conn.close()

        self.tableProducts.setRowCount(0)
        self.tableProducts.setColumnCount(3)
        self.tableProducts.setHorizontalHeaderLabels(["Название", "Цена", "Кол-во"])

        for i, (pid, name, price, quantity) in enumerate(rows):
            self.tableProducts.insertRow(i)
            item0 = QTableWidgetItem(name)
            item0.setData(Qt.UserRole, pid)
            self.tableProducts.setItem(i, 0, item0)
            self.tableProducts.setItem(i, 1, QTableWidgetItem(f"{price} ₽"))
            self.tableProducts.setItem(i, 2, QTableWidgetItem(str(quantity)))

    def add_product(self):
        name  = self.inputProductName.text()  if self.inputProductName  else ""
        price = self.inputProductPrice.text() if self.inputProductPrice else ""
        quantity = 1
        if hasattr(self, "inputProductQuantity") and self.inputProductQuantity:
            quantity = self.inputProductQuantity.value()
        if not name or not price:
            QMessageBox.warning(self, "Ошибка", "Введите данные товара!")
            return
        if quantity < 1:
            QMessageBox.warning(self, "Ошибка", "Введите количество больше 0!")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO products(name, price, quantity) VALUES(?, ?, ?)", (name, price, quantity))
        conn.commit()
        conn.close()
        self.refresh_all()

    def delete_product(self):
        row = self.tableProducts.currentRow()
        if row < 0:
            return
        item = self.tableProducts.item(row, 0)
        if not item:
            return
        pid = item.data(Qt.UserRole)
        if pid is None:
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = ?", (pid,))
        conn.commit()
        conn.close()
        self.refresh_all()

    
    def load_orders(self):
        try:
            self.cleanup_expired_orders()
        except Exception:
            pass
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT orders.id, clients.name, date
            FROM orders
            JOIN clients ON clients.id = orders.client_id
        """)
        rows = cur.fetchall()
        conn.close()

        self.tableOrders.setRowCount(0)
        self.tableOrders.setColumnCount(2)
        self.tableOrders.setHorizontalHeaderLabels(["Клиент", "Дата"])

        for i, (oid, cname, date) in enumerate(rows):
            self.tableOrders.insertRow(i)
            item0 = QTableWidgetItem(cname)
            item0.setData(Qt.UserRole, oid)
            self.tableOrders.setItem(i, 0, item0)
            self.tableOrders.setItem(i, 1, QTableWidgetItem(date))

    def add_order(self):
        cid = self.comboClient.currentData()
        date = self.inputOrderDate.text() if self.inputOrderDate else ""
        if not cid:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента!")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO orders(client_id, date) VALUES(?, ?)", (cid, date))
        conn.commit()
        conn.close()
        self.refresh_all()

    def delete_order(self):
        row = self.tableOrders.currentRow()
        if row < 0:
            return
        item = self.tableOrders.item(row, 0)
        if not item:
            return
        oid = item.data(Qt.UserRole)
        if oid is None:
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id = ?", (oid,))
        conn.commit()
        conn.close()
        self.refresh_all()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthWindow()
    sys.exit(app.exec())