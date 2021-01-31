from django.contrib import admin
from .models import Post, Category, Comment
from django_summernote.admin import SummernoteModelAdmin


class PostAdmin(SummernoteModelAdmin, admin.ModelAdmin):
    summernote_fields = ['content']
    list_display = ['title', 'author', 'category', 'created_at']
    list_filter = ['author__username', 'category', 'tags']
    search_fields = ['title', 'author__username', 'content']


admin.site.register(Post, PostAdmin)
admin.site.register(Category)
admin.site.register(Comment)