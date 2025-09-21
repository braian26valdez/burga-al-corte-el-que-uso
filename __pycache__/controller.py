
from modelo import db_connect
from mysql.connector import Error
from PyQt5.QtWidgets import QMessageBox

ADMIN_CREDENTIALS = {
	"braian": "proburga",
	"jose luis": "proburga",
	"cajero": ""  # El usuario 'cajero' no requiere contraseña
}



def ensure_cierres_table():
	"""
	Crea tabla 'cierres_dia' si no existe. No borra nada.
	"""
	cn = db_connect()
	if not cn:
		return False
	try:
		cur = cn.cursor()
		cur.execute("""
			CREATE TABLE IF NOT EXISTS cierres_dia (
				id INT AUTO_INCREMENT PRIMARY KEY,
				fecha DATE NOT NULL,
				total_efectivo DECIMAL(12,2) DEFAULT 0,
				total_mp DECIMAL(12,2) DEFAULT 0,
				total_general DECIMAL(12,2) DEFAULT 0,
				cerrado_por VARCHAR(100),
				cerrado_at DATETIME DEFAULT CURRENT_TIMESTAMP
			)
		""")
		cn.commit()
		return True
	except Error as e:
		QMessageBox.critical(None, "Error DB", f"No se pudo crear/checkear tabla cierres_dia:\n{e}")
		return False
	finally:
		cn.close()

def fetch_productos():
	cn = db_connect()
	if not cn: return []
	try:
		cur = cn.cursor(dictionary=True)
		cur.execute("SELECT id_producto, nombre, descripcion, precio, categoria FROM productos ORDER BY id_producto")
		return cur.fetchall()
	except Error as e:
		QMessageBox.critical(None, "Error", f"No se pudieron obtener los productos:\n{e}")
		return []
	finally:
		cn.close()

def insert_pedido_y_detalles(nombre_cliente, telefono, direccion, metodo_pago, carrito):
	"""
	Inserta usuario, pedido y detalles. 
	Ya no valida ni actualiza stock.
	"""
	if not carrito:
		return (False, "El carrito está vacío.", None)

	cn = db_connect()
	if not cn:
		return (False, "No hay conexión a DB.", None)

	try:
		# Cursor principal para inserts/updates
		cur = cn.cursor()
		# Insert usuario (guardamos teléfono si lo hay)
		cur.execute(
			"INSERT INTO usuarios (nombre, telefono, direccion, email, tipo) VALUES (%s,%s,%s,%s,'cliente')",
			(nombre_cliente, telefono or None, direccion, None)
		)
		id_usuario = cur.lastrowid

		total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

		# Insert pedido
		cur.execute(
			"INSERT INTO pedidos (id_usuario, metodo_pago, total) VALUES (%s,%s,%s)",
			(id_usuario, metodo_pago, total)
		)
		id_pedido = cur.lastrowid

		# Insertar detalles de pedido (sin controlar stock)
		for pid, item in carrito.items():
			subtotal = item['precio'] * item['cantidad']
			cur.execute(
				"INSERT INTO detalles_pedidos (id_pedido, id_producto, cantidad, precio_unitario, subtotal) "
				"VALUES (%s,%s,%s,%s,%s)",
				(id_pedido, pid, item['cantidad'], item['precio'], subtotal)
			)

		cn.commit()
		return (True, "Pedido guardado correctamente.", id_pedido)

	except Error as e:
		cn.rollback()
		return (False, f"Error guardando pedido: {e}", None)
	finally:
		cn.close()

def fetch_ventas():
	cn = db_connect()
	if not cn: return []
	try:
		cur = cn.cursor(dictionary=True)
		cur.execute("""
			SELECT 
				p.id_pedido,
				u.nombre AS cliente,
				u.direccion,
				GROUP_CONCAT(CONCAT(pr.nombre, ' x', d.cantidad) SEPARATOR ', ') AS productos,
				p.metodo_pago,
				p.total,
				p.fecha,
				DATE(p.fecha) AS dia,
				TIME(p.fecha) AS hora
			FROM pedidos p
			JOIN usuarios u ON u.id_usuario = p.id_usuario
			JOIN detalles_pedidos d ON d.id_pedido = p.id_pedido
			JOIN productos pr ON pr.id_producto = d.id_producto
			GROUP BY p.id_pedido
			ORDER BY p.fecha DESC
		""")
		return cur.fetchall()
	except Error as e:
		QMessageBox.critical(None, "Error", f"No se pudieron obtener las ventas:\n{e}")
		return []
	finally:
		cn.close()

def fetch_recaudacion_por_metodo(metodo):
	# Si metodo == "Todos", devolvemos todo y luego filtramos
	cn = db_connect()
	if not cn: return []
	try:
		cur = cn.cursor(dictionary=True)
		if metodo == "Todos":
			cur.execute("""
				SELECT 
					p.id_pedido,
					u.nombre AS cliente,
					GROUP_CONCAT(CONCAT(pr.nombre, ' x', d.cantidad) SEPARATOR ', ') AS productos,
					p.total,
					p.fecha,
					DATE(p.fecha) AS dia,
					TIME(p.fecha) AS hora,
					p.metodo_pago
				FROM pedidos p
				JOIN usuarios u ON u.id_usuario = p.id_usuario
				JOIN detalles_pedidos d ON d.id_pedido = p.id_pedido
				JOIN productos pr ON pr.id_producto = d.id_producto
				GROUP BY p.id_pedido
				ORDER BY p.fecha DESC
			""")
			return cur.fetchall()
		else:
			cur.execute("""
				SELECT 
					p.id_pedido,
					u.nombre AS cliente,
					GROUP_CONCAT(CONCAT(pr.nombre, ' x', d.cantidad) SEPARATOR ', ') AS productos,
					p.total,
					p.fecha,
					DATE(p.fecha) AS dia,
					TIME(p.fecha) AS hora,
					p.metodo_pago
				FROM pedidos p
				JOIN usuarios u ON u.id_usuario = p.id_usuario
				JOIN detalles_pedidos d ON d.id_pedido = p.id_pedido
				JOIN productos pr ON pr.id_producto = d.id_producto
				WHERE p.metodo_pago = %s
				GROUP BY p.id_pedido
				ORDER BY p.fecha DESC
			""", (metodo,))
			return cur.fetchall()
	except Error as e:
		QMessageBox.critical(None, "Error", f"No se pudo obtener recaudación ({metodo}):\n{e}")
		return []
	finally:
		cn.close()

def insert_cierre_fecha(fecha, total_ef, total_mp, cerrado_por="sistema"):
	"""
	Inserta un registro en cierres_dia para marcar cierre.
	"""
	cn = db_connect()
	if not cn:
		return (False, "No hay conexión a DB.")
	try:
		cur = cn.cursor()
		cur.execute("""
			INSERT INTO cierres_dia (fecha, total_efectivo, total_mp, total_general, cerrado_por)
			VALUES (%s, %s, %s, %s, %s)
		""", (fecha, total_ef, total_mp, total_ef + total_mp, cerrado_por))
		cn.commit()
		return (True, "Cierre guardado.")
	except Error as e:
		cn.rollback()
		return (False, f"Error insertando cierre: {e}")
	finally:
		cn.close()

def last_cierre_date():
	"""
	Retorna la última fecha registrada en cierres_dia (DATE) o None.
	"""
	cn = db_connect()
	if not cn: return None
	try:
		cur = cn.cursor()
		cur.execute("SELECT MAX(fecha) FROM cierres_dia")
		r = cur.fetchone()
		if r and r[0]:
			return r[0]
		return None
	except Error:
		return None
	finally:
		cn.close()
