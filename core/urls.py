from django.urls import path
from core.views import tensor_gui_view, predict_view

urlpatterns = [
    path('', tensor_gui_view, name='tensor_gui'),
    path('predict', predict_view, name='predict'),
]
