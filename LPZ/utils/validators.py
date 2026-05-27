def validate_required_fields(data, fields):
    missing = [f for f in fields if not data or not data.get(f)]
    if missing:
        return False, f"Campos requeridos faltantes: {', '.join(missing)}"
    return True, None


def validate_positive_integer(value, name="id"):
    try:
        val = int(value)
        if val <= 0:
            return False, f"El campo '{name}' debe ser un entero positivo"
        return True, None
    except (TypeError, ValueError):
        return False, f"El campo '{name}' debe ser un numero entero"
