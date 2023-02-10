import re
#import pdb
import config
import pytest
import unittest
import logging
import subprocess
import os
import json
import ib_utils.ib_NIOS as ib_NIOS
import commands
import json, ast
import requests
from time import sleep as sleep
import pexpect
import paramiko
import time
import sys
from paramiko import client
from ib_utils.start_stop_logs import log_action as log
from ib_utils.file_content_validation import log_validation as logv

def start_subscriber_collection_services_for_added_site(member):
    for mem in member:
        get_ref=ib_NIOS.wapi_request('GET', object_type='member:parentalcontrol?name='+mem)
        get_ref=json.loads(get_ref)
        ref=get_ref[0]["_ref"]
        print ref
        logging.info(ref)
        data={"enable_service":True}
        reference=ib_NIOS.wapi_request('PUT', object_type=ref,fields=json.dumps(data))
        logging.info(reference)
        print reference
    grid =  ib_NIOS.wapi_request('GET', object_type="grid")
    ref = json.loads(grid)[0]['_ref']
    publish={"member_order":"SIMULTANEOUSLY"}
    request_publish = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=publish_changes",fields=json.dumps(publish))
    time.sleep(1)
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus")
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices")
    time.sleep(20)
    for mem in member:
        get_ref=ib_NIOS.wapi_request('GET', object_type='member:parentalcontrol?name='+mem)
        get_ref=json.loads(get_ref)
        if get_ref[0]["enable_service"]==True:
            return True
            print("subscriber service is started in "+mem)
        else:
            return None
            print("Not able to start subscriber service "+mem)
    time.sleep(40)

def mem_ref_string_pc(hostname):
    response = ib_NIOS.wapi_request('GET', object_type="member:parentalcontrol")
    logging.info(response)
    #print(response)
    if type(response)!=tuple:
        ref1 = json.loads(response)
        for key in ref1:
            if key.get('name') == hostname:
                mem_ref = key.get('_ref')
                break
    else:
        print("Failed to get member ref string")
        mem_ref = "NIL"

    return mem_ref

def change_default_route():
    ref=ib_NIOS.wapi_request('GET', object_type="grid")
    print("#############",ref)
    ref=json.loads(ref)[0]['_ref']
    #data={"enable_gui_api_for_lan_vip":"true","dns_resolver_setting": {"resolvers": ["10.0.2.35"]}}
    data={"dns_resolver_setting": {"resolvers": [config.resolver_ip]}}
    ref1=ib_NIOS.wapi_request('PUT', object_type=ref,fields=json.dumps(data))
    child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
    child.logfile=sys.stdout
    child.expect('-bash-5.0#')
    child.sendline('ip route del default via 10.35.0.1 dev eth1 table main')
    child.expect('-bash-5.0#')
    child.sendline('ip route add default via 10.36.0.1 dev eth0 table main')
    child.sendline('exit')
    child.expect(pexpect.EOF)
    time.sleep(20)

def enable_mgmt_port_for_dns():
    ref=ib_NIOS.wapi_request('GET', object_type="member:dns")
    ref=json.loads(ref)[0]['_ref']
    data={"use_mgmt_port":True}
    ref1=ib_NIOS.wapi_request('PUT', object_type=ref,fields=json.dumps(data))
    logging.info (ref1)
    time.sleep(120)

def enable_GUI_and_API_access_through_LAN_and_MGMT():
    ref=ib_NIOS.wapi_request('GET', object_type="grid",grid_vip=config.Master1_MGMT_IP)
    logging.info (ref)
    ref=json.loads(ref)[0]['_ref']
    logging.info(ref)
    data={"enable_gui_api_for_lan_vip":True}
    ref1=ib_NIOS.wapi_request('PUT', object_type=ref,fields=json.dumps(data),grid_vip=config.Master1_MGMT_IP)
    logging.info (ref1)
    time.sleep(120)


def stop_subscriber_collection_services_for_added_site(member):#config.grid_fqdn
    get_ref=ib_NIOS.wapi_request('GET', object_type='member:parentalcontrol?name='+member)
    get_ref=json.loads(get_ref)
    ref=get_ref[0]["_ref"]
    logging.info(ref)
    data={"enable_service":False}
    reference=ib_NIOS.wapi_request('PUT', object_type=ref,fields=json.dumps(data))
    logging.info(reference)
    grid =  ib_NIOS.wapi_request('GET', object_type="grid")
    ref = json.loads(grid)[0]['_ref']
    publish={"member_order":"SIMULTANEOUSLY"}
    request_publish = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=publish_changes",fields=json.dumps(publish))
    time.sleep(1)
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus")
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices")
    get_ref=ib_NIOS.wapi_request('GET', object_type='member:parentalcontrol?name='+member)
    get_ref=json.loads(get_ref)
    if get_ref[0]["enable_service"]==False:
        logging.info ("Test case passed")
        time.sleep(40)
        logging.info ("subscriber service is stopped")
        return get_ref[0]["enable_service"]
    else:
        logging.info("Not able to stop subscriber service")
        return None

