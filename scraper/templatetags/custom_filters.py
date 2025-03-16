from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """從字典中獲取值，用於在模板中訪問嵌套字典"""
    if dictionary is None:
        return None

    if isinstance(dictionary, dict):
        return dictionary.get(key)

    try:
        return getattr(dictionary, key)
    except (AttributeError, TypeError):
        return None