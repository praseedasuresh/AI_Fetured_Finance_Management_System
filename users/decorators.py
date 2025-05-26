from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from functools import wraps


def admin_required(view_func):
    """Decorator to restrict access to admin users only"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_admin:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You don't have permission to access this page.")
    return _wrapped_view


def finance_staff_required(view_func):
    """Decorator to restrict access to finance staff and admin users"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_admin or request.user.is_finance_staff):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You don't have permission to access this page.")
    return _wrapped_view


def faculty_required(view_func):
    """Decorator to restrict access to faculty, finance staff and admin users"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_admin or request.user.is_finance_staff or request.user.is_faculty):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You don't have permission to access this page.")
    return _wrapped_view


def student_required(view_func):
    """Decorator to restrict access to student users only"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_student:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You don't have permission to access this page.")
    return _wrapped_view
