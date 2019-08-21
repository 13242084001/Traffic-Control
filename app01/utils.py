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
            print("this is net_info_list %s" % net_info_list)
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

    def get_nic(self, nic_ip):
        for nic in self.nic_list:
            addr = netifaces.ifaddresses(nic)[netifaces.AF_INET][0].get("addr")
            print('######%s' % addr)
            if nic_ip == addr:
                return nic

class CmdHandle(object):

    def __init__(self, controlling_ip, **kwargs):
        self.controlling_ip = controlling_ip
        self.rule = kwargs.get('rule')
        self.upstream = kwargs.get('upstream')
        self.downstream = kwargs.get('downstream')
        self.iptables_cmd_list, self.local_ip, self.mark = self.make_iptables_list()
        self.tc_cmd_list, self.parent_id = self.make_tc_list()

    def make_iptables_list(self):

        protocol = "All" if not self.rule.get("protocol") else self.rule.get("protocol")

        local_ip = self.controlling_ip if not self.rule.get("local_ip") else self.rule.get("local_ip")

        src_string = " -s %s" % local_ip

        if not self.rule.get("local_port"):
            sport_string = ""
        elif len(str(self.rule.get("local_port")).split(",")) > 1:
            sport_string = " –m multiport --sports %s" % self.rule.get("local_port")
        else:
            sport_string = " --dport %s" % self.rule.get("local_port")

        dst_string = "" if not self.rule.get("remote_ip") else " -d %s" % self.rule.get("remote_ip")

        if not self.rule.get("remote_ip"):
            dport_string = ""

        elif len(str(self.rule.get("remote_ip")).split(",")) > 1:
            dport_string = " –m multiport --dports %s" % self.rule.get("remote_ip")
        else:
            dport_string = " --dport %s" % self.rule.get("remote_ip")
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
            if protocol == "All":
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

        if protocol == "All":
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
        return iptables_cmd_list, local_ip, mark

    def confirm_dev(self, updown):
        inet_obj = GetIfaces()
        net_dict = inet_obj.interfaces_dict
        print("this is net_dict %s" % net_dict)
        for k, v in net_dict.items():
            # print(type(v.get("hosts")))
            if self.controlling_ip in v.get("hosts"):
                if updown == "upstream":
                    net_dict.pop(k)
                    print(net_dict.keys())
                    return net_dict.keys()
                elif updown == "downstream":
                    print('this is k %s' % k)
                    return k,

    def make_tc_list(self):
        tc_cmd_list = []
        for i in ["upstream", "downstream"]:
            dev = self.confirm_dev(i)
            updown = getattr(self, i)
            if updown.get("rate"):
                rate_string = " rate %skbps" % updown.get("rate")
            else:
                rate_string = " rate 10mbit"

            if updown.get("loss").get("percentage"):
                if updown.get("loss").get("correlation"):
                    loss_string = " loss %s%% %s%%" % (updown.get("loss").get("percentage"), updown.get("loss").get("correlation"))
                else:
                    loss_string = " loss %s%%" % updown.get("loss").get("percentage")
            else:
                loss_string = ""

            if updown.get("delay").get("delay"):
                delay_string = " delay %sms" % updown.get("delay").get("delay")
            else:
                delay_string = ""

            if updown.get("corruption").get("percentage"):
                corruption_string = " corruption %s%%" % updown.get("corruption").get("percentage")
            else:
                corruption_string = ""

            if updown.get("reorder").get("percentage"):

                if updown.get("reorder").get("correlation"):
                    reorder_string = " reorder %s%% %s%%" % (updown.get("reorder").get("percentage"), updown.get("reorder").get("correlation"))
                else:
                    reorder_string = " reorder %s%%" % updown.get("reorder").get("percentage")
            else:
                reorder_string = ""

            try:
                parent_id = models.Info.objects.all().last().parent_id
                parent_id += 1
            except Exception:
                parent_id = 22
            class_id = int(str(parent_id)[-1] + str(parent_id))

            for nic in dev:
                cmd1 = "tc class add dev %s parent 1: classid 1:%s htb rate 10mbps" % (nic, parent_id)
                cmd2 = "tc class add dev %s parent 1:%s classid 1:%s htb" % (nic, parent_id, class_id) + rate_string
                cmd3 = "tc qdisc add dev %s parent 1:%s netem" % (nic, class_id) + loss_string + delay_string + \
                       corruption_string + reorder_string
                cmd4 = "tc filter add dev %s protocol ip handle %s fw classid 1:%s" % (nic, self.mark, class_id)
                tc_cmd_list.extend([cmd1, cmd2, cmd3, cmd4])
        print(tc_cmd_list)
        return tc_cmd_list, parent_id

    def exec_cmd(self):
        for cmd_list in (self.iptables_cmd_list, self.tc_cmd_list):
            for cmd in cmd_list:
                ouput = subprocess.getstatusoutput(cmd)
                print(ouput[0])
                if ouput[0]:
                    print(ouput[1])

    def __call__(self):
        self.exec_cmd()
