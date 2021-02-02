from django.contrib import admin
from .models import Item, Brand, OrderItem, Order, Payment, Coupon, Carrousel, Category, Refund, Address, Customer, Image, ImageAlbum, Review


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


make_refund_accepted.short_description = 'Update orders to refund granted'

class OrderAdmin(admin.ModelAdmin):
    list_display = ['customer', 'ref_code', 'ordered', 'being_delivered',
                    'received', 'refund_requested', 'refund_granted', 'billing_address', 'shipping_address', 'payment', 'coupon']
    list_display_links = ['customer', 'billing_address',
                          'shipping_address', 'payment', 'coupon']
    list_filter = ['customer', 'ordered', 'being_delivered',
                   'received', 'refund_requested', 'refund_granted']
    #search_fields = ['customer', 'ref_code']
    actions = [make_refund_accepted]


class AddressAdmin(admin.ModelAdmin):
    list_display = ['customer', 'street_address', 'apartment_address',
                    'country', 'zip', 'address_type', 'default']
    list_filter = ['customer', 'address_type', 'default', 'country']
    #search_fields = ['customer', 'street_address', 'apartment_address', 'zip']


class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'category', 'brand', 'tag_list', 'slug']
    list_filter = ['category', 'brand']
    list_display_links = ['title', 'category', 'brand']
    search_fields = ['title', 'subtitle', 'slug']
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')
    
    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'active']
    search_fields = ['name']

class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'active']
    search_fields = ['name']


admin.site.register(Item, ItemAdmin)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Carrousel)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Refund)
admin.site.register(Address, AddressAdmin)
admin.site.register(Customer)
admin.site.register(ImageAlbum)
admin.site.register(Image)
admin.site.register(Review)
