"""Modelo inicial de la base propia (diseño §3) y unidades con decimales iniciales (R6.7).

Revisión: 30a7367590f8
Creada: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "30a7367590f8"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lista inicial de R6.7, fija en la migración: luego la mantiene el Administrador.
UNIDADES_DECIMALES_INICIALES = ("CC", "GL", "GR", "KL", "LB", "LT", "MT")


def upgrade() -> None:
    op.create_table(
        "articulo",
        sa.Column("codigo", sa.String(length=6), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("unidad", sa.String(length=10), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("sincronizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("codigo ~ '^[0-9]{6}$'", name=op.f("ck_articulo_codigo")),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_articulo")),
    )
    op.create_table(
        "centro_costo",
        sa.Column("codigo", sa.String(length=8), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("sincronizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "codigo ~ '^[0-9]{3}-[0-9]{2}-[0-9]$'", name=op.f("ck_centro_costo_codigo")
        ),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_centro_costo")),
    )
    op.create_table(
        "sincronizacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column(
            "recibido_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("registros", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('articulos', 'centros', 'precios')", name=op.f("ck_sincronizacion_tipo")
        ),
        sa.CheckConstraint("registros >= 0", name=op.f("ck_sincronizacion_registros")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sincronizacion")),
    )
    unidad_decimal = op.create_table(
        "unidad_decimal",
        sa.Column("unidad", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("unidad", name=op.f("pk_unidad_decimal")),
    )
    op.bulk_insert(unidad_decimal, [{"unidad": u} for u in UNIDADES_DECIMALES_INICIALES])
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("hash_clave", sa.Text(), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint(
            "rol IN ('jefe', 'comprador', 'gerente', 'administrador')", name=op.f("ck_usuario_rol")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("usuario", name=op.f("uq_usuario_usuario")),
    )
    op.create_table(
        "anio_presupuesto",
        sa.Column("anio", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("cargado_por", sa.Integer(), nullable=False),
        sa.Column(
            "cargado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archivo", sa.String(length=255), nullable=False),
        sa.CheckConstraint("anio BETWEEN 2000 AND 2100", name=op.f("ck_anio_presupuesto_anio")),
        sa.ForeignKeyConstraint(
            ["cargado_por"], ["usuario.id"], name=op.f("fk_anio_presupuesto_cargado_por_usuario")
        ),
        sa.PrimaryKeyConstraint("anio", name=op.f("pk_anio_presupuesto")),
    )
    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column(
            "fecha", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("entidad", sa.String(length=40), nullable=False),
        sa.Column("entidad_id", sa.String(length=40), nullable=False),
        sa.Column("accion", sa.String(length=40), nullable=False),
        sa.Column("antes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("despues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_auditoria_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria")),
    )
    op.create_table(
        "jefe_centro",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("centro_codigo", sa.String(length=8), nullable=False),
        sa.ForeignKeyConstraint(
            ["centro_codigo"],
            ["centro_costo.codigo"],
            name=op.f("fk_jefe_centro_centro_codigo_centro_costo"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_jefe_centro_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("usuario_id", "centro_codigo", name=op.f("pk_jefe_centro")),
    )
    op.create_table(
        "lote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("generado_por", sa.Integer(), nullable=False),
        sa.Column(
            "generado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["generado_por"], ["usuario.id"], name=op.f("fk_lote_generado_por_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lote")),
    )
    op.create_table(
        "pedido",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jefe_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), server_default="borrador", nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("enviado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("justificacion_gerencia", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "estado IN ('borrador', 'enviado', 'pendiente_gerencia', 'aprobado', "
            "'rechazado', 'exportado', 'anulado')",
            name=op.f("ck_pedido_estado"),
        ),
        sa.ForeignKeyConstraint(
            ["jefe_id"], ["usuario.id"], name=op.f("fk_pedido_jefe_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pedido")),
    )
    op.create_index(op.f("ix_pedido_jefe_id"), "pedido", ["jefe_id"], unique=False)
    op.create_table(
        "precio",
        sa.Column("articulo", sa.String(length=6), nullable=False),
        sa.Column("precio_unitario", sa.BigInteger(), nullable=False),
        sa.Column("fecha_compra", sa.Date(), nullable=False),
        sa.Column("orden_compra", sa.String(length=30), nullable=False),
        sa.CheckConstraint("precio_unitario >= 0", name=op.f("ck_precio_precio_unitario")),
        sa.ForeignKeyConstraint(
            ["articulo"], ["articulo.codigo"], name=op.f("fk_precio_articulo_articulo")
        ),
        sa.PrimaryKeyConstraint("articulo", name=op.f("pk_precio")),
    )
    op.create_table(
        "prohibido",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("articulo_codigo", sa.String(length=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["articulo_codigo"],
            ["articulo.codigo"],
            name=op.f("fk_prohibido_articulo_codigo_articulo"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_prohibido_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("usuario_id", "articulo_codigo", name=op.f("pk_prohibido")),
    )
    op.create_table(
        "partida",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("anio", sa.SmallInteger(), nullable=False),
        sa.Column("rubro", sa.String(length=120), nullable=False),
        sa.Column("area", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["anio"], ["anio_presupuesto.anio"], name=op.f("fk_partida_anio_anio_presupuesto")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partida")),
        sa.UniqueConstraint("anio", "rubro", "area", name=op.f("uq_partida_anio_rubro_area")),
    )
    op.create_table(
        "asignacion_mensual",
        sa.Column("partida_id", sa.Integer(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("valor", sa.BigInteger(), nullable=False),
        sa.Column("semanas", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("mes BETWEEN 1 AND 12", name=op.f("ck_asignacion_mensual_mes")),
        sa.CheckConstraint("semanas IN (4, 5)", name=op.f("ck_asignacion_mensual_semanas")),
        sa.CheckConstraint("valor >= 0", name=op.f("ck_asignacion_mensual_valor")),
        sa.ForeignKeyConstraint(
            ["partida_id"],
            ["partida.id"],
            name=op.f("fk_asignacion_mensual_partida_id_partida"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("partida_id", "mes", name=op.f("pk_asignacion_mensual")),
    )
    op.create_table(
        "jefe_partida",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("partida_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["partida_id"], ["partida.id"], name=op.f("fk_jefe_partida_partida_id_partida")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_jefe_partida_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("usuario_id", "partida_id", name=op.f("pk_jefe_partida")),
    )
    op.create_table(
        "linea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("articulo", sa.String(length=6), nullable=False),
        sa.Column("centro_costo", sa.String(length=8), nullable=False),
        sa.Column("partida_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("fecha_requerida", sa.Date(), nullable=False),
        sa.Column("comentario", sa.Text(), server_default="", nullable=False),
        sa.Column("precio_congelado", sa.BigInteger(), nullable=True),
        sa.Column("valor", sa.BigInteger(), nullable=True),
        sa.Column("bodega", sa.SmallInteger(), nullable=True),
        sa.Column("lote_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("bodega IN (1, 2, 5)", name=op.f("ck_linea_bodega")),
        sa.CheckConstraint("cantidad > 0", name=op.f("ck_linea_cantidad")),
        sa.CheckConstraint("precio_congelado >= 0", name=op.f("ck_linea_precio_congelado")),
        sa.CheckConstraint("valor >= 0", name=op.f("ck_linea_valor")),
        sa.ForeignKeyConstraint(
            ["articulo"], ["articulo.codigo"], name=op.f("fk_linea_articulo_articulo")
        ),
        sa.ForeignKeyConstraint(
            ["centro_costo"],
            ["centro_costo.codigo"],
            name=op.f("fk_linea_centro_costo_centro_costo"),
        ),
        sa.ForeignKeyConstraint(["lote_id"], ["lote.id"], name=op.f("fk_linea_lote_id_lote")),
        sa.ForeignKeyConstraint(
            ["partida_id"], ["partida.id"], name=op.f("fk_linea_partida_id_partida")
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["pedido.id"], name=op.f("fk_linea_pedido_id_pedido"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_linea")),
        sa.UniqueConstraint(
            "pedido_id",
            "articulo",
            "centro_costo",
            name=op.f("uq_linea_pedido_id_articulo_centro_costo"),
        ),
    )
    op.create_index(op.f("ix_linea_lote_id"), "linea", ["lote_id"], unique=False)
    op.create_index(op.f("ix_linea_partida_id"), "linea", ["partida_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_linea_partida_id"), table_name="linea")
    op.drop_index(op.f("ix_linea_lote_id"), table_name="linea")
    op.drop_table("linea")
    op.drop_table("jefe_partida")
    op.drop_table("asignacion_mensual")
    op.drop_table("partida")
    op.drop_table("prohibido")
    op.drop_table("precio")
    op.drop_index(op.f("ix_pedido_jefe_id"), table_name="pedido")
    op.drop_table("pedido")
    op.drop_table("lote")
    op.drop_table("jefe_centro")
    op.drop_table("auditoria")
    op.drop_table("anio_presupuesto")
    op.drop_table("usuario")
    op.drop_table("unidad_decimal")
    op.drop_table("sincronizacion")
    op.drop_table("centro_costo")
    op.drop_table("articulo")
