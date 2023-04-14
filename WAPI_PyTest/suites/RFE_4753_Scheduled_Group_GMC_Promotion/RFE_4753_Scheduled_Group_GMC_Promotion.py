import re
import sys
import config
import pytest
import unittest
import logging
import ast
import os
import os.path
from os.path import join
import subprocess
import json
import time
import subprocess
from time import sleep
import commands
import ib_utils.ib_NIOS as ib_NIOS
import ib_utils.common_utilities as common_util
import ib_utils.log_capture as log_capture
from  ib_utils.log_capture import log_action as log
from  ib_utils.log_validation import log_validation as logv
import pexpect
import paramiko
from ib_utils.common_utilities import generate_token_from_file

#Variables
global group_ref_Default; group_ref_Default = "gmcgroup/b25lLmdtY19ncm91cCREZWZhdWx0:Default"
global group_ref_gp1; group_ref_gp1 = "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
global group_ref_gp2; group_ref_gp2 = "gmcgroup/b25lLmdtY19ncm91cCRncDI:gp2"
global group_schedule_ref; group_schedule_ref = "b25lLmdtY19zY2hlZHVsZV9ncm91cCQw"
global current_epoch_time; current_epoch_time = 0

global non_super_user_group1_name; non_super_user_group1_name = "non_super_group1"
global non_super_user_group1_ref
global non_super_user_group1_username1; non_super_user_group1_username1 = "ns_group1_user1"
global non_super_user_group1_password1; non_super_user_group1_password1 = "infoblox"
global non_super_user_group1_username1_ref
global schedule_group_time_gp1; schedule_group_time_gp1 = 0
global schedule_group_time_gp2; schedule_group_time_gp2 = 0



#supporting Functions
def print_and_log(arg=""):
        print(arg)
        logging.info(arg)

def print_and_log_header(arg=""):
	arg = "\n" + "*"*10 + " " + "Beginning of Test Case : " + arg +  " " + "*"*10
	print_and_log(arg)

def print_and_log_footer(arg=""):
        arg = "*"*10 + " " + "End of Test Case: " + arg +  " " + "*"*10
        print_and_log(arg)


#GMC group WAPI Requests functions
def Get_GMC_Groups(master_ip=config.grid_vip):
        print_and_log("Get GMC groups in the grid")
	get_data = ib_NIOS.wapi_request('GET', object_type="gmcgroup", grid_vip=master_ip)
	gmc_groups = json.loads(get_data)
	print_and_log("GMC Groups in the grid are : " + str(gmc_groups))
	return gmc_groups

def Count_GMC_Groups(local_gmc_groups):
	print_and_log("Count GMC groups in the grid")
        count = len(local_gmc_groups)
	return count	

def Get_GMC_Group_Name_and_Ref_using_index(local_gmc_groups, index):
	print_and_log("Print GMC group Names and Ref in the grid of given index : " + str(index))
	gmc_group = local_gmc_groups[index]
	group_name, group_ref = (gmc_group["name"], gmc_group["_ref"])
	print_and_log("GMC group Name is " +  group_name)
	print_and_log("GMC group Ref is " +  group_ref)
        return group_name, group_ref

def Get_GMC_Group_Name_and_Ref_using_Group_Name(local_gmc_groups, search_group_name):
        print_and_log("Print GMC group name and ref in the grid using given group name : " + str(index))
	for group_group in local_gmc_groups:
		group_name, group_ref = (gmc_group["name"], gmc_group["_ref"])
		if (group_name ==  search_group_name):
			return group_ref
		else:
			return "GroupNOTFound"

def Get_GroupRef_DefaultGroup():
        print_and_log("Get GroupRef of Default Group")
        get_data = ib_NIOS.wapi_request('GET', object_type="gmcgroup")
        res = json.loads(get_data)
	group_ref = res[0]["_ref"]
        global group_ref

def Create_GMC_Group(group_name, master_ip=config.grid_vip):
        print_and_log("\n********** Function: Create_GMC_Group **********")
        data = {"name":group_name}
        get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data), grid_vip=master_ip)
        print_and_log(get_data)
        group_ref = json.loads(get_data)
        print_and_log(group_ref)
        return group_ref

def Delete_GMC_Group(group_ref, master_ip=config.grid_vip):
        	print_and_log("\n********** Validate Deletion of GMC Group **********")
                get_data = ib_NIOS.wapi_request('DELETE', object_type=""+group_ref, grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == group_ref


def Add_Members_to_GMC_Group(group_ref, data, master_ip=config.grid_vip):
                print_and_log("\n********** Function: Validate Addition of Members to GMC Group **********")
                #member_name = "vm-sa1.infoblox.com"
                #member_name = config.grid1_member2_fqdn
                #data =  {"members":[{"member": member_name}]}
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}]}
                print_and_log("member data :"+ str(data))
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref, fields=json.dumps(data), grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == group_ref_gp1
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of members in group : " + str(count))
                #validate member count in group matches the member count in data
		assert count == len(data["members"])
                #ToDo: Validate member is moved out of default group as it is moved to new group

def join_now(group_name, master_ip=config.grid_vip):
                print_and_log("\n********** Function: join now **********")
                data = {"gmc_group_name": group_name}
                print_and_log("data :"+ str(data))
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup?_function=reconnect_group_now", fields=json.dumps(data), grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)


def Get_GMC_Schedule_Activation_Status(master_ip=config.grid_vip):
                # Get  GMC schedule 
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                activate_status_gmcschedule = res["activate_gmc_group_schedule"]
                return activate_status_gmcschedule
		#assert activate_status_gmcschedule == True

def Activate_GMC_Schedule(master_ip=config.grid_vip):
                print_and_log("\n********** Activating GMC Schedule **********")
                data = {"activate_gmc_group_schedule": True}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcschedule/"+group_schedule_ref
                # Validate GMC schedule is active
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                activate_status_gmcschedule = res["activate_gmc_group_schedule"]
                assert activate_status_gmcschedule == True
                print_and_log("*********** Function Execution Completed **********")

def Deactivate_GMC_Schedule(master_ip=config.grid_vip):
                print_and_log("\nFunction: ********** Deactivating GMC Schedule **********")
                #Deactivate schedule to bring back to base state
                data = {"activate_gmc_group_schedule": False}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data), grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcschedule/"+group_schedule_ref
                # Validate GMC schedule is inactive
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                activate_status_gmcschedule = res["activate_gmc_group_schedule"]
                assert activate_status_gmcschedule == False
		print_and_log("*********** Function Execution Completed **********")

def Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref, schedule_time, gmc_promotion_policy, master_ip=config.grid_vip):
                print_and_log("\n********** Function: Validate Updation of Scheduled Time and GMC Promotion Policy to GMC Group **********")
                #data = {"scheduled_time": 1675772044,"gmc_promotion_policy":"SEQUENTIALLY"}
                data = {"scheduled_time": schedule_time, "gmc_promotion_policy": gmc_promotion_policy}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref, fields=json.dumps(data), grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == group_ref
                # Validate gmcpromotion and Scheduled Time is added to gp1 group [EXPECTED to FAIL as we have a bug]
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                gmc_promotion_policy = res["gmc_promotion_policy"]
                scheduled_time = res["scheduled_time"]
		#scheduled_time = add_minutes_to_epoch_time(scheduled_time, 8*60) # validate and log a bug
                print_and_log("gmc_promotion_policy is " + gmc_promotion_policy + " scheduled_time is " + str(scheduled_time)) 
		assert gmc_promotion_policy == data["gmc_promotion_policy"] and scheduled_time == data["scheduled_time"]
                print_and_log("*********** Function Execution Completed **********")
                # Validat5 member is added to gp1 group
		print_and_log("Current Grid master vip is " + config.grid_vip)
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                print_and_log("Number of members : " + str(count))
                #assert count == 1
                return count
                print_and_log("*********** Function Execution Completed **********")


def Get_Count_of_members_in_GMCGroup(group_ref, master_ip=config.grid_vip):
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone", grid_vip=master_ip)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                #assert count == 1
                return count
                print_and_log("*********** Function Execution Completed **********")


def Get_List_of_members_in_GMCGroup(group_ref):
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                list_members = res["members"]
                print_and_log("List of members : " + str(list_members))
		member_array = []
		for element in list_members:
			print_and_log("element is " + str(element) + " and parsed is " + element["member"])
			member_array.append(str(element["member"]))
                return member_array
                print_and_log("*********** Function Execution Completed **********")

def Get_jsonList_of_members_in_GMCGroup(group_ref):
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                list_members = res["members"]
                print_and_log("List of members : " + str(list_members))
                return list_members
                print_and_log("*********** Function Execution Completed **********")


#GMC Promotion functions
def GMC_promote_member_as_master_candidate(master_vip, member_fqdn):
    print_and_log("\nFunction: GMC_promote_member_as_master_candidate for master " + master_vip + " member_fqdn is " + member_fqdn)
    print_and_log("grid_master_vip is " + master_vip)
    get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=master_vip)
    print_and_log(get_ref)
    print_and_log("member_fqdn is " + member_fqdn)
    for ref in json.loads(get_ref):
	print_and_log(ref)
        if member_fqdn in ref['_ref']: #if config.grid1_member2_fqdn in ref['_ref']:
            print_and_log("grid_member _ref is " + ref['_ref'])
	    data = {"master_candidate": True}
            #ref1 = json.loads(get_ref)[1]['_ref']
    	    print_and_log("grid_master_vip is " + master_vip)
            print_and_log("_ref is " + ref['_ref'])
            print_and_log("data is " + str(data))
	    response = ib_NIOS.wapi_request('PUT', ref=ref['_ref'], fields=json.dumps(data), grid_vip=master_vip)
            print_and_log(response)
            if type(response) == tuple:
                if response[0]==200:
                    print_and_log("Success: set master candidate to true for member")
                    assert True
                else:
                    print_and_log("Failure: Can't set master candidate to true for member")
                    assert False
            elif "member" in response:
                print_and_log("Success: set master candidate to true for member")
                assert True

