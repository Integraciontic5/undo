import socket
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import sys
from PyQt5.uic import loadUi
from pyqtgraph import PlotWidget
import pyqtgraph as pg

ESP32_HOST = "0.0.0.0"  # Cambia esto por la IP del ESP32
ESP32_PORT = 1234        # Puerto usado por el ESP32
db_filename = "datos_sensores.db"

# Función para inicializar la base de datos
def inicializar_db():
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            datos TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Función para guardar los datos en la base de datos
def guardar_datos(datos):
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sensores (timestamp, datos) 
        VALUES (?, ?)
    ''', (datetime.now().isoformat(), datos))
    conn.commit()
    conn.close()

class ServerThread(QThread):
    new_data_signal = pyqtSignal(str)

    def run(self):
        # Configuración del servidor TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((ESP32_HOST, ESP32_PORT))
            s.listen()
            print("El servidor está esperando conexiones en el puerto", ESP32_PORT)

            conn, addr = s.accept()  # Acepta una conexión
            with conn:
                print('Conectado por', addr)
                while True:
                    data = conn.recv(1024)  # Recibe hasta 1024 bytes del cliente
                    if not data:
                        break  # Sale del bucle si no hay datos (conexión cerrada)
                    mensaje = data.decode('utf-8')
                    print("Datos recibidos:", mensaje)  # Muestra el mensaje recibido

                    # Intenta guardar el mensaje recibido en la base de datos
                    try:
                        guardar_datos(mensaje)  # Guarda los datos en la base de datos SQLite
                    except Exception as e:
                        print("Error al guardar los datos en la base de datos:", e)

                    # Emitir los datos para actualizar la interfaz
                    self.new_data_signal.emit(mensaje)

                    # Enviar una respuesta de confirmación al ESP32
                    respuesta = "ACK"
                    conn.sendall(respuesta.encode('utf-8'))


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("interfaz.ui", self)
        
        print("Interfaz cargada correctamente.")
        self.socket = None
        self.monitoring = False
        self.initUI()

        # Inicializa la base de datos
        inicializar_db()

        # Crea el hilo para el servidor
        self.server_thread = ServerThread()
        self.server_thread.new_data_signal.connect(self.update_graph_and_data)
        self.server_thread.start()

    def initUI(self):
        # Conecta los botones a sus funciones
        self.pushButton.clicked.connect(self.start_monitoring)
        self.pushButton_2.clicked.connect(self.stop_monitoring)

        # Configurar el gráfico
        self.graphWidget = self.centralwidget.findChild(PlotWidget, "plotWidget")
        self.graphWidget.setTitle("Temperatura y Humedad")
        self.graphWidget.setBackground("w")
        self.graphWidget.addLegend()
        self.temp_plot = self.graphWidget.plot(pen="r", name="Temperatura (C)")
        self.hum_plot = self.graphWidget.plot(pen="b", name="Humedad (%)")

        # Variables para almacenar datos
        self.temp_data = []
        self.hum_data = []

        # Configurar el temporizador para actualizar los datos
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)

    def start_monitoring(self):
        # Inicia el monitoreo
        if not self.monitoring:
            self.monitoring = True
            self.timer.start(1000)  # Actualiza cada segundo

    def stop_monitoring(self):
        # Detiene el monitoreo
        if self.monitoring:
            self.monitoring = False
            self.timer.stop()

    def update_graph(self):
        # Actualiza el gráfico
        self.temp_plot.setData(self.temp_data)
        self.hum_plot.setData(self.hum_data)

    def update_graph_and_data(self, data):
        # Parsear los datos recibidos
        try:
            temp, hum = map(float, data.split(","))
            self.temp_data.append(temp)
            self.hum_data.append(hum)

            # Limitar la cantidad de datos mostrados
            if len(self.temp_data) > 100:
                self.temp_data.pop(0)
                self.hum_data.pop(0)

            # Actualizar el gráfico
            self.update_graph()
        except ValueError:
            print("Error al parsear los datos:", data)


# Inicializa la aplicación
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
