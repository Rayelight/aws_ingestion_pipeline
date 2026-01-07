from __future__ import annotations

from typing import Any, Dict


class TemplateError(ValueError):
    pass


def render_templates(template_map: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remplace "{var}" dans les strings à partir de values.
    Si la valeur n’existe pas => erreur (mieux pour éviter ingestion foireuse).
    """
    out: Dict[str, Any] = {}

    for k, v in template_map.items():
        if isinstance(v, str) and "{" in v and "}" in v:
            try:
                out[k] = v.format(**values)
            except KeyError as e:
                raise TemplateError(f"Missing template value for {k}: {e}") from e
        else:
            out[k] = v

    return out
