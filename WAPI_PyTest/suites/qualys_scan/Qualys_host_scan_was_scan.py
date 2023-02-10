import re
import pytest
import unittest
import logging
import logger
import subprocess
import xmltodict
import os
import json
import ib_utils.ib_NIOS as ib_NIOS
import commands
import json, ast
import requests
from time import sleep as sleep
import xml.etree.ElementTree as ET
import pexpect
from io import StringIO
import paramiko
from datetime import datetime
import time
import sys
import socket
from paramiko import client
from ib_utils.start_stop_logs import log_action as log
from ib_utils.file_content_validation import log_validation as logv
import paramiko
import config
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from ast import literal_eval

mail_list=literal_eval(config.mail_list)
print(mail_list,type(mail_list))
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)

host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)

time_stamp = "-" + datetime.utcnow().strftime('%Y-%m-%d-%H-%M')
build_name=config.build_name

#build_name="nios-9.0.0-48144-c0fe6b4e5108-2022-08-26-23-57-18-ddi.ova"
file_name="-".join(build_name.split("-", 3)[:3])
file_name=file_name+time_stamp
logging.basicConfig(filename=file_name+'_host_scan_and_was_scan.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

scan_title=file_name

CWD = os.getcwd()
DIRECTORY = os.path.join(CWD, 'tracking_nios_report')
if not os.path.exists(DIRECTORY):
    os.mkdir(DIRECTORY)

if not os.path.exists('QUALYS_SCAN_REPORTS'):
    os.makedirs('QUALYS_SCAN_REPORTS')


RESULT_PATH = os.path.join(CWD, "QUALYS_SCAN_REPORTS")

session_url = config.session_url
username=config.qusername
password=config.qpassword
auth = (config.qusername, config.qpassword)

### host scan varibales ###
files=[]
global files
mail_status=""
unix_record_id_list=[]
global unix_record_id_list
group_id=config.asset_group_ids

def q_session(session,username,password,session_url):
    login = {"action": "login", "username": username, "password": password}
    try:
        response = session.post(session_url, data=login)
        response.raise_for_status()
        logging.info("Logged in successfully")
        return True

    except requests.exceptions.HTTPError as err:
        logging.info("Not able to login")
        logging.info(err)
        if "Forbidden" in err:
            logging.info("looks there are many sessions created, will wait for some time, will give back even if i cant login")
            sleep(500)
            response = session.post(session_url, data=login)
            response.raise_for_status()
            logging.info("logged in successfully")
            return True
        else:
            sys.exit(1)
            return False

def logout_session(session):
    logout = {"action": "logout"}
    logout_url =  config.QUALYS_API_SESSION
    try:
        response = session.post(session_url, data=logout)
        response.raise_for_status()
        logging.info("Qualys session logged out!")

    except requests.exceptions.HTTPError as err:
        logging.info("Failed to logout Qualys session :%s", err)
        return False

def check_scan_status(session,scan_ref,scanType):
    status_url = config.QUALYS_STATUS_URL + scanType + "/"
    fetch_status = {"action": "list", "scan_ref": scan_ref}
    response = session.post(status_url, data=fetch_status)
    response.raise_for_status()
    xmlreturn = ET.fromstring(response.text)

    for elem in xmlreturn.findall('.//STATUS'):
        if elem.find('STATE') is not None:
            scanStatus = elem.find('STATE').text
        else:
            scanStatus = "NotFound"
    response = logout_session(session)
    return scanStatus

def download_reports(session,report_id,format,type):
    build_name=config.build_name
    global file_name
    file_name="-".join(build_name.split("-", 3)[:3])
    file_name=file_name +"_"+type+"."+format
    logging.info("filename: %s",file_name)
    logging.info("report id: %s",report_id)
    params = {
        'action': "fetch",
        "id" : int(report_id)
    }
    try:
        response = session.post(config.QUALYS_REPORT, data=params)
        response.raise_for_status()
        with open(file_name,"wb") as f:
            f.write(response.content)
        try:
            child = pexpect.spawn("scp "+file_name+' '+config.DOWNLOAD_PATH)
            child.logfile=sys.stdout
            child.expect('Are you sure you want to continue connecting (yes/no)?',timeout=None)
            child.sendline('yes')
            c=child.before
            logging.info("your report file :"+file_name+"  copied to "+config.DOWNLOAD_PATH)
        except Exception as e:
            c = False
        if c:
            pass
        else:
            logging.info("Copying files to "+config.DOWNLOAD_PATH)
            dig_cmd = "scp "+file_name+' '+config.DOWNLOAD_PATH
            dig_result = subprocess.check_output(dig_cmd, shell=True)
            assert re.search(r'',str(dig_result))
            logging.info("your report file :"+file_name+"  copied to "+config.DOWNLOAD_PATH)
            logging.info("Test Case Execution Completed")
            sleep(5)
    except requests.exceptions.HTTPError as err:
        logging.error("Failed download scan results :%s", err)
    return file_name

def ping_ip(ip):
    ping_response = subprocess.Popen(["/bin/ping", "-c4", ip], stdout=subprocess.PIPE).stdout.read()
    if "4 received" in ping_response:
        logging.info(ip+" is up, Ping Successful")
        return True
    else:
        logging.info(ip+" is Down, Ping Unsuccessful")
        return False

def ping_grid_send_mail(subject,body):
    data = MIMEMultipart()
    sender = 'jenkins@infoblox.com'
    receivers = mail_list
    data['Subject'] = subject
    data['From'] = sender
    data['To'] = ", ".join(receivers)
    body =body
    data.attach(MIMEText(body, 'plain'))
    message = data.as_string()
    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender, receivers, message)
        logging.info("Successfully sent email")
    except smtplib.SMTPException:
        logging.info("Error: unable to send email")

def check_was_scan_status(scan_status_id):
    headers = {"Accept": "application/xml"}
    url = config.status_url+scan_status_id
    try:
        r1=requests.get(url, auth=auth, headers=headers)
        data_dict = xmltodict.parse(r1.content)
        json_data = json.dumps(data_dict)
        json_data=json.loads(json_data)
        #logging.info(json_data)
        scanStatus=json_data['ServiceResponse']['data']['WasScan']['status']
        return scanStatus
    except requests.exceptions.HTTPError as err:
        logging.info("Not able to login")
        logging.info(err)
        if "Forbidden" in err:
            logging.info("looks there are many sessions created, will wait for some time, will give back even if i cant login")
            sleep(500)
            rr1=requests.get(url, auth=auth, headers=headers)
            data_dict = xmltodict.parse(r1.content)
            json_data = json.dumps(data_dict)
            json_data=json.loads(json_data)
            logging.info(json_data)
            scanStatus=json_data['ServiceResponse']['data']['WasScan']['status']
            return scanStatus
        else:
            sys.exit(1)
            return False


