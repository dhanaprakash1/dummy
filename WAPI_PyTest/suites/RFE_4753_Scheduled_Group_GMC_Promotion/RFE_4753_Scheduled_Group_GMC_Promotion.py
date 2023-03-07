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
group_ref_Default = "gmcgroup/b25lLmdtY19ncm91cCREZWZhdWx0:Default"; global group_ref_Default
group_ref_gp1 = "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"; global group_ref_gp1
group_ref_gp2 = "gmcgroup/b25lLmdtY19ncm91cCRncDI:gp2"; global group_ref_gp2
group_schedule_ref = "b25lLmdtY19zY2hlZHVsZV9ncm91cCQw"; global group_schedule_ref
current_epoch_time = 0; global current_epoch_time


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
def Get_GMC_Groups(objectname):
        print_and_log("Get GMC groups in the grid")
	get_data = ib_NIOS.wapi_request('GET', object_type="gmcgroup")
	gmc_groups = json.loads(get_data)
	return gmc_groups
	print_and_log("GMC Groups in the grid are : " + gmc_groups)

def Count_GMC_Groups(objectname, local_gmc_groups):
	print_and_log("Count GMC groups in the grid")
        count = len(local_gmc_groups)
	return count	

def Get_GMC_Group_Name_and_Ref_using_index(objectname, local_gmc_groups, index):
	print_and_log("Print GMC group Names and Ref in the grid of given index : " + str(index))
	gmc_group = local_gmc_groups[index]
	group_name, group_ref = (gmc_group["name"], gmc_group["_ref"])
	print_and_log("GMC group Name is " +  group_name)
	print_and_log("GMC group Ref is " +  group_ref)
        return group_name, group_ref

def Get_GMC_Group_Name_and_Ref_using_Group_Name(objectname, local_gmc_groups, search_group_name):
        print_and_log("Print GMC group name and ref in the grid using given group name : " + str(index))
	for group_group in local_gmc_groups:
		group_name, group_ref = (gmc_group["name"], gmc_group["_ref"])
		if (group_name ==  search_group_name):
			return group_ref
		else:
			return "GroupNOTFound"

def Get_GroupRef_DefaultGroup(object_name):
        print_and_log("Get GroupRef of Default Group")
        get_data = ib_NIOS.wapi_request('GET', object_type="gmcgroup")
        res = json.loads(get_data)
	group_ref = res[0]["_ref"]
        global group_ref

def Create_GMC_Group(group_name):
        print_and_log("\n********** Function: Create_GMC_Group **********")
        data = {"name":group_name}
        get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
        print_and_log(get_data)
        group_ref = json.loads(get_data)
        print_and_log(group_ref)
        return group_ref

def Add_Members_to_GMC_Group(group_ref, data):
                print_and_log("\n********** Function: Validate Addition of Members to GMC Group **********")
                #member_name = "vm-sa1.infoblox.com"
                #member_name = config.grid1_member2_fqdn
                #data =  {"members":[{"member": member_name}]}
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}]}
                print_and_log("member data :"+ str(data))
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                #assert res == group_ref_gp1
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of memebrs in group : " + str(count))
                #assert count == 1
                #ToDo: Validate member is moved out of default group as it is moved to new group

def Get_GMC_Schedule_Activation_Status():
                # Get  GMC schedule 
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                activate_status_gmcschedule = res["activate_gmc_group_schedule"]
                return activate_status_gmcschedule
		#assert activate_status_gmcschedule == True


def Activate_GMC_Schedule():
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

