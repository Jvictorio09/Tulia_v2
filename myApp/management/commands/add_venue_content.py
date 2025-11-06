from django.core.management.base import BaseCommand
from myApp.models import Venue, VenueTaskSheet


class Command(BaseCommand):
    help = 'Add content to District-1 venues using RAG or manual entry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--venue',
            type=str,
            help='Venue name to add content to (optional)',
        )
        parser.add_argument(
            '--use-rag',
            action='store_true',
            help='Use RAG to generate content from Knowledge Blocks (requires n8n setup)',
        )

    def handle(self, *args, **options):
        venue_name = options.get('venue')
        use_rag = options.get('use_rag', False)
        
        if venue_name:
            venues = Venue.objects.filter(name__icontains=venue_name)
        else:
            # Get all District-1 venues
            from myApp.models import District
            district_1 = District.objects.get(number=1)
            venues = Venue.objects.filter(district=district_1)
        
        for venue in venues:
            self.stdout.write(f'\nProcessing: {venue.name}')
            
            if use_rag:
                # In production, this would call n8n to generate content from Knowledge Blocks
                self.stdout.write('  → RAG generation would happen here via n8n webhook')
                self.stdout.write('  → Would retrieve relevant Knowledge Blocks based on venue theme')
                self.stdout.write('  → Would generate exercises that mirror Level-1 concepts')
                # Example: Call n8n webhook with venue context and get back exercise suggestions
            else:
                # Manual content creation
                self.stdout.write('  → Using manual content entry')
                self.stdout.write('  → You can add content via Django admin or this command')
            
            # Check existing task sheets
            existing = VenueTaskSheet.objects.filter(venue=venue).count()
            self.stdout.write(f'  → Current task sheets: {existing}')
            
            if existing == 0:
                self.stdout.write(self.style.WARNING(f'  → No task sheets found for {venue.name}'))
                self.stdout.write('  → Add content via: python manage.py shell')
                self.stdout.write('  → Or use Django admin at /admin/myApp/venuetasksheet/')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Content check completed!'))
        self.stdout.write('\nTo add content:')
        self.stdout.write('1. Via Django Admin: /admin/myApp/venuetasksheet/add/')
        self.stdout.write('2. Via Python shell:')
        self.stdout.write('   python manage.py shell')
        self.stdout.write('   >>> from myApp.models import Venue, VenueTaskSheet')
        self.stdout.write('   >>> venue = Venue.objects.get(name="Greek Amphitheater")')
        self.stdout.write('   >>> VenueTaskSheet.objects.create(venue=venue, title="...", ...)')
        self.stdout.write('3. Via RAG (when n8n is configured):')
        self.stdout.write('   python manage.py add_venue_content --use-rag')

