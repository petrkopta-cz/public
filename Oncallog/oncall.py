import tkinter as tk
import paramiko
import requests
import configparser
import csv
from tkinter import font
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import QName


config = configparser.ConfigParser()
config.read('config.ini')

phone_list = config.get('VAR','phone_list')
cfdbtn_txt = config.get('VAR','config_button_text')
icibtn_txt = config.get('VAR','icinga_button_text')
resizable = config.get('VAR','resizable')

# Create a new tkinter window
root = tk.Tk()
root.title("OnCall Duty Manager")
root.geometry("400x300")
root.resizable(resizable, resizable)



    

# Create a function to manage call forwarding
def manage_call_forwarding():
    # CHECK FILE
    ws_set = config.get('SOAP','set_file')
    set_webservice_file = open(ws_set, "r")
    set_xml_string = set_webservice_file.read()
    set_webservice_file.close()
    
    # CALL WS
    set_action = config.get('SOAP','set_soapaction')
    set_host = config.get('SOAP','set_host')

    set_user = config.get('SOAP','set_user')
    set_pass = config.get('SOAP','set_password')
    set_credentials = (set_user, set_pass)
    set_url = config.get('SOAP','set_url')
    custom_headers = {
        "SOAPAction": set_action,
        "Content-Type": "text/xml;charset=UTF-8",
        "Accept-Encoding": "gzip,deflate",
        "Host":set_host,
        "Connection": "Keep-Alive",
        "User-Agent": "Apache-HttpClient/4.5.5 (Java/12.0.1)",
        "Authorization": "Basic"
    }
    
    oncall_num = config.get('VAR','oncallnumber')
    myphone = config.get('VAR','myphone')
    
    set_webservice_xml = set_xml_string.replace(
        '{ONCALL}',oncall_num
    )
    set_webservice_xml = set_webservice_xml.replace(
        '{FWD}',myphone
    )    
    response = requests.post(set_url, data=set_webservice_xml, auth=set_credentials, headers=custom_headers)
	
    #print("XML Request:", set_webservice_xml)
    #print("XML Response:", response.text)
	
    # RETURN VALUE
    if response.status_code == 200:
        # Parse the XML response
        root = ET.fromstring(response.content)
        namespaces = {"ns1": "http://www.vodafone.cz/Common/xml/Common"}
        status_elements = root.findall(".//ns1:returnStatus",namespaces)
        if status_elements:
            status_text = status_elements[0].text
        else:
            status_text = "Failed - cannot find element"
    else:
        status_text = "Webservice call failed"

    current_duty_number = read_oncall_duties()
    current_duty_person = find_person(current_duty_number)
    
    lbl_text = "Oncall : " + current_duty_number + " " + current_duty_person
    oncall_duties_label.config(text=lbl_text)
    
    return status_text


# GET CURRENT FORWARDED NUMBER FROM IL
def read_oncall_duties():
    # CHECK FILE
    ws_get = config.get('SOAP','get_file')
    get_webservice_file = open(ws_get, "r")
    get_xml_string = get_webservice_file.read()
    
    oncall_num = config.get('VAR','oncallnumber')
    myphone = config.get('VAR','myphone')
    
    get_webservice_xml = get_xml_string.replace(
        '{ONCALL}',oncall_num
    )
    
    get_webservice_file.close()
    
    # CALL WS
    get_action = config.get('SOAP','get_soapaction')
    get_host = config.get('SOAP','get_host')

    get_user = config.get('SOAP','get_user')
    get_pass = config.get('SOAP','get_password')
    get_credentials = (get_user, get_pass)
    get_url = config.get('SOAP','get_url')
    custom_headers = {
        "SOAPAction": get_action,
        "Content-Type": "text/xml;charset=UTF-8",
        "Accept-Encoding": "gzip,deflate",
        "Host":get_host,
        "Connection": "Keep-Alive",
        "User-Agent": "Apache-HttpClient/4.5.5 (Java/12.0.1)",
        "Authorization": "Basic"
    }
    response = requests.post(get_url, data=get_webservice_xml, auth=get_credentials, headers=custom_headers)
	
    #print("XML Request:", get_webservice_xml)
    #print("XML Response:", response.text)
	
    # RETURN VALUE
    if response.status_code == 200:
        # Parse the XML response
        root = ET.fromstring(response.content)
        namespaces = {"cas": "http://www.vodafone.cz/ComptelAdapter/xml/Services/1.1"}
        unconditional_voice_elements = root.findall(".//cas:unconditionalVoice",namespaces)
        if unconditional_voice_elements:
            unconditional_voice_text = unconditional_voice_elements[0].text
        else:
            unconditional_voice_text = "Failed - cannot find number"
    else:
        unconditional_voice_text = "Webservice call failed"
    return unconditional_voice_text



# CHECK PERSON BASED ON MSISDN
def find_person(msisdn):
    found = "not found"
    with open(phone_list) as f:
        for line in f:
            line = line.strip()
            if line:
                number, name = line.split(",")
                if number == msisdn:
                    found = name
    return found

