# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework.response import Response
from rest_framework.views import APIView
from app01 import models
import json
import netifaces
import subprocess
from app01.utils import IptablesHandle, TcHandle


def init():
    nic_list = netifaces.interfaces().remove('lo')
    for nic in nic_list:
        out = subprocess.getstatusoutput("tc qdisc add dev %s root htb" % (nic,))
        if out[0]:
            print("初始化失败!")

init()

class ControlingInfo(APIView):
    def get(self, request):
        controling_ip = request.META.get("REMOTE_ADDR")
        print(controling_ip)
        return Response({"client_ip": controling_ip})


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
    def post(self, request):
        print(request.data)
        controlling_ip = request.META.get("REMOTE_ADDR")

        # 生成iptables命令
        iptables_cmd_list, local_ip = IptablesHandle.make_iptables_list(controlling_ip, **request.data)

        request.data.pop("rule")
        print("#" * 20)
        print(request.data)
        # 生成tc命令
        tc_cmd_list, parent_id = TcHandle.make_tc_list(controlling_ip, **request.data)

        try:
            # 如果该被控制ip有一个规则，则判断该规则是不是有名字的，如果是，则新增规则，并修改外键pk；如果没有名字，则修改该规则
            profile_obj = models.Info.objects.filter(controlled_ip=local_ip).first().profile_pk
            if not profile_obj.name:
                #   没有名字
                models.Profile.objects.filter(id=profile_obj.id).update(content=request.data)
                #models.Info.objects.filter(controlled_ip=local_ip).update(profile_pk=new_profile_obj)
            else:
                #   有名字
                new_profile_obj = models.Profile.objects.create(content=request.data)
                models.Info.objects.filter(controlled_ip=local_ip).update(profile_pk=new_profile_obj)
        except Exception:
            # 如果报错了，说明还没有这条shaping记录
            profile_obj = models.Profile.objects.create(content=request.data)
            models.Info.objects.create(controlling_ip=controlling_ip, controlled_ip=local_ip,
                                       iptables=iptables_cmd_list, parent_id=parent_id, tc=tc_cmd_list,
                                       profile_pk=profile_obj)


        # 执行相关命令
        IptablesHandle.exec_iptables(*iptables_cmd_list)
        TcHandle.exec_tc(*tc_cmd_list)

        return Response(request.data)


class Action(APIView):
    def get(self, request, **kwargs):
        obj = models.Info.objects.all().values()
        print(json.dumps(list(obj)))
        obj1 = models.Profile.objects.all().values()
        print(json.dumps(list(obj1)))
        return Response(None)

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
            tc_list = list(map(lambda x: "tc qdisc delete dev %s parent 1:%s" % (x, parent_id), netifaces.interfaces().remove('lo')))
            if IptablesHandle.exec_iptables(*iptables_list):
                #   如果命令没有执行成功
                pass
            # 执行tc命令
            TcHandle.exec_tc(*tc_list)
            obj.delete()
            if not profile_obj.name:
                profile_obj.delete()

        return Response(None)

