# Configuracion del nodo CBBA (Cochabamba)
# Bandera Cochabamba: Verde y Blanco

SQL_DB = {
    'driver': 'ODBC Driver 17 for SQL Server',
    'server': 'localhost',
    'port': 1433,
    'database': 'hospital_cbba',
    'user': 'sa',
    'password': 'Admin1234!'
}

# URLs de los demas nodos (para consultas distribuidas via HTTP)
LPZ_URL  = 'http://26.91.247.115:5000'
CBBA_URL = 'http://26.8.33.47:5001'
STCZ_URL = 'http://26.XX.XX.XX:5002'

ID_HOSPITAL = 2
NODO        = 'CBBA'
PORT        = 5001
HOST        = '0.0.0.0'
SECRET_KEY  = 'hospital-cbba-2026-bd3'

# Colores bandera departamento Cochabamba (verde arriba / blanco abajo)
COLOR_PRIMARY   = '#2E7D32'   # Verde oscuro
COLOR_SECONDARY = '#A5D6A7'   # Verde claro
COLOR_BG        = '#F1F8E9'   # Verde muy tenue
HOSPITAL_NOMBRE = 'Hospital Regional de Cochabamba'
