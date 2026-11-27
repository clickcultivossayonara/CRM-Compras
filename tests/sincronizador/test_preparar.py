"""T3.2 · Filas de Softland convertidas al contrato de la API, con descartes reportados."""

from datetime import date, datetime
from decimal import Decimal

from sincronizador.preparar import preparar_articulos, preparar_centros, preparar_precios


def test_articulos() -> None:
    filas: list[dict[str, object]] = [
        {"codigo": "020093  ", "descripcion": " A ", "unidad": "und", "activo": "S"},
        {"codigo": "000001", "descripcion": "B", "unidad": "LT", "activo": "N"},
        {"codigo": "12345", "descripcion": "C", "unidad": "UND", "activo": "S"},
        {"codigo": "000002", "descripcion": None, "unidad": "UND", "activo": None},
        {"codigo": "000001", "descripcion": "B otra vez", "unidad": "LT", "activo": "S"},
    ]
    articulos, descartes = preparar_articulos(filas)
    assert [(a.codigo, a.descripcion, a.unidad, a.activo) for a in articulos] == [
        ("020093", "A", "UND", True),
        ("000001", "B", "LT", False),
    ]
    assert len(descartes) == 3
    assert descartes[0].startswith("Artículo '12345': codigo:")
    assert descartes[1].startswith("Artículo '000002': descripcion:")
    assert descartes[2] == "Artículo '000001': repetido"


def test_descripcion_larga_se_recorta() -> None:
    articulos, _ = preparar_articulos(
        [{"codigo": "020093", "descripcion": "X" * 600, "unidad": "UND", "activo": "S"}]
    )
    assert len(articulos[0].descripcion) == 500


def test_centros() -> None:
    filas = [
        {"codigo": "513-01-2", "descripcion": "CENTRO", "acepta_datos": "S"},
        {"codigo": "100-01-1", "descripcion": "OTRO", "acepta_datos": "N"},
        {"codigo": "51301", "descripcion": "MAL", "acepta_datos": "S"},
        {"codigo": "513-01-2", "descripcion": "REPETIDO", "acepta_datos": "S"},
    ]
    centros, descartes = preparar_centros(filas)
    assert [(c.codigo, c.activo) for c in centros] == [("513-01-2", True), ("100-01-1", False)]
    assert descartes[0].startswith("Centro de costo '51301': codigo:")
    assert descartes[1] == "Centro de costo '513-01-2': repetido"


def precio(articulo: str, valor: object, comentario: object = None) -> dict[str, object]:
    return {
        "articulo": articulo,
        "precio_unitario": valor,
        "comentario": comentario,
        "fecha_compra": datetime(2026, 10, 20, 8, 30),
        "orden_compra": " OC-1 ",
    }


def test_precios_normalizados_y_descartes() -> None:
    filas = [
        precio("020093", Decimal("1500.5")),
        precio("020215", Decimal("24000"), "CAJA X 24"),
        precio("999999", Decimal("10")),
        precio("020215", Decimal("1"), "x 2"),
        precio("000005", None),
        precio("000006", "no es número"),
        precio("000007", Decimal("NaN")),
    ]
    catalogo = {"020093", "020215", "000005", "000006", "000007"}
    precios, descartes = preparar_precios(filas, catalogo)
    assert [(p.articulo, p.precio_unitario, p.fecha_compra, p.orden_compra) for p in precios] == [
        ("020093", 1501, date(2026, 10, 20), "OC-1"),
        ("020215", 1000, date(2026, 10, 20), "OC-1"),
    ]
    assert descartes == [
        "Precio de '999999': el artículo no está en el catálogo sincronizado",
        "Precio de '020215': repetido",
        "Precio de '000005': precio o factor del comentario no válido",
        "Precio de '000006': precio o factor del comentario no válido",
        "Precio de '000007': precio o factor del comentario no válido",
    ]


def test_factor_invalido_del_020215_se_descarta() -> None:
    precios, descartes = preparar_precios([precio("020215", Decimal("24000"), "x 0")], {"020215"})
    assert precios == []
    assert descartes == ["Precio de '020215': precio o factor del comentario no válido"]


def test_fecha_sin_hora_y_orden_vacia() -> None:
    fila = {**precio("020093", Decimal("10")), "fecha_compra": date(2026, 1, 2), "orden_compra": ""}
    precios, descartes = preparar_precios([fila], {"020093"})
    assert precios == []
    assert descartes[0].startswith("Precio de '020093': orden_compra:")
