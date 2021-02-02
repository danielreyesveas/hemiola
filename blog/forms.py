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
            'name': forms.TextInput(attrs={'placeholder': 'Nombre'},),
            'email': forms.TextInput(attrs={'placeholder': 'Email'},),
            'website': forms.TextInput(attrs={'placeholder': 'Sitio web'},),
            'content': forms.Textarea(attrs={'placeholder': 'Comentario'},)
        }
    