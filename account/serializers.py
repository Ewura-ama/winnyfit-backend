from django.db import transaction, IntegrityError
from rest_framework import serializers
from .models import UserAccount, Trainer, TrainerProfile, Customer


# ---------- simple serializers used for representation ----------
class TrainerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainerProfile
        fields = ['avatar', 'instagram', 'facebook', 'twitter', 'linkedin', 'website', 'bio']


class UserAccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    avatar = serializers.SerializerMethodField()
    class Meta:
        model = UserAccount
        fields = ['id', 'firstname', 'lastname', 'password', 'email', 'role', 'avatar', 'is_active', 'is_staff']
        
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = UserAccount(**validated_data)
        user.set_password(password)  # hash password before saving
        user.save()
        return user
    
    # def get_avatar(self, obj):
    #     if obj.avatar:
    #         request = self.context.get('request')
    #         if request is not None:
    #             return request.build_absolute_uri(obj.avatar.url)
    #         return obj.avatar.url
    #     return None

    def get_avatar(self, obj):
        if obj.avatar:
            try:
                request = self.context.get('request', None)
                url = obj.avatar.url
                if request is not None:
                    return request.build_absolute_uri(url)
                return url  # fallback to relative if no request
            except Exception:
                return None
        return None



class CustomerCreateSerializer(serializers.ModelSerializer):
    user = UserAccountSerializer()

    class Meta:
        model = Customer
        fields = ['user', 'contact_number']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        
        user_serializer = UserAccountSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()  # this ensures password is hashed
        
        customer = Customer.objects.create(user=user, **validated_data)
        return customer



class TrainerSerializer(serializers.ModelSerializer):
    user = UserAccountSerializer(read_only=True)
    profile = TrainerProfileSerializer(read_only=True)

    class Meta:
        model = Trainer
        fields = [
            'id', 'user', 'specialization', 'date_of_birth',
            'contact_number', 'address', 'available', 'created_at',
            'profile'
        ]


# ---------- nested serializers used for creation ----------
class TrainerProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainerProfile
        # avatar is allowed here; DRF will handle file uploads through multipart requests
        fields = ['avatar', 'instagram', 'facebook', 'twitter', 'linkedin', 'website', 'bio']
        extra_kwargs = {
            'avatar': {'required': False, 'allow_null': True}
        }


class TrainerCreateSerializer(serializers.ModelSerializer):
    # Accept a nested profile object on creation
    profile = TrainerProfileCreateSerializer(required=False)

    class Meta:
        model = Trainer
        fields = ['specialization', 'date_of_birth', 'contact_number', 'address', 'available', 'profile']


# ---------- registration serializer that ties everything together ----------
class TrainerRegistrationSerializer(serializers.ModelSerializer):
    """
    Accepts:
    {
      "firstname": "...",
      "lastname": "...",
      "email": "...",
      "password": "...",
      "trainer": {
          "specialization": "...",
          "date_of_birth": "YYYY-MM-DD",
          "contact_number": "...",
          "address": "...",
          "available": "yes",
          "profile": {
              "avatar": <file>,
              "instagram": "...",
              ...
          }
      }
    }
    """
    trainer = TrainerCreateSerializer(write_only=True)
    # Return a full trainer representation after creation
    trainer_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserAccount
        fields = ['id', 'firstname', 'lastname', 'email', 'password', 'trainer', 'trainer_details']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

    def get_trainer_details(self, obj):
        # obj is the created user; fetch trainer via related_name 'staff_profile'
        try:
            trainer = obj.staff_profile
            return TrainerSerializer(trainer, context=self.context).data
        except Trainer.DoesNotExist:
            return None

    def validate_email(self, value):
        # normalize and lowercase (your manager already normalizes but good to ensure at serializer-level)
        return value.lower()

    def create(self, validated_data):
        trainer_data = validated_data.pop('trainer')
        profile_data = trainer_data.pop('profile', None)
        password = validated_data.pop('password')

        # Ensure role is trainer; ignore whatever client may have passed
        validated_data['role'] = 'trainer'

        with transaction.atomic():
            # create user and set password
            user = UserAccount(**validated_data)
            user.set_password(password)
            try:
                user.save()
            except IntegrityError as e:
                raise serializers.ValidationError({"email": "A user with this email already exists."})

            # create trainer. contact_number unique constraint may raise IntegrityError
            try:
                trainer = Trainer.objects.create(user=user, **trainer_data)
            except IntegrityError as e:
                # rollback will happen automatically because of the transaction.atomic()
                # map to a nicer message if it's the contact number:
                if 'contact_number' in str(e).lower() or 'unique' in str(e).lower():
                    raise serializers.ValidationError({"trainer": {"contact_number": "This contact number is already taken."}})
                raise serializers.ValidationError({"trainer": "Unable to create trainer. Detail: %s" % str(e)})

            # create profile if provided
            if profile_data:
                # avatar might be a file from request.FILES; DRF passes that in validated_data already
                TrainerProfile.objects.create(trainer=trainer, **profile_data)

        # return the user (trainer_details field will be used to get the nested trainer data)
        return user

    def to_representation(self, instance):
        """Return the created Trainer data (not just user)."""
        rep = super().to_representation(instance)
        # trainer_details already included via get_trainer_details
        return rep


