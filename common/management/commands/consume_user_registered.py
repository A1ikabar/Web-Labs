from django.core.management.base import BaseCommand

from common.user_registered_consumer import start_user_registered_consumer

class Command(BaseCommand):
    help = "Start RabbitMQ consumer for user.registered events"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Starting user registered consumer...")
        )
        start_user_registered_consumer()