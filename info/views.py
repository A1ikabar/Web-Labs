from datetime import date
from django.http import JsonResponse

def info_view(request):
    """
    Обработчик GET /info
    Возвращает JSON с количеством дней до Нового года
    """
    today = date.today()
    current_year = today.year
    new_year = date(current_year + 1, 1, 1)
    
    days_before_new_year = (new_year - today).days
    
    return JsonResponse({'days_before_new_year': days_before_new_year})