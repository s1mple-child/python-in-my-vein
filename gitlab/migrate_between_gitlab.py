'''
Migrate repositories between 2 gitlab

This used for different version(big gap of version) of gitlab. If they have same version or other situations, 
you can use mirror feature in gitlab.

Author: s1mple-child

'''
import json
import sys
import requests
from migrate_from_gitlab_2gerrit import set_access_token_gitlab, find_group_in_gitlab


# find projects under given group name in gitlab
def find_all_projects_in_gitlab(source_gitlab_ip, target_gitlab_ip, group_name):
    """
    find all projects under given group in gitlab then create all of them in target gitlab
    :param source_gitlab_ip: source gitlab ip address
    :param target_gitlab_ip: target gitlab ip address
    :param group_name: group name need to find in gitlab
    """
    # set access token for http request
    gitlab_access_token = set_access_token_gitlab(source_gitlab_ip)
    if '/' in group_name:
        group_name = group_name.replace('/', '%2F')

    target_group_id = find_group_in_gitlab(source_gitlab_ip, group_name)
    page = 1
    count = 0
    while True:
        # find all projects under target group
        all_projects_finding_response = requests.get('http://' + source_gitlab_ip + '/api/v4/groups/' 
        + str(target_group_id) + '/projects?private_token=' + gitlab_access_token + '&page=' + str(page)).text

        # project not found in gitlab
        if not json.loads(all_projects_finding_response):
            break
        for i in range(len(json.loads(all_projects_finding_response))):
            project_id = json.loads(all_projects_finding_response)[i]['id']
            project_name = json.loads(all_projects_finding_response)[i]['name']
            print('Project ' + project_name + ' is under ' + group_name + ' of gitlab and its id is ' + str(project_id))
            # create new group in target gitlab
            new_group_id = create_group_in_target_gitlab(target_gitlab_ip, group_name)
            # create project in target gitlab with given project name
            create_project_in_target_gitlab(target_gitlab_ip, new_group_id, project_name)
            count += 1
        page += 1
    print('Total number of created projects is: ' + str(count))


# check and create group in target gitlab
def create_group_in_target_gitlab(target_gitlab_ip, group_name):
    """
    find group in gitlab with given and create new group in target gitlab if not found
    :param target_gitlab_ip: target gitlab ip address
    :param group_name: group name to find in target gitlab
    :return: new_group_id: id of group in target gitlab
    """
    # set access token for http request
    gitlab_access_token = set_access_token_gitlab(target_gitlab_ip)
    # add a new user as 'developer' role in target gitlab
    # this use is already existed in target gitlab
    access_level = '30'
    group_finding_response = requests.get('http://' + target_gitlab_ip + '/api/v4/groups?private_token=' 
    + gitlab_access_token + '&search=' + group_name).text
    if len(json.loads(group_finding_response)) == 0:
        # group not found in target gitlab, create new one
        create_group_response = requests.post('http://' + target_gitlab_ip + '/api/v4/groups?private_token=' 
        + gitlab_access_token + '&name=' + group_name + '&path=' + group_name + '&visibility=internal').text
        # find its id from response text
        new_group_id = json.loads(create_group_response)["id"]
        # add a user to new group
        user_id = find_user_id_in_gitlab(target_gitlab_ip, 'foo')
        # add user 'foo' to new group and set developer role
        requests.post('http://' + target_gitlab_ip + '/api/v4/groups/' + str(new_group_id) + '/members?private_token=' 
        + gitlab_access_token + '&user_id=' + str(user_id) + '&access_level=' + access_level)
    else:
        new_group_id = json.loads(group_finding_response)[0]["id"]
    
    return new_group_id


# check and create project under target group in target gitlab
def create_project_in_target_gitlab(gitlab_ip, group_id, project_name):
    """
    create project in gitlab with project name and group id
    :param gitlab_ip: gitlab ip address
    :param group_id: group id in gitlab
    :param project_name: project name in gitlab
    """
    gitlab_access_token = set_access_token_gitlab(gitlab_ip)
    requests.post('http://' + gitlab_ip + '/api/v4/projects?access_token=' + gitlab_access_token 
    + '&name=' + project_name + '&namespace_id=' + str(group_id)+ '&visibility=internal')


# find user id in gitlab with given user
def find_user_id_in_gitlab(target_gitlab_ip, user_name):
    """
    find user id in target gitlab with given username
    :param target_gitlab_ip: target gitlab ip address
    :param user_name: user name in gitlab
    :return: user_id: user id find in target gitlab
    """
    # set access token for http request
    gitlab_access_token = set_access_token_gitlab(target_gitlab_ip)
    user_finding_response = requests.get('http://' + target_gitlab_ip + '/api/v4/users?private_token=' 
    + gitlab_access_token + '&username=' + user_name).text
    # get user id from response text
    user_id = json.loads(user_finding_response)[0]["id"]

    return user_id


find_all_projects_in_gitlab(sys.argv[1], sys.argv[2], sys.argv[3])
