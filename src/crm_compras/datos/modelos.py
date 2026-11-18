"""Modelos de la base propia (diseño §3).

Las reglas que la base puede garantizar van como restricciones: formatos de códigos, estados,
roles, rangos y unicidad. El dinero es BIGINT en pesos (D2) y la cantidad, Numeric(12,2) (D13).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from crm_compras.dominio.cargador import HOJAS
from crm_compras.dominio.pedido import Estado, Rol

# Nombres estables de restricciones para que Alembic genere migraciones reproducibles.
CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

ARTICULO_FORMATO = "^[0-9]{6}$"
CENTRO_COSTO_FORMATO = "^[0-9]{3}-[0-9]{2}-[0-9]$"
TIPOS_SINCRONIZACION = ("articulos", "centros", "precios")


def _en(columna: str, valores: Any) -> str:
    """Condición SQL ``columna IN (...)`` a partir de valores conocidos del dominio."""
    lista = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in valores)
    return f"{columna} IN ({lista})"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (CheckConstraint(_en("rol", [r.value for r in Rol]), name="rol"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    hash_clave: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Articulo(Base):
    __tablename__ = "articulo"
    __table_args__ = (CheckConstraint(f"codigo ~ '{ARTICULO_FORMATO}'", name="codigo"),)

    codigo: Mapped[str] = mapped_column(String(6), primary_key=True)
    descripcion: Mapped[str] = mapped_column(Text)
    unidad: Mapped[str] = mapped_column(String(10))
    activo: Mapped[bool] = mapped_column(Boolean)
    sincronizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CentroCosto(Base):
    __tablename__ = "centro_costo"
    __table_args__ = (CheckConstraint(f"codigo ~ '{CENTRO_COSTO_FORMATO}'", name="codigo"),)

    codigo: Mapped[str] = mapped_column(String(8), primary_key=True)
    descripcion: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean)
    sincronizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Precio(Base):
    """Precio de última compra, ya normalizado (regla del 020215)."""

    __tablename__ = "precio"
    __table_args__ = (CheckConstraint("precio_unitario >= 0", name="precio_unitario"),)

    articulo: Mapped[str] = mapped_column(ForeignKey("articulo.codigo"), primary_key=True)
    precio_unitario: Mapped[int] = mapped_column(BigInteger)
    fecha_compra: Mapped[date] = mapped_column(Date)
    orden_compra: Mapped[str] = mapped_column(String(30))


class UnidadDecimal(Base):
    __tablename__ = "unidad_decimal"

    unidad: Mapped[str] = mapped_column(String(10), primary_key=True)


class AnioPresupuesto(Base):
    __tablename__ = "anio_presupuesto"
    __table_args__ = (CheckConstraint("anio BETWEEN 2000 AND 2100", name="anio"),)

    anio: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    cargado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    cargado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archivo: Mapped[str] = mapped_column(String(255))


class Partida(Base):
    """Fila de detalle del Excel: rubro x área de un año (D7)."""

    __tablename__ = "partida"
    __table_args__ = (UniqueConstraint("anio", "rubro", "area"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(ForeignKey("anio_presupuesto.anio"))
    rubro: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(160))


class AsignacionMensual(Base):
    __tablename__ = "asignacion_mensual"
    __table_args__ = (
        CheckConstraint("mes BETWEEN 1 AND 12", name="mes"),
        CheckConstraint("valor >= 0", name="valor"),
        CheckConstraint("semanas IN (4, 5)", name="semanas"),
    )

    partida_id: Mapped[int] = mapped_column(
        ForeignKey("partida.id", ondelete="CASCADE"), primary_key=True
    )
    mes: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    valor: Mapped[int] = mapped_column(BigInteger)
    semanas: Mapped[int] = mapped_column(SmallInteger)


class JefePartida(Base):
    __tablename__ = "jefe_partida"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"), primary_key=True)


class JefeCentro(Base):
    __tablename__ = "jefe_centro"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), primary_key=True)
    centro_codigo: Mapped[str] = mapped_column(ForeignKey("centro_costo.codigo"), primary_key=True)


class Prohibido(Base):
    """Artículo prohibido de un jefe: sus líneas van a la bodega 5 (D14)."""

    __tablename__ = "prohibido"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), primary_key=True)
    articulo_codigo: Mapped[str] = mapped_column(ForeignKey("articulo.codigo"), primary_key=True)


class Pedido(Base):
    __tablename__ = "pedido"
    __table_args__ = (CheckConstraint(_en("estado", [e.value for e in Estado]), name="estado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    jefe_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), index=True)
    estado: Mapped[str] = mapped_column(String(20), server_default=Estado.BORRADOR.value)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    justificacion_gerencia: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str | None] = mapped_column(Text)


class Lote(Base):
    """Generación del cargador: sus líneas no pueden entrar en otro lote (D17)."""

    __tablename__ = "lote"

    id: Mapped[int] = mapped_column(primary_key=True)
    generado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Linea(Base):
    __tablename__ = "linea"
    __table_args__ = (
        # D15: el mismo artículo con el mismo centro de costo no se repite en un pedido.
        UniqueConstraint("pedido_id", "articulo", "centro_costo"),
        CheckConstraint("cantidad > 0", name="cantidad"),
        CheckConstraint("precio_congelado >= 0", name="precio_congelado"),
        CheckConstraint("valor >= 0", name="valor"),
        CheckConstraint(_en("bodega", sorted(HOJAS)), name="bodega"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedido.id", ondelete="CASCADE"))
    articulo: Mapped[str] = mapped_column(ForeignKey("articulo.codigo"))
    centro_costo: Mapped[str] = mapped_column(ForeignKey("centro_costo.codigo"))
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"), index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fecha_requerida: Mapped[date] = mapped_column(Date)
    comentario: Mapped[str] = mapped_column(Text, server_default="")
    precio_congelado: Mapped[int | None] = mapped_column(BigInteger)
    valor: Mapped[int | None] = mapped_column(BigInteger)
    bodega: Mapped[int | None] = mapped_column(SmallInteger)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote.id"), index=True)


class Auditoria(Base):
    """Registro de cambios; solo admite inserciones (D19, T2.2)."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(40))
    antes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    despues: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Sincronizacion(Base):
    __tablename__ = "sincronizacion"
    __table_args__ = (
        CheckConstraint(_en("tipo", TIPOS_SINCRONIZACION), name="tipo"),
        CheckConstraint("registros >= 0", name="registros"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))
    recibido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    registros: Mapped[int] = mapped_column(Integer)
