"""
Created on Wed Jun 26, 2024
@author: Isaac Sudweeks
"""

# import needed libraries
import json
import time
import pandas as pd
import requests
import helpers

#  TODO: Make it so that there is error handeling and it will notify the user if there is any problem downloading stuff
###################################### Hard Coded Variables ####################################################

email = 'callumf@byu.edu'
key = 'dunfrog78'


###############################################################################################################
def get_AQS_data(email, key, param, start_date, end_date, state='49', county='035', site='3006'):
    """
    This function gets data from AQS website and returns it
    @param email: The email used to access the AQS data
    @param key: The key used to access the AQS data
    @param param: The parameter that the user wants to download
    @param start_date: The start data of the data
    @param end_date: The end date of the data
    @param state: The state where the data is located
    @param county: The county where the data is located
    @param site: The site number where the data is located
    @return: The data that has been downloaded
    """

    global request
    edate = end_date
    sdate = start_date
    df = pd.DataFrame()
    if end_date.year != start_date.year:
        for year in range(start_date.year, end_date.year + 1):
            # TODO: make this much more streamlined less redundant code
            if year == range(start_date.year, end_date.year + 1)[0]:
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime('12-31-{} 23:59'.format(year))

                request = get_AQS_url(email=email, key=key, param=param, start_date=start_date.strftime('%Y%m%d'),
                                      end_date=end_date.strftime('%Y%m%d'),
                                      state=state, county=county, site=site)
                response = requests.get(request)
                aqs_data = json.loads(response.text).get('Data')

                df = pd.concat([df, pd.DataFrame.from_dict(aqs_data, orient='columns')], axis=0, join='outer')

            elif year == range(start_date.year, end_date.year + 1)[-1]:
                start_date = pd.to_datetime('01-01-{} 00:00'.format(year))
                end_date = pd.to_datetime(end_date)
                request = get_AQS_url(email=email, key=key, param=param, start_date=start_date.strftime('%Y%m%d'),
                                      end_date=end_date.strftime('%Y%m%d'), state=state, county=county, site=site)
                response = requests.get(request)
                aqs_data = json.loads(response.text).get('Data')
                df = pd.concat([df, pd.DataFrame.from_dict(aqs_data, orient='columns')], axis=0, join='outer')

            else:
                start_date = pd.to_datetime('01-01-{} 00:00'.format(year))
                end_date = pd.to_datetime('12-31-{} 23:59'.format(year))
                request = get_AQS_url(email=email, key=key, param=param, start_date=start_date.strftime('%Y%m%d'),
                                      end_date=end_date.strftime('%Y%m%d'), state=state, county=county, site=site)
                response = requests.get(request)
                aqs_data = json.loads(response.text).get('Data')
                df = pd.concat([df, pd.DataFrame.from_dict(aqs_data, orient='columns')], axis=0, join='outer')
            time.sleep(5)
    else:
        request = get_AQS_url(email=email, key=key, param=param, start_date=start_date.strftime('%Y%m%d'),
                              end_date=end_date.strftime('%Y%m%d'), state=state, county=county, site=site)
        response = requests.get(request)
        aqs_data = json.loads(response.text).get('Data')
        df = pd.DataFrame.from_dict(aqs_data, orient='columns')
    try:
        df['dt'] = pd.to_datetime(df['date_local'] + ' ' + df['time_local'])
    except KeyError:
        pass
    if len(df) >= 1:
        df = df[(df['dt'] < edate) & (df['dt'] > sdate)]
    return df


def get_AQS_url(email, key, param, start_date, end_date, state, county, site):
    """
    This creates the url used to get data from AQS
    @param email: The email used to access data
    @param key: The key used to access data
    @param param: The parameters that want to be downloaded
    @param start_date: The start date of the data
    @param end_date: The end date of the data
    @param state: The state of the collection site
    @param county: The county of the collection site
    @param site: The code for the collection site
    @return: the URL is returned
    """
    url = f"https://aqs.epa.gov/data/api/sampleData/bySite?email={email}&key={key}&bdate={start_date}&edate={end_date}&param={param}&state={state}&county={county}&site={site}"
    print(url)
    return url