def promote_master(IP):
    print_and_log("\nFunction: promote_master")
    child1 = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+IP)
    try:
        child1.logfile=sys.stdout
        child1.expect('password:')
        child1.sendline('infoblox')
        child1.expect('Infoblox >')
        child1.sendline('set promote_master')
        child1.expect('y or n')
        child1.sendline('y')
        child1.expect('Default: 30s')
        child1.sendline('\n')
        child1.expect('y or n')

        child1.sendline('y\n')

        child1.expect('y or n')
        child1.sendline('y\n')

        child1.expect('y or n')
        child1.sendline('y\n')

        output = child1.before
        print_and_log(output)
        check_able_to_login_appliances(IP)
        child1.close()
        assert True
    except Exception as e:
        child1.close()
        print_and_log("Failure: Can't promote GMC Master as master candidate")
        print_and_log(e)
        assert False

def promote_master_new(IP):
    print_and_log("\nFunction: promote_master")
    child1 = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+IP)
    try:
        child1.logfile=sys.stdout
        child1.expect('password:')
        child1.sendline('infoblox')
        child1.expect('Infoblox >')
        child1.sendline('set promote_master')
	child1.expect('y or n')
        child1.sendline('y')
        #child1.expect('Default: 30s')
        #child1.sendline('\n')
        child1.expect('y or n')

 	child1.sendline('y\n')

        #child1.expect('y or n')
        #child1.sendline('y\n')

        #child1.expect('y or n')
        #child1.sendline('y\n')

       #offline members
	#child1.expect('y or n')
        #child1.sendline('y')

	#disaster recovery
	#child1.expect('y or n')
        #child1.sendline('y\n')

        # scheduled time expired
        #child1.expect('y or n')
        #child1.sendline('y')
        
        # will come grid master
        #child1.expect('y or n')
        #child1.sendline('y\n')

        #child1.expect('Default: 30s')
        #child1.sendline('\n')
        #child1.expect('y or n')

        #sleep(120)
        output = child1.before
        print_and_log(output)
        check_able_to_login_appliances(IP)
        child1.close()
        assert True

    except Exception as e:
        child1.close()
        print_and_log("Failure: Can't promote GMC Master as master candidate")
        print_and_log(e)
        assert False

def validate_status_GM_after_GMC_promotion(IP):
    print_and_log("\nFunction: validate_status_GM_after_GMC_promotion")
    check_able_to_login_appliances(IP)
    try:
        child = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no admin@'+IP)
        child.logfile=sys.stdout
        child.expect('password:')
        child.sendline('infoblox')
        child.expect('Infoblox >')
        child.sendline('show network')
        child.expect('Infoblox >')
        print_and_log("\n")
        output = child.before
        print_and_log("==============================")
        print_and_log(output)
        data = 'Master of Infoblox Grid'
        if data in output:
            print_and_log("Success: this member become GM after the promotion")
            assert True
        else:
            print_and_log("Failure: this member did not become GM after the promotion")
            assert False
    except Exception as error_message:
            print_and_log(error_message)
            assert False
    finally:
            child.close()

def reboot_node(IP):
    print_and_log("start rebooting "+str(IP))
    try:
        child1 = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+IP)
        child1.logfile=sys.stdout
        child1.expect('password:')
        child1.sendline('infoblox')
        child1.expect('Infoblox >')
        child1.sendline('reboot')
        child1.expect('y or n')
        child1.sendline('y')
        sleep(240)
        check_able_to_login_appliances(IP)
        sleep(30)
        child1.close()

    except Exception as e:
        child1.close()
        print_and_log("\n Failure: error in rebooting")
        print_and_log("\n================Error====================\n")
        print_and_log(e)
        assert False

def verify_the_node_after_a_HA_failover(IP,data):
    try:
        child = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no admin@'+IP)
        child.logfile=sys.stdout
        child.expect('password:')
        child.sendline('infoblox')
        child.expect('Infoblox >')
        child.sendline('show status')
        child.expect('Infoblox >')
        print("\n")
        output = child.before
        print("==============================")
        #print(output)
        if data in output:
            print("Success: this member become "+data+" node after the HA failover")
            assert True
        else:
            print("Failure: this member did not become "+data+" node after the HA failover")
            assert False

    except Exception as error_message:
            print(error_message)
            assert False
    finally:
            child.close()

    for i in range(5):
        try:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+ip)
            child.logfile=sys.stdout
            child.expect('password:')
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.close()
            print_and_log("\n************Appliances is Working************\n ")
            sleep(120)
            assert True
            break

        except Exception as e:
            child.close()
            print_and_log(e)
            sleep(120)
            continue
            print_and_log("Failure: Appliances did not comeup(vm didn't comeup)")
            assert False


def verify_the_node_after_a_GMC_promotion(IP,data):
    try:
        child = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no admin@'+IP)
        child.logfile=sys.stdout
        child.expect('password:')
        child.sendline('infoblox')
        child.expect('Infoblox >')
        child.sendline('show status')
        child.expect('Infoblox >')
        print("\n")
        output = child.before
        print("==============================")
        #print(output)
        if data in output:
            print("Success: this member become "+data+" node after the HA failover")
            assert True
        else:
            print("Failure: this member did not become "+data+" node after the HA failover")
            assert False

    except Exception as error_message:
            print(error_message)
            assert False
    finally:
            child.close()

    for i in range(5):
        try:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+ip)
            child.logfile=sys.stdout
            child.expect('password:')
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.close()
            print_and_log("\n************Appliances is Working************\n ")
            sleep(120)
            assert True
            break

        except Exception as e:
            child.close()
            print_and_log(e)
            sleep(120)
            continue
            print_and_log("Failure: Appliances did not comeup(vm didn't comeup)")
            assert False

def is_grid_alive(grid=config.grid_vip):
    """
    Checks whether the grid is reachable
    """
    ping = os.popen("ping -c 2 "+grid).read()
    display_msg(ping)
    if "0 received" in ping:
        return False
    else:
        return True

def check_able_to_login_appliances(ip):

    for i in range(5):
        try:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+ip)
            child.logfile=sys.stdout
            child.expect('password:')
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.close()
            print("\n************Appliances is Working************\n ")
            sleep(120)
            assert True
            break

        except Exception as e:
            child.close()
            print(e)
            sleep(120)
            continue

            print("Failure: Appliances did not comeup(vm didn't comeup)")

            assert False


def get_restart_time_from_cli(protocol,grid=config.grid_vip,user='admin',password='infoblox'):
    #remove_known_hosts_file()
    try:
        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no '+user+'@'+grid)
        child.logfile=sys.stdout
        child.expect('password:',timeout=None)
        child.sendline(password)
        child.expect('Infoblox >')
        output=child.before
        child.sendline('exit')
    except Exception as E:
        display_msg("Exception: ")
        display_msg(E)
        assert False
    finally:
        child.close()
    output=output.split('\n')
    pasword = ''
    enable_password = ''
    for line in output:
        line = line.encode('ascii','ignore')
        match = re.match("^(.+) System restart.*", line)
        match2 = re.match("^Infoblox NIOS Release (.+)$", line)
#        if match:
#            pasword = match.group(1)
#            display_msg("Password: "+pasword)
#        elif match2:
#            enable_password = match2.group(1)
#            display_msg("Enable password: "+enable_password)
    return match

def Poweroff_the_member(eng_lab_id):
        logging.info("Poweroff the member")
        cmd = 'reboot_system -H '+str(eng_lab_id)+' -a poweroff -c '+config.client_user+''
        cmd_result = subprocess.check_output(cmd, shell=True)
        print cmd_result
        assert re.search(r'.*poweroff completed.*',str(cmd_result))
        logging.info("Poweroff Completed")

def Poweron_the_member(eng_lab_id):
        logging.info("Poweron the member")
        cmd = 'reboot_system -H '+str(eng_lab_id)+' -a poweron -c '+config.client_user+''
        cmd_result = subprocess.check_output(cmd, shell=True)
        print cmd_result
        assert re.search(r'.*poweron completed.*',str(cmd_result))
        logging.info("Poweron Completed")
        sleep(320)




# Time related Functions 
def get_current_epoch_time():
    print_and_log("Function: get_current_epoch_time")
    current_epoch_time = int(time.time())
    #current_epoch_time_DST = add_minutes_to_epoch_time(current_epoch_time, 60)
    #return current_epoch_time_DST
    return current_epoch_time

def add_minutes_to_epoch_time(epoch_time, minutes_to_add):
    print_and_log("Function: add_minutes_to_epoch_time")
    return int(epoch_time + (minutes_to_add * 60))

def subtract_minutes_to_epoch_time(epoch_time, minutes_to_subtract):
    print_and_log("Function: subtract_minutes_to_epoch_time")
    return int(epoch_time - (minutes_to_subtract * 60))

#non-superuser group
def create_nonsuperuser_group(group_name):
	logging.info("Create a non-super-user group")
        data={"name": group_name,"access_method": ["API","CLI"]}
        response = ib_NIOS.wapi_request('POST',object_type="admingroup",fields=json.dumps(data))
        print("#######################",response)
        logging.info(response)
        logging.info("============================")
        read  = re.search(r'200',response)
        for read in response:
            assert True
        print("Group" + group_name + " is created")
	return response #group_ref

def create_nonsuperuser_user(group_name, user_name, user_password):
        logging.info("Create a non-super-user group")
        data = {"name": user_name,"password":user_password,"admin_groups": [group_name]}
        response = ib_NIOS.wapi_request('POST',object_type="adminuser",fields=json.dumps(data))
        print("#######################",response)
        logging.info(response)
        logging.info("============================")
        read  = re.search(r'200',response)
        for read in response:
            assert True
        print("Admin user 'user' is created")
        return response #user_ref

def get_admingroup_ref(non_super_user_group1_username1):
                object_type_string = 'admingroup?name=' + non_super_user_group1_username1
                #res = ib_NIOS.wapi_request('GET',object_type='admingroup?name=non_super_group1')
                res = ib_NIOS.wapi_request('GET',object_type=object_type_string)
                res = json.loads(res)
                print_and_log("res is " + str(res))
                ref1=res[0]['_ref']
                print_and_log("nonsuperuser ref " + ref1)

