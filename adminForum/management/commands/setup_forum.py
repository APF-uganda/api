from django.core.management.base import BaseCommand
from adminForum.models import Category, Tag


class Command(BaseCommand):
    help = 'Create initial categories and tags for the forum'

    def handle(self, *args, **options):
        # Create categories
        categories = [
            {'name': 'Budgeting', 'slug': 'budgeting', 'description': 'Budget planning and financial management discussions', 'icon': '💰'},
            {'name': 'Savings', 'slug': 'savings', 'description': 'Saving strategies, tips, and best practices', 'icon': '🏦'},
            {'name': 'Investing', 'slug': 'investing', 'description': 'Investment advice and portfolio discussions', 'icon': '📈'},
            {'name': 'Tax Planning', 'slug': 'tax-planning', 'description': 'Tax strategies and compliance discussions', 'icon': '📋'},
            {'name': 'General Discussion', 'slug': 'general', 'description': 'General financial topics and conversations', 'icon': '💬'},
        ]

        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'icon': cat_data['icon']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {category.name}'))

        # Create tags
        tags = [
            {'name': 'discussion', 'slug': 'discussion'},
            {'name': 'help', 'slug': 'help'},
            {'name': 'advice', 'slug': 'advice'},
            {'name': 'question', 'slug': 'question'},
            {'name': 'tutorial', 'slug': 'tutorial'},
            {'name': 'news', 'slug': 'news'},
            {'name': 'beginner', 'slug': 'beginner'},
            {'name': 'advanced', 'slug': 'advanced'},
            {'name': 'tips', 'slug': 'tips'},
            {'name': 'resources', 'slug': 'resources'},
        ]

        for tag_data in tags:
            tag, created = Tag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults={'name': tag_data['name']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created tag: {tag.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Tag already exists: {tag.name}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Forum setup complete!'))
        self.stdout.write(self.style.SUCCESS(f'Categories created: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Tags created: {Tag.objects.count()}'))
