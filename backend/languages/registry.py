"""Language module registry - factory pattern for language support."""
from .base import LanguageModule

_MODULES: dict[str, LanguageModule] = {}


def register(module: LanguageModule) -> None:
    """Register a language module."""
    _MODULES[module.code] = module


def get_module(code: str) -> LanguageModule:
    """Get a language module by code."""
    if code not in _MODULES:
        available = ", ".join(_MODULES.keys()) or "none"
        raise ValueError(f"Language '{code}' not registered. Available: {available}")
    return _MODULES[code]


def list_languages() -> list[dict]:
    """List all registered languages."""
    return [{"code": m.code, "name": m.name, "nativeName": m.native_name} for m in _MODULES.values()]


def _auto_register() -> None:
    """Auto-register language modules on import."""
    # Import triggers registration
    from .russian import RussianModule  # noqa: F401
    register(RussianModule())


_auto_register()
