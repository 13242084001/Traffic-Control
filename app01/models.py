# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

"""
class Profile(models.Model):
    name = models.CharField(max_length=16, null=True, verbose_name="规则名称")
    content = models.TextField(max_length=2048, null=True, verbose_name="规则json字符串")
"""


class Profile(models.Model):
    name = models.CharField(max_length=16, null=True, verbose_name="规则名称")
    content = models.TextField(max_length=2048, null=True, verbose_name="规则json字符串")



class Info(models.Model):
    controlling_ip = models.GenericIPAddressField(max_length=32, null=True, verbose_name="控制设备ip")
    controlled_ip = models.GenericIPAddressField(max_length=32, null=True, verbose_name="被控制设备ip")
    #remote_ip = models.GenericIPAddressField(max_length=32, null=32, verbose_name="目的ip")
    #protocol = models.CharField(max_length=5, null=True, verbose_name="协议")
    #local_port = models.IntegerField(max_length=5, null=True, verbose_name="本地端口")
    #remote_port = models.IntegerField(max_length=5, null=True, verbose_name="对端端口")

    mark = models.IntegerField(null=True, verbose_name="mark标记值")
    parent_id = models.IntegerField(null=True, verbose_name="tc parentid")
    iptables = models.TextField(max_length=2048, null=True, verbose_name="iptables字符串")
    tc = models.TextField(max_length=2048, null=True, verbose_name="tc命令字符串")
    profile_pk = models.ForeignKey("Profile", null=True, on_delete=models.CASCADE, verbose_name="profile规则编号")
    status = models.BooleanField(null=False, default=False, verbose_name="默认为未shaping")