#backup restore
def grid_backup(master_ip=config.grid_vip):
        print ("Take Grid Backup")
        data = {"type": "BACKUP"}
        response = ib_NIOS.wapi_request('POST', object_type="fileop?_function=getgriddata", fields=json.dumps(data), grid_vip=master_ip)
        res = json.loads(response)
        URL=res['url']
        print("URL is : %s", URL)
        infoblox_log_validation ='curl -k -u admin:infoblox -H  "content-type: application/force-download" "' + str(URL) +'" -o "database.bak"'
        print ("infoblox.log",infoblox_log_validation)
        out2 = commands.getoutput(infoblox_log_validation)
        print("logs are",out2)
        print ("Backup is Done")
        read  = re.search(r'201',URL)
        for read in  response:
                assert True
        logging.info("Backup Completed")
        sleep(10)

def grid_restore(master_ip=config.grid_vip):
        logging.info("Grid Restore")
        response = ib_NIOS.wapi_request('POST', object_type="fileop?_function=uploadinit", grid_vip=master_ip)
        print response
        res = json.loads(response)
        URL=res['url']
        token1=res['token']
        print("URL is : %s", URL)
        print("Token is %s",token1)
        infoblox_log_validation ='curl -k -u admin:infoblox -H content_type="content-typemultipart-formdata" ' + str(URL) +' -F file=@database.bak'
        print infoblox_log_validation
        out2 = commands.getoutput(infoblox_log_validation)
        print ("out2$$$$$$",out2)
        data2={"mode":"NORMAL","nios_data":True,"token":token1}
        print ("&*&*&*&*&*&*",data2)
        response2 = ib_NIOS.wapi_request('POST', object_type="fileop?_function=restoredatabase",fields=json.dumps(data2), grid_vip=master_ip)
        sleep(300)
        logging.info("Validate Syslog afer perform queries")
        infoblox_log_validation = 'ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o UserKnownHostsFile=/dev/null root@' + str(master_ip) + ' " tail -2400 /infoblox/var/infoblox.log "'
        out1 = commands.getoutput(infoblox_log_validation)
        print out1
        logging.info(out1)
        assert re.search(r'restore_node complete',out1)
        sleep(50)
        read  = re.search(r'201',response)
        for read in  response:
            assert True
        logging.info("Restore Completed")



#DNS functions 
def dns_test_zone_arecords(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    #adding Zone
    zone1 = {"fqdn":"top_clients_per_domain.com","view":"default","grid_primary": [{"name": master_fqdn,"stealth": False}]}
    response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(zone1), grid_vip=master_ip)
    print(response)
    #Restarting 
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(60)

    #Adding RR's
    a_record1 = {"name":"domain1.top_clients_per_domain.com","ipv4addr":"10.10.10.10"}
    ref_admin_a = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(a_record1), grid_vip=master_ip)
    print(ref_admin_a)
    a_record2 = {"name":"domain2.top_clients_per_domain.com","ipv4addr":"20.20.20.20"}
    ref_admin_a = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(a_record2), grid_vip=master_ip)
    print(ref_admin_a)
    a_record3 = {"name":"domain3.top_clients_per_domain.com","ipv4addr":"30.30.30.30"}
    ref_admin_a = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(a_record3), grid_vip=master_ip)
    print(ref_admin_a)


def dns_test_zone_allrecords_restart_simultaneously(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    data = {"fqdn": "abc.com"}
    response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(data), grid_vip=master_ip)
    print response
    logging.info(response)

    get_ref = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn=abc.com", grid_vip=master_ip)
    logging.info(get_ref)
    res = json.loads(get_ref)
    ref1 = json.loads(get_ref)[0]['_ref']
    print ref1

    data = {"grid_primary": [{"name": master_fqdn,"stealth":False}]}
    response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=master_ip)
    logging.info(response)

    logging.info("Restart services")
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    publish={"member_order":"SIMULTANEOUSLY"}
    request_publish = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=publish_changes",fields=json.dumps(publish), grid_vip=master_ip)
    sleep(10)
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(20)

    data={"name":"arec.abc.com","ipv4addr":"3.3.3.3","view": "default"}
    response = ib_NIOS.wapi_request('POST', object_type="record:a",fields=json.dumps(data), grid_vip=master_ip)
    data={"name":"aaaa.abc.com","ipv6addr": "23::","view": "default"}
    response = ib_NIOS.wapi_request('POST', object_type="record:aaaa",fields=json.dumps(data), grid_vip=master_ip)
    data={"name":"cname.abc.com","canonical": "test.com","view": "default"}
    response = ib_NIOS.wapi_request('POST', object_type="record:cname",fields=json.dumps(data), grid_vip=master_ip)
    data={"name": "mx.test.com","mail_exchanger": "test.com","preference": 10,"view": "default"}
    response = ib_NIOS.wapi_request('POST', object_type="record:mx",fields=json.dumps(data), grid_vip=master_ip)
    data={"name": "hinfo.test.com","record_type": "hinfo","subfield_values": [{"field_type": "P","field_value": "\"INTEL\" \"INTEL\"","include_length": "NONE"}],"view": "default"}
    response = ib_NIOS.wapi_request('POST', object_type="record:unknown",fields=json.dumps(data), grid_vip=master_ip)


def dns_test_recursive_queries(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    #Need's to configure forwarder & enabling recursion

    print_and_log("Enabling Recursion")
    member_dns =  ib_NIOS.wapi_request('GET', object_type="member:dns?host_name~="+config.grid1_member1_fqdn, grid_vip=master_ip)
    ref = json.loads(member_dns)[0]['_ref']
#   enable_recursion_forwarder={"allow_recursive_query":True,"forwarders":[config.client_ip]}
    enable_recursion_forwarder={"allow_recursive_query":True}
    response = ib_NIOS.wapi_request('PUT', object_type=ref, fields=json.dumps(enable_recursion_forwarder), grid_vip=master_ip)

    #Restarting 
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(60)

    #fp=os.popen("/usr/bin/queryperf/queryperf -s "+config.grid_member1_vip+" -d ib_data/DNS_Query/DNS_Top_Timed_Out_Recursive_Queries/queryperf.txt -t 1")
    #fp=os.popen("dduq -i 10.35.195.11 -f ~/API_Automation_08_12_20/WAPI_PyTest/Reporting_FR/ib_data/DNS_Query/DNS_Top_Timed_Out_Recursive_Queries/queryperf.txt -t 1")
    #logger.info("%s",''.join(fp.readlines()))

    print_and_log("Cleanup,disabling recursion")
    member_dns =  ib_NIOS.wapi_request('GET', object_type="member:dns?host_name~="+config.grid1_member1_fqdn, grid_vip=master_ip)
    ref = json.loads(member_dns)[0]['_ref']
    disable_recursion_forwarder={"allow_recursive_query":False,"use_recursive_query_setting":False,"use_forwarders":False}
    response = ib_NIOS.wapi_request('PUT', object_type=ref, fields=json.dumps(disable_recursion_forwarder), grid_vip=master_ip)

    #Restarting 
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(60)


def dns_test_nxdomain_noerror(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    print_and_log("Adding zone 57.in-addr.arpa, dns_top_nxdomain_or_noerror.com & 7.7.7.7.ip6.arpa")
    #TEST Preparation, Adding zone 'dns_top_clients.com',  GM as Primary , Member1 & Member2 as secondary for resolving members
    zone1 = {"fqdn":"dns_top_nxdomain_or_noerror.com","view":"default","grid_primary": [{"name": config.grid1_master_fqdn,"stealth": False}]}
    response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(zone1), grid_vip=master_ip)

    zone2 = {"fqdn":"57.0.0.0/8","view":"default","zone_format":"IPV4","grid_primary": [{"name": config.grid1_master_fqdn,"stealth": False}]}
    response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(zone2), grid_vip=master_ip)

    zone3 = {"fqdn":"7777::/64","view":"default","zone_format":"IPV6","grid_primary": [{"name": config.grid1_master_fqdn,"stealth": False}]}
    response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(zone3), grid_vip=master_ip)

    #Restarting 
    print_and_log("Restaring DNS Service")
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices")
    sleep(60)

    print_and_log("Performing Query using Queryperf")
#   fp=os.popen("/usr/bin/queryperf -s "+config.grid_member1_vip+" -d ib_data/DNS_Query/Top_DNS_NXDOMAIN_NOERROR/queryperf.txt")
    #fp=os.popen("/usr/bin/queryperf/queryperf -s "+config.grid_vip+" -d ib_data/DNS_Query/Top_DNS_NXDOMAIN_NOERROR/queryperf.txt")
#    fp=os.popen("dduq -i 10.35.132.6 -f ~/API_Automation_08_12_20/WAPI_PyTest/Reporting_FR/ib_data/DNS_Query/Top_DNS_NXDOMAIN_NOERROR/queryperf.txt")
#    logger.info("%s",''.join(fp.readlines()))

    #Cleanup 
    print_and_log("Cleanup deleting added zones")
    del_zone = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn~=dns_top_nxdomain_or_noerror.com", grid_vip=master_ip)
    ref = json.loads(del_zone)[0]['_ref']
    del_status = ib_NIOS.wapi_request('DELETE', object_type = ref, grid_vip=master_ip)

    del_zone = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn~=57.0.0.0/8", grid_vip=master_ip)
    ref = json.loads(del_zone)[0]['_ref']
    del_status = ib_NIOS.wapi_request('DELETE', object_type = ref, grid_vip=master_ip)

    del_zone = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn~=7777::/64", grid_vip=master_ip)
    ref = json.loads(del_zone)[0]['_ref']
    del_status = ib_NIOS.wapi_request('DELETE', object_type = ref, grid_vip=master_ip)

    #Restarting
    print_and_log("Restaring DNS Service")
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(60)






