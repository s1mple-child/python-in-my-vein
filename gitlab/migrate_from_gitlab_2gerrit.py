'''
Migrate repositories only from GitLab to Gerrit

Author: s1mple-child

Step 1: find all projects under given group
Step 2: create all projects in gerrit
'''
import json
import sys
import requests
import massedit


# create a project in gerrit which name is group name in gitlab
# this project created only inherate permission from other projects under this project
def create_parent_project_in_gerrit(gerrit_ip, parent_project_name, group_owner, access_rights_json_full_path):
    """
    create project as parent project for access inheriting 
    :param gerrit_ip: gerrit ip address
    :param parent_project_name: name of project created in gerrit
    :param group_owner: owner of gerrit group
    :param access_rights_json_full_path: full path of access rights template json file
    """
    gerrit_port = set_gerrit_port(gerrit_ip)
    parent_project_description = 'Parent project for ' + parent_project_name + ' child projects.'
    admin_group_name = 'Administrators'

    # find 'Administrators' group id in gerrit
    admin_group_finding_response = find_group_in_gerrit(gerrit_ip, admin_group_name)
    admin_group_id = json.loads(admin_group_finding_response)[0]['group_id']

    # find project in gerrit
    # create project when the response is empty
    find_parent_project_response = find_project_in_gerrit(gerrit_ip, parent_project_name)
    if len(json.loads(find_parent_project_response)) != 0:
        print('Parent project' + parent_project_name + ' already existed.')
    # some parent_project_name contains '/' which means this 'parent project' is a 'child project' actually
    # when create this project, set project name in front of '/' as parent in json data used in http request data
    elif '/' in parent_project_name:
        actual_parent = parent_project_name.split('/')[0]
        parent_project_name = parent_project_name.replace('/', '%2F')
        # create project
        http_session = create_access_session(gerrit_ip)
        http_session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/projects/' + parent_project_name,
        json={
            "parent": actual_parent,
            "description": parent_project_description,
            "owners": [admin_group_id],
            "permission_only": True
        })
        create_access_rights_in_parent(gerrit_ip, parent_project_name, group_owner, access_rights_json_full_path)
    else:
        http_session = create_access_session(gerrit_ip)
        http_session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/projects/' + parent_project_name,
        json={
            "description": parent_project_description,
            "owners": [admin_group_id],
            "permission_only": True
        })
        create_access_rights_in_parent(gerrit_ip, parent_project_name, group_owner, access_rights_json_full_path)


# create project in gerrit with given project name
def create_project_in_gerrit(gerrit_ip, parent_group_name, group_name, project_name, project_admin):
    """
    create project with given project name in gerrit as well as group which contains administrators of new project
    :param gerrit_ip: gerrit ip address
    :param parent_group_name: name of parent group
    :param group_name: name of group
    :param project_name: name of project
    :param project_admin: admin username of project
    """
    # create session for http request
    http_session = create_access_session(gerrit_ip)
    # set gerrit port
    gerrit_port = set_gerrit_port(gerrit_ip)

    if parent_group_name != '':
        group_name = parent_group_name + '/' + group_name

    new_project_name = group_name + '/' + project_name
    # find id of new project's admin group in gerrit
    admin_group_id = create_group_all_admins(gerrit_ip, group_name, project_admin)
    if '/' in new_project_name:
        new_project_name = new_project_name.replace('/', '%2F')
    
    http_session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/projects/' + new_project_name, 
    json={
        "parent": group_name,
        "owners": [admin_group_id]
    })
    print('Project ' + group_name + '/' + project_name + ' created in gerrit.\n')


# iterate projects list and create project to given group in gerrit
def create_separate_project_in_gerrit(gerrit_ip, group_name, project_admin, projects_list):
    """
    parse projects list and create project in projects_list in gerrit
    :param gerrit_ip: gerrit ip address
    :param group_name: name of group
    :param project_admin: admin username of project
    :param projects_list: a list contains all projects need to create in gerrit
    """
    parent_group_name = ''
    # convert projects_list from string representation of list to list
    projects_list = projects_list.strip('][').split(', ')

    # iterate in projects_list
    for project in projects_list:
        project_full_name = group_name + '/' + project
        # check project in gerrit
        project_finding_response = find_project_in_gerrit(gerrit_ip, project_full_name)
        if len(json.loads(project_finding_response)) != 0:
            # project already existed
            pring(project_full_name + ' is already existed.')
        else:
            # project not found
            print('Creating ' + project_full_name + ' in gerrit.')
            if '/' in group_name:
                parent_group_name = group_name.split('/')[0]
                group_name = group_name.split('/')[1]
                # create project
                create_project_in_gerrit(gerrit_ip, parent_group_name, group_name, project, project_admin)


