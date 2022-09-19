import re
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.http import urlsafe_base64_decode
from user_custom.models import User_custom
from django.utils.encoding import force_text
from .models import Candidate, Candidate_profile, Candidate_edu, Candidate_skills, Candidate_profdetail, \
    Candidate_resume, Resume_order, Candidate_expdetail, Resume_headline
from .forms import SignUpForm, ProfileRegisterForm, ProfileRegisterForm_edu, ProfileRegisterForm_profdetail, \
    ProfileRegisterForm_resume, ProfileRegistration_expdetail, ProfileRegistration_skills, Resumeforming_Entery, \
    Resumeforming_Executive, Resumeforming_Mid, Resumeforming_senior, Resume_headlineForm
from django.views.generic import View
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect

from recruiter.models import Employer_job, Employer_jobquestion, Employer_job_Applied, Employer_job_Like, \
    Employer_job_Saved, Employer_candidate_jobanswer, Employer_expired_job, Employer_profile


from django.contrib.auth.decorators import login_required
from django.core.files import File
from io import BytesIO




class SignUpView(View):
    form_class = SignUpForm

    template_name = 'jobseeker/signup.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        print(User_custom.objects.all())
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            emaill = form.cleaned_data['email']
            # print(form.password1)
            if User_custom.objects.filter(email=emaill).exists():

                return HttpResponse('User with same email already exists, Please try again with different Username!!')
            else:
                user = form.save(commit=False)
                user.username = user.email
                user.user_name = user.email
                user.is_active = True  # change this to False after testing
                user.is_candidate = True
                user.save()
                new_candidate = Candidate(user=user, is_email_verified=False)  # change is email to False after testing
                new_candidate.save()

                username = form.cleaned_data['email']
                password = form.cleaned_data['password1']

                # print(username)
                # print(password)
                user = authenticate(request, username=username, password=password)

                if user is not None and user.is_candidate:
                    login(request, user)
                    return redirect('jobseeker:jobseeker_home')
                # return render(request, self.template_name, {'form': form})
        else:
            return render(request, self.template_name, {'form': form})

def index(request):
    return render(request, 'index.html')


def login_candidate(request):
    if request.user.is_authenticated and request.user.is_candidate:
        print(request.user)
        return redirect('jobseeker:jobseeker_home')
    else:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('pass')
            Pattern = re.compile("(0|91)?[0-9]{10}")
            if Pattern.match(username):
                c = Candidate_profile.objects.get(phone=username)
                username = c.employer.user.username
            # print(username)
            # print(password)
            user = authenticate(request, username=username, password=password)

            if user is not None and user.is_candidate:
                login(request, user)
                if 'next' in request.POST:
                    return redirect(request.POST.get('next'))
                else:
                    return redirect('jobseeker:jobseeker_home')
            else:
                messages.info(request, 'Username OR password is incorrect')

        context = {}
        return render(request, 'index.html', context)
        # return render(request, 'jobseeker/login.html', context)


