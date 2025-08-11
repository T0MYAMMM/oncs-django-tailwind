from functools import wraps
from typing import Callable, Optional

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse


def feature_required(flag_name: str, group_name: Optional[str] = None) -> Callable:
    """
    Decorator to enforce feature visibility based on SHOW_APP_CONFIG.

    - If group_name is provided, it will be checked first (e.g., 'SHOW_CRUD').
    - Then the specific flag_name is checked (e.g., 'SHOW_CRUD_USERS').
    - If either is False (or missing -> treated as False), a 404 is raised.
    """

    # Infer a default group when not provided
    inferred_group = None
    if group_name is None and flag_name.startswith("SHOW_CRUD"):
        inferred_group = "SHOW_CRUD"

    effective_group = group_name or inferred_group

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            config = getattr(settings, "SHOW_APP_CONFIG", {}) or {}

            if effective_group is not None and not bool(config.get(effective_group, False)):
                raise Http404()

            if not bool(config.get(flag_name, False)):
                raise Http404()

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


