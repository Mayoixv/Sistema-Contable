import csv
import io
from decimal import Decimal
from typing import Any

from fastapi import Response


def _celda(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return str(valor)
    if valor is None:
        return ""
    return valor


def filas_a_csv(fieldnames: list[str], filas: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for fila in filas:
        writer.writerow({campo: _celda(fila.get(campo)) for campo in fieldnames})
    return buffer.getvalue()


def csv_response(contenido: str, *, nombre_archivo: str) -> Response:
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