class QUALYS_SCAN(unittest.TestCase):
    ############################################# test case started ############################################

    @pytest.mark.run(order=1)
    def test_001_execute_cli_command_set_ssl_tls_settings_override(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:',timeout=None)
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set ssl_tls_settings override')
            child.expect('Infoblox >')
            c= child.before
            assert re.search(r'.*The following services need to be restarted manually: GUI.*',c)
            logging.info("Test Case Execution Completed")
            assert True
        else:
            logging.info("grid is not up")
            assert False

    @pytest.mark.run(order=3)
    def test_003_execute_cli_command_set_ssl_tls_settings_override_1_0(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:',timeout=None)
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set ssl_tls_protocols disable TLSv1.0')
            child.expect('Infoblox >')
            c= child.before
            assert re.search(r'.*TLSv1\.0 was disabled.*',c)
            logging.info("Test Case Execution Completed")
        else:
            logging.info("grid is not up")
            assert False

    @pytest.mark.run(order=5)
    def test_005_execute_cli_command_set_ssl_tls_settings_override(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:',timeout=None)
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set ssl_tls_protocols disable TLSv1.1')
            child.expect('Infoblox >')
            c= child.before
            assert re.search(r'.*TLSv1\.1 was disabled.*',c)
            logging.info("Test Case Execution Completed")
        else:
            logging.info("grid is not up")
            assert False

    @pytest.mark.run(order=7)
    def test_007_execute_cli_command_set_ssl_tls_settings_override(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:',timeout=None)
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set ssl_tls_ciphers disable 10')
            child.expect('Infoblox >')
            c= child.before
            assert re.search(r'.*set ssl_tls_ciphers disable 10.*',c)
            logging.info("Test Case Execution Completed")
        else:
            logging.info("grid is not up")
            assert False


    @pytest.mark.run(order=8)
    def test_008_prod_restart(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:')
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set maintenancemode')
            child.expect('Maintenance Mode >')
            child.sendline('restart_product')
            child.expect(':')
            child.sendline('y')
            child.expect(pexpect.EOF)
            for i in range(1,20):
                sleep(60)
                status = os.system("ping -c1 -w2 "+config.grid_vip_lan_ipv4)
                if status == 0:
                    logging.info("System is up")
                    break
                else:
                    logging.info("System is down")
            sleep(10)
            logging.info("Product Reboot done")
        else:
            logging.info("grid is not up")
            assert False


    @pytest.mark.run(order=9)
    def test_009_validate_cli_command_set_ssl_tls_settings_override(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:',timeout=None)
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('show ssl_tls_protocols')
            child.expect('Infoblox >')
            c= child.before
            if ("TLSv1.1" not in c) and ("TLSv1.0" not in c):
                assert True
            else:
                assert False
            sleep(15)
        else:
            logging.info("grid is not up")
            assert False

    @pytest.mark.run(order=11)
    def test_011_verify_asset_group_present_if_not_create_edit_ip_if_not_present_in_group(self):
        sleep(15)
        session_url = config.session_url
        username=config.qusername
        password=config.qpassword
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        supported_actions = {'action': 'list',
                                        'ids': group_id}
        try:
            response = session.post(config.QUALYS_GROUP,
                                    params=supported_actions,
                                    headers={'Content-type': 'text/xml'})
            xml_return = ET.parse(StringIO(response.content.decode('utf-8'))).getroot()
            data_dict = xmltodict.parse(response.content)
            json_data = json.dumps(data_dict)
            json_data=json.loads(json_data)
            varify_asset_list=json_data['ASSET_GROUP_LIST_OUTPUT']['RESPONSE'].keys()
            if 'ASSET_GROUP_LIST' in varify_asset_list:
                if json_data['ASSET_GROUP_LIST_OUTPUT']['RESPONSE']['ASSET_GROUP_LIST']['ASSET_GROUP']['TITLE'] == 'NIOS Testing':
                    ip_list=json_data['ASSET_GROUP_LIST_OUTPUT']['RESPONSE']['ASSET_GROUP_LIST']['ASSET_GROUP']['IP_SET']['IP_RANGE']
                    if config.ips in ip_list:
                        logging.info('yes ip range is present in asset group '+ json_data['ASSET_GROUP_LIST_OUTPUT']['RESPONSE']['ASSET_GROUP_LIST']['ASSET_GROUP']['TITLE'])
                        response = logout_session(session)
                    else:
                        add_group = {"action": "edit", "id": group_id,
                                     "add_ips": config.ips}
                        try:
                            response = session.post(config.QUALYS_GROUP, data=add_group)
                            response.raise_for_status()
                            xmlreturn = ET.fromstring(response.text)
                            logging.info("Added target assets to group with ID :%s", group_id)
                            logging.info('NIOS Testing  is added with ip range '+config.ips)
                            response = logout_session(session)
                            assert True
                        except requests.exceptions.HTTPError as err:
                            logging.error("Failed to edit assets to group :%s", err)
                            assert False
            else:
                add_group = {"action": "add", "title":'NIOS Testing',
                             "comments": "Group created by NIOS team",
                             "ips": config.ips}
                try:
                    response = session.post(config.QUALYS_GROUP, data=add_group)
                    response.raise_for_status()
                    xmlreturn = ET.fromstring(response.text)
                    for elem in xmlreturn.findall('.//ITEM'):
                        if elem[0].text == 'ID':
                            global group_id
                            group_id = elem[1].text
                            logging.info("Added target assets to group with ID :%s", group_id)
                    logging.info('NIOS Testing  is added with ip range '+config.ips)
                    assert True
                except requests.exceptions.HTTPError as err:
                    logging.error("Failed to add assets to group :%s", err)
        except requests.exceptions.HTTPError as err:
            logging.error("Failed to add or edit assets to group :%s", err)
            assert False

    @pytest.mark.run(order=12)
    def test_012_unauthentication_scan(self):
        count=1
        for i in range(1,4):
            grid_status=ping_ip(config.grid_vip_lan_ipv4)
            #connector_status=ping_ip(config.connector_ip)
            connector_status=True
            if (grid_status == True) and (connector_status==True):
                #global scan_ref
                session = requests.Session()
                logging.info('session created')
                session.headers.update({'X-Requested-With': 'Python Script'})
                status=q_session(session,username,password,session_url)
                if status == True:
                    scan_url = config.QUALYS_API_SCAN
                    scan_data = {'action': "launch", 'scan_title': scan_title,
                                'iscanner_name': config.SCANNER_NAME,'target_from': 'assets', 'asset_group_ids':group_id,
                                'option_title': config.VM_OPTION_PROFILE_UNAUTHENTICATED}
                    try:
                        response = session.post(scan_url, data=scan_data)
                        response.raise_for_status()
                        logging.info("scan started")
                        xmlreturn = ET.fromstring(response.text)
                        for elem in xmlreturn.findall('.//ITEM'):
                            if elem[0].text == 'REFERENCE':
                                scan_ref = elem[1].text
                                logging.info("Scan started with reference ID %s", scan_ref)
                                global scan_ref
                                response = logout_session(session)
                        break
                        assert True
                    except requests.exceptions.HTTPError as err:
                        logging.error("Scan initiation failed :%s", err)
                else:
                    logging.info("Test Case Execution Failed, not able to login")
                    assert False
                response = logout_session(session)
                #if grid status is up, start scan and come out
                assert True
            elif count<=2:
                sleep(120)
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if (grid_status == False) or (connector_status==False):
                    count=count+1
            else:
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if connector_status ==False:
                    subject="Qualys connector "+config.connector_ip+" is not up"
                    body="Qualys connector "+config.connector_ip+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"
                elif grid_status ==False:
                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"

    @pytest.mark.run(order=13)
    def test_013_get_scan_status_unathenticated(self):
            #global scan_ref
            status=['Finished', 'Queued', 'Running','Error','Canceled','Expired','Paused']
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,config.qusername,config.qpassword,config.session_url)
            checkStatus = check_scan_status(session,scan_ref,"scan")
            if checkStatus in status:
                timeout = time.time() + 3600
                resume=0
                while checkStatus != "Finished":
                    session = requests.Session()
                    session.headers.update({'X-Requested-With': 'Python Script'})
                    grid_status=ping_ip(config.grid_vip_lan_ipv4)
                    #connector_status=ping_ip(config.connector_ip)
                    connector_status=True
                    if (grid_status == False) or (connector_status==False):
                        sleep(120)
                        grid_status=ping_ip(config.grid_vip_lan_ipv4)
                        connector_status=True
                        if (grid_status == False) or (connector_status==False):
                            if mail_status !="sent mail":
                                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                                #connector_status=ping_ip(config.connector_ip)
                                connector_status=True
                                if connector_status ==False:
                                    subject="Qualys connector "+config.connector_ip+" is not up"
                                    body="Qualys connector "+config.connector_ip+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                elif grid_status ==False:
                                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                    break
                    else:
                        q_session(session,config.qusername,config.qpassword,config.session_url)
                        checkStatus = check_scan_status(session,scan_ref,"scan")
                        logging.info("Scan status: %s",checkStatus)
                        logging.info("cheking scan status:[error,canceled,Expired,Paused]")
                        if (checkStatus == 'Error') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'ERROR'"
                            body="scan status is showing 'ERROR'"+scan_ref+" report will not generate for unauthentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Canceled') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Canceled'"
                            body="scan status is showing 'Canceled'"+scan_ref+" report will not generate for unauthentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Expired') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Expired'"
                            body="scan status is showing 'Expired'"+scan_ref+" report will not generate for unauthentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif checkStatus == 'Paused' and resume <1:
                            scan_url = config.QUALYS_API_SCAN
                            scan_data = {'action': "resume", 'scan_ref': scan_ref}
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,username,password,session_url)
                            try:
                                response = session.post(scan_url, data=scan_data)
                                response.raise_for_status()
                                logging.info("restarted once ")
                                resume=resume+1
                            except requests.exceptions.HTTPError as err:
                                logging.error("not able to restart :%s", err)
                                response = logout_session(session)
                                break


                        elif checkStatus == 'Paused' and resume == 1:
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is paused"
                            body="scan status is paused , once restarted but again paused for scan_ref: "+scan_ref+" report will not generate for unauthentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        # elif checkStatus == 'Queued':
                        #     sleep(300)
                        #     print(time.time(),timeout)
                        #     if time.time() > timeout:
                        #         print("Queued----------")
                        #         subject="Scan status is Queued from last 1 hour"
                        #         body="Scan status is Queued from last 1 hour"
                        #         ping_grid_send_mail(subject,body)
                        #         mail_status="sent mail"
                        #         break

                        elif checkStatus == "Finished":
                            logging.info("Scan job completed for :%s", scan_ref)
                            assert True
                        else:
                            logging.info("Scan in progress")
                            logging.info("Will check again after 5 minutes of sleep time\n")
                            time.sleep(300)
            else:
                subject=checkStatus
                body="Scan status is showing" +checkStatus
                ping_grid_send_mail(subject,body)
                mail_status="sent mail"
                assert False

    @pytest.mark.run(order=14)
    def test_014_download_vm_scan_results_unauthenticated(self):
        global files
        files=[]
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        checkStatus = check_scan_status(session,scan_ref, "scan")
        if checkStatus == "Finished":
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,username,password,session_url)
            output_format = ["pdf","csv"]
            for format in output_format:
                params = {
                'action': "launch",
                'template_id': 4173070,
                'output_format': format,
                "report_refs": scan_ref
                }

                try:
                    response = session.post(config.QUALYS_REPORT, data=params)
                    response.raise_for_status()
                    myroot = ET.fromstring(response.text)
                    for x in myroot.findall(".//ITEM"):
                        if x[1].tag == "VALUE":
                            report_id = x[1].text
                            sleep(180)
                    type='qualys_unauthenticated_default'
                    file_name=download_reports(session,report_id,format,type)
                    files.append(file_name)
                    print(files)
                except requests.exceptions.HTTPError as err:
                    logging.error("Failed to launch report :%s", err)
                    assert False
        else:
            logging.error("Failed to launch report :%s", err)
            assert False

    @pytest.mark.run(order=15)
    def test_015_send_report_as_mail_unauthenticated(self):
        data = MIMEMultipart()
        sender = 'jenkins@infoblox.com'
        receivers = mail_list
        data['Subject'] = "QUALYS_UNAUTHENTICATION_SCAN_REPORT_DEFAULT"
        data['From'] = sender
        data['To'] = ", ".join(receivers)
        body = "Please Analyse Qualys host scan results default"
        data.attach(MIMEText(body, 'plain'))
        for i in files:
            path='/import/qaddi/QUALYS_SCAN_REPORTS'
            logging.info("file_name :%s",i)
            attachment = open(i,"rb")
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((attachment).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', "attachment; filename="+i)
            data.attach(p)
            message = data.as_string()
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            logging.info("Successfully sent email")
            assert True
        except smtplib.SMTPException:
            logging.info("Error: unable to send email")
            assert False

    @pytest.mark.run(order=16)
    def test_016_q_authentication(self):
        vm_to_scan=[{"title":config.grid_vip_lan_ipv4,"ips":config.grid_vip_lan_ipv4,'password':config.grid_vip_pass},
                {"title":config.grid_member1_vip_lan_ipv4,"ips":config.grid_member1_vip_lan_ipv4,'password':config.grid_member1_vip_pass},
                {"title":config.grid_member2_vip_lan_ipv4,"ips":config.grid_member2_vip_lan_ipv4,'password':config.grid_member2_vip_pass},
                {"title":config.grid_member3_vip_lan_ipv4,"ips":config.grid_member3_vip_lan_ipv4,'password':config.grid_member3_vip_pass}]

        session_url = config.session_url
        username=config.qusername
        password=config.qpassword
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        for i in vm_to_scan:
            supported_actions = {'action': 'create',
                                            'title': i['title'],
                                            'comments': 'Unix record created by cyberint VM automation',
                                            'username': 'root',
                                            'skip_password': 0,
                                            'password':password,
                                            'ips':i['ips']}
            try:
                response = session.post(config.unix_record_api,
                                        params=supported_actions,
                                        headers={'Content-type': 'text/xml'})
                response.raise_for_status()
                xml_return = ET.parse(StringIO(response.content.decode('utf-8'))).getroot()
                data_dict = xmltodict.parse(response.content)
                json_data = json.dumps(data_dict)
                json_data=json.loads(json_data)
                unix_record_id =xml_return[0][1][0][1][0].text
                unix_record_id_list.append(unix_record_id)
                logging.info("authenticated")
            except requests.exceptions.HTTPError as err:
                logging.info("authentication is not happening")
        logout_session(session)

    @pytest.mark.run(order=17)
    def test_017_q_authentication_verify(self):
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        supported_actions = {'action': 'list',
                                        'title': 'NIOS - GM'}
        try:
            response = session.post(config.unix_record_api,
                                    params=supported_actions,
                                    headers={'Content-type': 'text/xml'})
            res=response.text
            if res =='':
                logging.info("aut record not created")
            else:
                logging.info('verified authentication record has been created')
                assert True
        except requests.exceptions.HTTPError as err:
            logging.info("authentication is not happening")
            assert False
        logout_session(session)

    @pytest.mark.run(order=18)
    def test_018_authentication_scan(self):
        count=1
        for i in range(1,4):
            grid_status=ping_ip(config.grid_vip_lan_ipv4)
            #connector_status=ping_ip(config.connector_ip)
            connector_status=True
            if (grid_status == True) and (connector_status==True):
                session = requests.Session()
                logging.info('session created')
                session.headers.update({'X-Requested-With': 'Python Script'})
                status=q_session(session,username,password,session_url)
                if status == True:
                    scan_url = config.QUALYS_API_SCAN
                    scan_data = {'action': "launch", 'scan_title': file_name,
                                'iscanner_name': config.SCANNER_NAME,'target_from': 'assets', 'asset_group_ids':group_id,
                                'option_title': config.VM_OPTION_PROFILE}
                    try:
                        response = session.post(scan_url, data=scan_data)
                        response.raise_for_status()
                        logging.info("scan started")
                        xmlreturn = ET.fromstring(response.text)
                        for elem in xmlreturn.findall('.//ITEM'):
                            if elem[0].text == 'REFERENCE':
                                scan_ref = elem[1].text
                                logging.info("scan_ref: %s",scan_ref)
                                logging.info("Scan started with reference ID %s", scan_ref)
                                global scan_ref
                                response = logout_session(session)
                        break
                        assert True
                    except requests.exceptions.HTTPError as err:
                        logging.info("Scan initiation failed :%s", err)
                else:
                    logging.info("Test Case Execution Failed, not able to login")
                    assert False
                response = logout_session(session)
                #if grid status is up, start scan and come out
                assert True
            elif count<=2:
                sleep(120)
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if (grid_status == False) or (connector_status==False):
                    count=count+1
            else:
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if connector_status ==False:
                    subject="Qualys connector "+config.connector_ip+" is not up"
                    body="Qualys connector "+config.connector_ip+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"
                elif grid_status ==False:
                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"

    @pytest.mark.run(order=19)
    def test_019_get_scan_status_athenticated(self):
            status=['Finished', 'Queued', 'Running','Error','Canceled','Expired','Paused']
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,config.qusername,config.qpassword,config.session_url)
            checkStatus = check_scan_status(session,scan_ref,"scan")
            if checkStatus in status:
                timeout = time.time() + 3600
                resume=0
                while checkStatus != "Finished":
                    session = requests.Session()
                    session.headers.update({'X-Requested-With': 'Python Script'})
                    grid_status=ping_ip(config.grid_vip_lan_ipv4)
                    #connector_status=ping_ip(config.connector_ip)
                    connector_status=True
                    if (grid_status == False) or (connector_status==False):
                        sleep(120)
                        grid_status=ping_ip(config.grid_vip_lan_ipv4)
                        connector_status=True
                        if (grid_status == False) or (connector_status==False):
                            if mail_status !="sent mail":
                                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                                #connector_status=ping_ip(config.connector_ip)
                                connector_status=True
                                if connector_status ==False:
                                    subject="Qualys connector "+config.connector_ip+" is not up"
                                    body="Qualys connector "+config.connector_ip+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                elif grid_status ==False:
                                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                    break
                    else:
                        q_session(session,config.qusername,config.qpassword,config.session_url)
                        checkStatus = check_scan_status(session,scan_ref,"scan")
                        logging.info("Scan status: %s",checkStatus)
                        logging.info("cheking scan status:[error,canceled,Expired,Paused]")
                        if (checkStatus == 'Error') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'ERROR'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Canceled') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Canceled'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Expired') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Expired'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif checkStatus == 'Paused' and resume <1:
                            scan_url = config.QUALYS_API_SCAN
                            scan_data = {'action': "resume", 'scan_ref': scan_ref}
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,username,password,session_url)
                            try:
                                response = session.post(scan_url, data=scan_data)
                                response.raise_for_status()
                                logging.info("restarted once ")
                                resume=resume+1
                            except requests.exceptions.HTTPError as err:
                                logging.error("not able to restart :%s", err)
                                response = logout_session(session)
                                break


                        elif checkStatus == 'Paused' and resume == 1:
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is paused"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan before service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif checkStatus == "Finished":
                            #checkStatus_list.append(checkStatus)
                            logging.info("Scan job completed for :%s", scan_ref)
                            assert True
                        else:
                            logging.info("Scan in progress")
                            logging.info("Will check again after 5 minutes of sleep time\n")
                            time.sleep(300)
            else:
                subject=checkStatus
                body="Scan status is showing" +checkStatus
                ping_grid_send_mail(subject,body)
                mail_status="sent mail"
                assert False

    @pytest.mark.run(order=20)
    def test_020_download_vm_scan_results_athenticated(self):
        global files
        files=[]
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        checkStatus = check_scan_status(session,scan_ref, "scan")
        if checkStatus == "Finished":
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,username,password,session_url)
            output_format = ["pdf","csv"]
            for format in output_format:
                params = {
                'action': "launch",
                'template_id': 4173070,
                'output_format': format,
                "report_refs": scan_ref
                }

                try:
                    response = session.post(config.QUALYS_REPORT, data=params)
                    response.raise_for_status()
                    myroot = ET.fromstring(response.text)
                    for x in myroot.findall(".//ITEM"):
                        if x[1].tag == "VALUE":
                            report_id = x[1].text
                            sleep(180)
                    type='qualys_athenticated_default'
                    file_name=download_reports(session,report_id,format,type)
                    files.append(file_name)
                except requests.exceptions.HTTPError as err:
                    logging.error("Failed to launch report :%s", err)
                    assert False
        else:
            logging.error("Failed to launch report :%s", err)
            assert False

    @pytest.mark.run(order=21)
    def test_021_send_report_as_mail(self):
        data = MIMEMultipart()
        sender = 'jenkins@infoblox.com'
        receivers = mail_list
        data['Subject'] = "QUALYS_AUTHENTICATED_SCAN_REPORT_DEFAULT"
        data['From'] = sender
        data['To'] = ", ".join(receivers)
        body = "Please Analyse Qualys host scan results default"
        data.attach(MIMEText(body, 'plain'))
        for i in files:
            path='/import/qaddi/QUALYS_SCAN_REPORTS'
            file_name=i
            logging.info("file_name: %s",file_name)
            attachment = open(file_name,"rb")
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((attachment).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', "attachment; filename="+file_name)
            data.attach(p)
            message = data.as_string()
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            logging.info("Successfully sent email")
            assert True
        except smtplib.SMTPException:
            logging.info("Error: unable to send email")
            assert False

    # @pytest.mark.run(order=22)
    # def test_022_clear_authentication(self):
    #     logging.info(unix_record_id_list)
    #     for i in unix_record_id_list:
    #         session = requests.Session()
    #         session.headers.update({'X-Requested-With': 'Python Script'})
    #         q_session(session,username,password,session_url)
    #         supported_actions = {'action': 'delete',
    #                                         'ids':i}
    #         try:
    #             response = session.post(config.unix_record_api,
    #                                     params=supported_actions,
    #                                     headers={'Content-type': 'text/xml'})
    #             res=response.raise_for_status()
    #             logging.info(res)
    #             logging.info("cleared authentication")
    #         except requests.exceptions.HTTPError as err:
    #             logging.info(err)
    #             return False
    #         logout_session(session)

    @pytest.mark.run(order=23)
    def test_023_Start_DNS_Service(self):
        logging.info("Start dns Service")
        get_ref = ib_NIOS.wapi_request('GET', object_type="member:dns")
        logging.info(get_ref)
        res = json.loads(get_ref)
        for i in res:
            ref=i["_ref"]
            logging.info("Modify a enable_dns")
            data = {"enable_dns": True}
            response = ib_NIOS.wapi_request('PUT', ref=ref, fields=json.dumps(data))

    @pytest.mark.run(order=24)
    def test_024_Validate_DNS_service_is_Enabled(self):
        logging.info("Validate dns Service is enabled")
        get_response_val = ib_NIOS.wapi_request('GET', object_type="member:dns",params="?_return_fields=enable_dns")
        logging.info(get_response_val)
        res = json.loads(get_response_val)
        logging.info(res)
        for i in res:
            if i["enable_dns"] == True:
                assert True
            else:
                logging.info("Test Case Execution Failed")
                assert False
        logging.info("Test Case Execution Passed")

    @pytest.mark.run(order=25)
    def test_025_Start_ntp_Service(self):
        logging.info("Start ntp Service")
        get_ref = ib_NIOS.wapi_request('GET', object_type="member")
        logging.info(get_ref)
        res = json.loads(get_ref)
        for i in res:
            ref=i["_ref"]
            logging.info("Modify a enable_ntp")
            data={'ntp_setting':{'enable_ntp': True}}
            response = ib_NIOS.wapi_request('PUT', ref=ref, fields=json.dumps(data))

    @pytest.mark.run(order=26)
    def test_026_Validate_NTP_service_is_Enabled(self):
        logging.info("Validate ntp Service is enabled")
        get_response_val = ib_NIOS.wapi_request('GET', object_type="member",params="?_return_fields=ntp_setting")
        logging.info(get_response_val)
        res = json.loads(get_response_val)
        for i in res:
            if i['ntp_setting']['enable_ntp'] == True:
                assert True
            else:
                logging.info("Test Case Execution Failed")
                assert False
        logging.info("Test Case Execution Passed")

    @pytest.mark.run(order=27)
    def test_027_Start_FTP_Service(self):
       logging.info("Start FTP Service")
       get_ref = ib_NIOS.wapi_request('GET', object_type="member:filedistribution")
       logging.info(get_ref)
       res = json.loads(get_ref)
       for i in res:
           ref=i["_ref"]
           data={'enable_ftp': True}
           response = ib_NIOS.wapi_request('PUT', ref=ref, fields=json.dumps(data))
           logging.info(response)

    @pytest.mark.run(order=28)
    def test_028_Validate_FTP_service_is_Enabled(self):
        logging.info("Validate ftp Service is enabled")
        get_response_val = ib_NIOS.wapi_request('GET', object_type="member:filedistribution",params="?_return_fields=enable_ftp")
        logging.info(get_response_val)
        res = json.loads(get_response_val)
        logging.info(res)
        for i in res:
            if i["enable_ftp"] == True:
                assert True
            else:
                logging.info("Test Case Execution Failed")
                assert False
        logging.info("Test Case Execution Passed")

    @pytest.mark.run(order=29)
    def test_029_Start_DHCP_Service(self):
        logging.info("Start dhcp Service")
        get_ref = ib_NIOS.wapi_request('GET', object_type="member:dhcpproperties")
        logging.info(get_ref)
        res = json.loads(get_ref)
        for i in res:
            ref=i["_ref"]
            logging.info("Modify a enable_dhcp")
            data={'enable_dhcp': True}
            response = ib_NIOS.wapi_request('PUT', ref=ref, fields=json.dumps(data))

    @pytest.mark.run(order=30)
    def test_030_Validate_DHCP_service_is_Enabled(self):
        logging.info("Validate dhcp Service is enabled")
        get_response_val = ib_NIOS.wapi_request('GET', object_type="member:dhcpproperties",params="?_return_fields=enable_dhcp")
        logging.info(get_response_val)
        res = json.loads(get_response_val)
        logging.info(res)
        for i in res:
            if i["enable_dhcp"] == True:
                assert True
            else:
                logging.info("Test Case Execution Failed")
                assert False
        logging.info("Test Case Execution Passed")

    @pytest.mark.run(order=31)
    def test_031_Start_HTTP_Service(self):
        logging.info("Start http Service")
        get_ref = ib_NIOS.wapi_request('GET', object_type="member:filedistribution")
        logging.info(get_ref)
        res = json.loads(get_ref)
        for i in res:
            ref=i["_ref"]
            data={'enable_http': True}
            response = ib_NIOS.wapi_request('PUT', ref=ref, fields=json.dumps(data))
            logging.info(response)

    @pytest.mark.run(order=32)
    def test_032_Validate_DHCP_service_is_Enabled(self):
        logging.info("Validate http Service is enabled")
        get_response_val = ib_NIOS.wapi_request('GET', object_type="member:filedistribution",params="?_return_fields=enable_http")
        logging.info(get_response_val)
        res = json.loads(get_response_val)
        logging.info(res)
        for i in res:
            if i["enable_http"] == True:
                assert True
            else:
                logging.info("Test Case Execution Failed")
                assert False
        logging.info("Test Case Execution Passed")
        sleep(60)

    @pytest.mark.run(order=33)
    def test_033_prod_restart(self):
        grid_status=ping_ip(config.grid_vip_lan_ipv4)
        if grid_status ==True:
            child = pexpect.spawn('ssh admin@'+config.grid_vip_lan_ipv4)
            child.logfile=sys.stdout
            child.expect('password:')
            child.sendline('infoblox')
            child.expect('Infoblox >')
            child.sendline('set maintenancemode')
            child.expect('Maintenance Mode >')
            child.sendline('restart_product')
            child.expect(':')
            child.sendline('y')
            child.expect(pexpect.EOF)
            for i in range(1,20):
                sleep(60)
                status = os.system("ping -c1 -w2 "+config.grid_vip_lan_ipv4)
                if status == 0:
                    logging.info("System is up")
                    break
                else:
                    logging.info("System is down")
            sleep(10)
            logging.info("Product Reboot done")
        else:
            logging.info("grid is not up")
            assert False

    @pytest.mark.run(order=34)
    def test_034_unauthentication_scan_after_enble_service(self):
        sleep(60)
        count=1
        for i in range(1,4):
            grid_status=ping_ip(config.grid_vip_lan_ipv4)
            #connector_status=ping_ip(config.connector_ip)
            connector_status=True
            if (grid_status == True) and (connector_status==True):
                #global scan_ref
                session = requests.Session()
                logging.info('session created')
                session.headers.update({'X-Requested-With': 'Python Script'})
                status=q_session(session,username,password,session_url)
                if status == True:
                    scan_url = config.QUALYS_API_SCAN
                    scan_data = {'action': "launch", 'scan_title': scan_title,
                                'iscanner_name': config.SCANNER_NAME,'target_from': 'assets', 'asset_group_ids':group_id,
                                'option_title': config.VM_OPTION_PROFILE_UNAUTHENTICATED}
                    try:
                        response = session.post(scan_url, data=scan_data)
                        response.raise_for_status()
                        logging.info("scan started")
                        xmlreturn = ET.fromstring(response.text)
                        for elem in xmlreturn.findall('.//ITEM'):
                            if elem[0].text == 'REFERENCE':
                                scan_ref = elem[1].text
                                logging.info("Scan started with reference ID %s", scan_ref)
                                global scan_ref
                                response = logout_session(session)
                        break
                        assert True
                    except requests.exceptions.HTTPError as err:
                        logging.error("Scan initiation failed :%s", err)
                else:
                    logging.info("Test Case Execution Failed, not able to login")
                    assert False
                response = logout_session(session)
                #if grid status is up, start scan and come out
                assert True
            elif count<=2:
                sleep(120)
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if (grid_status == False) or (connector_status==False):
                    count=count+1
            else:
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if connector_status ==False:
                    subject="Qualys connector "+config.connector_ip+" is not up"
                    body="Qualys connector "+config.connector_ip+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"
                elif grid_status ==False:
                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"

    @pytest.mark.run(order=35)
    def test_035_get_scan_status_unathenticated_after_enble_service(self):
            status=['Finished', 'Queued', 'Running','Error','Canceled','Expired','Paused']
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,config.qusername,config.qpassword,config.session_url)
            checkStatus = check_scan_status(session,scan_ref,"scan")
            if checkStatus in status:
                timeout = time.time() + 3600
                resume=0
                while checkStatus != "Finished":
                    session = requests.Session()
                    session.headers.update({'X-Requested-With': 'Python Script'})
                    grid_status=ping_ip(config.grid_vip_lan_ipv4)
                    #connector_status=ping_ip(config.connector_ip)
                    connector_status=True
                    if (grid_status == False) or (connector_status==False):
                        sleep(120)
                        grid_status=ping_ip(config.grid_vip_lan_ipv4)
                        connector_status=True
                        if (grid_status == False) or (connector_status==False):
                            if mail_status !="sent mail":
                                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                                #connector_status=ping_ip(config.connector_ip)
                                connector_status=True
                                if connector_status ==False:
                                    subject="Qualys connector "+config.connector_ip+" is not up"
                                    body="Qualys connector "+config.connector_ip+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                elif grid_status ==False:
                                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                    break
                    else:
                        q_session(session,config.qusername,config.qpassword,config.session_url)
                        checkStatus = check_scan_status(session,scan_ref,"scan")
                        logging.info("Scan status: %s",checkStatus)
                        logging.info("cheking scan status:[error,canceled,Expired,Paused]")
                        if (checkStatus == 'Error') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'ERROR'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for unauthentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Canceled') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Canceled'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for unauthentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Expired') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Expired'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for unauthentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif checkStatus == 'Paused' and resume <1:
                            scan_url = config.QUALYS_API_SCAN
                            scan_data = {'action': "resume", 'scan_ref': scan_ref}
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,username,password,session_url)
                            try:
                                response = session.post(scan_url, data=scan_data)
                                response.raise_for_status()
                                logging.info(response)
                                logging.info("restarted once ")
                                resume=resume+1
                            except requests.exceptions.HTTPError as err:
                                logging.error("not able to restart :%s", err)
                                response = logout_session(session)
                                break


                        elif checkStatus == 'Paused' and resume == 1:
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is paused"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for unauthentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        # elif checkStatus == 'Queued':
                        #     sleep(300)
                        #     print(time.time(),timeout)
                        #     if time.time() > timeout:
                        #         print("Queued----------")
                        #         subject="Scan status is Queued from last 1 hour"
                        #         body="Scan status is Queued from last 1 hour"
                        #         ping_grid_send_mail(subject,body)
                        #         mail_status="sent mail"
                        #         break

                        elif checkStatus == "Finished":
                            #checkStatus_list.append(checkStatus)
                            logging.info("Scan job completed for :%s", scan_ref)
                            assert True
                        else:
                            logging.info("Scan in progress")
                            logging.info("Will check again after 5 minutes of sleep time\n")
                            time.sleep(300)
            else:
                subject=checkStatus
                body="Scan status is showing" +checkStatus
                ping_grid_send_mail(subject,body)
                mail_status="sent mail"
                assert False

    @pytest.mark.run(order=36)
    def test_036_download_vm_scan_results_after_service_enable(self):
        global files
        files=[]
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        checkStatus = check_scan_status(session,scan_ref, "scan")
        if checkStatus == "Finished":
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,username,password,session_url)
            output_format = ["pdf","csv"]
            for format in output_format:
                params = {
                'action': "launch",
                'template_id': 4173070,
                'output_format': format,
                "report_refs": scan_ref
                }

                try:
                    response = session.post(config.QUALYS_REPORT, data=params)
                    response.raise_for_status()
                    myroot = ET.fromstring(response.text)
                    for x in myroot.findall(".//ITEM"):
                        if x[1].tag == "VALUE":
                            report_id = x[1].text
                            sleep(180)
                    type='qualys_unathenticated_custom'
                    file_name=download_reports(session,report_id,format,type)
                    files.append(file_name)
                except requests.exceptions.HTTPError as err:
                    logging.error("Failed to launch report :%s", err)
                    assert False
        else:
            logging.error("Failed to launch report :%s", err)
            assert False

    @pytest.mark.run(order=37)
    def test_037_send_report_as_mail_after_service_start(self):
        data = MIMEMultipart()
        sender = 'jenkins@infoblox.com'
        receivers = mail_list
        data['Subject'] = "QUALYS_UNAUTHENTICATION_SCAN_REPORT_CUSTOM"
        data['From'] = sender
        data['To'] = ", ".join(receivers)
        body = "Please Analyse Qualys host scan custom report"
        data.attach(MIMEText(body, 'plain'))
        for i in files:
            path='/import/qaddi/QUALYS_SCAN_REPORTS'
            file_name=i
            logging.info("file_name :%s",file_name)
            attachment = open(file_name,"rb")
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((attachment).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', "attachment; filename="+file_name)
            data.attach(p)
            message = data.as_string()
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            logging.info("Successfully sent email")
            assert True
        except smtplib.SMTPException:
            logging.info("Error: unable to send email")
            assert False

    # @pytest.mark.run(order=38)
    # def test_038_q_authentication(self):
    #     vm_to_scan=[{"title":config.grid_vip_lan_ipv4,"ips":config.grid_vip_lan_ipv4,'password':config.grid_vip_pass},
    #             {"title":config.grid_member1_vip_lan_ipv4,"ips":config.grid_member1_vip_lan_ipv4,'password':config.grid_member1_vip_pass},
    #             {"title":config.grid_member2_vip_lan_ipv4,"ips":config.grid_member2_vip_lan_ipv4,'password':config.grid_member2_vip_pass},
    #             {"title":config.grid_member3_vip_lan_ipv4,"ips":config.grid_member3_vip_lan_ipv4,'password':config.grid_member3_vip_pass}]
    #
    #     session_url = config.session_url
    #     username=config.qusername
    #     password=config.qpassword
    #     session = requests.Session()
    #     session.headers.update({'X-Requested-With': 'Python Script'})
    #     q_session(session,username,password,session_url)
    #     for i in vm_to_scan:
    #         supported_actions = {'action': 'create',
    #                                         'title': i['title'],
    #                                         'comments': 'Unix record created by cyberint VM automation',
    #                                         'username': 'root',
    #                                         'skip_password': 0,
    #                                         'password':password,
    #                                         'ips':i['ips']}
    #         try:
    #             response = session.post(config.unix_record_api,
    #                                     params=supported_actions,
    #                                     headers={'Content-type': 'text/xml'})
    #             response.raise_for_status()
    #             xml_return = ET.parse(StringIO(response.content.decode('utf-8'))).getroot()
    #             unix_record_id =xml_return[0][1][0][1][0].text
    #             logging.info("authenticated")
    #         except requests.exceptions.HTTPError as err:
    #             logging.info("authentication is not happening")
    #     logout_session(session)

    @pytest.mark.run(order=39)
    def test_039_q_authentication_verify(self):
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        supported_actions = {'action': 'list',
                                        'title': 'NIOS - GM'}
        try:
            response = session.get(config.unix_record_api,
                                    params=supported_actions,
                                    headers={'Content-type': 'text/xml'})
            res=response.text
            if res =='':
                logging.info("aut record not created")
            else:
                logging.info('verified authentication record has been created')
                assert True
        except requests.exceptions.HTTPError as err:
            logging.info("authentication is not happening")
            assert False
        logout_session(session)

    @pytest.mark.run(order=40)
    def test_040_authentication_scan(self):
        count=1
        for i in range(1,4):
            grid_status=ping_ip(config.grid_vip_lan_ipv4)
            #connector_status=ping_ip(config.connector_ip)
            connector_status=True
            if (grid_status == True) and (connector_status==True):
                session = requests.Session()
                logging.info('session created')
                session.headers.update({'X-Requested-With': 'Python Script'})
                status=q_session(session,username,password,session_url)
                if status == True:
                    scan_url = config.QUALYS_API_SCAN
                    scan_data = {'action': "launch", 'scan_title':scan_title,
                                'iscanner_name': config.SCANNER_NAME,'target_from': 'assets', 'asset_group_ids':group_id,
                                'option_title': config.VM_OPTION_PROFILE}
                    try:
                        response = session.post(scan_url, data=scan_data)
                        response.raise_for_status()
                        logging.info("scan started")
                        xmlreturn = ET.fromstring(response.text)
                        for elem in xmlreturn.findall('.//ITEM'):
                            if elem[0].text == 'REFERENCE':
                                scan_ref = elem[1].text
                                logging.info("Scan started with reference ID %s", scan_ref)
                                global scan_ref
                                response = logout_session(session)
                        break
                        assert True
                    except requests.exceptions.HTTPError as err:
                        logging.info("Scan initiation failed :%s", err)
                else:
                    logging.info("Test Case Execution Failed, not able to login")
                    assert False
                response = logout_session(session)
                #if grid status is up, start scan and come out
                assert True
            elif count<=2:
                sleep(120)
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if (grid_status == False) or (connector_status==False):
                    count=count+1
            else:
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if connector_status ==False:
                    subject="Qualys connector "+config.connector_ip+" is not up"
                    body="Qualys connector "+config.connector_ip+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"
                elif grid_status ==False:
                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                    ping_grid_send_mail(subject,body)
                    mail_status="sent mail"

    @pytest.mark.run(order=41)
    def test_041_get_scan_status_athenticated(self):
            status=['Finished', 'Queued', 'Running','Error','Canceled','Expired','Paused']
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,config.qusername,config.qpassword,config.session_url)
            checkStatus = check_scan_status(session,scan_ref,"scan")
            if checkStatus in status:
                timeout = time.time() + 3600
                resume=0
                while checkStatus != "Finished":
                    session = requests.Session()
                    session.headers.update({'X-Requested-With': 'Python Script'})
                    grid_status=ping_ip(config.grid_vip_lan_ipv4)
                    #connector_status=ping_ip(config.connector_ip)
                    connector_status=True
                    if (grid_status == False) or (connector_status==False):
                        sleep(120)
                        grid_status=ping_ip(config.grid_vip_lan_ipv4)
                        connector_status=True
                        if (grid_status == False) or (connector_status==False):
                            if mail_status !="sent mail":
                                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                                #connector_status=ping_ip(config.connector_ip)
                                connector_status=True
                                if connector_status ==False:
                                    subject="Qualys connector "+config.connector_ip+" is not up"
                                    body="Qualys connector "+config.connector_ip+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                elif grid_status ==False:
                                    subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                    ping_grid_send_mail(subject,body)
                                    mail_status="sent mail"
                                    break
                    else:
                        q_session(session,config.qusername,config.qpassword,config.session_url)
                        checkStatus = check_scan_status(session,scan_ref,"scan")
                        logging.info("Scan status: %s",checkStatus)
                        logging.info("cheking scan status:[error,canceled,Expired,Paused]")
                        if (checkStatus == 'Error') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'ERROR'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Canceled') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Canceled'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif (checkStatus == 'Expired') and (mail_status !="sent mail"):
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is showing 'Expired'"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        elif checkStatus == 'Paused' and resume <1:
                            scan_url = config.QUALYS_API_SCAN
                            scan_data = {'action': "resume", 'scan_ref': scan_ref}
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,username,password,session_url)
                            try:
                                response = session.post(scan_url, data=scan_data)
                                response.raise_for_status()
                                logging.info("restarted once ")
                                resume=resume+1
                            except requests.exceptions.HTTPError as err:
                                logging.error("not able to restart :%s", err)
                                response = logout_session(session)
                                break


                        elif checkStatus == 'Paused' and resume == 1:
                            session = requests.Session()
                            session.headers.update({'X-Requested-With': 'Python Script'})
                            q_session(session,config.qusername,config.qpassword,config.session_url)
                            subject="scan status is paused"
                            body="scan status is paused , once restrted but again paused for scan_ref: "+scan_ref+" report will not generate for authentication scan after service start, please check in GUI for more information."
                            ping_grid_send_mail(subject,body)
                            mail_status="sent mail"
                            response = logout_session(session)
                            break

                        # elif checkStatus == 'Queued':
                        #     sleep(300)
                        #     print(time.time(),timeout)
                        #     if time.time() > timeout:
                        #         print("Queued----------")
                        #         subject="Scan status is Queued from last 1 hour"
                        #         body="Scan status is Queued from last 1 hour"
                        #         ping_grid_send_mail(subject,body)
                        #         mail_status="sent mail"
                        #         break

                        elif checkStatus == "Finished":
                            #checkStatus_list.append(checkStatus)
                            logging.info("Scan job completed for :%s", scan_ref)
                            assert True
                        else:
                            logging.info("Scan in progress")
                            logging.info("Will check again after 5 minutes of sleep time\n")
                            time.sleep(300)
            else:
                subject=checkStatus
                body="Scan status is showing" +checkStatus
                ping_grid_send_mail(subject,body)
                mail_status="sent mail"
                assert False

    @pytest.mark.run(order=42)
    def test_042_download_vm_scan_results(self):
        global files
        files=[]
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'Python Script'})
        q_session(session,username,password,session_url)
        checkStatus = check_scan_status(session,scan_ref, "scan")
        if checkStatus == "Finished":
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,username,password,session_url)
            output_format = ["pdf","csv"]
            for format in output_format:
                params = {
                'action': "launch",
                'template_id': 4173070,
                'output_format': format,
                "report_refs": scan_ref
                }

                try:
                    response = session.post(config.QUALYS_REPORT, data=params)
                    response.raise_for_status()
                    myroot = ET.fromstring(response.text)
                    for x in myroot.findall(".//ITEM"):
                        if x[1].tag == "VALUE":
                            report_id = x[1].text
                            sleep(180)
                    type='qualys_athenticated_custom'
                    file_name=download_reports(session,report_id,format,type)
                    files.append(file_name)
                except requests.exceptions.HTTPError as err:
                    logging.error("Failed to launch report :%s", err)
                    assert False
        else:
            logging.error("Failed to launch report :%s", err)
            assert False

    @pytest.mark.run(order=43)
    def test_043_send_report_as_mail(self):
        data = MIMEMultipart()
        sender = 'jenkins@infoblox.com'
        receivers = mail_list
        data['Subject'] = "QUALYS_AUTHENTICATION_SCAN_REPORT_CUSTOM"
        data['From'] = sender
        data['To'] = ", ".join(receivers)
        body = "Please Analyse Qualys host scan custom report"
        data.attach(MIMEText(body, 'plain'))
        for i in files:
            path='/import/qaddi/QUALYS_SCAN_REPORTS'
            file_name=i
            logging.info("file_name: %s",file_name)
            attachment = open(file_name,"rb")
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((attachment).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', "attachment; filename="+file_name)
            data.attach(p)
            message = data.as_string()
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            logging.info("Successfully sent email")
            assert True
        except smtplib.SMTPException:
            logging.info("Error: unable to send email")
            assert False

    @pytest.mark.run(order=44)
    def test_044_clear_authentication(self):
        logging.info(unix_record_id_list)
        for i in unix_record_id_list:
            session = requests.Session()
            session.headers.update({'X-Requested-With': 'Python Script'})
            q_session(session,username,password,session_url)
            supported_actions = {'action': 'delete',
                                            'ids':i}
            try:
                response = session.post(config.unix_record_api,
                                        params=supported_actions,
                                        headers={'Content-type': 'text/xml'})
                res=response.raise_for_status()
                logging.info(res)
                logging.info("cleared authentication")
            except requests.exceptions.HTTPError as err:
                logging.info(err)
                return False
            logout_session(session)

class QUALYS_WAS_SCAN(unittest.TestCase):
    @pytest.mark.run(order=45)
    def test_045_launch_was_scan(self):
        headers = {"content-type: text/xml"}
        tree = ET.parse("file1.xml")
        tree.find('data/WasScan/name').text = "qualys_was_scan_"+file_name
        tree.write("file1.xml")
        sleep(30)
        with open('file1.xml') as xml:
            r1=requests.post(config.launch_url, auth=auth, data=xml)
            logging.info(r1.content)
            data_dict = xmltodict.parse(r1.content)
            json_data = json.dumps(data_dict)
            json_data=json.loads(json_data)
            logging.info(json_data)
            if json_data['ServiceResponse']['responseCode'] == "SUCCESS":
                global scan_id
                scan_id=json_data['ServiceResponse']['data']['WasScan']['id']
                logging.info("scan_id:%s",scan_id)
                assert True
            else:
                assert False

    @pytest.mark.run(order=46)
    def test_046_get_scan_status(self):
        status=['SUBMITTED','RUNNING', 'FINISHED','ERROR','CANCELED','PROCESSING']
        checkStatus = check_was_scan_status(str(scan_id))
        global was_scan_send_mail
        was_scan_send_mail=''
        if checkStatus in status:
            while checkStatus != "FINISHED":
                session = requests.Session()
                session.headers.update({'X-Requested-With': 'Python Script'})
                grid_status=ping_ip(config.grid_vip_lan_ipv4)
                #connector_status=ping_ip(config.connector_ip)
                connector_status=True
                if (grid_status == False) or (connector_status==False):
                    sleep(120)
                    grid_status=ping_ip(config.grid_vip_lan_ipv4)
                    connector_status=True
                    if (grid_status == False) or (connector_status==False):
                        if was_scan_send_mail !="sent mail":
                            grid_status=ping_ip(config.grid_vip_lan_ipv4)
                            #connector_status=ping_ip(config.connector_ip)
                            connector_status=True
                            if connector_status ==False:
                                subject="Qualys connector "+config.connector_ip+" is not up"
                                body="Qualys connector "+config.connector_ip+" is not up"
                                ping_grid_send_mail(subject,body)
                                was_scan_send_mail="sent mail"
                            elif grid_status ==False:
                                subject="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                body="Grid "+config.grid_vip_lan_ipv4+" is not up"
                                ping_grid_send_mail(subject,body)
                                was_scan_send_mail="sent mail"
                                break
                else:
                    checkStatus = check_was_scan_status(str(scan_id))
                    logging.info("Scan status: %s",checkStatus)
                    if (checkStatus == 'ERROR') and (was_scan_send_mail !="was sent mail"):
                        subject="scan status is showing 'ERROR'"
                        body="scan status is showing 'ERROR' "+scan_id+" report will not generate for WAS SCAN, please check in GUI for more information."
                        ping_grid_send_mail(subject,body)
                        was_scan_send_mail="sent mail"
                        break

                    elif (checkStatus == 'CANCELED') and (was_scan_send_mail !="sent mail"):
                        subject="scan status is showing 'Canceled'"
                        body="scan status is showing 'Canceled' "+scan_id+" report will not generate for WAS SCAN please check in GUI for more information."
                        ping_grid_send_mail(subject,body)
                        was_scan_send_mail="sent mail"
                        break

                    elif checkStatus == "FINISHED":
                        logging.info("Scan job completed for :%s", scan_id)
                        assert True
                    else:
                        logging.info("WAS scan in progress")
                        logging.info("Will check again after 6 minutes of sleep time\n")
                        time.sleep(360)
        else:
            subject=checkStatus
            body="Scan status is showing" +checkStatus
            ping_grid_send_mail(subject,body)
            was_scan_send_mail="sent mail"
            assert False

    @pytest.mark.run(order=47)
    def test_047_create_report(self):
        types=['PDF','CSV']
        global reports
        reports=[]
        for i in types:
            headers = {"content-type: text/xml"}
            tree = ET.parse("report.xml")
            root = tree.getroot()
            root[0][0][0].text='qualys_was_scan_'+file_name
            root[0][0][1].text=i
            root[0][0][3][0][0][0][0][0].test=scan_id
            tree.write("report.xml")
            with open('report.xml') as xml:
                r1=requests.post(config.was_report_url, auth=auth, data=xml)
                data_dict = xmltodict.parse(r1.content)
                json_data = json.dumps(data_dict)
                json_data=json.loads(json_data)
                if json_data['ServiceResponse']['responseCode'] == "SUCCESS":
                    global report_id
                    type_and_id={}
                    report_id=json_data['ServiceResponse']['data']['Report']['id']
                    type_and_id['id']=report_id
                    type_and_id['file_type']=i
                    logging.info(type_and_id)
                    reports.append(type_and_id)
        logging.info(reports)
        if len(reports) !=0:
            assert True
        else :
            assert False

    @pytest.mark.run(order=48)
    def test_048_download_reports(self):
        file_name="-".join(build_name.split("-", 3)[:3])
        file_name=file_name
        global was_report_files
        was_report_files=[]
        headers = {"Accept": "application/xml"}
        logging.info(reports)
        for i in reports :
            url=config.was_report_status_url+i['id']
            r1=requests.get(url, auth=auth, headers=headers)
            data_dict = xmltodict.parse(r1.content)
            json_data = json.dumps(data_dict)
            json_data=json.loads(json_data)
            logging.info(json_data)
            if json_data['ServiceResponse']['responseCode'] == "SUCCESS":
                sleep(300)
                if json_data['ServiceResponse']['data']['Report']['status']=='COMPLETE':
                    if i['file_type']=='PDF':
                        file="qualys_was_scan_"+file_name+".pdf"
                        logging.info("file:",file)
                        url = config.was_report_download+i['id']
                        r1=requests.get(url, auth=auth, headers=headers)
                        my_file=open(file, 'w')
                        my_file.write(r1.content)
                        was_report_files.append(file)
                    elif i['file_type']=='CSV':
                        file="qualys_was_scan_"+file_name+".csv"
                        url = config.was_report_download+i['id']
                        r1=requests.get(url, auth=auth, headers=headers)
                        my_file=open(file, 'w')
                        my_file.write(r1.content)
                        was_report_files.append(file)
                    else:
                        assert false
        logging.info(was_report_files)
        for i in was_report_files:
            logging.info("report file:%s",i)
            try:
                child = pexpect.spawn("scp "+i+' '+config.DOWNLOAD_PATH)
                child.logfile=sys.stdout
                child.expect('Are you sure you want to continue connecting (yes/no)?',timeout=None)
                child.sendline('yes')
                c=child.before
                logging.info("your was report file :"+i+"  copied to "+config.DOWNLOAD_PATH)
            except Exception as e:
                c = False
            if c:
                pass
            else:
                logging.info("Copying files to "+config.DOWNLOAD_PATH)
                dig_cmd = "scp "+i+' '+config.DOWNLOAD_PATH
                dig_result = subprocess.check_output(dig_cmd, shell=True)
                assert re.search(r'',str(dig_result))
                logging.info("your report file :"+i+"  copied to "+config.DOWNLOAD_PATH)
        logging.info("Test Case Execution Completed")
        sleep(5)

    @pytest.mark.run(order=49)
    def test_049_send_report_as_mail(self):
        logging.info(was_report_files)
        data = MIMEMultipart()
        sender = 'jenkins@infoblox.com'
        receivers = mail_list
        data['Subject'] = "WAS SCANNING REPORT"
        data['From'] = sender
        data['To'] = ", ".join(receivers)
        body = "Please Analyse Qualys WAS scan results"
        data.attach(MIMEText(body, 'plain'))
        for i in was_report_files:
            path='/import/qaddi/QUALYS_SCAN_REPORTS'
            file_name=i
            logging.info("file_name: %s",file_name)
            attachment = open(file_name,"rb")
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((attachment).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', "attachment; filename="+file_name)
            data.attach(p)
            message = data.as_string()
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            logging.info("Successfully sent email")
            assert True
        except smtplib.SMTPException:
            logging.info("Error: unable to send email")
            assert False


class nmap(unittest.TestCase):
    @pytest.mark.run(order=50)
    def test_050_run_nmap_scan(self):
        file_name="-".join(build_name.split("-", 3)[:3])
        file_name=file_name
        try:
            global nmap_file
            nmap_file=file_name+"_nmap_report.txt"
            os.system("nmap -p 1-65535 -T4 -A -v -PE -PS22,25,80 -PA21,23,80,3389 "+config.grid_vip_lan_ipv4+" > "+nmap_file)
            child = pexpect.spawn("scp "+nmap_file+' '+config.DOWNLOAD_PATH)
            logging.info("your nmap report file :"+nmap_file+"  copied to "+config.DOWNLOAD_PATH)
        except requests.exceptions.HTTPError as err:
            logging.error("Failed to execute nmap scan :%s", err)
            assert False

    @pytest.mark.run(order=51)
    def test_051_send_report_as_mail(self):
        data = MIMEMultipart()
        sender = 'jenkins@infoblox.com'
        receivers = mail_list
        data['Subject'] = "NMAP SCANNING REPORT"
        data['From'] = sender
        data['To'] = ", ".join(receivers)
        body = "Please Analyse NMAP scan results"
        data.attach(MIMEText(body, 'plain'))
        path='/import/qaddi/QUALYS_SCAN_REPORTS'
        logging.info("file_name: %s",nmap_file)
        attachment = open(file_name,"rb")
        p = MIMEBase('application', 'octet-stream')
        p.set_payload((attachment).read())
        encoders.encode_base64(p)
        p.add_header('Content-Disposition', "attachment; filename="+nmap_file)
        data.attach(p)
        message = data.as_string()
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            logging.info("Successfully sent email")
            assert True
        except smtplib.SMTPException:
            logging.info("Error: unable to send email")
            assert False