# create access rights in gerrit
def create_access_rights_in_parent(gerrit_ip, parent_project_name, group_owner, access_rights_json_full_path):
    """
    use template json file to create access rights in new project
    :param gerrit_ip: gerrit ip address
    :param parent_project_name: name of project created in gerrit
    :param group_owner: owner of gerrit group
    :param access_rights_json_full_path: full path of access rights template json file
    """
    gerrit_port = set_gerrit_port(gerrit_ip)
    parent_group_id =  create_group_all_members(gerrit_ip, parent_project_name, group_owner)

    # find UUID of 'Service Users' group in gerrit
    service_users_group_name = 'Service Users'
    service_users_group_id = json.loads(find_group_in_gerrit(gerrit_ip, service_users_group_name))[0]['id']

    # replace access rights file content
    # use massedit to replace some stable values to group UUID
    # template json loadted in template_json directory
    source_json = [access_rights_json_full_path]
    massedit.edit_files(source_json, ["re.sub('Team-Group-UUID', '" + parent_group_id + "', line)"], dry_run=False)
    massedit.edit_files(source_json, ["re.sub('Service-Users-UUID', '" + service_users_group_id + "', line)"], dry_run=False)
    # read json with changed values of group UUID
    with open(access_rights_json_full_path) as f:
        data = json.loads(f.read())
    # set access right with json data
    session = create_access_session(gerrit_ip)
    if '/' in parent_project_name:
        parent_project_name = parent_project_name.replace('/', '%2F')
    access_set_response = session.post('http://' + gerrit_ip + ':' + gerrit_port + '/a/projects/' + parent_project_name + '/access', 
    json=data).text.replace(')]}\'', '')
    project_access_revision = json.loads(response)["revision"]
    print('Access rights rights applied. The revision of access right is ' + project_access_revision)


# create group that contains all members of project
def create_group_all_members(gerrit_ip, parent_project_name, group_owner):
    """
    create group that all members of project in this group 
    :param gerrit_ip: gerrit ip address
    :param parent_project_name: name of project created in gerrit
    :param group_owner: owner of gerrit group
    :return: group_id: id of new group
    """
    # set gerrit port from given gerrit ip address
    gerrit_port = set_gerrit_port(gerrit_ip)
    # add this member as owner
    # because user can't set as owner when creat from gerrit REST API
    # add this user in new group 
    group_owner_id = find_user_id_in_gerrit(gerrit_ip, group_owner)
    # change ' ' in group name to %20 for http request
    group_name = 'Team%20' + parent_project_name
    group_description = 'All members of ' + parent_project_name + ' team.'

    # check group
    find_group_response = find_group_in_gerrit(gerrit_ip, group_name)
    if len(json.loads(find_group_response)) != 0:
        # group exist, find its id
        group_id = json.loads(find_group_response)[0]['id']
    else:
        # group not found, create this group
        session = create_access_session(gerrit_ip)
        if '/' in parent_project_name:
            group_name = group_name.replace('/', '%2F')
        create_group_response = session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/groups/' + group_name, 
        json={"description": group_description, "members": [group_owner_id]}).text.replace(')]}\'', '')
        group_id = json.loads(create_group_response)['id']
        # add 'Administrator' account to new group
        gerrit_admin_username = set_admin_username_n_http_cred(gerrit_ip)[0]
        gerrit_admin_id = find_user_id_in_gerrit(gerrit_ip, gerrit_admin_username)
        session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/groups/' + group_id + '/members/' + str(gerrit_admin_id))
    
    return group_id


