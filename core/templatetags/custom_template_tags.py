from urllib.parse import urlencode
from django import template
from babel.numbers import format_currency
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.text import normalize_newlines
from django.utils.safestring import SafeData, mark_safe
from django.utils.html import escape

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):

    dict_ = request.GET.copy()

    dict_[field] = value

    return dict_.urlencode()

@register.filter
def currency(value):
    formated = format_currency(value, 'EUR', locale='es_ES')
    return formated.replace(",00", "")
    
@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def linebreaksbr(value, autoescape=True):
    """
    Convert all newlines in a piece of plain text to HTML line breaks
    (``<br>``).
    """
    autoescape = autoescape and not isinstance(value, SafeData)
    value = normalize_newlines(value)
    if autoescape:
        value = escape(value)
    return mark_safe(value.replace('\n', '<br>'))