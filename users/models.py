from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.db.models import Count, Q


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    is_public = models.BooleanField(default=True)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')    

    def __str__(self):
        return f'{self.user.username}'

    def bookmark(self, post):
        return self.user.bookmarks.filter(post=post).exists()

    def get_posts(self):
        return self.user.posts.filter(is_active=True).count()

    def get_likes(self):
        return self.user.posts.aggregate(count=Count('votes', filter=Q(votes__like=True)))['count']

    def get_comments(self):
        return self.user.posts.filter(is_active=True).aggregate(count=Count('comments'))['count']


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)
        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)