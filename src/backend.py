'''
 Copyright (C) 2024  Synconics Technologies Pvt. Ltd.

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; version 3.

 odooprojecttimesheet is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import xmlrpc.client
import logging
from datetime import datetime
import requests
import urllib3
urllib3.disable_warnings()
import json
http = urllib3.PoolManager(cert_reqs='CERT_NONE')


logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

url = False
db = False
uid = False
password = False

def logout():
    global url
    url = False
    global db
    db = False
    global uid
    uid = False
    global password
    password = False
    return True    

def fetch_databases(url):
    logging.info('\n\n fetch_databases >>>>>>>>>>>>> >>>>>>>>>>>>>>> %s' % url)
    database_list = get_db_list(url)
    visibility_dict = {'menu_items': False,
                        'text_field': False}
    if not database_list:
        visibility_dict['text_field'] = True
    elif len(database_list) == 1:
        global db
        db = database_list[0]
    else:
        visibility_dict['menu_items'] = database_list
    logging.info('\n\n visibility_dict >>>>>>>>>>>>> >>>>>>>>>>>>>>> %s' % visibility_dict)
    return visibility_dict

def get_db_list(url):
    logging.info('\n\n url >>>>>>>>>>>>>>> %s' % url)
    try:
        response = http.request('POST', url + "/web/database/list", body='{}', headers={'Content-type': 'application/json'})
        logging.debug('\n\n response --------> %s' % response)
        if response.status == 200:
            logging.info('\n\n response.data %s' % response.data)
            data = json.loads(response.data)
            return data['result']
        else:
            return []
    except Exception as e:
        return []
    return []

def login_odoo(selected_url, username, password_filled, database_dict):
    global db
    selected_db = db
    if database_dict['isTextInputVisible']:
        selected_db = database_dict['input_text']
    elif database_dict['isTextMenuVisible']:
        selected_db = database_dict['selected_db']
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(selected_url))
    generated_uid = common.authenticate(selected_db, username, password_filled, {})
    db = selected_db
    global url
    url = selected_url
    global password
    password = password_filled
    if generated_uid:
        global uid
        uid = generated_uid
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(selected_url))
        user_name = models.execute_kw(selected_db, uid, password_filled,
                                  'res.users', 'read',
                                  [uid],
                                  {'fields': ['name']})
        logging.info('\n\n user_name >>>>>>>>>>>>>', user_name)
        return {'result': 'pass', 'name_of_user': user_name[0]['name']}
    return {'result': 'Fail'}

def fetch_options():
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    partner_ids = models.execute_kw(db, uid, password,
        'project.project', 'search',
        [[]]
    )
    partners = models.execute_kw(db, uid, password,
        'project.project', 'read',
        [partner_ids],
        {'fields': ['name']}
    )
    return [partner.get('name') for partner in partners]

def fetch_options_tasks(selectedProject):

    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    partner_ids = models.execute_kw(db, uid, password,
        'project.project', 'search',
        [[]]
    )

    partners = models.execute_kw(db, uid, password,
        'project.project', 'read',
        [partner_ids],
        {'fields': ['name']}
    )

    projects_list = list(filter(lambda pid: pid.get('name') == selectedProject, partners))

    partner_ids = models.execute_kw(db, uid, password,
        'project.task', 'search',
        [[['project_id', 'in', [project.get('id') for project in projects_list]]]]
    )
    partners = models.execute_kw(db, uid, password,
        'project.task', 'read',
        [partner_ids],
        {'fields': ['name']}
    )
    return [partner.get('name') for partner in partners]

def save_timesheet_entries(timesheet_entries):

    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    entry_vals = []
    entry_list = eval(timesheet_entries)
    for entry in entry_list:
        project = [False]
        task = [False]
        if entry.get('project'):
            project = models.execute_kw(db, uid, password,
                'project.project', 'search',
                [[['name', '=', entry.get('project')]]]
            )
        if entry.get('task'):
            task = models.execute_kw(db, uid, password,
                'project.task', 'search',
                [[['name', '=', entry.get('task')]]]
            )

        formatted_date = False
        if entry.get('dateTime'):
            date_obj = datetime.strptime(entry.get('dateTime'), '%m/%d/%Y')  # Parse date string to datetime object
            formatted_date = date_obj.strftime('%Y-%m-%d')
        time_float = False
        if entry.get('spenthours'):
            hours, minutes = entry.get('spenthours').split(':')
            hours = int(hours)
            minutes = int(minutes)
            time_float = hours + minutes / 60.0
        entry_vals.append({
            'date': formatted_date,
            'project_id': project[0],
            'task_id': task[0],
            'name': entry.get('description'),
            'unit_amount': time_float
        })
    entries_timesheet = models.execute_kw(db, uid, password,
        'account.analytic.line', 'create',
        [entry_vals]
    )
    return True
