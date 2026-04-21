import os
import traceback

print("boot")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myserver.settings")

try:
    import django

    print("before setup")
    django.setup()
    print("after setup")

    from django.test import Client

    client = Client()

    print("posting api login")
    response = client.post(
        "/api/auth/login/",
        data={"username": "admin", "password": "Admin123!"},
        content_type="application/json",
    )
    print("api status", response.status_code)
    print("api body", response.content.decode())

    print("posting frontend login")
    response = client.post(
        "/login/",
        data={"user_number": "admin", "password": "Admin123!"},
    )
    print("login status", response.status_code)
    print("login location", response.get("Location"))
    print("login body", response.content.decode())

except Exception:
    traceback.print_exc()