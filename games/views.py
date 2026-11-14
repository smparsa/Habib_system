from django.contrib.auth.decorators import login_required
from django.shortcuts import render

LOGIN_URL = "core:index"


@login_required(login_url=LOGIN_URL)
def home(request):
    """مرکز بازی - فهرست بازی‌ها"""
    return render(request, "games/home.html")


@login_required(login_url=LOGIN_URL)
def snake(request):
    """بازی مار (Snake)"""
    return render(request, "games/snake.html")


@login_required(login_url=LOGIN_URL)
def magnet(request):
    """بازی مگنت (Magnet) - استراتژیک در برابر هوش مصنوعی"""
    return render(request, "games/magnet.html")


@login_required(login_url=LOGIN_URL)
def tetris(request):
    """بازی تتریس (Tetris)"""
    return render(request, "games/tetris.html")


@login_required(login_url=LOGIN_URL)
def hok(request):
    """بازی Honor of Kings - موبا ۵ لِین با لِین‌های سه‌گانه، برج‌ها، مینیون‌ها و ۶ هیرو"""
    return render(request, "games/hok.html")
