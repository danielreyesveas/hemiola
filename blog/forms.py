from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = [
            'name',
            'email',
            'website',
            'content'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Name'},),
            'email': forms.TextInput(attrs={'placeholder': 'Email'},),
            'website': forms.TextInput(attrs={'placeholder': 'Website'},),
            'content': forms.Textarea(attrs={'placeholder': 'Comment'},)
        }
    