@login_required(login_url='/')
def jobseeker_Home(request):
    if request.method == 'GET':
        val = request.GET.get('search_box', None)
        print("val")
        print(val)
        if val:
            job = Employer_job.objects.filter(
                Q(job_title__icontains=val) |
                Q(skill__icontains=val) |
                Q(job_description__icontains=val) |
                Q(job_salary__icontains=val) |
                Q(job_location__icontains=val)
            ).distinct()
            print(job)
            jobs = []
            job_ques = []
            relevant_jobs = []
            common = []
            companyprofile = []
            job_skills = []
            u = request.user
            if u is not None and u.is_candidate:
                c = Candidate.objects.get(user=u)
                try:
                    cp = Candidate_profile.objects.get(user_id=c)
                except Candidate_profile.DoesNotExist:
                    cp = None
                try:
                    cep = Candidate_expdetail.objects.get(user_id=c)
                except Candidate_expdetail.DoesNotExist:
                    cep = None
                try:
                    cr = Candidate_resume.objects.get(user_id=c)
                except Candidate_resume.DoesNotExist:
                    cr = None
                if u.first_login:

                    skills = Candidate_skills.objects.filter(user_id=c)
                    print("skills")
                    print(skills)
                    if len(skills) != 0:

                        my_sk = []
                        j = 0
                        for i in skills:
                            my_sk.insert(j, i.skill.lower())
                            j = j + 1

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
                            if diff > 30:
                                # expired_job.append(j)
                                Employer_expired_job.objects.create(job_id=j).save()

                            else:
                                jobs.append(j)

                        for job in jobs:
                            skills = []
                            sk = str(job.skill).split(",")
                            for i in sk:
                                skills.append(i.strip().lower())
                            common_skills = list(set(my_sk) & set(skills))
                            if len(common_skills) != 0:
                                e = job.employer_id
                                companyprofile.append(Employer_profile.objects.get(employer=e))
                                try:
                                    userS = Employer_job_Saved.objects.get(job_id=job.pk, candidate_id=c)
                                    # print(userS.job_id)
                                except Employer_job_Saved.DoesNotExist:
                                    userS = None
                                try:
                                    userA = Employer_job_Applied.objects.get(job_id=job.pk, candidate_id=c)
                                    # print(userA.job_id)
                                except Employer_job_Applied.DoesNotExist:
                                    userA = None

                                if userA:
                                    # print(userA)
                                    continue
                                if userS:
                                    # print(userS)
                                    continue
                                relevant_jobs.append(job)
                                common.append(len(common_skills))
                                job_skills.append(len(skills))
                                job_ques.append(Employer_jobquestion.objects.filter(job_id=job))

                        pj = Paginator(relevant_jobs, 5)
                        pjt = Paginator(relevant_jobs, 5)
                        pc = Paginator(common, 5)
                        pjs = Paginator(job_skills, 5)
                        pjq = Paginator(job_ques, 5)
                        pcp = Paginator(companyprofile, 5)
                        page_num = request.GET.get('page', 1)
                        try:
                            pj_objects = pj.page(page_num)
                            pjt_objects = pjt.page(page_num)
                            pc_objects = pc.page(page_num)
                            pjs_objects = pjs.page(page_num)
                            pjq_objects = pjq.page(page_num)
                            pcp_objects = pcp.page(page_num)
                        except EmptyPage:
                            pj_objects = pj.page(1)
                            pjt_objects = pjt.page(1)
                            pc_objects = pc.page(1)
                            pjs_objects = pjs.page(1)
                            pjq_objects = pjq.page(1)
                            pcp_objects = pcp.page(1)
                        objects = zip(pj_objects, pc_objects, pjs_objects, pjq_objects, pcp_objects)

                        return render(request, 'jobseeker/home.html',
                                      {'jobs': objects, 'c': c, 'cp': cp, 'cep': cep, 'cr': cr, 'pjs': pjt_objects})
                    else:

                        print("len job")
                        print(len(job))
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
                            # print(diff)
                            if diff > 30:
                                # expired_job.append(j)
                                Employer_expired_job.objects.create(job_id=j).save()

                            else:
                                jobs.append(j)
                            print("len")
                            print(len(jobs))
                        for jo in jobs:
                            skills = []
                            sk = str(jo.skill).split(",")
                            for i in sk:
                                skills.append(i.strip().lower())
                            common_skill = []
                            e = jo.employer_id
                            companyprofile.append(Employer_profile.objects.get(employer=e))
                            try:
                                userS = Employer_job_Saved.objects.get(job_id=jo.pk, candidate_id=c)
                                # print(userS.job_id)
                            except Employer_job_Saved.DoesNotExist:
                                userS = None
                            try:
                                userA = Employer_job_Applied.objects.get(job_id=jo.pk, candidate_id=c)
                                # print(userA.job_id)
                            except Employer_job_Applied.DoesNotExist:
                                userA = None

                            if userA:
                                # print(userA)
                                continue
                            if userS:
                                # print(userS)
                                continue
                            relevant_jobs.append(jo)
                            print("job:")
                            print(jo)

                            common.append(len(common_skill))
                            job_skills.append(len(skills))
                            job_ques.append(Employer_jobquestion.objects.filter(job_id=jo))
                        print("job_quest:")
                        print(job_ques)
                        print("relevant_jobs")
                        print(len(relevant_jobs))
                        pj = Paginator(relevant_jobs, 5)
                        pjt = Paginator(relevant_jobs, 5)
                        pc = Paginator(common, 5)
                        pjs = Paginator(job_skills, 5)
                        pjq = Paginator(job_ques, 5)
                        pcp = Paginator(companyprofile, 5)
                        page_num = request.GET.get('page', 1)
                        try:
                            pj_objects = pj.page(page_num)
                            pjt_objects = pjt.page(page_num)
                            pc_objects = pc.page(page_num)
                            pjs_objects = pjs.page(page_num)
                            pjq_objects = pjq.page(page_num)
                            pcp_objects = pcp.page(page_num)
                        except EmptyPage:
                            pj_objects = pj.page(1)
                            pjt_objects = pjt.page(1)
                            pc_objects = pc.page(1)
                            pjs_objects = pjs.page(1)
                            pjq_objects = pjq.page(1)
                            pcp_objects = pcp.page(1)
                        objects = zip(pj_objects, pc_objects, pjs_objects, pjq_objects, pcp_objects)

                        return render(request, 'jobseeker/home.html',
                                      {'jobs': objects, 'c': c, 'cp': cp, 'cep': cep, 'cr': cr, 'pjs': pjt_objects})


        else:
            jobs = []
            job_ques = []
            relevant_jobs = []
            common = []
            companyprofile = []
            job_skills = []
            u = request.user
            if u is not None and u.is_candidate:
                c = Candidate.objects.get(user=u)
                try:
                    cp = Candidate_profile.objects.get(user_id=c)
                except Candidate_profile.DoesNotExist:
                    cp = None
                try:
                    cep = Candidate_expdetail.objects.get(user_id=c)
                except Candidate_expdetail.DoesNotExist:
                    cep = None
                try:
                    cr = Candidate_resume.objects.get(user_id=c)
                except Candidate_resume.DoesNotExist:
                    cr = None
                if u.first_login:

                    skills = Candidate_skills.objects.filter(user_id=c)
                    print(skills)
                    if len(skills) != 0:

                        my_sk = []
                        j = 0
                        for i in skills:
                            my_sk.insert(j, i.skill.lower())
                            j = j + 1
                        job = Employer_job.objects.all()
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
                            if diff > 30:
                                # expired_job.append(j)
                                Employer_expired_job.objects.create(job_id=j).save()

                            else:
                                jobs.append(j)

                        for job in jobs:
                            skills = []
                            sk = str(job.skill).split(",")
                            for i in sk:
                                skills.append(i.strip().lower())
                            common_skills = list(set(my_sk) & set(skills))
                            if len(common_skills) != 0:
                                e = job.employer_id
                                companyprofile.append(Employer_profile.objects.get(employer=e))
                                try:
                                    userS = Employer_job_Saved.objects.get(job_id=job.pk, candidate_id=c)
                                    # print(userS.job_id)
                                except Employer_job_Saved.DoesNotExist:
                                    userS = None
                                try:
                                    userA = Employer_job_Applied.objects.get(job_id=job.pk, candidate_id=c)
                                    # print(userA.job_id)
                                except Employer_job_Applied.DoesNotExist:
                                    userA = None

                                if userA:
                                    # print(userA)
                                    continue
                                if userS:
                                    # print(userS)
                                    continue
                                relevant_jobs.append(job)
                                common.append(len(common_skills))
                                job_skills.append(len(skills))
                                job_ques.append(Employer_jobquestion.objects.filter(job_id=job))
                        pj = Paginator(relevant_jobs, 5)
                        pjt = Paginator(relevant_jobs, 5)
                        pc = Paginator(common, 5)
                        pjs = Paginator(job_skills, 5)
                        pjq = Paginator(job_ques, 5)
                        pcp = Paginator(companyprofile, 5)
                        page_num = request.GET.get('page', 1)
                        try:
                            pj_objects = pj.page(page_num)
                            pjt_objects = pjt.page(page_num)
                            pc_objects = pc.page(page_num)
                            pjs_objects = pjs.page(page_num)
                            pjq_objects = pjq.page(page_num)
                            pcp_objects = pcp.page(page_num)
                        except EmptyPage:
                            pj_objects = pj.page(1)
                            pjt_objects = pjt.page(1)
                            pc_objects = pc.page(1)
                            pjs_objects = pjs.page(1)
                            pjq_objects = pjq.page(1)
                            pcp_objects = pcp.page(1)
                        objects = zip(pj_objects, pc_objects, pjs_objects, pjq_objects, pcp_objects)

                        return render(request, 'jobseeker/home.html',
                                      {'jobs': objects, 'c': c, 'cp': cp, 'cep': cep, 'cr': cr, 'pjs': pjt_objects})
                    else:
                        job = Employer_job.objects.all()
                        print("len job")
                        print(len(job))
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
                            # print(diff)
                            if diff > 30:
                                # expired_job.append(j)
                                Employer_expired_job.objects.create(job_id=j).save()

                            else:
                                jobs.append(j)
                            print("len")
                            print(len(jobs))
                        for jo in jobs:
                            skills = []
                            sk = str(jo.skill).split(",")
                            for i in sk:
                                skills.append(i.strip().lower())
                            common_skill = []
                            e = jo.employer_id
                            companyprofile.append(Employer_profile.objects.get(employer=e))
                            try:
                                userS = Employer_job_Saved.objects.get(job_id=jo.pk, candidate_id=c)
                                # print(userS.job_id)
                            except Employer_job_Saved.DoesNotExist:
                                userS = None
                            try:
                                userA = Employer_job_Applied.objects.get(job_id=jo.pk, candidate_id=c)
                                # print(userA.job_id)
                            except Employer_job_Applied.DoesNotExist:
                                userA = None

                            if userA:
                                # print(userA)
                                continue
                            if userS:
                                # print(userS)
                                continue
                            relevant_jobs.append(jo)
                            print("job:")
                            print(jo)

                            common.append(len(common_skill))
                            job_skills.append(len(skills))
                            job_ques.append(Employer_jobquestion.objects.filter(job_id=jo))
                        print("job_quest:")
                        print(job_ques)
                        print("relevant_jobs")
                        print(len(relevant_jobs))
                        pj = Paginator(relevant_jobs, 5)
                        pjt = Paginator(relevant_jobs, 5)
                        pc = Paginator(common, 5)
                        pjs = Paginator(job_skills, 5)
                        pjq = Paginator(job_ques, 5)
                        pcp = Paginator(companyprofile, 5)
                        page_num = request.GET.get('page', 1)
                        try:
                            pj_objects = pj.page(page_num)
                            pjt_objects = pjt.page(page_num)
                            pc_objects = pc.page(page_num)
                            pjs_objects = pjs.page(page_num)
                            pjq_objects = pjq.page(page_num)
                            pcp_objects = pcp.page(page_num)
                        except EmptyPage:
                            pj_objects = pj.page(1)
                            pjt_objects = pjt.page(1)
                            pc_objects = pc.page(1)
                            pjs_objects = pjs.page(1)
                            pjq_objects = pjq.page(1)
                            pcp_objects = pcp.page(1)
                        objects = zip(pj_objects, pc_objects, pjs_objects, pjq_objects, pcp_objects)

                        return render(request, 'jobseeker/home.html',
                                      {'jobs': objects, 'c': c, 'cp': cp, 'cep': cep, 'cr': cr, 'pjs': pjt_objects})

                else:
                    u.first_login = True
                    u.save()
                    return redirect('jobseeker:create_profile')
            else:
                return redirect('/')

    if request.method == 'POST':
        print(request.POST)
        pk = request.POST.get('pk')
        print(pk)
        c = Candidate.objects.get(user=request.user)
        job = Employer_job.objects.get(pk=pk)
        questions = Employer_jobquestion.objects.filter(job_id=job)
        for q in questions:
            print(request.POST.get(q.question))

            get_text = request.POST.get(q.question)
            print(get_text)
            Employer_candidate_jobanswer.objects.create(candidate_id=c, question_id=q, answer=get_text).save()
        Employer_job_Applied.objects.create(candidate_id=c, job_id=job).save()


