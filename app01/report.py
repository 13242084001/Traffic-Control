#!/usr/bin/env python3.6
#
import pandas


class Pd(object):
    def __init__(self):
        self.data = {"分辨率": [], "发送端丢包设置": [], "发送端编码帧率(F/S)": [], "发送端Qos之前丢包率":[], "发送端Qos前占用带宽(kbps)": [], "发送端Qos后丢包率": [], "发送端Qos后占用带宽(kbps)": [], "测试时长（min）": [], "接收端解码帧率(F/S)": [], "最大连续丢包个数": [], "nack平均补偿码率(bps)": [], "主观感受": []}
        pd = pandas.DataFrame(self.data)
        excel = pd.to_excel('report.xlsx')

test = Pd()
