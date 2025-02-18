from django import template

register = template.Library()

@register.filter
def split(value, key):
    """
    Returns the string split by key.
    """
    return value.split(key)

@register.filter
def get_file_extension(filename):
    """
    Returns the file extension from a filename.
    """
    try:
        return filename.split('.')[-1].upper()
    except (AttributeError, IndexError):
        return ''