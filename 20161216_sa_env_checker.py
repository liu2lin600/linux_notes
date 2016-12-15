#!/usr/bin/env python3
"""Sensors Analytics installation evironment information gathering and checking script
Copyright (c) 2016 SensorsData, Inc. All Rights Reserved
"""
import os
import logging
import math
from subprocess import getoutput, call

# requirements constants
REQUIRED_RELEASE = ["centos release 6.4", "centos release 6.5", "centos release 6.6", "centos release 6.7", "centos release 6.8"]
REQUIRED_HARDWARE = ["x86_64"]
REQUIRED_FS = ["ext3", "ext4"]

SUDO_LDAP_FILE = '/etc/sudo-ldap.conf'
SUDO_CONF_FILE = '/etc/nsswitch.conf'

STANDALONE_SYS_REQ = {
        'MIN_MEMORY_GB': 8,
        'MIN_CPU_CORE_NUM': 4,
        'MIN_DISK_DATA_GB': 64 - 1,
        'MIN_DISK_HOME_GB': 20 - 1
        }

CLUSTER_SYS_REQ = {
        'MIN_MEMORY_GB': 64,
        'MIN_CPU_CORE_NUM': 16,
        'MIN_DISK_DATA_GB': 1024 - 1,
        'MIN_DISK_HOME_GB': 20 - 1,
        }

DATA_DISK_REQ = {
        'SEQ_READ_BW_MEAN_KB' : 100000,
        'SEQ_WRITE_BW_MEAN_KB' : 100000,
        'RAND_READ_BW_MEAN_KB' : 7000,
        'RAND_WRITE_BW_MEAN_KB' : 7000,
        }

STANDALONE_DATA_DISK_NUM_REQ = 1
CLUSTER_DATA_DISK_NUM_REQ = 3

GIGA = 1024 * 1024 * 1024

PART_MIN_FIO_SPACE_GB = 2

# /dev/null
FNULL = open(os.devnull, 'w')

if hasattr(os, 'statvfs'):
    """define disk_usage function (for compatible with python 3.2)"""
    import collections
    _ntuple_diskusage = collections.namedtuple('usage', 'total used free')

    def disk_usage(path):
        """Return disk usage statistics about the given path.

        Returned value is a named tuple with attributes 'total', 'used' and
        'free', which are the amount of total, used and free space, in bytes.
        """
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        return _ntuple_diskusage(total, used, free)

def read_conf(file_name):
    with open(file_name) as f:
        for line in f.readlines():
            clean_line = line.strip()
            if clean_line and not clean_line.startswith('#'):
                yield clean_line

def sample_check(self):
   """demonstrate the checker function protocol"""
   return {
           "key":"default",
           "cn_desc":"中文说明",
           "value":"取值",
           "pass_standalone":True,
           "pass_cluster":True,
           "fail_reason":"",
           }
def datetime_check():
    from time import gmtime, strftime
    return {
        "key": "test datetime",
        "cn_desc": "测试时间",
        "value": strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime()),
        "pass_standalone": True,
        "pass_cluster": True,
        "fail_reason": "",
    }

def hostname_check():
    return {
        "key": "hostname -f",
        "cn_desc": "hostname -f",
        "value": getoutput("hostname -f"),
        "pass_standalone": True,
        "pass_cluster": True,
        "fail_reason": ""
    }

def distribution_check():
    ret = {
            "key": "Linux distribution",
            "cn_desc": "Linux 发行版",
            }
    if os.path.exists("/etc/redhat-release"):
        release = getoutput("cat /etc/redhat-release").strip().lower()
        pass_check = False
        for r in REQUIRED_RELEASE:
            if r in release:
                pass_check = True
        if pass_check:
            ret.update({
                "value": release,
                "pass_standalone": True,
                "pass_cluster": True,
                "fail_reason": ""
                })
        else:
            ret.update({
                "value": release,
                "pass_standalone": False,
                "pass_cluster": False,
                "fail_reason": "仅支持以下发行版: %s" % ",".join(REQUIRED_RELEASE),
                })

        pass
    else:
        ret.update({
                "value": "[ " + getoutput("lsb_release -a") + "] not CentOS",
                "pass_standalone": False,
                "pass_cluster": False,
                "fail_reason": "非 CentOS 系统"
                })
    return ret

