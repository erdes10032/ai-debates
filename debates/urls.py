from django.urls import path

from debates.views import (
    DebateConsensusHtmlView,
    DebateCreateView,
    DebateDetailView,
    DebateHistoryPdfDownloadView,
    DebateListView,
)

app_name = 'debates'


urlpatterns = [
    path(
        '',
        DebateListView.as_view(),
        name='list',
    ),

    path(
        'create/',
        DebateCreateView.as_view(),
        name='create',
    ),

    path(
        '<int:pk>/',
        DebateDetailView.as_view(),
        name='detail',
    ),
    path(
        '<int:pk>/consensus/html/',
        DebateConsensusHtmlView.as_view(),
        name='consensus-html',
    ),
    path(
        '<int:pk>/history/pdf/',
        DebateHistoryPdfDownloadView.as_view(),
        name='history-pdf',
    ),
]
