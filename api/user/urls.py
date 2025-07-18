from django.urls import path
from .views import (
    SubjectListView,
    QuestionListView,
    SubmitTestView,
    TestHistoryView,
    RegisterView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/subjects/', SubjectListView.as_view(), name='subject-list'),
    path('api/subjects/<int:subject_id>/questions/', QuestionListView.as_view(), name='questions'),
    path('api/submit-test/', SubmitTestView.as_view(), name='submit-test'),
    path('api/history/', TestHistoryView.as_view(), name='test-history'),
]