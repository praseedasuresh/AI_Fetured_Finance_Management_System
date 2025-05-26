from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def replace_underscore(value):
    """Replace underscores with spaces in a string"""
    return value.replace('_', ' ')

@register.filter
def format_currency(value):
    """Format a number as currency"""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return value

@register.filter
def format_percentage(value):
    """Format a number as percentage"""
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return value
