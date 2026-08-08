# Importa aquí Base y todos los modelos para que Alembic los detecte
# al generar migraciones automáticas (target_metadata en alembic/env.py).
from app.db.base_class import Base  # noqa: F401
from app.models.asiento import Asiento, MovimientoContable  # noqa: F401
from app.models.cuenta import Cuenta  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
