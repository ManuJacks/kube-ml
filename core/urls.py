from django.urls import path
from core.views import tensor_gui_view, predict_view, health_view, ready_view, metrics_view

urlpatterns = [
    path('', tensor_gui_view, name='tensor_gui'),
    path('predict', predict_view, name='predict'),
    path('healthz', health_view, name='health'),
    path('readyz', ready_view, name='ready'),
    path('metrics', metrics_view, name='metrics'),
]
