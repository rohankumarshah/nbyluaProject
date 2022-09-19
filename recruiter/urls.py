from django.urls import include, path, reverse_lazy
from .views import SignUpView, Home, login_employer, delete_job, job_detail, publish_job, \
    view_applied_candidate, job_post, ProfileView,ProfileEdit
from . import views
from django.contrib.auth import views as auth_views  # import this

app_name = 'recruiter'
urlpatterns = [
    path('', Home, name='employer_home'),
    path('addjob/', job_post, name='job_post'),
    path('deletejob/<int:pk>', delete_job, name='delete_job'),
    path('jobdetail/<int:pk>', job_detail, name='job_detail'),
    path('jobdetail/publishjob/<int:pk>', publish_job, name='publish_job'),
    path('jobdetail/applied_candidate/<int:pk>', view_applied_candidate, name='view_applied_candidate'),

    path('viewprofile/', ProfileView, name='profile'),
    path('profile_edit/', ProfileEdit, name='ProfileEdit'),
    path('create_profile/', ProfileEdit, name='create_profile'),
    path('login', login_employer, name='employer/login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup', SignUpView.as_view(), name='employer/register'),

]