# GET ALL NUMBERS AND NAMES
def get_phone_list():
    phone_list_arr = []
    with open(phone_list) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            number, name = row
            phone_list_arr.append((number, name))
    return phone_list_arr


# UPDATE ARRAY OF ICINGA NUMBERS
def update_icinga_array(var_dict, content):
    numbers = []
    with open(phone_list) as list:
        reader = csv.reader(list)
        for row in reader:
            number, name = row
            if number in var_dict:
                is_checked = var_dict[number].get()
                if is_checked:
                    numbers.append(number)
    return numbers

# CREATE ICINGA CONNECTION
def icinga_connection():
    # SET VALUES
    ssh_host = config.get('SSH','host')
    ssh_username = config.get('SSH','user')
    ssh_key_filename = config.get('SSH','key_file')
    ssh_port = config.get('SSH','port')
    
    
    # CONNECT
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_key = paramiko.RSAKey.from_private_key_file(ssh_key_filename)
    ssh_client.connect(hostname=ssh_host, username=ssh_username, pkey=ssh_key, disabled_algorithms=dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"]))
    
    return ssh_client

# WRITE THE MSISDNS TO ICINGA FILE
def update_ssh_file(contents):
    icinga = icinga_connection()
    # Open a new SFTP session
    sftp = icinga.open_sftp()
    # Open the remote file for writing
    file_path = config.get('SSH','file')
    with sftp.open(file_path, "w") as f:
        # Write the contents to the file
        f.write(contents)
    # Close the SFTP session and the SSH client
    sftp.close()
    icinga.close()

# UPDATE LABEL
def update_lbl(lbl,txt):
    lbl.config(text = txt)

# HANDLE THE CHANGE OF ICINGA MSISDNS
def save_checked_numbers(var_dict, content, label):
    new_arr = update_icinga_array(var_dict, content)
    str_to_write = " ".join(new_arr)
    #print(str_to_write)
    update_ssh_file(str_to_write)
    txt = read_icinga_file_contents()
    update_lbl(label,txt)


# GET NUMBERS FROM ICINGA MONITORING
def read_icinga_file_contents():
    icinga = icinga_connection()
    
    # READ FILE
    file_path = config.get('SSH','file')
    _, stdout, _ = icinga.exec_command(f"cat {file_path}")
    file_contents = stdout.read().decode().strip()
    icinga.close()
    
    return file_contents

# OPEN ICINGA WINDOW 
def open_icinga_window():
    content = read_icinga_file_contents()
    icinga_window = tk.Toplevel(root)
    caption = tk.Label(icinga_window, text = "ICINGA SMS file content:")
    caption.pack()
    icinga_window.geometry("400x300")
    icinga_window.resizable(False, False)
    icinga_label = tk.Label(icinga_window, text = "")
    icinga_label.pack()
    
    icinga_file_contents = read_icinga_file_contents()
    lbl2_text = icinga_file_contents
    update_lbl(icinga_label,lbl2_text)
    
    # LIST NAMES
    var_dict = {}
    phone_label = tk.Label(icinga_window, text='Phone Numbers:')
    phone_label.config(width = 50, height = 3, font=("Arial",12,"bold"))
    phone_label.pack()
    
    phone_list_arr = get_phone_list()
    
    for number, name in phone_list_arr:
        var = tk.BooleanVar(value=number in content)
        var_dict[number] = var
        cb = tk.Checkbutton(icinga_window, text=name, variable=var)
        cb.pack(anchor='w')
    save_button = tk.Button(icinga_window, text='Save', command=lambda: save_checked_numbers(var_dict, phone_list_arr, icinga_label))
    save_button.pack()   
 

# Create a label to display the result of the get_webservice call
current_duty_number = read_oncall_duties()
current_duty_person = find_person(current_duty_number)

lbl_text = "Oncall : " + current_duty_number + " " + current_duty_person
oncall_duties_label = tk.Label(root, text=lbl_text)
#oncall_duties_label.config(pady=50)
oncall_duties_label.config(width = 50, height = 2, font=("Arial",12,"bold"))
oncall_duties_label.grid(row=0, column=0, sticky="nsew")
#oncall_duties_label.pack()


# BTN TO FORWARD ON ME
call_forwarding_button = tk.Button(root, text=cfdbtn_txt, command=manage_call_forwarding, width=20, height=3, bg='#333333', fg='#ffffff')
call_forwarding_button['font'] = font.Font(family='Arial')
call_forwarding_button.grid(row=1, column=0, sticky="nsew", pady=10, padx=20)
#call_forwarding_button.pack()

# BUTTON TO OPEN ICINGA FILE HANDLER
ici_btn = tk.Button(root, text=icibtn_txt, command=open_icinga_window, width=20, height=3, bg='#333333', fg='#ffffff')
ici_btn['font'] = font.Font(family='Arial')
ici_btn.grid(row=2, column=0, sticky="nsew", pady=10, padx=20)
#ici_btn.pack()

#root.grid_rowconfigure(0, minsize=10)
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Start the tkinter mainloop
root.mainloop()
