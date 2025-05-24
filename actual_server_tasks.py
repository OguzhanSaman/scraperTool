from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .utils import scrape_resmi_gazete, scrape_wikipedia_today_in_history
import logging
from datetime import date # Import date
import locale # Import locale
from django.contrib.auth import get_user_model # Import User model

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60) # Added retry logic
def send_daily_gazette_email(self):
    """
    Celery task to scrape Resmi Gazete and send the daily digest email to all active users.
    """
    
    # --- Get Recipient List (All Active Users) ---
    User = get_user_model()
    # Fetch emails of all active users who have an email address set.
    # Consider adding filtering based on user preferences/roles if needed.
    recipient_list = list(User.objects.filter(is_active=True, email__isnull=False).exclude(email='').values_list('email', flat=True))
    
    if not recipient_list:
        logger.warning("No active users with email addresses found. Skipping email send.")
        return "No recipients found."
    # --- End Recipient List ---

    # Set locale to Turkish for month name translation
    try:
        locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
    except locale.Error:
        logger.warning("Turkish locale 'tr_TR.UTF-8' not found. Using default locale for date.")
        # Fallback or handle error as needed
        
    today_str = date.today().strftime("%d %B %Y") # Get today's date formatted
    locale.setlocale(locale.LC_TIME, '') # Reset locale to default if necessary

    # Scrape content
    scraped_html = scrape_resmi_gazete()
    wikipedia_html = scrape_wikipedia_today_in_history() # Scrape Wikipedia

    if wikipedia_html and "içeriği alınamadı" not in wikipedia_html and "bulunamadı" not in wikipedia_html:
        pass
    elif wikipedia_html: # It means it returned a known "not found" or "error" message from the scraper
        logger.warning(f"Wikipedia scraping returned a message: {wikipedia_html}")
    else: # It means scraping might have returned None or empty string unexpectedly
        logger.warning("Wikipedia content scraping returned no content or an unexpected empty/None value.")
    # ---- END ADDITION ----
    
    if not scraped_html:
        logger.error("Failed to scrape content from Resmi Gazete. Retrying if possible.")
        try:
            # Use Celery's retry mechanism
            self.retry(exc=Exception("Scraping failed"))
        except Exception as e:
            logger.exception("Failed to retry task after scraping failure.")
            return "Scraping failed, retry mechanism failed."
        # If retry limit is reached, it will raise MaxRetriesExceededError
        # which Celery handles. We can also return a specific error message.
        return "Scraping failed after multiple retries."

    # Prepare email content
    subject = f'Günlük Resmi Gazete Özeti - {today_str}' # Add date to subject
    context = {
        'subject': subject,
        'content': scraped_html,
        'publication_date': today_str, # Add date to context
        'wikipedia_content': wikipedia_html if wikipedia_html else "Tarihte bugün içeriği alınamadı." # Add wikipedia content
    }
    html_message = render_to_string('emails/daily_gazette.html', context)
    # Plain text version is good practice for email clients that don't support HTML
    # For now, we'll send an empty plain text part or a simple message.
    plain_message = "Lütfen e-postayı HTML formatında görüntüleyin."

    try:
        with open("daily_gazette_preview.html", "w", encoding="utf-8") as f:
            f.write(html_message)
    except Exception as e:
        logger.error(f"Failed to write HTML email preview: {e}")

    try:
        send_mail(
            subject=subject,
            message=plain_message, # Plain text body
            from_email=settings.DEFAULT_FROM_EMAIL, # Make sure this is configured in settings
            recipient_list=recipient_list,
            html_message=html_message, # HTML content
            fail_silently=False, # Raise exceptions on failure
        )
        return f"Email sent successfully to {len(recipient_list)} recipients."
    except Exception as e:
        logger.error(f"Failed to send daily gazette email: {e}", exc_info=True)
        try:
            # Retry sending the email if it fails
            self.retry(exc=e)
        except Exception as retry_exc:
            logger.exception("Failed to retry task after email sending failure.")
            return "Email sending failed, retry mechanism failed."
        return "Email sending failed after multiple retries."

# Example of how to call the task (for testing)
# from .tasks import send_daily_gazette_email
# send_daily_gazette_email.delay() 