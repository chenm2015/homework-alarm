import downloader_class
import radix
from  env import *

import urllib
import subprocess
import hashlib
import calendar
import traceback
import cmlib
import patricia
import os
import datetime
import logging
import time as time_lib
logging.basicConfig(filename='main.log', filemode='w', level=logging.DEBUG, format='%(asctime)s %(message)s')

# Work as input to update analysis functions
class Period():

    def __init__(self, index):
        self.index = index
        self.sdate = daterange[index][0] 
        self.edate = daterange[index][1] 

        self.sdatetime_obj = datetime.datetime.strptime(self.sdate, '%Y%m%d')
        self.edatetime_obj = datetime.datetime.strptime(self.edate, '%Y%m%d') + datetime.timedelta(days=1)
        
        # location to store supporting files
        self.spt_dir = spt_dir + self.sdate + '_' + self.edate + '/'
        cmlib.make_dir(self.spt_dir)

        # Store the rib information of every collector (Note: do not change this!)
        self.rib_info_file = rib_info_dir + self.sdate + '_' + self.edate + '.txt'
    
        self.co_mo = dict() # collector: monitor list (does not store empty list)
        self.mo_asn = dict()
        self.mo_cc = dict()
        self.mo_tier = dict()

        self.as2nation = dict()
        self.as2name = dict()

        # Note: Occassionally run to get the latest data. (Now up to 20141225)
        #self.get_fib_size_file()
        #self.get_AS_num_file()

        self.dt_anchor1 = datetime.datetime(2003,2,3,19,0) # up to now, never used data prior
        self.dt_anchor2 = datetime.datetime(2006,2,1,21,0)

    def get_mon2index_file_path(self):
        return rib_info_dir + self.sdate + '_' + self.edate + '_mo2index.txt'
        # Note that we map id to ip in alarm class instead of here

    def get_middle_dir(self):
        return datadir+'middle_output/'+self.sdate+'_'+self.edate+'/'

    def get_final_dir(self):
        return datadir+'final_output/'+self.sdate+'_'+self.edate+'/'

    def get_blank_dir(self):
        return blank_indo_dir+self.sdate+'_'+self.edate+'/'

    def get_AS_num_file(self):
        url = 'http://bgp.potaroo.net/as2.0/'
        cmlib.force_download_file(url, pub_spt_dir, 'bgp-as-count.txt')
        return 0

    def get_AS_num(self):
        objdt = datetime.datetime.strptime(self.sdate, '%Y%m%d') 
        intdt = calendar.timegm(objdt.timetuple())

        dtlist = []
        datalist = []
        ASnum_f = pub_spt_dir + 'bgp-as-count.txt'
        f = open(ASnum_f, 'r')
        for line in f:
            dt = line.split()[0]
            count = line.split()[1]
            dtlist.append(int(dt))
            datalist.append(int(count))
        f.close()

        least = 9999999999
        loc = 0
        for i in xrange(0, len(dtlist)):
            if abs(dtlist[i]-intdt) < least:
                least = abs(dtlist[i]-intdt)
                loc = i

        goal = 0
        for j in xrange(loc, len(dtlist)-1):
            prev = datalist[j-1]
            goal = datalist[j]
            nex = datalist[j+1]
            if abs(goal-prev) > prev/7 or abs(goal-nex) > nex/7: # outlier
                continue
            else:
                break

        return goal

    def get_fib_size_file(self):
        url = 'http://bgp.potaroo.net/as2.0/'
        cmlib.force_download_file(url, pub_spt_dir, 'bgp-active.txt')
        return 0

    def get_fib_size(self):
        objdt = datetime.datetime.strptime(self.sdate, '%Y%m%d') 
        intdt = calendar.timegm(objdt.timetuple())

        dtlist = []
        pclist = []
        fibsize_f = pub_spt_dir + 'bgp-active.txt'
        f = open(fibsize_f, 'r')
        for line in f:
            dt = line.split()[0]
            pcount = line.split()[1]
            dtlist.append(int(dt))
            pclist.append(int(pcount))
        f.close()

        least = 9999999999
        loc = 0
        for i in xrange(0, len(dtlist)):
            if abs(dtlist[i]-intdt) < least:
                least = abs(dtlist[i]-intdt)
                loc = i

        goal = 0
        for j in xrange(loc, len(dtlist)-1):
            prev = pclist[j-1]
            goal = pclist[j]
            nex = pclist[j+1]
            if abs(goal-prev) > prev/7 or abs(goal-nex) > nex/7: # outlier
                continue
            else:
                break

        return goal
        

    # Run it once will be enough. (Note: we can only get the *latest* AS to nation mapping)
    def get_as2nn_file(self):
        cmlib.force_download_file('http://bgp.potaroo.net/cidr/', pub_spt_dir, 'autnums.html')

    def get_as2nn_dict(self):
        print 'Constructing AS to nation dict...'
        as2nation = {}
        as2name = {}

        f = open(pub_spt_dir+'autnums.html')
        for line in f:
            if not line.startswith('<a h'):
                continue
            line = line.split('</a> ')
            content = line[1].rsplit(',', 1)
            name = content[0]
            nation = content[1].rstrip('\n')
            asn = int(line[0].split('>AS')[1])
            if asn in tier1_asn:
                as2nation[asn] = 'global'
            else:
                as2nation[asn] = nation
            as2name[asn] = name
        f.close()

        return [as2nation, as2name]

    def get_as2namenation(self):
        # Note: Get this only when necessary
        #self.get_as2nn_file()
        as2nn = self.get_as2nn_dict()
        self.as2nation = as2nn[0]
        self.as2name = as2nn[1]

    def get_as2cc_file(self): # AS to customer cone
        sptfiles = os.listdir(self.spt_dir)
        for line in sptfiles:
            if 'ppdc' in line:
                return 0 # already have a file

        target_line = None
        yearmonth = self.sdate[:6] # YYYYMM
        print 'Downloading AS to customer cone file ...'
        theurl = 'http://data.caida.org/datasets/2013-asrank-data-supplement/data/'
        webraw = cmlib.get_weblist(theurl)
        for line in webraw.split('\n'):
            if yearmonth in line and 'ppdc' in line:
                target_line = line
                break

        assert target_line != None

        fname = target_line.split()[0]
        cmlib.force_download_file(theurl, self.spt_dir, fname)
        if int(yearmonth) <= 201311:
            # unpack .gz (only before 201311 (include))
            subprocess.call('gunzip '+self.spt_dir+fname, shell=True)
        else:
            # unpack .bz2 (only after 201406 (include))
            subprocess.call('bunzip2 -d '+self.spt_dir+fname, shell=True)

        return 0

    def get_as2cc_dict(self): # AS to customer cone
        print 'Calculating AS to customer cone dict...'

        as2cc_file = None
        sptfiles = os.listdir(self.spt_dir)
        for line in sptfiles:
            if 'ppdc' in line:
                as2cc_file = line
                break

        assert as2cc_file != None

        as2cc = {}
        f = open(self.spt_dir+as2cc_file)
        for line in f:
            if line == '' or line == '\n' or line.startswith('#'):
                continue
            line = line.rstrip('\n')
            attr = line.split()
            as2cc[int(attr[0])] = len(attr) - 1 
        f.close()

        return as2cc

    def get_mo2cc(self):
        self.get_as2cc_file()
        as2cc = self.get_as2cc_dict()
        for mo in self.mo_asn:
            asn = self.mo_asn[mo]
            try:
                cc = as2cc[asn]
            except:
                cc = -1
            self.mo_cc[mo] = cc

    def get_mo2tier(self):
        assert self.mo_cc != {}
        for m in self.mo_asn:
            if self.mo_asn[m] in tier1_asn:
                self.mo_tier[m] = 1

        for m in self.mo_cc:
            try:
                if self.mo_tier[m] == 1:
                    continue
            except:
                pass
            cc = self.mo_cc[m]
            if cc < 0:
                self.mo_tier[m] = -1 #unknown
            elif cc <= 4:
                self.mo_tier[m] = 999 # stub
            elif cc <= 50:
                self.mo_tier[m] = 3 # small ISP
            else:
                self.mo_tier[m] = 2 # large ISP

    def get_global_monitors(self):
        norm_size = self.get_fib_size()

        f = open(self.rib_info_file, 'r')
        totalc = 0
        totalok = 0
        nationc = dict() # nation: count
        for line in f:
            co = line.split(':')[0]
            logging.info('collector:%s', co)
            ribfile = line.split(':')[1]
            peerfile = cmlib.peer_path_by_rib_path(ribfile).rstrip('\n')

            count = 0
            ok = 0
            fp = open(peerfile, 'r')
            for line in fp:
                mo_ip = line.split('@')[0]
                if '.' not in mo_ip: # ignore ipv6
                    continue
                fibsize = int(line.split('@')[1].split('|')[0])
                asn = int(line.split('@')[1].split('|')[1])
                self.mo_asn[mo_ip] = asn
                if fibsize > 0.9 * norm_size:
                    try: 
                        test = self.co_mo[co]
                    except:
                        self.co_mo[co] = list()
                    if mo_ip not in self.co_mo[co]:
                        self.co_mo[co].append(mo_ip)
                    ok += 1
                    asn = int(line.split('@')[1].split('|')[1])
                    try:
                        nation = self.as2nation[asn]
                    except:
                        nation = 'unknown'
                    try:
                        nationc[nation] += 1
                    except:
                        nationc[nation] = 1
                count += 1
            fp.close()
            logging.info('This collector Feasible monitor %d/%d', ok, count)
            totalc += count
            totalok += ok
        f.close()
        logging.info('Feasible monitors:%d/%d', totalok, totalc)
        logging.info('%s', str(nationc))
        
        return 0

    # remove the ip whose co has smaller hash value
    def rm_dup_mo(self):
        print 'Removing duplicate monitors...'
        mo_count = dict()
        for co in self.co_mo.keys():
            for mo in self.co_mo[co]:
                try:
                    mo_count[mo] += 1
                except:
                    mo_count[mo] = 1

        for mo in mo_count.keys():
            if mo_count[mo] == 1:
                continue
            co2 = list()
            for co in self.co_mo.keys():
                if mo in self.co_mo[co]:
                    co2.append(co)

            assert len(co2) == 2
            co_chosen = ''
            max_hash = -1
            for co in co2:
                ha = int(hashlib.md5(co).hexdigest(), 16)
                if ha > max_hash:
                    max_hash = ha
                    co_chosen = co

            co2.remove(co_chosen)
            co_rm = co2[0]

            self.co_mo[co_rm].remove(mo)


    # choose only one monitor from each AS
    # Note: the choice should be consistent (e.g., choose the one with the largest prefix integer)
    def mo_filter_same_as(self):
        print 'Selecting only one monitor in each AS...'
        mo_co = dict()
        for co in self.co_mo.keys():
            for mo in self.co_mo[co]:
                mo_co[mo] = co

        mo_list = mo_co.keys()

        asn_mo = dict() # ASN: monitor list

        f = open(self.rib_info_file, 'r')
        for line in f:
            co = line.split(':')[0]
            ribfile = line.split(':')[1]
            peerfile = cmlib.peer_path_by_rib_path(ribfile).rstrip('\n')
            fp = open(peerfile, 'r')
            for line in fp:
                if len(line.split(':')) > 2:
                    continue
                mo_ip = line.split('@')[0]
                asn = int(line.split('@')[1].split('|')[1])
                if mo_ip in mo_list:
                    try:
                        test = asn_mo[asn]
                        if mo_ip not in asn_mo[asn]:
                            asn_mo[asn].append(mo_ip)
                    except:
                        asn_mo[asn] = list()
                        asn_mo[asn].append(mo_ip)
                else:
                    pass
            fp.close()
        f.close()

        remove_mo = list() # monitors to remove

        for asn in asn_mo.keys(): 
            tmp_list = asn_mo[asn]
            if len(tmp_list) <= 1:
                continue

            max = 0
            selected = ''
            for mo in tmp_list:
                if cmlib.ip_to_integer(mo) > max:
                    selected = mo
                    max = cmlib.ip_to_integer(mo)
            tmp_list.remove(selected)
            remove_mo.extend(tmp_list)

        for rmo in remove_mo:
            try:
                co = mo_co[rmo]
            except: # no such monitor in self.co_mo
                continue
            
            try:
                self.co_mo[co].remove(rmo)
            except:
                pass

            if self.co_mo[co] == []: # empty list
                del self.co_mo[co]

        count = 0
        for co in self.co_mo.keys():
            count += len(self.co_mo[co])
        logging.info('Filtered out same-AS-monitors, # now:%d', count)

    def get_mo_number(self):
        count = 0
        for co in self.co_mo:
            for mo in self.co_mo[co]:
                count += 1
        return count

    def used_monitors(self):
        monset = set()
        for co in self.co_mo:
            for mo in self.co_mo[co]:
                monset.add(mo)
        return monset

    def get_filelist(self):
        print 'Getting combined file list'
        listdir = ''

        #co_list = self.co_mo.keys()
        co_list = list()
        for co in all_collectors.keys():
            co_sdate = all_collectors[co]
            if co not in co_blank.keys():
                if int(co_sdate) <= int(self.sdate):
                    co_list.append(co)
            else:
                bstart = co_blank[co][0]
                bend = co_blank[co][1]
                if int(co_sdate)<=int(self.sdate) and not (int(bstart)<=int(self.sdate)<=\
                        int(bend) or int(bstart)<=int(self.edate)<=int(bend)):
                    co_list.append(co)
        listfiles = list()

        for co in co_list:
            dl = downloader_class.Downloader(self.sdate, self.edate, co)
            listfiles.append(dl.get_listfile())
            listdir = dl.get_listfile_dir()

        eqixshift = None
        rv_shift = None

        fnames = dict()
        for lf in listfiles:
            f = open(lf, 'r')
            for name in f:
                name = name.rstrip('\n')
                file_attr = name.split('.')
                file_dt = file_attr[-6] + file_attr[-5]
                dt_obj = datetime.datetime.strptime(file_dt, '%Y%m%d%H%M')

                co = name.split('/')[1]
                if co == 'bgpdata':
                    co = ''

                # FIXME these code create holes between months when dealing with whole year!!
                # FIXME fix this hole by update in the previous and next month...
                # XXX Do this when processing 2005 whole year data
                if co == 'route-views.eqix' and dt_obj <= self.dt_anchor2: # PST time
                    eqixshift = 7
                    dt_obj = dt_obj + datetime.timedelta(hours=eqixshift) # XXX not 8
                elif not co.startswith('rrc') and dt_obj <= self.dt_anchor1: 
                    rv_shift = 8
                    dt_obj = dt_obj + datetime.timedelta(hours=8) # XXX 8, not 7

                fnames[name] = dt_obj
            f.close()
        newlist = sorted(fnames, key=fnames.get)
        
        # XXX note: our logic is correct iff we only deal with eqix and rv2, if other
        # collectors are used, re-consider the logic
        if eqixshift is not None:
            to_remove = []
            #------------------------------------------------------------------
            # cut off head and end of the list because they can eat up memo
            # However, this makes 'ignoring first hour' fail when creating middle
            first_fn = newlist[0]
            last_fn = newlist[-1]
            # 0 line could not be eqix # start: align with eqix
            # FIXME fill the gap if possible!
            start_dt = fnames[first_fn] + datetime.timedelta(hours=eqixshift)
            # -1 line must be eqix # end: cut off eqix
            # FIXME be more accurate when deciding this! (do not omit any file carelessly)
            end_dt = fnames[last_fn] + datetime.timedelta(hours=-eqixshift)

            for fn in newlist: # sorted list
                co = fn.split('/')[1]
                if co == 'bgpdata':
                    co = ''

                if not co.endswith('eqix') and fnames[fn] < start_dt:
                    to_remove.append(fn)
                elif co.endswith('eqix') and fnames[fn] > end_dt:
                    to_remove.append(fn)

            for fn in to_remove:
                newlist.remove(fn)


        if rv_shift is not None: # TODO test needed
            to_remove = []
            first_fn = newlist[0]
            last_fn = newlist[-1]
            # XXX fill the gap if possible!!!
            start_dt = fnames[first_fn] + datetime.timedelta(hours=rv_shift)
            end_dt = fnames[last_fn] + datetime.timedelta(hours=-rv_shift)

            for fn in newlist: # sorted list
                co = fn.split('/')[1]
                if co == 'bgpdata':
                    co = ''

                if co.startswith('rrc') and fnames[fn] < start_dt:
                    to_remove.append(fn)
                elif not co.startswith('rrc') and fnames[fn] > end_dt:
                    to_remove.append(fn)
            for fn in to_remove:
                newlist.remove(fn)

        filelist = listdir + 'combined_list.txt'
        f = open(filelist, 'w')
        for name in newlist:
            f.write(name+'\n')
        f.close()

        return filelist

    def get_prefix(self):
        return 0


    def get_pfx2as_file(self):
        location = self.spt_dir
        cmlib.make_dir(location)

        tmp = os.listdir(self.spt_dir)
        for line in tmp:
            if 'pfx2as' in line:
                return 0 # we already have a prefix2as file

        print 'Downloading prefix to AS file ...'
        year, month = self.sdate[:4], self.sdate[4:6] # YYYY, MM
        webloc = 'http://data.caida.org/datasets/routing/routeviews-prefix2as' +\
                '/' + year + '/' + month + '/'

        webraw = cmlib.get_weblist(webloc)
        target_line = ''
        for line in webraw.split('\n'):
            if self.sdate in line:
                target_line = line
                break

        if target_line == '':
            print 'Downloading prefix to AS file fails: no such date!'
            return 0

        fname = target_line.split()[0]
        urllib.urlretrieve(webloc+fname, location+fname)
        subprocess.call('gunzip -c '+location+fname+' > '+\
                location+fname.replace('.gz', ''), shell=True)
        os.remove(location+fname)

        return 0

    def pfx2as_LPM(self, pfx_set): # longest prefix matching
        self.get_pfx2as_file()

        #pfx_set_9121 = set()

        print 'Calculating prefix to AS number trie...'
        pfx_radix = radix.Radix()

        pfx2as_file = ''
        tmp = os.listdir(self.spt_dir)
        for line in tmp:
            if 'pfx2as' in line:
                pfx2as_file = line
                break

        f = open(self.spt_dir+pfx2as_file)
        for line in f:
            line = line.rstrip('\n')
            attr = line.split()
            if '_' in attr[2] or ',' in attr[2]:
                continue
            pfx = attr[0]+'/'+attr[1]
            '''
            try:
                pfx2as[pfx] = int(attr[2]) # pfx: origin AS
            except: # When will this happen?
                pfx2as[pfx] = -1
            '''
            rnode = pfx_radix.add(pfx)
            try:
                rnode.data[0] = int(attr[2]) # pfx->AS
            except:
                rnode.data[0] = -1
        f.close()


        print 'Getting origin ASes of target prefixes'
        non_exact_p2a = dict()
        exact_p2a = dict() # exact prefix matching
        for pfx in pfx_set:
            rnode = pfx_radix.search_best(pfx) # longest prefix matching
            try:
                asn = rnode.data[0]
                #if asn == 9121:
                #   pfx_set_9121.add(rnode.prefix) 
                if pfx == rnode.prefix:
                    exact_p2a[pfx] = asn
                else:
                    non_exact_p2a[pfx] = asn
            except:
                asn = -1

        non_exact_a2p = dict() # only for easier output presentation
        for pfx in non_exact_p2a:
            asn = non_exact_p2a[pfx]
            try:
                non_exact_a2p[asn].add(pfx)
            except:
                non_exact_a2p[asn] = set([pfx])

        exact_a2p = dict() # only for easier output presentation
        for pfx in exact_p2a:
            asn = exact_p2a[pfx]
            try:
                exact_a2p[asn].add(pfx)
            except:
                exact_a2p[asn] = set([pfx])

        # Output everything
        f = open(datadir+'final_output/cluster3_compfx2AS_RIB'+str(self.index)+'.txt', 'w')
        for pfx in non_exact_p2a:
            f.write('N|'+pfx+':'+str(non_exact_p2a[pfx])+'\n')
        for pfx in exact_p2a:
            f.write('E|'+pfx+':'+str(exact_p2a[pfx])+'\n')

        for asn in non_exact_a2p:
            f.write('N#|'+str(asn)+':'+str(len(non_exact_a2p[asn]))+'\n')
        for asn in exact_a2p:
            f.write('E#|'+str(asn)+':'+str(len(exact_a2p[asn]))+'\n')

        #f.write('$9121 involved prefix quantity:'+str(len(pfx_set_9121)))
        f.close()


    def get_pfx2as(self):
        self.get_pfx2as_file()

        print 'Calculating prefix to AS number trie...'
        pfx2as = dict()

        if int(self.sdate) >= 20050509:
            self.get_pfx2as_file()

            pfx2as_file = ''
            tmp = os.listdir(self.spt_dir)
            for line in tmp:
                if 'pfx2as' in line:
                    pfx2as_file = line
                    break

            f = open(self.spt_dir+pfx2as_file)
            for line in f:
                line = line.rstrip('\n')
                attr = line.split()
                if '_' in attr[2] or ',' in attr[2]:
                    continue
                pfx = attr[0]+'/'+attr[1]
                try:
                    pfx2as[pfx] = int(attr[2]) # pfx: origin AS
                except: # When will this happen?
                    pfx2as[pfx] = -1

            f.close()
        else:
            # Extract info from RIB of the monitor route-views2 and XXX
            mydate = self.sdate[0:4] + '.' + self.sdate[4:6]
            rib_location = datadir+'archive.routeviews.org/bgpdata/'+mydate+'/RIBS/'
            dir_list = os.listdir(datadir+'archive.routeviews.org/bgpdata/'+mydate+'/RIBS/')


            for f in dir_list:
                if not f.startswith('.'):
                    rib_location = rib_location + f # if RIB is of the same month. That's OK.
                    break
            
            if rib_location.endswith('txt.gz'):
                subprocess.call('gunzip '+rib_location, shell=True)  # unpack                        
                rib_location = rib_location.replace('.txt.gz', '.txt')
            elif not rib_location.endswith('txt'):  # .bz2/.gz file exists
                cmlib.parse_mrt(rib_location, rib_location+'.txt')
                os.remove(rib_location)  # then remove .bz2/.gz
                rib_location = rib_location + '.txt'
            # now rib file definitely ends with .txt, let's rock and roll
            with open(rib_location, 'r') as f:
                for line in f:
                    try:
                        tmp = line.split('|')[5]
                        pfx = tmp
                        ASlist = line.split('|')[6]
                        originAS = ASlist.split()[-1]
                        try:
                            pfx2as[pfx] = int(originAS)
                        except:
                            pfx2as[pfx] = -1
                    except:
                        pass

            f.close()
            # compress RIB into .gz
            if not os.path.exists(rib_location+'.gz'):
                cmlib.pack_gz(rib_location)

        return pfx2as
