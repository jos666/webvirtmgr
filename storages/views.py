from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from servers.models import Compute
from storages.forms import AddStgPool, AddImage, CloneImage

from vrtManager.storage import wvmStorage

from libvirt import libvirtError


def storages(request, host_id):
        return render_to_response('storage.html', locals(),  context_instance=RequestContext(request))



def storage(request, host_id, pool):
    """

    Storage pool block

    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    def handle_uploaded_file(path, f_name):
        target = path + '/' + str(f_name)
        destination = open(target, 'wb+')
        for chunk in f_name.chunks():
            destination.write(chunk)
        destination.close()

    errors = []
    compute = Compute.objects.get(id=host_id)

    try:
        conn = wvmStorage(compute.hostname, compute.login, compute.password, compute.type, pool)
        storages = conn.get_storages()

        if pool is None:
            return HttpResponseRedirect('/storages/%s' % host_id)
        else:
            size, free, usage = conn.get_size()
            percent = (free * 100) / size
            state = conn.is_active()
            path = conn.get_target_path()
            type = conn.get_type()
            autostart = conn.get_autostart()
            if state:
                conn.refresh()
                volumes = conn.update_volumes()
            else:
                volumes = None

            print conn.get_uuid()

        if request.method == 'POST':
            if 'start' in request.POST:
                try:
                    conn.start()
                    return HttpResponseRedirect(request.get_full_path())
                except libvirtError as error_msg:
                    errors.append(error_msg.message)
            if 'stop' in request.POST:
                try:
                    conn.stop()
                    return HttpResponseRedirect(request.get_full_path())
                except libvirtError as error_msg:
                    errors.append(error_msg.message)
            if 'delete' in request.POST:
                try:
                    conn.delete()
                    return HttpResponseRedirect('/storages/%s/' % host_id)
                except libvirtError as error_msg:
                    errors.append(error_msg.message)
            if 'set_autostart' in request.POST:
                try:
                    conn.set_autostart(1)
                    return HttpResponseRedirect(request.get_full_path())
                except libvirtError as error_msg:
                    errors.append(error_msg.message)
            if 'unset_autostart' in request.POST:
                try:
                    conn.set_autostart(0)
                    return HttpResponseRedirect(request.get_full_path())
                except libvirtError as error_msg:
                    errors.append(error_msg.message)
            if 'img_add' in request.POST:
                form = AddImage(request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    img_name = data['name'] + '.img'
                    if img_name in stg.listVolumes():
                        msg = _("Volume name already use")
                        errors.append(msg)
                    if not errors:
                        conn.new_volume(pool, data['name'], data['size'], data['format'])
                        return HttpResponseRedirect(request.get_full_path())
            if 'img_del' in request.POST:
                img = request.POST.get('img', '')
                try:
                    vol = stg.storageVolLookupByName(img)
                    vol.delete(0)
                    return HttpResponseRedirect(request.get_full_path())
                except libvirtError as error_msg:
                    errors.append(error_msg.message)
            if 'iso_upload' in request.POST:
                if str(request.FILES['file']) in stg.listVolumes():
                    msg = _("ISO image already exist")
                    errors.append(msg)
                else:
                    handle_uploaded_file(path, request.FILES['file'])
                    return HttpResponseRedirect(request.get_full_path())
            if 'img_clone' in request.POST:
                form = CloneImage(request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    img_name = data['name'] + '.img'
                    if img_name in stg.listVolumes():
                        msg = _("Name of volume name already use")
                        errors.append(msg)
                    if not errors:
                        if 'convert' in data:
                            format = data['format']
                        else:
                            format = None
                        try:
                            conn.clone_volume(pool, data['image'], data['name'], format)
                            return HttpResponseRedirect(request.get_full_path())
                        except libvirtError as error_msg:
                            errors.append(error_msg.message)
        conn.close()
    except libvirtError as err:
        errors.append(e.message)

    return render_to_response('storage.html', locals(),  context_instance=RequestContext(request))