# -*- coding: utf-8 -*-
"""
INTERFAZ DE MONITOREO APIARIO - UBV v7.5
Autor: TSU Jose R. Flores A.
"""

import sys
import traceback

def mostrar_error_fatal(error):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error Fatal", f"La aplicacion no pudo iniciar:\n\n{error}")
    root.destroy()

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    import serial
    import serial.tools.list_ports
    import json
    import threading
    import psycopg2
    from datetime import datetime
    from collections import deque
    import os
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
except ImportError as e:
    mostrar_error_fatal(f"Falta instalar una libreria:\n\n{e}\n\nEjecuta en CMD:\npip install {str(e).split()[-1]}")
    sys.exit(1)
except Exception as e:
    mostrar_error_fatal(f"Error al importar librerias:\n\n{e}")
    sys.exit(1)

# ============================================
# CONFIGURACION
# ============================================
BAUDRATE = 115200

DB_CONFIG = {
    'host': 'localhost',
    'database': 'apiario_db',
    'user': 'postgres',
    'password': 'postgres',
    'port': '5432'
}

TEMP_MIN, TEMP_MAX = 34.0, 35.0
HUM_MIN, HUM_MAX = 45.0, 65.0
PRES_MIN, PRES_MAX = 1005.0, 1025.0
LLUVIA_MIN, LLUVIA_MAX = 30.0, 70.0
EXCESO_UMBRAL = 80.0

LOGO_PATH = r'C:\Users\JOSE FLORES\Music\OneDrive\Desktop\logo_ubv.png'
LOGO_SIZE = (60, 60)

COLOR_FONDO = '#0f1419'
COLOR_CARD = '#1a2332'
COLOR_BORDE = '#2d3e50'
COLOR_TEXTO_PRIMARIO = '#e8eaed'
COLOR_TEXTO_SECUNDARIO = '#9aa0a6'
COLOR_DORADO = '#f4b400'
COLOR_AZUL = '#4285f4'
COLOR_VERDE = '#34a853'
COLOR_ROJO = '#ea4335'
COLOR_NARANJA = '#fbbc04'
COLOR_GRIS = '#5f6368'
COLOR_CYAN = '#00bcd4'

MAX_PUNTOS_GRAFICA = 50