@login_required(login_url='/')
def ProfileView(request):
    if request.method == 'GET':
        val = request.GET.get('search_box', None)
        print("val")
        print(val)
        if val:
            job = Employer_job.objects.filter(
                Q(job_title__icontains=val) |
                Q(skill__icontains=val) |
                Q(job_description__icontains=val) |
                Q(job_salary__icontains=val) |
                Q(job_location__icontains=val)
            ).distinct()
            print(job)
            jobs = []
            job_ques = []
            relevant_jobs = []
            common = []
            companyprofile = []
            job_skills = []
            u = request.user
            if u is not None and u.is_candidate:
                c = Candidate.objects.get(user=u)
                try:
                    cp = Candidate_profile.objects.get(user_id=c)
                except Candidate_profile.DoesNotExist:
                    cp = None
                try:
                    cep = Candidate_expdetail.objects.get(user_id=c)
                except Candidate_expdetail.DoesNotExist:
                    cep = None
                try:
                    cr = Candidate_resume.objects.get(user_id=c)
                except Candidate_resume.DoesNotExist:
                    cr = None
                if u.first_login:

                    skills = Candidate_skills.objects.filter(user_id=c)
                    print("skills")
                    print(skills)
                    if len(skills) != 0:

                        my_sk = []
                        j = 0
                        for i in skills:
                            my_sk.insert(j, i.skill.lower())
                            j = j + 1

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
                            if diff > 30:
                                # expired_job.append(j)
                                Employer_expired_job.objects.create(job_id=j).save()

                            else:
                                jobs.append(j)

                        for job in jobs:
                            skills = []
                            sk = str(job.skill).split(",")
                            for i in sk:
                                skills.append(i.strip().lower())
                            common_skills = list(set(my_sk) & set(skills))
                            if len(common_skills) != 0:
                                e = job.employer_id
                                companyprofile.append(Employer_profile.objects.get(employer=e))
                                try:
                                    userS = Employer_job_Saved.objects.get(job_id=job.pk, candidate_id=c)
                                    # print(userS.job_id)
                                except Employer_job_Saved.DoesNotExist:
                                    userS = None
                                try:
                                    userA = Employer_job_Applied.objects.get(job_id=job.pk, candidate_id=c)
                                    # print(userA.job_id)
                                except Employer_job_Applied.DoesNotExist:
                                    userA = None

                                if userA:
                                    # print(userA)
                                    continue
                                if userS:
                                    # print(userS)
                                    continue
                                relevant_jobs.append(job)
                                common.append(len(common_skills))
                                job_skills.append(len(skills))
                                job_ques.append(Employer_jobquestion.objects.filter(job_id=job))

                        objects = zip(relevant_jobs, common, job_skills, job_ques, companyprofile)

                        return render(request, 'jobseeker/home.html',
                                      {'jobs': objects, 'c': c, 'cp': cp, 'cep': cep, 'cr': cr})
                    else:

                        print("len job")
                        print(len(job))
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
                            # print(diff)
                            if diff > 30:
                                # expired_job.append(j)
                                Employer_expired_job.objects.create(job_id=j).save()

                            else:
                                jobs.append(j)
                            print("len")
                            print(len(jobs))
                        for jo in jobs:
                            skills = []
                            sk = str(jo.skill).split(",")
                            for i in sk:
                                skills.append(i.strip().lower())
                            common_skill = []
                            e = jo.employer_id
                            companyprofile.append(Employer_profile.objects.get(employer=e))
                            try:
                                userS = Employer_job_Saved.objects.get(job_id=jo.pk, candidate_id=c)
                                # print(userS.job_id)
                            except Employer_job_Saved.DoesNotExist:
                                userS = None
                            try:
                                userA = Employer_job_Applied.objects.get(job_id=jo.pk, candidate_id=c)
                                # print(userA.job_id)
                            except Employer_job_Applied.DoesNotExist:
                                userA = None

                            if userA:
                                # print(userA)
                                continue
                            if userS:
                                # print(userS)
                                continue
                            relevant_jobs.append(jo)
                            print("job:")
                            print(jo)

                            common.append(len(common_skill))
                            job_skills.append(len(skills))
                            job_ques.append(Employer_jobquestion.objects.filter(job_id=jo))
                        print("job_quest:")
                        print(job_ques)
                        print("relevant_jobs")
                        print(len(relevant_jobs))
                        objects = zip(relevant_jobs, common, job_skills, job_ques, companyprofile)
                        return render(request, 'jobseeker/home.html',
                                      {'jobs': objects, 'c': c, 'cp': cp, 'cep': cep, 'cr': cr})
        else:
            u = request.user
            c = Candidate.objects.get(user=u)
            try:
                profile = Candidate_profile.objects.get(user_id=c)
            except Candidate_profile.DoesNotExist:
                profile = None
            try:
                edu = Candidate_edu.objects.filter(user_id=c)
            except Candidate_edu.DoesNotExist:
                edu = None
            try:
                professional = Candidate_profdetail.objects.filter(user_id=c)
            except Candidate_profdetail.DoesNotExist:
                professional = None
            try:
                resume = Candidate_resume.objects.get(user_id=c)
            except Candidate_resume.DoesNotExist:
                resume = None

            try:
                skills = Candidate_skills.objects.filter(user_id=c)
            except Candidate_skills.DoesNotExist:
                skills = None
            return render(request, 'jobseeker/skills.html', {
                "user": u,
                "profile": profile,
                "edu": edu,
                "professional": professional,
                "resume": resume,
                "skills": skills,
            })


