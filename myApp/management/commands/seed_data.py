from django.core.management.base import BaseCommand
from myApp.models import Level, Module, KnowledgeBlock, District, Venue, VenueTaskSheet


class Command(BaseCommand):
    help = 'Seed initial data for Level 1, Modules, and District-1'

    def handle(self, *args, **options):
        # Create Level 1
        level_1, created = Level.objects.get_or_create(
            number=1,
            defaults={
                'name': 'Foundation',
                'description': 'Master the fundamentals of effective communication',
                'milestone_threshold': 70.0
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Level 1'))
        else:
            self.stdout.write('Level 1 already exists')

        # Create Modules A, B, C, D
        modules_data = [
            {'code': 'A', 'name': 'Core Principles', 'order': 1, 'xp_reward': 50},
            {'code': 'B', 'name': 'Audience Psychology', 'order': 2, 'xp_reward': 50},
            {'code': 'C', 'name': 'Structure & Flow', 'order': 3, 'xp_reward': 50},
            {'code': 'D', 'name': 'Presence & Influence', 'order': 4, 'xp_reward': 50},
        ]

        for mod_data in modules_data:
            module, created = Module.objects.get_or_create(
                level=level_1,
                code=mod_data['code'],
                defaults={
                    'name': mod_data['name'],
                    'order': mod_data['order'],
                    'xp_reward': mod_data['xp_reward'],
                    'description': f'Learn {mod_data["name"]}'
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Module {mod_data["code"]}'))
                
                # Create sample knowledge blocks for each module
                for i in range(3):
                    KnowledgeBlock.objects.create(
                        module=module,
                        title=f'{mod_data["name"]} - Concept {i+1}',
                        summary=f'This is a foundational concept about {mod_data["name"]}. Understanding this will help you communicate more effectively.',
                        tags=['foundation', 'core'],
                        exercise_seeds=[],
                        citations=[f'Source {i+1}'],
                        order=i
                    )

        # Create District-1
        district_1, created = District.objects.get_or_create(
            number=1,
            defaults={
                'name': 'Ancient Communicators',
                'description': 'Practice in historical settings',
                'unlock_requirement': 'Complete Level 1 + Milestone ≥70%'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created District-1'))
            
            # Create venues
            venues_data = [
                {'name': 'Greek Amphitheater', 'description': 'Composure drills', 'ticket_cost': 1, 'xp_reward': 20, 'coin_reward': 10, 'order': 1},
                {'name': 'Roman Forum', 'description': 'Audience empathy drills', 'ticket_cost': 1, 'xp_reward': 20, 'coin_reward': 10, 'order': 2},
                {'name': 'Medieval Market Square', 'description': 'Presence-in-noise drills', 'ticket_cost': 1, 'xp_reward': 20, 'coin_reward': 10, 'order': 3},
            ]
            
            for venue_data in venues_data:
                venue, _ = Venue.objects.get_or_create(
                    district=district_1,
                    name=venue_data['name'],
                    defaults=venue_data
                )
                
                # Create sample task sheets for each venue
                if venue_data['name'] == 'Greek Amphitheater':
                    VenueTaskSheet.objects.get_or_create(
                        venue=venue,
                        title='Composure Under Pressure',
                        defaults={
                            'description': 'Practice maintaining composure when facing challenging questions or interruptions.',
                            'exercises': [
                                {
                                    'title': 'Handle Interruption',
                                    'type': 'scenario',
                                    'description': 'Practice responding calmly to an unexpected question during your presentation.',
                                    'prompt': 'You\'re presenting quarterly results. A board member interrupts: "But what about the Q2 losses?" How do you respond?'
                                },
                                {
                                    'title': 'Maintain Presence',
                                    'type': 'speak',
                                    'description': 'Deliver a 30-second statement while maintaining steady eye contact and calm demeanor.',
                                    'prompt': 'Explain your company\'s vision while staying composed under pressure.'
                                }
                            ],
                            'order': 0
                        }
                    )
                elif venue_data['name'] == 'Roman Forum':
                    VenueTaskSheet.objects.get_or_create(
                        venue=venue,
                        title='Audience Empathy Practice',
                        defaults={
                            'description': 'Develop your ability to read and respond to your audience\'s needs and reactions.',
                            'exercises': [
                                {
                                    'title': 'Read the Room',
                                    'type': 'scenario',
                                    'description': 'Identify audience signals and adjust your communication style accordingly.',
                                    'prompt': 'Your audience looks confused. How do you adapt your message?'
                                },
                                {
                                    'title': 'Connect with Different Personalities',
                                    'type': 'scenario',
                                    'description': 'Practice tailoring your message to different audience types.',
                                    'prompt': 'Address a mixed audience: analytical thinkers and emotional decision-makers.'
                                }
                            ],
                            'order': 0
                        }
                    )
                elif venue_data['name'] == 'Medieval Market Square':
                    VenueTaskSheet.objects.get_or_create(
                        venue=venue,
                        title='Presence in Noise',
                        defaults={
                            'description': 'Build your ability to command attention and maintain presence in distracting environments.',
                            'exercises': [
                                {
                                    'title': 'Command Attention',
                                    'type': 'speak',
                                    'description': 'Practice using voice, body language, and pauses to capture and hold attention.',
                                    'prompt': 'Deliver a 1-minute pitch that cuts through background noise and distractions.'
                                },
                                {
                                    'title': 'Energy Management',
                                    'type': 'scenario',
                                    'description': 'Maintain high energy and engagement even when the environment is challenging.',
                                    'prompt': 'Keep your audience engaged during a presentation in a noisy, distracting space.'
                                }
                            ],
                            'order': 0
                        }
                    )
            self.stdout.write(self.style.SUCCESS('Created 3 venues with task sheets in District-1'))
        else:
            self.stdout.write('District-1 already exists')

        self.stdout.write(self.style.SUCCESS('Data seeding completed!'))

