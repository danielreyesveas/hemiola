from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Category, Refund, Customer
from blog.models import Post
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm, ReviewForm
from django.http import HttpResponseRedirect, JsonResponse

import stripe
import random
import string
from django.db.models import Q

from .utils import api_response
import requests
import time
import json
from .constants import contact_template_slug, newsletter_template_slug, email_sender_url

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


class HomeView(ListView):
    model = Item
    template_name = 'home.html'
    object_list  = []

    def get_context_data(self, *args, **kwargs):
        self.context["posts"] = Post.objects.order_by('-created_at')[:3]
        return self.context
    
    def get_queryset(self):
        self.context = super(HomeView, self).get_context_data()
        queryset = super(HomeView, self).get_queryset()
        queryset = queryset.order_by('-created_at')[:12]
        self.context['object_list'] = queryset
        cat_ids = list(queryset.values('category__name', 'category__slug'))
        categories = []
        for cat in cat_ids:
            if cat not in categories:
                categories.append(cat)
        self.context['categories'] = categories

        return queryset

class ShopView(ListView):
    template_name = 'shop.html'
    paginate_by = 6

    def get_context_data(self, *args, **kwargs):
        context = super(ShopView, self).get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', "")
        context['category_slug'] = self.request.GET.get('category', None)
        context['brand_slug'] = self.request.GET.get('brand', None)
        context['tag_slug'] = self.request.GET.get('tag', None)

        return context


    def get_queryset(self):
        search = self.request.GET.get('search', None)
        category_slug = self.request.GET.get('category', None)
        brand_slug = self.request.GET.get('brand', None)
        tag_slug = self.request.GET.get('tag', None)
        if category_slug:
            return Item.objects.filter(category__slug=category_slug).order_by("title")
        elif brand_slug:
            return Item.objects.filter(brand__slug=brand_slug).order_by("title")
        elif tag_slug:
            return Item.objects.filter(tags__name__in=[tag_slug]).order_by("title")
        elif search:
            return Item.objects.filter(
                Q(title__icontains=search) | 
                Q(category__name__icontains=search) | 
                Q(brand__name__icontains=search) | 
                Q(tags__name__icontains=search)
            ).distinct().order_by("title")
        return Item.objects.order_by("title")

class PaymentView(View):
    def get(self, *args, **kwargs):
        try:
            customer = self.request.user.customer
        except:
            device = self.request.COOKIES["device"]
            customer, created = Customer.objects.get_or_create(device=device)

        order = Order.objects.get(customer=customer, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'key': settings.STRIPE_PUBLISHABLE_KEY
            }
            if customer.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    customer.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        try:
            customer = self.request.user.customer
        except:
            device = self.request.COOKIES["device"]
            customer, created = Customer.objects.get_or_create(device=device)

        order = Order.objects.get(customer=customer, ordered=False)
        form = PaymentForm(self.request.POST)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if customer.stripe_customer_id != '' and customer.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        customer.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    customer.stripe_customer_id = customer['id']
                    customer.one_click_purchasing = True
                    customer.save()

            amount = int(order.get_total() * 100)

            try:

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        customer=customer.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        source=token
                    )

                # create the payment
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # assign the payment to the order

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                messages.success(self.request, "Your order was successful!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")


class OrderSummaryView(View):
    def get(self, *args, **kwargs):
        try:
            try:
                customer = self.request.user.customer
            except:
                device = self.request.COOKIES["device"]
                customer, created = Customer.objects.get_or_create(device=device)

            order = Order.objects.get(customer=customer, ordered=False)
            couponForm = CouponForm()
            context = {'object': order, 'couponForm': couponForm}
            template_name = 'order_summary.html'
            return render(self.request, template_name, context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an active order.")
            return redirect("/")


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    # Cannot assign "<HttpResponseRedirect status_code=302, "text/html; charset=utf-8", url="/checkout/">": "Order.coupon" must be a "Coupon" instance.
    except ObjectDoesNotExist:
        return False

class addCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    customer=self.request.user.customer, ordered=False)
                coupon = get_coupon(self.request, code)
                if coupon:
                    order.coupon = coupon
                    order.save()
                else:
                    messages.info(self.request, "This coupon does not exist")
                    return redirect("core:order-summary")                    
                messages.success(self.request, "Succesfully added coupon!")
                return redirect("core:order-summary")

            except Order.DoesNotExist:
                messages.info(self.request, "You don't have an active order.")
                return redirect("core:order-summary")

# class addCouponView(View):
#     def post(self, *args, **kwargs):
#         form = CouponForm(self.request.POST or None)
#         if form.is_valid():
#             try:
#                 code = form.cleaned_data.get('code')
#                 order = Order.objects.get(
#                     user=self.request.user, ordered=False)
#                 coupon = get_coupon(self.request, code)
#                 order.coupon = coupon
#                 order.save()
#                 messages.success(self.request, "Succesfully added coupon!")
#                 return redirect("core:checkout")

#             except ObjectDoesNotExist:
#                 messages.info(self.request, "You don't have an active order.")
#                 return redirect("core:checkout")                


