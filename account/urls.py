from django.urls import path
from .views import *

urlpatterns = [
    path('trainers/register/', TrainerRegistrationView.as_view(), name='trainer-register'),
    path('customers/register/', CustomerRegisterView.as_view(), name='customer-register'),
    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('signin/', SignInView.as_view(), name='signin'), 
    path('signout/', SignOutView.as_view(), name='signout'),
    path('trainers/', trainer_list, name="trainer-list"),
    path('bookings/create/', create_booking, name="create-booking" ),
    path('bookings/upcoming/', upcoming_sessions, name="upcoming-sessions" ),
    path('bookings/past/', past_sessions, name="past-sessions" ),
    path('bookings/trainer/upcoming/', upcoming_trainer_sessions, name="upcoming-trainer-sessions"),
    path('bookings/trainer/past/', past_trainer_sessions, name="past-trainer-sessions"),
    path('bookings/<int:booking_id>/start/', start_session, name='start-session'),
]