# create group that contains all administrators of new project
def create_group_all_admins(gerrit_ip, group_name, member_name):
    """
    create new group that contains all administrators of new project
    :param gerrit_ip: gerrit ip address
    :param group_name: group name that need to create new admin group it can also regard as project
    :param member_name: one member of new admin group
    :return: group_id: new admin group id
    """
    # admin group name
    admin_group_name = 'Group' + group_name + ' Administrators'
    # gerrit port
    gerrit_port = set_gerrit_port(gerrit_ip)
    # find member id of given member name
    member_id = find_user_id_in_gerrit(gerrit_ip, member_name)
    # http session
    http_session = create_access_session(gerrit_ip)

    admin_group_finding_response = http_session.get('http://' + gerrit_ip + ':' + gerrit_port + '/a/groups/?query=name:"' 
    + admin_group_name + '"').text.replace(')]}\'','')
    
    if len(json.loads(admin_group_finding_response)) != 0:
        # group already existed
        print('Group ' + admin_group_name + ' already existed, find its id.')
        group_id = json.loads(admin_group_finding_response)[0]['id']
    else:
        # group not found, create one
        print('Create group ' + admin_group_name + ' in gerrit.')
        # convert ' ' and '/' to '%20' and '%2F' for http request
        if '/' in admin_group_name:
            admin_group_name = admin_group_name.replace('/', '%2F')
        if ' ' in admin_group_name:
            admin_group_name = admin_group_name.replace(' ', '%20')
        
        group_creating_response = http_session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/groups/' + admin_group_name, 
        json={
            "description": "Administrators for " + admin_group_name + " group.",
            "members": [member_id]
        }).text.replace(')]}\'', '')
        group_id = json.loads(group_creating_response)['id']
    
    # when use above code create group which name contains '/', the subgroup not in parent group 
    # set subgroup under its parent group
    if '/' in group_name:
        # find parent administrators group id
        parent_admin_group_name = 'Group ' + group_name.split('/')[0] + ' Administrators'
        parent_admin_group_finding_response = http_session.get('http://' + gerrit_ip + ':' + gerrit_port 
        + '/a/groups/?query=name:"' + parent_admin_group_name + '"').text.replace(')]}\'', '')
        parent_admin_group_id = json.loads(parent_admin_group_finding_response)[0]['id']
        # create subgroup under parent group
        http_session.put('http://' + gerrit_ip + ':' + gerrit_port + '/a/groups/' + parent_admin_group_id + '/groups/' + group_id)
    
    return group_id


# check project create parameter
def check_project_create_para(gitlab_ip, gerrit_ip, group_name, project_admin, project_create_para):
    """
    check project create parameter(all or separate projects list) and revoke different methods
    :param gitlab_ip: gitlab ip address
    :param gerrit_ip: gerrit ip address
    :param group_name: name of group
    :param project_admin: admin username of project
    :param project_create_para: all or a list contains all projects need to create in gerrit
    """
    if project_create_para = 'all':
        # create all projects with given gitlab group in gerrit
        total_created_project = find_project_in_gitlab(gitlab_ip, gerrit_ip, group_name, project_admin)
        print('Total number of created projects is: ' + str(total_created_project))
    else:
        # create separate projects
        # pattern of project_create_para is ['proj_a', 'proj_b', ...]
        create_separate_project_in_gerrit(gerrit_ip, group_name, project_admin, project_create_para)


# find user id in gerrit
def find_user_id_in_gerrit(gerrit_ip, member_name):
    """
    find user id use given username
    :param gerrit_ip: gerrit ip address
    :param member_name: account name in gerrit 
    :return: account_id: account id of given member_name
    """
    gerrit_port = set_gerrit_port(gerrit_ip)
    http_session = create_access_session(gerrit_ip)
    # request for user via gerrit REST API
    user_response = session.get('http://' + gerrit_ip + ':' + gerrit_port + '/accounts/' + member_name).text.replace(')]}\'', '')
    account_id = json.loads(user_response)['_account_id']
    return account_id


# find group in gerrit with given group name
def find_group_in_gerrit(gerrit_ip, group_name):
    """
    return http response of group request via gerrit REST API
    :param gerrit_ip: gerrit ip address
    :param group_name: name of group to find in gerrit
    :return: find_group_response: response text after request via gerrit REST API
    """
    gerrit_port = set_gerrit_port(gerrit_ip)
    # create http access session in gerrit
    http_session = create_access_session(gerrit_ip)
    # request via gerrit API
    # in 3.x gerrit, at the beginning of response text contains ')]}', should remove them with string.replace
    find_group_response = http_session.get('http://' + gerrit_ip + ':' + gerrit_port 
    + '/a/groups/?query=name:"' + group_name + '"').text.replace(')]}\'', '')

    return find_group_response


