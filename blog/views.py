from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Post, Category
from taggit.models import Tag
from .forms import CommentForm
from django.views.generic import ListView, DetailView


class BlogListView(ListView):
    model = Post
    template_name = 'blog/list.html'

    def get_queryset(self):
        category_pk = self.request.GET.get('category', None)
        tag_slug = self.request.GET.get('tag', None)

        if category_pk:
            return Post.objects.filter(category__pk=category_pk).order_by("title")
        elif tag_slug:
            return Post.objects.filter(tags__name__in=[tag_slug]).order_by("title")
            
        return Post.objects.order_by("title")

def blog_list(request):
    posts = Post.objects.all()

    search = request.GET.get('search')
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) | 
            Q(tags__name__icontains=search)
        ).distinct()

    paginator = Paginator(posts, 3)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    context = {'posts': posts}

    return render(request, 'blog/list.html', context)

class BlogDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'    

    def get_context_data(self, *args, **kwargs):
        context = super(BlogDetailView, self).get_context_data(**kwargs)
        context['form'] = CommentForm()        
        print(context)
        return context

    def post(self, *args, **kwargs):
        form = CommentForm(self.request.POST or None)
        if form.is_valid():
            comment = form.save(commit=False)
            self.object = self.get_object()
            post = self.object
            comment.post = post

            if self.request.user.is_authenticated:
                comment.author = self.request.user
            else:
                name = form.cleaned_data.get('name')
                email = form.cleaned_data.get('email')
                website = form.cleaned_data.get('website')
                comment.name = name
                comment.email = email
                comment.website = website
                
            comment.save()
            context = super().get_context_data(**kwargs)
            return self.render_to_response(context=context)
  

def blog_detail(request, id):
    post = Post.objects.get(id=id)
    categories = Category.objects.all()
    tags = Tag.objects.all()

    form = CommentForm()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()

    context = {'post': post, 'categories': categories, 'tags': tags, 'form': form}
    return render(request, 'blog/detail.html', context)

def by_tag(request, tag):
    posts = Post.objects.filter(tags__name__in=[tag])
    context = {'posts': posts}

    return render(request, 'blog/list.html', context)

def by_category(request, category):
    posts = Post.objects.filter(category__name=category)
    context = {'posts': posts}

    return render(request, 'blog/list.html', context)