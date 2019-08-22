#!/usr/bin/env python3.6
#coding=utf-8
from pyroute2 import IPRoute,protocols
import socket
import getopt
import sys
import os
import netifaces
import ipaddress
from IPy import IP
from prettyprinter import cpprint


def usage():
    print('Usage: -h help \n'
            '       -d destination ip address\n'
            '       -s source ip address\n'
            '       -i interface\n'
            '       -r rate bitrate\n'
            '       -f flush tc qdisc\n'
            '       -l loss rate\n'
            '       -D delay\n'
            )

def args(usage):
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hfd:s:i:r:l:D:", ['help', 'flush', 'dst=', 'src=', 'interface=', 'rate=', 'loss=', 'delay='])
        options_dict = {}
        for k, v in opts:
            if k in ('-h', '--help'):
                usage()
                os._exit(0)
            elif k in ('-f', '--flush'):
                interface = options_dict.get('interface')
                options_dict.clear()
                options_dict['interface'] = interface
                options_dict['flush'] = True
                return options_dict
            elif k in ('-d', '--dst'):
                options_dict['dst'] = v
            elif k in ('-s', '--src'):
                options_dict['src'] = v
            elif k in ('-i', '--interface'):
                options_dict["interface"] = v
            elif k in ('-r', "--rate"):
                options_dict["rate"] = v
            elif k in ('-l', '--loss'):
                options_dict["loss"] = int(v)
            elif k in ('-D', '--delay'):
                options_dict['delay'] = int(v)
        return options_dict
    except Exception as e:
        print(str(e))
        usage()
        os._exit(0)
    
class tc_handle(object):
    
    def __init__(self, dst=None, src=None, interface=None, rate='500', flush=False, loss=0, delay=0):
        self.ip = IPRoute()
        self.rate = rate
        self.nic = self.ip.link_lookup(ifname=interface if interface else 'eth0')[0]
        #print('nic is %s'% (self.nic))
        self.flush = flush
        self.loss = loss
        self.delay = delay
        if not self.flush:
            if dst != None and src == None:
                filter_addr_tp = ('dst', dst)
            elif src != None and dst == None:
                filter_addr_tp = ('src', src)
            else:
                filter_addr_tp = None
            flag, self.filter_addr = (None, self.ip.get_addr(label=interface)[0].get('attrs')[0][1]) if not filter_addr_tp else filter_addr_tp
            #print(self.filter_addr, self.rate)
            self.keys = self.v4_hex(self.filter_addr, flag)
            #print(self.keys)
            #print(self.nic)

    def v4_hex(self, dict_str, flag):
        flags = '+12' if flag == 'src' else '+16'
        #print('flags %s' % flags)
        try:
            dst_ip_str = IP(dict_str).strNormal(2) if len(dict_str.split('/')) > 1 else dict_str + '/255.255.255.255'
            #dst_net, mask = dst_ip_str.split('/')
            #print(dst_ip_str)
            try:
                keys = ['/'.join([str(hex(int(ipaddress.IPv4Address(i)))) for i in dst_ip_str.split('/')]) + flags]
                #print('this is key %s' % keys)

            except Exception as e:
                #print("ip is not available!")
                os._exit(0)
            return keys
        except Exception as e:
            print(str(e))
            os._exit(0)

    def flush_instance(self):
        try:
            self.ip.tc('del', 'htb', self.nic, 0x10000)
        except Exception as e:
            pass
    """
    def only_rate_limit(self):
        self.ip.tc('add', 'tbf', self.nic, 0x100000, parent=0x10010, rate=self.rate+'kbit', burst=1024 * 2, latency='200ms')

    def only_no_rate_limit(self):
        self.ip.tc('add', 'netem', self.nic, 0x100000, parent=0x10010, loss=30)
    """
    def __call__(self):
        self.flush_instance()
        if not self.flush:
            self.ip.tc('add', 'htb', self.nic, 0x10000, default=0x200000)
            self.ip.tc('add-class', 'htb', self.nic, 0x10001, parent=0x10000, rate='1000mbit', prio=4)
            #print(self.rate)
            self.ip.tc('add-class', 'htb', self.nic, 0x10010, parent=0x10001, rate=self.rate+'kbit',prio=3)
            self.ip.tc('add-class', 'htb', self.nic, 0x10020, parent=0x10001, rate='700mbit', prio=2)
            if self.loss or self.delay:
                #print(self.delay)
                self.ip.tc('add', 'netem', self.nic, 0x100000, parent=0x10010, loss=self.loss, delay=self.delay)
            else:
                self.ip.tc('add', 'tbf', self.nic, 0x100000, parent=0x10010, rate=self.rate+'kbit', burst=1024 * 2, latency='200ms')
            self.ip.tc('add', 'sfq', self.nic, 0x200000, parent=0x10020, perturb=10)
            #pyroute2 有bug，对socket家族的协议解析有不正确的地方，比如AF_INET应该解析成IPV4,但是解析成了ax25,AF_AX25解析成了all,所以将错就错用这个好了,protocols也一样的结果
            self.ip.tc('add-filter', 'u32', self.nic, parent=0x10000, prio=1, protocol=socket.AF_AX25, target=0x10010, keys=self.keys)
    
def main():
    options_dict = args(usage)
    cpprint(options_dict)
    tc_handle(**options_dict)()

if __name__ == "__main__":
    main()
