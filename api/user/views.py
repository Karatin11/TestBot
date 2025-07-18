from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny

User = get_user_model()
from django.shortcuts import get_object_or_404
from .models import Subject, Question, Answer, TestResult, UserAnswer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"detail": "Username and password required"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already exists"}, status=400)
        User.objects.create_user(username=username, password=password)
        return Response({"detail": "User created"}, status=201)

from .serializers import LoginSerializer

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': user.username,
        })

class SubjectListView(APIView):
    def get(self, request):
        subjects = Subject.objects.all().values("id", "name")
        return Response(subjects)

class QuestionListView(APIView):
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        questions = Question.objects.filter(subject=subject)
        data = []
        for q in questions:
            answers = q.answers.all()
            data.append({
                "question_id": q.id,
                "text": q.text,
                "answers": [{"id": a.id, "text": a.text} for a in answers]
            })
        return Response(data)

class SubmitTestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        {
            "subject_id": 1,
            "answers": [
                {"question_id": 5, "answer_id": 23},
                {"question_id": 6, "answer_id": 27}
            ]
        }
        """
        user = request.user
        subject = get_object_or_404(Subject, id=request.data["subject_id"])
        answers_data = request.data["answers"]

        correct = 0
        total = len(answers_data)
        result = TestResult.objects.create(user=user, subject=subject, score=0, total=total)

        for item in answers_data:
            question = get_object_or_404(Question, id=item["question_id"])
            selected_answer = get_object_or_404(Answer, id=item["answer_id"])
            UserAnswer.objects.create(result=result, question=question, selected_answer=selected_answer)

            if selected_answer.is_correct:
                correct += 1

        result.score = correct
        result.save()

        return Response({
            "message": "Результат сохранён",
            "score": correct,
            "total": total
        })


class TestHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        results = TestResult.objects.filter(user=user).order_by("-created_at")
        data = [{
            "subject": r.subject.name,
            "score": r.score,
            "total": r.total,
            "date": r.created_at
        } for r in results]
        return Response(data)