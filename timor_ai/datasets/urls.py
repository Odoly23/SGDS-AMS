from django.urls import path

from . import views

urlpatterns = [
    path("kontribusi/", views.contribute_page, name="contribute-page"),
    path("api/contribute/next/", views.NextTaskView.as_view()),
    path("api/contribute/", views.SubmitView.as_view()),
    path("api/contribute/review/", views.NextReviewView.as_view()),
    path("api/contribute/vote/", views.VoteView.as_view()),
    path("api/contribute/stats/", views.StatsView.as_view()),
]
