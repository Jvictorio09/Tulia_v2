from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import user_passes_test, login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect

from .forms import AdminLoginForm

User = get_user_model()

COLUMN_LABELS = {
    "username": "User Name",
    "email": "Email",
    "role": "Role",
    "typical_audience": "Typical Audience",
    "main_goal": "Main Goal",
    "comfort_under_pressure": "How Comfortable",
    "time_pressure_profile": "Under Time Pressure",
    "preferred_practice_time": "Practice Time",
    "daily_goal_minutes": "Daily Minutes Target",
}

COLUMN_GROUPS = [
    (
        "core",
        "Registered Users",
        ["username", "email", "role", "typical_audience", "main_goal", "daily_goal_minutes"],
    ),
    (
        "practice",
        "Practice Details",
        [
            "username",
            "email",
            "comfort_under_pressure",
            "time_pressure_profile",
            "preferred_practice_time",
            "daily_goal_minutes",
        ],
    ),
]


def _is_admin(user):
    """Return True for authenticated superusers."""
    return user.is_authenticated and user.is_superuser


def admin_required(view_func):
    return user_passes_test(_is_admin, login_url="/admin-/login/")(view_func)


def _resolve_theme(request):
    theme_param = request.GET.get("theme")
    if theme_param in {"light", "dark"}:
        request.session["adminpanel_theme"] = theme_param
        return theme_param
    return request.session.get("adminpanel_theme", "light")


def _valid_view(view_key: str) -> str:
    group_keys = {key for key, _, _ in COLUMN_GROUPS}
    return view_key if view_key in group_keys else COLUMN_GROUPS[0][0]


def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("adminpanel:dashboard")

    form = AdminLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user and user.is_superuser:
            login(request, user)
            return redirect("adminpanel:dashboard")
        messages.error(request, "Invalid credentials or not an admin user.")
    return render(request, "adminpanel/login.html", {"form": form})


@login_required(login_url="/admin-/login/")
@admin_required
def admin_dashboard(request):
    theme = _resolve_theme(request)
    current_view = _valid_view(request.GET.get("view", ""))

    query = (request.GET.get("q") or "").strip()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .select_related("profile")
    )

    if query:
        users = users.filter(
            Q(email__icontains=query)
            | Q(username__icontains=query)
            | Q(profile__role__icontains=query)
            | Q(profile__typical_audience__icontains=query)
            | Q(profile__main_goal__icontains=query)
            | Q(profile__preferred_practice_time__icontains=query)
        )
    elif request.method == "GET" and "q" in request.GET:
        # User cleared the search field; reset the view.
        reset_params = request.GET.copy()
        reset_params.pop("q", None)
        reset_params.pop("page", None)
        query_string = reset_params.urlencode()
        if query_string:
            return redirect(f"{request.path}?{query_string}")
        return redirect(request.path)

    users = users.order_by("email")

    records = []
    for user in users:
        profile = getattr(user, "profile", None)
        records.append(
            {
                "username": user.username,
                "email": user.email,
                "role": getattr(profile, "role", ""),
                "typical_audience": getattr(profile, "typical_audience", ""),
                "main_goal": getattr(profile, "main_goal", ""),
                "comfort_under_pressure": getattr(profile, "comfort_under_pressure", ""),
                "time_pressure_profile": getattr(profile, "time_pressure_profile", ""),
                "preferred_practice_time": getattr(profile, "preferred_practice_time", ""),
                "daily_goal_minutes": getattr(profile, "daily_goal_minutes", ""),
            }
        )

    group_map = {key: cols for key, _, cols in COLUMN_GROUPS}
    selected_columns = group_map[current_view]
    columns = [(col_key, COLUMN_LABELS[col_key]) for col_key in selected_columns]

    row_data = [
        [record.get(col_key, "") for col_key in selected_columns]
        for record in records
    ]

    paginator = Paginator(row_data, 25)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    start_number = page_obj.start_index() if paginator.count else 0

    toggle_params = request.GET.copy()
    toggle_params["theme"] = "light" if theme == "dark" else "dark"
    toggle_url = f"?{toggle_params.urlencode()}"

    base_params = request.GET.copy()
    base_params.pop("page", None)
    base_query = base_params.urlencode()

    nav_params = request.GET.copy()
    nav_params.pop("page", None)
    nav_params.pop("view", None)
    nav_base = nav_params.urlencode()

    nav_items = [
        {"key": key, "label": label}
        for key, label, _ in COLUMN_GROUPS
    ]

    return render(
        request,
        "adminpanel/dashboard.html",
        {
            "page_obj": page_obj,
            "q": query,
            "total_count": paginator.count,
            "theme": theme,
            "toggle_url": toggle_url,
            "base_query": base_query,
            "nav_base": nav_base,
            "columns": columns,
            "start_number": start_number,
            "nav_items": nav_items,
            "current_view": current_view,
        },
    )


@login_required(login_url="/admin-/login/")
@admin_required
def admin_export_csv(request):
    _resolve_theme(request)
    current_view = _valid_view(request.GET.get("view", ""))

    query = (request.GET.get("q") or "").strip()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .select_related("profile")
    )
    if query:
        users = users.filter(
            Q(email__icontains=query)
            | Q(username__icontains=query)
            | Q(profile__role__icontains=query)
            | Q(profile__typical_audience__icontains=query)
            | Q(profile__main_goal__icontains=query)
            | Q(profile__preferred_practice_time__icontains=query)
        )

    users = users.order_by("email")
    selected_columns = {key: cols for key, _, cols in COLUMN_GROUPS}[current_view]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registered_users.csv"'
    headers = [COLUMN_LABELS[col_key] for col_key in selected_columns]
    response.write(",".join(headers) + "\n")
    for user in users:
        profile = getattr(user, "profile", None)
        field_source = {
            "username": user.username,
            "email": user.email,
            "role": getattr(profile, "role", ""),
            "typical_audience": getattr(profile, "typical_audience", ""),
            "main_goal": getattr(profile, "main_goal", ""),
            "comfort_under_pressure": getattr(profile, "comfort_under_pressure", ""),
            "time_pressure_profile": getattr(profile, "time_pressure_profile", ""),
            "preferred_practice_time": getattr(profile, "preferred_practice_time", ""),
            "daily_goal_minutes": getattr(profile, "daily_goal_minutes", ""),
        }
        safe_values = [
            str((field_source.get(col_key) or "")).replace(",", " ")
            for col_key in selected_columns
        ]
        response.write(",".join(safe_values) + "\n")
    return response


def admin_logout(request):
    logout(request)
    return redirect("adminpanel:login")