def get_data():
    """
    Gets data from the AQS database
    """

    print('[Info] Getting data ...')

    if (input("[INPUT] Do you have a excel file with the requested parameter names and codes (Y/N)? ").lower() == "y"):
        excel_file_path = input("[INPUT] What is the filepath or filename of the excel file?")
        # TODO: add error handling to make it so that if there is no index column labeled it will explain it to the
        #  user
        df = pd.read_excel(excel_file_path, index_col="Index")
        params = df['Parameter Code']
        params = list(params.values)
        names = df['Parameter Name']
        names = list(names.values)
        param_dict = dict(zip(names, params))
        parameter_code_dict = {v: k for k, v in param_dict.items()}

    else:
        params = helpers.get_params(email, key)
    print('______________________________________________________________')
    user_start_date = pd.to_datetime(input('[INPUT] Start date (YYYY-MM-DD): '))
    user_end_date = pd.to_datetime(input('[INPUT] End date (YYYY-MM-DD): '))
    aqs_df = pd.DataFrame()
    print('______________________________________________________________')

    # TODO: Make it so it creates a dictionary containing all the sites in the USA
    station_sym_dict = {'490110004': 'BV', '490450004': 'ED', '490170006': 'ES', '490351007': 'MA',
                        '490030003': 'BR', '490571003': 'HV', '490570002': 'O2', '490050007': 'SM',
                        '490494001': 'LN', '490354002': 'NR', '490130002': 'RS', '490495010': 'SF', '490471004': 'V4',
                        '490353013': 'H3', '490353006': 'HW', '490071003': 'P2', '490116001': 'AI',
                        '490456001': '490456001', '490353005': 'SA',
                        '490352005': 'CV', '490210005': 'EN', '490530007': 'HC', '490353010': 'RP', '490353015': 'UT',
                        '490353014': 'LP', '490353016': 'IP',
                        '490190007': 'M7', '490353018': 'RB'}

    site_dict = {v: k for k, v in station_sym_dict.items()}

    if input("[INPUT] Do you have a site code?(y/n) ").lower() == 'y':
        site_code = str(input('[INPUT] What is the site code? '))
        try:
            print(f'[INFO] You have selected {station_sym_dict[site_code]}')
        except KeyError:
            print('[WARNING] Site code unknown will try to pull data anyway')

        state_code = site_code[:2]
        county_code = site_code[2:5]
        site_code = site_code[-4:]
    else:
        response = requests.get(f'https://aqs.epa.gov/data/api/list/states?email={email}&key={key}')
        temp_dict = helpers.listOfDicts(json.loads(response.text).get('Data'))
        state_code_dict = {v: k for k, v in temp_dict.items()}
        temp = True
        while temp:
            try:
                state_code = state_code_dict[input('[INPUT] What state are you getting data from?')]
                temp = False
            except KeyError:
                print("[ERROR] State unsupported or spelled incorrectly please try again")

        response = requests.get(
            f'https://aqs.epa.gov/data/api/list/countiesByState?email={email}&key={key}&state={state_code}')
        temp_dict = helpers.listOfDicts(json.loads(response.text).get('Data'))
        county_code_dict = {v: k for k, v in temp_dict.items()}

        print('[INFO] Counties:', *county_code_dict.keys(), sep='\n')

        temp = True
        while temp:
            try:
                county_code = county_code_dict[
                    input('[INPUT] Which county from the list above are you getting data from?')]
                temp = False
            except KeyError:
                print("[ERROR] County unsupported or spelled incorrectly please try again")
        response = requests.get(
            f'https://aqs.epa.gov/data/api/list/sitesByCounty?email={email}&key={key}&state={state_code}&county={county_code}')
        temp_dict = helpers.listOfDicts(json.loads(response.text).get('Data'))
        site_code_dict = {v: k for k, v in temp_dict.items()}

        print('[INFO] Sites:', *site_code_dict.keys(), sep='\n')
        # TODO: Make it so that it doesn't display none as potential sites
        # TODO: Make it so that it will handel situations where there are no sites in a county
        temp = True
        while temp:
            try:
                site_code = site_code_dict[input('[INPUT] Which site would you like to get data from? ')]
                temp = False
            except KeyError:
                print("[ERROR] Site unsupported or spelled incorrectly please try again")
    print('______________________________________________________________')
    print('[INFO] Downloading data')
    for param in params:
        try:
            temp_df = get_AQS_data(email=email, key=key, param=param, start_date=user_start_date,
                                   end_date=user_end_date, state=state_code, county=county_code, site=site_code)
        except Exception as e:
            print(e)
            do_nothing = 1
            temp_df = pd.DataFrame()
        aqs_df = pd.concat([aqs_df, temp_df], axis=0, join='outer')
        time.sleep(1)
    aqs_df.to_csv(input("[INPUT] What is the filepath of the output file (filename.csv)"), index=False)
    print('[INFO] Data downloaded and saved to file!')
