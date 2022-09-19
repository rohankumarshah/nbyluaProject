import re

import requests
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.utils.http import urlsafe_base64_decode
from user_custom.models import User_custom
from django.utils.encoding import force_text
from .models import Employer, Employer_profile, Employer_candidate_jobanswer, Employer_job, Employer_job_Applied, \
    Employer_jobquestion, Employer_expired_job, Employer_Subscription
from .forms import SignUpForm, ProfileRegisterForm, JobPostForm, JobsQuestionForm, QuestionFormset, keyWordFormset
from django.views.generic import View
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect, get_object_or_404

from jobseeker.models import Candidate_profile, Candidate_edu, Candidate_profdetail, Candidate_resume, Candidate_skills, \
    Candidate_expdetail, Candidate
from datetime import datetime
from django.forms import modelformset_factory
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required
from bs4 import BeautifulSoup

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}


class SignUpView(View):
    form_class = SignUpForm

    template_name = 'employer/signup.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        print(User_custom.objects.all())
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            emaill = form.cleaned_data['email']
            if User_custom.objects.filter(email=emaill).exists():

                return HttpResponse('User with same email already exists, Please try again with different Username!!')
            else:
                user = form.save(commit=False)
                user.username = user.email
                user.user_name = user.email
                user.is_active = True
                user.is_employeer = True
                user.save()

                return redirect('recruiter:employer/login')
                # username = form.cleaned_data['email']
                # password = form.cleaned_data['password1']
                #
                # # print(username)
                # # print(password)
                # user = authenticate(request, username=username, password=password)

                # if user is not None and user.is_employeer:
                #     login(request, user)
                #     return redirect('recruiter:employer_home')
                # return render(request, self.template_name, {'form': form})
        else:
            return render(request, self.template_name, {'form': form})


def login_employer(request):
    if request.user.is_authenticated and request.user.is_employeer:
        print(request.user)
        return redirect('recruiter:employer_home')
    else:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('pass')

            print(password)
            print(username)
            user = authenticate(request, username=username, password=password)
            print(user)

            if user is not None and user.is_employeer:
                login(request, user)
                if 'next' in request.POST:
                    return redirect(request.POST.get('next'))
                else:
                    return redirect('recruiter:employer_home')
            else:
                messages.info(request, 'Username OR password is incorrect')

        context = {}
        return render(request, 'index.html', context)
        # return render(request, 'employer/login.html', context)


@login_required(login_url='/')
def Home(request):
    jobs = []
    expired_job = []
    user = request.user
    if user is not None and user.is_employeer:
        if user.first_login:
            try:
                e = Employer.objects.get(user=user)
            except Employer.DoesNotExist:
                e = None
            # uncomment this after making the profile update correct
            # if Employer_profile.objects.get(employer=e):
            if e:
                try:
                    ep = Employer_profile.objects.get(employer=e)
                except Employer_profile.DoesNotExist:
                    ep = None
                job = Employer_job.objects.filter(employer_id=e)
                for j in job:
                    start_date = j.created_on
                    # print(start_date)
                    today = datetime.now()
                    # print(type(today))
                    stat_date = str(start_date)
                    start_date = stat_date[:19]
                    tday = str(today)
                    today = tday[:19]
                    s_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                    e_date = datetime.strptime(today, "%Y-%m-%d %H:%M:%S")
                    # print(s_date)
                    # print(e_date)
                    diff = abs((e_date - s_date).days)
                    print(diff)
                    try:
                        e_j = Employer_expired_job.objects.get(job_id=j)
                    except Employer_expired_job.DoesNotExist:
                        e_j = None
                    if diff > 30:
                        if e_j:
                            expired_job.append(j)

                        else:
                            Employer_expired_job.objects.create(job_id=j).save()
                            expired_job.append(j)
                    elif e_j:
                        expired_job.append(j)
                    else:
                        jobs.append(j)
                context = {'jobs': jobs, 'expired': expired_job, 'ep': ep}
                return render(request, 'employer/job-post.html', context)
            else:
                return redirect('/')
        else:
            user.first_login = True
            user.save()
            return redirect('recruiter:job_post')
    else:
        return redirect('/')


@login_required(login_url='/')
def job_detail(request, pk):
    user = request.user
    if user is not None and user.is_employeer:
        e = Employer.objects.get(user=request.user)
        job = Employer_job.objects.get(pk=pk)
        company = Employer_profile.objects.get(employer=e)
        # candidate_Applied = Employer_job_Applied.objects.filter(job_id=job)
        # objects = zip(job,candidate_Applied)
        return render(request, 'employer/job_details.html', {'job': job, 'c': company})
    else:
        return redirect('/')