@login_required(login_url='/')
def ProfileEdit(request):
    try:
        profile = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        profile = None
    print(profile)
    print('notrun', request.method)
    if profile is not None:
        if request.method == 'POST':
            print('run', request.method)
            form1 = ProfileRegisterForm(data=request.POST or None, files=request.FILES or None)
            form2 = ProfileRegisterForm_edu(request.POST or None)
            form3 = ProfileRegisterForm_profdetail(request.POST or None)
            form4 = ProfileRegisterForm_resume(request.POST or None)
            form5 = ProfileRegistration_skills(request.POST or None)
            form6 = ProfileRegistration_expdetail(request.POST or None)
            form7 = Resume_headlineForm(request.POST)
            form8 = ProfileRegistration_skills(request.POST)
            print('form2', form2.is_valid())
            if form1.is_valid():
                print(form1.cleaned_data.get('profile_pic'))
                if form1.cleaned_data.get('birth_date'):
                    f1 = form1.save(commit=False)
                    try:
                        c = Candidate_profile.objects.get(user_id=profile)
                    except Candidate_profile.DoesNotExist:
                        c = None
                    if c:
                        c.delete()

                    f1.user_id = profile

                    f1.save()

            if form2.is_valid():
                f2 = form2.save(commit=False)
                if form2.cleaned_data.get('institute_name'):
                    f2.user_id = profile
                    f2.save()
            if form3.is_valid():
                if form2.cleaned_data.get('designation'):
                    f3 = form3.save(commit=False)
                    print(f3)
                    f3.user_id = profile
                    print('f3', f3.user_id)
                    f3.save()
            if form4.is_valid():
                f4 = form4.save(commit=False)
                f4.user_id = profile
                try:
                    f = request.FILES['resume_link']
                except MultiValueDictKeyError:
                    f = False
                if f is not False:
                    f4.resume_link = f
                    f4.save()

                # f5 = form5.save(commit=False)
                # f5.user_id = profile
                # f5.save()

                # for form in form5:
                #     # extract name from each form and save
                #     skill = form.cleaned_data.get('skill')
                #     rating = form.cleaned_data.get('rating')
                #     # save book instance
                #     if skill:
                #         Candidate_skills(user_id=profile, skil=skill, rating=rating).save()
            if form6.is_valid():
                d = form6.cleaned_data.get('department')
                print(d)
                if d != "":

                    f6 = form6.save(commit=False)
                    f6.user_id = profile
                    f6.save()
            if form7.is_valid():
                f7 = form7.save(commit=False)
                f7.user_id = profile
                f7.save()
            if form8.is_valid():
                for form in form8:

                    skill = form.cleaned_data.get('skill')
                    rating = form.cleaned_data.get('rating')

                    if skill:
                        Candidate_skills(user_id=profile, skill=skill, rating=rating).save()
            return redirect('jobseeker:ProfileEdit')
        print(request.method)
        try:
            c = Candidate_profile.objects.get(user_id=profile)
        except Candidate_profile.DoesNotExist:
            c = None
        if c is None:
            cN = 0
        else:
            cN=10
        try:
            cr = Candidate_resume.objects.get(user_id=profile)
        except Candidate_resume.DoesNotExist:
            cr = None
        if cr is not None:
            re = True
            crN=10
        else:
            re = False
            crN =0
        try:
            cep = Candidate_expdetail.objects.get(user_id=profile)
        except Candidate_expdetail.DoesNotExist:
            cep = None
        if cep is None:
            cepN=0
        else:
            cepN=10
        try:
            Resume = Resume_headline.objects.get(user_id=profile)
        except Resume_headline.DoesNotExist:
            Resume = None
        if Resume is None:
            rN=0
        else:
            rN=10
        form1 = ProfileRegisterForm(instance=c)
        form2 = ProfileRegisterForm_edu()
        form3 = ProfileRegisterForm_profdetail()
        form4 = ProfileRegisterForm_resume(instance=cr)

        form6 = ProfileRegistration_expdetail(instance=cep)
        form7 = Resume_headlineForm(instance=Resume)
        form8 = ProfileRegistration_skills()
        skills = Candidate_skills.objects.filter(user_id=profile)
        if len(skills)!=0:
            sN= 10
        else:
            sN=0
        edu = Candidate_edu.objects.filter(user_id=profile)
        if len(edu)!=0:
            eN=10
        else:
            eN=0
        professional = Candidate_profdetail.objects.filter(user_id=profile)
        if len(professional)!=0:
            pN=10
        else:
            pN=0
        per = ((sN+pN+eN+rN+crN+cepN+cN)/70)*100
        print(per)
        return render(request, 'jobseeker/Profile.html',
                      {"form1": form1, 'form2': form2, "form3": form3, 'form4': form4, 'form6': form6, 'form7': form7,
                       'form8': form8,
                       'skills': skills, 'edu': edu, 'professional': professional, 'c': c, 'cr': cr, 're': re,'cep':cep,
                       'rh': Resume,'per':per})

    else:
        return redirect('/')


