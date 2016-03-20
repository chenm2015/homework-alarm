import radix # takes 1/4 the time as patricia
import datetime
import numpy as np
import calendar # do not use the time module
import cmlib
import operator
import string
import gzip
import traceback
import logging
import subprocess
import ast
import calendar
import os
import urllib

import sklearn
print('The scikit-learn version is {}.'.format(sklearn.__version__))

from sklearn.cluster import DBSCAN

from netaddr import *
from env import *
from cStringIO import StringIO

#from sklearn.datasets.samples_generator import make_blobs
#from sklearn.preprocessing import StandardScaler

class Micro_fighter():

    def __init__(self, reaper):
        self.reaper = reaper
        self.sdate = self.reaper.period.sdate
        self.granu = self.reaper.granu
        self.period = reaper.period
        self.sdt_obj = None
        self.edt_obj = None

        self.updt_filel = self.period.get_filelist()

        self.mfilegroups = None

        self.middle_dir = self.period.get_middle_dir()
        self.final_dir = self.period.get_final_dir()

    def all_events_ratios(self):

        event_dict = self.get_events_list()

        for unix_dt in event_dict:
            rel_size = event_dict[unix_dt][0] # relative size
            width = event_dict[unix_dt][4]
            size = event_dict[unix_dt][1]
            height = event_dict[unix_dt][3] # or prefix number


            #---------------------------------------------
            # obtain the prefix and monitor(index) sets of the event
            pfx_set = set()
            mon_set = set()

            event_fpath = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
            f = open(event_fpath, 'r')
            for line in f:
                line = line.rstrip('\n')
                if line.startswith('Mo'):
                    mon_set = ast.literal_eval(line.split('set')[1])
                else:
                    pfx_set.add(line.split(':')[0])
            f.close()


            #-----------------------------------
            # read the middle files
            target_fg = None
            for fg in self.reaper.filegroups:
                if int(fg[0].rstrip('.txt.gz')) == unix_dt:
                    target_fg = fg
                    break

            pfx_int_data = dict()
            for fname in target_fg:
                floc = self.reaper.middle_dir + fname
                print 'Reading ', floc
                p = subprocess.Popen(['zcat', floc],stdout=subprocess.PIPE)
                fin = StringIO(p.communicate()[0])
                assert p.returncode == 0
                for line in fin:
                    line = line.rstrip('\n')
                    if line == '':
                        continue

                    pfx = line.split(':')[0]
                    datalist = ast.literal_eval(line.split(':')[1])

                    try:
                        c_list = pfx_int_data[pfx]
                        combined = [x+y for x,y in zip(datalist, c_list)]
                        pfx_int_data[pfx] = combined
                    except:
                        pfx_int_data[pfx] = datalist

            #------------------------------------------
            # get the number of updates and 1s in and out of the event
            udt_num = 0
            for pfx in pfx_int_data:
                the_sum = sum(pfx_int_data[pfx])
                udt_num += the_sum

            udt_in_num = 0
            for pfx in pfx_set:
                for mon_index in mon_set:
                    udt_in_num += pfx_int_data[pfx][mon_index]

            udt_out_num = udt_num - udt_in_num
            print udt_num
            print udt_in_num

            ones_num = 0
            for pfx in pfx_int_data:
                datalist = pfx_int_data[pfx]
                for data in datalist:
                    if data > 0:
                        ones_num += 1

            ones_in_num = 0
            for pfx in pfx_set:
                for mon_index in mon_set:
                    if pfx_int_data[pfx][mon_index] > 0:
                        ones_in_num += 1

            ones_out_num = ones_num - ones_in_num
            print ones_num
            print ones_in_num

            #--------------------------------------------
            # analyze prefixes
            all_pfx_num = self.reaper.period.get_fib_size()
            prefix_ratio = float(height) / float(all_pfx_num)
            print prefix_ratio

            #-------------------------------------------
            # distribution of origin ASes TODO: move to somewhere else
            all_AS_num = self.reaper.period.get_AS_num()

            pfx2as = self.get_pfx2as()
            asn_dict = dict()
            for pfx in pfx_set:
                try:
                    asn = pfx2as[pfx]
                except:
                    asn = -1
                try:
                    asn_dict[asn] += 1
                except:
                    asn_dict[asn] = 1

            #for asn in asn_dict:
            #    asn_dict[asn] = float(asn_dict[asn]) / float(all_AS_num)
            print asn_dict

            #-----------------------------------------
            # TODO: write result to files


    def set_sedate(self, sdt_obj, edt_obj):
        self.sdt_obj = sdt_obj
        self.edt_obj = edt_obj

    def get_mfile_group_trange(self):
        self.mfilegroups = list() # list of middle file groups

        mfiles = os.listdir(self.middle_dir)
        for f in mfiles:
            if not f.endswith('.gz'):
                mfiles.remove(f)
        mfiles.sort(key=lambda x:int(x.rstrip('.txt.gz')))

        #----------------------------------------------------------------------
        # group middle files according to the desired granularity

        # get granularity of middle files
        self.m_granu = (int(mfiles[1].rstrip('.txt.gz')) - int(mfiles[0].rstrip('.txt.gz'))) / 60
        shift = self.reaper.shift
        shift_file_c = shift / self.m_granu
        mfiles = mfiles[shift_file_c:] # shift the interval

        group_size = self.granu / self.m_granu
        group = []
        for f in mfiles:
            group.append(f)
            if len(group) is group_size:
                self.mfilegroups.append(group)
                group = []

        #--------------------------------------------------------
        # delete the files that is not in our concern range
        group_to_delete = []
        for fg in self.mfilegroups:
            unix_dt = int(fg[0].rstrip('.txt.gz')) # timestamp of current file group
            dt_obj = datetime.datetime.utcfromtimestamp(unix_dt)
            if dt_obj < self.sdt_obj or dt_obj > self.edt_obj:
                group_to_delete.append(fg)

        for gd in group_to_delete:
            self.mfilegroups.remove(gd)


    def bgp_leak_pfx(self):
        pfx_set = set()
        fname = datadir + 'final_output/bell-leak.txt'
        f = open(fname, 'r')
        for line in f:
            line = line.rstrip('\n')
            pfx = line.split('=')[1]
            pfx_set.add(pfx)
        f.close()

        return pfx_set


    # Not used at any place ???
    def upattern_for_pfx(self, unix_dt, pset):
        pfx_set = pset
        mon_iset = set()
        mon_set = set()

        event_fpath = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
        f = open(event_fpath, 'r')
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('Mo'):
                mon_iset = ast.literal_eval(line.split('set')[1])
        f.close()

        i2ip = dict()
        f = open(self.reaper.period.get_mon2index_file_path(), 'r')
        for line in f:
            line = line.rstrip('\n')
            ip = line.split(':')[0]
            index = int(line.split(':')[1])
            i2ip[index] = ip
        f.close()

        for index in mon_iset:
            mon_set.add(i2ip[index])

        pattern2count = dict()
        # pfx=>xxxxxx, mon=>xxx, pfx+mon=>xxxxxxxxx, to save memory
        pfx2tag = dict()
        mon2tag = dict()

        start = 100000
        for pfx in pfx_set:
            pfx2tag[pfx] = str(start)
            start += 1

        start = 100
        for mon in mon_set:
            mon2tag[mon] = str(start)
            start += 1
        mcount = len(mon_set)

        #--------------------------------------------------------
        # Read update files
        sdt_unix = unix_dt
        edt_unix = unix_dt + self.reaper.granu * 60
        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)

        num2type = num2upattern
        for n in num2type:
            pattern2count[n] = set()
        #WW:0,AAdu1:1,AAdu2:2,AAdiff:3,WA:4(WADup:41,WADiff:42,WAUnknown:40),AW:5
        mp_dict = dict() # mon: prefix: successive update type series (0~5)
        mp_last_A = dict() # mon: prefix: latest full update
        mp_last_type = dict()
        for m in mon_set:
            mp_dict[m] = dict()
            mp_last_A[m] = dict() # NOTE: does not record W, only record A
            mp_last_type[m] = dict()


        pfx2aadiff = dict()
        pfx2policy = dict()
        for pfx in pfx_set:
            pfx2policy[pfx] = set()
            pfx2aadiff[pfx] = set()


        fpathlist = select_update_files(updt_files, sdt_unix, edt_unix)
        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat', fpath],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    pfx = attr[5]
                    type = attr[2]
                    mon = attr[3]

                    if (mon not in mon_set) or (pfx not in pfx_set):
                        continue

                    unix = int(attr[1])
                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    if type == 'A':
                        as_path = attr[6]

                    the_tag = pfx2tag[pfx] + mon2tag[mon]

                    try:
                        test = mp_dict[mon][pfx]
                    except:
                        mp_dict[mon][pfx] = list() # list of 0~5

                    try:
                        last_A = mp_last_A[mon][pfx]
                        last_as_path = last_A.split('|')[6]
                    except:
                        last_A = None
                        last_as_path = None

                    try:
                        last_type = mp_last_type[mon][pfx]
                    except: # this is the first update for the mon-pfx pair
                        last_type = None

                    if last_type == 'W':
                        if type == 'W':
                            mp_dict[mon][pfx].append(0)
                            pattern2count[0].add(the_tag)
                            pattern2count[800].add(the_tag)
                            pattern2count[801].add(the_tag)
                        elif type == 'A':
                            if last_as_path:
                                if as_path == last_as_path:
                                    mp_dict[mon][pfx].append(41)
                                    pattern2count[41].add(the_tag)
                                    pattern2count[799].add(the_tag)
                                    pattern2count[801].add(the_tag)
                                else:
                                    mp_dict[mon][pfx].append(42)
                                    pattern2count[42].add(the_tag)
                                    pattern2count[799].add(the_tag)
                                    pattern2count[798].add(the_tag)
                            else: # no A record
                                mp_dict[mon][pfx].append(40)
                                pattern2count[40].add(the_tag)
                            mp_last_A[mon][pfx] = line
                
                    elif last_type == 'A':
                        if type == 'W':
                            mp_dict[mon][pfx].append(5)
                            pattern2count[5].add(the_tag)
                        elif type == 'A':
                            if line == last_A:
                                mp_dict[mon][pfx].append(1)
                                pattern2count[1].add(the_tag)
                                pattern2count[800].add(the_tag)
                                pattern2count[801].add(the_tag)
                            elif as_path == last_as_path:
                                mp_dict[mon][pfx].append(2)
                                pattern2count[2].add(the_tag)
                                pattern2count[802].add(the_tag)
                                pfx2policy[pfx].add(the_tag)
                            else:
                                mp_dict[mon][pfx].append(3)
                                pattern2count[3].add(the_tag)
                                pattern2count[799].add(the_tag)
                                pattern2count[798].add(the_tag)
                                pfx2aadiff[pfx].add(the_tag)
                            mp_last_A[mon][pfx] = line
                
                    else: # last_type is None
                        pass

                    # Important: Get new information
                    if type == 'W':
                        mp_last_type[mon][pfx] = 'W'
                    elif type == 'A':
                        mp_last_type[mon][pfx] = 'A'
                        mp_last_A[mon][pfx] = line
                    else:
                        assert False
                    
                except Exception, err:
                    if line != '':
                        logging.info(traceback.format_exc())
                        logging.info(line)
            myf.close()


        type2num = dict()
        type2ratio = dict()
        total = 0
        for mon in mp_dict:
            for pfx in mp_dict[mon]:
                for t in mp_dict[mon][pfx]:
                    name = num2type[t]
                    total += 1
                    try:
                        type2num[name] += 1
                    except:
                        type2num[name] = 1
        
        for t in type2num:
            type2ratio[t] = float(type2num[t]) / float(total)

        print pfx2policy
        print 'writing ', self.reaper.get_output_dir_event() + str(unix_dt) + '_tpfx_policy_ratio.txt'
        f = open(self.reaper.get_output_dir_event() + str(unix_dt) + '_tpfx_policy_ratio.txt', 'w')
        for pfx in pfx2policy:
            f.write(pfx+':'+str(len(pfx2policy[pfx]))+'|'+str(mcount)+'\n')
        f.close()

        print 'writing ', self.reaper.get_output_dir_event() + str(unix_dt) + '_tpfx_aadiff_ratio.txt'
        f = open(self.reaper.get_output_dir_event() + str(unix_dt) + '_tpfx_aadiff_ratio.txt', 'w')
        for pfx in pfx2aadiff:
            f.write(pfx+':'+str(len(pfx2aadiff[pfx]))+'|'+str(mcount)+'\n')
        f.close()


    def analyze_slot(self, unix_dt):
        #-------------------------------------------------------
        # identify the HUQP HUVP and HAP sets
        Tv = self.reaper.Tv
        Tq = self.reaper.Tq
        huqp_set = set()
        huvp_set = set()
        hap_set = set()

        mydir = self.reaper.get_output_dir_pfx()
        fpath = mydir + str(unix_dt) + '_pfx.txt'
        f = open(fpath, 'r')
        for line in f:
            line = line.rstrip('\n')
            pfx = line.split(':')[0]
            line = line.split(':')[1].split('|')

            uq = int(line[0])
            uv = float(line[1])
            if uq >= Tq:
                huqp_set.add(pfx)
                if uv >= Tv:
                    hap_set.add(pfx)
            if uv >= Tv:
                huvp_set.add(pfx)


        #--------------------------------------------------------
        # Read update files

        # working monitor set
        monset = self.reaper.period.used_monitors()

        # origin AS recording
        huqp2oriAS = dict()
        hap2oriAS = dict()
        huqp_oriAS2num = dict()
        hap_oriAS2num = dict()

        # observing monitor set
        huqp2mon = dict()
        hap2mon = dict()

        sdt_unix = unix_dt
        edt_unix = unix_dt + self.reaper.granu * 60
        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)
        fmy.close()

        fo = open(datadir+'analyze_slot.txt', 'w')

        fpathlist = select_update_files(updt_files, sdt_unix, edt_unix)
        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat',fpath],stdout=subprocess.PIPE,close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    pfx = attr[5]
                    mon = attr[3]
                    type = attr[2]
                    unix = int(attr[1])

                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    if mon not in monset:
                        continue

                    if type == 'A':
                        as_path = attr[6]
                        oriAS = int(as_path.split()[-1])

                        if pfx in huqp_set:
                            huqp2oriAS[pfx] = oriAS

                        if pfx in hap_set:
                            hap2oriAS[pfx] = oriAS

                    try:
                        huqp2mon[pfx].add(mon)
                    except:
                        huqp2mon[pfx] = set([mon])
                    try:
                        hap2mon[pfx].add(mon)
                    except:
                        hap2mon[pfx] = set([mon])

                except:
                    pass
            myf.close()

        for p in huqp2oriAS:
            asn = huqp2oriAS[p]
            try:
                huqp_oriAS2num[asn] += 1
            except:
                huqp_oriAS2num[asn] = 1
        for p in hap2oriAS:
            asn = hap2oriAS[p]
            try:
                hap_oriAS2num[asn] += 1
            except:
                hap_oriAS2num[asn] = 1

        for asn in huqp_oriAS2num:
            fo.write('#'+str(asn)+':'+str(huqp_oriAS2num[asn])+'\n')
        for asn in hap_oriAS2num:
            fo.write('A'+str(asn)+':'+str(hap_oriAS2num[asn])+'\n')

        fo.close()


        #--------------------------------------------------
        # the UV and UQ of every pfx
        mydir = self.reaper.get_output_dir_pfx()
        fpath = mydir + str(unix_dt) + '_pfx.txt'

        uvsum = 0.0
        uvcount = 0.0
        fo2 = open(datadir+'analyze_slot2.txt', 'w')
        f = open(fpath, 'r')
        for line in f:
            line = line.rstrip('\n')
            pfx = line.split(':')[0]
            tmp = line.split(':')[1].split('|')
            uq = int(tmp[0])
            uv = float(tmp[1])
            if uq >= Tq:
                fo2.write('#'+line+'\n')
                if uv >= Tv:
                    fo2.write('A'+line+'\n')
                else:
                    uvsum += uv
                    uvcount += 1

        print uvsum/uvcount
        f.close()
        fo2.close()


    def event_update_pattern(self, unix_dt, target_pset):
        # all the prefixes and monitors in an LBE are considered

        pfx_set = set()
        if target_pset != None:
            pfx_set = target_pset

        mon_iset = set()
        mon_set = set()

        event_fpath = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
        f = open(event_fpath, 'r')
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('Mo'):
                mon_iset = ast.literal_eval(line.split('set')[1])
            elif target_pset == None:
                pfx_set.add(line.split(':')[0])
        f.close()

        i2ip = dict()
        f = open(self.reaper.period.get_mon2index_file_path(), 'r')
        for line in f:
            line = line.rstrip('\n')
            ip = line.split(':')[0]
            index = int(line.split(':')[1])
            i2ip[index] = ip
        f.close()

        for index in mon_iset:
            mon_set.add(i2ip[index])

        pattern2tag = dict()
        # pfx=>xxxxxx, mon=>xxx, pfx+mon=>xxxxxxxxx, to save memory
        pfx2tag = dict()
        mon2tag = dict()

        start = 100000
        for pfx in pfx_set:
            pfx2tag[pfx] = str(start)
            start += 1

        start = 100
        for mon in mon_set:
            mon2tag[mon] = str(start)
            start += 1

        tag_set = set() # record all existed tags (element '1's)

        #--------------------------------------------------------
        # Read update files
        sdt_unix = unix_dt
        edt_unix = unix_dt + self.reaper.granu * 60
        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)

        num2type = num2upattern
        for n in num2type:
            pattern2tag[n] = set()

        mp_dict = dict() # mon: prefix: successive update type series (0~5)
        mp_last_A = dict() # mon: prefix: latest full update
        mp_last_type = dict()
        for m in mon_set:
            mp_dict[m] = dict()
            mp_last_A[m] = dict() # NOTE: does not record W, only record A
            mp_last_type[m] = dict()

        total_update = 0

        fpathlist = cmlib.select_update_files(updt_files, sdt_unix, edt_unix)
        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat', fpath],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    pfx = attr[5]
                    type = attr[2]
                    mon = attr[3]

                    if (mon not in mon_set) or (pfx not in pfx_set):
                        continue

                    unix = int(attr[1])
                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    total_update += 1

                    if type == 'A':
                        as_path = attr[6]

                    the_tag = pfx2tag[pfx] + mon2tag[mon]
                    tag_set.add(the_tag)

                    try:
                        test = mp_dict[mon][pfx]
                    except:
                        mp_dict[mon][pfx] = list() # list of 0~5

                    try:
                        last_A = mp_last_A[mon][pfx]
                        last_as_path = last_A.split('|')[6]
                    except:
                        last_A = None
                        last_as_path = None

                    try:
                        last_type = mp_last_type[mon][pfx]
                    except: # this is the first update for the mon-pfx pair
                        last_type = None

                    up = self.get_update_pattern(last_type, type, last_as_path, as_path, last_A, line)
                    if up != -1: # not the first update
                        try:
                            mp_dict[mon][pfx].append(up)
                        except:
                            mp_dict[mon][pfx] = [up]

                        pattern2tag[up].add(the_tag)
                
                    if type == 'W':
                        mp_last_type[mon][pfx] = 'W'
                    elif type == 'A':
                        mp_last_type[mon][pfx] = 'A'
                        mp_last_A[mon][pfx] = line
                    else:
                        assert False
                    
                except Exception, err:
                    pass
            myf.close()


        type2num = dict()
        type2ratio = dict()
        total = 0
        for mon in mp_dict:
            for pfx in mp_dict[mon]:
                for t in mp_dict[mon][pfx]:
                    name = num2type[t]
                    total += 1
                    try:
                        type2num[name] += 1
                    except:
                        type2num[name] = 1
        
        for t in type2num:
            type2ratio[t] = float(type2num[t]) / float(total)

        print type2num
        print type2ratio
        sorted_list = sorted(type2num.items(), key=operator.itemgetter(1), reverse=True)
        if target_pset == None:
            f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_updt_pattern.txt', 'w')
        else:
            f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_updt_pattern_tpfx.txt', 'w')

        for item in sorted_list:
            tp = item[0]
            count = item[1]
            ratio = type2ratio[tp]
            f.write(str(tp)+':'+str(count)+' '+str(ratio)+'\n')
        f.close()

        p2ratio = dict()
        for p in pattern2tag:
            p2ratio[num2type[p]] = float(len(pattern2tag[p])) / float(len(tag_set))
        sorted_list = sorted(p2ratio.items(), key=operator.itemgetter(1), reverse=True)
        if target_pset == None:
            f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_updt_pattern_in_ones.txt', 'w')
        else:
            f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_updt_pattern_in_ones_tpfx.txt', 'w')

        for item in sorted_list:
            p = item[0]
            ratio = item[1]
            f.write(str(p)+':'+str(ratio)+'\n')
        f.close()

        print 'Total update: ', total_update


    # Note: cannot compare unix time in the lines
    def get_update_pattern(self, last_type, type, last_as_path, as_path, last_A, line):
        upattern = -1

        if last_type == 'W':
            if type == 'W':
                upattern = 0
                return upattern
            elif type == 'A':
                if last_as_path: # if not None
                    if line.split('|A|')[1] == last_A.split('|A|')[1]:
                        upattern = 411
                        return upattern
                    elif as_path == last_as_path:
                        upattern = 412
                        return upattern
                    else:
                        upattern = 42
                        return upattern
                else: # no A record
                    upattern = 40
                    return upattern
    
        elif last_type == 'A':
            if type == 'W':
                upattern = 5
                return upattern
            elif type == 'A':
                if line.split('|A|')[1] == last_A.split('|A|')[1]:
                    upattern = 1
                    return upattern
                elif as_path == last_as_path:
                    upattern = 2
                    return upattern
                else:
                    upattern = 3
                    return upattern

        else:
            return upattern # the first update


    def oriAS_in_updt(self, unix_dt, target_pfx):
        print 'getting origin AS for ', unix_dt

        pfx_set = set()
        pfx_recording = True
        mon_iset = set() # index set
        mon_set = set() # ip set

        if target_pfx != None:
            pfx_set = target_pfx
            pfx_recording = False

        event_fpath = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
        f = open(event_fpath, 'r')
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('Mo'):
                mon_iset = ast.literal_eval(line.split('set')[1])
            elif pfx_recording: # Do not record if target_pfx is not None
                pfx_set.add(line.split(':')[0])
        f.close()

        i2ip = dict()
        f = open(self.reaper.period.get_mon2index_file_path(), 'r')
        for line in f:
            line = line.rstrip('\n')
            ip = line.split(':')[0]
            index = int(line.split(':')[1])
            i2ip[index] = ip
        f.close()

        for index in mon_iset:
            mon_set.add(i2ip[index])

        #--------------------------------------------------------
        # Read update files
        sdt_unix = unix_dt
        edt_unix = unix_dt + self.reaper.granu * 60
        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)

        # XXX Note: 
        # (1) we record the last existence if multiple A exist
        # (2) we record when only W exist
        # (3) we record when inconsistency exists between monitors
        pfx2oriAS = dict()
        for pfx in pfx_set:
            pfx2oriAS[pfx] = -10

        fpathlist = cmlib.select_update_files(updt_files, sdt_unix, edt_unix)
        print fpathlist
        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat', fpath],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    pfx = attr[5]
                    type = attr[2]
                    mon = attr[3]

                    if (mon not in mon_set) or (pfx not in pfx_set):
                        continue

                    unix = int(attr[1])
                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    if type == 'A':
                        as_path = attr[6]

                        # a bug fixed!
                        oriAS = int(as_path.split()[-1])
                        '''
                        # seems not necessary. The origin AS is the same
                        existed = pfx2oriAS[pfx]
                        if existed != -10:
                            assert existed == oriAS
                        else:
                            pfx2oriAS[pfx] = oriAS
                        ''' 
                        pfx2oriAS[pfx] = oriAS
                        
                except Exception, err:
                    if line != '':
                        logging.info(traceback.format_exc())
                        logging.info(line)
            myf.close()

        AS2pfx = dict()
        for pfx in pfx2oriAS:
            ASN = pfx2oriAS[pfx]
            try:
                AS2pfx[ASN] += 1
            except:
                AS2pfx[ASN] = 1

        sorted_list = sorted(AS2pfx.items(), key=operator.itemgetter(1), reverse=True)
        if target_pfx == None:
            f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_pfx_oriAS.txt', 'w')
        else:
            f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_compfx_cluster1_1_oriAS.txt', 'w')
        for item in sorted_list:
            ASN = item[0]
            count = item[1]
            f.write(str(ASN)+':'+str(count)+'\n')
        f.close()

    def top_AS_ASlink(self, unix_dt):
        pfx_set = set()
        mon_iset = set()
        mon_set = set()

        event_fpath = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
        f = open(event_fpath, 'r')
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('Mo'):
                mon_iset = ast.literal_eval(line.split('set')[1])
            else:
                pfx_set.add(line.split(':')[0])
        f.close()

        i2ip = dict()
        f = open(self.reaper.period.get_mon2index_file_path(), 'r')
        for line in f:
            line = line.rstrip('\n')
            ip = line.split(':')[0]
            index = int(line.split(':')[1])
            i2ip[index] = ip
        f.close()

        for index in mon_iset:
            mon_set.add(i2ip[index])

        # get the number of element '1' within the event
        ones_num = 0
        f = open(self.reaper.events_ratios_path(), 'r')
        for line in f:
            if not line.startswith('ONE'):
                continue
            attr = line.rstrip('\n').split('|')
            unix = int(attr[1])
            if unix == unix_dt:
                ones_num = int(attr[4])
        f.close()
        print 'ones_num=',ones_num

        #--------------------------------------------------------
        # Read update files
        sdt_unix = unix_dt
        edt_unix = unix_dt + self.reaper.granu * 60
        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)


        as_count = dict()
        as_link_count = dict()
        # pfx=>xxxxxx, mon=>xxx, pfx+mon=>xxxxxxxxx, to save memory
        pfx2tag = dict()
        mon2tag = dict()

        start = 100000
        for pfx in pfx_set:
            pfx2tag[pfx] = str(start)
            start += 1

        start = 100
        for mon in mon_set:
            mon2tag[mon] = str(start)
            start += 1


        fpathlist = select_update_files(updt_files, sdt_unix, edt_unix)
        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat', fpath],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    pfx = attr[5]
                    type = attr[2]
                    mon = attr[3]

                    if (mon not in mon_set) or (pfx not in pfx_set):
                        continue

                    unix = int(attr[1])
                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    if type == 'A':
                        as_path = attr[6]

                    # now do something
                    the_tag = pfx2tag[pfx] + mon2tag[mon]

                    as_list = as_path.split()
                    mylen = len(as_list)
                    for i in xrange(0, mylen-1):
                        as1 = as_list[i]
                        as2 = as_list[i+1]

                        if as1 == as2:
                            continue

                        if int(as1) > int(as2):
                            as_link = as2+'_'+as1
                        else:
                            as_link = as1+'_'+as2

                        try:
                            as_link_count[as_link].add(the_tag)
                        except:
                            as_link_count[as_link] = set([the_tag])

                        try:
                            as_count[as1].add(the_tag)
                        except:
                            as_count[as1] = set([the_tag])

                    try:
                        as_count[as2].add(the_tag)
                    except:
                        as_count[as2] = set([the_tag])

                        
                except Exception, err:
                    if line != '':
                        logging.info(traceback.format_exc())
                        logging.info(line)
            myf.close()


        tmp_dict = dict()
        for al in as_link_count:
            tmp_dict[al] = float(len(as_link_count[al])) / ones_num

        tmp_list = sorted(tmp_dict.iteritems(),\
                key=operator.itemgetter(1), reverse=True)
        f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_topASlink.txt', 'w')
        for item in tmp_list:
            as_link = item[0]
            count = item[1]
            f.write(str(as_link)+':'+str(count)+'\n')
        f.close()


        tmp_dict = dict()
        for a in as_count:
            tmp_dict[a] = float(len(as_count[a])) / ones_num
        tmp_list = sorted(tmp_dict.iteritems(),\
                key=operator.itemgetter(1), reverse=True)
        f = open(self.reaper.get_output_dir_event()+str(unix_dt)+'_topAS.txt', 'w')
        for item in tmp_list:
            asn = item[0]
            count = item[1]
            f.write(str(asn)+':'+str(count)+'\n')
        f.close()


    def get_as_frequency_in_rib(self, as_set): 
        # get the locations of RIBs
        rib_list = list()
        ribf = open(self.period.rib_info_file, 'r')
        for line in ribf:
            rib_path = line.rstrip('\n').split(':')[1]
            rib_list.append(rib_path)
        ribf.close()

        asn2count = dict()
        for asn in as_set:
            asn2count[asn] = 0

        ignore_monset = set() # avoid duplicate count of a monitor

        total = 0
        for fline in rib_list:
            rib_monset = set() # the monitors in this RIB
            print 'Reading ', fline
            p = subprocess.Popen(['zcat', fline],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attrs = line.split('|')
                    path = attrs[6]
                    mon = attrs[3]
                    if mon in ignore_monset:
                        continue

                    total += 1
                    as_path = set(path.split())
                    common_set = as_path & as_set
                    for asn in common_set:
                        asn2count[asn] += 1

                    rib_monset.add(mon)
                except: # format error
                    pass
            myf.close()
            ignore_monset = ignore_monset | rib_monset

        print 'total=',total

        out_dir = final_output_root + 'event_RIB_analysis/' + 'largestLBE/'
        cmlib.make_dir(out_dir)

        tmp_list = sorted(asn2count.items(), key=operator.itemgetter(1), reverse=True)
        fo = open(out_dir + 'top_as_frenquency.txt', 'w')
        for item in tmp_list:
            fo.write(item[0]+':'+str(item[1])+'\n')
        fo.close()
    

    def get_common_as_in_rib(self, mfile_path, pfile_path):
        pfxset = set()
        f = open(pfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            pfxset.add(line)
        f.close()

        monset = set()
        f = open(mfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            monset.add(line)
        f.close()


        mon2pfx2as_list = dict() 
        for mon in monset:
            mon2pfx2as_list[mon] = dict()
            for pfx in pfxset:
                mon2pfx2as_list[mon][pfx] = list()


        tpath = 0 # the number of total path
        # get the locations of RIBs
        rib_list = list()
        ribf = open(self.period.rib_info_file, 'r')
        for line in ribf:
            rib_path = line.rstrip('\n').split(':')[1]
            rib_list.append(rib_path)
        ribf.close()

        for fline in rib_list:
            rib_monset = set() # the monitors in this RIB

            print 'Reading ', fline
            p = subprocess.Popen(['zcat', fline],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attrs = line.split('|')

                    pfx = attrs[5]
                    if pfx not in pfxset:
                        continue

                    mon = attrs[3]
                    if mon not in monset:
                        continue
                    
                    path = attrs[6]
                    tpath += 1
                    as_list = path.split()
                    mon2pfx2as_list[mon][pfx] = as_list
                    rib_monset.add(mon)
                except: # format error
                    pass
            myf.close()
            monset -= rib_monset

        asn2count = dict()
        for mon in mon2pfx2as_list:
            for pfx in mon2pfx2as_list[mon]:
                for asn in mon2pfx2as_list[mon][pfx]:
                    try:
                        asn2count[asn] += 1
                    except:
                        asn2count[asn] = 1

        print 'total path: ', tpath

        out_dir = final_output_root + 'event_RIB_analysis/' + 'largestLBE/'
        cmlib.make_dir(out_dir)

        tmp_list = sorted(asn2count.items(), key=operator.itemgetter(1), reverse=True)
        fo2 = open(out_dir + 'frequent_as_in_path.txt', 'w')
        for item in tmp_list:
            fo2.write(item[0]+':'+str(item[1])+'\n')
        fo2.close()

    def get_rib_end_states(self, mfile_path, pfile_path, sdt_unix, edt_unix):
        pfxset = set()
        f = open(pfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            pfxset.add(line)
        f.close()

        monset = set()
        f = open(mfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            monset.add(line)
        f.close()



        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)
        fmy.close()
        fpathlist = cmlib.select_update_files(updt_files, sdt_unix, edt_unix)

        mp_last_update = dict() # mon: prefix: last update
        for mon in monset:
            mp_last_update[mon] = dict()

        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat',fpath],stdout=subprocess.PIPE,close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    unix = int(attr[1])

                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    mon = attr[3]
                    if mon not in monset:
                        continue

                    pfx = attr[5]
                    if pfx not in pfxset:
                        continue

                    mp_last_update[mon][pfx] = line

                except:
                    pass
            myf.close()



        mp_rib_route = dict()
        for mon in monset:
            mp_rib_route[mon] = dict()

        rib_list = list()
        ribf = open(self.period.rib_info_file, 'r')
        for line in ribf:
            rib_path = line.rstrip('\n').split(':')[1]
            rib_list.append(rib_path)
        ribf.close()

        for fline in rib_list:
            rib_monset = set() # the monitors in this RIB
            print 'Reading ', fline
            p = subprocess.Popen(['zcat', fline],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attrs = line.split('|')

                    pfx = attrs[5]
                    if pfx not in pfxset:
                        continue

                    mon = attrs[3]
                    if mon not in monset:
                        continue
                    
                    mp_rib_route[mon][pfx] = line
                    rib_monset.add(mon)
                except: # format error
                    pass
            myf.close()
            monset -= rib_monset


        
        mp_change = dict()
        for mon in monset:
            mp_change[mon] = dict()

        for mon in mp_rib_route:
            for pfx in mp_rib_route[mon]:
                rib_route = mp_rib_route[mon][pfx]
                try:
                    # we care about only AADiff and AADup2 and ignore other changes
                    last_update = mp_last_update[mon][pfx]
                    last_attrs = last_update.split()
                    last_type = last_attrs[2]
                    if last_type == 'W':
                        mp_change[mon][pfx] = -1 # withdrawn
                        break

                    last_path = last_attrs[6]

                    rib_attrs = rib_route.split()
                    rib_path = rib_attrs[6]

                    if last_path != rib_path:
                        mp_change[mon][pfx] = 1 # path change
                        break

                    # last_path == rib_path
                    last_comm = last_attrs[11] # communities
                    rib_comm = rib_attrs[11]
                    if last_comm != rib_comm:
                        mp_change[mon][pfx] = 2 # community change
                    else:
                        mp_change[mon][pfx] = 10 # path and community no change

                except:
                    mp_change[mon][pfx] = 0 # no data



        # TODO present the result (per-monitor analysis? count the ratio of each type)



    def get_candidate_as(self, mfile_path, pfile_path, sdt_unix, edt_unix):
        pfxset = set()
        f = open(pfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            pfxset.add(line)
        f.close()

        monset = set()
        f = open(mfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            monset.add(line)
        f.close()

        updt_files = list()
        fmy = open(self.updt_filel, 'r')
        for fline in fmy:
            updatefile = fline.split('|')[0]
            updt_files.append(datadir+updatefile)
        fmy.close()
        fpathlist = cmlib.select_update_files(updt_files, sdt_unix, edt_unix)

        mp_last_A = dict() # mon: prefix: latest full announcement update
        mp_last_type = dict()
        for m in monset:
            mp_last_A[m] = dict()
            mp_last_type[m] = dict()
        # AS number->[a,b,c] where a=common-segment,b=FROM-seg,c=TO-seg 
        asn2path = dict()
        # segment change to count
        sc2count = dict() #'321|234#678|12|23': 19
        # community_change->count
        com_change2count = dict() # [from_set, to_set]: count
        
        count = 0
        community_change = 0
        other_change = 0

        for fpath in fpathlist:
            print 'Reading ', fpath
            p = subprocess.Popen(['zcat',fpath],stdout=subprocess.PIPE,close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    unix = int(attr[1])

                    if unix < sdt_unix or unix > edt_unix:
                        continue

                    mon = attr[3]
                    if mon not in monset:
                        continue

                    pfx = attr[5]
                    if pfx not in pfxset:
                        continue

                    type = attr[2]
                    if type == 'A':
                        as_path = attr[6]
                    else:
                        as_path = None

                    try:
                        last_A = mp_last_A[mon][pfx]
                        last_as_path = last_A.split('|')[6]
                    except:
                        last_A = None
                        last_as_path = None

                    try:
                        last_type = mp_last_type[mon][pfx]
                    except: # this is the first update
                        last_type = None

                    up = self.get_update_pattern(last_type, type, last_as_path, as_path, last_A, line)
                    if up in [3, 42]: # AADiff and WADiff
                        last_list = last_as_path.split()
                        now_list = as_path.split()
                        last_set = set(last_list)
                        now_set = set(now_list)

                        comset = last_set & now_set
                        for asn in comset:
                            last_list.remove(asn)
                            now_list.remove(asn)
                            last_set.remove(asn)
                            now_set.remove(asn)
                            try:
                                asn2path[asn][0] += 1
                            except:
                                asn2path[asn] = [1,0,0]

                        for asn in last_set:
                            try:
                                asn2path[asn][1] += 1
                            except:
                                asn2path[asn] = [0,1,0]
                        for asn in now_set:
                            try:
                                asn2path[asn][2] += 1
                            except:
                                asn2path[asn] = [0,0,1]
    
                        sc_symbol = ''
                        for asn in last_list:
                            sc_symbol += str(asn)
                            sc_symbol += '|'
                        sc_symbol += '#'
                        for asn in now_list:
                            sc_symbol += str(asn)
                            sc_symbol += '|'

                        try:
                            sc2count[sc_symbol] += 1
                        except:
                            sc2count[sc_symbol] = 1
                    
                    elif up in [2, 412]: # AADup2 and WADup2
                        try:
                            last_comm_seg = last_A.split('|')[11]
                            now_comm_seg = attr[11]
                            if last_comm_seg == now_comm_seg:# not community change
                                assert False
                            last_clist = last_comm_seg.split()
                            now_clist = now_comm_seg.split()
                            last_cset = set(last_comm_seg.split())
                            now_cset = set(now_comm_seg.split())

                            com_cset = last_cset & now_cset
                            for c in com_cset:
                                last_clist.remove(c)
                                now_clist.remove(c)

                            combo = str(last_clist) + '#' + str(now_clist)
                            try:
                                com_change2count[combo] += 1
                            except:
                                com_change2count[combo] = 0
                            community_change += 1
                        except:
                            other_change += 1
                            pass # not community change

                    '''
                        count += 1
                        if count < 6:
                            print last_as_path
                            print as_path
                            print asn2path
                            print '========================================'
                    '''

                    if type == 'W':
                        mp_last_type[mon][pfx] = 'W'
                    elif type == 'A':
                        mp_last_type[mon][pfx] = 'A'
                        mp_last_A[mon][pfx] = line
                    else:
                        assert False

                except:
                    pass
            myf.close()

        out_dir = final_output_root + 'change_analysis/' + str(sdt_unix) + '_' +\
                str(edt_unix) + '/'
        cmlib.make_dir(out_dir)

        
        out_path = out_dir + 'asn2path.txt'
        fo = open(out_path, 'w')
        for asn in sorted(asn2path.keys(), key=lambda k: asn2path[k][0], reverse=True):
            fo.write(str(asn)+':'+str(asn2path[asn])+'\n')
        fo.close()

        tmp_list = sorted(sc2count.items(), key=operator.itemgetter(1), reverse=True)
        fo2 = open(out_dir + 'segment_change.txt', 'w')
        for item in tmp_list:
            fo2.write(item[0]+':'+str(item[1])+'\n')
        fo2.close()
        
        tmp_list = sorted(com_change2count.items(), key=operator.itemgetter(1), reverse=True)
        fo3 = open(out_dir + 'community_change.txt', 'w')
        for item in tmp_list:
            fo3.write(str(item[0])+':'+str(item[1])+'\n')
        fo3.close()
        print community_change, other_change

    # pfile_path: None or the prefix file path
    def upattern_mon_pfxset_intime(self, mip, pfile_path, sdt_unix, edt_unix):
        fmy = open(self.updt_filel, 'r')
        sdt_obj = datetime.datetime.utcfromtimestamp(sdt_unix)
        edt_obj = datetime.datetime.utcfromtimestamp(edt_unix)

        target_pfx = set()
        f = open(pfile_path,'r')
        for line in f:
            line = line.rstrip('\n')
            target_pfx.add(line)
        f.close()

        mp_dict = dict() # prefix: successive update type series (0~5)
        mp_last_A = dict() # prefix: latest full announcement update
        mp_last_type = dict()
        for p in target_pfx:
            mp_dict[p] = list()

        for fline in fmy:
            # get date from file name
            updatefile = fline.split('|')[0]

            file_attr = updatefile.split('.')
            fattr_date, fattr_time = file_attr[-5], file_attr[-4]
            fname_dt_obj = datetime.datetime(int(fattr_date[0:4]),\
                    int(fattr_date[4:6]), int(fattr_date[6:8]),\
                    int(fattr_time[0:2]), int(fattr_time[2:4]))
            
            fline = datadir + fline.split('|')[0]

            # get current file's collector name
            attributes = fline.split('/') 
            j = -1
            for a in attributes:
                j += 1
                if a.startswith('data.ris') or a.startswith('archi'):
                    break

            co = fline.split('/')[j + 1]
            if co == 'bgpdata':  # route-views2, the special case
                co = ''

            # Deal with several special time zone problems according to collector name
            if co == 'route-views.eqix' and fname_dt_obj <= dt_anchor2: # PST time
                fname_dt_obj = fname_dt_obj + datetime.timedelta(hours=7) # XXX (not 8)
            elif not co.startswith('rrc') and fname_dt_obj <= dt_anchor1:
                fname_dt_obj = fname_dt_obj + datetime.timedelta(hours=8) # XXX here is 8

            if co.startswith('rrc'):
                shift = -10
            else:
                shift = -30

            # Check whether the file is within our intended time range
            if not sdt_obj+datetime.timedelta(minutes=shift)<=fname_dt_obj<=edt_obj:
                continue

            # read the update file
            print 'Reading ', fline
            p = subprocess.Popen(['zcat', fline],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    line = line.rstrip('\n')
                    attr = line.split('|')
                    mon = attr[3]
                    if mon != mip:
                        continue
                        
                    pfx = attr[5]
                    if pfx not in target_pfx:
                        continue

                    type = attr[2]
                    if type == 'A':
                        as_path = attr[6]
                    else:
                        as_path = None

                    try:
                        last_A = mp_last_A[pfx]
                        last_as_path = last_A.split('|')[6]
                    except:
                        last_A = None
                        last_as_path = None

                    try:
                        last_type = mp_last_type[pfx]
                    except: # this is the first update
                        last_type = None

                    up = self.get_update_pattern(last_type, type, last_as_path, as_path, last_A, line)
                    if up != -1: # not the first update
                        mp_dict[pfx].append(up)

                    # for debugging
                    '''
                    if count < 30 and up_num == 0:
                        print '================================================'
                        print up_num, num2upattern[up_num] 
                        print 'last_type:', last_type
                        print 'type:', type
                        print 'last_as_path:', last_as_path
                        print 'as_path:', as_path
                        print 'last_A:', last_A
                        print 'line:', line
                        count += 1
                    '''

                    if type == 'W':
                        mp_last_type[pfx] = 'W'
                    elif type == 'A':
                        mp_last_type[pfx] = 'A'
                        mp_last_A[pfx] = line
                    else:
                        assert False
                
                except Exception, err:
                    if line != '':
                        logging.info(traceback.format_exc())
                        logging.info(line)
            myf.close()

        outdir = final_output_root + 'upattern_TS/' + str(sdt_unix) + '_' + str(edt_unix) + '/' +\
                pfile_path.split('/')[-1] + '/'
        cmlib.make_dir(outdir)

        ff = open(outdir+mip+'.txt','w')
        for pfx in mp_dict:
            ff.write(pfx+':'+str(mp_dict[pfx])+'\n')
        ff.close()

        f.close()

    def event_analyze_pfx(self, unix_dt):

        pfx2as = self.get_pfx2as()
        as2count = dict()
        odd_pfx = set()

        event_detail_fname = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
        f = open(event_detail_fname, 'r')
        for line in f:
            line = line.rstrip('\n')
            if '#' in line: # monitor line
                pass
            else:
                pfx = line.split(':')[0]
                try:
                    asn = pfx2as[pfx]
                except:
                    asn = -1
                    odd_pfx.add(pfx)
                try:
                    as2count[asn] += 1
                except:
                    as2count[asn] = 1
        f.close()

        tmp_list = sorted(as2count.iteritems(),\
                key=operator.itemgetter(1), reverse=True)
        f2 = open('as_result.txt','w')
        for item in tmp_list:
            asn = item[0]
            count = item[1]
            f2.write(str(asn)+':'+str(count)+'\n')
        f2.close()

        f = open('odd_pfx.txt', 'w')
        for pfx in odd_pfx:
            f.write(pfx+'\n')
        f.close()
        

    def event_as_link_rank(self, unix_dt):
        as_link_count = dict()
        as_count = dict()

        event_sdt = datetime.datetime.utcfromtimestamp(unix_dt)
        event_unix_sdt = unix_dt
        event_edt = event_sdt + datetime.timedelta(minutes=self.granu)
        event_unix_edt = unix_dt + self.granu * 60

        # get event prefix and monitor set
        pfx_set = set()
        mon_index_set = set()
        event_detail_fname = self.reaper.get_output_dir_event() + str(unix_dt) + '.txt'
        f = open(event_detail_fname, 'r')
        for line in f:
            line = line.rstrip('\n')
            if '#' in line: # monitor line
                mondict = line.split('#')[1]
                mondict = ast.literal_eval(mondict)
                mon_index_set = set(mondict.keys())
            else:
                pfx = line.split(':')[0]
                pfx_set.add(pfx)
        f.close()

        pfx_count = len(pfx_set)
        mon_count = len(mon_index_set)
        event_size = pfx_count * mon_count

        #leak_pfx_set = self.bgp_leak_pfx()
        #common_set = pfx_set & leak_pfx_set
        #common_count = len(common_set)
        #print 'pfx set in event:',pfx_count
        #print 'pfx set in leak',len(leak_pfx_set)
        #print 'common pfx set in leak:',common_count
            
        index2mon = dict()
        mon2index_file = self.period.get_mon2index_file_path()
        f = open(mon2index_file, 'r')
        for line in f:
            line = line.rstrip('\n')
            ip = line.split(':')[0]
            index = int(line.split(':')[1])
            index2mon[index] = ip
        f.close()

        mon_set = set()
        for i in mon_index_set:
            mon_set.add(index2mon[i])

         
        # pfx=>xxxxxx, mon=>xxx, pfx+mon=>xxxxxxxxx, to save memory
        pfx2tag = dict()
        mon2tag = dict()

        start = 100000
        for pfx in pfx_set:
            pfx2tag[pfx] = str(start)
            start += 1

        start = 100
        for mon in mon_set:
            mon2tag[mon] = str(start)
            start += 1


        # obtain the target update file list
        f = open(self.updt_filel, 'r')
        for fline in f:
            # get date from file name
            updatefile = fline.split('|')[0]

            file_attr = updatefile.split('.')
            fattr_date, fattr_time = file_attr[-5], file_attr[-4]
            fname_dt_obj = datetime.datetime(int(fattr_date[0:4]),\
                    int(fattr_date[4:6]), int(fattr_date[6:8]),\
                    int(fattr_time[0:2]), int(fattr_time[2:4]))
            

            fline = datadir + fline.split('|')[0]


            # get current file's collector name
            attributes = fline.split('/') 
            j = -1
            for a in attributes:
                j += 1
                if a.startswith('data.ris') or a.startswith('archi'):
                    break

            co = fline.split('/')[j + 1]
            if co == 'bgpdata':  # route-views2, the special case
                co = ''


            # Deal with several special time zone problems
            if co == 'route-views.eqix' and fname_dt_obj <= dt_anchor2: # PST time
                fname_dt_obj = fname_dt_obj + datetime.timedelta(hours=7) # XXX (not 8)
            elif not co.startswith('rrc') and fname_dt_obj <= dt_anchor1:
                fname_dt_obj = fname_dt_obj + datetime.timedelta(hours=8) # XXX here is 8

            if co.startswith('rrc'):
                shift = -10
            else:
                shift = -30


            # Check whether the file is a possible target
            if not event_sdt+datetime.timedelta(minutes=shift)<=fname_dt_obj<=event_edt:
                continue


            # read the update file
            print 'Reading ', fline
            p = subprocess.Popen(['zcat', fline],stdout=subprocess.PIPE, close_fds=True)
            myf = StringIO(p.communicate()[0])
            assert p.returncode == 0
            for line in myf:
                try:
                    attr = line.rstrip('\n').split('|')
                    pfx = attr[5]
                    mon = attr[3]

                    if not event_unix_sdt<=int(attr[1])<=event_unix_edt:
                        continue

                    if (pfx not in pfx_set) or (mon not in mon_set):
                        continue

                    # now do something
                    the_tag = pfx2tag[pfx] + mon2tag[mon]

                    as_list = attr[6].split()
                    mylen = len(as_list)
                    for i in xrange(0, mylen-1):
                        as1 = as_list[i]
                        as2 = as_list[i+1]

                        if as1 == as2:
                            continue

                        if int(as1) > int(as2):
                            as_link = as2+'_'+as1
                        else:
                            as_link = as1+'_'+as2

                        try:
                            as_link_count[as_link].add(the_tag)
                        except:
                            as_link_count[as_link] = set()
                            as_link_count[as_link].add(the_tag)

                        try:
                            as_count[as1].add(the_tag)
                        except:
                            as_count[as1] = set()
                            as_count[as1].add(the_tag)

                    try:
                        as_count[as2].add(the_tag)
                    except:
                        as_count[as2] = set()
                        as_count[as2].add(the_tag)


                except Exception, err:
                    if line != '':
                        logging.info(traceback.format_exc())
                        logging.info(line)

            myf.close()

        f.close()

        tmp_dict = dict()
        for al in as_link_count:
            tmp_dict[al] = float(len(as_link_count[al])) / event_size

        tmp_list = sorted(tmp_dict.iteritems(),\
                key=operator.itemgetter(1), reverse=True)
        f = open(self.reaper.get_output_dir_event()+'as_link_rank_'+str(unix_dt)+'.txt', 'w')
        for item in tmp_list:
            as_link = item[0]
            count = item[1]
            f.write(str(as_link)+':'+str(count)+'\n')
        f.close()


        tmp_dict = dict()
        for a in as_count:
            tmp_dict[a] = float(len(as_count[a])) / event_size
        tmp_list = sorted(tmp_dict.iteritems(),\
                key=operator.itemgetter(1), reverse=True)
        f = open(self.reaper.get_output_dir_event()+'as_rank_'+str(unix_dt)+'.txt', 'w')
        for item in tmp_list:
            asn = item[0]
            count = item[1]
            f.write(str(asn)+':'+str(count)+'\n')
        f.close()

