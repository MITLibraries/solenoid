from django.dispatch import Signal

email_sent = Signal(providing_args=['instance', 'username'])