def hardware_check():
    ret = {
            "key": "hardware platform",
            "cn_desc": "硬件平台",
            }
    # x86_64
    hardware = getoutput("uname -i").strip()
    if hardware not in REQUIRED_HARDWARE:
        ret.update({
            "value": hardware,
            "pass_standalone": False,
            "pass_cluster": False,
            "fail_reason": "非 %s 架构" % REQUIRED_HARDWARE,
            })
    else:
        ret.update({
            "value": hardware,
            "pass_standalone": True,
            "pass_cluster": True,
            "fail_reason": "",
            })
    return ret

def mount_check():
    return {
        "key": "mount",
        "cn_desc": "mount",
        "value": getoutput("mount"),
        "pass_standalone": True,
        "pass_cluster": True,
        "fail_reason": "",
    }

def mount_check():
    return {
        "key": "mount",
        "cn_desc": "mount",
        "value": getoutput("mount"),
        "pass_standalone": True,
        "pass_cluster": True,
        "fail_reason": "",
    }

def get_lvm_devices():
    """获取lvm设备"""
    from subprocess import call, getoutput
    lvm_devices = []
    import shlex
    if call(shlex.split("which lvscan"), stdout=FNULL, stderr=FNULL) == 0:
        output = getoutput("lvscan 2>/dev/null").strip().lower()
        if output:
            for line in output.splitlines():
                dev_path = line.split("'")[1]
                if os.path.islink(dev_path):
                    dev_path = os.readlink(dev_path)
                lvm_devices.append(dev_path)
    return lvm_devices

def mem_check():
    ret = {
            "key": "ram",
            "cn_desc": "内存",
            }
    output = getoutput("cat /proc/meminfo").splitlines()
    # 某行类似MemTotal:       16268292 kB
    line = [x.lower() for x in output if
            x.lower().startswith('memtotal')][0]
    fields = line.split()
    # 单位转化
    num, unit = int(fields[1]), fields[2]
    unit_to_denominator = {
        'b': 1024 * 1024 * 1024.0,
        'kb': 1024 * 1024.0,
        'mb': 1024.0,
        'gb': 1.0,
    }
    if unit not in unit_to_denominator:
        ret.update({
            "value": "num:%d, unit:%s" % (num, unit),
            "pass_standalone": False,
            "pass_cluster": False,
            "fail_reason": "无法识别的单位: %s" % unit})
    else:
        num_gb = math.ceil(num / unit_to_denominator[unit])
        fail_standalone = num_gb < STANDALONE_SYS_REQ['MIN_MEMORY_GB']
        fail_cluster = num_gb < CLUSTER_SYS_REQ['MIN_MEMORY_GB']
        ret.update({
            "value": "%d GB" % num_gb,
            "pass_standalone": not fail_standalone,
            "pass_cluster": not fail_cluster,
            "fail_reason": ""
            })
        if fail_standalone:
            ret['fail_reason'] = ret['fail_reason'] + '单机版最小 %d GB' % STANDALONE_SYS_REQ['MIN_MEMORY_GB']
        if fail_cluster:
            ret['fail_reason'] = ret['fail_reason'] + '集群版最小 %d GB' % CLUSTER_SYS_REQ['MIN_MEMORY_GB']
    return ret

def cpu_check():
    """
    TODO: split processor num / ssse3
    """
    ret = {
            "key": "cpu",
            "cn_desc": "cpu",
            }
    output = getoutput('cat /proc/cpuinfo').splitlines()
    # 某行类似processor : 3
    lines = [l for l in output if l.strip() and l.split()[0] == 'processor']
    cpu_num = len(lines)
    fail_standalone = False
    fail_cluster = False
    fail_reason = ""
    if cpu_num < CLUSTER_SYS_REQ['MIN_CPU_CORE_NUM']:
        fail_cluster |= True
        fail_reason = "集群版最低CPU核数：%d" % CLUSTER_SYS_REQ['MIN_CPU_CORE_NUM']
    if cpu_num < STANDALONE_SYS_REQ['MIN_CPU_CORE_NUM']:
        fail_standalone = True
        fail_reason = fail_reason + ", 单机版最低CPU核数：%d" % STANDALONE_SYS_REQ['MIN_CPU_CORE_NUM']
    support_ssse3 = len([l for l in output if 'flags' in l and 'ssse3' in l]) > 0
    fail_cluster |= not support_ssse3
    if not support_ssse3:
        fail_reason = fail_reason + ", 集群版要求CPU支持ssse3指令集"
    ret.update({
        "value": "processor num: %d, support ssse3: %r" % (cpu_num, support_ssse3),
        "pass_standalone": not fail_standalone,
        "pass_cluster": not fail_cluster,
        "fail_reason": fail_reason,
        "lscpu": getoutput("lscpu"),
        "proc_cpuinfo": getoutput("cat /proc/cpuinfo"),
        })
    return ret

