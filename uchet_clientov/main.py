import sys
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QTableWidget,
    QComboBox, QLineEdit, QPushButton, QWidget, QLabel
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtCore import Qt


DB_NAME = "kursach.db"
AUTH_UI = "auth_window.ui"


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

        if self.btnBuy:
            self.btnBuy.clicked.connect(self.buy_product)

        self.init_db()
        self.refresh_products()
        self.show()

    def get_connection(self):
        return sqlite3.connect(DB_NAME)

    def init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                product_id INTEGER,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        conn.commit()
        conn.close()

    def refresh_products(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price FROM products")
        rows = cur.fetchall()
        conn.close()
        if self.tableProducts:
            self.tableProducts.setRowCount(0)
            self.tableProducts.setColumnCount(2)
            self.tableProducts.setHorizontalHeaderLabels(["Название", "Цена"])
            for i, (pid, name, price) in enumerate(rows):
                self.tableProducts.insertRow(i)
                item0 = QTableWidgetItem(name)
                item0.setData(Qt.UserRole, pid)
                self.tableProducts.setItem(i, 0, item0)
                self.tableProducts.setItem(i, 1, QTableWidgetItem(str(price)))

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
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO purchases (username, product_id) VALUES (?, ?)",
            (self.username, pid)
        )
        conn.commit()
        conn.close()
        if self.labelMessage:
            self.labelMessage.setText("Покупка успешно совершена!")


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
        self.ensure_admin()
        self.show()

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

        self.inputProductName  = self.ui_root.findChild(QLineEdit, "inputProductName")
        self.inputProductPrice = self.ui_root.findChild(QLineEdit, "inputProductPrice")

        self.inputOrderDate    = self.ui_root.findChild(QLineEdit, "inputOrderDate")

        
        self.btnAddClient    = self.ui_root.findChild(QPushButton, "btnAddClient")
        self.btnDeleteClient = self.ui_root.findChild(QPushButton, "btnDeleteClient")
        self.btnAddProduct    = self.ui_root.findChild(QPushButton, "btnAddProduct")
        self.btnDeleteProduct = self.ui_root.findChild(QPushButton, "btnDeleteProduct")
        self.btnAddOrder    = self.ui_root.findChild(QPushButton, "btnAddOrder")
        self.btnDeleteOrder = self.ui_root.findChild(QPushButton, "btnDeleteOrder")

        
        if self.btnAddClient:    self.btnAddClient.clicked.connect(self.add_client)
        if self.btnDeleteClient: self.btnDeleteClient.clicked.connect(self.delete_client)
        if self.btnAddProduct:    self.btnAddProduct.clicked.connect(self.add_product)
        if self.btnDeleteProduct: self.btnDeleteProduct.clicked.connect(self.delete_product)
        if self.btnAddOrder:    self.btnAddOrder.clicked.connect(self.add_order)
        if self.btnDeleteOrder: self.btnDeleteOrder.clicked.connect(self.delete_order)

        self.init_db()
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL
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

    def refresh_all(self):
        self.load_clients()
        self.load_products()
        self.load_orders()

    
    def load_clients(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, phone, email FROM clients")
        rows = cur.fetchall()
        conn.close()

        self.tableClients.setRowCount(0)
        self.tableClients.setColumnCount(3)
        self.tableClients.setHorizontalHeaderLabels(["Имя", "Телефон", "Email"])
        self.comboClient.clear()
        for i, (cid, name, phone, email) in enumerate(rows):
            self.tableClients.insertRow(i)
            item0 = QTableWidgetItem(name)
            item0.setData(Qt.UserRole, cid)
            self.tableClients.setItem(i, 0, item0)
            self.tableClients.setItem(i, 1, QTableWidgetItem(phone))
            self.tableClients.setItem(i, 2, QTableWidgetItem(email))
            self.comboClient.addItem(f"{cid}: {name}", cid)

    def add_client(self):
        name  = self.inputClientName.text() if self.inputClientName else ""
        phone = self.inputClientPhone.text() if self.inputClientPhone else ""
        email = self.inputClientEmail.text() if self.inputClientEmail else ""
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя клиента!")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO clients(name, phone, email) VALUES(?, ?, ?)", (name, phone, email))
        conn.commit()
        conn.close()
        self.refresh_all()

    def delete_client(self):
        row = self.tableClients.currentRow()
        if row < 0:
            return
        item = self.tableClients.item(row, 0)
        if not item:
            return
        cid = item.data(Qt.UserRole)
        if cid is None:
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM clients WHERE id = ?", (cid,))
        conn.commit()
        conn.close()
        self.refresh_all()
    
    def load_products(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price FROM products")
        rows = cur.fetchall()
        conn.close()

        self.tableProducts.setRowCount(0)
        self.tableProducts.setColumnCount(2)
        self.tableProducts.setHorizontalHeaderLabels(["Название", "Цена"])

        for i, (pid, name, price) in enumerate(rows):
            self.tableProducts.insertRow(i)
            item0 = QTableWidgetItem(name)
            item0.setData(Qt.UserRole, pid)
            self.tableProducts.setItem(i, 0, item0)
            self.tableProducts.setItem(i, 1, QTableWidgetItem(str(price)))

    def add_product(self):
        name  = self.inputProductName.text()  if self.inputProductName  else ""
        price = self.inputProductPrice.text() if self.inputProductPrice else ""
        if not name or not price:
            QMessageBox.warning(self, "Ошибка", "Введите данные товара!")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO products(name, price) VALUES(?, ?)", (name, price))
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