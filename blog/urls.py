from django.urls import path
from .views import BlogListView, BlogDetailView, by_tag, by_category

app_name = 'blog'

urlpatterns = [
    path('', BlogListView.as_view(), name='blog'),
    path('<int:pk>', BlogDetailView.as_view(), name='detail'),
    path('tag=<slug:tag>', by_tag, name='by_tag'),
    path('category=<slug:category>', by_category, name='by_category'),
]