def user_check():
    return {
            "key": "user",
            "cn_desc": "执行用户",
            "value": getoutput("whoami"),
            "pass_standalone": True,
            "pass_cluster": True,
            "fail_reason": "",
            }

def get_mount_info():
    """ parse /proc/mounts """
    d = []
    with open('/proc/mounts') as f:
        s = f.read()
    sp = s.split('\n')
    for l in sp:
        if l.strip() == '':
            continue
        ssp = l.split(' ')
        d.append({
            'dev': ssp[0],
            'mp': ssp[1], # mount point
            'fs_type': ssp[2],
            'rw': ssp[3],
            })
    return d

def get_diskmap():
    """ get disk to partitoned device map """
    out = getoutput('lsblk -n')
    d = {}
    disk = None
    for l in out.split('\n'):
        sp = l.split(' ')
        name = sp[0].lstrip('└├─')
        if l.startswith('└') or l.startswith('├'):
            d[disk].append(name)
        else:
            disk = name
            d[disk] = []
    return d

def jsonloads(s):
    """ return None if parse fail """
    import json
    try:
        return json.loads(s)
    except Exception as e:
        return None

def check_single_data_disk_perf(dev_info, base_sub_dir="fio_test"):
    """ check one data disk's performance """
    result = {
            'pass': True,
            'fail_reason':[],
            }
    import os
    # calc base dir
    base_dir = os.path.join(dev_info['mp'], base_sub_dir)
    # make dir
    os.makedirs(base_dir, exist_ok=True)
    # decide test file name
    seq_io_path = os.path.join(base_dir, 'seq_io_test_file')
    rand_io_path = os.path.join(base_dir, 'rand_io_test_file')
    # remove old file
    for fn in [seq_io_path, rand_io_path]:
        if os.path.exists(fn):
            os.remove(fn)
    # check fio test space need
    usage = disk_usage(dev_info['mp'])
    if usage.free / GIGA < PART_MIN_FIO_SPACE_GB:
        raise Exception("dev=%r has no spance for performance test, usage=%r, at lest %d GB required" % (dev_info, usage, PART_MIN_FIO_SPACE_GB))
    # do test
    cmd = "fio --rw=readwrite --size=1000m --name=seq_io --bs=512k --runtime=180 --output-format=json --filename=%s" % seq_io_path
    print("run fio seq-io test on %s, will be finish in minutes please wait ..." % dev_info['mp'])
    seq_out = getoutput(cmd)
    seq_out_obj = jsonloads(seq_out)  # todo error handle

    cmd = "fio --rw=randrw --size=500m --name=rand_io --bs=4k --runtime=180 --output-format=json --filename=%s" % rand_io_path
    print("run fio rand-io test on %s, will be finish in minutes please wait ..." % dev_info['mp'])
    rand_out = getoutput(cmd)
    rand_out_obj = jsonloads(rand_out)  # todo error handle

    if seq_out_obj is None:
        print("fail parse json, seq out = %r" % seq_out)
    if rand_out_obj is None:
        print("fail parse json, rand out = %r" % rand_out)
    if seq_out_obj is None or rand_out_obj is None:
        raise Exception("fail to parse fio output as json")

    # do checkpr
    # todo, handle partial report case.
    for tested, expected, title in [
            (seq_out_obj['jobs'][0]['read']['bw'], DATA_DISK_REQ['SEQ_READ_BW_MEAN_KB'], '顺序读带宽'),
            (seq_out_obj['jobs'][0]['write']['bw'], DATA_DISK_REQ['SEQ_WRITE_BW_MEAN_KB'], '顺序写带宽'),
            (rand_out_obj['jobs'][0]['read']['bw'], DATA_DISK_REQ['RAND_READ_BW_MEAN_KB'], '随机读带宽'),
            (rand_out_obj['jobs'][0]['write']['bw'], DATA_DISK_REQ['RAND_WRITE_BW_MEAN_KB'], '随机写带宽'),
            ]:
        # print("%s %d %d" % (title, tested, expected))
        if tested < expected:
            result['pass'] = False
            result['fail_reason'].append("%s 过低, %d KB/s (<%d KB/s)" % (title, tested, expected))
    result['seq_io_test'] = seq_out_obj
    result['rand_io_test'] = rand_out_obj
    return result

