from django.db import models
from django.utils import timezone

class ManualResmiGazeteData(models.Model):
    """
    Model to store manually entered Resmi Gazete HTML data
    """
    html_content = models.TextField(
        verbose_name="Resmi Gazete HTML Content",
        help_text="Paste the HTML content from Resmi Gazete website here"
    )
    date_added = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date Added"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Uncheck to disable this data entry"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
        help_text="Optional notes about this data entry"
    )
    
    class Meta:
        verbose_name = "Manual Resmi Gazete Data"
        verbose_name_plural = "Manual Resmi Gazete Data"
        ordering = ['-date_added']
    
    def __str__(self):
        return f"Resmi Gazete Data - {self.date_added.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def content_length(self):
        """Return the length of HTML content"""
        return len(self.html_content) if self.html_content else 0
