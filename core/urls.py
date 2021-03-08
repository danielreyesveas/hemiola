from django.urls import path
from .views import HomeView, ShopView, CheckoutView, OrderSummaryView, ItemDetailView, about, contact,add_to_cart, add_single_item_to_cart, \
     remove_from_cart, remove_single_item_from_cart, PaymentView, addCouponView, RequestRefundView, send_email, subscribe_newsletter

app_name = 'core'

urlpatterns = [
     path('', HomeView.as_view(), name='home'),
     path('shop/', ShopView.as_view(), name='shop'),
     path('product/<slug>/', ItemDetailView.as_view(), name='product'),

     path('add-single-item-to-cart/<slug>/', add_single_item_to_cart, name='add-single-item-to-cart'),
     path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
     path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
     path('remove-single-item-from-cart/<slug>/', remove_single_item_from_cart, name='remove-single-item-from-cart'),

     path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
     path('checkout/', CheckoutView.as_view(), name='checkout'),
     path('add-coupon/', addCouponView.as_view(), name='add-coupon'),
     path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
     path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    

     path('contact/', contact, name='contact'),
     path('send-email/', send_email, name='send_email'),
     path('subscribe-newsletter/', subscribe_newsletter, name='subscribe_newsletter'),
     path('about/', about, name='about'),
]
