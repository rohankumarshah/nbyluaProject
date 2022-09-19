from django.urls import include, path, reverse_lazy
from .views import SignUpView,  jobseeker_Home, ProfileView, ProfileEdit, create_profile
from . import views
from django.contrib.auth import views as auth_views  # import this

app_name = 'jobseeker'
urlpatterns = [
    path('', jobseeker_Home, name='jobseeker_home'),

    path('login', views.login_candidate, name='jobseeker/login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup', SignUpView.as_view(), name='jobseeker/register'),


    path('viewprofile/', ProfileView, name='profile'),
    path('profile_edit/', ProfileEdit, name='ProfileEdit'),
    path('create_profile/', ProfileEdit, name='create_profile'),
    # path('create_profile/',create_profile, name='create_profile'),

]
