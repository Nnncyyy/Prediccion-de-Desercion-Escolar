"""RNF_01 / PT_13 · Genera la configuración local con credenciales aleatorias."""
import argparse
import os
from pathlib import Path
import secrets
from tempfile import NamedTemporaryFile


def generar_env(plantilla: Path, destino: Path, *, forzar: bool = False) -> dict[str, str]:
    """Escribe la plantilla con permisos privados y devuelve las credenciales generadas."""
    reemplazos = {
        'JWT_SECRET': secrets.token_urlsafe(48),
        'ADMIN_PASSWORD': secrets.token_urlsafe(24),
        'POSTGRES_PASSWORD': secrets.token_urlsafe(24),
    }
    valores = {}
    lineas = []
    for linea in plantilla.read_text(encoding='utf-8').splitlines():
        clave, separador, valor = linea.partition('=')
        if separador and not clave.startswith('#'):
            valores[clave] = reemplazos.get(clave, valor)
            linea = f'{clave}={valores[clave]}'
        lineas.append(linea)

    contenido = '\n'.join(lineas) + '\n'
    if forzar:
        # Conserva los permisos privados al reemplazar la configuración anterior.
        temporal = NamedTemporaryFile(mode='w', dir=destino.parent, encoding='utf-8', delete=False)
        ruta_temporal = Path(temporal.name)
        try:
            with temporal:
                temporal.write(contenido)
            ruta_temporal.replace(destino)
        finally:
            ruta_temporal.unlink(missing_ok=True)
    else:
        with open(destino, 'x', encoding='utf-8', opener=lambda ruta, flags: os.open(
            ruta, flags, 0o600
        )) as archivo:
            archivo.write(contenido)
    return valores


def main() -> None:
    backend = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true', help='Reemplaza el archivo .env existente.')
    argumentos = parser.parse_args()
    try:
        valores = generar_env(backend.parent / '.env.example', backend / '.env', forzar=argumentos.force)
    except FileExistsError:
        parser.exit(1, 'Ya existe backend/.env. Usa --force para reemplazarlo.\n')

    print('Configuración creada en backend/.env.')
    for clave in ('ADMIN_EMAIL', 'ADMIN_PASSWORD', 'POSTGRES_PASSWORD'):
        print(f'{clave}={valores[clave]}')


if __name__ == '__main__':
    main()
