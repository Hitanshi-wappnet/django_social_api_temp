import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from authentication.serializers import RegistrationSerializer
from authentication.models import VerifyOtp
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated


def send_mail_otp(self, user, otp):
    subject = "Forget password"
    message = "Here is the otp to Reset your password." + str(otp)
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )


class RegisterView(APIView):
    """
    API endpoint for register User.
    It returns success response of registration or error.
    """

    def post(self, request):
        # Validate user registration data with serializer
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create a new user with validated data
            serializer.save()

            # Return success response
            response = {"status": True,
                        "message": "Registartion is Successfull!!"}
            return Response(data=response, status=status.HTTP_202_ACCEPTED)

        else:
            # Return error response with serializer errors
            response = {"status": False,
                        "message": serializer.errors,
                        "data": None}
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    API view for user login.User can be authenticated using email and password.
    If user is verified then get token key otherwise get error.
    """

    def post(self, request):
        # Getting the detail entered by user
        email = request.data.get("email")
        password = request.data.get("password")

        # check if the user not entered data
        if email is None or password is None:
            response = {
                "status": False,
                "message": "Provide email and password",
                "data": None,
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)

        # Login logic using AuthTokenSerializer
        if User.objects.filter(email=email).exists():
            username = User.objects.get(email=email).username
            data = {"username": username, "password": password}
            serializer = AuthTokenSerializer(data=data)
            if serializer.is_valid():
                user = serializer.validated_data["user"]

                # generate or get token for user
                token, _ = Token.objects.get_or_create(user=user)

                # Return success response
                response = {
                    "status": True,
                    "message": "Login is Successful!!",
                    "data": token.key,
                }
                return Response(data=response, status=status.HTTP_202_ACCEPTED)
            else:
                response = {
                    "status": False,
                    "message": "Provide correct email and password",
                    "data": None,
                }
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        else:
            response = {
                "status": False,
                "message": "Provide correct email address",
                "data": None,
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    """
    API endpoint for Reset password.
    It returns success response of email getting otp or error message.
    """

    def post(self, request):
        # retrieve email id entered by user
        email = request.data.get("email")

        # Check if email was provided in the request
        if email is None:
            response = {
                "status": False,
                "message": "Provide email address!!",
                "data": None,
            }
            return Response(data=response, status=status.HTTP_200_OK)

        # Check if a user with that email exists
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)

            # Generate a random 4-digit OTP
            otp = random.randint(1000, 9999)
            generated_otp = otp

            # Save the OTP to the database
            Forget_password = VerifyOtp(user=user, otp=generated_otp)
            Forget_password.save()

            # Send an email to the user containing the OTP
            send_mail_otp(self, user, otp)

            # Return a success response.
            response = {
                "status": True,
                "message": "Email sent to Reset your password!!",
            }
            return Response(data=response, status=status.HTTP_200_OK)
        else:
            # If no user with that email exists, return an error message
            response = {
                "status": False,
                "message": "Provide correct email id!!",
                "data": None,
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)


class VerifyOtpView(APIView):
    """
    This view handles verifying an OTP of Forget Password user.
    If the otp is verified then generate new token else get error message.
    """

    def post(self, request):
        # get the otp entered by user
        new_otp = request.data.get("otp")

        # check if user not entered data
        if new_otp is None:
            response = {"status": False,
                        "message": "Provide OTP!!",
                        "data": None}
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)

        # Get the Verifyotp object with the given OTP
        if VerifyOtp.objects.filter(otp=new_otp).exists():
            forget_password = VerifyOtp.objects.get(otp=new_otp)
            user = forget_password.user

            if user:
                # Delete the user's old auth token and generate a new one
                token = Token.objects.get(user=forget_password.user)
                token.delete()
                forget_password.delete()
                token = Token.objects.create(user=user)
                # Return a success response.
                response = {
                    "status": True,
                    "message": "OTP Verified SuccessFully!!",
                    "Token": token.key,
                }
                return Response(data=response, status=status.HTTP_200_OK)
            else:
                response = {
                    "status": False,
                    "message": "User does not exist",
                    "data": None,
                }
                return Response(data=response,
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            # If the OTP is incorrect, return an error message
            response = {"status": False,
                        "message": "OTP is incorrect!!",
                        "data": None}
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):

    # Allow only authenticated users
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):

        # retrieve username and new password from user entered data
        username = request.data.get("username")
        new_password = request.data.get("newpassword")

        if username is None or new_password is None:
            response = {
                "status": False,
                "message": "Provide username and newpassword.",
                "data": None,
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)

        # Get the user object based on the username
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)

            # Set the user's password to the new password and save
            user.set_password(new_password)
            user.save()

            # Return a success response.
            response = {
                "status": True,
                "message": "Password Changed Successfully.",
            }
            return Response(data=response, status=status.HTTP_200_OK)
        else:
            response = {
                "status": False,
                "message": "Provide Correct username.",
                "data": None,
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    """
    API view for user logout.
    User can logout by deleting the authentication token.
    """

    def post(self, request):

        # retrieve data entered by user
        username = request.data.get("username")

        if username is None:
            response = {
                "status": False,
                "message": "Provide username to logout",
                "data": None
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)

        # If username exists then get token
        if User.objects.filter(username=username).exists():

            user_id = User.objects.get(username=username).id

            # Get the user's token
            token = Token.objects.get(user=user_id)
            token.delete()

            # Return success response
            response = {"status": True, "message": "Logout is Successful!!"}
            return Response(data=response, status=status.HTTP_200_OK)

        # If username is invalid then returns an error response
        else:
            response = {
                "status": False,
                "message": "Invalid user name",
                "data": None
            }
            return Response(data=response, status=status.HTTP_400_BAD_REQUEST)
