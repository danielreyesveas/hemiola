from django.urls import path
from .views import BlogListView, BlogDetailView, by_tag, by_category

app_name = 'blog'

urlpatterns = [
    path('', BlogListView.as_view(), name='list'),
    path('<int:pk>', BlogDetailView.as_view(), name='detail'),
]