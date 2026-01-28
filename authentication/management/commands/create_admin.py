"""
Management command to create an admin user.
Usage: python manage.py create_admin --email admin@example.com --password securepass123
"""
from django.core.management.base import BaseCommand, CommandError
from authentication.models import User, UserRole


class Command(BaseCommand):
    help = 'Create an admin user with specified email and password'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address for the admin user'
        )
        parser.add_argument(
            '--password',
            type=str,
            required=True,
            help='Password for the admin user'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists')

        try:
            # Create admin user
            user = User.objects.create_user(
                email=email,
                password=password,
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created admin user: {email} (ID: {user.id})'
                )
            )
        except Exception as e:
            raise CommandError(f'Error creating admin user: {str(e)}')
