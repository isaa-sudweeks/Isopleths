"""
Helper functions
Created on Wed June 26, 2024
@author: Isaac Sudweeeks
"""
import requests
import json


def listOfDicts(ls):
    """
    @param ls: this is a list of dictionaries,
    @return: this is a dictionary made up of the dictionaries contained in ls
    """
    out = dict()
    for item in ls:
        code = item.get('code')
        val = item.get('value_represented')
        out[code] = val
    return out


def get_params(email, key):
    params = []
    temp_dict = get_param_dict(email, key)
    temp = list(temp_dict.values())
    for val in temp:
        params.append(val)
    return params

def get_param_dict(email,key):
    print('--------------------------------------------------------')
    response = input(
        "[INPUT] Would you like to(1-2):\n1.Get the parameters used to make isopleths \n2.Get the parameters for one of the AQS classes?\n")
    if response == "1":
        response = requests.get(f'https://aqs.epa.gov/data/api/list/parametersByClass?email={email}&key={key}&pc=VOC')
        temp_dict = listOfDicts(json.loads(response.text).get('Data'))
        temp_dict['44201'] = 'Ozone'
        temp_dict['88101'] = 'PM2.5 - Local Conditions'
        temp_dict['42603'] = 'Oxides of nitrogen (NOx)'
        temp_dict['42601'] = 'Nitric oxide (NO)'
        temp_dict['42602'] = 'Nitrogen dioxide (NO2)'
    else:
        response = requests.get(f'https://aqs.epa.gov/data/api/list/classes?email={email}&key={key}')
        temp_dict = listOfDicts(json.loads(response.text).get('Data'))
        class_codes_dict = {v: k for k, v in temp_dict.items()}

        print('[INFO] AQS classes:', *class_codes_dict.keys(), sep='\n')
        go = True
        while go:
            try:
                class_code = class_codes_dict[
                    input("[INPUT] which class do you want?(Please type the entire class description as seen above)")]
                go = False
            except KeyError:
                print('[ERROR] the class typed was not found in the data received from AQS please try again')
        params = []
        response = requests.get(
            f'https://aqs.epa.gov/data/api/list/parametersByClass?email={email}&key={key}&pc={class_code}')
        temp_dict = listOfDicts(json.loads(response.text).get('Data'))
    print('------------------------------------------------------------------------------')
    return {v: k for k, v in temp_dict.items()}