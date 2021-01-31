from django.db import models
from django.contrib.auth.models import User
from taggit.managers import TaggableManager
from django.contrib.staticfiles.templatetags.staticfiles import static

class Post(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    list_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    detail_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey('Category', null=True, on_delete=models.SET_NULL)
    # tags = 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = TaggableManager(blank=True)

    @property
    def author_image(self):
        image_url = static('img/default.png')
        if self.author and self.author.profile and self.author.profile.image:
            image_url = self.author.profile.image.url
        return image_url

    @property
    def list_image_url(self):
        image_url = static('img/list-default.jpg')
        if self.list_image:
            image_url = self.list_image.url
        return image_url

    @property
    def detail_image_url(self):
        image_url = static('img/detail-default.jpg')
        if self.detail_image:
            image_url = self.detail_image.url
        return image_url        

    def __str__(self):
        return self.title

class Category(models.Model):
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=50, blank=True, null=True)
    website = models.CharField(max_length=50, blank=True, null=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def author_name(self):
        return self.author or self.name

    @property
    def author_image(self):
        image_url = static('img/default.png')
        if self.author and self.author.profile and self.author.profile.image:
            image_url = self.author.profile.image.url
        return image_url

    def __str__(self):
        return "Comment by {}".format(self.author)