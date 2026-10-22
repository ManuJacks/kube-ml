from django.urls import path

from core.views import (
    example_view,
    examples_view,
    health_view,
    metrics_view,
    predict_view,
    ready_view,
    tensor_gui_view,
)

urlpatterns = [
    path('', tensor_gui_view, name='tensor_gui'),
    path('predict', predict_view, name='predict'),
    path('healthz', health_view, name='health'),
    path('readyz', ready_view, name='ready'),
    path('metrics', metrics_view, name='metrics'),
    path('api/v1/examples', examples_view, name='examples'),
    path('api/v1/examples/<str:name>', example_view, name='example'),
]