@login_required(login_url='/')
def view_applied_candidate(request, pk):
    user = request.user
    if user is not None and user.is_employeer:
        e = Employer.objects.get(user=user)
        try:
            eS = Employer_Subscription.objects.get(emp_id=e)
        except Employer_Subscription.DoesNotExist:
            eS = None

        if eS is not None:
            start_date = eS.subscribed_on
            today = datetime.now()
            stat_date = str(start_date)
            start_date = stat_date[:19]
            tday = str(today)
            today = tday[:19]
            s_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            e_date = datetime.strptime(today, "%Y-%m-%d %H:%M:%S")
            # print(s_date)
            # print(e_date)
            diff = abs((e_date - s_date).days)
            print(diff)
            if diff > eS.subscription_interval:
                eS.delete()

            candidate_user = []
            candidate_profile = []
            education_profile = []
            professional_profile = []
            skill = []
            resume = []
            expect = []
            candidate_answer = []
            # Question=[]
            e = Employer.objects.get(user=request.user)

            cp = Employer_profile.objects.get(employer=e)
            job = Employer_job.objects.get(pk=pk)

            valkey = request.GET.get('keyword_box', None)
            valcomp = request.GET.get('company_box', None)
            valloc = request.GET.get('location_box', None)
            valmin_box = request.GET.get('min_box', None)
            valmax_box = request.GET.get('max_box', None)
            valmin_salary_box = request.GET.get('min_salary_box', None)
            valmax_salary_box = request.GET.get('max_salary_box', None)
            question = Employer_jobquestion.objects.filter(job_id=job)
            candidate_Applied = Employer_job_Applied.objects.filter(job_id=job)
            for can in candidate_Applied:
                c = can.candidate_id
                c_p = Candidate_profile.objects.get(user_id=c)
                c_e = Candidate_edu.objects.filter(user_id=c).first()
                p_p = Candidate_profdetail.objects.filter(user_id=c)
                c_ed = Candidate_expdetail.objects.get(user_id=c)
                c_sk = Candidate_skills.objects.filter(user_id=c)
                if (valkey is not None) | (valloc is not None) | (valcomp is not None) | (valmax_box is not None) | (
                        valmin_box is not None) | (
                        valmin_box is not None) | (valmax_salary_box is not None) | (valmin_salary_box is not None):
                    for c_sks in c_sk:
                        try:
                            c_skss = c_sks.skill
                        except c_sks.DoesNotExist:
                            pass
                        if c_skss == valkey:

                            candidate_profile.append(c_p)
                            print("working filter")
                            print(candidate_profile)
                            candidate_user.append(c.user)
                            education_profile.append(c_e)
                            professional_profile.append(p_p)
                            expect.append(c_ed)
                            skill.append(c_sk)

                            resume.append(Candidate_resume.objects.get(user_id=c))
                            for q in question:
                                candidate_answer.append(
                                    Employer_candidate_jobanswer.objects.get(question_id=q, candidate_id=c))
                            continue
                        else:
                            pass

                    if valloc in c_ed.prefer_location:
                        print(valloc)

                        candidate_profile.append(c_p)
                        print("working location filter")
                        print(candidate_profile)
                        candidate_user.append(c.user)
                        education_profile.append(c_e)
                        professional_profile.append(p_p)
                        expect.append(c_ed)
                        skill.append(c_sk)

                        resume.append(Candidate_resume.objects.get(user_id=c))
                        for q in question:
                            candidate_answer.append(
                                Employer_candidate_jobanswer.objects.get(question_id=q, candidate_id=c))
                        continue
                    for p_ps in p_p:
                        try:
                            p_pss = p_ps.organization
                        except c_sks.DoesNotExist:
                            pass
                        if p_pss == valcomp:

                            candidate_profile.append(c_p)
                            print("working filter")
                            print(candidate_profile)
                            candidate_user.append(c.user)
                            education_profile.append(c_e)
                            professional_profile.append(p_p)
                            expect.append(c_ed)
                            skill.append(c_sk)

                            resume.append(Candidate_resume.objects.get(user_id=c))
                            for q in question:
                                candidate_answer.append(
                                    Employer_candidate_jobanswer.objects.get(question_id=q, candidate_id=c))
                            continue
                        else:
                            pass
                    if valmin_box <= c_ed.Total_Working <= valmax_box:

                        candidate_profile.append(c_p)
                        print("working location filter")
                        print(candidate_profile)
                        candidate_user.append(c.user)
                        education_profile.append(c_e)
                        professional_profile.append(p_p)
                        expect.append(c_ed)
                        skill.append(c_sk)

                        resume.append(Candidate_resume.objects.get(user_id=c))
                        for q in question:
                            candidate_answer.append(
                                Employer_candidate_jobanswer.objects.get(question_id=q, candidate_id=c))
                        continue
                    if valmin_salary_box <= c_ed.exp_salary <= valmax_salary_box:

                        candidate_profile.append(c_p)
                        print("working location filter")
                        print(candidate_profile)
                        candidate_user.append(c.user)
                        education_profile.append(c_e)
                        professional_profile.append(p_p)
                        expect.append(c_ed)
                        skill.append(c_sk)

                        resume.append(Candidate_resume.objects.get(user_id=c))
                        for q in question:
                            candidate_answer.append(
                                Employer_candidate_jobanswer.objects.get(question_id=q, candidate_id=c))
                        continue


                    else:
                        pass
                else:
                    candidate_profile.append(c_p)
                    candidate_user.append(c.user)
                    education_profile.append(c_e)
                    professional_profile.append(p_p)
                    expect.append(c_ed)
                    skill.append(c_sk)

                    resume.append(Candidate_resume.objects.get(user_id=c))
                    for q in question:
                        candidate_answer.append(Employer_candidate_jobanswer.objects.get(question_id=q, candidate_id=c))

            quest = zip(question, candidate_answer)
            # print(candidate_answer)
            objects = zip(candidate_profile, education_profile, professional_profile, skill, resume,
                          candidate_user, candidate_Applied, expect)

            return render(request, 'employer/job_candidate.html',
                          {'candidate': objects, 'job': job, 'question': question, 'answer': candidate_answer,
                           'cp': cp})



    else:
        return redirect('/')


