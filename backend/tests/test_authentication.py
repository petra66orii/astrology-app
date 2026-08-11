import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_registration_requires_csrf_and_creates_session():
    client = APIClient(enforce_csrf_checks=True)
    denied = client.post(
        reverse("register"),
        {"email": "new@example.com", "password": "Secure-passphrase-987"},
        format="json",
    )
    assert denied.status_code == 403

    csrf_response = client.get(reverse("csrf"))
    token = csrf_response.cookies["csrftoken"].value
    created = client.post(
        reverse("register"),
        {"email": "New@Example.COM", "password": "Secure-passphrase-987"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert created.status_code == 201
    assert created.data["user"]["email"] == "new@example.com"
    assert client.get(reverse("current-user")).status_code == 200


@pytest.mark.django_db
def test_anonymous_private_endpoint_is_blocked():
    assert APIClient().get(reverse("birth-profile-list-create")).status_code in {401, 403}


@pytest.mark.django_db
def test_login_logout_session_flow(user):
    client = APIClient(enforce_csrf_checks=True)
    token = client.get(reverse("csrf")).cookies["csrftoken"].value
    response = client.post(
        reverse("login"),
        {"email": "PERSON@example.com", "password": "Strong-passphrase-123"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    assert client.get(reverse("current-user")).status_code == 200
    token = client.cookies["csrftoken"].value
    assert client.post(reverse("logout"), HTTP_X_CSRFTOKEN=token).status_code == 204
    assert client.get(reverse("current-user")).status_code in {401, 403}
