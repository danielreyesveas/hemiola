from django import template
from core.models import Order

register = template.Library()

@register.simple_tag
def cart_item(user):
    cart = { 'count': 0, 'total': 0 }
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False)
        if qs.exists():
            cart['count'] = qs[0].items.count()             
            cart['total'] = qs[0].get_total()             
    return cart
