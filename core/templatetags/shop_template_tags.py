from django import template
from core.models import Brand, Category
from taggit.models import Tag
from django.db.models import Q, Count

register = template.Library()

@register.simple_tag
def get_categories_total():
    qs = Category.objects.filter(active=True).annotate(
            items_count=(Count('items'))
        ).order_by('name').values('name', 'items_count', 'slug')
    if qs.exists():
        return qs
    return []

@register.simple_tag
def get_brands_total():
    qs = Brand.objects.filter(active=True).annotate(
            items_count=(Count('items'))
        ).order_by('name').values('name', 'items_count', 'slug')
    if qs.exists():
        return qs
    return []

@register.simple_tag
def get_popular_tags():
    qs = Tag.objects.all().order_by('name')[:6]
    if qs.exists():
        return qs
    return []

@register.simple_tag
def get_related_items(item):
    if item:
        return item.related_items()
    return []