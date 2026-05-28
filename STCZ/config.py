# Configuracion del nodo STCZ (Santa Cruz)
# Bandera Santa Cruz: 5 franjas verde-blanco-verde-blanco-verde

SQL_DB = {
    'driver': 'ODBC Driver 17 for SQL Server',
    'server': 'localhost',
    'port': 1433,
    'database': 'hospital_stcz',
    'user': 'sa',
    'password': '123456'
}

# URLs de los demas nodos (para consultas distribuidas via HTTP)
LPZ_URL  = 'http://26.91.247.115:5000'
CBBA_URL = 'http://26.8.33.47:5001'
STCZ_URL = 'http://26.116.149.11:5002'

ID_HOSPITAL = 3
NODO        = 'STCZ'
PORT        = 5002
HOST        = '0.0.0.0'
SECRET_KEY  = 'hospital-stcz-2026-bd3'

# Colores bandera departamento Santa Cruz (5 franjas: verde oscuro y blanco)
COLOR_PRIMARY   = '#1B5E20'   # Verde muy oscuro
COLOR_SECONDARY = '#80CBC4'   # Verde-teal claro
COLOR_BG        = '#E8F5E9'   # Verde palido
HOSPITAL_NOMBRE = 'Hospital del Oriente - Santa Cruz'
