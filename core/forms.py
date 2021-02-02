from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

PAYMENT_CHOICES = (
    ('P', 'PayPal'),
    ('S', 'Credit Card')
)


class CheckoutForm(forms.Form):
    shipping_first_name = forms.CharField(required=False)
    shipping_last_name = forms.CharField(required=False)
    shipping_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Dirección',        
    }))
    shipping_address2 = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartamento, habitación, etc (opcional)',        
    }))
    shipping_country = CountryField(blank_label='(Selecciona tu país)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100'
    }))
    shipping_city = forms.CharField(required=False)
    shipping_zip = forms.CharField(required=False)
    shipping_phone = forms.CharField(required=False)

    billing_first_name = forms.CharField(required=False)
    billing_last_name = forms.CharField(required=False)
    billing_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Dirección',        
    }))
    billing_address2 = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartamento, habitación, etc (opcional)',        
    }))
    billing_country = CountryField(blank_label='(Selecciona tu país)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100'
        }))
    billing_city = forms.CharField(required=False)
    billing_zip = forms.CharField(required=False)
    billing_phone = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(required=False)
    set_default_shipping = forms.BooleanField(required=False)
    use_default_shipping = forms.BooleanField(required=False)

    set_default_billing = forms.BooleanField(required=False)
    use_default_billing = forms.BooleanField(required=False)

    payment_option = forms.ChoiceField(required=False,
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Código',        
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()


class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)