def disk_check2(has_fio):
    """ 检查所有磁盘的状态/性能，检查是否适合安装单机版/集群版，并生成报告 """
    fail_cluster = False
    fail_standalone = False
    fail_cluster_reason = []
    fail_standalone_reason = []
    # get lvm
    lvm_devs = get_lvm_devices()
    # get mounted
    mi = get_mount_info()
    mi = [i for i in mi if i['mp'].startswith('/') and not i['mp'].startswith("/proc") and not i['mp'].startswith("/sys") and not i['mp'].startswith("/boot") and not i['mp'].startswith("/dev") and not i['mp'].startswith("/var") and i['fs_type'] != 'rootfs'] # don't check non disk part and not related part
    mi_by_name = {}
    for i in mi:
        mi_by_name[i['dev']] = i
    # get single disk part
    part_map = get_diskmap()
    single_disk_devs = []
    for pk, pv in part_map.items():
        if len(pv) == 1:
            single_disk_devs.append(pv[0])
            single_disk_devs.append(pk)
    # mark single disk part
    for i in mi:
        if len([x for x in single_disk_devs if i['dev'].endswith(x)]) > 0:
            i['single_disk_part'] = True
        else:
            i['single_disk_part'] = False
    # mark lvm
    for i in mi:
        i['is_lvm'] = i['dev'] in lvm_devs
    # chekc all disk perf.
    # only check ext3 ext4 disks
    for i in mi:
        if i['fs_type'] in ['ext3', 'ext4']:
            usage = disk_usage(i['mp'])
            i['usage'] = {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            }
            if has_fio:
                res = check_single_data_disk_perf(i)
                i['perf_res'] = res
            else:
                i['perf_res'] = {
                    'pass': False,
                    'error': 'no fio, could not perf test'
                }
    # find home part and check space
    home_device = getoutput('df /home | tail -n "+2"').split(' ')[0]
    home_usage = disk_usage(mi_by_name[home_device]['mp'])
    if home_usage.total <= STANDALONE_SYS_REQ['MIN_DISK_HOME_GB'] * GIGA:
        fail_standalone = True
        fail_standalone_reason.append('单机版 /home 分区不得低于 %d GB (实测 %s %d GB)' % (STANDALONE_SYS_REQ['MIN_DISK_HOME_GB'], home_device, home_usage.total / GIGA))
    if home_usage.total <= CLUSTER_SYS_REQ['MIN_DISK_HOME_GB'] * GIGA:
        fail_cluster = True
        fail_cluster_reason.append('集群版 /home 分区不得低于 %d GB (实测 %s %d GB)' % (CLUSTER_SYS_REQ['MIN_DISK_HOME_GB'], home_device, home_usage.total / GIGA))
    # check single disk fit data disk need
    for i in mi:
        # cluster support
        # ext4 && perf && size && single disk && size && perf
        usage = disk_usage(i['mp'])
        cluster_size_pass = usage.total / GIGA > CLUSTER_SYS_REQ['MIN_DISK_DATA_GB']
        standalone_size_pass = usage.total / GIGA > STANDALONE_SYS_REQ['MIN_DISK_DATA_GB']
        i['cluster_data_disk_pass'] = i['fs_type'] == 'ext4' and i['single_disk_part'] and i['perf_res']['pass'] and cluster_size_pass
        i['standalone_data_disk_pass'] = i['fs_type'] in ['ext3', 'ext4'] and i['single_disk_part'] and i['perf_res']['pass'] and standalone_size_pass
    # check disk num
    cluster_pass_parts = list(filter(lambda x: x['cluster_data_disk_pass'], mi))
    standalone_pass_parts = list(filter(lambda x: x['standalone_data_disk_pass'], mi))

    if len(cluster_pass_parts) < CLUSTER_DATA_DISK_NUM_REQ:
        fail_cluster = True
        if not has_fio:
            fail_cluster_reason.append("未安装 fio，无法确认磁盘性能")
        else:
            fail_cluster_reason.append("找到 %d 块合格的数据盘，集群版每台机器需要至少 %d 块" % (len(cluster_pass_parts), CLUSTER_DATA_DISK_NUM_REQ))
    if len(standalone_pass_parts) < STANDALONE_DATA_DISK_NUM_REQ:
        fail_standalone = True
        if not has_fio:
            fail_standalone_reason.append("未安装 fio，无法确认磁盘性能")
        else:
            fail_standalone_reason.append("找到 %d 块合格的数据盘，单机版需要至少 %d 块" % (len(cluster_pass_parts), STANDALONE_DATA_DISK_NUM_REQ))
    return {
        "fail_cluster": fail_cluster,
        "fail_standalone": fail_standalone,
        "fail_cluster_reason": fail_cluster_reason,
        "fail_standalone_reason": fail_standalone_reason,
        "disk_stats": mi,
        "home_device": home_device,
        "lvm_devices": lvm_devs
    }

