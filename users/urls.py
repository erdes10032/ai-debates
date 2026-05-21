from django.urls import path

from .views import (
    ProfileDetailView,
    ProfileUpdateView,
)

app_name = 'users'


urlpatterns = [
    path(
        'profile/',
        ProfileDetailView.as_view(),
        name='profile',
    ),

    path(
        'profile/edit/',
        ProfileUpdateView.as_view(),
        name='profile_edit',
    ),
]