class ItemDetailView(DetailView):
    model = Item
    template_name = 'product.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ItemDetailView, self).get_context_data(**kwargs)
        context['form'] = ReviewForm()       
        return context

    def post(self, *args, **kwargs):
        form = ReviewForm(self.request.POST or None)
        if form.is_valid():
            review = form.save(commit=False)
            self.object = self.get_object()
            item = self.object
            review.item = item

            if self.request.user.is_authenticated:
                customer, created = Customer.objects.get_or_create(user=self.request.user)
                review.author = customer
            else:
                name = form.cleaned_data.get('name')
                email = form.cleaned_data.get('email')
                website = form.cleaned_data.get('website')
                review.name = name
                review.email = email
                review.website = website
                
            review.save()
            return HttpResponseRedirect(self.request.path_info)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            try:
                customer = self.request.user.customer
            except:
                device = self.request.COOKIES["device"]
                customer, created = Customer.objects.get_or_create(device=device)

            order = Order.objects.get(customer=customer, ordered=False)
            form = CheckoutForm()
            couponForm = CouponForm()
            context = {'form': form, 'order': order,
                       'couponForm': couponForm, 'DISPLAY_COUPON_FORM': True}

            shipping_address_qs = Address.objects.filter(
                customer=customer,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                customer=customer,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, 'checkout.html', context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You don't have an active order.")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            customer = self.request.user.customer
        except:
            device = self.request.COOKIES["device"]
            customer, created = Customer.objects.get_or_create(device=device)

        try:
            print(1234)
            order = Order.objects.get(customer=customer, ordered=False)
            print(12345)
            print(form.is_valid())
            if form.is_valid():
                print(123456)
                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                print(123)
                if use_default_shipping:
                    print("Using the default shipping address")
                    address_qs = Address.objects.filter(
                        customer=customer,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')
                    shipping_first_name = form.cleaned_data.get('shipping_first_name')
                    shipping_last_name = form.cleaned_data.get('shipping_last_name')
                    shipping_city = form.cleaned_data.get('shipping_city')
                    shipping_phone = form.cleaned_data.get('shipping_phone')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            customer=customer,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            first_name=shipping_first_name,
                            last_name=shipping_last_name,
                            city=shipping_city,
                            phone=shipping_phone,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")
                        return redirect('core:checkout')

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the default billing address")
                    address_qs = Address.objects.filter(
                        customer=customer,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')
                    billing_first_name = form.cleaned_data.get('billing_first_name')
                    billing_last_name = form.cleaned_data.get('billing_last_name')
                    billing_city = form.cleaned_data.get('billing_city')
                    billing_phone = form.cleaned_data.get('billing_phone')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            customer=customer,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            first_name=billing_first_name,
                            last_name=billing_last_name,
                            city=billing_city,
                            phone=billing_phone,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()
                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")
                        return redirect('core:checkout')

                # payment_option = form.cleaned_data.get('payment_option')
                payment_option = "S"
                print(payment_option)
                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')

        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an active order.")
            return redirect("core:order-summary")
        print(form.errors)
        messages.warning(self.request, "Failed Checkout.")
        return redirect('core:checkout')


def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    try:
        customer = request.user.customer
    except:
        device = request.COOKIES["device"]
        customer, created = Customer.objects.get_or_create(device=device)

    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        customer=customer,
        ordered=False
    )
    order_qs = Order.objects.filter(
        customer=customer,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # Check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:product", slug=slug)
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:product", slug=slug)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            customer=customer, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:product", slug=slug)


def remove_from_cart(request, slug):
    try:
        customer = request.user.customer
    except:
        device = request.COOKIES["device"]
        customer, created = Customer.objects.get_or_create(device=device)

    item = get_object_or_404(Item, slug=slug)

    order_qs = Order.objects.filter(
        customer=customer,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # Check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                customer=customer,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You don't have an active order.")
        return redirect("core:product", slug=slug)


def remove_single_item_from_cart(request, slug):
    try:
        customer = request.user.customer
    except:
        device = request.COOKIES["device"]
        customer, created = Customer.objects.get_or_create(device=device)

    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        customer=customer,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # Check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                customer=customer,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You don't have an active order.")
        return redirect("core:product", slug=slug)


def add_single_item_to_cart(request, slug):
    try:
        customer = request.user.customer
    except:
        device = request.COOKIES["device"]
        customer, created = Customer.objects.get_or_create(device=device)

    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        customer=customer,
        ordered=False
    )
    order_qs = Order.objects.filter(
        customer=customer,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # Check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            customer=customer, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")





class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {'form': form}

        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')

            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.success(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")

def contact(request):
    template_name = 'contact.html'
    return render(request, template_name)

def send_email(request):
    json_response = {'success': False}

    data = json.loads(request.body.decode("utf-8"))

    if('subject' not in data): 
        json_response['msg'] = 'El campo \'subject\' no puede estar vacío' 
        return api_response(json_response)
    elif('email' not in data): 
        json_response['msg'] = 'El campo \'email\' no puede estar vacío' 
        return api_response(json_response)
    elif('content' not in data): 
        json_response['msg'] = 'El campo \'content\' no puede estar vacío' 
        return api_response(json_response)

    name = data['name']
    email = data['email']
    subject = data['subject']
    content = data['content']

    attempt_num = 0
    while attempt_num < 1:       
        body = {'name': name, 'from': email, 'subject': subject, 'content': content, 'template_slug': contact_template_slug, 'type': 'contact'}
        response = requests.post(email_sender_url, data = json.dumps(body))
        if response.status_code == 200:
            data = response.json()
            return JsonResponse(data)
        else:
            attempt_num += 1
            time.sleep(5) 

    return JsonResponse(json_response)

def subscribe_newsletter(request):
    json_response = {'success': False}

    data = json.loads(request.body.decode("utf-8"))

    if('email' not in data): 
        json_response['msg'] = 'El campo \'email\' no puede estar vacío' 
        return api_response(json_response)
   
    email = data['email']    
   
    attempt_num = 0
    while attempt_num < 1:       
        body = {'from': email, 'template_slug': newsletter_template_slug, 'type': 'newsletter'}
        response = requests.post(email_sender_url, data = json.dumps(body))
        if response.status_code == 200:
            data = response.json()
            return JsonResponse(data)
        else:
            attempt_num += 1
            time.sleep(5) 

    return JsonResponse(json_response)

def about(request):
    template_name = 'about.html'
    return render(request, template_name)