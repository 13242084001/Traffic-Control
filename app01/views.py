# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework.response import Response
from rest_framework.views import APIView
from app01 import models
import json
import netifaces
import subprocess
from app01.utils import CmdHandle


def init():
    nic_list = netifaces.interfaces()
    nic_list.remove("lo")
    for nic in nic_list:
        print(nic)
        subprocess.getstatusoutput("tc qdisc delete dev %s root" % (nic,))
        out = subprocess.getstatusoutput("tc qdisc add dev %s root handle 1: htb default 11" % (nic,))
        if out[0]:
            print(out[1])

init()


class ControlingInfo(APIView):
    def get(self, request):
        controlling_ip = request.META.get("REMOTE_ADDR")
        print(controlling_ip)
        controlled_ip_list = models.Info.objects.filter(controlling_ip=controlling_ip).all().values("controlled_ip", "status")
        return Response({"client_ip": controlling_ip, "controlled_ip_list": controlled_ip_list})


class AddControlledIp(APIView):
    def get(self, request):
        obj = models.Profile.objects.all().values()
        print(obj)

        return Response(None)

    def post(self, request):
        print(str(request.body))    # bytes字符串
        print(request.data)     # 字典
        models.Profile.objects.update_or_create(**request.data)
        return Response(None)


class CheckDevStatus(APIView):
    def post(self, request):
        dev_ip = request.data.get('controlled_ip')
        print(dev_ip)
        status = subprocess.getstatusoutput("ping -i 0.01 %s -c 2" % dev_ip)
        if not status[0]:
            return Response({"status": "online"})
        return Response({"status": "offline"})


class Profile(APIView):
    def get(self, request):
        obj = list(models.Profile.objects.all().values())
        return Response({"ret": 10000, "data": obj, "error": None})

    def post(self, request):
        print(request.data)
        models.Profile.objects.create(**request.data)
        return Response({"ret": 10000, "data": request.data, "error": None})


class Shaping(APIView):
    def get(self, request, **kwargs):
        controlling_ip = request.META.get("REMOTE_ADDR")
        ip = kwargs.get("slug")
        print(ip)
        obj = models.Info.objects.filter(controlling_ip=controlling_ip, controlled_ip=ip, status=1).first()
        print(obj.profile_pk.content)
        print("#################")
        print(type(obj.profile_pk.content))
        return Response(eval(obj.profile_pk.content))

    def post(self, request, **kwargs):
        print(request.data)
        controlling_ip = request.META.get("REMOTE_ADDR")
        handle = CmdHandle(controlling_ip, **request.data)
        iptables_cmd_list = handle.iptables_cmd_list
        local_ip = handle.local_ip
        tc_cmd_list = handle.tc_cmd_list
        parent_id = handle.parent_id
        mark = handle.mark

        try:
            # 如果该被控制ip有一个规则，则判断该规则是不是有名字的，如果是，则新增规则，并修改外键pk；如果没有名字，则修改该规则
            profile_obj = models.Info.objects.filter(controlled_ip=local_ip).first().profile_pk
            print(profile_obj)
            print("************")
            print(111111111111)
            if not profile_obj.name:
                print(profile_obj.name)
                #   没有名字
                models.Profile.objects.filter(id=profile_obj.id).update(content=request.data)
                print(2222222222)
                #models.Info.objects.filter(controlled_ip=local_ip).update(profile_pk=new_profile_obj)
            else:
                #   有名字
                new_profile_obj = models.Profile.objects.create(content=request.data)
                models.Info.objects.filter(controlled_ip=local_ip).update(profile_pk=new_profile_obj)

        except Exception:
            # 如果报错了，说明还没有这条shaping记录
            profile_obj = models.Profile.objects.create(content=request.data)
            print(33333333333)
            models.Info.objects.create(controlling_ip=controlling_ip, controlled_ip=local_ip,
                                       iptables=iptables_cmd_list, parent_id=parent_id, tc=tc_cmd_list,
                                       profile_pk=profile_obj, status=1, mark=mark)
            print(4444444444)

        # 执行相关命令
        handle()
        return Response(request.data)

        #   删除某个正在shaping的ip相关规则，也就是停止
    def delete(self, request, **kwargs):
        ip = kwargs.get("slug")
        print(ip)
        obj = models.Info.objects.filter(controlled_ip=ip).first()
        if obj:
            profile_obj = obj.profile_pk  # 返回profile对象
            print(profile_obj, type(profile_obj))
            # print(obj.iptables, type(obj.iptables))
            # 将iptables命令替换成删除命令
            iptables_list = list(map(lambda x: x.replace("-A", "-D"), eval(obj.iptables)))  # eval方法将列表字符串转换成列表
            print(iptables_list)
            # tc 删除命令
            parent_id = obj.parent_id
            dev_list = netifaces.interfaces()
            dev_list.remove("lo")
            print(dev_list)
            #tc_list = list(map(lambda x: "tc qdisc delete dev %s parent 1:%s" % (x, parent_id), dev_list))
            #print(tc_list)
            # tc删除不了，要想办法呀
            for i in iptables_list:
                subprocess.getstatusoutput(i)

            obj.update(status=0)
            if not profile_obj.name:
                profile_obj.delete()

        return Response(None)

    def put(self, request, **kwargs):
        self.delete(request, **kwargs)
        self.post(request, **kwargs)
        return Response(None)

"""
class Action(APIView):
    def get(self, request, **kwargs):
        controlling_ip = request.META.get("REMOTE_ADDR")
        ip = kwargs.get("slug")
        print(ip)
        obj = models.Info.objects.filter(controlling_ip=controlling_ip, controlled_ip=ip).first()
        print(obj.profile_pk.content)
        print("#################")
        print(type(obj.profile_pk.content))
        return Response(eval(obj.profile_pk.content))

    def post(self, request):
        return Response(None)

    #   删除某个正在shaping的ip相关规则，也就是停止
    def delete(self, request, **kwargs):
        ip = kwargs.get("slug")
        print(ip)
        obj = models.Info.objects.filter(controlled_ip=ip).first()
        if obj:
            profile_obj = obj.profile_pk  # 返回profile对象
            print(profile_obj, type(profile_obj))
            # print(obj.iptables, type(obj.iptables))
            # 将iptables命令替换成删除命令
            iptables_list = list(map(lambda x: x.replace("-A", "-D"), eval(obj.iptables)))  # eval方法将列表字符串转换成列表
            print(iptables_list)
            #tc 删除命令
            parent_id = obj.parent_id
            dev_list = netifaces.interfaces()
            dev_list.remove("lo")
            print(dev_list)
            tc_list = list(map(lambda x: "tc qdisc delete dev %s parent 1:%s" % (x, parent_id), dev_list))
            print(tc_list)
            for i in (iptables_list, tc_list):
                for k in i:
                    subprocess.getstatusoutput(k)

            obj.delete()
            if not profile_obj.name:
                profile_obj.delete()

        return Response(None)
"""
