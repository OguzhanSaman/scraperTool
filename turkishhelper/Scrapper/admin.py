from django.contrib import admin
from django import forms
from .models import ManualResmiGazeteData

class ManualResmiGazeteDataForm(forms.ModelForm):
    """
    Custom form with large textarea for HTML content
    """
    html_content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 20,
            'cols': 100,
            'style': 'width: 100%; font-family: monospace;',
            'placeholder': 'Paste the HTML content from Resmi Gazete website here...'
        }),
        help_text="Copy and paste the HTML content from the Resmi Gazete website. You can get this by right-clicking on the page and selecting 'View Page Source' or using browser developer tools."
    )
    
    class Meta:
        model = ManualResmiGazeteData
        fields = ['html_content', 'is_active', 'notes']

@admin.register(ManualResmiGazeteData)
class ManualResmiGazeteDataAdmin(admin.ModelAdmin):
    form = ManualResmiGazeteDataForm
    list_display = ['__str__', 'content_length', 'is_active', 'date_added']
    list_filter = ['is_active', 'date_added']
    search_fields = ['html_content', 'notes']
    readonly_fields = ['date_added']
    
    fieldsets = (
        ('HTML Content', {
            'fields': ('html_content',),
            'description': 'Paste the HTML content from Resmi Gazete website. This should be the raw HTML source code.'
        }),
        ('Settings', {
            'fields': ('is_active', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('date_added',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-date_added')