@login_required(login_url='/')
def delete_job(request, pk):
    Employer_job.objects.get(pk=pk).delete()

    return redirect('recruiter:employer_home')


@login_required(login_url='/')
def publish_job(request, pk):
    e = Employer_job.objects.get(pk=pk)
    e.is_save_later = False
    e.save()
    return redirect('recruiter:job_detail', pk)


@login_required(login_url='/')
def ProfileView(request):
    u = request.user
    e = Employer.objects.get(user=u)
    profile = Employer_profile.objects.get(employer=e)

    return render(request, 'employer/skills.html', {
        "user": u,
        "profile": profile,

    })


@login_required(login_url='/')
def ProfileEdit(request):
    try:
        profile = Employer.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        profile = None
    print(profile)
    print('notrun', request.method)
    if profile is not None:
        if request.method == 'POST':
            print('run', request.method)
            form1 = ProfileRegisterForm(data=request.POST or None, files=request.FILES or None)

            if form1.is_valid():
                print(form1.cleaned_data.get('profile_pic'))
                if form1.cleaned_data.get('birth_date'):
                    f1 = form1.save(commit=False)
                    try:
                        c = Employer_profile.objects.get(employer=profile)
                    except Employer_profile.DoesNotExist:
                        c = None
                    if c:
                        c.delete()

                    f1.user_id = profile

                    f1.save()

            return redirect('jobseeker:ProfileEdit')
        print(request.method)
        try:
            c = Employer_profile.objects.get(employer=profile)
        except Employer_profile.DoesNotExist:
            c = None

        form1 = ProfileRegisterForm(instance=c)

        return render(request, 'jobseeker/Profile.html',
                      {"form1": form1, 'c': c})

    else:
        return redirect('/')


@login_required(login_url='/')
def job_post(request):
    user = request.user
    if user is not None and user.is_employeer:
        e = Employer.objects.get(user=request.user)
        if request.method == 'GET':
            form1 = JobPostForm(request.GET or None)
            formset = QuestionFormset(request.GET or None)
        elif request.method == 'POST':
            form1 = JobPostForm(request.POST)
            formset = QuestionFormset(request.POST)
            if form1.is_valid():
                f1 = form1.save(commit=False)
                f1.employer_id = e
                f1.save()
                # print(f1)
            if formset.is_valid():
                # print("formset:")
                # print(formset)
                for form in formset:

                    quest = form.cleaned_data.get('question')
                    # ans =form.cleaned_data.get('answer_size')

                    if quest:
                        Employer_jobquestion(job_id=f1, question=quest).save()

                return redirect('recruiter:employer_home')
        #
        #         form2 = JobsQuestionForm(request.POST)
        #         if form2.is_valid():
        #             f2 = form2.save(commit=False)
        #             f2.employer_id = e
        #             f2.job_id = f1
        #             f2.save()
        #             f1.save()
        # form1 = JobPostForm(request.POST)
        # form2 = JobsQuestionForm(request.POST)
        return render(request, 'employer/addjob.html', {"form1": form1, "form2": formset})
    else:
        return redirect('/')
