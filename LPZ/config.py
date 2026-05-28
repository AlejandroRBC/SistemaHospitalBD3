# Configuracion del nodo LPZ (La Paz) - MEDIADOR CENTRAL
# Bandera La Paz: Rojo y Amarillo

LPZ_DB = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hospital_lpz',
    'user': 'postgres',
    'password': 'admin'
}

# Conexion directa al SQL Server de Cochabamba (desde el mediador)
CBBA_SQL = {
    'driver': 'ODBC Driver 17 for SQL Server',
    'server': '26.8.33.47',
    'port': 1433,
    'database': 'hospital_cbba',
    'user': 'sa',
    'password': '123456'
}

# Conexion directa al SQL Server de Santa Cruz (desde el mediador)
STCZ_SQL = {
    'driver': 'ODBC Driver 17 for SQL Server',
    'server': '26.116.149.11',
    'port': 1433,
    'database': 'hospital_stcz',
    'user': 'sa',
    'password': '123456'
}

# URLs HTTP de cada nodo (fallback cuando la conexion directa falla)
LPZ_URL  = 'http://26.91.247.115:5000'
CBBA_URL = 'http://26.8.33.47:5001'
STCZ_URL = 'http://26.116.149.11:5002'

ID_HOSPITAL = 1
NODO        = 'LPZ'
PORT        = 5000
HOST        = '0.0.0.0'
SECRET_KEY  = 'hospital-lpz-2026-bd3'

# Colores bandera departamento La Paz (rojo arriba / amarillo abajo)
COLOR_PRIMARY   = '#B22222'   # Rojo firebrick
COLOR_SECONDARY = '#FFD700'   # Amarillo dorado
COLOR_BG        = '#FFF8DC'   # Crema claro
HOSPITAL_NOMBRE = 'Hospital Central de La Paz'
