import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, confusion_matrix, classification_report)
import warnings
warnings.filterwarnings('ignore')

class AcademicDropoutPredictor:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Predicción de Deserción Académica")
        self.root.geometry("512x384")
        self.root.resizable(False, False)
        
        self.df = None
        self.X = None
        self.y = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.model = None
        self.model_type = "logistic"
        self.preprocessor = None
        self.is_preprocessed = False
        self.is_model_trained = False
        
        # Mapeo de target
        self.target_map = {"Dropout": 0, "Enrolled": 1, "Graduate": 2}
        self.reverse_target_map = {0: "Dropout", 1: "Enrolled", 2: "Graduate"}
        self.classes = ['Dropout', 'Enrolled', 'Graduate']
        
        # Ventanas abiertas
        self.table_window = None
        self.metrics_window = None
        self.cm_window = None
        self.train_window = None
        self.pred_window = None
        
        self.setup_main_window()
        
    def setup_main_window(self):
        # Frame principal centrado
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="Sistema de Predicción\nDeserción Académica", 
                                font=('Arial', 16, 'bold'), justify='center')
        title_label.pack(pady=20)
        
        # Botones
        btn_style = {'width': 25, 'padding': 5}
        
        ttk.Button(main_frame, text="Cargar CSV", command=self.load_csv, **btn_style).pack(pady=10)
        ttk.Button(main_frame, text="Entrenar Modelo", command=self.open_train_window, **btn_style).pack(pady=10)
        ttk.Button(main_frame, text="Nueva Predicción", command=self.open_prediction_window, **btn_style).pack(pady=10)
        
        # Estado
        self.status_label = ttk.Label(main_frame, text="Estado: Esperando carga de datos", font=('Arial', 9))
        self.status_label.pack(pady=20)
    
    def update_status(self, message):
        self.status_label.config(text=f"Estado: {message}")
        self.root.update_idletasks()
    
    def close_all_child_windows(self):
        """Cierra todas las ventanas secundarias abiertas"""
        if self.table_window is not None and self.table_window.winfo_exists():
            self.table_window.destroy()
            self.table_window = None
        if self.metrics_window is not None and self.metrics_window.winfo_exists():
            self.metrics_window.destroy()
            self.metrics_window = None
        if self.cm_window is not None and self.cm_window.winfo_exists():
            self.cm_window.destroy()
            self.cm_window = None
        if self.train_window is not None and self.train_window.winfo_exists():
            self.train_window.destroy()
            self.train_window = None
        if self.pred_window is not None and self.pred_window.winfo_exists():
            self.pred_window.destroy()
            self.pred_window = None
    
    def load_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            try:
                # Cerrar ventanas secundarias existentes
                self.close_all_child_windows()
                
                # 1. Cargar dataset
                self.df = pd.read_csv(file_path)
                self.update_status(f"Dataset cargado: {self.df.shape[0]} filas, {self.df.shape[1]} columnas")
                
                # 2. Preprocesar dataset
                success = self.preprocess_data()
                
                if success:
                    self.update_status("Preprocesamiento completado")
                    
                    # 3. Abrir ventana con el dataset preprocesado (modal)
                    self.show_data_table()
                    
                    # Esperar a que se cierre la ventana de la tabla
                    self.root.wait_window(self.table_window)
                    
                    # 4. Ejecutar primera predicción con modelo predeterminado
                    self.train_default_model()
                else:
                    self.update_status("Error en preprocesamiento")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar el archivo: {str(e)}")
                self.update_status("Error al cargar dataset")
    
    def preprocess_data(self):
        """Preprocesamiento completo de datos basado en los códigos de referencia"""
        if self.df is None:
            return False
        
        # Verificar que existe la columna Target
        if "Target" not in self.df.columns:
            messagebox.showerror("Error", "El dataset debe contener una columna 'Target'")
            return False
        
        # Separar características y target
        self.X = self.df.drop("Target", axis=1)
        
        # Manejar posibles valores NaN en Target
        self.df["Target"] = self.df["Target"].fillna("Dropout")
        self.y = self.df["Target"].map(self.target_map)
        
        # Verificar que no hay NaN en y
        if self.y.isna().any():
            most_common = self.y.mode()[0] if len(self.y.mode()) > 0 else 0
            self.y = self.y.fillna(most_common)
        
        # Identificar columnas numéricas y categóricas
        numeric_cols = self.X.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_cols = self.X.select_dtypes(include=['object']).columns.tolist()
        
        # Crear pipelines de preprocesamiento
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_cols),
                ('cat', categorical_transformer, categorical_cols)
            ]
        )
        
        # Transformar datos
        X_processed = self.preprocessor.fit_transform(self.X)
        
        # Verificar que no hay NaN después del preprocesamiento
        if np.isnan(X_processed).any():
            X_processed = np.nan_to_num(X_processed)
        
        # Dividir en entrenamiento y prueba con estratificación
        # Asegurar que todas las clases estén representadas
        unique_classes = self.y.unique()
        min_samples_per_class = 2  # Mínimo para estratificación
        
        # Verificar si hay suficientes muestras por clase
        valid = True
        for cls in unique_classes:
            count = (self.y == cls).sum()
            if count < min_samples_per_class:
                valid = False
                break
        
        if valid and len(unique_classes) > 1:
            self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                X_processed, self.y, test_size=0.2, random_state=42, stratify=self.y
            )
        else:
            # Si no se puede estratificar, hacer split normal
            self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                X_processed, self.y, test_size=0.2, random_state=42
            )
        
        # Verificar que el conjunto de prueba tenga todas las clases
        test_classes = set(self.y_test.unique())
        train_classes = set(self.y_train.unique())
        
        # Si faltan clases en prueba, ajustar
        if len(test_classes) < len(unique_classes):
            # Hacer un split manual para asegurar representación
            indices = np.arange(len(self.y))
            train_indices = []
            test_indices = []
            
            for cls in unique_classes:
                cls_indices = indices[self.y == cls]
                n_test = max(1, int(len(cls_indices) * 0.2))
                test_indices.extend(cls_indices[:n_test])
                train_indices.extend(cls_indices[n_test:])
            
            self.X_train = X_processed[train_indices]
            self.X_test = X_processed[test_indices]
            self.y_train = self.y.iloc[train_indices].reset_index(drop=True)
            self.y_test = self.y.iloc[test_indices].reset_index(drop=True)
        
        self.is_preprocessed = True
        return True
    
    def show_data_table(self):
        """Muestra la tabla completa en una nueva ventana (modal)"""
        if self.df is None:
            return
        
        self.table_window = Toplevel(self.root)
        self.table_window.title("Dataset Cargado - Vista Completa")
        self.table_window.geometry("1200x600")
        self.table_window.transient(self.root)
        self.table_window.grab_set()
        
        # Frame para tabla con scroll
        frame = ttk.Frame(self.table_window)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")
        
        # Treeview para mostrar datos
        tree = ttk.Treeview(frame, columns=list(self.df.columns), 
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        # Configurar columnas
        tree.column("#0", width=50, anchor="center")
        for col in self.df.columns:
            tree.column(col, width=120, anchor="center")
            tree.heading(col, text=col)
        
        # Insertar datos
        for idx, row in self.df.iterrows():
            tree.insert("", "end", text=idx+1, values=list(row))
        
        # Posicionar
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Información del dataset
        info_label = ttk.Label(self.table_window, 
                               text=f"Dimensiones: {self.df.shape[0]} filas × {self.df.shape[1]} columnas\nCierre esta ventana para continuar con el entrenamiento...",
                               font=('Arial', 10))
        info_label.pack(pady=5)
        
        # Botón cerrar
        ttk.Button(self.table_window, text="Cerrar y Continuar", command=self.table_window.destroy).pack(pady=5)
    
    def train_default_model(self):
        """Entrena modelo por default (Regresión Logística) y muestra métricas"""
        if not self.is_preprocessed:
            messagebox.showwarning("Advertencia", "Primero debe cargar un dataset")
            return False
        
        try:
            # Usar regresión logística por default
            self.model = LogisticRegression(max_iter=1000, random_state=42)
            self.model_type = "logistic"
            
            # Entrenar
            self.model.fit(self.X_train, self.y_train)
            self.is_model_trained = True
            self.update_status("Modelo entrenado correctamente")
            
            # Evaluar
            y_pred = self.model.predict(self.X_test)
            
            # 5. Abrir ventana con las métricas de predicción del modelo (modal)
            self.show_metrics_window(y_pred)
            
            # Esperar a que se cierre la ventana de métricas
            self.root.wait_window(self.metrics_window)
            
            # 6. Abrir ventana con la matriz de confusión graficada
            self.show_confusion_matrix_window(y_pred)
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en entrenamiento inicial: {str(e)}")
            self.update_status("Error en entrenamiento")
            return False
    
    def train_custom_model(self, model_type, params):
        """Entrena modelo personalizado con parámetros específicos"""
        if not self.is_preprocessed:
            messagebox.showwarning("Advertencia", "Primero debe cargar un dataset")
            return False
        
        try:
            if model_type == "logistic":
                self.model = LogisticRegression(max_iter=params.get('max_iter', 1000), random_state=42)
                self.model_type = "logistic"
            else:
                self.model = DecisionTreeClassifier(max_depth=params.get('max_depth', 4), random_state=42)
                self.model_type = "tree"
            
            # Entrenar
            self.model.fit(self.X_train, self.y_train)
            self.is_model_trained = True
            self.update_status("Modelo entrenado correctamente")
            
            # Evaluar
            y_pred = self.model.predict(self.X_test)
            
            # Mostrar métricas
            self.show_metrics_window(y_pred)
            
            # Mostrar matriz de confusión
            self.show_confusion_matrix_window(y_pred)
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error al entrenar modelo: {str(e)}")
            return False
    
    def show_metrics_window(self, y_pred):
        """Muestra las métricas en una nueva ventana modal"""
        self.metrics_window = Toplevel(self.root)
        self.metrics_window.title("Resultados del Modelo - Métricas de Evaluación")
        self.metrics_window.geometry("500x400")
        self.metrics_window.transient(self.root)
        self.metrics_window.grab_set()
        
        # Calcular métricas
        acc = accuracy_score(self.y_test, y_pred)
        prec = precision_score(self.y_test, y_pred, average='weighted', zero_division=0)
        rec = recall_score(self.y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(self.y_test, y_pred, average='weighted', zero_division=0)
        
        # Validación cruzada
        X_processed = self.preprocessor.transform(self.X)
        if np.isnan(X_processed).any():
            X_processed = np.nan_to_num(X_processed)
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self.model, X_processed, self.y, cv=cv, scoring='f1_weighted')
        
        # Frame principal
        main_frame = ttk.Frame(self.metrics_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title = "Regresión Logística" if self.model_type == "logistic" else f"Árbol de Decisión"
        ttk.Label(main_frame, text=f"Métricas del Modelo: {title}", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Frame para métricas
        metrics_frame = ttk.LabelFrame(main_frame, text="Métricas de Evaluación", padding="10")
        metrics_frame.pack(fill=tk.X, pady=10)
        
        metrics_text = tk.Text(metrics_frame, height=12, width=55, font=('Courier', 10))
        metrics_text.pack()
        
        metrics_text.insert(tk.END, f"Accuracy:   {acc:.4f} ({acc*100:.2f}%)\n")
        metrics_text.insert(tk.END, f"Precision:  {prec:.4f}\n")
        metrics_text.insert(tk.END, f"Recall:     {rec:.4f}\n")
        metrics_text.insert(tk.END, f"F1-Score:   {f1:.4f}\n\n")
        metrics_text.insert(tk.END, f"Validación Cruzada (5 folds):\n")
        metrics_text.insert(tk.END, f"  F1 promedio: {cv_scores.mean():.4f}\n")
        metrics_text.insert(tk.END, f"  Desviación:  {cv_scores.std():.4f}\n\n")
        metrics_text.insert(tk.END, f"Tamaño conjunto entrenamiento: {len(self.y_train)}\n")
        metrics_text.insert(tk.END, f"Tamaño conjunto prueba: {len(self.y_test)}\n")
        metrics_text.insert(tk.END, f"Número de clases: {len(np.unique(self.y_test))}\n")
        
        metrics_text.config(state=tk.DISABLED)
        
        # Botón cerrar
        ttk.Button(main_frame, text="Cerrar", command=self.metrics_window.destroy).pack(pady=10)
    
    def show_confusion_matrix_window(self, y_pred):
        """Muestra la matriz de confusión en una nueva ventana modal"""
        self.cm_window = Toplevel(self.root)
        self.cm_window.title("Matriz de Confusión")
        self.cm_window.geometry("550x500")
        self.cm_window.transient(self.root)
        self.cm_window.grab_set()
        
        # Frame principal
        main_frame = ttk.Frame(self.cm_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="Matriz de Confusión del Modelo", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Calcular matriz de confusión
        cm = confusion_matrix(self.y_test, y_pred, labels=[0, 1, 2])
        
        # Información de soporte
        info_frame = ttk.LabelFrame(main_frame, text="Información por Clase", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        info_text = tk.Text(info_frame, height=6, width=50, font=('Courier', 9))
        info_text.pack()
        
        # Mostrar distribución real
        unique, counts = np.unique(self.y_test, return_counts=True)
        info_text.insert(tk.END, "Distribución real en prueba:\n")
        for u, c in zip(unique, counts):
            info_text.insert(tk.END, f"  {self.reverse_target_map[u]}: {c} muestras\n")
        info_text.insert(tk.END, "\n")
        
        # Mostrar predicciones
        pred_unique, pred_counts = np.unique(y_pred, return_counts=True)
        info_text.insert(tk.END, "Distribución de predicciones:\n")
        for u, c in zip(pred_unique, pred_counts):
            info_text.insert(tk.END, f"  {self.reverse_target_map[u]}: {c} muestras\n")
        
        info_text.config(state=tk.DISABLED)
        
        # Matriz de confusión gráfica
        cm_frame = ttk.LabelFrame(main_frame, text="Matriz de Confusión (Visual)", padding="10")
        cm_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        fig, ax = plt.subplots(figsize=(5, 4))
        
        # Crear matriz con soporte completo de 3 clases
        cm_display = np.zeros((3, 3), dtype=int)
        for i in range(min(cm.shape[0], 3)):
            for j in range(min(cm.shape[1], 3)):
                cm_display[i, j] = cm[i, j]
        
        im = ax.imshow(cm_display, interpolation='nearest', cmap=plt.cm.Blues)
        ax.figure.colorbar(im, ax=ax)
        
        ax.set(xticks=np.arange(3),
               yticks=np.arange(3),
               xticklabels=self.classes,
               yticklabels=self.classes,
               title='Matriz de Confusión',
               ylabel='Valor Real',
               xlabel='Predicción')
        
        # Ajustar tamaño de texto en la matriz
        thresh = cm_display.max() / 2.
        for i in range(3):
            for j in range(3):
                ax.text(j, i, format(cm_display[i, j], 'd'),
                       ha="center", va="center",
                       fontsize=12,
                       color="white" if cm_display[i, j] > thresh else "black")
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=cm_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()
        
        # Botón cerrar
        ttk.Button(main_frame, text="Cerrar", command=self.cm_window.destroy).pack(pady=10)
    
    def open_train_window(self):
        """Abre ventana para seleccionar modelo y parámetros"""
        if not self.is_preprocessed:
            messagebox.showwarning("Advertencia", "Primero debe cargar un dataset")
            return
        
        # Cerrar ventana de entrenamiento si existe
        if self.train_window is not None and self.train_window.winfo_exists():
            self.train_window.destroy()
        
        self.train_window = Toplevel(self.root)
        self.train_window.title("Entrenar Modelo")
        self.train_window.geometry("400x350")
        self.train_window.resizable(False, False)
        
        main_frame = ttk.Frame(self.train_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Configuración del Modelo", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Selección de modelo
        model_var = tk.StringVar(value="logistic")
        ttk.Label(main_frame, text="Tipo de Modelo:").pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(main_frame, text="Regresión Logística", variable=model_var, 
                       value="logistic").pack(anchor=tk.W)
        ttk.Radiobutton(main_frame, text="Árbol de Decisión", variable=model_var, 
                       value="tree").pack(anchor=tk.W)
        
        # Frame para parámetros
        params_frame = ttk.LabelFrame(main_frame, text="Parámetros", padding="10")
        params_frame.pack(fill=tk.X, pady=15)
        
        # Parámetros específicos
        max_iter_var = tk.StringVar(value="1000")
        max_depth_var = tk.StringVar(value="4")
        
        def update_params(*args):
            # Limpiar frame
            for widget in params_frame.winfo_children():
                widget.destroy()
            
            if model_var.get() == "logistic":
                ttk.Label(params_frame, text="Máximas Iteraciones:").grid(row=0, column=0, sticky=tk.W, padx=5)
                ttk.Entry(params_frame, textvariable=max_iter_var, width=15).grid(row=0, column=1, padx=5)
            else:
                ttk.Label(params_frame, text="Profundidad Máxima:").grid(row=0, column=0, sticky=tk.W, padx=5)
                ttk.Entry(params_frame, textvariable=max_depth_var, width=15).grid(row=0, column=1, padx=5)
        
        model_var.trace('w', update_params)
        update_params()
        
        def do_train():
            if model_var.get() == "logistic":
                params = {'max_iter': int(max_iter_var.get())}
                success = self.train_custom_model("logistic", params)
            else:
                params = {'max_depth': int(max_depth_var.get())}
                success = self.train_custom_model("tree", params)
            
            if success:
                self.train_window.destroy()
                messagebox.showinfo("Éxito", "Modelo entrenado correctamente")
        
        ttk.Button(main_frame, text="Entrenar", command=do_train).pack(pady=10)
        ttk.Button(main_frame, text="Cancelar", command=self.train_window.destroy).pack()
    
    def open_prediction_window(self):
        """Abre ventana para realizar una nueva predicción"""
        if not self.is_model_trained:
            messagebox.showwarning("Advertencia", "Primero debe entrenar un modelo")
            return
        
        # Cerrar ventana de predicción si existe
        if self.pred_window is not None and self.pred_window.winfo_exists():
            self.pred_window.destroy()
        
        self.pred_window = Toplevel(self.root)
        self.pred_window.title("Nueva Predicción")
        self.pred_window.geometry("500x600")
        self.pred_window.resizable(False, False)
        
        main_frame = ttk.Frame(self.pred_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Formulario de Datos del Estudiante", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Crear formulario basado en las columnas del dataset original
        entries = {}
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Obtener columnas originales
        original_cols = self.X.columns.tolist()
        
        # Valores por defecto (medianas para numéricas, moda para categóricas)
        default_values = {}
        for col in original_cols:
            if pd.api.types.is_numeric_dtype(self.X[col]):
                default_values[col] = self.X[col].median()
            else:
                default_values[col] = self.X[col].mode()[0] if len(self.X[col].mode()) > 0 else "unknown"
        
        # Crear campos del formulario
        row = 0
        for col in original_cols[:15]:
            ttk.Label(scrollable_frame, text=f"{col}:", font=('Arial', 9)).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
            
            if pd.api.types.is_numeric_dtype(self.X[col]):
                entry = ttk.Entry(scrollable_frame, width=25)
                entry.insert(0, str(default_values[col]))
            else:
                unique_vals = self.X[col].dropna().unique().tolist()
                if len(unique_vals) > 0:
                    entry = ttk.Combobox(scrollable_frame, values=unique_vals, width=22)
                    entry.set(default_values[col])
                else:
                    entry = ttk.Entry(scrollable_frame, width=25)
                    entry.insert(0, str(default_values[col]))
            
            entry.grid(row=row, column=1, pady=3, padx=5)
            entries[col] = entry
            row += 1
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Resultado
        result_text = tk.Text(main_frame, height=8, width=55, font=('Arial', 10))
        result_text.pack(pady=10)
        
        def do_prediction():
            try:
                new_data = {}
                for col, entry in entries.items():
                    val = entry.get()
                    if pd.api.types.is_numeric_dtype(self.X[col]):
                        new_data[col] = float(val) if val else default_values[col]
                    else:
                        new_data[col] = val if val else default_values[col]
                
                for col in original_cols:
                    if col not in new_data:
                        if pd.api.types.is_numeric_dtype(self.X[col]):
                            new_data[col] = default_values[col]
                        else:
                            new_data[col] = default_values[col]
                
                new_df = pd.DataFrame([new_data])
                new_processed = self.preprocessor.transform(new_df)
                
                if np.isnan(new_processed).any():
                    new_processed = np.nan_to_num(new_processed)
                
                prediction = self.model.predict(new_processed)[0]
                proba = self.model.predict_proba(new_processed)[0]
                
                # Ajustar probabilidades a 3 clases si es necesario
                if len(proba) < 3:
                    new_proba = np.zeros(3)
                    for i in range(min(len(proba), 3)):
                        new_proba[i] = proba[i]
                    proba = new_proba
                
                result_text.delete(1.0, tk.END)
                
                if prediction == 0:
                    result_text.insert(tk.END, "PREDICCIÓN: ALTO RIESGO DE DESERCIÓN\n", "red")
                    result_text.tag_config("red", foreground="red")
                    result_text.insert(tk.END, "El estudiante tiene alta probabilidad de desertar.\n\n")
                elif prediction == 1:
                    result_text.insert(tk.END, "PREDICCIÓN: RIESGO MODERADO\n", "orange")
                    result_text.tag_config("orange", foreground="orange")
                    result_text.insert(tk.END, "El estudiante podría estar en riesgo.\n\n")
                else:
                    result_text.insert(tk.END, "PREDICCIÓN: BAJO RIESGO\n", "green")
                    result_text.tag_config("green", foreground="green")
                    result_text.insert(tk.END, "El estudiante tiene alta probabilidad de graduarse.\n\n")
                
                result_text.insert(tk.END, "Probabilidades:\n")
                result_text.insert(tk.END, f"  Dropout:   {proba[0]*100:.1f}%\n")
                result_text.insert(tk.END, f"  Enrolled:  {proba[1]*100:.1f}%\n")
                result_text.insert(tk.END, f"  Graduate: {proba[2]*100:.1f}%\n")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error en la predicción: {str(e)}")
        
        ttk.Button(main_frame, text="Realizar Predicción", command=do_prediction).pack(pady=10)
        ttk.Button(main_frame, text="Cerrar", command=self.pred_window.destroy).pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = AcademicDropoutPredictor(root)
    root.mainloop()