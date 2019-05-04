import subprocess
from app01 import models
import netifaces
from IPy import IP


class GetIfaces(object):

    def __init__(self):
        self.nic_list = netifaces.interfaces().remove('lo')
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
    """
    def __call__(self, *args, **kwargs):
        self.nic_interface_info()
    """


class IptablesHandle(object):
    def make_iptables_list(*args, **kwargs):
        rule = kwargs.get("rule")
        protocol = rule.get("protocol")
        local_ip = rule.get("local_ip")
        print(local_ip, type(local_ip))
        local_port = rule.get("local_port")
        remote_ip = rule.get("remote_ip")
        remote_port = rule.get("remote_port")
        controlling_ip = args
        print(controlling_ip*3)

        if not protocol:
            protocol = "all"

        if not local_ip:
            local_ip = controlling_ip
        src_string = " -s %s" % local_ip

        if not local_port:
            sport_string = ""
        elif len(str(local_port).split(",")) > 1:
            sport_string = " –m multiport --sports %s" % local_port
        else:
            sport_string = " --dport %s" % local_port

        if not remote_ip:
            dst_string = ""
        else:
            dst_string = " -d %s" % remote_ip

        if not remote_port:
            dport_string = ""

        elif len(str(remote_port).split(",")) > 1:
            dport_string = " –m multiport --dports %s" % remote_port
        else:
            dport_string = " --dport %s" % remote_port
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

        return iptables_cmd_list, local_ip

    def exec_iptables(*args):
        for rule in args:
            pass
            #ouput = subprocess.getstatusoutput(rule)
            #if ouput[0]:
            #    return ouput[1]


class TcHandle(object):
    def confirm_dev(*args):
        inet_obj = GetIfaces()
        net_dict = inet_obj.interfaces_dict
        print(net_dict)
        for k, v in net_dict.items():
            print(type(v.get("hosts")))
            if args[0] in v.get("hosts"):
                net_dict.pop(k)
                return net_dict.keys()

    def make_tc_list(*args, **kwargs):
        controlling_ip = args
        upstream = kwargs.get('upstream')
        downstream = kwargs.get('downstream')

        dev = TcHandle.confirm_dev(*args)
        print(upstream, type(upstream))
        # 带宽
        rate = upstream.get("rate")
        # 丢包
        loss = upstream.get('loss')

        # 延时
        delay = upstream.get('delay')

        # 包损坏
        corruption = upstream.get("corruption")

        # 包乱序
        reorder = upstream.get("reorder")

        if rate:
            rate_string = " rate %skbps" % rate
        else:
            rate_string = " rate 10mbit"

        if loss.get("percentage"):
            if loss.get("correlation"):
                loss_string = " loss %s%% %s%%" % (loss.get("percentage"), loss.get("correlation"))
            else:
                loss_string = " loss %s%%" % loss.get("percentage")
        else:
            loss_string = ""

        if delay.get("delay"):
            delay_string = " delay %s%%" % delay.get("delay")
        else:
            delay_string = ""

        if corruption.get("percentage"):
            corruption_string = " corruption %s%%" % corruption.get("percentage")
        else:
            corruption_string = ""

        if reorder.get("percentage"):

            if reorder.get("correlation"):
                reorder_string = " reorder %s%% %s%%" % (reorder.get("percentage"), reorder.get("correlation"))
            else:
                reorder_string = " reorder %s%%" % reorder.get("percentage")
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
        return tc_cmd_list, parent_id

    def exec_tc(*args):
        for rule in args:
            pass
            # ouput = subprocess.getstatusoutput(rule)
            # if ouput[0]:
            #    return ouput[1]



