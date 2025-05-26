from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Template tag to replace a parameter in the current URL.
    
    Usage:
    <a href="?{% url_replace request 'page' 1 %}">First Page</a>
    
    This will replace the 'page' parameter with '1' while preserving all other parameters.
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()
