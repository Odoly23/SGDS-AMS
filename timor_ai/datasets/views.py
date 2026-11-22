"""Halaman & API crowdsourcing untuk user biasa (bukan admin)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


@login_required
def contribute_page(request):
    return render(request, "contribute/contribute.html")


def _err(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class NextTaskView(APIView):
    def get(self, request):
        try:
            return Response({"task": services.next_task(request.user, request.query_params.get("language", ""))})
        except services.ContribError as e:
            return _err(e)


class SubmitView(APIView):
    def post(self, request):
        d = request.data
        try:
            t = services.submit(request.user, str(d.get("phrase", "")), str(d.get("language", "")), str(d.get("text", "")),
                                str(d.get("dialect", "")), str(d.get("notes", "")))
        except services.ContribError as e:
            return _err(e)
        return Response({"id": t.pk, "status": t.status}, status=status.HTTP_201_CREATED)


class NextReviewView(APIView):
    def get(self, request):
        try:
            return Response({"item": services.next_review(request.user, request.query_params.get("language", ""))})
        except services.ContribError as e:
            return _err(e)


class VoteView(APIView):
    def post(self, request):
        try:
            return Response(services.vote(request.user, request.data.get("translation"), bool(request.data.get("agree"))))
        except services.ContribError as e:
            return _err(e)


class StatsView(APIView):
    def get(self, request):
        return Response({"me": services.my_stats(request.user), "leaderboard": services.leaderboard(request.user)})
