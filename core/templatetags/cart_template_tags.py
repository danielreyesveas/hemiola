from django import template
from core.models import Category, Order, Customer

register = template.Library()

@register.simple_tag(takes_context=True)
def cart_item(context):
    cart = { 'count': 0, 'total': 0 }
    request = context['request']

    try:
        customer = request.user.customer
    except:
        device = request.COOKIES.get("device", False)
        if not device:
            return cart
        customer, created = Customer.objects.get_or_create(device=device)

    order, created = Order.objects.get_or_create(customer=customer, ordered=False)

    cart['count'] = order.items.count()             
    cart['total'] = order.get_total()

    return cart

@register.simple_tag
def get_categories():
    qs = Category.objects.filter(active=True).order_by('name')
    if qs.exists():
        return qs
    return []
