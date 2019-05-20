import subprocess
from app01 import models
import netifaces
from IPy import IP


class GetIfaces(object):

    def __init__(self):
        self.nic_list = netifaces.interfaces()
        self.nic_list.remove('lo')
        self.interfaces_dict = {}
        self.nic_interface_info()

    def nic_interface_info(self):
        for nic in self.nic_list:
            net_info_list = netifaces.ifaddresses(nic)[netifaces.AF_INET]
            addr = net_info_list[0]["addr"]
            netmask = net_info_list[0]["netmask"]
            hosts = self.get_net_hosts(addr, netmask)
            self.interfaces_dict[nic] = {"addr": addr, "netmask": netmask, "hosts": hosts}

    def get_gateway(self):
        ipv4_gateway_list = netifaces.gateways()[netifaces.AF_INET]
        for tup in ipv4_gateway_list:
            pass
            #if self.nic in tup:
            #    return tup[0]

    def get_net_hosts(self, addr, netmask):
        return IP(addr).make_net(netmask)


class CmdHandle(object):

    def __init__(self, controlling_ip, **kwargs):
        self.controlling_ip = controlling_ip
        for i in kwargs:
            for k in i:
                self.__dict__[k] = i.get(k)
        self.make_iptables_list()
        self.make_tc_list()

    def make_iptables_list(self):
        
        protocol = "all" if not self.protocol else self.protocol

        local_ip = self.controlling_ip if not self.local_ip else self.local_ip

        src_string = " -s %s" % local_ip
        
        if not self.local_port:
            sport_string = ""
        elif len(str(self.local_port).split(",")) > 1:
            sport_string = " –m multiport --sports %s" % self.local_port
        else:
            sport_string = " --dport %s" % local_port
        
        dst_string = "" if not remote_ip else " -d %s" % self.remote_ip
        
        if not self.remote_port:
            dport_string = ""

        elif len(str(self.remote_port).split(",")) > 1:
            dport_string = " –m multiport --dports %s" % self.remote_port
        else:
            dport_string = " --dport %s" % self.remote_port
        iptables_cmd_list = []
        try:
            last_mark = models.Info.objects.all().last().mark
            mark = last_mark + 1
        except Exception:
            mark = 2
        #   mark = last_mark + 1 if last_mark else 2
        print(mark)
        mark_string = " -j MARK --set-mark %d" % mark
        if dst_string or dport_string:
            if protocol == "all":
                if not dport_string:
                    cmd = "iptables -t mangle -A PREROUTING" + dst_string + " -p %s" % protocol + dport_string + mark_string
                    iptables_cmd_list.append(cmd)
                else:
                    cmd = "iptables -t mangle -A PREROUTING" + dst_string + " -p tcp" + dport_string + mark_string
                    iptables_cmd_list.append(cmd)
                    cmd = "iptables -t mangle -A PREROUTING" + dst_string + " -p udp" + dport_string + mark_string
                    iptables_cmd_list.append(cmd)
            else:
                cmd = "iptables -t mangle -A PREROUTING" + dst_string + " -p %s" % protocol + dport_string + mark_string
                iptables_cmd_list.append(cmd)

        if protocol == "all":
            if not sport_string:
                cmd = "iptables -t mangle -A PREROUTING" + src_string + " -p %s" % protocol + dport_string + mark_string
                iptables_cmd_list.append(cmd)
            else:
                cmd = "iptables -t mangle -A PREROUTING" + src_string + " -p tcp" + sport_string + mark_string
                iptables_cmd_list.append(cmd)
                cmd = "iptables -t mangle -A PREROUTING" + src_string + " -p udp" + sport_string + mark_string
                iptables_cmd_list.append(cmd)
        else:
            cmd = "iptables -t mangle -A PREROUTING" + src_string + " -p %s" % protocol + sport_string + mark_string
            iptables_cmd_list.append(cmd)

        for cmd in iptables_cmd_list:
            print(cmd)

        self.iptables_cmd_list = iptables_cmd_list
        self.local_ip = local_ip

    def confirm_dev(self):
        inet_obj = GetIfaces()
        net_dict = inet_obj.interfaces_dict
        print(net_dict)
        for k, v in net_dict.items():
            print(type(v.get("hosts")))
            if self.controlling_ip in v.get("hosts"):
                net_dict.pop(k)
                return net_dict.keys()

    def make_tc_list(self):
        dev = self.confirm_dev()

        if self.rate:
            rate_string = " rate %skbps" % self.rate
        else:
            rate_string = " rate 10mbit"

        if self.loss.get("percentage"):
            if self.loss.get("correlation"):
                loss_string = " loss %s%% %s%%" % (self.loss.get("percentage"), self.loss.get("correlation"))
            else:
                loss_string = " loss %s%%" % self.loss.get("percentage")
        else:
            loss_string = ""

        if self.delay.get("delay"):
            delay_string = " delay %s%%" % self.delay.get("delay")
        else:
            delay_string = ""

        if self.corruption.get("percentage"):
            corruption_string = " corruption %s%%" % self.corruption.get("percentage")
        else:
            corruption_string = ""

        if self.reorder.get("percentage"):

            if self.reorder.get("correlation"):
                reorder_string = " reorder %s%% %s%%" % (self.reorder.get("percentage"), self.reorder.get("correlation"))
            else:
                reorder_string = " reorder %s%%" % self.reorder.get("percentage")
        else:
            reorder_string = ""

        try:
            parent_id = models.Info.objects.all().last().parent_id
            parent_id += 1
        except Exception:
            parent_id = 22
        class_id = int(str(parent_id)[-1] + str(parent_id))
        tc_cmd_list = []
        for nic in dev:
            cmd1 = "tc class add dev %s parent 1: classid 1:%s htb rate 10mbps" % (nic, parent_id)
            cmd2 = "tc class add dev %s parent 1:%s class 1:%s htb" % (nic, parent_id, class_id) + rate_string
            cmd3 = "tc qdisc add dev %s parent 1:%s netem" % (nic, parent_id) + loss_string + delay_string + \
                   corruption_string + reorder_string
            tc_cmd_list.extend([cmd1, cmd2, cmd3])
        self.tc_cmd_list = tc_cmd_list
        self.parent_id = parent_id

    def exec_cmd():
        for cmd_list in (self.iptables_cmd_list, self.tc_cmd_list):
            for cmd in cmd_list
                pass
            # ouput = subprocess.getstatusoutput(rule)
            # if ouput[0]:
            #    return ouput[1]
    
    def __call__(self):
        self.exec_cmd()