def Deactivate_GMC_Schedule():
                print_and_log("\nFunction: ********** Activating GMC Schedule **********")
                data = {"activate_gmc_group_schedule": True}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcschedule/"+group_schedule_ref
                #Deactivate schedule to bring back to base state
                data = {"activate_gmc_group_schedule": False}
                get_data = ib_NIOS.wapi_request('PUT', object_type="gmcschedule/"+group_schedule_ref, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcschedule/"+group_schedule_ref
                print_and_log("*********** Function Execution Completed **********")


def Update_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(group_ref, schedule_time, gmc_promotion_policy):
                print_and_log("\n********** Function: Validate Updation of Scheduled Time and GMC Promotion Policy to GMC Group **********")
                #data = {"scheduled_time": 1675772044,"gmc_promotion_policy":"SEQUENTIALLY"}
                data = {"scheduled_time": schedule_time, "gmc_promotion_policy": gmc_promotion_policy}
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
                assert gmc_promotion_policy == data["gmc_promotion_policy"] and scheduled_time == data["scheduled_time"]
                print_and_log("*********** Function Execution Completed **********")

def Get_Count_of_members_in_GMCGroup(group_ref):
                # Validate member is added to gp1 group
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                count = len(res["members"])
                #ToDo: Validate list of members
                print_and_log("Number of groups : " + str(count))
                #assert count == 1
                return count
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
        # scheduled time expired
        #child1.expect('y or n')
        #child1.sendline('y')
        
        # disaster recovery feature confirmation
        child1.expect('y or n')
        child1.sendline('y')

        #child1.expect('Default: 30s')
        #child1.sendline('\n')
        #child1.expect('y or n')

        #child1.sendline('y\n')

        #child1.expect('y or n')
        #child1.sendline('y\n')

        #child1.expect('y or n')
        #child1.sendline('y\n')

        sleep(120)
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
            print_and_log("Success: this member become GMC after the promotion")
            assert True
        else:
            print_and_log("Failure: this member did not become GMC after the promotion")
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


def get_current_epoch_time():
    print_and_log("Function: get_current_epoch_time")
    current_epoch_time = int(time.time())
    return current_epoch_time

def add_minutes_to_epoch_time(epoch_time, minutes_to_add):
    print_and_log("Function: add_minutes_to_epoch_time")
    return int(epoch_time + (minutes_to_add * 60))


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
		assert count == 1 and groupname == "Default" and groupref == "gmcgroup/b25lLmdtY19ncm91cCREZWZhdWx0:Default"
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=101)
        def test_101_Validate_Default_GMC_Group(self):
		test_case_title = "Test 101 Validate whether only Default Group is available"
                print_and_log_header(test_case_title)
                res = Get_GMC_Groups(self); 
		print_and_log(res)
                count = Count_GMC_Groups(self, res); 
		print_and_log("Number of groups : " + str(count))
		group_name, group_ref = Get_GMC_Group_Name_and_Ref_using_index(self, res, index=0)
                print_and_log("Name of group : " + group_name); print_and_log("Ref of group : " + group_ref)
                assert count == 1 and group_name == "Default" and group_ref == group_ref_Default
                print_and_log_footer(test_case_title)

        @pytest.mark.run(order=2)
        def test_002_Validate_Default_GMC_Group_Details(self):
                print_and_log("\n********** Validate Default Group Details **********")
                Get_GroupRef_DefaultGroup(self)
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

        @pytest.mark.run(order=3)
        def test_003_Validate_Creation_of_GMC_Group(self):
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
        def test_005_Validate_Creation_of_Default_GMC_Group_is_not_possible(self):
                test_case_title = "Test 005 Validate_Creation_of_Default_GMC_Group_is_not_possible"
                print_and_log_header(test_case_title)
                data = {"name":"Default"}
                get_data = ib_NIOS.wapi_request('POST', object_type="gmcgroup", fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"Duplicate object 'Default' of type 'gmc_group' already exists in the database.", errortext1)
                print_and_log_footer(test_case_title)

        @pytest.mark.run(order=6)
        def test_006_Validate_Adding_Members_to_GMC_Group(self):
                print_and_log("\n********** Validate Addition of Members to GMC Group **********")
		#member_name = "vm-sa1.infoblox.com"
                member_name = config.grid1_member2_fqdn
		data = 	{"members":[{"member": member_name}]}
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
                assert count == 1
                #ToDo: Validate member is moved out of default group as it is moved to new group
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=8)
        def test_008_Validate_Updating_SCHEDULED_TIME_and_GMC_PROMOTION_POLICY_to_GMC_Group(self):
                print_and_log("\n********** Validate Updation of Scheduled Time and GMC Promotion Policy to GMC Group **********")
                data = {"scheduled_time": 1675772044,"gmc_promotion_policy":"SEQUENTIALLY"}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                assert res == "gmcgroup/b25lLmdtY19ncm91cCRncDE:gp1"
		# Validate gmcpromotion and Scheduled Time is added to gp1 group [EXPECTED to FAIL as we have a bug]
                get_data = ib_NIOS.wapi_request('GET', object_type=""+group_ref_gp1+"?_return_fields=name,comment,gmc_promotion_policy,scheduled_time,members,time_zone")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
                gmc_promotion_policy = res["gmc_promotion_policy"]
                scheduled_time = res["scheduled_time"]
                assert gmc_promotion_policy == "SEQUENTIALLY" and scheduled_time == data["scheduled_time"]
                print_and_log("*********** Test Case Execution Completed **********")


	# GMC Schedule Object Testing
        @pytest.mark.run(order=10)
        def test_010_Getting_GMC_Schedule_Object(self):
                print_and_log("\n********** Validating GMC Schedule Object **********")
                get_data = ib_NIOS.wapi_request('GET', object_type="gmcschedule/"+group_schedule_ref+"?_return_fields=activate_gmc_group_schedule,gmc_groups")
                print_and_log(get_data)
                res = json.loads(get_data)
                print_and_log(res)
		gmcschedule_ref = res["_ref"]
                assert gmcschedule_ref == "gmcschedule/"+group_schedule_ref
                #ToDo: Validations for schedule
                print_and_log("*********** Test Case Execution Completed **********")

        @pytest.mark.run(order=11)
        def test_011_Activating_GMC_Schedule(self):
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

        @pytest.mark.run(order=12)
    	def test_012_Making_normal_member_as_GMC(self):
        	print_and_log("\n********** Making Normal Member as GMC  **********")
		# get members of a ref and ref of member 1
		#master_vip = config.grid1_master_vip 
		master_vip = "10.35.151.10"
		print_and_log("grid_master_vip is " + master_vip)
        	#get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=config.grid_vip)
		get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=master_vip)
        	print_and_log(get_ref)
		ref1 = json.loads(get_ref)[1]['_ref']
		print_and_log("grid_member 1 ref is " + ref1)
		# make member 1 master candidate
                #member_vip = config.grid1_member1_fqdn
		member_vip = "10.20.0.20"
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
        	print("-----------Test Case 10 Execution Completed------------")


        #Negative Test Case
        @pytest.mark.run(order=4)
        def test_004_Validate_Creation_of_Existing_GMC_Group_is_not_possible(self):
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
        @pytest.mark.run(order=13)
        def test_013_Validate_Adding_GMC_to_Custom_GMC_Group_should_Fail(self):
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

        #Negative Test Case
        @pytest.mark.run(order=14)
        def test_014_Validate_Adding_GM_to_Custom_GMC_Group_should_Fail(self):
                print_and_log("\n********** Validate Addition of GMC to Custom GMC Group Should Fail **********")
                # Add function to make a memebr GMC
                #data = {"members":[{"member":"vm-sa1.infoblox.com"}, {"member":"gmc1.infoblox.com"}]}
                #member1_fqdn = "vm-sa1.infoblox.com"
                #member2_fqdn = "gmc1.infoblox.com"
                member1_fqdn = config.grid_fqdn
                member2_fqdn = config.grid1_member2_fqdn
                data = {"members":[{"member": member1_fqdn}, {"member": member2_fqdn}]}
                get_data = ib_NIOS.wapi_request('PUT', object_type=""+group_ref_gp1, fields=json.dumps(data))
                print_and_log(get_data)
                errortext1 = get_data[1]
                print_and_log(errortext1)
                assert re.search(r"GM is not allowed in GMC promotion groups", errortext1)
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

        @pytest.mark.run(order=15)
        def test_015_Validate_Deletion_of_GMC_Group(self):
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

        @pytest.mark.run(order=16)
        def test_016_Promote_GMC_as_GM(self):
                print_and_log("\n********** Promote GMC as GM **********")
		#promote_master(config.grid1_member2_vip)
		#check_able_to_login_appliances(config.grid1_member2_vip)
		#validate_status_GM_after_GMC_promotion(config.grid1_member2_vip)
		#master_vip = "10.35.160.6"
		#member_fqdn = "ib-10-35-157-14.infoblox.com"
		#member_vip = "10.35.157.14" 
		master_vip = config.grid_vip
		member_fqdn = config.grid_member3_fqdn
		member_vip = config.grid_member3_vip
		GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
		promote_master(member_vip)
		check_able_to_login_appliances(member_vip)
		validate_status_GM_after_GMC_promotion(member_vip)

        @pytest.mark.run(order=17)
        def test_017_Promote_oldGM_back(self):
                print_and_log("\n********** Promote old GM back **********")
                #promote_master(config.grid1_member2_vip)
                #check_able_to_login_appliances(config.grid1_member2_vip)
                #validate_status_GM_after_GMC_promotion(config.grid1_member2_vip)
                #master_vip = "10.35.135.10"
                #member_fqdn = "ib-10-35-112-3.infoblox.com"
                #member_vip = "10.35.112.3" 
                master_vip = config.grid_member3_vip
                member_fqdn = config.grid_member_fqdn
                member_vip = config.grid_vip
                GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                promote_master(member_vip)
                check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)

        @pytest.mark.run(order=108)
        def test_108_test_epoch_time(self):
                print_and_log("\n********** Promote GMC as GM **********")
		current_epoch_time = get_current_epoch_time()
		print_and_log("current time is " + str(current_epoch_time))
                schedule_group_time = add_minutes_to_epoch_time(current_epoch_time, 10)
                print_and_log("current time + 10 minutes is " + str(schedule_group_time))

        @pytest.mark.run(order=109)
        def test_109_test_member_ips(self):
                print_and_log("\n********** Test config *********")
                #print_and_log("grid master ip " + str(grid_master_vip))
                #print_and_log("grid grid_member_fqdn " + str(grid_member_fqdn))
                #print_and_log("grid grid_member1_vip " + str(grid_member1_vip))
                #print_and_log("grid grid_member1_fqdn " + str(grid_member1_fqdn))
                print_and_log("grid config.grid1_member1_fqdn " + config.grid1_member1_fqdn)

	@pytest.mark.run(order=19)
        def test_019_Test_Setting_Schedule_for_GMC_Promotion(self):
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

        @pytest.mark.run(order=20)
        def test_020_Test_Max_allowed_Schedule_time(self):
                #set schedule time for gp2 after 8 hour 15 minutes 
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

        @pytest.mark.run(order=21)
        def test_021_Test_Scheduled_GMC_Promotion(self):
                # Activate GMC group schedule
                Activate_GMC_Schedule()        

		#config.grid_vip = "10.35.135.10"
                #config.member5_fqdn = "ib-10-35-112-3.infoblox.com"
                #config.grid_member5_vip = "10.35.112.3" 
                
		# Promote Master
                master_vip = config.grid_vip
                member_fqdn = config.member5_fqdn
                member_vip = config.grid_member5_vip
                GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                promote_master_new(member_vip)
                check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)
                #To Do: Validate Timestamps
                #To Do: validate scheduled time cannot be changed when promotion is in progress
                #To Do: validate memebr assignment  cannot be changed when promotion is in progress

        @pytest.mark.run(order=22)
        def test_022_Validate_Members_in_GMCGroup_After_Promotion(self):
                #Validate members in gmc groups
                count_members_gp1 = Get_Count_of_members_in_GMCGroup(group_ref_gp1)
                assert count_members_gp1 == 2
                count_members_gp2 = Get_Count_of_members_in_GMCGroup(group_ref_gp2)
                assert count_members_gp2 == 2
                count_members_Default = Get_Count_of_members_in_GMCGroup(group_ref_Default)
                assert count_members_Default == 2

        @pytest.mark.run(order=23)
        def test_023_Validate_GMCSchedule_Deactivated_after_promotion_After_Promotion(self):
                #Validate schedule status
                assert Get_GMC_Schedule_Activation_Status() == False

        @pytest.mark.run(order=24)
        def test_024_Promote_oldGM_back(self):
                print_and_log("\n********** Promote old GM back **********")
                master_vip = config.grid_member5_vip
                member_fqdn = config.grid_fqdn
                member_vip = config.grid_vip
                GMC_promote_member_as_master_candidate(master_vip, member_fqdn)
                promote_master(member_vip)
                check_able_to_login_appliances(member_vip)
                validate_status_GM_after_GMC_promotion(member_vip)