#DHCP Functions
def dhcp_test_network_leases(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    # Add ipv4 Network
    print_and_log("Add Network '10.0.0.0/8' with Grid master as Member assignment")
    network1 = {"network":"10.0.0.0/8","network_view":"default","members":[{"name":master_fqdn,"_struct": "dhcpmember"}],"options":[{"name": "dhcp-lease-time","value": "74390400"}]}
    network1_response = ib_NIOS.wapi_request('POST', object_type="network", fields=json.dumps(network1), grid_vip=master_ip)
    network1_get = ib_NIOS.wapi_request('GET', object_type="network?network=10.0.0.0/8", grid_vip=master_ip)
    network1_ref = json.loads(network1_get)[0]['_ref']
    print(network1_ref)

    # Add ipv6 Network
    print_and_log("Add ipv6 Network '2001:550:40a:2500::/64' with Grid master as Member assignment")
    network2 = {"network": "2001:550:40a:2500::/64","network_view":"default","members":[{"name":master_fqdn,"_struct": "dhcpmember"}],"options":[{"name": "dhcp-lease-time","value": "74390400"}]}
    network2_response = ib_NIOS.wapi_request('POST', object_type="ipv6network", fields=json.dumps(network2), grid_vip=master_ip)
    network2_get = ib_NIOS.wapi_request('GET', object_type="ipv6network", grid_vip=master_ip)
    network2_ref = json.loads(network2_get)[0]['_ref']
    print(network2_ref)

    # Add range in 10.0.0.0/8
    print_and_log("Add Range '10.0.0.1 - 10.9.255.255' in '10.0.0.0/8' with Grid master as Member assignment")
    range = {"network":"10.0.0.0/8","network_view":"default","member":{"_struct": "dhcpmember","name":master_fqdn},"start_addr":"10.0.0.1","end_addr":"10.9.255.255"}
    range_response = ib_NIOS.wapi_request('POST', object_type="range", fields=json.dumps(range), grid_vip=master_ip)
    print(range_response)

    # Add range in 2001:550:40a:2500::/64
    print_and_log("Add Range '2001:550:40a:2500::1111 - 2001:550:40a:2500::5555' in '2001:550:40a:2500::/64' with Grid master as Member assignment")
    range = {"network":"2001:550:40a:2500::/64","network_view":"default","member":{"_struct": "dhcpmember","name":master_fqdn},"start_addr":"2001:550:40a:2500::1111","end_addr":"2001:550:40a:2500::5555"}
    range_response = ib_NIOS.wapi_request('POST', object_type="ipv6range", fields=json.dumps(range), grid_vip=master_ip)
    print(range_response)

    # Restart Services
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(60)

# Requesting 200 Leases
    #cmd1 = os.system("sudo /import/tools/qa/tools/dras/dras  -n 10 -i "+master_ip)
    #print(cmd1)
    #cmd2 = os.system("sudo /import/tools/qa/tools/dras6/dras6  -n 10 -i "+config.grid_ipv6+" -A")
    #print(cmd2)



def dhcp_test_fingerprint(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    #Network View
    network_view = {"name":"network_view_dhcp"}
    response = ib_NIOS.wapi_request('POST', object_type="networkview", fields=json.dumps(network_view), grid_vip=master_ip)
    print(response)
    # Add Network
    #data = {"members":[{"_struct": "dhcpmember", "ipv4addr":config.grid1_member3_vip,"name":config.grid1_member3_fqdn}], \
    # "network": "10.0.0.0/8", "network_view": "network_view_dhcp"}
    #response = ib_NIOS.wapi_request('POST', object_type="network", fields=json.dumps(data), grid_vip=master_ip)
    #print(response)
    data = {"members":[{"_struct": "dhcpmember", "ipv4addr":config.grid1_member3_vip,"name":config.grid1_member3_fqdn}], \
     "network": "51.0.0.0/24", "network_view": "network_view_dhcp"}
    response = ib_NIOS.wapi_request('POST', object_type="network", fields=json.dumps(data), grid_vip=master_ip)
    print(response)
    #Add Range
    range_obj = {"start_addr":"51.0.0.1","end_addr":"51.0.0.100","member":{"_struct": "dhcpmember","ipv4addr":config.grid1_member3_vip, \
     "name":config.grid1_member3_fqdn},"network_view":"network_view_dhcp", \
     "options":[{"_struct": "dhcpoption","name":"dhcp-lease-time","num": 51,"use_option": True,"value": "300","vendor_class": "DHCP"}]}
    range = ib_NIOS.wapi_request('POST', object_type="range", fields=json.dumps(range_obj), grid_vip=master_ip)
    print(range)

    range_obj = {"start_addr":"10.0.0.1","end_addr":"10.0.0.100","member":{"_struct": "dhcpmember","ipv4addr":config.grid1_member3_vip, \
     "name":config.grid1_member3_fqdn},"network_view":"network_view_dhcp", \
     "options":[{"_struct": "dhcpoption","name":"dhcp-lease-time","num": 51,"use_option": True,"value": "300","vendor_class": "DHCP"}]}
    range = ib_NIOS.wapi_request('POST', object_type="range", fields=json.dumps(range_obj), grid_vip=master_ip)
    print(range)

    # Add Shared network
    network_ref_list=[]
    network_10 = ib_NIOS.wapi_request('GET', object_type="network?network=10.0.0.0/8", grid_vip=master_ip)
    print(network_10)
    ref_10 = json.loads(network_10)[0]['_ref']
    network_ref_list.append({"_ref":ref_10})
    network_51 = ib_NIOS.wapi_request('GET', object_type="network?network=51.0.0.0/24", grid_vip=master_ip)
    print(network_10)
    ref_51 = json.loads(network_51)[0]['_ref']
    network_ref_list.append({"_ref":ref_51})
    shared_obj={"name":"sharednetworks","networks":network_ref_list,"network_view":"network_view_dhcp"}
    shared1 = ib_NIOS.wapi_request('POST',object_type="sharednetwork",fields=json.dumps(shared_obj), grid_vip=master_ip)
    print(shared1)

    #Restarting
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(160)

    # Generate Requested leases for Device Trend, Device Class Trend, Top Device Class Identified, Fingerprint Name Change Detected and (Voip Phones/Adapters)
    #cmd=os.popen("sudo /import/tools/qa/tools/dras_opt55/dras -i "+config.grid1_member3_vip+" -n 10 -w -D -O 55:0103060c0f2a424378")
    #fp=os.popen("sudo /import/tools/qa/tools/dras/dras -i "+master_ip+" -n 20 -x l=20.0.0.0")
    #print_and_log("%s", ''.join( cmd.readlines()))
    #sleep(10)
    # Switches
    #cmd1=os.popen("sudo /import/tools/qa/tools/dras_opt55/dras -i "+config.grid1_member3_vip+" -n 10 -w -D -O 55:0103060f1B")
    #print_and_log("%s", ''.join( cmd1.readlines()))
    #sleep(30)
    # Apple Airport  ( Device Fingerprint Name Change Detected Report )
    #cmd2=os.popen("sudo /import/tools/qa/tools/dras_opt55/dras -i "+config.grid1_member3_vip+" -n 1 -w -D -O 55:1c03060f -a  aa:11:bb:22:cc:33")
    #print_and_log("%s", ''.join( cmd2.readlines()))
    #sleep(180)
    # AP Meraki
    #cmd3=os.popen("sudo /import/tools/qa/tools/dras_opt55/dras -i "+config.grid1_member3_vip+" -n 1 -w -D -O 55:0103060c0f1a1c28292a -a aa:11:bb:22:cc:33")
    #cmd3=os.popen("sudo /import/tools/qa/tools/dras_opt55/dras -i "+config.grid1_member3_vip+" -n 1 -w -D -O  55:0103060f0c13 -a aa:11:bb:22:cc:33")
    #print_and_log("%s", ''.join( cmd3.readlines()))

    # Add Fingerprint Filter to Generate lease for DHCP TOP DEVICE Denied IP Address
    fingerprint_data = {"name":"fingerprint_filter","fingerprint":["Alps Electric"]}
    shared = ib_NIOS.wapi_request('POST', object_type="filterfingerprint", fields=json.dumps(fingerprint_data), grid_vip=master_ip)

    # Modify DHCP Range 51.0.0.1 to 51.0.0.100 Fingerprint Filter in Range.
    get_range = ib_NIOS.wapi_request('GET', object_type="range?start_addr~=51.0.0.1", grid_vip=master_ip)
    ref_range = json.loads(get_range)[0]['_ref']
    modify_range={"fingerprint_filter_rules":[{"filter": "fingerprint_filter","permission": "Deny"}]}
    modify_filter = ib_NIOS.wapi_request('PUT',object_type=ref_range,fields=json.dumps(modify_range), grid_vip=master_ip)

    #Restarting
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(160)
    
    # Alps Electric For DHCP TOP DEVICE Denied IP Address
    #cmd4=os.popen("sudo /import/tools/qa/tools/dras_opt55/dras -i "+config.grid1_member3_vip+" -n 1 -w -D -O 55:010304060f")
    #print_and_log("%s", ''.join( cmd4.readlines()))
    sleep(30)
    #Restarting
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)
    sleep(180)

    # Delete Shared Network
    delshared = ib_NIOS.wapi_request('GET', object_type="sharednetwork?name~=sharednetworks", grid_vip=master_ip)
    ref = json.loads(delshared)[0]['_ref']
    del_status = ib_NIOS.wapi_request('DELETE', object_type = ref, grid_vip=master_ip)

    # Delete and Disable Networks
    delnetwork = ib_NIOS.wapi_request('GET', object_type="network?network~=10.0.0.0/8", grid_vip=master_ip)
    ref = json.loads(delnetwork)[0]['_ref']
    del_status = ib_NIOS.wapi_request('DELETE', object_type = ref, grid_vip=master_ip)
    delnetwork = ib_NIOS.wapi_request('GET', object_type="network?network~=51.0.0.0/24", grid_vip=master_ip)
    ref_51 = json.loads(delnetwork)[0]['_ref']
    data = {"disable":True}
    del_status = ib_NIOS.wapi_request('PUT',object_type=ref_51,fields=json.dumps(data), grid_vip=master_ip)


def dhcp_test_usage(master_ip=config.grid_vip, master_fqdn=config.grid1_master_fqdn):
    #MAC Filter
    mac_filter = {"name":"mac1"}
    response = ib_NIOS.wapi_request('POST', object_type="filtermac", fields=json.dumps(mac_filter), grid_vip=master_ip)

    mac_filter_2 = {"name":"mac2"}
    response = ib_NIOS.wapi_request('POST', object_type="filtermac", fields=json.dumps(mac_filter_2), grid_vip=master_ip)

    # MAC Filter Address
    mac_filter_address_1 = {"filter":"mac1","mac":"11:22:33:44:55:66"}
    response = ib_NIOS.wapi_request('POST', object_type="macfilteraddress", fields=json.dumps(mac_filter_address_1), grid_vip=master_ip)

    mac_filter_address_2 = {"filter":"mac2","mac":"99:66:33:88:55:22"}
    response = ib_NIOS.wapi_request('POST', object_type="macfilteraddress", fields=json.dumps(mac_filter_address_2), grid_vip=master_ip)

    #Network View
    network_view = {"name":"custom_view_1"}
    response = ib_NIOS.wapi_request('POST', object_type="networkview", fields=json.dumps(network_view), grid_vip=master_ip)

    #Add Network
    network_data = {"members":[{"_struct": "dhcpmember", "ipv4addr": config.grid1_member2_vip,"name":config.grid1_member2_fqdn}], \
                    "network":"10.0.0.0/8","network_view":"custom_view_1"}
    response = ib_NIOS.wapi_request('POST', object_type="network", fields=json.dumps(network_data), grid_vip=master_ip)

    network_data_30 = {"members":[{"_struct": "dhcpmember", "ipv4addr": config.grid1_member2_vip,"name":config.grid1_member2_fqdn}], \
                       "network":"30.0.0.0/24","network_view":"custom_view_1"}
    response = ib_NIOS.wapi_request('POST', object_type="network", fields=json.dumps(network_data_30), grid_vip=master_ip)

    network_data_32 = {"members":[{"_struct": "dhcpmember", "ipv4addr": config.grid1_member2_vip,"name":config.grid1_member2_fqdn}],\
                        "network":"32.0.0.0/24","network_view":"custom_view_1"}
    response = ib_NIOS.wapi_request('POST', object_type="network", fields=json.dumps(network_data_32), grid_vip=master_ip)
    #Add Range

    range_obj = {"start_addr":"10.0.0.1","end_addr":"10.0.0.50","network_view":"custom_view_1","member":{"_struct": "dhcpmember", \
    "ipv4addr":config.grid1_member2_vip,"name": config.grid1_member2_fqdn},"mac_filter_rules":[{"filter": "mac1","permission": "Allow"}]}
    range = ib_NIOS.wapi_request('POST', object_type="range", fields=json.dumps(range_obj), grid_vip=master_ip)


    range_obj = {"start_addr":"30.0.0.1","end_addr":"30.0.0.50","network_view":"custom_view_1","member":{"_struct": "dhcpmember", \
    "ipv4addr":config.grid1_member2_vip,"name": config.grid1_member2_fqdn},"mac_filter_rules":[{"filter": "mac1","permission": "Allow"}]}
    range = ib_NIOS.wapi_request('POST', object_type="range", fields=json.dumps(range_obj), grid_vip=master_ip)

    range_obj_25 = {"start_addr":"32.0.0.1","end_addr":"32.0.0.100","network_view":"custom_view_1","member":{"_struct": "dhcpmember", \
    "ipv4addr":config.grid1_member2_vip,"name": config.grid1_member2_fqdn},"mac_filter_rules":[{"filter": "mac2","permission": "Allow"}]}
    range = ib_NIOS.wapi_request('POST', object_type="range", fields=json.dumps(range_obj_25), grid_vip=master_ip)

    #Add Fixed Address
    fixed_address = {"ipv4addr":"30.0.0.32","mac":"88:55:22:99:66:33","network_view":"custom_view_1"}
    response = ib_NIOS.wapi_request('POST', object_type="fixedaddress", fields=json.dumps(fixed_address), grid_vip=master_ip)

    fixed_address_2 = {"ipv4addr":"32.0.0.32","mac":"55:22:66:33:99:55","network_view":"custom_view_1"}
    response = ib_NIOS.wapi_request('POST', object_type="fixedaddress", fields=json.dumps(fixed_address_2), grid_vip=master_ip)


    # Add Shared Network
    network_ref_list = []
    network_10 = ib_NIOS.wapi_request('GET', object_type="network?network=10.0.0.0/8", grid_vip=master_ip)
    print(network_10)
    ref10 = json.loads(network_10)[0]['_ref']
    network_ref_list.append({"_ref":ref10})
    network_30 = ib_NIOS.wapi_request('GET', object_type="network?network=30.0.0.0/24", grid_vip=master_ip)
    ref30 = json.loads(network_30)[0]['_ref']
    network_ref_list.append({"_ref":ref30})
    network_32 = ib_NIOS.wapi_request('GET', object_type="network?network=32.0.0.0/24", grid_vip=master_ip)
    ref32 = json.loads(network_32)[0]['_ref']
    network_ref_list.append({"_ref":ref32})

    range_obj = {"name":"shareddhcp","networks":network_ref_list,"network_view": "custom_view_1"}
    shared = ib_NIOS.wapi_request('POST', object_type="sharednetwork", fields=json.dumps(range_obj), grid_vip=master_ip)

    #Restarting
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)

    #sleep(120)

    #cmd9=os.popen("sudo /import/tools/qa/tools/dras/dras -i "+config.grid1_member2_vip+" -n 1 -a 11:22:33:44:55:66")
    #print_and_log("%s", ''.join( cmd9.readlines()))
    #sleep(30)

    #cmd10=os.popen("sudo /import/tools/qa/tools/dras/dras -i "+config.grid1_member2_vip+" -n 1 -x l=32.0.0.0 -a 99:66:33:88:55:22")
    #print_and_log("%s", ''.join( cmd10.readlines()))
    #sleep(10)


    #Restarting
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=master_ip)
    ref = json.loads(grid)[0]['_ref']
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus", grid_vip=master_ip)
    restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices", grid_vip=master_ip)

    #sleep(180)
    # Delete Network

    # Delete and Disable Networks
    del_network_10 = ib_NIOS.wapi_request('GET', object_type="network?network=10.0.0.0/8", grid_vip=master_ip)
    ref = json.loads(del_network_10)[0]['_ref']
    del_status = ib_NIOS.wapi_request('DELETE', object_type = ref, grid_vip=master_ip)

    disable_network = ib_NIOS.wapi_request('GET', object_type="network?network=30.0.0.0/24", grid_vip=master_ip)
    ref_30 = json.loads(disable_network)[0]['_ref']
    data = {"disable":True}
    del_status = ib_NIOS.wapi_request('PUT',object_type=ref_30,fields=json.dumps(data), grid_vip=master_ip)

    disable_network_32 = ib_NIOS.wapi_request('GET', object_type="network?network=32.0.0.0/24", grid_vip=master_ip)
    ref_32 = json.loads(disable_network_32)[0]['_ref']
    data = {"disable":True}
    del_status = ib_NIOS.wapi_request('PUT',object_type=ref_32,fields=json.dumps(data), grid_vip=master_ip)




