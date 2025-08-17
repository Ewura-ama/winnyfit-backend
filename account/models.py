from django.db import models
from django.contrib.auth.models import User, AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid
class UserAccountManager(BaseUserManager):
    def create_user(self, email, firstname, lastname, password=None, role=None):
        if not email:
            raise ValueError('Users must have an email address')
        if not firstname:
            raise ValueError('Users must have a name')

        email = self.normalize_email(email)
        email = email.lower()

        user = self.model(
            email=email,
            firstname=firstname,
            lastname=lastname,
            role=role
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, firstname, lastname, password=None):
        user = self.create_user(
            email,
            firstname=firstname,
            lastname=lastname,
            password=password,
            role='administrative'  # Superusers have the 'admin' role
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class UserAccount(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('trainer', 'Trainer'),
        ('customer', 'Customer'),
        ('administrative', 'Administrative'),
    
    )

    firstname = models.CharField(max_length=255, default='')
    lastname = models.CharField(max_length=255, default='')
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstname', 'lastname']

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='useraccount_set',  # Custom related name to avoid clashes
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='useraccount_set',  # Custom related name to avoid clashes
        blank=True,
    )
    def __str__(self):
        return self.email
    
    def fullname(self):
        return f"{self.firstname} {self.lastname}"
    


class Customer(models.Model):
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, related_name='customer_profile')
    contact_number = models.CharField(db_column='contactnumber', unique=True, max_length=20)
    reg_date = models.DateTimeField(default=timezone.now)
    class Meta:
        managed = True
        db_table = 'customers'

    def __str__(self):
        return f"{self.user.firstname} {self.user.lastname}"


class Trainer(models.Model):
    
    SPECIALIZATION_CHOICES = (
        ('personal-training', 'Personal Training'),
        ('group-fitness', 'Group Fitness'),
        ('strength-conditioning', 'Strength and Conditioning'),
        ('weight-loss-coaching', 'Weight Loss Coaching'),
        ('rehabilitation-training', 'Rehabilitation Training')
    )
    

    AVAILABILITY_CHOICES = (
        ('yes', 'Yes'),
        ('no', 'No')
       
    )
    
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, related_name='staff_profile')
    specialization = models.CharField(choices=SPECIALIZATION_CHOICES, max_length=50, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)  
    contact_number = models.CharField(unique=True, max_length=20)
    address = models.CharField(max_length=255)
    available = models.CharField(choices=AVAILABILITY_CHOICES, default="yes", blank=True, max_length=20)
    # appointments = models.ManyToManyField('training.Appointment', related_name='appointments', blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = True
        db_table = 'trainer'
        verbose_name = 'Trainer'
        verbose_name_plural = 'Trainers'
        indexes = [
            models.Index(fields=['contact_number']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.firstname} {self.user.lastname} - {self.specialization}"
    
class TrainerProfile(models.Model):
    trainer = models.OneToOneField('Trainer', on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/')
    instagram = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'trainer_profile'

    def __str__(self):
        return f"Profile of {self.trainer.user.firstname} {self.trainer.user.lastname}"





class Booking(models.Model):
    AVAILABLE_CHOICES = (
        ('virtual', 'VIRTUAL'),
        ('in-person', 'IN-PERSON')
       
    )
    customer = models.ForeignKey(Customer, related_name="bookings", on_delete=models.CASCADE)
    trainer = models.ForeignKey(Trainer, related_name="sessions", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    session_type = models.CharField(choices=AVAILABLE_CHOICES, blank=True, max_length=20)
    start_time = models.DateTimeField()
    session_started = models.BooleanField(default=False)
    meeting_id = models.CharField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.meeting_id:
            self.meeting_id = str(uuid.uuid4())  # unique Jitsi room name
        super().save(*args, **kwargs)
