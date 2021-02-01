from urllib.parse import urlencode
from django import template
from babel.numbers import format_currency

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
    

   