#Test Cases
class RFE_4753_Scheduled_Group_GMC_Promotion(unittest.TestCase):

        @pytest.mark.run(order=1)
        def test_001_Validate_Default_GMC_Group(self):
                print_and_log("\n********** Validate whether only Default Group is available **********")
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcgroup")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
		count = len(res)
                print_and_log("Number of groups : " + str(count))
                groupname = res[0]["name"]
                print_and_log("Name of group : " + groupname)
                groupref = res[0]["_ref"]
                print_and_log("Id of group : " + groupref)
		#assert count == 1 and groupname == "Default" and groupref == group_ref_Default
		#Validate List of members in the group
                list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_Default)
		list_members = list_members.sort()
		print_and_log("List of members in of group ref : " + group_ref_Default + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
		expected_member_list = [config.grid1_master_fqdn, config.grid1_member1_fqdn, config.grid1_member2_fqdn, config.grid1_member3_fqdn, config.grid1_member4_fqdn, config.grid1_member5_fqdn]
		expected_member_list = expected_member_list.sort()
		print_and_log("expected_member_list: " + str(expected_member_list))
		print_and_log("actual_member_list: " + str(list_members))
		#assert len(expected_member_list) == len(list_members)
                #assert expected_member_list[0] == list_members[0]
		#assert expected_member_list[5] == list_members[5]
		assert expected_member_list == list_members
		print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=2)
        def test_002_Validate_Default_GMC_Group(self):
		test_case_title = "Test 101 Validate whether only Default Group is available"
                print_and_log_header(test_case_title)
                res = Get_GMC_Groups(); 
		print_and_log(res)
                count = Count_GMC_Groups(res); 
		print_and_log("Number of groups : " + str(count))
		group_name, group_ref = Get_GMC_Group_Name_and_Ref_using_index(res, index=0)
                print_and_log("Name of group : " + group_name); print_and_log("Ref of group : " + group_ref)
                assert count == 1 and group_name == "Default" and group_ref == group_ref_Default
                print_and_log_footer(test_case_title)

        @pytest.mark.run(order=3)
        def test_003_Validate_Default_GMC_Group_Details(self):
                print_and_log("\n********** Validate Default Group Details **********")
                Get_GroupRef_DefaultGroup()
		print_and_log("group_ref : " + group_ref)
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
		res = json.loads(get_data)
		print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
		print_and_log("Number of members in Default Group : " + str(count))
                assert count == 6
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=4)
        def test_004_Validate_Creation_of_GMC_Group(self):
                print_and_log("\n********** Validate Creation of Group **********")
                data = {"name":"gp1"}
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
		print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
		#assert res == "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
		assert res == group_ref_gp1
                #ToDo: Validate whether list of groups has 2 groups
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=5)
        def test_005_Validate_DefaultTime_of_GMC_Group_with_members(self):
                expected_schedule_time = get_current_epoch_time()
	        expected_schedule_time_1 = subtract_minutes_to_epoch_time(expected_schedule_time, (2*60))
	        expected_schedule_time_2 = add_minutes_to_epoch_time(expected_schedule_time, (2*60))
		get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                gmc_promotion_policy = res["gmc_promotion_policy"]
                scheduled_time = res["scheduled_time"]
                assert scheduled_time >= expected_schedule_time_1 and scheduled_time <= expected_schedule_time_2
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=6)
        def test_006_Validate_Creation_of_GMC_Group_with_members(self):
                print_and_log("\n********** Validate Creation of Group with members **********")
                #config.grid1_member2_fqdn = gmc1.infoblox.com
		current_epoch_time = get_current_epoch_time()
                print_and_log("current time is " + str(current_epoch_time))
                schedule_group_time = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time))
                data = {"name":"gp2","gmc_promotion_policy": "SIMULTANEOUSLY","members": [{"member": config.grid1_member1_fqdn}, {"member": config.grid1_member2_fqdn}],"scheduled_time": schedule_group_time}
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == group_ref_gp2
		#Verify list of members in a group
                list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_gp2)
                print_and_log("List of members in of group ref : " + group_ref_gp2 + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_member1_fqdn, config.grid1_member2_fqdn]
                assert expected_member_list.sort() == list_members.sort()
		#Delete GMC group
                Delete_GMC_Group(group_ref_gp2)
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=7)
        def test_007_Validate_Creation_of_GMC_Group_with_Duplicate_members(self):
                print_and_log("\n********** Validate Creation of Group with members **********")
                #config.grid1_member1_fqdn = "vm-ha1.infoblox.com" 
		#config.grid1_member2_fqdn = "vm-sa1.infoblox.com"
		current_epoch_time = get_current_epoch_time()
                print_and_log("current time is " + str(current_epoch_time))
                schedule_group_time = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time))
                member1_fqdn = config.grid1_member1_fqdn
                member2_fqdn = config.grid1_member2_fqdn
                #data = {"members":[{"member": member1_fqdn}, {"member": member2_fqdn}]}
                data = {"name":"gp3","gmc_promotion_policy": "SIMULTANEOUSLY", "members":[{"member": member1_fqdn}, {"member": member1_fqdn}],"scheduled_time": schedule_group_time}
                #data = {"name":"gp3","gmc_promotion_policy": "SIMULTANEOUSLY", "members":[{"member": member1_fqdn}],"scheduled_time": schedule_group_time}
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"There are duplicate members in the GMC group. Remove the duplicates from the group.", errortext1)
                print_and_log("*********** Test Case Execution Completed **********")

        #Negative Test Case
        @pytest.mark.run(order=8)
        def test_008_Validate_Creation_of_Existing_GMC_Group_is_not_possible(self):
                test_case_title = "Test 004 Validate_Creation_of_Existing_GMC_Group_is_not_possible"
                print_and_log_header(test_case_title)
                data = {"name":"gp1"}
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"Duplicate object 'gp1' of type 'gmc_group' already exists in the database.", errortext1)
                print_and_log_footer(test_case_title)

        #Negative Test Case
        @pytest.mark.run(order=9)
        def test_009_Validate_Creation_of_Default_GMC_Group_is_not_possible(self):
                test_case_title = "Test 005 Validate_Creation_of_Default_GMC_Group_is_not_possible"
                print_and_log_header(test_case_title)
                data = {"name":"Default"}
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"Duplicate object 'Default' of type 'gmc_group' already exists in the database.", errortext1)
                print_and_log_footer(test_case_title)

        @pytest.mark.run(order=10)
        def test_010_Validate_Adding_Members_to_GMC_Group(self):
                print_and_log("\n********** Validate Addition of Members to GMC Group **********")
		#member_name = "vm-sa1.infoblox.com"
                #member_name = config.grid1_member2_fqdn
		data = 	{"members":[{"member": config.grid1_member1_fqdn}, {"member": config.grid1_member2_fqdn}]}
		#data = {"members":[{"member":"vm-sa1.infoblox.com"}]}
		print_and_log("member data :"+ str(data))
		get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
		print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
                assert res == group_ref_gp1
		# Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                assert count == 2
                #Validate member is moved out of default group as it is moved to new group
		list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_Default)
                print_and_log("List of members in of group ref : " + group_ref_Default + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_master_fqdn, config.grid1_member3_fqdn, config.grid1_member4_fqdn, config.grid1_member5_fqdn]
                assert expected_member_list.sort() == list_members.sort()
                #Validate memebers in the group
		list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_gp1)
                print_and_log("List of members in of group ref : " + group_ref_gp1 + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_member1_fqdn, config.grid1_member2_fqdn]
                assert expected_member_list[0] == list_members[0]["member"]
		assert expected_member_list[1] == list_members[1]["member"]
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=11)
        def test_011_Validate_Changing_order_of_Members_to_GMC_Group(self):
                print_and_log("\n********** Validate Changing Order of Members to GMC Group **********")
                data =  {"members":[{"member": config.grid1_member2_fqdn}, {"member": config.grid1_member1_fqdn}]}
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}]}
                print_and_log("member data :"+ str(data))
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
                assert res == group_ref_gp1
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                assert count == 2
                #Validate member is moved out of default group as it is moved to new group
                list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_Default)
                print_and_log("List of members in of group ref : " + group_ref_Default + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_master_fqdn, config.grid1_member3_fqdn, config.grid1_member4_fqdn, config.grid1_member5_fqdn]
                assert expected_member_list.sort() == list_members.sort()
                #Validate memebers in the group
                list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_gp1)
                print_and_log("List of members in of group ref : " + group_ref_gp1 + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_member2_fqdn, config.grid1_member1_fqdn]
                assert expected_member_list[0] == list_members[0]["member"]
                assert expected_member_list[1] == list_members[1]["member"]
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=12)
        def test_012_Validate_Changing_Policy_does_not_change_order_of_Members_to_GMC_Group(self):
                print_and_log("\n********** Validate Changing Policy does not change Order of Members to GMC Group **********")
                data =  {"gmc_promotion_policy": "SEQUENTIALLY"}
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}]}
                print_and_log("member data :"+ str(data))
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
                assert res == group_ref_gp1
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert data["gmc_promotion_policy"] == res["gmc_promotion_policy"]

                #Validate member is moved out of default group as it is moved to new group
                list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_Default)
                print_and_log("List of members in of group ref : " + group_ref_Default + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_master_fqdn, config.grid1_member3_fqdn, config.grid1_member4_fqdn, config.grid1_member5_fqdn]
                assert expected_member_list.sort() == list_members.sort()
                #Validate memebers in the group
                list_members = Get_jsonList_of_members_in_GMCGroup(group_ref_gp1)
                print_and_log("List of members in of group ref : " + group_ref_gp1 + " is " + str(list_members))
                #[{u'member': u'infoblox.localdomain'}, {u'member': u'gmc1.infoblox.com'}, {u'member': u'gmc2.infoblox.com'}]
                expected_member_list = [config.grid1_member2_fqdn, config.grid1_member1_fqdn]
                assert expected_member_list[0] == list_members[0]["member"]
                assert expected_member_list[1] == list_members[1]["member"]
                print_and_log("*********** Test Case Execution Completed **********")

        #@pytest.mark.run(order=11)
        def removedtest_011_Validate_Adding_GMC_to_Custom_GMC_Group_should_Fail(self):
                print_and_log("\n********** Validate Addition of GMC to Custom GMC Group Should Fail **********")
                # Add function to make a memebr GMC
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}, {"member":"gmc1.infoblox.com"}]}
                #member1_fqdn = "vm-sa1.infoblox.com"
                #member2_fqdn = "gmc1.infoblox.com"
                member1_fqdn = config.grid1_member1_fqdn
                member2_fqdn = config.grid1_member2_fqdn
                data = {"members":[{"member": member1_fqdn}, {"member": member2_fqdn}]}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"GMC members are not allowed in GMC promotion groups", errortext1)
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                assert count == 1
                #ToDo: Validate member is NOT moved out of default group as it is moved to new group
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=13)
        def test_013_Validate_Updating_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(self):
                print_and_log("\n********** Validate Updation of Scheduled Time and GMC Promotion Policy to GMC Group **********")
                #get scheduled time                
		current_epoch_time = get_current_epoch_time()
                print_and_log("current time is " + str(current_epoch_time))
                schedule_group_time_gp1 = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time_gp1))
		data = {"scheduled_time": schedule_group_time_gp1,"gmc_promotion_policy": "SEQUENTIALLY"}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == group_ref_gp1
		# Validate gmcpromotion and Scheduled Time is added to gp1 group [EXPECTED to FAIL as we have a bug]
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                gmc_promotion_policy = res["gmc_promotion_policy"]
                scheduled_time = res["scheduled_time"]
		#scheduled_time = add_minutes_to_epoch_time(scheduled_time, 8*60) # validate and log a bug
                print_and_log("gmc_promotion_policy is " + gmc_promotion_policy + "and scheduled_time is " + str(scheduled_time))
                assert gmc_promotion_policy == data["gmc_promotion_policy"]
		assert scheduled_time == data["scheduled_time"]
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=14)
        def test_014_Validate_GMC_PROMOTION_POLICY_of_Default_GMC_Group(self):
                # Validate gmcpromotion and Scheduled Time in Default Group [EXPECTED to FAIL as we have a bug]
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_Default+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                gmc_promotion_policy = res["gmc_promotion_policy"]
                assert gmc_promotion_policy == "SIMULTANEOUSLY"
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=15)
        def test_015_Validate_Updating_GMC_PROMOTION_POLICY_to_Default_GMC_Group(self):
                print_and_log("\n********** Validate Updation of GMC Promotion Policy to GMC Group **********")
                data = {"gmc_promotion_policy": "SEQUENTIALLY"}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_Default, fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"Upating promotion policy on Default group is not allowed", errortext1)
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=16)
        def test_016_Validate_Updating_SCHEDULED_TIME_to_Default_GMC_Group(self):
                print_and_log("\n********** Validate Updation of Scheduled Time to GMC Group **********")
		#get scheduled time                
                current_epoch_time = get_current_epoch_time()
                print_and_log("current time is " + str(current_epoch_time))
                schedule_group_time_gp1 = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time_gp1))
                data = {"scheduled_time": schedule_group_time_gp1}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_Default, fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"Upating scheduled time on default group is not allowed", errortext1)
                print_and_log("*********** Test Case Execution Completed **********")


	# GMC Schedule Object Testing
        @pytest.mark.run(order=17)
        def test_017_Getting_GMC_Schedule_Object(self):
                print_and_log("\n********** Validating GMC Schedule Object **********")
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
		gmcschedule_ref = res["_ref"]
                assert gmcschedule_ref == "gmcschedule/"+group_schedule_ref
                #ToDo: Validations for schedule
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=18)
        def test_018_Activating_GMC_Schedule(self):
                print_and_log("\n********** Activating GMC Schedule **********")
		data = {"activate_gmc_group_schedule": True}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
		assert res == "gmcschedule/"+group_schedule_ref
		# Validate GMC schedule is active
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                activate_status_gmcschedule = res["activate_gmc_group_schedule"]
                assert activate_status_gmcschedule == True
                #Deactivate schedule to bring back to base state
                data = {"activate_gmc_group_schedule": False}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcschedule/"+group_schedule_ref
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=19)
        def test_019_Activating_GMC_Schedule_as_nonsuperuser(self):
                print_and_log("\n********** Activating GMC Schedule as nonsuperuser **********")
		#non_super_user_group1_name = "non_super_group1"
		#non_super_user_group1_username1 = "ns_group1_user1"
		#non_super_user_group1_password1 = "infoblox"
		# Create non-super-user
		group_ref = create_nonsuperuser_group(non_super_user_group1_name)
		user_ref = create_nonsuperuser_user(non_super_user_group1_name, non_super_user_group1_username1, non_super_user_group1_password1)
	        print_and_log("Response is " + group_ref)
		non_super_user_group1_ref = group_ref
		#object_type_string = 'admingroup?name=' + non_super_user_group1_username1 
		#res = ib_NIOS.wapi_request('GET',object_type=object_type_string)
	        #res = json.loads(res)
                #print_and_log("res is " + str(res))
        	#ref1=res[0]['_ref']
                #print_and_log("nonsuperuser ref " + ref1)
		#Activate GMC schedule as non-super-user
                data = {"activate_gmc_group_schedule": True}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data), user=non_super_user_group1_username1, password=non_super_user_group1_password1)
                print_and_log("get_data is " + str(get_data))
                errortext1 = get_data[1]
                print_and_log("error text is " + errortext1)
                assert re.search(r"Access Denied", errortext1)
                #assert re.search(r"Only superusers are allowed to perform this operation on GMC Groups", errortext1)
		#assert res == "gmcschedule/"+group_schedule_ref
                """
		# Validate GMC schedule is active
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                activate_status_gmcschedule = res["activate_gmc_group_schedule"]
                assert activate_status_gmcschedule == True
                #Deactivate schedule to bring back to base state
                data = {"activate_gmc_group_schedule": False}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcschedule/"+group_schedule_ref
                print_and_log("*********** Test Case Execution Completed **********")
		"""

        @pytest.mark.run(order=20)
        def test_020_Activating_GMC_Schedule(self):
                object_type_string = 'admingroup?name=' + non_super_user_group1_name 
                #res = ib_NIOS.wapi_request('GET',object_type='admingroup?name=non_super_group1')
                res = ib_NIOS.wapi_request('GET',object_type=object_type_string)
                res = json.loads(res)
                print_and_log("res is " + str(res))
                ref1=res[0]['_ref']
                print_and_log("nonsuperuser ref " + ref1)

        @pytest.mark.run(order=21)
    	def test_021_Making_normal_member_as_GMC(self):
        	print_and_log("\n********** Making Normal Member as GMC  **********")
		# get members of a ref and ref of member 1
		master_vip = config.grid1_master_vip 
		#master_vip = "10.35.151.10"
		print_and_log("grid_master_vip is " + master_vip)
        	#get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=config.grid_vip)
		get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=master_vip)
        	print_and_log(get_ref)
		ref1 = json.loads(get_ref)[5]['_ref'] # ref for member5
		print_and_log("grid_member 1 ref is " + ref1)
		# make member 5 master candidate
                member_vip = config.grid1_member5_fqdn
		#member_vip = "10.20.0.20"
		data1 = {"master_candidate": True}
        	#output1 = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data1),grid_vip=config.grid_vip)
        	response = ib_NIOS.wapi_request('PUT',ref=ref1, fields=json.dumps(data1), grid_vip=master_vip)
        	print_and_log(response)
		if type(response) == tuple:
                	if response[0]==200:
                    		print("Success: set master candidate to true for member")
                    		assert True
                	else:
                    		print("Failure: Can't set master candidate to true for member")
                    		assert False
            	elif "member" in response:
                	print("Success: set master candidate to true for member")
                	assert True
        	#sleep(600)
        	print("-----------Test Case Execution Completed------------")

        #Negative Test Case
        @pytest.mark.run(order=22)
        def test_022_Validate_Adding_GMC_to_Custom_GMC_Group_should_Fail(self):
                print_and_log("\n********** Validate Addition of GMC to Custom GMC Group Should Fail **********")
                # Add function to make a memebr GMC
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}, {"member":"gmc1.infoblox.com"}]}
                #member1_fqdn = "vm-sa1.infoblox.com"
                #member2_fqdn = "gmc1.infoblox.com"
                member1_fqdn = config.grid1_member5_fqdn
                #member2_fqdn = config.grid1_member2_fqdn
                data = {"members":[{"member": member1_fqdn}]}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"GMC members are not allowed in GMC promotion groups", errortext1)
                """
		# Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                assert count == 1
                #ToDo: Validate member is NOT moved out of default group as it is moved to new group
                print_and_log("*********** Test Case Execution Completed **********")
                """

        #Negative Test Case
        @pytest.mark.run(order=23)
        def test_023_Validate_Adding_GM_to_Custom_GMC_Group_should_Fail(self):
                print_and_log("\n********** Validate Addition of GMC to Custom GMC Group Should Fail **********")
                member1_fqdn = config.grid1_master_fqdn
                #member2_fqdn = config.grid1_member2_fqdn
                data = {"members":[{"member": member1_fqdn}]}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"GMC is not allowed in GMC promotion groups", errortext1)
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                assert count == 1
                #ToDo: Validate member is NOT moved out of default group as it is moved to new group
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=24)
        def test_024_Validate_Deletion_of_GMC_Group(self):
                print_and_log("\n********** Validate Deletion of GMC Group **********")
                get_data = ib_NIOS.wapi_request('DELETE', object_type=""+group_ref_gp1)
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
                # Validate only Default Group exists and gp1 is deleted
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcgroup")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res)
                print_and_log("Number of groups : " + str(count))
                groupname = res[0]["name"]
                print_and_log("Name of group : " + groupname)
                groupref = res[0]["_ref"]
                print_and_log("Id of group : " + groupref)
                assert count == 1 and groupname == "Default" and groupref == "gmcgroup/b25lLmdtY19ncm91cCREZWZhdWx0:Default"
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=25)
        def test_025_Promote_GMC_as_GM(self):
                print_and_log("\n********** Promote GMC as GM **********")
		#promote_master(config.grid1_member2_vip)
		#check_able_to_login_appliances(config.grid1_member2_vip)
		#validate_status_GM_after_GMC_promotion(config.grid1_member2_vip)
		#master_vip = "10.35.160.6"
		#member_fqdn = "ib-10-35-157-14.infoblox.com"
		#member_vip = "10.35.157.14" 
		sleep(120)
		master_vip = config.grid_vip
		member_fqdn = config.grid1_member5_fqdn
		member_vip = config.grid1_member5_vip
		GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
		#sleep(120)
		promote_master(member_vip)
		check_able_to_login_appliances(member_vip)
		validate_status_GM_after_GMC_promotion(member_vip)
		sleep(600)

        @pytest.mark.run(order=26)
        def test_026_Promote_oldGM_back(self):
                print_and_log("\n********** Promote old GM back **********")
                #promote_master(config.grid1_member2_vip)
                #check_able_to_login_appliances(config.grid1_member2_vip)
                #validate_status_GM_after_GMC_promotion(config.grid1_member2_vip)
                #master_vip = "10.35.135.10"
                #member_fqdn = "ib-10-35-112-3.infoblox.com"
                #member_vip = "10.35.112.3" 
                #sleep(600)
		master_vip = config.grid1_member5_vip
                member_fqdn = config.grid1_master_fqdn
                member_vip = config.grid_vip
                GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                promote_master(member_vip)
                check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)
                sleep(600)

        @pytest.mark.run(order=27)
        def test_027_test_epoch_time(self):
		#sleep(620)
                print_and_log("\n********** Promote GMC as GM **********")
		current_epoch_time = get_current_epoch_time()
		print_and_log("current time is " + str(current_epoch_time))
                schedule_group_time = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time))

        @pytest.mark.run(order=28)
        def test_028_test_member_ips(self):
                print_and_log("\n********** Test config *********")
                #print_and_log("grid master ip " + str(grid_master_vip))
                #print_and_log("grid grid_member_fqdn " + str(grid_member_fqdn))
                #print_and_log("grid grid_member1_vip " + str(grid_member1_vip))
                #print_and_log("grid grid_member1_fqdn " + str(grid_member1_fqdn))
                print_and_log("grid config.grid1_member1_fqdn " + config.grid1_member1_fqdn)

	@pytest.mark.run(order=29)
        def test_029_Test_Setting_Schedule_for_GMC_Promotion(self):
                print_and_log("\n********** Test_Scheduled_GMC_Promotion *********")
                # Create Group gp1
                #config.grid1_member1_fqdn = "ib-10-35-196-6.infoblox.com"
		#config.grid1_member2_fqdn = "ib-10-35-193-14.infoblox.com"
		#config.grid1_member3_fqdn = "ib-10-34-19-254.infoblox.com"
                #config.grid1_member4_fqdn = "ib-offline.infoblox.com"

		group_ref_gp1 = Create_GMC_Group("gp1") #uncomment this
                data_gp1 = {"members":[{"member":config.grid1_member1_fqdn}, {"member":config.grid1_member2_fqdn}]}
                #data_gp1_json = json.dumps(data_gp1)
		print_and_log("Data is " + str(data_gp1))
                Add_Members_to_GMC_Group(group_ref_gp1, data_gp1)
                # Create Group gp2
                group_ref_gp2 = Create_GMC_Group("gp2") #uncomment this
                data_gp2 = {"members":[{"member":config.grid1_member3_fqdn}, {"member":config.grid1_member4_fqdn}]}
                Add_Members_to_GMC_Group(group_ref_gp2, data_gp2)

                current_epoch_time = get_current_epoch_time()
                print_and_log("current time is " + str(current_epoch_time))

                #set schedule time for gp1 
                schedule_group_time_gp1 = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time_gp1))
                Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref_gp1,schedule_group_time_gp1,"SEQUENTIALLY")  
  
                #set schedule time for gp2 
                schedule_group_time_gp2 = add_minutes_to_epoch_time(current_epoch_time, 15)
                print_and_log("current time + 15 minutes is " + str(schedule_group_time_gp2))
                Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref_gp2,schedule_group_time_gp2,"SIMULTANEOUSLY")  

        @pytest.mark.run(order=30)
        def test_030_Test_Max_allowed_Schedule_time(self):
                #set schedule time for gp2 after 8 hr and 15 minutes 
                schedule_group_time_gp2 = add_minutes_to_epoch_time(current_epoch_time, (8*60 +15))
                print_and_log("current time + 15 minutes is " + str(schedule_group_time_gp2))
                #Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref_gp1,schedule_group_time_gp2,"SIMULTANEOUSLY")
		group_ref = group_ref_gp1
		data = {"scheduled_time": schedule_group_time_gp2, "gmc_promotion_policy": "SIMULTANEOUSLY"}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == group_ref
                # Validate gmcpromotion and Scheduled Time is added to gp1 group [EXPECTED to FAIL as we have a bug]
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                gmc_promotion_policy = res["gmc_promotion_policy"]
                scheduled_time = res["scheduled_time"]
                print_and_log("gmc_policy and schedule time are :" + gmc_promotion_policy + " and  " + str(scheduled_time))
                assert gmc_promotion_policy == data["gmc_promotion_policy"] and scheduled_time != data["scheduled_time"]
                print_and_log("*********** Function Execution Completed **********")
                
		#reset schedule time for gp2 
                schedule_group_time_gp2 = add_minutes_to_epoch_time(current_epoch_time, 15)
                print_and_log("current time + 15 minutes is " + str(schedule_group_time_gp2))
                Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref_gp1,schedule_group_time_gp2,"SIMULTANEOUSLY")

        @pytest.mark.run(order=31)
        def test_031_Test_Scheduled_GMC_Promotion(self):
                # Activate GMC group schedule
                Activate_GMC_Schedule()        

		#config.grid_vip = "10.35.135.10"
                #config.member5_fqdn = "ib-10-35-112-3.infoblox.com"
                #config.grid_member5_vip = "10.35.112.3" 
                
		# Promote Master
                sleep(120)
                master_vip = config.grid1_master_vip
                member_fqdn = config.grid1_member5_fqdn
                member_vip = config.grid1_member5_vip
                GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                sleep(180)
		promote_master_new(member_vip)
                check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)
                sleep(1200)

	#@pytest.mark.run(order=32)
        def remove_test_032_Promote_oldGM_back(self):
                print_and_log("\n********** Promote old GM back **********")
                join_now(group_ref_gp1, config.grid1_member5_vip)
		join_now(group_ref_gp2, config.grid1_member5_vip)
		sleep(600)
		#Deactivate_GMC_Schedule(config.grid_member5_vip)
		#master_vip = config.grid_member5_vip
                #member_fqdn = config.grid_fqdn
                #member_vip = config.grid_vip
                #GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                #promote_master(member_vip)
                #check_able_to_login_appliances(member_vip)
                #validate_status_GM_after_GMC_promotion(member_vip)

        @pytest.mark.run(order=33)
        def test_033_Validate_Members_in_GMCGroup_After_Promotion(self):
		"""
		temp_grid1_session_ip = config.grid1_session_ip
		temp_grid1_master_vip = config.grid1_master_vip
		temp_grid1_master_fqdn = config.grid1_master_fqdn
		temp_grid1_master_mgmt_vip = config.grid1_master_mgmt_vip
		temp_grid1_master_id = config.grid1_master_id
		temp_grid1_master_ipv6 = config.grid1_master_ipv6
		temp_grid1_master_mgmt_vip6 = config.grid1_master_mgmt_vip6

		config.grid1_session_ip=config.grid1_member5_vip
		config.grid1_master_vip=config.grid1_member5_vip
		config.grid1_master_fqdn=config.grid1_member5_fqdn
		config.grid1_master_mgmt_vip=config.grid1_member5_mgmt_ip
		config.grid1_master_id=config.grid1_member5_id
		config.grid1_master_ipv6=config.grid1_member5_ipv6
		config.grid1_master_mgmt_vip6=config.grid1_member5_mgmt_ipv6

                config.grid1_member5_vip=temp_grid1_master_vip
		config.grid1_member5_fqdn=temp_grid1_master_fqdn
		config.grid1_member5_id=temp_grid1_master_id
		config.grid1_member5_ipv6=temp_grid1_master_ipv6
		config.grid1_member5_mgmt_ip=temp_grid1_master_mgmt_vip
		config.grid1_member5_mgmt_ipv6=temp_grid1_master_mgmt_vip6		
		"""
                
		#config.grid_vip = config.grid1_member5_vip
		#GRIDVIP = config.grid1_member5_vip
		#USERNAME = config.username
		#PASSWORD = config.password

		print_and_log("New Grid VIP is " + config.grid_vip)
		print_and_log("New master is config.grid1_member5_vip " + config.grid1_member5_vip + " Old master is config.grid1_master_vip " + config.grid1_master_vip)
		groups_info = Get_GMC_Groups(config.grid1_member5_vip)
                print_and_log("groups " + str(groups_info))
                
                #Validate members in gmc groups
                count_members_gp1 = Get_Count_of_members_in_GMCGroup(group_ref_gp1, config.grid1_member5_vip)
                assert count_members_gp1 == 2
                count_members_gp2 = Get_Count_of_members_in_GMCGroup(group_ref_gp2, config.grid1_member5_vip)
                assert count_members_gp2 == 2
                count_members_Default = Get_Count_of_members_in_GMCGroup(group_ref_Default, config.grid1_member5_vip)
                assert count_members_Default == 2
                

        @pytest.mark.run(order=34)
        def test_034_Validate_GMCSchedule_Deactivated_after_promotion_After_Promotion(self):
                #Validate schedule status
                assert Get_GMC_Schedule_Activation_Status(config.grid1_member5_vip) == True


        @pytest.mark.run(order=35)
        def test_035_test_dns_zone_arecords(self):
                dns_test_zone_arecords(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=36)
        def test_036_test_dns_zone_allrecords_restart_simultaneously(self):
                dns_test_zone_allrecords_restart_simultaneously(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=37)
        def test_037_test_dns_recursive_queries(self):
                dns_test_recursive_queries(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=38)
        def test_038_test_dns_nxdomain_noerror(self):
		dns_test_nxdomain_noerror(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=39)
        def test_039_test_dhcp_network_leases(self):
		dhcp_test_network_leases(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=40)
        def test_040_test_dhcp_fingerprint(self):
		dhcp_test_fingerprint(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=41)
        def test_041_test_dhcp_usage(self):
		dhcp_test_usage(config.grid1_member5_vip, config.grid1_member5_fqdn)

        @pytest.mark.run(order=42)
        def test_042_backup(self):
                grid_backup(config.grid1_member5_vip)

        @pytest.mark.run(order=43)
        def test_043_restore(self):
                grid_restore(config.grid1_member5_vip)
                sleep(240)

        @pytest.mark.run(order=44)
        def test_044_Test_Setting_Schedule_for_GMC_Promotion(self):
                print_and_log("\n********** Test_Scheduled_GMC_Promotion *********")
                # Create Group gp1
                #config.grid1_member1_fqdn = "ib-10-35-196-6.infoblox.com"
                #config.grid1_member2_fqdn = "ib-10-35-193-14.infoblox.com"
                #config.grid1_member3_fqdn = "ib-10-34-19-254.infoblox.com"
                #config.grid1_member4_fqdn = "ib-offline.infoblox.com"
                
		#Deactivate_GMC_Schedule(config.grid1_member5_vip)
                #Delete_GMC_Group(group_ref_gp1, config.grid1_member5_vip)
                #Delete_GMC_Group(group_ref_gp2, config.grid1_member5_vip)   

                #group_ref_gp1 = Create_GMC_Group("gp1", config.grid1_member5_vip) #uncomment this
                data_gp1 = {"members":[{"member":config.grid1_member1_fqdn}, {"member":config.grid1_member2_fqdn}]}
                #data_gp1_json = json.dumps(data_gp1)
                print_and_log("Data is " + str(data_gp1))
                Add_Members_to_GMC_Group(group_ref_gp1, data_gp1, config.grid1_member5_vip)
                # Create Group gp2
                #group_ref_gp2 = Create_GMC_Group("gp2", config.grid1_member5_vip) #uncomment this
                data_gp2 = {"members":[{"member":config.grid1_member3_fqdn}, {"member":config.grid1_member4_fqdn}]}
                Add_Members_to_GMC_Group(group_ref_gp2, data_gp2, config.grid1_member5_vip)

                current_epoch_time = get_current_epoch_time()
                print_and_log("current time is " + str(current_epoch_time))

                #set schedule time for gp1 
                schedule_group_time_gp1 = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time_gp1))
                Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref_gp1,schedule_group_time_gp1,"SEQUENTIALLY", config.grid1_member5_vip)

                #set schedule time for gp2 
                schedule_group_time_gp2 = add_minutes_to_epoch_time(current_epoch_time, 15)
                print_and_log("current time + 15 minutes is " + str(schedule_group_time_gp2))
                Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref_gp2,schedule_group_time_gp2,"SIMULTANEOUSLY", config.grid1_member5_vip)

        @pytest.mark.run(order=45)
	def test_045_Test_Scheduled_GMC_Promotion(self):
                # Activate GMC group schedule
                #Activate_GMC_Schedule(config.grid1_member5_vip)

                #config.grid_vip = "10.35.135.10"
                #config.member5_fqdn = "ib-10-35-112-3.infoblox.com"
                #config.grid_member5_vip = "10.35.112.3" 

                # Promote Master
                master_vip = config.grid1_member5_vip
                member_fqdn = config.grid1_master_fqdn
                member_vip = config.grid1_master_vip
                #GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                Poweroff_the_member(config.grid1_member3_id)
		sleep(60)
		promote_master_new(member_vip)
                sleep(1200)
                join_now(group_ref_gp2, member_vip)
                sleep(300)
		check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)
"""
        @pytest.mark.run(order=138)
        def test_138_Promote_oldGM_back(self):
                print_and_log("\n********** Promote old GM back **********")
                master_vip = config.grid1_member5_vip
                member_fqdn = config.grid_fqdn
                member_vip = config.grid_vip
                GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                promote_master(member_vip)
                check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)
"""

