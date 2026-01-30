from src.models import orm_models as _orm_models

_public = getattr(_orm_models, "__all__", None)
if _public is None:
    _public = [n for n in dir(_orm_models) if not n.startswith("_")]

__all__ = list(_public)
globals().update({name: getattr(_orm_models, name) for name in __all__})
