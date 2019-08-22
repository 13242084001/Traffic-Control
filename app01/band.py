#!/usr/bin/env python3.6
#
import subprocess
import time
from collections import deque
from functools import reduce
from app01 import gol
from app01.utils import GetIfaces


last = [0,0]
#gol._init()

def get_mcu_ip():
    cmd = "netstat -antp|awk '{print $4,$5}'|grep 1089|head -1"
    out = subprocess.getstatusoutput(cmd)
    if not out[0] and out[1]:
    #return ["192.168.0.102", "192.168.0.10"]
        #print('*************%s' % out[1].split())
        return [x.split(':')[0] for x in out[1].split()]

def check_iptables(mcu_ip):
    cmd1 = "iptables -L INPUT --line-number|grep %s|awk '{print $1}'" % mcu_ip
    cmd2 = "iptables -L OUTPUT --line-number|grep %s|awk '{print $1}'" % mcu_ip
    iptables_dict = {}
    for cmd in (cmd1, cmd2):
        out = subprocess.getstatusoutput(cmd)
        if not out[0] and out[1]:
            if 'input_list' in iptables_dict:
                iptables_dict["output_list"] = out[1].split("\n")
            else:
                iptables_dict["input_list"] = out[1].split("\n")
    print('this is %s' % iptables_dict)
    for k, v in iptables_dict.items():
        v.reverse()
        if "input_list" == k:
            print('zheshi %s' % v)
            for num in v:
                subprocess.getstatusoutput("iptables -D INPUT %s" % num)
        elif "output_list" == k:
            for num in v:
                subprocess.getstatusoutput("iptables -D OUTPUT %s" % num)

def exec_iptables_cmd(mcu_ip):
    check_iptables(mcu_ip)
    cmd1 = "iptables -I INPUT -s %s" % mcu_ip
    cmd2 = "iptables -I OUTPUT -d %s" % mcu_ip
    for cmd in (cmd1, cmd2):
        out = subprocess.getstatusoutput(cmd)
        if not out[0]:
            pass
        else:
            return print(out[1])

def bandwidth():
    """
    获取到特定ip的流量，bytes，返回一个数组，进入的bytes数，发出的bytes数；[234.11,2233.33]
    """
    cmd = "iptables -nvxL|grep %s|awk '{print $2}'" % gol.get_value("mcu_ip")
    out = subprocess.getstatusoutput(cmd)
    if not out[0]:
        st = map(lambda x: int(x) * 8 / 1000, out[1].split())
        #print(st)
        return list(st)

def calc(after, last):
    time.sleep(1)
    new_last = after()
    result = list(map(lambda x, y: x-y, new_last, last))
    #print(result)
    return result, new_last

def data_queue(calc, a, b):
    dq = deque(maxlen=10)
    while True:
        #print('this is %s' % b)
        result, b = calc(a, b)
        dq.append(result)
        yield dq

def add(x, y):
    return list(map(lambda a, b: a+b, x,y))

def get_network_status():
    #print(gol._global_dict)
    out = subprocess.getstatusoutput("ping %s -f -c 10" % gol.get_value("mcu_ip"))
    #print(out)
    if not out[0]:
        re = out[1].split(',')[2:]
        gol.set_value("packet loss", re[0].split()[0])
        gol.set_value(re[1].split(' = ')[0].split('\n')[1], re[1].split(' = ')[1])
        #print(gol._global_dict)


def main():
    nic_ip, mcu_ip = get_mcu_ip()
    iface_obj = GetIfaces()
    nic = iface_obj.get_nic(nic_ip)
    gol.set_value('mcu_ip', mcu_ip)
    gol.set_value('nic_ip', nic_ip)
    gol.set_value('nic', nic)
    exec_iptables_cmd(mcu_ip)
    time.sleep(1)
    for dq in data_queue(calc, bandwidth, last):
        tmp_list = list(dq)
        #print(tmp_list)
        avg10 = list(map(lambda x: round(x / 10, 2), reduce(add, tmp_list)))
        avg2 = list(map(lambda x: round(x / 2, 2), reduce(add, tmp_list[-2:])))
        avg5 = list(map(lambda x: round(x / 5, 2), reduce(add, tmp_list[-5:])))
        get_network_status()
        gol.set_value('avg10', avg10)
        gol.set_value('avg2', avg2)
        gol.set_value('avg5', avg5)
        #print(gol._global_dict)

if __name__ == "__main__":
    main()       