@login_required(login_url='/')
def create_profile(request):
    profile = Candidate.objects.get(user=request.user)
    if request.method == 'POST':
        form1 = ProfileRegisterForm(request.POST)
        form2 = ProfileRegisterForm_edu(request.POST)
        form3 = ProfileRegisterForm_profdetail(request.POST)
        form4 = ProfileRegisterForm_resume(request.POST)
        form5 = ProfileRegistration_skills(request.POST)
        form6 = ProfileRegistration_expdetail(request.POST)
        if form1.is_valid() and form2.is_valid() and form3.is_valid() and form4.is_valid() and form5.is_valid() and form6.is_valid():
            f1 = form1.save(commit=False)
            f1.user_id = profile
            f1.save()

            f2 = form2.save(commit=False)
            if f2.cleaned_data.get('institute_name'):
                f2.user_id = profile
                f2.save()

            f3 = form3.save(commit=False)
            if f2.cleaned_data.get('designation'):
                f3.user_id = profile
                f3.save()

            f4 = form4.save(commit=False)
            f4.user_id = profile
            f4.save()

            # f5 = form5.save(commit=False)
            # f5.user_id = profile
            # f5.save()
            for form in form5:
                # extract name from each form and save
                skill = form.cleaned_data.get('skill')
                rating = form.cleaned_data.get('rating')
                # save book instance
                if skill:
                    Candidate_skills(user_id=profile, skil=skill, rating=rating).save()

            f6 = form6.save(commit=False)
            f6.user_id = profile
            f6.save()
            return redirect('jobseeker:jobseeker_home')

    form1 = ProfileRegisterForm()
    form2 = ProfileRegisterForm_edu()
    form3 = ProfileRegisterForm_profdetail()
    form4 = ProfileRegisterForm_resume()
    form5 = ProfileRegistration_skills()
    form6 = ProfileRegistration_expdetail()

    return render(request, 'jobseeker/createprofile.html',
                  {"form1": form1, 'form2': form2, "form3": form3, 'form4': form4, "form5": form5, 'form6': form6})

