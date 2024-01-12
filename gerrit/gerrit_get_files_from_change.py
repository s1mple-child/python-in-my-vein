'''
find all changed files of every changes in gerrit

author: s1mple-child
'''
import json
import sys
import requests
from migrate_from_gitlab_2gerrit import create_access_session, set_gerrit_port


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


get_changed_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
