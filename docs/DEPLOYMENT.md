# Guía de Despliegue y Configuración

---

## 1. Requisitos Previos

* **Python:** 3.12+
* **Node.js:** v20+ o v24+
* **.NET SDK:** .NET 8.0 SDK (o .NET Runtime para ejecución de binarios compilados)
* **PostgreSQL:** Versión 15, 16, 17 o 18
* **Redis:** Versión 6 o superior (para tareas Celery)

---

## 2. Puesta en Marcha Local en Desarrollo

### A. Backend (Django)
```bash
# 1. Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\activate   # En Windows

# 2. Instalar dependencias
pip install -r backend/requirements.txt

# 3. Aplicar migraciones
python backend/manage.py migrate

# 4. Sembrar datos de prueba con modelo real de Equinor
python backend/seed_demo.py

# 5. Iniciar servidor Django
python backend/manage.py runserver 8000
```

### B. Worker Celery (en otra terminal)
```bash
.\venv\Scripts\activate
cd backend
celery -A core worker -l info
```

### C. Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install
npm run dev
```
La aplicación web estará disponible en `http://localhost:5173`.
