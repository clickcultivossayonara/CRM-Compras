"""Entorno de Alembic: usa el URL de ``config.attributes["url"]`` o, si no, DATABASE_URL."""

from alembic import context
from sqlalchemy import create_engine, pool

from crm_compras.datos.conexion import url_desde_entorno, url_sqlalchemy
from crm_compras.datos.modelos import Base

url_recibida = context.config.attributes.get("url")
url = url_sqlalchemy(str(url_recibida)) if url_recibida else url_desde_entorno()


def migrar_sin_conexion() -> None:
    """Genera el SQL de las migraciones sin conectarse (``alembic upgrade --sql``)."""
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def migrar_con_conexion() -> None:
    motor = create_engine(url, poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    migrar_sin_conexion()
else:
    migrar_con_conexion()