def write_report(user, time, hostname, distro, hw, mem, cpu, disk, outfile):
    lines = []
    sp = "---------------------------------------"
    lines.append("Sensors Analytics installation evironment check report")
    lines.append(sp)
    lines.append("user:              " + user.get("value"))
    lines.append("test date:         " + time.get("value"))
    lines.append("hostname -f:       " + hostname.get("value"))
    lines.append("distro:            " + distro.get("value"))
    lines.append("hardware platform: " + hw.get("value"))
    lines.append("memory:            " + mem.get("value"))
    lines.append(sp)
    lines.append("lscpu:")
    lines.append(cpu['lscpu'])
    lines.append(sp)
    lines.append("/proc/cpuinfo:")
    lines.append(cpu['proc_cpuinfo'])
    lines.append(sp)
    lines.append("df -h")
    lines.append(getoutput("df -h"))
    lines.append(sp)
    lines.append("mount")
    lines.append(getoutput("mount"))
    lines.append(sp)
    lines.append("disk detail:")
    import io
    ppout = io.StringIO()
    import pprint
    pprint.pprint(disk, stream=ppout)
    lines.append(ppout.getvalue())

    for l in lines:
        print(l, file=outfile)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog='sa_env_check', add_help=True)
    subp = parser.add_subparsers(dest='subp')
    check = subp.add_parser('check', help='执行环境检查')
    check.add_argument('--no_disk', dest='no_disk', action='store_true', help="无法安装fio或无需检查磁盘的时候，可选择不做磁盘检查")
    check.add_argument('--outfile', dest='outfile', type=str, required=True, help="指定报告输出到的文件名")
    args = parser.parse_args()
    
    if args.subp in ['check']:
        fail_cluster = False
        fail_standalone = False

        list_a = [
            user_check,
            datetime_check,
            hostname_check,
            distribution_check,
            hardware_check,
            mem_check,
            cpu_check,
            ]
        ret_list_a = [f() for f in list_a]
        for i in ret_list_a:
            if not i.get('pass_standalone', False):
                fail_standalone = True
            if not i.get('pass_cluster', False):
                fail_cluster = True
        disk_ret = {}
        import shlex, pprint
        has_fio = call(shlex.split("which fio"), stdout=FNULL, stderr=FNULL) == 0
        if not args.no_disk:
            if not has_fio:
                print("fio not found, won't do disk performance test. (install fio and run check again to get full report)")
            disk_ret = disk_check2(has_fio)
            if disk_ret['fail_cluster']:
                fail_cluster = True
            if disk_ret['fail_standalone']:
                fail_standalone = True
        with open(args.outfile, 'w') as f:
            a = ret_list_a
            write_report(a[0], a[1], a[2], a[3], a[4], a[5], a[6], disk_ret, f)
        print("check finish")
    else:
        parser.print_help()
