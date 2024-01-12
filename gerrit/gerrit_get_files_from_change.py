'''
find all changed files of every changes in gerrit

author: s1mple-child
'''
import json
import sys
import requests


# find changed files via gerrit REST API
def get_changed_files(gerrit_ip, project_name, branch_name, change_id, revision_id):
    """
    get changed files from change in gerrit
    :param gerrit_ip: gerrit ip address
    :param project_name: project name of change
    :param branch_name: target branch name of change
    :param change_id: change id
    :param revision_id: revision of change 
    """
    files_list = []
    # create http request session
    http_session = create_access_session(gerrit_ip)
    # set gerrit port
    gerrit_port = set_gerrit_port(gerrit_ip)

    # replace '/' in project_name for http request
    if '/' in project_name:
        project_name = project_name.replace('/', '%2F')
    files_finding_response = http_session.get('http://' + gerrit_ip + ':' + gerrit_port + '/a/changes/' 
    + project_name + '~' + branch_name + '~' + change_id + '/revisions/' + revision_id 
    + '/files/').text.replace(')]}\'', '')
    for key in json.loads(files_finding_response):
        files_list.append(key)

    print(files_list)


# create http access session in gerrit
def create_access_session(gerrit_ip):
    """
    create http access session for http request in gerrit
    :param gerrit_ip: gerrit ip address
    :return: session: a session to request with gerrit admin username and http credential
    """
    # set admin username and http credential in gerrit with different gerrit instances
    gerrit_admin_username, gerrit_admin_http_cred = set_admin_username_n_http_cred(gerrit_ip)
    # create session
    session = requests.Session()
    session.auth = (gerrit_admin_username, gerrit_admin_http_cred)

    return session

# in my use case, gerrit always have diffenent ports after deployed
# set port number with given gerrit ip address
def set_gerrit_port(gerrit_ip):
    """
    set gerrit port with given gerrit ip address
    :param gerrit_ip: gerrit ip address
    :return: gerrit_port: port number of gerrit
    """
    gerrit_port = ''
    if gerrit_ip == 'gerrit.ip.addr.1':
        gerrit_port = '1111'
    elif gerrit_ip == 'gerrit.ip.addr.2':
        gerrit_port = '2222'
    return gerrit_port


# set admin user name and http credential
def set_admin_username_n_http_cred(gerrit_ip):
    """
    set gerrit system administrator username and http credential
    :param gerrit_ip: gerrit ip address
    :return: admin_user_name: username of gerrit system administrator
    :return: admin_http_cred: http credential of this gerrit administrator
    """
    admin_user_name = ''
    admin_http_cred = ''
    if gerrit_ip == 'gerrit.ip.addr.1':
        admin_user_name = 'user1'
        admin_http_cred = 'http_cred1'
    elif gerrit_ip == 'gerrit.ip.addr.2':
        admin_user_name = 'user2'
        admin_http_cred = 'http_cred2'
    
    return admin_user_name, admin_http_cred


get_changed_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
