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

@register.filter
def divisor(value, arg):
    """將值除以參數"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """將值乘以參數"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0

@register.filter
def subtract(value, arg):
    """從值中減去參數"""
    try:
        return float(value) - float(arg)
    except ValueError:
        return 0

@register.filter
def percentage(value, arg):
    """計算百分比"""
    try:
        return (float(value) / float(arg)) * 100
    except (ValueError, ZeroDivisionError):
        return 0