# find group in gitlab
def find_group_in_gitlab(gitlab_ip, group_name):
    """
    return group id with given group name
    :param gitlab_ip: gitlab ip address
    :param group_name: group name in gitlab
    :return: group_id: group id of given group
    """
    # set gitlab access token
    gitlab_access_token = set_gitlab_access_token()
    # request via gitlab REST API
    group_finding_response = requests.get('http://' + gitlab_ip + '/api/v4/groups?private_token=' + gitlab_access_token 
    + '&search=' + group_name).text
    # get group id from response text
    group_id = json.loads(group_finding_response)[0]["id"]

    return group_id

# find project in gerrit with given project name
def find_project_in_gerrit(gerrit_ip, project_name):
    """
    return response of project with given project name
    :param gerrit_ip: gerrit ip address
    :param project_name: name of project to find in gerrit
    :return: find_project_response: response text after request via gerrit REST API
    """
    gerrit_port = set_gerrit_port(gerrit_ip)
    http_session = create_access_session(gerrit_ip)
    # convert '/' to '%2F' which project name with '/'
    if '/' in project_name:
        project_name = project_name.replace('/', '%2F')
    find_project_response = http_session.get('http://' + gerrit_ip + ':' + gerrit_port 
    + '/a/projects/?query=name:"' + project_name + '"').text.replace(')]}\'', '')

    return find_project_response

# find project in gitlab
def find_project_in_gitlab(gitlab_ip, gerrit_ip, group_name, project_admin):
    """
    find projects under given group in gitlab then create them in gerrit
    :param gitlab_ip: gitlab ip address
    :param gerrit_ip: gerrit ip address
    :param group_name: group in gitlab
    :param project_admin: admin of project
    :return: count: number of created projects
    """
    # some project name contains '/', split this and first part of it is parent group name in gitlab
    # another is the subgroup name in gitlab
    parent_group_name = ''
    if '/' in group_name:
        parent_group_name = group_name.split('/')[0]
        group_name = group_name.split('/')[1]
    # use group name to find group id in gitlab
    group_id = find_group_in_gitlab(gitlab_ip, group_name)
    # gitlab access token
    gitlab_access_token = set_access_token_gitlab(gitlab_ip)

    page = 1
    count = 0
    while True:
        # one page have 20 results aka projects, so set page when projects count is more than 20
        projects_under_group_response = requests.get('http://' + gitlab_ip + '/api/v4/groups/' + str(group_id) 
        + 'projects?private_token=' + gitlab_access_token + '&page=' + str(page)).text
        # exit when response json is not valid
        if not json.loads(projects_under_group_response):
            break
        # iterate project and create project in gerrit
        for i in range(len(response_json)):
            project_name = json.loads(projects_under_group_response)[i]['name']
            print('Project ' + project_name + ' is under ' + group_name + ' of gitlab.')
            create_project_in_gerrit(gerrit_ip, parent_group_name, group_name, project_name, project_admin)
            count += 1
        page += 1

    return count
    

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


# set access token with given gitlab ip address
def set_access_token_gitlab(gitlab_ip):
    """
    set access token with given gitlab ip address
    :param gitlab_ip: gitlab ip address
    :return: gitlab_access_token: access token for given gitlab ip address 
    """
    # replace them with actual ip address and access token value
    gitlab_access_token = ''
    if gitlab_ip == 'one.gitlab.ip.addr':
        gitlab_access_token = 'token_1'
    elif gitlab_ip == 'two.gitlab.ip.addr':
        gitlab_access_token = 'token_2'

    return gitlab_access_token


"""
:parameter
sys.argv[1]: gitlab(source) instance ip address
sys.argv[2]: gerrit(target) instance ip address
sys.argv[3]: group name of gitlab
sys.argv[4]: username of admin group in gerrit
sys.argv[5]: access rights template json file full path
sys.argv[6]: create projects option: all or separated projects
"""
create_parent_project_in_gerrit(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
check_project_create_para(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[6])
