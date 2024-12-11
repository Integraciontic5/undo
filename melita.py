class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("interfaz.ui", self)

        print("Interfaz cargada correctamente.")
        self.socket = None
        self.monitoring = False
        self.esp32_connection = None
        self.initUI()

        # Renombrar botones
        self.rename_buttons()

        # Inicializa la base de datos
        inicializar_db()

        # Crea el hilo para el servidor
        self.server_thread = ServerThread()
        self.server_thread.new_data_signal.connect(self.update_graph_and_data)
        self.server_thread.start()

    def initUI(self):
        # Crear el PlotWidget dinámicamente
        self.graphWidget = PlotWidget(self.centralwidget)
        self.graphWidget.setObjectName("plotWidget")
        self.graphWidget.setGeometry(100, 100, 400, 300)  # Ajusta según el diseño
        self.graphWidget.setTitle("Temperatura y Humedad")
        self.graphWidget.setBackground("w")
        self.graphWidget.addLegend()

        # Configurar gráficos
        self.temp_plot = self.graphWidget.plot(pen="r", name="Temperatura (C)")
        self.hum_plot = self.graphWidget.plot(pen="b", name="Humedad (%)")

        # Variables para almacenar datos
        self.temp_data = []
        self.hum_data = []

        # Configurar el temporizador para actualizar los datos
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)

        # Conectar los botones a sus funciones
        self.pushButton.clicked.connect(self.start_monitoring)
        self.pushButton_2.clicked.connect(self.stop_monitoring)
        self.pushButton_4.clicked.connect(self.send_start_command)
        self.pushButton.setText("Stop")
        self.pushButton_4.setText("Start")

    def rename_buttons(self):
        # Cambiar los nombres de los botones
        self.pushButton.setObjectName("btnStop")
        self.pushButton_2.setObjectName("btnMode1")
        self.pushButton_3.setObjectName("btnMode2")
        self.pushButton_4.setObjectName("btnStart")

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
        self.send_stop_command()

    def update_graph(self):
        # Actualiza el gráfico
        self.temp_plot.setData(self.temp_data)
        self.hum_plot.setData(self.hum_data)

    def update_graph_and_data(self, data):
        # Parsear los datos recibidos
        try:
            # Eliminar etiquetas y unidades
            parsed_data = data.replace("Temperatura:", "").replace("Humedad:", "")
            parsed_data = parsed_data.replace("Â°C", "").replace("%", "")
            temp, hum = map(float, parsed_data.split(","))

            # Añadir los nuevos datos al gráfico
            self.temp_data.append(temp)
            self.hum_data.append(hum)

            # Limitar la cantidad de datos mostrados
            if len(self.temp_data) > 100:
                self.temp_data.pop(0)
                self.hum_data.pop(0)

            # Actualizar los gráficos
            self.update_graph()

            # Actualizar los QLCDNumber con los nuevos valores
            self.lcdTempMax.display(temp)  # Suponiendo que tienes un QLCDNumber llamado lcdTempMax
            self.lcdTempMin.display(temp)  # Suponiendo que tienes un QLCDNumber llamado lcdTempMin
            self.lcdHumMax.display(hum)   # Lo mismo para humedad
            self.lcdHumMin.display(hum)

        except ValueError:
            print("Error al parsear los datos:", data)

    def send_start_command(self):
        # Enviar comando de inicio a la ESP32
        self.send_command_to_esp32("START")

    def send_stop_command(self):
        # Enviar comando de parada a la ESP32
        self.send_command_to_esp32("STOP")

    def send_command_to_esp32(self, command):
        if self.esp32_connection:
            try:
                self.esp32_connection.sendall(command.encode('utf-8'))
                print(f"Comando enviado a la ESP32: {command}")
            except Exception as e:
                print(f"Error al enviar el comando a la ESP32: {e}")
        else:
            print("No hay conexión con la ESP32 para enviar comandos.")
