from django import template

register = template.Library()

@register.filter
def getattr(obj, attr):
    """
    Template filter to get an attribute of an object
    Usage: {{ object|getattr:"attribute_name" }}
    """
    try:
        # Handle nested attributes like "portal.name"
        if '.' in attr:
            value = obj
            for part in attr.split('.'):
                value = getattr(value, part)
            return value
        else:
            return getattr(obj, attr)
    except (AttributeError, TypeError):
        return ''
