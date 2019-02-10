# #  vms
import logging
#from datetime import datetime
import operator
#import os

import subprocess
from django.http import JsonResponse
import re

#from django.contrib.auth.models import User
#from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
#from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, StreamingHttpResponse, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
#from django.views.decorators.cache import cache_page
from django.utils import timezone
#from time import strftime

from dojo.filters import VMFilter
from dojo.forms import VMForm, DeleteVMForm, AddVMEngagementForm, DeleteVMEngagementForm
#    CheckForm, \
#    UploadThreatForm, UploadRiskForm, NoteForm, DoneForm, \
#    EngForm, TestForm, ReplaceRiskAcceptanceForm, AddFindingsRiskAcceptanceForm, DeleteEngagementForm, ImportScanForm, \
#    JIRAFindingForm, CredMappingForm
from dojo.models import VM, VMOnEngagement
#Finding, Product, Engagement, Test, \
#from dojo.models import Finding, Product, Engagement, Test, \
#    Check_List, Test_Type, Notes, \
#    Risk_Acceptance, Development_Environment, BurpRawRequestResponse, Endpoint, \
#    JIRA_PKey, JIRA_Issue, Cred_Mapping, Dojo_User, System_Settings
#from dojo.tools.factory import import_parser_factory
from dojo.utils import get_page_items, add_breadcrumb
#from dojo.utils import get_page_items, add_breadcrumb, handle_uploaded_threat, \
#    FileIterWrapper, get_cal_event, message, get_system_setting, create_notification, Product_Tab
#from dojo.tasks import update_epic_task, add_epic_task, close_epic_task

logger = logging.getLogger(__name__)

@user_passes_test(lambda u: u.is_staff)
def vm(request):
    filtered = VMFilter(
        request.GET,
        queryset=VM.objects.all().distinct())

    vms = get_page_items(request, filtered.qs, 25)
#    name_words = [
#        product.name for product in Product.objects.filter(
#            ~Q(engagement=None),
#            engagement__active=True,
#        ).distinct()
#    ]
#    eng_words = [
#        engagement.name for product in Product.objects.filter(
#            ~Q(engagement=None),
#            engagement__active=True,
#        ).distinct() for engagement in product.engagement_set.all()
#    ]

    add_breadcrumb(
        title="Virtual Machines",
        top_level=not len(request.GET),
        request=request)

    return render(
        request, 'dojo/vm.html', {
            'vms': vms,
            'filtered': filtered,
#            'name_words': sorted(set(name_words)),
#            'eng_words': sorted(set(eng_words)),
        })


@user_passes_test(lambda u: u.is_staff)
def new_vm(request):
    if request.method == 'POST':
        form = VMForm(request.POST)
        if form.is_valid():
            new_vm = form.save()
            new_vm.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                'VM added successfully.',
                extra_tags='alert-success')
            return HttpResponseRedirect(
                reverse('view_vm', args=(new_vm.id, )))
    else:
        form = VMForm()

    add_breadcrumb(title="New Virtual machine", top_level=False, request=request)
    return render(request, 'dojo/new_vm.html', {
        'form': form,
    })

def view_vm(request, id):
    vm = get_object_or_404(VM, id=id)
    add_breadcrumb(parent=vm, top_level=False, request=request)
    return render(
        request, 'dojo/view_vm.html', {
            'vm': vm,
        })

@user_passes_test(lambda u: u.is_staff)
def edit_vm(request, id):
    vm = VM.objects.get(pk=id)
    if request.method == 'POST':
        form = VMForm(request.POST, instance=vm)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                'VM updated successfully.',
                extra_tags='alert-success')
            return HttpResponseRedirect(reverse('view_vm', args=(vm.id,)))
    else:
        form = VMForm(instance=vm)
    title = ""
    return render(request, 'dojo/new_vm.html', {
        'form': form,
        'edit': True,
        'vm': vm
    })

@user_passes_test(lambda u: u.is_staff)
def delete_vm(request, id):
    vm = get_object_or_404(VM, pk=id)
    form = DeleteVMForm(instance=vm)

    from django.contrib.admin.utils import NestedObjects
    from django.db import DEFAULT_DB_ALIAS

    collector = NestedObjects(using=DEFAULT_DB_ALIAS)
    collector.collect([vm])
    rels = collector.nested()

    if request.method == 'POST':
        if 'id' in request.POST and str(vm.id) == request.POST['id']:
            form = DeleteVMForm(request.POST, instance=vm)
            if form.is_valid():
                vm.delete()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Virtual Machine removed.',
                    extra_tags='alert-success')
                return HttpResponseRedirect(reverse("vm"))

    return render(request, 'dojo/delete_vm.html', {
        'vm': vm,
        'form': form,
        'rels': rels,
    })

@user_passes_test(lambda u: u.is_staff)
def add_vm_engagement(request, id):
    if request.method == 'POST':
        form = AddVMEngagementForm(request.POST)
        if form.is_valid():
            new_eng = form.save()
            new_eng.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                'Engagement added successfully.',
                extra_tags='alert-success')
            return HttpResponseRedirect(
                reverse('view_vm', args=(new_eng.vm.id, )))
    else:
        form = AddVMEngagementForm(initial={'vm': id})

    add_breadcrumb(title="New Engagement for VM", top_level=False, request=request)
    return render(request, 'dojo/new_vm_eng.html', {
        'form': form,
    })

@user_passes_test(lambda u: u.is_staff)
def delete_vm_engagement(request, id):
    vmoneng = get_object_or_404(VMOnEngagement, pk=id)
    form = DeleteVMEngagementForm(instance=vmoneng)

    from django.contrib.admin.utils import NestedObjects
    from django.db import DEFAULT_DB_ALIAS

    collector = NestedObjects(using=DEFAULT_DB_ALIAS)
    collector.collect([vmoneng])
    rels = collector.nested()

    if request.method == 'POST':
        if 'id' in request.POST and str(vmoneng.id) == request.POST['id']:
            form = DeleteVMEngagementForm(request.POST, instance=vmoneng)
            if form.is_valid():
                vmid = vmoneng.vm.id #for the reverse http response
                vmoneng.delete()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Virtual Machine removed from engagement.',
                    extra_tags='alert-success')
                return HttpResponseRedirect(reverse("view_vm", args=(vmid,)))

    return render(request, 'dojo/delete_vm_eng.html', {
        'vmoneng': vmoneng,
        'form': form,
        'rels': rels,
    })

def ping_vm(request, id):
    vm = get_object_or_404(VM, pk=id)
    if vm.IP.startswith('10.') and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",vm.IP):
        try:
            response = subprocess.check_output(["ping", "-c", "1", vm.IP], shell=False)
        except subprocess.CalledProcessError:
            response = False
        return JsonResponse({
                   'status':'up' if response else 'down',
                   'time':timezone.now().strftime("%m/%d/%Y, %H:%M:%S")
               })
