"""Auditoría de solo inserción (D19, R6.6).

Un REVOKE no basta: el dueño de la tabla conserva sus permisos. Un trigger rechaza UPDATE,
DELETE y TRUNCATE para cualquier usuario; quitarlo exige cambiar la estructura de la base.

Revisión: 473ddc01e959
Creada: 2026-11-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "473ddc01e959"
down_revision: str | Sequence[str] | None = "30a7367590f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION auditoria_solo_insercion() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'La auditoría solo admite inserciones (%).', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER auditoria_sin_cambios BEFORE UPDATE OR DELETE ON auditoria "
        "FOR EACH ROW EXECUTE FUNCTION auditoria_solo_insercion()"
    )
    op.execute(
        "CREATE TRIGGER auditoria_sin_truncate BEFORE TRUNCATE ON auditoria "
        "FOR EACH STATEMENT EXECUTE FUNCTION auditoria_solo_insercion()"
    )
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON auditoria FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP TRIGGER auditoria_sin_truncate ON auditoria")
    op.execute("DROP TRIGGER auditoria_sin_cambios ON auditoria")
    op.execute("DROP FUNCTION auditoria_solo_insercion()")
