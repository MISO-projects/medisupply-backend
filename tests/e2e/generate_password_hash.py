"""
Script para generar hashes de password con Argon2

Este script genera los hashes de password necesarios para los usuarios de prueba E2E.

Uso:
    python tests/e2e/generate_password_hash.py

Luego copia los hashes generados al archivo seed_test_data.sql
"""
try:
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher
except ImportError:
    print("Error: pwdlib no está instalado")
    print("Instala con: pip install 'pwdlib[argon2]'")
    exit(1)


def generar_hash(password: str) -> str:
    """Genera un hash Argon2 para el password dado"""
    password_hash = PasswordHash((Argon2Hasher(),))
    return password_hash.hash(password)


def main():
    print("=" * 80)
    print("Generador de Hashes de Password para Pruebas E2E")
    print("=" * 80)

    password = "test123"

    print(f"\nGenerando hashes para password: '{password}'")
    print("\nEsto puede tardar unos segundos debido a Argon2...\n")

    # Generar hashes para ambos usuarios
    hash_cliente = generar_hash(password)
    hash_operador = generar_hash(password)

    print("✓ Hashes generados exitosamente!\n")

    print("-" * 80)
    print("HASH PARA USUARIO CLIENTE (cliente@test.com):")
    print("-" * 80)
    print(hash_cliente)

    print("\n")
    print("-" * 80)
    print("HASH PARA USUARIO OPERADOR (operador@test.com):")
    print("-" * 80)
    print(hash_operador)

    print("\n")
    print("=" * 80)
    print("INSTRUCCIONES:")
    print("=" * 80)
    print("1. Copia los hashes generados arriba")
    print("2. Abre el archivo: tests/e2e/seed_test_data.sql")
    print("3. Reemplaza los PLACEHOLDER con los hashes correspondientes")
    print("4. Ejecuta el script SQL para crear los datos de prueba")
    print("=" * 80)

    # Generar también el SQL actualizado
    print("\n¿Quieres generar el SQL actualizado automáticamente? (s/n): ", end="")
    respuesta = input().strip().lower()

    if respuesta == 's':
        generar_sql_actualizado(hash_cliente, hash_operador)


def generar_sql_actualizado(hash_cliente: str, hash_operador: str):
    """Genera el archivo SQL con los hashes actualizados"""
    import os

    sql_path = os.path.join(os.path.dirname(__file__), "seed_test_data.sql")
    output_path = os.path.join(os.path.dirname(__file__), "seed_test_data_updated.sql")

    try:
        with open(sql_path, 'r') as f:
            contenido = f.read()

        # Reemplazar los placeholders
        contenido_actualizado = contenido

        # Primera aparición = cliente
        contenido_actualizado = contenido_actualizado.replace(
            "$argon2id$v=19$m=65536,t=3,p=4$PLACEHOLDER",
            hash_cliente,
            1
        )

        # Segunda aparición = operador
        contenido_actualizado = contenido_actualizado.replace(
            "$argon2id$v=19$m=65536,t=3,p=4$PLACEHOLDER",
            hash_operador,
            1
        )

        with open(output_path, 'w') as f:
            f.write(contenido_actualizado)

        print(f"\n✓ SQL actualizado generado en: {output_path}")
        print("\nAhora puedes ejecutar:")
        print(f"psql -h localhost -p 5480 -U postgres -d medisupply -f {output_path}")

    except Exception as e:
        print(f"\n✗ Error al generar SQL actualizado: {e}")


if __name__ == "__main__":
    main()
