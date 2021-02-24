from django.dispatch import Signal

# providing_args=['instance', 'username']
email_sent = Signal()
