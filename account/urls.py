from django.urls import path
from .views import *

urlpatterns = [
    path('trainers/register/', TrainerRegistrationView.as_view(), name='trainer-register'),
    path('customers/register/', CustomerRegisterView.as_view(), name='customer-register'),
    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('signin/', SignInView.as_view(), name='signin'), 
    path('signout/', SignOutView.as_view(), name='signout'),
]
