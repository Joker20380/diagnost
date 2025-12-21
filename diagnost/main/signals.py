from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import News, Subscriber
from django.core.mail import EmailMultiAlternatives  # Используем EmailMultiAlternatives
from django.template.loader import render_to_string  # Для рендеринга HTML-шаблона



@receiver(post_save, sender=News)
def send_email_to_subscribers(sender, instance, **kwargs):
    if instance.is_published:
        if kwargs.get('created') or instance.tracker.has_changed('is_published'):
            subscribers = Subscriber.objects.all()
            subject = f'Новый пост: {instance.title}'

            # Текстовая версия письма
            text_content = f'Пост: {instance.title}\n\n{instance.content}'

            # HTML-версия письма
            html_content = render_to_string('diagnost/email_template.html', {
                'news': instance
            })

            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [subscriber.email for subscriber in subscribers]

            # Создаем письмо
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, "text/html")  # Добавляем HTML-версию
            msg.send()