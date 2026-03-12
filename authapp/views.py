import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from authapp.dto import RegisterDTO, LoginDTO

from authapp.auth_service import register_user, login_user, get_current_user_from_access_token, refresh_user_tokens, logout_user, logout_all_user_sessions

@csrf_exempt
def register(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        body = json.loads(request.body)

        dto = RegisterDTO(body)

        user = register_user(
            dto.email,
            dto.password,
            dto.phone
        )

        return JsonResponse({
            "id": str(user.id),
            "email": user.email
        }, status=201)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def login(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        body = json.loads(request.body)

        dto = LoginDTO(body)

        user, access_token, refresh_token = login_user(
            dto.email,
            dto.password
        )

        response = JsonResponse({
            "message": "login successful",
            "email": user.email
        }, status=200)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

def whoami(request):

    if request.method != "GET":
        return JsonResponse({"error": "method not allowed"}, status=405)

    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        user = get_current_user_from_access_token(access_token)

        return JsonResponse({
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
        }, status=200)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=401)

@csrf_exempt
def refresh(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    refresh_token = request.COOKIES.get("refresh_token")

    if not refresh_token:
        return JsonResponse({"error": "refresh token missing"}, status=401)

    try:
        user, access_token, new_refresh_token = refresh_user_tokens(refresh_token)

        response = JsonResponse({
            "message": "tokens refreshed",
            "email": user.email
        }, status=200)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=401)

@csrf_exempt
def logout(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return JsonResponse({"error": "not authenticated"}, status=401)

    logout_user(access_token)

    response = JsonResponse({
        "message": "logged out"
    })

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response

@csrf_exempt
def logout_all(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return JsonResponse({"error": "not authenticated"}, status=401)

    try:
        logout_all_user_sessions(access_token)

        response = JsonResponse({
            "message": "logged out from all sessions"
        }, status=200)

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=401)