# ============================================
# CLASE PRINCIPAL
# ============================================
class MonitorApiario:
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("Sistema de Monitoreo Apiario - UBV 2026")
            self.root.geometry("1600x900")
            self.root.configure(bg=COLOR_FONDO)
            self.root.minsize(1200, 700)
            
            self.ser = None
            self.running = False
            self.hilo_serial = None
            self.datos_recientes = deque(maxlen=50)
            self.datos_por_nodo = {}
            self.max_nodos = 5
            self.logo_photo = None
            
            self.historial_temp = deque(maxlen=MAX_PUNTOS_GRAFICA)
            self.historial_hum = deque(maxlen=MAX_PUNTOS_GRAFICA)
            self.historial_pres = deque(maxlen=MAX_PUNTOS_GRAFICA)
            self.historial_lluvia = deque(maxlen=MAX_PUNTOS_GRAFICA)
            
            self.logo_image = self.cargar_logo()
            self.crear_interfaz()
            
        except Exception as e:
            messagebox.showerror("Error de Inicializacion", f"Error al crear la interfaz:\n\n{str(e)}")
            traceback.print_exc()
            raise
        
    def cargar_logo(self):
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH)
                img = img.resize(LOGO_SIZE, Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(img)
                return self.logo_photo
            except Exception as e:
                print(f"Error cargando logo: {e}")
        
        img = Image.new('RGBA', LOGO_SIZE, (244, 180, 0, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            draw.text((30, 30), "UBV", fill=(26, 35, 50, 255), anchor="mm", font=font)
        except:
            draw.text((20, 25), "UBV", fill=(26, 35, 50, 255))
        
        self.logo_photo = ImageTk.PhotoImage(img)
        return self.logo_photo

    def crear_interfaz(self):
        # HEADER
        header = tk.Frame(self.root, bg=COLOR_CARD, height=70, bd=0, relief='flat')
        header.pack(fill='x', padx=0, pady=0)
        header.pack_propagate(False)
        
        header_left = tk.Frame(header, bg=COLOR_CARD)
        header_left.pack(side='left', padx=20, fill='y')
        
        if self.logo_image:
            logo_label = tk.Label(header_left, image=self.logo_image, bg=COLOR_CARD)
            logo_label.image = self.logo_image
            logo_label.pack(side='left', padx=(0, 15))
        
        titulo_container = tk.Frame(header_left, bg=COLOR_CARD)
        titulo_container.pack(side='left', fill='y')
        
        tk.Label(titulo_container, text="SISTEMA DE MONITOREO APIARIO",
                font=('Segoe UI', 16, 'bold'), fg=COLOR_DORADO, bg=COLOR_CARD, anchor='w').pack(fill='x')
        tk.Label(titulo_container, text="Universidad Bolivariana de Venezuela | PFG Informatica Para la Gestión Social",
                font=('Segoe UI', 9), fg=COLOR_TEXTO_SECUNDARIO, bg=COLOR_CARD, anchor='w').pack(fill='x')
        
        header_right = tk.Frame(header, bg=COLOR_CARD)
        header_right.pack(side='right', padx=20, fill='y')
        
        self.lbl_estado = tk.Label(header_right, text="● DESCONECTADO",
                                   font=('Segoe UI', 11, 'bold'), fg=COLOR_ROJO, bg=COLOR_FONDO,
                                   padx=20, pady=8)
        self.lbl_estado.pack(side='right')
        
        self.lbl_hora = tk.Label(header_right, text="--:--:--",
                                font=('Segoe UI', 10), fg=COLOR_TEXTO_SECUNDARIO, bg=COLOR_CARD)
        self.lbl_hora.pack(side='right', padx=(0, 15))
        
        # CONTENEDOR PRINCIPAL
        main_container = tk.Frame(self.root, bg=COLOR_FONDO)
        main_container.pack(fill='both', expand=True, padx=15, pady=10)
        
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=3)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        
        # PANEL IZQUIERDO: 4 Cards
        left_panel = tk.Frame(main_container, bg=COLOR_FONDO)
        left_panel.grid(row=0, column=0, rowspan=2, sticky='nsew', padx=(0, 10))
        
        section_title = tk.Label(left_panel, text="PARAMETROS EN TIEMPO REAL",
                                font=('Segoe UI', 11, 'bold'), fg=COLOR_TEXTO_PRIMARIO, 
                                bg=COLOR_FONDO, anchor='w')
        section_title.pack(fill='x', pady=(0, 5))
        
        self.card_temp = self.crear_card_parametro(left_panel, "TEMPERATURA", "°C", COLOR_ROJO, TEMP_MIN, TEMP_MAX)
        self.card_temp['card'].pack(fill='both', expand=True, pady=4)
        
        self.card_hum = self.crear_card_parametro(left_panel, "HUMEDAD", "%", COLOR_AZUL, HUM_MIN, HUM_MAX)
        self.card_hum['card'].pack(fill='both', expand=True, pady=4)
        
        self.card_pres = self.crear_card_parametro(left_panel, "PRESION", "hPa", COLOR_VERDE, PRES_MIN, PRES_MAX)
        self.card_pres['card'].pack(fill='both', expand=True, pady=4)
        
        self.card_lluvia = self.crear_card_parametro(left_panel, "LLUVIA", "mm", COLOR_CYAN, LLUVIA_MIN, LLUVIA_MAX)
        self.card_lluvia['card'].pack(fill='both', expand=True, pady=4)
        
        # PANEL DERECHO SUPERIOR: Graficas CON SEPARADORES
        right_top = tk.Frame(main_container, bg=COLOR_FONDO)
        right_top.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        
        graficas_title = tk.Label(right_top, text="GRAFICAS EN TIEMPO REAL",
                                 font=('Segoe UI', 11, 'bold'), fg=COLOR_TEXTO_PRIMARIO,
                                 bg=COLOR_FONDO, anchor='w')
        graficas_title.pack(fill='x', pady=(0, 5))
        
        graficas_card = tk.Frame(right_top, bg=COLOR_CARD, bd=1, relief='flat')
        graficas_card.pack(fill='both', expand=True)
        
        self.fig_realtime = Figure(figsize=(8, 5), facecolor=COLOR_CARD, dpi=100)
        self.fig_realtime.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.08, hspace=0.5)
        
        self.ax_temp = self.fig_realtime.add_subplot(411)
        self.ax_hum = self.fig_realtime.add_subplot(412)
        self.ax_pres = self.fig_realtime.add_subplot(413)
        self.ax_lluvia = self.fig_realtime.add_subplot(414)
        
        self.lines = {}
        
        # Configuración de cada gráfica con separadores visuales
        configuraciones = [
            (self.ax_temp, COLOR_ROJO, 'Temp', 25, 45, TEMP_MIN, TEMP_MAX, '°C'),
            (self.ax_hum, COLOR_AZUL, 'Hum', 20, 90, HUM_MIN, HUM_MAX, '%'),
            (self.ax_pres, COLOR_VERDE, 'Pres', 990, 1040, PRES_MIN, PRES_MAX, 'hPa'),
            (self.ax_lluvia, COLOR_CYAN, 'Lluvia', 0, 120, LLUVIA_MIN, LLUVIA_MAX, 'mm')
        ]
        
        for idx, (ax, color, label, ymin, ymax, min_val, max_val, unidad) in enumerate(configuraciones):
            ax.set_facecolor(COLOR_CARD)
            ax.set_ylabel(f"{label} ({unidad})", color=COLOR_TEXTO_SECUNDARIO, fontsize=8, fontweight='bold')
            ax.tick_params(colors=COLOR_TEXTO_SECUNDARIO, labelsize=7)
            ax.set_ylim(ymin, ymax)
            ax.grid(True, alpha=0.2, color=COLOR_TEXTO_SECUNDARIO, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(COLOR_BORDE)
            ax.spines['bottom'].set_color(COLOR_BORDE)
            
            line, = ax.plot([], [], color=color, linewidth=2, marker='o', markersize=3, markerfacecolor=color)
            ax.axhline(y=min_val, color=COLOR_VERDE, linestyle='--', alpha=0.6, linewidth=1)
            ax.axhline(y=max_val, color=COLOR_ROJO, linestyle='--', alpha=0.6, linewidth=1)
            
            # SEPARADOR VISUAL entre gráficas
            if idx < len(configuraciones) - 1:
                ax.axhline(y=ymin - (ymax-ymin)*0.05, color=COLOR_BORDE, linestyle='-', linewidth=2, alpha=0.8)
            
            self.lines[label] = line
        
        self.canvas_realtime = FigureCanvasTkAgg(self.fig_realtime, master=graficas_card)
        self.canvas_realtime.get_tk_widget().pack(fill='both', expand=True)
        
        # PANEL DERECHO INFERIOR: Nodos y Controles
        right_bottom = tk.Frame(main_container, bg=COLOR_FONDO)
        right_bottom.grid(row=1, column=1, sticky='nsew', padx=(10, 0), pady=(10, 0))
        
        nodos_card = tk.Frame(right_bottom, bg=COLOR_CARD, bd=1, relief='flat')
        nodos_card.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        nodos_title = tk.Label(nodos_card, text="NODOS ACTIVOS",
                              font=('Segoe UI', 10, 'bold'), fg=COLOR_TEXTO_PRIMARIO,
                              bg=COLOR_CARD, anchor='w')
        nodos_title.pack(fill='x', padx=10, pady=(5, 5))
        
        columnas = ('Nodo', 'Temp', 'Hum', 'Pres', 'Lluvia', 'Estado')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.Treeview', 
                       background=COLOR_CARD,
                       foreground=COLOR_TEXTO_PRIMARIO,
                       fieldbackground=COLOR_CARD,
                       borderwidth=0,
                       font=('Segoe UI', 9))
        style.configure('Custom.Treeview.Heading',
                       background=COLOR_FONDO,
                       foreground=COLOR_DORADO,
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0)
        style.map('Custom.Treeview', background=[('selected', COLOR_AZUL)])
        
        self.tree_nodos = ttk.Treeview(nodos_card, columns=columnas, 
                                        show='headings', height=6, style='Custom.Treeview')
        
        for col, width in zip(columnas, [70, 70, 70, 80, 70, 80]):
            self.tree_nodos.heading(col, text=col)
            self.tree_nodos.column(col, width=width, anchor='center')
        
        self.tree_nodos.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # CONTROLES
        controles_card = tk.Frame(right_bottom, bg=COLOR_CARD, bd=1, relief='flat')
        controles_card.pack(side='right', fill='y', padx=(10, 0))
        
        controles_title = tk.Label(controles_card, text="CONTROLES",
                                  font=('Segoe UI', 10, 'bold'), fg=COLOR_TEXTO_PRIMARIO,
                                  bg=COLOR_CARD, anchor='w')
        controles_title.pack(fill='x', padx=15, pady=(10, 10))
        
        self.btn_conectar = tk.Button(controles_card, text="▶ Conectar",
                                      command=self.conectar_serial,
                                      font=('Segoe UI', 10, 'bold'), bg=COLOR_VERDE, fg='white',
                                      width=16, height=2, bd=0, relief='flat',
                                      activebackground=COLOR_VERDE, activeforeground='white',
                                      cursor='hand2')
        self.btn_conectar.pack(pady=5, padx=15, fill='x')
        
        self.btn_desconectar = tk.Button(controles_card, text="⏹ Desconectar",
                                         command=self.desconectar_serial,
                                         font=('Segoe UI', 10, 'bold'), bg=COLOR_ROJO, fg='white',
                                         width=16, height=2, bd=0, relief='flat',
                                         activebackground=COLOR_ROJO, activeforeground='white',
                                         cursor='hand2', state='disabled')
        self.btn_desconectar.pack(pady=5, padx=15, fill='x')
        
        self.btn_estadisticas = tk.Button(controles_card, text="📊 Estadisticas",
                                          command=self.ver_estadisticas,
                                          font=('Segoe UI', 10, 'bold'), bg=COLOR_AZUL, fg='white',
                                          width=16, height=2, bd=0, relief='flat',
                                          activebackground=COLOR_AZUL, activeforeground='white',
                                          cursor='hand2')
        self.btn_estadisticas.pack(pady=5, padx=15, fill='x')
        
        separator = tk.Frame(controles_card, bg=COLOR_BORDE, height=1)
        separator.pack(fill='x', padx=15, pady=10)
        
        info_card = tk.Frame(controles_card, bg=COLOR_FONDO, bd=1, relief='flat')
        info_card.pack(fill='x', padx=15, pady=(0, 10))
        
        info_title = tk.Label(info_card, text="INFORMACION",
                             font=('Segoe UI', 9, 'bold'), fg=COLOR_TEXTO_SECUNDARIO,
                             bg=COLOR_FONDO, anchor='w')
        info_title.pack(fill='x', padx=10, pady=(5, 5))
        
        self.lbl_total_lecturas = tk.Label(info_card, text="Lecturas: 0",
                                           font=('Segoe UI', 10, 'bold'), fg=COLOR_DORADO, bg=COLOR_FONDO)
        self.lbl_total_lecturas.pack(fill='x', pady=2, padx=10)
        
        self.lbl_nodos_activos = tk.Label(info_card, text="Nodos: 0",
                                          font=('Segoe UI', 10, 'bold'), fg=COLOR_AZUL, bg=COLOR_FONDO)
        self.lbl_nodos_activos.pack(fill='x', pady=2, padx=10)
        
        # BARRA DE ESTADO
        self.status_bar = tk.Frame(self.root, bg=COLOR_CARD, height=30)
        self.status_bar.pack(fill='x', side='bottom', padx=0, pady=0)
        self.status_bar.pack_propagate(False)
        
        self.lbl_status = tk.Label(self.status_bar,
                                   text="Sistema listo | Haga clic en Conectar",
                                   font=('Segoe UI', 9), fg=COLOR_TEXTO_SECUNDARIO, bg=COLOR_CARD,
                                   anchor='w', padx=15)
        self.lbl_status.pack(side='left', fill='x', expand=True)
        
        self.lbl_status_bar_right = tk.Label(self.status_bar,
                                            text="v7.5 | UBV 2026",
                                            font=('Segoe UI', 9), fg=COLOR_TEXTO_SECUNDARIO, bg=COLOR_CARD,
                                            anchor='e', padx=15)
        self.lbl_status_bar_right.pack(side='right')
        
        self.actualizar_hora()
    
    def crear_card_parametro(self, parent, nombre, unidad, color, minimo, maximo):
        card = tk.Frame(parent, bg=COLOR_CARD, bd=1, relief='flat')
        
        header = tk.Frame(card, bg=color, height=3)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        content = tk.Frame(card, bg=COLOR_CARD)
        content.pack(fill='both', expand=True, padx=10, pady=5)
        
        tk.Label(content, text=nombre,
                font=('Segoe UI', 8, 'bold'), fg=COLOR_TEXTO_SECUNDARIO, 
                bg=COLOR_CARD, anchor='w').pack(fill='x')
        
        valor_label = tk.Label(content, text="--",
                              font=('Segoe UI', 20, 'bold'), fg=color, 
                              bg=COLOR_CARD, anchor='w')
        valor_label.pack(fill='x', pady=(2, 0))
        
        tk.Label(content, text=unidad,
                font=('Segoe UI', 9), fg=COLOR_TEXTO_SECUNDARIO, 
                bg=COLOR_CARD, anchor='w').pack(fill='x')
        
        progress_frame = tk.Frame(card, bg=COLOR_FONDO, height=4)
        progress_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        progress_bar = tk.Frame(progress_frame, bg=color, height=4, width=0)
        progress_bar.pack(side='left', fill='y')
        
        estado_label = tk.Label(card, text="ESPERANDO DATOS",
                               font=('Segoe UI', 7, 'bold'), fg=COLOR_GRIS, 
                               bg=COLOR_CARD, anchor='w')
        estado_label.pack(fill='x', padx=10, pady=(0, 2))
        
        tk.Label(card, text=f"Rango: {minimo}-{maximo} {unidad}",
                font=('Segoe UI', 6), fg=COLOR_TEXTO_SECUNDARIO, 
                bg=COLOR_CARD, anchor='w').pack(fill='x', padx=10, pady=(0, 5))
        
        return {
            'card': card, 'valor': valor_label, 'estado': estado_label,
            'progress_bar': progress_bar, 'progress_frame': progress_frame,
            'color': color, 'minimo': minimo, 'maximo': maximo, 'unidad': unidad
        }
    
    def actualizar_card_parametro(self, card_data, valor):
        card_data['valor'].config(text=f"{valor:.1f}")
        
        if card_data['unidad'] == 'mm':
            self.actualizar_card_lluvia_especial(card_data, valor)
            return
        
        rango = card_data['maximo'] - card_data['minimo']
        porcentaje = max(0, min(100, ((valor - card_data['minimo']) / rango) * 100)) if rango > 0 else 50
        
        ancho_total = card_data['progress_frame'].winfo_width()
        if ancho_total > 0:
            card_data['progress_bar'].config(width=int(ancho_total * porcentaje / 100))
        
        if valor < card_data['minimo'] or valor > card_data['maximo']:
            color, estado = COLOR_ROJO, "FUERA DE RANGO"
            status_text = f"ALERTA: Parametro fuera de rango ({valor:.1f}{card_data['unidad']})"
        elif valor < (card_data['minimo'] + rango * 0.2) or valor > (card_data['maximo'] - rango * 0.2):
            color, estado = COLOR_NARANJA, "PRECAUCION"
            status_text = f"Parametro en precaucion ({valor:.1f}{card_data['unidad']})"
        else:
            color, estado = COLOR_VERDE, "OPTIMO"
            status_text = "Todos los parametros dentro del rango biologico"
        
        card_data['estado'].config(text=estado, fg=color)
        self.lbl_status.config(text=status_text, fg=color)
    
    def actualizar_card_lluvia_especial(self, card_data, valor):
        porcentaje = max(0, min(100, valor))
        ancho_total = card_data['progress_frame'].winfo_width()
        if ancho_total > 0:
            card_data['progress_bar'].config(width=int(ancho_total * porcentaje / 100))
        
        if valor > EXCESO_UMBRAL:
            color = COLOR_ROJO
            estado = "EXCESO DE LLUVIA"
            status_text = f"ALERTA: Lluvia excesiva ({valor:.1f} mm)"
        elif valor > LLUVIA_MAX:
            color = COLOR_NARANJA
            estado = "LLUVIA ABUNDANTE"
            status_text = f"Precaucion: Lluvia abundante ({valor:.1f} mm)"
        elif valor >= LLUVIA_MIN:
            color = COLOR_VERDE
            estado = "LLUVIA OPTIMA"
            status_text = f"Lluvia en rango optimo ({valor:.1f} mm)"
        elif valor > 0:
            color = COLOR_CYAN
            estado = "LLUVIA LIGERA"
            status_text = f"Lluvia ligera ({valor:.1f} mm)"
        else:
            color = COLOR_GRIS
            estado = "SIN LLUVIA"
            status_text = f"Sin lluvia ({valor:.1f} mm)"
        
        card_data['estado'].config(text=estado, fg=color)
        self.lbl_status.config(text=status_text, fg=color)
    
    def actualizar_graficas_tiempo_real(self):
        try:
            if len(self.historial_temp) == 0: return
            x = range(len(self.historial_temp))
            
            for label, hist in [('Temp', self.historial_temp), ('Hum', self.historial_hum), 
                                ('Pres', self.historial_pres), ('Lluvia', self.historial_lluvia)]:
                self.lines[label].set_data(x, list(hist))
                ax = getattr(self, f'ax_{label.lower()}')
                ax.set_xlim(0, max(len(hist) - 1, 10))
            
            self.canvas_realtime.draw_idle()
        except Exception as e:
            print(f"Error actualizando graficas: {e}")
    
    def actualizar_hora(self):
        self.lbl_hora.config(text=datetime.now().strftime('%H:%M:%S'))
        self.root.after(1000, self.actualizar_hora)
    
    def conectar_serial(self):
        puertos = [p.device for p in serial.tools.list_ports.comports()]
        
        if not puertos:
            messagebox.showerror("Sin Puertos", "No se encontraron puertos COM disponibles.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Seleccionar Puerto COM")
        dialog.geometry("420x300")
        dialog.configure(bg=COLOR_FONDO)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        header = tk.Frame(dialog, bg=COLOR_CARD, height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="SELECCIONAR PUERTO",
                font=('Segoe UI', 13, 'bold'), fg=COLOR_DORADO, bg=COLOR_CARD).pack(pady=12)
        
        content = tk.Frame(dialog, bg=COLOR_FONDO)
        content.pack(fill='both', expand=True, padx=20, pady=15)
        
        tk.Label(content, text="Seleccione el puerto COM del ESP32 Servidor:",
                font=('Segoe UI', 10), fg=COLOR_TEXTO_PRIMARIO, 
                bg=COLOR_FONDO, anchor='w').pack(fill='x', pady=(0, 10))
        
        puerto_var = tk.StringVar()
        puerto_combo = ttk.Combobox(content, textvariable=puerto_var,
                                    state='readonly', 
                                    font=('Segoe UI', 11, 'bold'),
                                    values=puertos)
        puerto_combo.pack(fill='x', pady=(0, 10))
        puerto_combo.current(0)
        
        info_frame = tk.Frame(content, bg=COLOR_CARD, bd=1, relief='flat')
        info_frame.pack(fill='x', pady=(5, 10))
        
        tk.Label(info_frame, text=f"{len(puertos)} puerto(s) detectado(s)",
                font=('Segoe UI', 9), fg=COLOR_VERDE, bg=COLOR_CARD,
                anchor='w').pack(fill='x', padx=10, pady=8)
        
        resultado = {'puerto': None}
        
        def conectar():
            puerto = puerto_var.get()
            if not puerto:
                messagebox.showwarning("Atencion", "Debe seleccionar un puerto", parent=dialog)
                return
            resultado['puerto'] = puerto
            dialog.destroy()
        
        def cancelar():
            resultado['puerto'] = None
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLOR_FONDO)
        btn_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Button(btn_frame, text="Cancelar",
                 command=cancelar,
                 font=('Segoe UI', 10, 'bold'), bg=COLOR_ROJO, fg='white',
                 width=12, height=1, bd=0, relief='flat',
                 activebackground=COLOR_ROJO, cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="▶ Conectar",
                 command=conectar,
                 font=('Segoe UI', 10, 'bold'), bg=COLOR_VERDE, fg='white',
                 width=12, height=1, bd=0, relief='flat',
                 activebackground=COLOR_VERDE, cursor='hand2').pack(side='right', padx=5)
        
        self.root.wait_window(dialog)
        
        if resultado['puerto'] is None:
            return
        
        puerto_seleccionado = resultado['puerto']
        
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            self.ser = serial.Serial(puerto_seleccionado, BAUDRATE, timeout=1)
            self.running = True
            
            self.lbl_estado.config(text="● CONECTADO", fg=COLOR_VERDE)
            self.btn_conectar.config(state='disabled')
            self.btn_desconectar.config(state='normal')
            
            self.hilo_serial = threading.Thread(target=self.leer_serial, daemon=True)
            self.hilo_serial.start()
            
            self.lbl_status.config(text=f"Conectado a {puerto_seleccionado}", fg=COLOR_VERDE)
            messagebox.showinfo("Conexion Exitosa", f"Conectado al puerto {puerto_seleccionado}")
            
        except Exception as e:
            self.lbl_status.config(text=f"Error: {str(e)}", fg=COLOR_ROJO)
            messagebox.showerror("Error de Conexion", f"No se pudo conectar:\n{str(e)}")
    
    def desconectar_serial(self):
        self.running = False
        if self.hilo_serial:
            self.hilo_serial.join(timeout=2)
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        self.lbl_estado.config(text="● DESCONECTADO", fg=COLOR_ROJO)
        self.btn_conectar.config(state='normal')
        self.btn_desconectar.config(state='disabled')
        self.lbl_status.config(text="Desconectado", fg=COLOR_TEXTO_SECUNDARIO)
    
    def leer_serial(self):
        buffer = ""
        while self.running:
            try:
                if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                    texto = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += texto
                    while '\n' in buffer:
                        linea, buffer = buffer.split('\n', 1)
                        if linea.strip():
                            try:
                                datos = json.loads(linea.strip())
                                if 'temperature' in datos:
                                    self.root.after(0, self.procesar_datos, datos)
                            except json.JSONDecodeError: pass
            except Exception as e:
                print(f"Error lectura: {e}")
                break
    
    def procesar_datos(self, datos):
        try:
            node_id = datos.get('node_id', 0)
            temp = datos.get('temperature', 0)
            hum = datos.get('humidity', 0)
            pres = datos.get('pressure', 0)
            lluvia = datos.get('water_level', 0)
            
            self.historial_temp.append(temp)
            self.historial_hum.append(hum)
            self.historial_pres.append(pres)
            self.historial_lluvia.append(lluvia)
            self.datos_recientes.append(datos)
            
            if node_id not in self.datos_por_nodo: 
                self.datos_por_nodo[node_id] = deque(maxlen=100)
            self.datos_por_nodo[node_id].append(datos)
            
            self.actualizar_lista_nodos()
            self.actualizar_info()
            
            self.actualizar_card_parametro(self.card_temp, temp)
            self.actualizar_card_parametro(self.card_hum, hum)
            self.actualizar_card_parametro(self.card_pres, pres)
            self.actualizar_card_parametro(self.card_lluvia, lluvia)
            
            self.actualizar_graficas_tiempo_real()
            threading.Thread(target=self.guardar_en_bd, args=(datos,), daemon=True).start()
        except Exception as e:
            print(f"Error procesando: {e}")
    
    def actualizar_lista_nodos(self):
        for item in self.tree_nodos.get_children(): 
            self.tree_nodos.delete(item)
        for node_id in list(self.datos_por_nodo.keys())[:self.max_nodos]:
            if self.datos_por_nodo[node_id]:
                u = self.datos_por_nodo[node_id][-1]
                t = u.get('temperature', 0)
                h = u.get('humidity', 0)
                p = u.get('pressure', 0)
                lluvia = u.get('water_level', 0)
                
                alerta_lluvia = lluvia > EXCESO_UMBRAL
                alerta_temp = not (TEMP_MIN <= t <= TEMP_MAX)
                alerta_hum = not (HUM_MIN <= h <= HUM_MAX)
                alerta_pres = not (PRES_MIN <= p <= PRES_MAX)
                
                if alerta_lluvia or alerta_temp or alerta_hum or alerta_pres:
                    estado = "ALERTA"
                else:
                    estado = "OK"
                
                self.tree_nodos.insert('', 'end', values=(
                    f"Nodo {node_id}", f"{t:.1f}", f"{h:.1f}", f"{p:.1f}", f"{lluvia:.1f}", estado
                ))
    
    def actualizar_info(self):
        self.lbl_total_lecturas.config(text=f"Lecturas: {len(self.datos_recientes)}")
        self.lbl_nodos_activos.config(text=f"Nodos: {len(self.datos_por_nodo)}")
    
    def guardar_en_bd(self, datos):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("INSERT INTO colmena_data (node_id, timestamp_ms, temperature, humidity, pressure, water_level) VALUES (%s, %s, %s, %s, %s, %s)",
                        (datos['node_id'], datos['timestamp'], datos['temperature'], datos['humidity'], datos['pressure'], datos.get('water_level', 0)))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e: 
            print(f"Error BD: {e}")

    def ver_estadisticas(self):
        if not self.datos_por_nodo:
            messagebox.showwarning("Sin Datos", "No hay datos disponibles.")
            return
        
        win = tk.Toplevel(self.root)
        win.title("Estadisticas de Nodos")
        win.geometry("1200x800")
        win.configure(bg=COLOR_FONDO)
        
        hdr = tk.Frame(win, bg=COLOR_CARD, height=60)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        
        tk.Label(hdr, text="ANALISIS ESTADISTICO", font=('Segoe UI', 16, 'bold'), fg=COLOR_DORADO, bg=COLOR_CARD).pack(side='left', padx=20)
        tk.Button(hdr, text="X Cerrar", command=win.destroy, font=('Segoe UI', 10, 'bold'), bg=COLOR_ROJO, fg='white', bd=0, padx=15, pady=5, cursor='hand2').pack(side='right', padx=20)
        
        nb = ttk.Notebook(win)
        nb.pack(fill='both', expand=True, padx=10, pady=10)
        style = ttk.Style()
        style.configure('TNotebook', background=COLOR_FONDO, borderwidth=0)
        style.configure('TNotebook.Tab', background=COLOR_CARD, foreground=COLOR_TEXTO_SECUNDARIO, font=('Segoe UI', 10, 'bold'), padding=[20, 10])
        style.map('TNotebook.Tab', background=[('selected', COLOR_AZUL)], foreground=[('selected', 'white')])
        
        ids = sorted(self.datos_por_nodo.keys())
        
        f1 = tk.Frame(nb, bg=COLOR_FONDO)
        nb.add(f1, text=" Promedios ")
        p_t, p_h, p_p, p_l = [], [], [], []
        for nid in ids:
            d = list(self.datos_por_nodo[nid])
            p_t.append(np.mean([x.get('temperature',0) for x in d]) if d else 0)
            p_h.append(np.mean([x.get('humidity',0) for x in d]) if d else 0)
            p_p.append(np.mean([x.get('pressure',0) for x in d]) if d else 0)
            p_l.append(np.mean([x.get('water_level',0) for x in d]) if d else 0)
            
        fig = Figure(figsize=(12, 7), facecolor=COLOR_FONDO)
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLOR_FONDO)
        x = np.arange(len(ids))
        w = 0.18
        b1 = ax.bar(x-1.5*w, p_t, w, label='Temp', color=COLOR_ROJO, alpha=0.8)
        b2 = ax.bar(x-0.5*w, p_h, w, label='Hum', color=COLOR_AZUL, alpha=0.8)
        b3 = ax.bar(x+0.5*w, p_p, w, label='Pres', color=COLOR_VERDE, alpha=0.8)
        b4 = ax.bar(x+1.5*w, p_l, w, label='Lluvia', color=COLOR_CYAN, alpha=0.8)
        
        ax.set_title('Promedios por Nodo', fontweight='bold', fontsize=14, color=COLOR_DORADO)
        ax.set_xticks(x)
        ax.set_xticklabels([f'Nodo {n}' for n in ids], color=COLOR_TEXTO_PRIMARIO)
        ax.legend(facecolor=COLOR_CARD, labelcolor=COLOR_TEXTO_PRIMARIO)
        ax.grid(alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(colors=COLOR_TEXTO_SECUNDARIO)
        for b in [b1,b2,b3,b4]:
            for bar in b: 
                ax.annotate(f'{bar.get_height():.1f}', xy=(bar.get_x()+bar.get_width()/2, bar.get_height()), ha='center', color='white', fontsize=9)
        fig.tight_layout()
        FigureCanvasTkAgg(fig, f1).get_tk_widget().pack(fill='both', expand=True, padx=20, pady=20)
        
        f2 = tk.Frame(nb, bg=COLOR_FONDO)
        nb.add(f2, text=" Tendencia ")
        fig2 = Figure(figsize=(12, 7), facecolor=COLOR_FONDO)
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor(COLOR_FONDO)
        cols = [COLOR_ROJO, COLOR_AZUL, COLOR_VERDE, COLOR_CYAN]
        for i, nid in enumerate(ids):
            temps = [x.get('temperature',0) for x in self.datos_por_nodo[nid]]
            ax2.plot(temps, label=f'Nodo {nid}', color=cols[i%4], linewidth=2, marker='o', markersize=4)
        ax2.set_title('Evolucion de Temperatura', fontweight='bold', fontsize=14, color=COLOR_DORADO)
        ax2.axhline(TEMP_MIN, color=COLOR_VERDE, linestyle='--', label=f'Min {TEMP_MIN}°C')
        ax2.axhline(TEMP_MAX, color=COLOR_ROJO, linestyle='--', label=f'Max {TEMP_MAX}°C')
        ax2.legend(facecolor=COLOR_CARD, labelcolor=COLOR_TEXTO_PRIMARIO)
        ax2.grid(alpha=0.2, linestyle='--')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.tick_params(colors=COLOR_TEXTO_SECUNDARIO)
        fig2.tight_layout()
        FigureCanvasTkAgg(fig2, f2).get_tk_widget().pack(fill='both', expand=True, padx=20, pady=20)
        
        f3 = tk.Frame(nb, bg=COLOR_FONDO)
        nb.add(f3, text=" Tabla Resumen ")
        tree_frame = tk.Frame(f3, bg=COLOR_FONDO)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=20)
        columnas = ('Nodo', 'Lecturas', 'Temp Prom', 'Hum Prom', 'Pres Prom', 'Lluvia Prom')
        tree = ttk.Treeview(tree_frame, columns=columnas, show='headings', height=10, style='Custom.Treeview')
        for col in columnas:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor='center')
        for nid in ids:
            d = list(self.datos_por_nodo[nid])
            temps = [x.get('temperature',0) for x in d]
            hums = [x.get('humidity',0) for x in d]
            pres = [x.get('pressure',0) for x in d]
            lluvias = [x.get('water_level',0) for x in d]
            tree.insert('', 'end', values=(
                f'Nodo {nid}', len(d),
                f'{np.mean(temps):.1f}°C' if temps else '--',
                f'{np.mean(hums):.1f}%' if hums else '--',
                f'{np.mean(pres):.1f} hPa' if pres else '--',
                f'{np.mean(lluvias):.1f} mm' if lluvias else '--'
            ))
        tree.pack(fill='both', expand=True)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = MonitorApiario(root)
        root.mainloop()
    except Exception as e:
        print(f"Error fatal: {e}")
        traceback.print_exc()
        input("Presiona Enter para salir...")