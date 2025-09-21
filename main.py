import sys
# Cargar variables de entorno desde .env automáticamente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print('ADVERTENCIA: python-dotenv no está instalado. Variables de entorno desde .env no serán cargadas automáticamente.', file=sys.stderr)
# DEBUG: print y log de arranque
print('INICIO DEL PROGRAMA', file=sys.stderr)
with open('arranque_log.txt', 'a', encoding='utf-8') as f:
    f.write('INICIO DEL PROGRAMA\n')
import webbrowser
import urllib.parse
import csv
from collections import defaultdict
from datetime import datetime, date, time, timedelta
import { SpeedInsights } from "@vercel/speed-insights/next"
import mysql.connector
from mysql.connector import Error

from PyQt5.QtCore import Qt, QSize, QDate, QTimer
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QSpacerItem, QSizePolicy,
    QFileDialog, QDateEdit, QComboBox
)

from controller import *

# ---------------- Login Dialog ----------------
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 Login Administrador")
        self.setFixedSize(500, 450)  # Aumenta el alto para el logo
        self.user_role = None  # Para saber el perfil

        main = QVBoxLayout(self)

        # Logo arriba del título (ajusta la ruta si es necesario)
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(QPixmap("logo.jpg").scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        main.addWidget(logo)

        title = QLabel("Burga al Corte - Acceso Admin")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18px; font-weight:bold; color:white; background:#d32f2f; padding:10px; border-radius:8px;")
        main.addWidget(title)
        main.addSpacing(8)

        self.user_edit = QLineEdit(); self.user_edit.setPlaceholderText("Usuario")
        self.pass_edit = QLineEdit(); self.pass_edit.setPlaceholderText("Contraseña"); self.pass_edit.setEchoMode(QLineEdit.Password)
        for w in (self.user_edit, self.pass_edit):
            w.setFixedHeight(36); w.setStyleSheet("padding:6px; font-size:14px;")
        main.addWidget(self.user_edit); main.addWidget(self.pass_edit)

        main.addSpacing(6)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet("color:#bbb;"); main.addWidget(sep)

        btn = QPushButton("Ingresar"); btn.setFixedHeight(36)
        btn.setStyleSheet("background:#1976d2; color:white; font-weight:bold; border-radius:8px;")
        btn.clicked.connect(self.accept_login)
        main.addWidget(btn)

    def accept_login(self):
        u = self.user_edit.text().strip()
        p = self.pass_edit.text().strip()
        if u in ADMIN_CREDENTIALS:
            if u == "cajero":
                self.user_role = "cajero"
                self.accept()
                return
            elif ADMIN_CREDENTIALS[u] == p:
                self.user_role = "admin"
                self.accept()
                return
        QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos")

# ---------------- Customer Dialog ----------------
class ClienteDialog(QDialog):
    def __init__(self, metodo_pago, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Confirmar Pedido - {metodo_pago}")
        self.setFixedSize(420, 220)
        self.nombre = ""
        self.direccion = ""
        self.metodo_pago = metodo_pago

        lay = QVBoxLayout(self)
        lbl = QLabel("Completá los datos del cliente"); lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:16px; font-weight:bold;"); lay.addWidget(lbl)

        self.edit_nombre = QLineEdit(); self.edit_nombre.setPlaceholderText("Nombre del cliente")
        self.edit_direccion = QLineEdit(); self.edit_direccion.setPlaceholderText("Dirección")
        for w in (self.edit_nombre, self.edit_direccion):
            w.setFixedHeight(36); lay.addWidget(w)

        lay.addSpacing(6)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); lay.addWidget(sep)

        boton = QPushButton("Confirmar pedido")
        boton.setStyleSheet("background:#2e7d32; color:#fff; font-weight:bold; height:36px; border-radius:8px;")
        boton.clicked.connect(self.confirmar)
        lay.addWidget(boton)

    def confirmar(self):
        self.nombre = self.edit_nombre.text().strip()
        self.direccion = self.edit_direccion.text().strip()
        self.telefono = ""  # Siempre vacío
        if not self.nombre or not self.direccion:
            QMessageBox.warning(self, "Faltan datos", "Completá nombre y dirección.")
            return
        self.accept()

# ---------------- Main Window ----------------
class MainWindow(QMainWindow):
    def __init__(self, user_role="admin"):
        super().__init__()
        self.user_role = user_role  # Guardar el rol para chequeos internos
        self.setWindowTitle("Burga al Corte - Admin")
        self.resize(1200, 800)

        self.theme = 'night'
        self.carrito = {}

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_menu = QWidget()
        self.tab_ventas = QWidget()
        self.tab_recaud = QWidget()
        self.tab_cierres = QWidget()
        self.tab_reportes = QWidget()

        # Encapsular la lógica de pestañas según el rol
        if self.user_role == "cajero":
            self.setup_tabs_for_cajero()
        else:
            self.setup_tabs_for_admin()

        # Build UI solo para las pestañas visibles
        self.build_menu_tab()
        self.build_ventas_tab()
        if self.user_role != "cajero":
            self.build_recaud_tab()
            self.build_historial_tab()
            self.build_reportes_tab()

        ensure_cierres_table()
        self.load_productos_grid()
        self.refresh_ventas()
        self.apply_theme()
        self.schedule_daily_auto_close()
        self.schedule_auto_clear_ventas()

    def setup_tabs_for_admin(self):
        self.tabs.addTab(self.tab_menu, "🍔 Menú Burga")
        self.tabs.addTab(self.tab_ventas, "📄 Registro de ventas")
        self.tabs.addTab(self.tab_recaud, "💰 Recaudación")
        self.tabs.addTab(self.tab_cierres, "🗂️ Historial de Cierres")
        self.tabs.addTab(self.tab_reportes, "📊 Reporte de Ventas")

    def setup_tabs_for_cajero(self):
        self.tabs.addTab(self.tab_menu, "🍔 Menú Burga")
        self.tabs.addTab(self.tab_ventas, "📄 Registro de ventas")

# ---------- THEME ----------
    def apply_theme(self):
        """
        Aplica tema global. Ajusta paletas y estilos que se usan en toda la app.
        """
        if self.theme == 'day':
            # Light theme - clear interface
            app_style = """
                QWidget { background: #FFFFF0; color: #111111; font-family: Arial; }
                QTabWidget::pane { border: 0; }
                QHeaderView::section { background: #E0E0E0; }
                QTableWidget { background: white; }
                QPushButton { padding:6px; border-radius:6px; }
            """
        else:
            # Night theme - dark interface
            app_style = """
                QWidget { background: #121212; color: #EDEDED; font-family: Arial; }
                QTabWidget::pane { border: 0; }
                QHeaderView::section { background: #2b2b2b; color: #EDEDED; }
                QTableWidget { background: #1e1e1e; color: #EDEDED; }
                QPushButton { padding:6px; border-radius:6px; }
            """
        QApplication.instance().setStyleSheet(app_style)

        # Ajustar fondo del menú y color del total según el tema
        if hasattr(self, 'scroll_area'):
            container = self.scroll_area.widget()
            if container:
                if self.theme == 'day':
                    container.setStyleSheet("background: #F5F5DC;")
                else:
                    container.setStyleSheet("background: black;")

        if hasattr(self, 'lbl_total'):
            if self.theme == 'day':
                self.lbl_total.setStyleSheet("font-size:16px; font-weight:bold; color: #FF9800;")
            else:
                self.lbl_total.setStyleSheet("font-size:16px; font-weight:bold; color: #FFD54F;")

        # Cambiar texto del botón de tema si existe
        if hasattr(self, 'btn_theme'):
            if self.theme == 'day':
                self.btn_theme.setText("☀️ Modo Día")
            else:
                self.btn_theme.setText("🌙 Modo Noche")

    def on_toggle_theme_clicked(self):
        self.toggle_theme()
        # El texto del botón se actualiza en apply_theme

    def toggle_theme(self):
        self.theme = 'day' if self.theme == 'night' else 'night'
        self.apply_theme()

    def build_menu_tab(self):
        layout = QVBoxLayout(self.tab_menu)
        top_bar = QHBoxLayout()
        # Botón para alternar tema con ícono
        if self.theme == 'night':
            self.btn_theme = QPushButton("🌙 Modo Noche")
        else:
            self.btn_theme = QPushButton("☀️ Modo Día")
        self.btn_theme.setFixedHeight(28)
        self.btn_theme.setStyleSheet("""
            QPushButton {
                font-size:15px;
                border-radius:8px;
                padding:6px;
                border: 2px solid #1976d2;
                background: #fff;
                color: #1976d2;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        self.btn_theme.clicked.connect(self.on_toggle_theme_clicked)
        top_bar.addWidget(self.btn_theme)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        top_sep = QFrame()
        top_sep.setFrameShape(QFrame.HLine)
        layout.addWidget(top_sep)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.scroll_area)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(12)
        # El fondo se ajusta en apply_theme
        self.scroll_area.setWidget(container)

        layout.addSpacing(10)
        cart_title = QLabel("🛒 pedidos")
        cart_title.setStyleSheet("font-size:18px; font-weight:bold;")
        layout.addWidget(cart_title)

        self.table_cart = QTableWidget(0, 6)
        self.table_cart.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio", "Subtotal", "", ""])
        self.table_cart.verticalHeader().setVisible(False)
        self.table_cart.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cart.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cart.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_cart)

        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0.00")
        self.lbl_total.setStyleSheet("font-size:16px; font-weight:bold;")
        bottom.addWidget(self.lbl_total)
        bottom.addStretch()

        btn_efec = QPushButton("📲 Pedido Efectivo")
        btn_efec.setStyleSheet("background:#ff9800; color:#000; font-weight:bold; padding:8px;")
        btn_efec.clicked.connect(lambda: self.confirmar_pedido("Efectivo"))
        bottom.addWidget(btn_efec)

        btn_mp = QPushButton("💳 Pedido MP")
        btn_mp.setStyleSheet("background:#1976d2; color:#fff; font-weight:bold; padding:8px;")
        btn_mp.clicked.connect(lambda: self.confirmar_pedido("MercadoPago"))
        bottom.addWidget(btn_mp)

        btn_cancel = QPushButton("❌ Cancelar pedido")
        btn_cancel.setStyleSheet("background:#d32f2f; color:#fff; font-weight:bold; padding:8px;")
        btn_cancel.clicked.connect(self.cancelar_carrito)
        bottom.addWidget(btn_cancel)

        layout.addLayout(bottom)
    

        self.toggle_theme()
        self.btn_theme.setText("Modo Noche" if self.theme == 'day' else "Modo Día")

    def load_productos_grid(self):
        # Limpiar grid
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        productos = fetch_productos()
        colores = {"burger":"#FFD700","promo":"#FF7043","extra":"#FFA000","bebida":"#212121"}
        textos = {"burger":"🍔","promo":"🎁","extra":"➕","bebida":"🥤"}
        columns = 3; row = col = 0
        for p in productos:
            card = QFrame()
            bg = colores.get(p['categoria'], "#EEEEEE")
            fg = "#FFFFFF" if p['categoria'] == "bebida" else "#000000"
            card.setStyleSheet(f"QFrame{{background:{bg}; color:{fg}; border-radius:12px;}}")
            card.setFixedSize(QSize(320, 200))
            v = QVBoxLayout(card)
            title = QLabel(f"{textos.get(p['categoria'],'')} {p['nombre']}"); title.setStyleSheet("font-size:16px; font-weight:bold;")
            v.addWidget(title)
            desc = QLabel(p.get('descripcion') or ""); desc.setWordWrap(True); v.addWidget(desc)
            price = QLabel(f"${float(p['precio']):.2f}"); price.setStyleSheet("font-weight:bold;"); v.addWidget(price)

            h = QHBoxLayout(); h.addWidget(QLabel("Cantidad:"))
            spin = QSpinBox(); spin.setRange(1, 50); spin.setValue(1); h.addWidget(spin); h.addStretch()
            btn_add = QPushButton("Agregar al carrito"); btn_add.setStyleSheet("background:#263238; color:white; border-radius:8px; padding:6px;")
            btn_add.clicked.connect(lambda _=None, prod=p, sp=spin: self.add_to_cart(prod, sp.value()))
            h.addWidget(btn_add)
            v.addLayout(h)

            self.grid.addWidget(card, row, col)
            col += 1
            if col >= columns:
                col = 0; row += 1

    # --- Carrito ---
    def add_to_cart(self, prod, cantidad):
        if cantidad <= 0:
            return
        pid = prod['id_producto']
        if pid in self.carrito:
            self.carrito[pid]['cantidad'] += cantidad
        else:
            self.carrito[pid] = {'nombre': prod['nombre'], 'precio': float(prod['precio']), 'cantidad': int(cantidad)}
        self.render_cart()

    def render_cart(self):
        self.table_cart.setRowCount(0)
        total = 0.0
        for pid, item in self.carrito.items():
            row = self.table_cart.rowCount(); self.table_cart.insertRow(row)
            self.table_cart.setItem(row, 0, QTableWidgetItem(item['nombre']))
            self.table_cart.setItem(row, 1, QTableWidgetItem(str(item['cantidad'])))
            self.table_cart.setItem(row, 2, QTableWidgetItem(f"${item['precio']:.2f}"))
            subtotal = item['precio'] * item['cantidad']; total += subtotal
            self.table_cart.setItem(row, 3, QTableWidgetItem(f"${subtotal:.2f}"))

            btn_plus = QPushButton("➕"); btn_plus.clicked.connect(lambda _=None, _pid=pid: self.cart_plus(_pid))
            self.table_cart.setCellWidget(row, 4, btn_plus)

            cont = QWidget(); h = QHBoxLayout(cont); h.setContentsMargins(0,0,0,0)
            btn_minus = QPushButton("➖"); btn_minus.clicked.connect(lambda _=None, _pid=pid: self.cart_minus(_pid))
            btn_del = QPushButton("❌"); btn_del.clicked.connect(lambda _=None, _pid=pid: self.cart_delete(_pid))
            h.addWidget(btn_minus); h.addWidget(btn_del)
            self.table_cart.setCellWidget(row, 5, cont)

        self.lbl_total.setText(f"Total: ${total:.2f}")

    def cart_plus(self, pid):
        if pid in self.carrito:
            self.carrito[pid]['cantidad'] += 1; self.render_cart()

    def cart_minus(self, pid):
        if pid in self.carrito:
            self.carrito[pid]['cantidad'] -= 1
            if self.carrito[pid]['cantidad'] <= 0: self.carrito.pop(pid)
            self.render_cart()

    def cart_delete(self, pid):
        if pid in self.carrito:
            self.carrito.pop(pid); self.render_cart()

    def cancelar_carrito(self):
        self.carrito.clear(); self.render_cart()

    # --- Pedido ---
    def confirmar_pedido(self, metodo):
        if not self.carrito:
            QMessageBox.information(self, "Carrito vacío", "Agregá productos antes de confirmar el pedido.")
            return
        dlg = ClienteDialog(metodo, self)
        if dlg.exec_() == QDialog.Accepted:
            ok, msg, id_pedido = insert_pedido_y_detalles(
                dlg.nombre,
                "",  # Teléfono vacío
                dlg.direccion,
                dlg.metodo_pago,
                self.carrito
            )
            if not ok:
                QMessageBox.critical(self, "Error", msg)
                return
            self.cancelar_carrito()
            self.refresh_ventas()
            # Solo refrescar recaudación si el usuario es admin
            if self.user_role != "cajero":
                try:
                    self.refresh_recaudacion()
                except Exception as e:
                    with open('error_log.txt', 'a', encoding='utf-8') as f:
                        f.write(f"[confirmar_pedido] {datetime.now()} - Exception: {e}\n")
                    QMessageBox.warning(self, "Error interno", f"Error inesperado: {e}")
            QMessageBox.information(self, "Pedido realizado", "¡Su pedido se realizó con éxito!")

# ---------- VENTAS TAB ----------
    def build_ventas_tab(self):
        lay = QVBoxLayout(self.tab_ventas)
        title = QLabel("📄 Registro de Ventas")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        lay.addWidget(title)
        lay.addWidget(self._hr())

        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Buscar por cliente:"))
        self.filter_name = QLineEdit()
        self.filter_name.setPlaceholderText("Nombre (dejar vacío para todos)")
        filtro_layout.addWidget(self.filter_name)

        filtro_layout.addWidget(QLabel("Desde:"))
        self.filter_from = QDateEdit()
        self.filter_from.setCalendarPopup(True)
        self.filter_from.setDate(QDate.currentDate().addMonths(-1))
        filtro_layout.addWidget(self.filter_from)

        filtro_layout.addWidget(QLabel("Hasta:"))
        self.filter_to = QDateEdit()
        self.filter_to.setCalendarPopup(True)
        self.filter_to.setDate(QDate.currentDate())
        filtro_layout.addWidget(self.filter_to)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.setStyleSheet("""
            QPushButton {
                border: 2px solid #1976d2;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #1976d2;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        btn_filtrar.clicked.connect(self.refresh_ventas)
        filtro_layout.addWidget(btn_filtrar)

        # Botón Exportar CSV eliminado

        btn_clear_view = QPushButton("Limpiar pantalla")
        btn_clear_view.setStyleSheet("""
            QPushButton {
                border: 2px solid #d32f2f;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #d32f2f;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ffebee;
            }
        """)
        btn_clear_view.clicked.connect(self.clear_ventas_view)
        filtro_layout.addWidget(btn_clear_view)

        btn_manual_close = QPushButton("Cierre manual del día")
        btn_manual_close.setStyleSheet("""
            QPushButton {
                border: 2px solid #ffa000;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #ffa000;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #fff8e1;
            }
        """)
        btn_manual_close.clicked.connect(self.manual_cierre_del_dia)
        filtro_layout.addWidget(btn_manual_close)

        btn_cancelar = QPushButton("Cancelar Pedido")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                border: 2px solid #616161;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #616161;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #eeeeee;
            }
        """)
        btn_cancelar.clicked.connect(self.cancelar_pedido)
        filtro_layout.addWidget(btn_cancelar)

        lay.addLayout(filtro_layout)

        self.table_ventas = QTableWidget(0, 8)
        self.table_ventas.setHorizontalHeaderLabels([
            "ID", "Cliente", "Dirección", "Productos", "Pago", "Total", "📅 Día", "⏰ Hora"
        ])
        self.table_ventas.verticalHeader().setVisible(False)
        self.table_ventas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_ventas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_ventas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_ventas.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.table_ventas)

        btns_row = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualizar Registro de Ventas")
        btn_refresh.clicked.connect(self.refresh_ventas)

        btns_row.addWidget(btn_refresh)
        btns_row.addStretch()
        lay.addLayout(btns_row)

    def clear_ventas_view(self):
        self.table_ventas.setRowCount(0)
        QMessageBox.information(self, "Pantalla limpia", "La vista de ventas fue limpiada (los datos en la base permanecen).")

    def refresh_ventas(self):
        all_data = fetch_ventas()
        nombre_q = self.filter_name.text().strip().lower()
        date_from = self.filter_from.date().toPyDate()
        date_to = self.filter_to.date().toPyDate()

        self.table_ventas.setRowCount(0)
        for v in all_data:
            try:
                dia = v.get('dia')
                if dia:
                    dia_date = dia if isinstance(dia, date) else datetime.strptime(str(dia), "%Y-%m-%d").date()
                else:
                    dia_date = None
            except Exception:
                dia_date = None

            if nombre_q and (not v.get('cliente') or nombre_q not in v.get('cliente', '').lower()):
                continue
            if dia_date:
                if dia_date < date_from or dia_date > date_to:
                    continue

            row = self.table_ventas.rowCount()
            self.table_ventas.insertRow(row)
            self.table_ventas.setItem(row, 0, QTableWidgetItem(str(v.get('id_pedido') or "")))
            self.table_ventas.setItem(row, 1, QTableWidgetItem(v.get('cliente') or ""))
            self.table_ventas.setItem(row, 2, QTableWidgetItem(v.get('direccion') or ""))
            self.table_ventas.setItem(row, 3, QTableWidgetItem(v.get('productos') or ""))
            self.table_ventas.setItem(row, 4, QTableWidgetItem(v.get('metodo_pago') or ""))
            self.table_ventas.setItem(row, 5, QTableWidgetItem(f"${float(v.get('total') or 0):.2f}"))
            self.table_ventas.setItem(row, 6, QTableWidgetItem(str(v.get('dia') or "")))
            self.table_ventas.setItem(row, 7, QTableWidgetItem(str(v.get('hora') or "")))

    def export_ventas_csv(self):
        if self.table_ventas.rowCount() == 0:
            QMessageBox.information(self, "Exportar", "No hay filas para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV ventas", f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = [self.table_ventas.horizontalHeaderItem(i).text() for i in range(self.table_ventas.columnCount())]
                writer.writerow(headers)
                for r in range(self.table_ventas.rowCount()):
                    row = [self.table_ventas.item(r, c).text() if self.table_ventas.item(r, c) else "" for c in range(self.table_ventas.columnCount())]
                    writer.writerow(row)
            QMessageBox.information(self, "Exportar", f"Ventas exportadas correctamente a:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar CSV:\n{e}")

    def cancelar_pedido(self):
        row = self.table_ventas.currentRow()
        if row == -1:
            QMessageBox.information(self, "Cancelar", "Selecciona un pedido para cancelar.")
            return
        id_pedido = self.table_ventas.item(row, 0).text()
        ok = QMessageBox.question(self, "Cancelar pedido", f"¿Seguro que deseas cancelar el pedido {id_pedido}?", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        cn = db_connect()
        if not cn:
            QMessageBox.critical(self, "Error", "No se pudo conectar a la base de datos.")
            return
        try:
            cur = cn.cursor()
            cur.execute("DELETE FROM detalles_pedidos WHERE id_pedido = %s", (id_pedido,))
            cur.execute("DELETE FROM pedidos WHERE id_pedido = %s", (id_pedido,))
            cn.commit()
            self.refresh_ventas()
            QMessageBox.information(self, "Cancelado", f"Pedido {id_pedido} cancelado correctamente.\nAhora puedes cargar un nuevo pedido para el cliente.")
            # Aquí podrías abrir el flujo para crear un nuevo pedido si lo deseas
        except Error as e:
            cn.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo cancelar el pedido:\n{e}")
        finally:
            cn.close()

    def schedule_auto_clear_ventas(self):
        """
        Limpia la vista de la tabla de ventas automáticamente a las 2:00 AM todos los días.
        No borra la base de datos, solo limpia la pantalla.
        """
        now = datetime.now()
        next_2am = datetime.combine(now.date(), time(2, 0))
        if now >= next_2am:
            next_2am += timedelta(days=1)
        delta = (next_2am - now).total_seconds()
        QTimer.singleShot(int(delta * 1000), self.auto_clear_ventas_view)

    def auto_clear_ventas_view(self):
        self.clear_ventas_view()
        # Reprogramar para el siguiente día
        self.schedule_auto_clear_ventas()

    # ---------- RECAUDACIÓN TAB ----------
    def build_recaud_tab(self):
        lay = QVBoxLayout(self.tab_recaud)
        title = QLabel("💰 Recaudación (por método y por día)")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        lay.addWidget(title)
        lay.addWidget(self._hr())

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Desde:"))
        self.rec_from = QDateEdit(); self.rec_from.setCalendarPopup(True); self.rec_from.setDate(QDate.currentDate().addMonths(-1))
        filtros.addWidget(self.rec_from)
        filtros.addWidget(QLabel("Hasta:"))
        self.rec_to = QDateEdit(); self.rec_to.setCalendarPopup(True); self.rec_to.setDate(QDate.currentDate())
        filtros.addWidget(self.rec_to)

        filtros.addWidget(QLabel("Método:"))
        self.rec_metodo = QComboBox(); self.rec_metodo.addItems(["Todos", "Efectivo", "MercadoPago"])
        filtros.addWidget(self.rec_metodo)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.setStyleSheet("""
            QPushButton {
                border: 2px solid #1976d2;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #1976d2;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        btn_filtrar.clicked.connect(self.refresh_recaudacion)
        filtros.addWidget(btn_filtrar)

        # Botones de exportar eliminados

        # Cierre del día manual
        self.btn_cierre = QPushButton("Cierre del Día (manual)")
        self.btn_cierre.setStyleSheet("""
            QPushButton {
                border: 2px solid #d32f2f;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #d32f2f;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ffebee;
            }
        """)
        self.btn_cierre.clicked.connect(self.manual_cierre_del_dia)
        filtros.addWidget(self.btn_cierre)

        lay.addLayout(filtros)

        self.lbl_totales_general = QLabel("Detalle diarios: Efectivo: $0.00 | MP: $0.00 | Total: $0.00")
        lay.addWidget(self.lbl_totales_general)
        lay.addWidget(self._hr())

        # --- NUEVO: QTabWidget para Efectivo y MercadoPago ---
        self.recaud_tabs = QTabWidget()
        # Tab Efectivo
        tab_efectivo = QWidget()
        v_ef = QVBoxLayout(tab_efectivo)
        lbl_e = QLabel("Efectivo"); lbl_e.setStyleSheet("font-size:16px; font-weight:bold; color:#2e7d32;")
        v_ef.addWidget(lbl_e)
        self.table_efectivo = QTableWidget(0, 6)
        self.table_efectivo.setHorizontalHeaderLabels(["ID", "Cliente", "Productos", "Total", "📅 Día", "⏰ Hora"])
        self.table_efectivo.verticalHeader().setVisible(False)
        self.table_efectivo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_efectivo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_efectivo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        v_ef.addWidget(self.table_efectivo)
        self.lbl_totales_ef = QLabel("Totales por día (Efectivo): —  |  Total general: $0.00")
        v_ef.addWidget(self.lbl_totales_ef)
        v_ef.addWidget(self._hr())

        # Tab MercadoPago
        tab_mp = QWidget()
        v_mp = QVBoxLayout(tab_mp)
        lbl_m = QLabel("MercadoPago"); lbl_m.setStyleSheet("font-size:16px; font-weight:bold; color:#1976d2;")
        v_mp.addWidget(lbl_m)
        self.table_mp = QTableWidget(0, 6)
        self.table_mp.setHorizontalHeaderLabels(["ID", "Cliente", "Productos", "Total", "📅 Día", "⏰ Hora"])
        self.table_mp.verticalHeader().setVisible(False)
        self.table_mp.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_mp.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_mp.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        v_mp.addWidget(self.table_mp)
        self.lbl_totales_mp = QLabel("Totales por día (MP): —  |  Total general: $0.00")
        v_mp.addWidget(self.lbl_totales_mp)

        self.recaud_tabs.addTab(tab_efectivo, "Efectivo")
        self.recaud_tabs.addTab(tab_mp, "MercadoPago")
        lay.addWidget(self.recaud_tabs)

        btn_refresh = QPushButton("🔄 Actualizar"); btn_refresh.clicked.connect(self.refresh_recaudacion)
        lay.addWidget(btn_refresh, alignment=Qt.AlignRight)

    def refresh_recaudacion(self):
        metodo_filter = self.rec_metodo.currentText()
        date_from = self.rec_from.date().toPyDate()
        date_to = self.rec_to.date().toPyDate()

        # Datos según método (si "Todos" devolvemos todo y filtramos)
        all_data = fetch_recaudacion_por_metodo("Todos")  # traer todo y filtrar en python para más flexibilidad

        # Totales diarios de la vista (por método)
        tot_por_dia_ef = defaultdict(float)
        tot_por_dia_mp = defaultdict(float)
        tot_gen_ef = 0.0
        tot_gen_mp = 0.0

        # Limpiar tablas
        self.table_efectivo.setRowCount(0)
        self.table_mp.setRowCount(0)

        for r in all_data:
            try:
                dia = r.get('dia')
                dia_date = dia if isinstance(dia, date) else (datetime.strptime(str(dia), "%Y-%m-%d").date() if dia else None)
            except Exception:
                dia_date = None
            if dia_date and (dia_date < date_from or dia_date > date_to):
                continue

            metodo = r.get('metodo_pago') or "Efectivo"
            rowdata = {
                'id_pedido': r.get('id_pedido'),
                'cliente': r.get('cliente') or "",
                'productos': r.get('productos') or "",
                'total': float(r.get('total') or 0),
                'dia': str(r.get('dia') or ""),
                'hora': str(r.get('hora') or "")
            }
            if metodo == "Efectivo":
                row = self.table_efectivo.rowCount(); self.table_efectivo.insertRow(row)
                self.table_efectivo.setItem(row, 0, QTableWidgetItem(str(rowdata['id_pedido'])))
                self.table_efectivo.setItem(row, 1, QTableWidgetItem(rowdata['cliente']))
                self.table_efectivo.setItem(row, 2, QTableWidgetItem(rowdata['productos']))
                self.table_efectivo.setItem(row, 3, QTableWidgetItem(f"${rowdata['total']:.2f}"))
                self.table_efectivo.setItem(row, 4, QTableWidgetItem(rowdata['dia']))
                self.table_efectivo.setItem(row, 5, QTableWidgetItem(rowdata['hora']))
                tot_gen_ef += rowdata['total']
                if rowdata['dia']:
                    tot_por_dia_ef[rowdata['dia']] += rowdata['total']
            else:
                # Consideramos todo lo que no sea "Efectivo" como MP (por simplicidad)
                row = self.table_mp.rowCount(); self.table_mp.insertRow(row)
                self.table_mp.setItem(row, 0, QTableWidgetItem(str(rowdata['id_pedido'])))
                self.table_mp.setItem(row, 1, QTableWidgetItem(rowdata['cliente']))
                self.table_mp.setItem(row, 2, QTableWidgetItem(rowdata['productos']))
                self.table_mp.setItem(row, 3, QTableWidgetItem(f"${rowdata['total']:.2f}"))
                self.table_mp.setItem(row, 4, QTableWidgetItem(rowdata['dia']))
                self.table_mp.setItem(row, 5, QTableWidgetItem(rowdata['hora']))
                tot_gen_mp += rowdata['total']
                if rowdata['dia']:
                    tot_por_dia_mp[rowdata['dia']] += rowdata['total']

        # Resumen y labels
        resumen_ef = "  |  ".join([f"{d}: ${tot_por_dia_ef[d]:.2f}" for d in sorted(tot_por_dia_ef.keys(), reverse=True)]) or "—"
        resumen_mp = "  |  ".join([f"{d}: ${tot_por_dia_mp[d]:.2f}" for d in sorted(tot_por_dia_mp.keys(), reverse=True)]) or "—"
        self.lbl_totales_ef.setText(f"Totales por día (Efectivo): {resumen_ef}  |  Total general: ${tot_gen_ef:.2f}")
        self.lbl_totales_mp.setText(f"Totales por día (MP): {resumen_mp}  |  Total general: ${tot_gen_mp:.2f}")

        # Totales combinados por día (muestra detalle de efectivo y MP y total)
        total_general = tot_gen_ef + tot_gen_mp
        self.lbl_totales_general.setText(f"Detalle diarios: Efectivo: ${tot_gen_ef:.2f} | MP: ${tot_gen_mp:.2f} | Total: ${total_general:.2f}")

        # Si hoy es domingo: mostrar recaudación semanal (jueves->domingo)
        today = date.today()
        if today.weekday() == 6:  # 6 == Sunday
            # Semana: Thursday (3) to Sunday (6)
            semana_inicio = today - timedelta(days=(today.weekday() - 3))  # Thursday
            semana_fin = today  # Sunday
            tot_semana = 0.0
            # sumar todas las ordenes entre semana_inicio y semana_fin
            for r in all_data:
                try:
                    dia = r.get('dia')
                    dia_date = dia if isinstance(dia, date) else (datetime.strptime(str(dia), "%Y-%m-%d").date() if dia else None)
                except Exception:
                    dia_date = None
                if dia_date and semana_inicio <= dia_date <= semana_fin:
                    tot_semana += float(r.get('total') or 0)
            QMessageBox.information(self, "Recaudación Semanal",
                                    f"Total semana (jueves→domingo) del {semana_inicio} al {semana_fin}: ${tot_semana:.2f}")
            # Nota: no se detectan feriados automáticamente; si necesitás lógica de feriados hay que agregar una fuente de feriados.

    def export_recaud_csv(self, metodo):
        # elegir tabla según metodo
        table = self.table_efectivo if metodo == "Efectivo" else self.table_mp
        if table.rowCount() == 0:
            QMessageBox.information(self, "Exportar", f"No hay filas para exportar ({metodo})."); return
        path, _ = QFileDialog.getSaveFileName(self, f"Guardar CSV recaudacion {metodo}", f"recaudacion_{metodo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                writer.writerow(headers)
                for r in range(table.rowCount()):
                    row = [table.item(r, c).text() if table.item(r, c) else "" for c in range(table.columnCount())]
                    writer.writerow(row)
            QMessageBox.information(self, "Exportar", f"Recaudación ({metodo}) exportada a:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar CSV:\n{e}")

    # ---------- Cierres (manual y automático) ----------
    def manual_cierre_del_dia(self):
        """
        Cierra manualmente la recaudación del 'día anterior' o del día seleccionado.
        Para simplificar se cerrará la fecha del día anterior (según horario comercial).
        """
        # Pedimos confirmación
        hoy = date.today()
        fecha_a_cerrar = hoy  # cerramos el día actual por defecto
        # Calculamos totales del día seleccionado (hoy)
        data = fetch_recaudacion_por_metodo("Todos")
        tot_ef = 0.0; tot_mp = 0.0
        for r in data:
            try:
                dia = r.get('dia')
                dia_date = dia if isinstance(dia, date) else (datetime.strptime(str(dia), "%Y-%m-%d").date() if dia else None)
            except Exception:
                dia_date = None
            if dia_date == fecha_a_cerrar:
                if (r.get('metodo_pago') or "Efectivo") == "Efectivo":
                    tot_ef += float(r.get('total') or 0)
                else:
                    tot_mp += float(r.get('total') or 0)
        ok = QMessageBox.question(self, "Confirmar cierre", f"Cerrar recaudación de {fecha_a_cerrar}?\nEfectivo: ${tot_ef:.2f}\nMP: ${tot_mp:.2f}\nTotal: ${tot_ef+tot_mp:.2f}")
        if ok != QMessageBox.Yes:
            return
        success, msg = insert_cierre_fecha(fecha_a_cerrar, tot_ef, tot_mp, cerrado_por="admin_manual")
        if success:
            QMessageBox.information(self, "Cierre", "Cierre guardado correctamente.")
        else:
            QMessageBox.critical(self, "Cierre", f"No se pudo guardar cierre:\n{msg}")

    # ---------- Cierres (manual y automático) ----------
    # Lista de feriados (agrega aquí los feriados que quieras considerar)
    FERIADOS = [
        date(2026, 1, 1),   
        date(2026, 2, 16),  
        date(2026, 2, 17),   
        date(2026, 3, 24),
        date(2026, 4, 2),   
        date(2026, 4, 3),
        date(2026, 5, 1),   
        date(2026, 5, 25),
        date(2026, 6, 20),   
        date(2026, 7, 9),
        date(2026, 12, 8),   
        date(2026, 12, 25),
    ]

    def es_dia_laborable(self, fecha):
        # Jueves (3), Viernes (4), Sábado (5), Domingo (6) o feriado
        return fecha.weekday() in (3, 4, 5, 6) or fecha in self.FERIADOS

    def schedule_daily_auto_close(self):
        """
        Programa un QTimer singleShot para ejecutar close_at_00_30 en el próximo 00:30 AM,
        pero solo si el día anterior fue laborable (jueves, viernes, sábado, domingo o feriado).
        """
        now = datetime.now()
        # Hora objetivo: próximo 00:30 AM
        next_00_30 = datetime.combine(now.date(), time(0, 30))
        if now >= next_00_30:
            next_00_30 = next_00_30 + timedelta(days=1)
        delta_seconds = (next_00_30 - now).total_seconds()

        # singleShot para el próximo 00:30
        QTimer.singleShot(int(delta_seconds * 1000), self.do_daily_close_scheduled)

        # Si ya pasó 00:30 y el último cierre registrado es anterior al día anterior, cerrar ahora
        if now.time() >= time(0, 30):
            dia_anterior = now.date() - timedelta(days=1)
            if self.es_dia_laborable(dia_anterior):
                last = last_cierre_date()
                if (last is None) or (last < dia_anterior):
                    QTimer.singleShot(1000, lambda: self.do_close_for_date(dia_anterior, auto=True))

    def do_daily_close_scheduled(self):
        """
        Evento disparado a las 00:30 AM por schedule_daily_auto_close — cierra el día anterior si corresponde.
        """
        dia_a_cerrar = datetime.now().date() - timedelta(days=1)
        if self.es_dia_laborable(dia_a_cerrar):
            self.do_close_for_date(dia_a_cerrar, auto=True)
        # Reprogramar para el siguiente día 00:30
        self.schedule_daily_auto_close()

    def do_close_for_date(self, fecha, auto=False):
        """
        Calcula totales del día 'fecha' y guarda en cierres_dia si no existe ya.
        auto=True indica cierre automático.
        """
        # Check si ya existe cierre para esa fecha
        last = last_cierre_date()
        if last == fecha:
            # ya cerrado
            return
        data = fetch_recaudacion_por_metodo("Todos")
        tot_ef = 0.0; tot_mp = 0.0
        for r in data:
            try:
                dia = r.get('dia')
                dia_date = dia if isinstance(dia, date) else (datetime.strptime(str(dia), "%Y-%m-%d").date() if dia else None)
            except Exception:
                dia_date = None
            if dia_date == fecha:
                if (r.get('metodo_pago') or "Efectivo") == "Efectivo":
                    tot_ef += float(r.get('total') or 0)
                else:
                    tot_mp += float(r.get('total') or 0)
        cerrado_por = "sistema_auto" if auto else "sistema"
        success, msg = insert_cierre_fecha(fecha, tot_ef, tot_mp, cerrado_por=cerrado_por)
        if success:
            # notificar solo en modo visible si el admin está usando la app
            if auto:
                # notificar en UI de forma no intrusiva
                QMessageBox.information(self, "Cierre automático", f"Cierre automático del {fecha} registrado.\nTotal: ${tot_ef+tot_mp:.2f}")
            else:
                QMessageBox.information(self, "Cierre", f"Cierre del {fecha} registrado.\nTotal: ${tot_ef+tot_mp:.2f}")
        else:
            QMessageBox.critical(self, "Cierre", f"No se pudo guardar cierre:\n{msg}")

# ---------- HISTORIAL CIERRES (NUEVO) ----------
    def build_historial_tab(self):
        lay = QVBoxLayout(self.tab_cierres)
        title = QLabel("🗂️ Historial de Cierres")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        lay.addWidget(title)
        lay.addWidget(self._hr())

        # Filtros de fecha
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Desde:"))
        self.cierre_from = QDateEdit()
        self.cierre_from.setCalendarPopup(True)
        self.cierre_from.setDate(QDate.currentDate().addMonths(-1))
        filtro_layout.addWidget(self.cierre_from)

        filtro_layout.addWidget(QLabel("Hasta:"))
        self.cierre_to = QDateEdit()
        self.cierre_to.setCalendarPopup(True)
        self.cierre_to.setDate(QDate.currentDate())
        filtro_layout.addWidget(self.cierre_to)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.setStyleSheet("""
            QPushButton {
                border: 2px solid #1976d2;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #1976d2;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        btn_filtrar.clicked.connect(self.load_historial_cierres)
        filtro_layout.addWidget(btn_filtrar)

        btn_clear = QPushButton("Limpiar pantalla")
        btn_clear.setStyleSheet("""
            QPushButton {
                border: 2px solid #d32f2f;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #d32f2f;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ffebee;
            }
        """)
        btn_clear.clicked.connect(self.clear_historial_cierres_view)
        filtro_layout.addWidget(btn_clear)

        # Botón de exportar eliminado

        lay.addLayout(filtro_layout)

        # Tabla de cierres con columna DÍAS
        self.table_cierres = QTableWidget(0, 8)
        self.table_cierres.setHorizontalHeaderLabels([
            "ID", "Fecha", "DÍAS", "Total Efectivo", "Total MP", "Total General", "Cerrado por", "Cerrado at"
        ])
        self.table_cierres.verticalHeader().setVisible(False)
        self.table_cierres.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cierres.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cierres.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        lay.addWidget(self.table_cierres)

        # Totales semanales
        self.lbl_totales_semanales = QLabel("Totales semanales: —")
        self.lbl_totales_semanales.setStyleSheet("font-weight:bold; color:#1976d2;")
        lay.addWidget(self.lbl_totales_semanales)

        btns = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_historial_cierres)
        btns.addWidget(btn_refresh)
        btns.addStretch()
        lay.addLayout(btns)

        self.tab_cierres.setLayout(lay)
        self.load_historial_cierres()

    def clear_historial_cierres_view(self):
        self.table_cierres.setRowCount(0)
        self.lbl_totales_semanales.setText("Totales semanales: —")
        QMessageBox.information(self, "Pantalla limpia", "La vista de cierres fue limpiada (los datos en la base permanecen).")

    def load_historial_cierres(self):
        cn = db_connect()
        if not cn:
            return
        try:
            cur = cn.cursor(dictionary=True)
            cur.execute("SELECT id, fecha, total_efectivo, total_mp, total_general, cerrado_por, cerrado_at FROM cierres_dia ORDER BY fecha DESC")
            rows = cur.fetchall()
            cn.close()
        except Error as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar historial de cierres:\n{e}")
            return

        # Filtro por fechas
        date_from = self.cierre_from.date().toPyDate()
        date_to = self.cierre_to.date().toPyDate()
        filtered = [r for r in rows if date_from <= r['fecha'] <= date_to]

        self.table_cierres.setRowCount(0)
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

        # Para totales semanales (solo jueves a domingo)
        semanas = []
        semana_actual = None
        tot_ef, tot_mp, tot_gen = 0.0, 0.0, 0.0

        for r in filtered:
            fecha = r.get('fecha')
            dia_idx = fecha.weekday()
            dia_nombre = dias_semana[dia_idx]
            row = self.table_cierres.rowCount()
            self.table_cierres.insertRow(row)
            self.table_cierres.setItem(row, 0, QTableWidgetItem(str(r.get('id') or "")))
            self.table_cierres.setItem(row, 1, QTableWidgetItem(str(fecha or "")))
            self.table_cierres.setItem(row, 2, QTableWidgetItem(dia_nombre))
            self.table_cierres.setItem(row, 3, QTableWidgetItem(f"${float(r.get('total_efectivo') or 0):.2f}"))
            self.table_cierres.setItem(row, 4, QTableWidgetItem(f"${float(r.get('total_mp') or 0):.2f}"))
            self.table_cierres.setItem(row, 5, QTableWidgetItem(f"${float(r.get('total_general') or 0):.2f}"))
            self.table_cierres.setItem(row, 6, QTableWidgetItem(r.get('cerrado_por') or ""))
            cerrado_at = r.get('cerrado_at')
            self.table_cierres.setItem(row, 7, QTableWidgetItem(str(cerrado_at) if cerrado_at else ""))
            # Acumular totales semanales solo jueves a domingo
            if dia_idx in (3, 4, 5, 6):  # jueves a domingo
                if semana_actual is None or fecha.isocalendar()[1] != semana_actual:
                    if semana_actual is not None:
                        semanas.append((semana_actual, tot_ef, tot_mp, tot_gen))
                    semana_actual = fecha.isocalendar()[1]
                    tot_ef, tot_mp, tot_gen = 0.0, 0.0, 0.0
                tot_ef += float(r.get('total_efectivo') or 0)
                tot_mp += float(r.get('total_mp') or 0)
                tot_gen += float(r.get('total_general') or 0)
        # Agregar la última semana
        if semana_actual is not None:
            semanas.append((semana_actual, tot_ef, tot_mp, tot_gen))

        # Mostrar resumen semanal
        if semanas:
            resumen = []
            for sem, ef, mp, gen in semanas:
                resumen.append(f"Semana {sem}: Efectivo ${ef:.2f} | MP ${mp:.2f} | Total ${gen:.2f}")
            self.lbl_totales_semanales.setText("Totales semanales: " + "   ||   ".join(resumen))
        else:
            self.lbl_totales_semanales.setText("Totales semanales: —")

# ---------- REPORTE DE VENTAS (NUEVO) ----------
    def build_reportes_tab(self):
        lay = QVBoxLayout(self.tab_reportes)
        title = QLabel("📊 Reporte de Ventas por Producto (Diario / Período)")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        lay.addWidget(title)
        lay.addWidget(self._hr())

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Desde:"))
        self.rep_from = QDateEdit(); self.rep_from.setCalendarPopup(True); self.rep_from.setDate(QDate.currentDate().addDays(-7))
        filtros.addWidget(self.rep_from)
        filtros.addWidget(QLabel("Hasta:"))
        self.rep_to = QDateEdit(); self.rep_to.setCalendarPopup(True); self.rep_to.setDate(QDate.currentDate())
        filtros.addWidget(self.rep_to)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.setStyleSheet("""
            QPushButton {
                border: 2px solid #1976d2;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #1976d2;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        btn_filtrar.clicked.connect(self.load_reportes_data)
        filtros.addWidget(btn_filtrar)

        btn_limpiar = QPushButton("Limpiar pantalla")
        btn_limpiar.setStyleSheet("""
            QPushButton {
                border: 2px solid #d32f2f;
                border-radius: 6px;
                padding: 6px 12px;
                background: #fff;
                color: #d32f2f;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ffebee;
            }
        """)
        btn_limpiar.clicked.connect(self.clear_reportes_view)
        filtros.addWidget(btn_limpiar)

        filtros.addStretch()
        lay.addLayout(filtros)

        # Refrescar recaudación solo después de crear todos los widgets necesarios
        self.refresh_recaudacion()

        # Tabla detalle por pedido
        lbl_tabla = QLabel("Ventas por producto y día laboral (jueves a domingo)")
        lbl_tabla.setStyleSheet("font-weight:bold;")
        lay.addWidget(lbl_tabla)
        self.table_reporte = QTableWidget(0, 7)
        self.table_reporte.setHorizontalHeaderLabels(["Fecha", "Producto", "Jueves", "Viernes", "Sábado", "Domingo", "Cantidad"])
        self.table_reporte.verticalHeader().setVisible(False)
        self.table_reporte.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_reporte.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_reporte.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_reporte.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.table_reporte)

        lay.addWidget(self._hr())

        # Resumen global por producto (solo jueves a domingo)
        lbl_resumen = QLabel("Resumen de ventas por producto (jueves a domingo)")
        lbl_resumen.setStyleSheet("font-weight:bold;")
        lay.addWidget(lbl_resumen)
        self.table_resumen = QTableWidget(0, 2)
        self.table_resumen.setHorizontalHeaderLabels(["Producto", "TOTAL SEMANAL"])
        self.table_resumen.verticalHeader().setVisible(False)
        self.table_resumen.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_resumen.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_resumen.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_resumen.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.table_resumen)

        # Total general
        self.lbl_total_general = QLabel("TOTAL GENERAL: 0")
        self.lbl_total_general.setStyleSheet("font-size:16px; font-weight:bold; color:#1976d2;")
        lay.addWidget(self.lbl_total_general)

        self.tab_reportes.setLayout(lay)
        self.load_reportes_data()

    def clear_reportes_view(self):
        self.table_reporte.setRowCount(0)
        self.table_resumen.setRowCount(0)
        self.lbl_total_general.setText("TOTAL GENERAL: 0")
        QMessageBox.information(self, "Pantalla limpia", "La vista de reportes fue limpiada (los datos en la base permanecen).")

    def load_reportes_data(self):
        date_from = self.rep_from.date().toPyDate()
        date_to = self.rep_to.date().toPyDate()

        cn = db_connect()
        if not cn:
            return
        try:
            cur = cn.cursor(dictionary=True)
            cur.execute("""
                SELECT DATE(p.fecha) AS dia, pr.nombre AS producto, SUM(d.cantidad) AS cantidad
                FROM detalles_pedidos d
                JOIN pedidos p ON p.id_pedido = d.id_pedido
                JOIN productos pr ON pr.id_producto = d.id_producto
                WHERE DATE(p.fecha) BETWEEN %s AND %s
                GROUP BY dia, producto
                ORDER BY dia ASC, producto ASC
            """, (date_from, date_to))
            detalle = cur.fetchall()

            # --- Tabla detalle por pedido ---
            tabla_dict = {}
            for r in detalle:
                fecha = r.get('dia')
                producto = r.get('producto') or ""
                dia_idx = fecha.weekday() if isinstance(fecha, date) else datetime.strptime(str(fecha), "%Y-%m-%d").weekday()
                if dia_idx in (3, 4, 5, 6):  # jueves a domingo
                    if (fecha, producto) not in tabla_dict:
                        tabla_dict[(fecha, producto)] = [0, 0, 0, 0]  # jueves, viernes, sabado, domingo
                    tabla_dict[(fecha, producto)][dia_idx - 3] += int(r.get('cantidad') or 0)

            self.table_reporte.setRowCount(0)
            for (fecha, producto), cantidades in sorted(tabla_dict.items()):
                total = sum(cantidades)
                row = self.table_reporte.rowCount()
                self.table_reporte.insertRow(row)
                self.table_reporte.setItem(row, 0, QTableWidgetItem(str(fecha or "")))
                self.table_reporte.setItem(row, 1, QTableWidgetItem(producto))
                self.table_reporte.setItem(row, 2, QTableWidgetItem(str(cantidades[0])))  # Jueves
                self.table_reporte.setItem(row, 3, QTableWidgetItem(str(cantidades[1])))  # Viernes
                self.table_reporte.setItem(row, 4, QTableWidgetItem(str(cantidades[2])))  # Sábado
                self.table_reporte.setItem(row, 5, QTableWidgetItem(str(cantidades[3])))  # Domingo
                self.table_reporte.setItem(row, 6, QTableWidgetItem(str(total)))

            # --- Resumen global por producto ---
            resumen_dict = {}
            for (fecha, producto), cantidades in tabla_dict.items():
                if producto not in resumen_dict:
                    resumen_dict[producto] = 0
                resumen_dict[producto] += sum(cantidades)

            self.table_resumen.setRowCount(0)
            total_general = 0
            for producto, total in sorted(resumen_dict.items()):
                row = self.table_resumen.rowCount()
                self.table_resumen.insertRow(row)
                self.table_resumen.setItem(row, 0, QTableWidgetItem(producto))
                self.table_resumen.setItem(row, 1, QTableWidgetItem(str(total)))
                total_general += total

            self.lbl_total_general.setText(f"TOTAL GENERAL: {total_general}")

            cn.close()
        except Error as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{e}")
            cn.close()

    # ---------- Utilities ----------
    def _hr(self):
        hr = QFrame(); hr.setFrameShape(QFrame.HLine); hr.setStyleSheet("color:#bbb;"); return hr

# ---------------- bootstrap ----------------
def main():
    app = QApplication(sys.argv)
    login = LoginDialog()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)
    win = MainWindow(user_role=getattr(login, "user_role", "admin"))
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        # Loguear error y traceback completo
        with open('error_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"[FATAL] {datetime.now()} - Exception: {e}\n")
            f.write(traceback.format_exc())
        print(f"[FATAL] {datetime.now()} - Exception: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        # También escribir en arranque_log.txt para máxima visibilidad
        with open('arranque_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"[FATAL] {datetime.now()} - Exception: {e}\n")
        sys.exit(1)

