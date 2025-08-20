from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from .serializers import TrainerRegistrationSerializer, CustomerCreateSerializer, UserAccountSerializer
from .models import Customer, Booking, Trainer, TrainerProfile
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from django.utils.timezone import now
from datetime import timedelta
import datetime

class TrainerRegistrationView(APIView):
    def post(self, request):
        serializer = TrainerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            trainer = serializer.save()
            return Response({"message": "Trainer registered successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerRegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = Customer.objects.all()
    serializer_class = CustomerCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Customer created successfully"},
            status=status.HTTP_201_CREATED
        )

        
class SignInView(ObtainAuthToken):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

      
        # Authenticate user
        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        # Create or get the token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'email': user.email,
            'name': user.firstname,
            'role': user.role
           
        })

class SignOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()  # Delete the token
        except (AttributeError, Token.DoesNotExist):
            pass  # Token might not exist
        
        return Response({"message": "Successfully logged out."})
    

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserAccountSerializer(user)
        return Response(serializer.data)

class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            return Response({"detail": "Customer profile not found"}, status=404)

        data = {
            "firstname": customer.user.firstname,
            "lastname": customer.user.lastname,
            "email": customer.user.email,
            "contact_number": customer.contact_number,
        }

        return Response(data)

    
#Trainers
@api_view(["GET"])
@permission_classes([AllowAny])  # or IsAuthenticated if needed
def trainer_list(request):
    trainers = TrainerProfile.objects.all()
    
    data = []
    for ind in trainers:
        data.append({
            "id": ind.id,
            "name": f"{ind.trainer.user.firstname} {ind.trainer.user.lastname}",  # comes from User model
            "specialization": ind.trainer.specialization,
            "phonenumber": ind.trainer.contact_number,
            "instagram": ind.instagram,
            "twitter": ind.twitter,
            "availableTimes": ["05:00 AM", "10:00 AM", "7:00 PM"],  # replace with real availability
        })
    return Response(data)


#Bookings
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_booking(request):
    """
    Expected JSON:
    {
        "session_type": "virtual",
        "instructor": "Ama Agyei",
        "date": "2025-08-20",
        "time": "09:30 AM"
    }
    """
    data = request.data
    print(data)
   
    session_type = data.get("session_type")
    instructor_name = data.get("instructor")
    date = data.get("date")
    time = data.get("time")

    customer = Customer.objects.get(user=request.user)

    if not (session_type and instructor_name and date and time):
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    # Example: you can store trainer as a User with role=trainer
    try:
        trainer = Trainer.objects.get(user__firstname=instructor_name.split()[0], user__lastname=instructor_name.split()[-1])
    except Trainer.DoesNotExist:
        return Response({"error": "Trainer not found"}, status=status.HTTP_404_NOT_FOUND)

    # Combine date + time into a datetime object
    
    start_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")

    # Assume fixed duration (e.g., 1 hr) or adjust later
    # end_time = start_time + datetime.timedelta(minutes=60)

    booking = Booking.objects.create(
        customer=customer,
        trainer=trainer,
        session_type=session_type,
        title=f"{session_type.capitalize()} Session",
        start_time=start_time,
    )

    return Response({
        "message": "Booking created successfully",
        "booking_id": booking.id
    }, status=status.HTTP_201_CREATED)

@api_view(["GET"])
def get_meeting(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        return Response({
            "meeting_id": booking.meeting_id,
            "customer": booking.customer.user.firstname,
            "trainer": booking.trainer.user.firstname,
        })
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def upcoming_sessions(request):
    user = request.user
    customer = Customer.objects.get(user=user)
    # get all future bookings for this user
    bookings = Booking.objects.filter(customer=customer, start_time__gte=now()).order_by("start_time")
    # print(bookings)
    data = []
    for booking in bookings:
        # check if current time is within 30 minutes of the meeting
        can_join = booking.start_time - timedelta(minutes=30) >= now() #Remember to change the sign

        data.append({
            "id": booking.id,
            "title": booking.title,
            "trainer": booking.trainer.user.fullname(),
            "customer": booking.customer.user.fullname(),
            "date": booking.start_time.strftime("%d %B, %Y"),
            "start_time": booking.start_time.strftime("%I:%M %p"),
            "session_started": booking.session_started,
            "can_join": can_join,
            # link to Jitsi meeting, e.g. generate based on booking id
            "meeting_url": f"https://meet.jit.si/winnyfit_{booking.meeting_id}"
        })

   
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def past_sessions(request):
    user = request.user
    customer = Customer.objects.get(user=user)
    # get all future bookings for this user
    bookings = Booking.objects.filter(customer=customer, start_time__lte=now()).order_by("start_time")
    # print(bookings)
    data = []
    for booking in bookings:
        data.append({
            "id": booking.id,
            "title": booking.title,
            "trainer": booking.trainer.user.fullname(),
            "customer": booking.customer.user.fullname(),
            "date": booking.start_time.strftime("%d %B, %Y"),
            "start_time": booking.start_time.strftime("%I:%M %p"),
            "session_started": booking.session_started,
        })

    print(data)
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def upcoming_trainer_sessions(request):
    user = request.user
    trainer = Trainer.objects.get(user=user)
    # get all future bookings for this user
    bookings = Booking.objects.filter(trainer=trainer, start_time__gte=now()).order_by("start_time")
    # print(bookings)
    data = []
    for booking in bookings:
        # check if current time is within 30 minutes of the meeting
        can_join = booking.start_time - timedelta(minutes=30) >= now() #Remember to change the sign

        data.append({
            "id": booking.id,
            "title": booking.title,
            "trainer": booking.trainer.user.fullname(),
            "customer": booking.customer.user.fullname(),
            "date": booking.start_time.strftime("%d %B, %Y"),
            "start_time": booking.start_time.strftime("%I:%M %p"),
            "session_started": booking.session_started,
            "can_join": can_join,
            # link to Jitsi meeting, e.g. generate based on booking id
            "meeting_url": f"https://meet.jit.si/winnyfit_{booking.meeting_id}"
        })

    print(data)
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def past_trainer_sessions(request):
    user = request.user
    trainer = Trainer.objects.get(user=user)
    # get all future bookings for this user
    bookings = Booking.objects.filter(trainer=trainer, start_time__lte=now()).order_by("start_time")
    # print(bookings)
    data = []
    for booking in bookings:
        data.append({
            "id": booking.id,
            "title": booking.title,
            "trainer": booking.trainer.user.fullname(),
            "customer": booking.customer.user.fullname(),
            "date": booking.start_time.strftime("%d %B, %Y"),
            "start_time": booking.start_time.strftime("%I:%M %p"),
        })

    print(data)
    return Response(data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request, booking_id):
    """
    Mark a booking's session as started. Only trainers can do this.
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        
        # Only trainer can start their session
        trainer = Trainer.objects.get(user=request.user)
        if booking.trainer != trainer:
            return Response({"error": "Only trainer can start the session"}, status=403)

        booking.session_started = True
        booking.save()
        return Response({"success": True, "session_started": True})
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)