class Network(unittest.TestCase):
    @pytest.mark.run(order=1)
    def test_001_Start_DNS_Service(self):
        change_default_route()
        logging.info("Start DNS Service")
        get_ref = ib_NIOS.wapi_request('GET', object_type="member:dns")
        logging.info(get_ref)
        logging.info(get_ref)
        res = json.loads(get_ref)
        for i in res:
            ref=i["_ref"]
            logging.info("Modify a enable_dns")
            data = {"enable_dns": True}
            response = ib_NIOS.wapi_request('PUT', ref=ref, fields=json.dumps(data))
            sleep(20)
            logging.info(response)
            read  = re.search(r'200',response)
            for read in  response:
                assert True
        logging.info("Test Case 5 Execution Completed")

    @pytest.mark.run(order=2)
    def test_002_Validate_DNS_service_Enabled(self):
        logging.info("Validate DNs Service is enabled")
        get_tacacsplus = ib_NIOS.wapi_request('GET', object_type="member:dns",params="?_return_fields=enable_dns")
	print(get_tacacsplus)
        logging.info(get_tacacsplus)
        res = json.loads(get_tacacsplus)
        logging.info(res)
        for i in res:
            logging.info("found")
            assert i["enable_dns"] == True
        logging.info("Test Case 6 Execution Completed")
        logging.info("============================")

    @pytest.mark.run(order=3)
    def test_003_modify_grid_dns_properties(self):
        logging.info("Mofifying GRID dns properties")
        get_ref=ib_NIOS.wapi_request('GET', object_type="grid:dns")
        get_ref1=json.loads(get_ref)[0]['_ref']
        logging.info(get_ref1)
        data={"allow_recursive_query":True,"allow_query":[{"_struct": "addressac","address":"Any","permission":"ALLOW"}],"forwarders":[config.forwarder_ip],"logging_categories":{"log_rpz":True,"log_queries":True,"log_responses":True}}
        put_ref=ib_NIOS.wapi_request('PUT', object_type=get_ref1,fields=json.dumps(data))
        logging.info(put_ref)
        if type(put_ref)!=tuple:
            logging.info("Test Case 8 Execution Passed")
            assert True
        else:
            logging.info("Test Case 8 Execution Failed")
            assert False

    @pytest.mark.run(order=4)
    def test_004_validate_grid_dns_properties(self):
        logging.info("Validating GRID dns properties")
        get_ref=ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=allow_recursive_query,forwarders")
        get_ref1=json.loads(get_ref)
        if get_ref1[0]["allow_recursive_query"]==True and get_ref1[0]["forwarders"]==[config.forwarder_ip]:
            logging.info("Test Case 8 Execution Passed")
            assert True
        else:
            logging.info("Test Case 8 Execution Failed")
            assert False
    
    @pytest.mark.run(order=5)
    def test_005_modify_grid_settings(self):
        logging.info("Mofifying GRID properties")
        response = ib_NIOS.wapi_request('GET', object_type="grid")
        response = json.loads(response)
	response=response[0]["_ref"]
	data={"dns_resolver_setting": {"resolvers": [config.resolver_ip]}}
        res = ib_NIOS.wapi_request('PUT', object_type=response,fields=json.dumps(data))
        print(res)
	logging.info(res)
        if type(res)!=tuple:
            logging.info("Test Case 9 Execution Passed")
            assert True
        else:
            logging.info("Test Case 9 Execution Failed")
            assert False

    @pytest.mark.run(order=10)
    def test_010_validate_grid_settings(self):
        logging.info("Validating GRID properties")
        response = ib_NIOS.wapi_request('GET', object_type="grid?_return_fields=dns_resolver_setting")
        response = json.loads(response)
        response=response[0]["dns_resolver_setting"]["resolvers"]
        if response==[config.resolver_ip]:
            logging.info("Test Case 10 Execution Passed")
            assert True
        else:
            logging.info("Test Case 10 Execution Failed")
            assert False

    @pytest.mark.run(order=11)
    def test_011_enable_parental_control(self):
        logging.info("enabling parental control")
        response = ib_NIOS.wapi_request('GET', object_type="parentalcontrol:subscriber")
        response = json.loads(response)
        response=response[0]["_ref"]
        logging.info(response)
        #data={"enable_parental_control": True,"cat_acctname":"infoblox_sdk", "cat_password":"LinWmRRDX0q","category_url":"https://dl.zvelo.com/","proxy_url":"http://10.196.9.113:8001", "proxy_username":"client", "proxy_password":"infoblox","pc_zone_name":"parental_control", "cat_update_frequency":24}
        data={"enable_parental_control": True,"cat_acctname":"InfoBlox", "cat_password":"CSg@vBz!rx7A","category_url":"https://pitchers.rulespace.com/ufsupdate/web.pl","pc_zone_name":"pc.com", "ident":"pkFu-yhrf-qPOV-s5BU","cat_update_frequency":1}
	#data={"enable_parental_control": True,"cat_acctname":"infoblox_sdk", "cat_password":"LinWmRRDX0q","category_url":"https://dl.zvelo.com/","pc_zone_name":"pc.com", "cat_update_frequency":24}
        res = ib_NIOS.wapi_request('PUT', object_type=response,fields=json.dumps(data))
	print(res)
        logging.info(res)
        if type(res)==tuple:
            if res[0]==400 or res[0]==401:
                logging.info("Test case 11 execution failed")
                assert False
            else:
                logging.info("Test Case 11 execution passed")
        else:
            logging.info("Test Case 11 execution passed")
            assert True

    @pytest.mark.run(order=12)
    def test_012_validate_parental_control_enabled(self):
        logging.info("validating parental control is enabled")
        response = ib_NIOS.wapi_request('GET', object_type="parentalcontrol:subscriber?_return_fields=enable_parental_control")
        print response
        response = json.loads(response)
        response=response[0]["enable_parental_control"]
        if response==True:
            logging.info("Test Case 12 execution passed")
            assert True
        else:
            logging.info("Test Case 12 execution failed")
            assert False

    @pytest.mark.run(order=13)
    def  test_013_add_subscriber_site(self):
        logging.info("Adding subscriber site site2")
        #data={"blocking_ipv4_vip1": "2.4.5.6","msps":[{"ip_address": "10.196.128.13"}],"spms": [{"ip_address": "10.12.11.11"}],"name":"site3","maximum_subscribers":100000,"members":[{"name":config.grid_fqdn}],"nas_gateways":[{"ip_address":"2.2.2.2","name":"nas1","shared_secret":"test123"}]}
        #data={"blocking_ipv4_vip1": "1.1.1.1","blocking_ipv4_vip2": "2.2.2.2","msps":[{"ip_address": "10.196.128.13"}],"spms": [{"ip_address": "10.12.11.11"}],"name":"site2","maximum_subscribers":100000,"members":[{"name":config.grid_fqdn}],"nas_gateways":[{"ip_address":"2.2.2.2","name":"nas1","shared_secret":"test123"}]}
        data={"name":"site2","maximum_subscribers":100000,"members":[{"name":config.grid_fqdn}],"nas_gateways":[{"ip_address":"2.2.2.2","name":"nas1","shared_secret":"test123"}]}
	get_ref=ib_NIOS.wapi_request('POST', object_type="parentalcontrol:subscribersite",fields=json.dumps(data))
        logging.info(get_ref)
        print(get_ref)
        if type(get_ref)!=tuple:
            reference=ib_NIOS.wapi_request('GET', object_type="parentalcontrol:subscribersite")
            reference=json.loads(reference)
            if reference[0]["name"]==data["name"]:
                logging.info("Test case 10 execution passed")
                assert True
            else:
                logging.info("Test case 13 execution Failed")
                assert False
        else:
            logging.info(get_ref)
            logging.info("Test case 13 execution failed")
            assert False

    @pytest.mark.run(order=14)
    def  test_014_validate_for_subscriber_site(self):
        logging.info("validating subscriber site site2 added")
        reference=ib_NIOS.wapi_request('GET', object_type="parentalcontrol:subscribersite")
        reference=json.loads(reference)
        if reference[0]["name"]=="site2":
            logging.info("Test case 14 execution passed")
            assert True
        else:
            logging.info("Test case 14 execution failed")
            assert False

    @pytest.mark.run(order=15)
    def test_015_Start_the_subscriber_service_on_members(self):
        logging.info("Start the subscriber service on members")
        ref=start_subscriber_collection_services_for_added_site([config.grid_fqdn])
        if ref!=None:
            logging.info("Test case 15 executed successfully")
            assert True
        else:
            logging.info("Test case 15 execution failed")
            assert False

    @pytest.mark.run(order=16)
    def test_016_Validate_subscriber_service_is_running(self):
        logging.info("Validating subscriber collection services started")
        members=[config.grid_fqdn]
        for mem in members:
            grid_ref = mem_ref_string_pc(mem)
            print grid_ref
            get_ref=ib_NIOS.wapi_request('GET', object_type=grid_ref)
            #get_ref=json.loads(get_ref)
            #print get_ref
            for ref in get_ref:
                if ref!=tuple:
                    logging.info("Test Case 17 Execution Passed")
                    assert True
                else:
                    logging.info("Test Case 17 Execution Failed")
                    assert False

    @pytest.mark.run(order=17)
    def test_017_start_ufclient_Messages_logs(self):
        logging.info("Starting Syslog Messages Logs")
        log("start","/storage/symantec/log/ufclient.log",config.grid_vip)
        logging.info("Test case 8 execution failed")
        time.sleep(1100)

    @pytest.mark.run(order=18)
    def test_018_stop_ufclient__Messages_logs(self):
        logging.info("Starting Syslog Messages Logs")
        log("stop","/storage/symantec/log/ufclient.log",config.grid_vip)
        logging.info("Test case 9 execution failed")

    @pytest.mark.run(order=19)
    def test_019_validate_for_ufcclient_data(self):
        #time.sleep(40)
        logging.info("Validating Sylog Messages Logs")
        LookFor="ufclient completed|ufclient had no work"
        logs=logv(LookFor,"/storage/symantec/log/ufclient.log",config.grid_vip)
        if logs!=None:
            logging.info(logs)
            logging.info("Test Case 10 Execution Completed")
            assert True
        else:
            logging.info("Test Case 10 Execution Failed")
            assert False

    @pytest.mark.run(order=20)
    def test_020_modify_grid_settings(self):
        logging.info("Mofifying GRID properties")
        response = ib_NIOS.wapi_request('GET', object_type="grid")
        response = json.loads(response)
        response=response[0]["_ref"]
        data={"dns_resolver_setting": {"resolvers": ["127.0.0.1"]}}
        res = ib_NIOS.wapi_request('PUT', object_type=response,fields=json.dumps(data))
        logging.info(res)
        if type(res)!=tuple:
            logging.info("Test Case 9 Execution Passed")
            assert True
        else:
            logging.info("Test Case 9 Execution Failed")
            assert False

    @pytest.mark.run(order=21)
    def test_021_validate_grid_settings(self):
        logging.info("Validating GRID properties")
        response = ib_NIOS.wapi_request('GET', object_type="grid?_return_fields=dns_resolver_setting")
        response = json.loads(response)
        response=response[0]["dns_resolver_setting"]["resolvers"]
        if response==["127.0.0.1"]:
            logging.info("Test Case 10 Execution Passed")
            assert True
        else:
            logging.info("Test Case 10 Execution Failed")
            assert False

    @pytest.mark.run(order=22)
    def  test_022_modify_subscriber_site(self):
        logging.info("Modifying subscriber site site2")
        response = ib_NIOS.wapi_request('GET', object_type="parentalcontrol:subscribersite")
        response = json.loads(response)
        response=response[0]["_ref"]
        #data={"blocking_ipv4_vip1": "2.4.5.6","msps":[{"ip_address": "10.196.128.13"}],"spms": [{"ip_address": "10.12.11.11"}],"name":"site3","maximum_subscribers":100000,"members":[{"name":config.grid_fqdn}],"nas_gateways":[{"ip_address":"2.2.2.2","name":"nas1","shared_secret":"test123"}]}
        data={"blocking_ipv4_vip1": "1.1.1.1","blocking_ipv4_vip2": "2.2.2.2","msps":[{"ip_address": "10.196.128.13"}],"spms": [{"ip_address": "10.12.11.11"}],"maximum_subscribers":100000,"members":[{"name":config.grid_fqdn}],"nas_gateways":[{"ip_address":"2.2.2.2","name":"nas1","shared_secret":"test123"}]}
        #data={"name":"site2","maximum_subscribers":100000,"members":[{"name":config.grid_fqdn}],"nas_gateways":[{"ip_address":"2.2.2.2","name":"nas1","shared_secret":"test123"}]}
        get_ref=ib_NIOS.wapi_request('PUT', object_type=response,fields=json.dumps(data))
        logging.info(get_ref)
        print(get_ref)
        if type(get_ref)!=tuple:
            reference=ib_NIOS.wapi_request('GET', object_type="parentalcontrol:subscribersite?_return_fields=blocking_ipv4_vip1,blocking_ipv4_vip2")
            reference=json.loads(reference)
            if reference[0]["blocking_ipv4_vip1"]==data["blocking_ipv4_vip1"] and reference[0]["blocking_ipv4_vip2"]==data["blocking_ipv4_vip2"]:
                logging.info("Test case 10 execution passed")
                assert True
            else:
                logging.info("Test case 13 execution Failed")
                assert False
        else:
            logging.info(get_ref)
            logging.info("Test case 13 execution failed")
            assert False

    @pytest.mark.run(order=24)
    def test_024_Add_Subscriber_Record_without_Proxy_all_set_and_Different_PCP_Policy_bit_than_above(self):
        try:
            logging.info("Add Subscriber Record without Proxy-All set and different PCP Policy bit than the above")
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip)
            child.logfile=sys.stdout
            child.expect('password:',timeout=None)
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set subscriber_secure_data add '+config.client_ip1+' 32 N/A N/A "ACS:Acct-Session-Id=9999735888;NAS:NAS-PORT=1813;PCP:Parental-Control-Policy=00000000000000000000000000020040;SUB:Calling-Station-Id=110361288;"')
            child.expect('Record successfully added')
            logging.info("Test Case 27 Execution Passed")
            assert True
        except:
            logging.info("Test Case 27 Execution Failed")
            assert False

    @pytest.mark.run(order=25)
    def test_025_Validate_Subscriber_Record_without_Proxy_all_set_and_Different_PCP_Policy_bit_than_above(self):
        logging.info("Validate Subscriber Record without Proxy-All set different PCP Policy bit than the above")
        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip)
        child.logfile=sys.stdout
        child.expect('password:',timeout=None)
        child.sendline('infoblox')
        child.expect('Infoblox >')
        child.sendline('show subscriber_secure_data')
        child.expect('Infoblox >')
        c=child.before
        assert re.search(r'.*'+config.client_ip1+'\/32\|LID\:N\/A\|IPS\:N\/A.*PCP\:Parental-Control-Policy=00000000000000000000000000020040.*',c)
        logging.info("Test case 28 execution completed")

    @pytest.mark.run(order=26)
    def test_026_start_Syslog_Messages_logs_on_IBFLEX_Member(self):
        logging.info("Starting Syslog Messages Logs on IB-FLEX Member")
        log("start","/var/log/syslog",config.grid_vip)
        logging.info("test case 29 passed")
        sleep(10)

    @pytest.mark.run(order=27)
    def test_027_Send_Query_from_PCP_bit_match_Subscriber_client_for_PCP_Domain_times_Using_IB_FLEX_Member_Validate_returns_Blocked_IPs_in_response_from_Bind_As_Not_DCA_Cache(self):
        logging.info("Perform Query from PCP bit match Subscriber client for PCP Domain times.com using IB-FLEX Member and get PCP Blocked IPs response from Bind as times.com not in DCA cache")
        dig_cmd = 'sshpass -p infoblox ssh -o StrictHostKeyChecking=no -o BatchMode=no  root@'+str(config.client_ip1)+' "dig @'+str(config.grid_vip)+' playboy.com +noedns -b '+config.client_ip1+'"'
        dig_result = subprocess.check_output(dig_cmd, shell=True)
        print dig_result
        assert re.search(r'.*QUERY, status: NOERROR.*',str(dig_result))
        assert re.search(r'.*site2-blocking.pc.com.*IN.*A.*1.1.1.1.*',str(dig_result))
        assert re.search(r'.*site2-blocking.pc.com.*IN.*A.*2.2.2.2.*',str(dig_result))
        logging.info("Test Case 30 Execution Completed")

    @pytest.mark.run(order=28)
    def test_028_stop_Syslog_Messages_Logs_on_IB_FLEX_Member(self):
        logging.info("Stopping Syslog Logs on master")
        log("stop","/var/log/syslog",config.grid_vip)
        logging.info("Test Case 31 Execution Completed")

    @pytest.mark.run(order=29)
    def test_029_Validate_Named_CEF_Log_Logs_when_get_response_from_Bind_for_PCP_domain_times_com(self):
        logging.info("Validate Named CEF Log for times.com  when get response from Bind")
        LookFor="named.*info CEF.*playboy.com.*CAT=0x00000000000000000000000000020000"
        logs=logv(LookFor,"/var/log/syslog",config.grid_vip)
        logging.info(logs)
        print logs
        if logs!=None:
            logging.info(logs)
            logging.info("Test Case 32 Execution Passed")
            assert True
        else:
            logging.info("Test Case 32 Execution Failed")
            assert False



    @pytest.mark.run(order=30)
    def test_030_Splunk_API_call_detailed_rpz_violations_subscriber_ID(self):
        logging.info("Detailed RPZ Violations by Subscriber ID")
        import xml.etree.ElementTree as ET
        dat1 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/ -d search="search source=ib:dns:query:top_rpz_hit index=ib_dns | eval SUB_TYPE=if(isnull(SUB_TYPE),\\"N/A\\",SUB_TYPE) | eval SUB_VAL=if(isnull(SUB_VAL),\\"N/A\\",SUB_VAL) | eval IPS_VAL=if(isnull(IPS_VAL),\\"N/A\\",IPS_VAL) | stats count as COUNT by SUB_TYPE, SUB_VAL, IPS_VAL, CLIENT, DOMAIN_NAME, RPZ_QNAME, RPZ_SEVERITY, MITIGATION_ACTION | eventstats sum(COUNT) as TOTAL_DEVICE_HITS by SUB_TYPE, SUB_VAL | sort -TOTAL_DEVICE_HITS | eventstats list(DOMAIN_NAME) as MALICIOUS_DOMAINS, list(RPZ_QNAME) as RPZ_ENTRIES by  SUB_TYPE, SUB_VAL, IPS_VAL, CLIENT, RPZ_SEVERITY, MITIGATION_ACTION | eval MALICIOUS_DOMAINS = mvindex(MALICIOUS_DOMAINS,0,2) | eval RPZ_ENTRIES = mvindex(RPZ_ENTRIES,0,2) | dedup 1 MITIGATION_ACTION, SUB_TYPE, SUB_VAL, IPS_VAL, CLIENT, RPZ_SEVERITY | head 10 | eval MITIGATION_ACTION=case(MITIGATION_ACTION == \\"PT\\", \\"Passthru\\", MITIGATION_ACTION == \\"NX\\", \\"Block (No Such Domain)\\", MITIGATION_ACTION == \\"ND\\", \\"Block (No Data)\\", MITIGATION_ACTION == \\"SB\\", \\"Substitute\\", MITIGATION_ACTION == \\"A1\\", \\"Substitute (A)\\", MITIGATION_ACTION == \\"A4\\", \\"Substitute (AAAA)\\", MITIGATION_ACTION == \\"AA\\", \\"Substitute (A/AAAA)\\", MITIGATION_ACTION == \\"DN\\", \\"Substitute (Domain Name)\\", MITIGATION_ACTION == \\"ER\\", \\"None\\") | eval RPZ_SEVERITY=case(RPZ_SEVERITY == \\"4\\", \\"INFORMATIONAL\\", RPZ_SEVERITY == \\"6\\", \\"WARNING\\", RPZ_SEVERITY == \\"7\\", \\"MAJOR\\", RPZ_SEVERITY == \\"8\\", \\"CRITICAL\\", RPZ_SEVERITY == \\"\\", \\"\\") | rename SUB_TYPE as \\"Subscriber ID Type\\", SUB_VAL as \\"Subscriber ID Value\\", IPS_VAL as \\"IP Space Discriminator\\", CLIENT as \\"Client ID\\", TOTAL_DEVICE_HITS as \\"Total Subscriber Hits\\", MALICIOUS_DOMAINS as \\"Malicious Domains\\", RPZ_ENTRIES as \\"RPZ Entries\\", RPZ_SEVERITY as \\"RPZ Severity\\", MITIGATION_ACTION as \\"Mitigation Action\\" | table \\"Subscriber ID Value\\", \\"Subscriber ID Type\\", \\"Client ID\\", \\"Total Subscriber Hits\\", \\"Malicious Domains\\", \\"RPZ Entries\\", \\"RPZ Severity\\", \\"Mitigation Action\\", \\"IP Space Discriminator\\""'

	print(dat1)
        print(">>>>>>>>>>>>>>>>>>")
	result= subprocess.check_output(dat1,stderr=subprocess.PIPE, shell=True)
        if not "sid" in result:
            assert False, "Could not able to connect reporting server"
        data = ET.fromstring(result)
	print("***********",data)
        sid_val = ''
        for child in data:
            if child.tag == 'sid':
                sid_val = child.text
		print("@@@@@@@@@@@@@@",sid_val)
        if not sid_val:
            assert False, "sid value not found"
	
	sleep(5)
	dat2 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/' +sid_val +'/results --get -d output_mode=json'
	result= subprocess.check_output(dat2,stderr=subprocess.PIPE, shell=True)
	print(dat2)
	sleep(5)
	print("------------------ Result ---------------",result)

        if result == "None":
           assert False, "\n\nReport having empty data"
        else:
           print("\n\nReport is not empty and it has some data")

	output_data = json.loads(result)
	results_list = output_data['results']
	print("\n#################################################",results_list)
        report_status = False
	for data in results_list:
	    print("\n\n",data)
	
            if data.get("Total Subscriber Hits") >= "1":
		if "playboy.com" in data.get("Malicious Domains"):
	            report_status = True
		    break 
		
	    continue
	
	assert report_status, "FAILED"
           
	print("\nTest Case 30 Executed Successfully")	

    @pytest.mark.run(order=31)
    def test_031_dns_rpz_hits_trend_mitigation_action(self):
        logging.info("DNS RPZ Hits Trend By Mitigation Action")
        import xml.etree.ElementTree as ET

	dat1 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/ -d search="search index=ib_dns_summary earliest=-24h report=si_dns_rpz_hits| eval MITIGATION_ACTION=case(MITIGATION_ACTION == \\"PT\\", \\"Passthru\\", MITIGATION_ACTION == \\"NX\\" or MITIGATION_ACTION == \\"ND\\", \\"Block\\", MITIGATION_ACTION == \\"SB\\" or MITIGATION_ACTION ==\\"A1\\" or MITIGATION_ACTION ==\\"A4\\" or MITIGATION_ACTION ==\\"AA\\" or MITIGATION_ACTION ==\\"DN\\", \\"Substitute\\") | fields _time  MITIGATION_ACTION   TOTAL_COUNT   | timechart bins=1000 avg(TOTAL_COUNT) by MITIGATION_ACTION  useother=f | fillnull | addtotals row=true col=false | rename Total as \\"ClientHits\\""'

        print(dat1)
        print(">>>>>>>>>>>>>>>>>>")
        result= subprocess.check_output(dat1,stderr=subprocess.PIPE, shell=True)
        if not "sid" in result:
            assert False, "Could not able to connect reporting server"
        data = ET.fromstring(result)
        print("***********",data)
        sid_val = ''
        for child in data:
            if child.tag == 'sid':
                sid_val = child.text
                print("@@@@@@@@@@@@@@",sid_val)
        if not sid_val:
            assert False, "sid value not found"

        sleep(5)
        dat2 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/' +sid_val +'/results --get -d output_mode=json'
        result= subprocess.check_output(dat2,stderr=subprocess.PIPE, shell=True)
        print(dat2)
        sleep(5)
        print("------------------ Result ---------------",result)

        if result == "None":
           assert False, "\n\nReport having empty data"
        else:
           print("\n\nReport is not empty and it has some data")

        output_data = json.loads(result)
        results_list = output_data['results']
        print("\n#################################################",results_list)
        report_status = False
        for data in results_list:
            #print("\n\n",data)

            if data.get("ClientHits") >= "1" and data.get("Substitute") >= "1":
                report_status = True
                break
	    continue
	assert report_status, "FAILED"
        
	print("\nTest Case 31 Executed Successfully")

    @pytest.mark.run(order=32)
    def test_032_dns_top_firewall_hits(self):
        logging.info("Top DNS Firewall Hits")
        import xml.etree.ElementTree as ET
	
	dat1 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/ -d search="search index=ib_dns_summary earliest=-48h report=si_dns_rpz_hits | fields RPZ_QNAME TOTAL_COUNT DOMAIN_NAME | stats sum(TOTAL_COUNT) as RPZ_HIT_COUNT by RPZ_QNAME DOMAIN_NAME | sort -RPZ_HIT_COUNT | head 10 | eventstats sum(RPZ_HIT_COUNT) as ALL_HIT_COUNT | eval RPZ_HIT_PCT = round(RPZ_HIT_COUNT * 100 / ALL_HIT_COUNT, 2) | rex  field=RPZ_QNAME \\"rpz-ip.(?<RPZ_IP_FEED>[^ ]+)\\""'
        
	print(dat1)
        print(">>>>>>>>>>>>>>>>>>")
        result= subprocess.check_output(dat1,stderr=subprocess.PIPE, shell=True)
        if not "sid" in result:
            assert False, "Could not able to connect reporting server"
        data = ET.fromstring(result)
        print("***********",data)
        sid_val = ''
        for child in data:
            if child.tag == 'sid':
                sid_val = child.text
                print("@@@@@@@@@@@@@@",sid_val)
        if not sid_val:
            assert False, "sid value not found"

        sleep(10)
        dat2 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/' +sid_val +'/results --get -d output_mode=json'
        result= subprocess.check_output(dat2,stderr=subprocess.PIPE, shell=True)
        print(dat2)
        sleep(5)
        print("------------------ Result ---------------",result)

        if result == "None":
           assert False, "\n\nReport having empty data"
        else:
           print("\n\nReport is not empty and it has some data")

        output_data = json.loads(result)
        results_list = output_data['results']
        print("\n#################################################",results_list)
        report_status = False
        for data in results_list:
            print("\n\n",data)

            if data.get("RPZ_HIT_COUNT") == "1" and data.get("RPZ_HIT_PCT") == "100.00":
                report_status = True
                break
            continue
        assert report_status, "FAILED"

        print("\nTest Case 32 Executed Successfully")
 

    @pytest.mark.run(order=33)
    def test_033_dns_top_rpz_hits(self):
        logging.info("DNS Top RPZ Hits")
        import xml.etree.ElementTree as ET
	dat1 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/ -d search="search index=ib_dns_summary earliest=-48h report=si_dns_rpz_hits | lookup dns_viewkey_displayname_lookup VIEW output display_name | eval SUB_VAL=if(isnull(SUB_VAL),\\"N/A\\",SUB_VAL) | stats sum(COUNT) as QCOUNT by _time, CLIENT, DOMAIN_NAME, orig_host, TOTAL_COUNT, MITIGATION_ACTION, RPZ_SEVERITY, REDIRECTION_RECORD, RPZ_QNAME, SUB_VAL | stats sum(TOTAL_COUNT) as TOTAL_COUNT, sum(QCOUNT) as QCOUNT by _time, CLIENT, DOMAIN_NAME, RPZ_QNAME | eval RPZ_SEVERITY=case(RPZ_SEVERITY == \\"4\\", \\"INFORMATIONAL\\", RPZ_SEVERITY == \\"6\\", \\"WARNING\\", RPZ_SEVERITY == \\"7\\", \\"MAJOR\\", RPZ_SEVERITY == \\"8\\", \\"CRITICAL\\", RPZ_SEVERITY == \\"\\", \\"\\") | rename CLIENT as \\"Client ID\\", QCOUNT as \\"Total Client Hits\\", DOMAIN_NAME as \\"Domain Name\\", TOTAL_COUNT as \\"Total Rule Hits\\", RPZ_QNAME as \\"RPZ Entry\\", RPZ_SEVERITY as \\"RPZ Severity\\" | sort -\\"Total Client Hits\\" | head 10 | table \\"Client ID\\", \\"Total Client Hits\\", \\"Domain Name\\", \\"RPZ Entry\\", \\"RPZ Severity\\", \\"Total Rule Hits\\", Time"'

        print(dat1)
        print(">>>>>>>>>>>>>>>>>>")
        result= subprocess.check_output(dat1,stderr=subprocess.PIPE, shell=True)
        if not "sid" in result:
            assert False, "Could not able to connect reporting server"
        data = ET.fromstring(result)
        print("***********",data)
        sid_val = ''
        for child in data:
            if child.tag == 'sid':
                sid_val = child.text
                print("@@@@@@@@@@@@@@",sid_val)
        if not sid_val:
            assert False, "sid value not found"

        sleep(10)
        dat2 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/' +sid_val +'/results --get -d output_mode=json'
        result= subprocess.check_output(dat2,stderr=subprocess.PIPE, shell=True)
        print(dat2)
        sleep(5)
        print("------------------ Result ---------------",result)

        if result == "None":
           assert False, "\n\nReport having empty data"
        else:
           print("\n\nReport is not empty and it has some data")

        output_data = json.loads(result)
        results_list = output_data['results']
        print("\n#################################################",results_list)
        report_status = False
        for data in results_list:
            print("\n\n",data)

            if all([data.get("Total Rule Hits") == "1", data.get("Total Client Hits") == "1", data.get("RPZ Entry") == "playboy.com"]):
                report_status = True
            else:
		assert report_status, "FAILED"

        print("\nTest Case 33 Executed Successfully")

    @pytest.mark.run(order=34)
    def test_034_dns_top_rpz_hits_by_clients(self):
        logging.info("DNS Top RPZ Hits by Clients")
        import xml.etree.ElementTree as ET
	dat1 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/ -d search="search index=ib_dns_summary earliest=-48h report=si_dns_rpz_hits | lookup dns_viewkey_displayname_lookup VIEW output display_name | stats avg(COUNT) as QCOUNT by _time,orig_host,VIEW,CLIENT,SUB_TYPE,SUB_VAL | stats sum(QCOUNT) as QCOUNT by _time, CLIENT | eval QCOUNT=round(QCOUNT) | convert ctime(_time) as Time | rename CLIENT as \\"Client ID\\", QCOUNT as \\"Total Client Hits\\" | append [ search index=ib_dns_summary report=si_dns_rpz_hits | stats avg(COUNT) as QCOUNT by _time, VIEW, CLIENT, orig_host | stats sum(QCOUNT) as QCOUNT by _time, CLIENT | eval QCOUNT=round(QCOUNT) | convert ctime(_time) as Time | rename CLIENT as \\"Client ID\\", QCOUNT as \\"Total Client Hits\\" ] | sort -\\"Total Client Hits\\" | head 10 | table \\"Client ID\\", \\"Total Client Hits\\", Time"' 

        print(dat1)
        print(">>>>>>>>>>>>>>>>>>")
        result= subprocess.check_output(dat1,stderr=subprocess.PIPE, shell=True)
        if not "sid" in result:
            assert False, "Could not able to connect reporting server"
        data = ET.fromstring(result)
        print("***********",data)
        sid_val = ''
        for child in data:
            if child.tag == 'sid':
                sid_val = child.text
                print("@@@@@@@@@@@@@@",sid_val)
        if not sid_val:
            assert False, "sid value not found"

        sleep(10)
        dat2 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/' +sid_val +'/results --get -d output_mode=json'
        result= subprocess.check_output(dat2,stderr=subprocess.PIPE, shell=True)
        print(dat2)
        sleep(5)
        print("------------------ Result ---------------",result)

        if result == "None":
           assert False, "\n\nReport having empty data"
        else:
           print("\n\nReport is not empty and it has some data")
        
	output_data = json.loads(result)
        results_list = output_data['results']
        print("\n#################################################",results_list)
        report_status = False
        for data in results_list:
            print("\n\n",data)

            if data.get("Client ID") == config.client_ip1 and data.get("Total Client Hits") >= "1":
                report_status = True
            else:
		assert report_status, "FAILED"

        print("\nTest Case 34 Executed Successfully")

    @pytest.mark.run(order=35)
    def test_035_dns_firewall_executive_threat(self):
        logging.info("DNS Firewall Executive Threat Report")
        import xml.etree.ElementTree as ET
        dat1 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/ -d search="search index=ib_dns_summary earliest=-72h report=si_dns_rpz_hits | fields RPZ_QNAME TOTAL_COUNT DOMAIN_NAME | stats sum(TOTAL_COUNT) as RPZ_HIT_COUNT by RPZ_QNAME, DOMAIN_NAME| where RPZ_HIT_COUNT >=0  | sort -RPZ_HIT_COUNT  | head 10  | eventstats sum(RPZ_HIT_COUNT) as ALL_HIT_COUNT  | eval RPZ_HIT_PCT = round(RPZ_HIT_COUNT * 100 / ALL_HIT_COUNT, 2)  | rex  field=RPZ_QNAME \\"rpz-ip.(?<RPZ_IP_FEED>[^ ]+)\\" | rename RPZ_QNAME as \\"RPZ Rule\\", RPZ_HIT_PCT as \\"Percentage\\", RPZ_HIT_COUNT as \\"# Hits\\", public_description as \\"Description\\"  | table \\"RPZ Rule\\" \\"Percentage\\" \\"# Hits\\" \\"Description\\""'
        print(dat1)
        print(">>>>>>>>>>>>>>>>>>")
        result= subprocess.check_output(dat1,stderr=subprocess.PIPE, shell=True)
        if not "sid" in result:
            assert False, "Could not able to connect reporting server"
        data = ET.fromstring(result)
        print("***********",data)
        sid_val = ''
        for child in data:
            if child.tag == 'sid':
                sid_val = child.text
                print("@@@@@@@@@@@@@@",sid_val)
        if not sid_val:
            assert False, "sid value not found"

        sleep(10)
        dat2 = 'curl -k -u manoj:manoj https://' +config.grid_member5_vip +':9185/services/search/jobs/' +sid_val +'/results --get -d output_mode=json'
        result= subprocess.check_output(dat2,stderr=subprocess.PIPE, shell=True)
        print(dat2)
        sleep(5)
        print("------------------ Result ---------------",result)
	
	if result == "None":
	   assert False, "\n\nReport having empty data"
	else:
	   print("\n\nReport is not empty and it has some data")
        
	output_data = json.loads(result)
        results_list = output_data['results']
        print("\n#################################################",results_list)
        report_status = False
        for data in results_list:
            print("\n\n",data)

            if all([data.get("RPZ Rule") == "playboy.com", data.get("Percentage") == "100.00", data.get("# Hits") == "1"]):
                report_status = True
            else:
		assert report_status, "FAILED"

        print("\nTest Case 35 Executed Successfully")

