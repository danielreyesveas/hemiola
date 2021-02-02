from django.db.models.signals import post_save
from django.db import models
from django.conf import settings
from django.shortcuts import reverse
from django_countries.fields import CountryField
from taggit.managers import TaggableManager
from django.utils import timezone
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.timezone import now
from django.utils.text import slugify

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger')
)

ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping')
)


class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="customer")
    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.CharField(max_length=200, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)
    device = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        if self.user:
            name = self.user
        else:
            name = self.device
        return str(name)

def get_upload_path(instance, filename):
    model = instance.album.model.__class__._meta
    name = model.verbose_name_plural.replace(' ', '_')
    return f'{name}/images/{filename}'

class ImageAlbum(models.Model):
    def default(self):
        return self.images.filter(default=True).first()
    def thumbnails(self):
        return self.images.filter(width__lt=100, length__lt=100)

    def __str__(self):
        if hasattr(self, 'model'):
            return f"{self.model}'s album"
        else:
            return f"Empty album #{self.id}"
            

class Image(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to=get_upload_path)
    default = models.BooleanField(default=False)
    width = models.FloatField(default=100)
    length = models.FloatField(default=100)
    album = models.ForeignKey(ImageAlbum, related_name='images', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} from {self.album}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.CharField(max_length=1000, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'

class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.CharField(max_length=1000, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Item(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True, related_name='items')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, blank=True, null=True, related_name='items')
    label = models.CharField(choices=LABEL_CHOICES, max_length=1, default='P')
    slug = models.SlugField(max_length=50, blank=True, null=True)
    description = models.TextField(default="Description")
    image = models.ImageField(default="default.jpg")
    album = models.OneToOneField(ImageAlbum, related_name='model', on_delete=models.CASCADE, null=True, blank=True)
    tags = TaggableManager(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        super(Item, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("core:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })

    def get_antiquity(self):
        return int((timezone.now() - self.created_at).days)

    def get_label(self):
        if self.get_antiquity() < 30:
            return "Nuevo"
        elif self.discount_price:
            return "Rebaja"
        return None

    def get_label_class(self):
        if self.get_antiquity() < 30:
            return "new"
        elif self.discount_price:
            return "sale"
        return None

    def related_items(self):
        tags_ids = list(self.tags.values_list('pk', flat=True))
        items = Item.objects.filter(tags__pk__in=(tags_ids)).exclude(pk=self.pk).order_by('-created_at').distinct()[:4]        
        if items.count() < 4:
            limit = (4 - items.count())
            extra = self.category.items.exclude(pk=self.pk).order_by('-created_at')[:limit]
            items = items | extra

        return items

class Review(models.Model):
    author = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=50, blank=True, null=True)
    website = models.CharField(max_length=50, blank=True, null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reviews')
    content = models.TextField()
    stars = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def author_name(self):
        return self.author or self.name

    @property
    def author_image(self):
        image_url = static('img/default.png')
        if self.author and self.author.user and self.author.user.profile:
            image_url = self.author.user.profile.image.url
        return image_url

    def __str__(self):
        return "Review by {}".format(self.author_name)


class OrderItem(models.Model):
    customer = models.ForeignKey(Customer,
                             on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_total_discount_item_price(self):
        return self.quantity * self.item.discount_price

    def get_ammount_saved(self):
        return self.get_total_item_price() - self.get_total_discount_item_price()

    def get_final_price(self):
        if self.item.discount_price:
            return self.get_total_discount_item_price()
        else:
            return self.get_total_item_price()


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField(default=now)
    ordered = models.BooleanField(default=False)
    billing_address = models.ForeignKey('Address', related_name='billing_address', on_delete=models.SET_NULL, blank=True, null=True)
    shipping_address = models.ForeignKey('Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer}'s' order"

    def get_sub_total(self):
        sub_total = 0
        for order_item in self.items.all():
            sub_total += order_item.get_final_price()

        return sub_total

    def get_total(self):
        total = self.get_sub_total()
        if self.coupon and total > 0:
            total -= self.coupon.amount
        return total


class Address(models.Model):
    customer = models.ForeignKey(Customer,
                             on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer}'s' address"

    class Meta:
        verbose_name_plural = 'Addresses'


class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=50)
    customer = models.ForeignKey(Customer,
                             on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer}'s' payment"


class Coupon(models.Model):
    code = models.CharField(max_length=15)
    amount = models.FloatField(default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code


class Carrousel(models.Model):
    image = models.ImageField()
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=1000, null=True, blank=True)
    link = models.CharField(max_length=200, null=True, blank=True)
    link_title = models.CharField(max_length=100, null=True, blank=True)
    active = models.BooleanField(default=True)
    order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.title


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pk}"


def customer_receiver(sender, instance, created, *args, **kwargs):
    if created:
        customer = Customer.objects.create(user=instance)

def image_album_receiver(sender, instance, created, *args, **kwargs):
    if created:
        imageAlbum = ImageAlbum.objects.create()
        instance.album = imageAlbum
        instance.save()


post_save.connect(customer_receiver, sender=settings.AUTH_USER_MODEL)
post_save.connect(image_album_receiver, sender=Item)
