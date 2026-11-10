from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


def signup(request):
    """Halaman daftar akun baru (pakai form bawaan Django)."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("chat-page")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})
