from datetime import date
from .models import DailyQuest


def footer_context(request):
    """Context processor to add footer-related data to all templates"""
    context = {}
    
    if request.user.is_authenticated:
        # Get or create today's daily quest for footer badges
        try:
            today = date.today()
            daily_quest, _ = DailyQuest.objects.get_or_create(
                user=request.user,
                date=today,
                quest_type='complete_drill',
                defaults={
                    'description': 'Complete one drill',
                    'xp_reward': 10,
                    'coin_reward': 5
                }
            )
            context['daily_quest'] = daily_quest if not daily_quest.completed else None
        except Exception:
            context['daily_quest'] = None
    
    return context

