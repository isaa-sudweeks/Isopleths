"""
Created on Jun 27, 2024
@author: Isaac Sudweeks
"""
import datetime

# Imports
import pandas as pd
import os

import helpers

################ USER SET VARIABLES #############################
email = 'callumf@byu.edu'
key = 'dunfrog78'


#################################################################
def get_meta_data(data):
    param = list(data['parameter'])[0]
    un_o_me = list(data['units_of_measure'])[0]
    sample_duration = list(data['sample_duration'])[0]
    sample_freq = list(data['sample_frequency'])[0]
    method = list(data['method'])[0]
    return pd.DataFrame([[param, un_o_me, sample_duration, sample_freq, method]],
                        columns=['parameter', 'units_of_measure', 'sample_duration', 'sample_frequency', 'method'])


def reformat_data(outpath, filename):
    """
    Reformat the data that the user enters
    @return: void
    """
    # TODO: Make it so that it spits out a csv with all of the metadata for each species as well

    # Check to see if the user has a params sheet
    if input('[INPUT] Do you have a sheet of desired parameters in the correct format? (y/n)').lower() == 'y':
        # Get the params sheet filename
        param_filename = input('[INPUT] Please enter the filename/filepath of the parameters sheet: ')
        print('----------------------------------------------------------')

        # Read in the list of parameters
        df = pd.read_excel(param_filename, index_col='Index')
        names = df['Parameter Name']
        names = list(names.values)
    else:
        # Get all parameters
        param_dict = helpers.get_param_dict(email, key)
        names = list(param_dict.keys())

    # Read in the raw input file
    input_df = pd.read_csv(filename, parse_dates=['dt'], dtype={'sample_measurement': float})

    # Create the output and metadata dataframes
    output_df = pd.DataFrame(columns=['dt'])
    meta_data = pd.DataFrame()

    # Wrangle the input data
    temp_df = input_df.drop(input_df.columns.difference(
        ['dt', 'parameter', 'sample_measurement', 'method', 'sample_duration', 'sample_frequency', 'units_of_measure']),
        axis=1)  #
    # drop all columns that are not dt, parameter, ect
    temp_df = temp_df[
        ['dt', 'parameter', 'sample_measurement', 'method', 'sample_duration', 'sample_frequency', 'units_of_measure']]
    # Rearrange the columns

    # Create a dictionary of dataframes by their parameters
    dfdict = dict(tuple(temp_df.groupby('parameter')))

    # TODO: Write something that can handel different time resolutions

    # A for loop going through each parameter and reformatting the information
    for name in names:
        try:
            method_dict = dict(tuple(dfdict[name].groupby('method')))
            if len(method_dict) > 1:
                if input(
                        f'[INFO] The parameter {name} has more than one method of recording would you like to specify which parameter to use? [y/n] ').lower() == 'y':
                    dfdict[name] = get_method(method_dict, name)

                else:
                    print('[INFO] will try to automatically select the correct method(s)')
                    df = pd.DataFrame(columns=['dt'])
                    try:
                        count = 0
                        df = method_dict[
                            'preconcentrator trap/thermal desorber - Nafion drier - CAS AirmOzone - butane response - factor adjusted']
                        count += 1
                    except KeyError:
                        pass
                    try:

                        df = df.merge(method_dict[
                                          'Preconcentrator trap/thermal desorber - no drier - CAS AirmOzone - benzene response - factor adjusted'],
                                      on=['dt'], how='outer', suffixes=('_', ''))
                        count += 1
                        df['sample_measurement'] = df.pop(f'sample_measurement_').fillna(df['sample_measurement'])
                        df.drop(['method_', 'sample_duration_', 'sample_frequency_', 'units_of_measure_', 'parameter_'],
                                axis=1, inplace=True)
                    except KeyError:
                        pass
                    try:
                        df = df.merge(method_dict['Preconcen trap/Thermal Desorber - Auto GC (PE Clarus 500 dual col)'],
                                      on=['dt'], how='outer', suffixes=('_', ''))
                        count += 1
                        df['sample_measurement'] = df.pop(f'sample_measurement_').fillna(df['sample_measurement'])
                        df.drop(['method_', 'sample_duration_', 'sample_frequency_', 'units_of_measure_', 'parameter_'],
                                axis=1,
                                inplace=True)
                    except KeyError:
                        pass
                    try:
                        df = df.merge(method_dict['SS CANISTER PRESSURIZED - CRYOGENIC PRECONCENTRATION GC/FID'],
                                      on=['dt'], how='outer', suffixes=('_', ''))
                        count += 1
                        df['sample_measurement'] = df.pop(f'sample_measurement_').fillna(df['sample_measurement'])
                        df.drop(['method_', 'sample_duration_', 'sample_frequency_', 'units_of_measure_', 'parameter_'],
                                axis=1,
                                inplace=True)
                    except KeyError:
                        pass
                    try:
                        df = df.merge(method_dict['SS 6L Pressurized Canister - Cryogenic Precon GC/MS'], on=['dt'],
                                      how='outer', suffixes=('_', ''))
                        count += 1
                        df['sample_measurement'] = df.pop(f'sample_measurement_').fillna(df['sample_measurement'])
                        df.drop(['method_', 'sample_duration_', 'sample_frequency_', 'units_of_measure_', 'parameter_'],
                                axis=1,
                                inplace=True)
                    except KeyError:
                        pass
                    try:
                        df = df.merge(method_dict['6L SUBATM CANISTER - Entech Precon-  GC/FID/MSD'], on=['dt'],
                                      how='outer', suffixes=('_', ''))
                        count += 1
                        df['sample_measurement'] = df.pop(f'sample_measurement_').fillna(df['sample_measurement'])
                        df.drop(['method_', 'sample_duration_', 'sample_frequency_', 'units_of_measure_', 'parameter_'],
                                axis=1,
                                inplace=True)
                    except KeyError:
                        pass

                    if count == 0:
                        print('[ERROR] The method can not be selected properly please select the correct method(s) '
                              'manually')
                        dfdict[name] = get_method(method_dict, name)
                    else:
                        dfdict[name] = df

            # FIXME: Fix the metadata so that it works again
            meta_data = pd.concat([meta_data, get_meta_data(dfdict[name])], ignore_index=True, copy=False)
            dfdict[name].drop(['method', 'sample_duration', 'sample_frequency', 'units_of_measure'], axis=1,
                              inplace=True)
            dfdict[name].drop('parameter', axis=1, inplace=True)  # TODO: See if these can be combined
            dfdict[name].rename(columns={'sample_measurement': name}, inplace=True)
            dfdict[name].dropna(inplace=True)
            dfdict[name].drop_duplicates(subset=['dt'], keep='first', inplace=True, ignore_index=True)
            output_df = output_df.merge(dfdict[name], on=['dt'], how='outer', sort=True)
            print('========================================================================')
        except KeyError:
            print(f'[WARNING] Could not find {name} in data file')
            print('========================================================================')

    # Save the data
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    file = filename.split('/')[-1]
    file = file.split('.')[0]
    output_df.to_csv(f'{outpath}/{file}_reformatted.csv', index=False)
    meta_data.to_csv(f'{outpath}/{file}_metadata.csv')
    print(f'[INFO] Saved {outpath}/{file} successfully!')


def get_method(method_dict, name):
    print(f'[INFO] The parameter {name} has more than one method of recording which are as follows:')
    for method in method_dict:
        print(
            f'      ({method}) which has a sample duration of {list(method_dict[method]["sample_duration"])[0]} and a sample frequency of {list(method_dict[method]["sample_frequency"])[0]}')
    print('--------------------------------------------------------------------')
    temp = True
    while temp:
        df = pd.DataFrame()
        try:
            if input('[INPUT] Do you want to use multiple methods of recording? (y/n): ').lower() == 'y':
                temp = True
                methods = []
                count = 1
                print(
                    '[INFO] please specify the method one at a time and when you are done press enter without typing anything else.')
                while temp:
                    response = input(f'[INPUT] What is method {count}: ')
                    if response == '':
                        temp = False
                    else:
                        methods.append(response)
                    count += 1
                for method in methods:
                    df = pd.concat([df, method_dict[method]])
            else:
                response = input(f'[INPUT] which method would you like to use?')
                df = method_dict[response]

            print('---------------------------------------------------------------------------')
            temp = False
        except KeyError:
            print(f'[ERROR] the method that was inputted was not valid please try again')
    return df


def change_units(data):
    """
    This function changes the units of the Ozone parameter from ppm to ppb
    @param data: the input data
    """
    data['Ozone'] = data['Ozone'] * 1000


def maxOzone(day):
    """
    This function returns the maximum ozone for a day
    @param day: A dataframe containing all of the data for 1 day
    @return: A dataframe with the max ozone for the given day
    """
    return day.loc[day['Ozone'].idxmax()]


def get_max_ozone(data):
    """
    This function returns a dataframe which contains only the maximum ozone values for each given day
    @param data:
    @return:
    """
    data['day'] = data['dt'].dt.date
    dfdict = dict(tuple(data.groupby('day')))
    maxdf = pd.DataFrame(columns=data.columns)
    for day in dfdict:
        maxdf.loc[len(maxdf)] = maxOzone(dfdict[day])
    return maxdf


def sumdf(data):
    names = list(data.columns)
    names.remove('dt')
    if input('[INPUT] are there any parameters that you do not want to include in the sum (y/n) ').lower() == 'y':
        for name in names:
            if input(f'[INPUT] do you want to include {name}(y/n) ').lower() == 'n':
                names.remove(name)
    try:
        names.remove('Ozone')
        names.remove('Oxides of nitrogen (NOx)')
        names.remove('time')
        names.remove('day')
        names.remove('Nitric oxide (NO)')
        names.remove('Nitrogen dioxide (NO2)')
    except:
        pass
    print('[INFO] Summing data frame')
    output = pd.DataFrame(columns=['NOx', 'VOC', 'Ozone', 'dt'])
    output['NOx'] = data['Oxides of nitrogen (NOx)']
    output['Ozone'] = data['Ozone']
    output['dt'] = data['dt']
    output.fillna(0, inplace=True)
    for name in names:
        try:
            output['VOC'] = output['VOC'] + data[name]
        except KeyError:
            print(f'[WARNING] {name} not found in data')
    return output[output['VOC'] > 0]


def sort_by_season(data):
    """
    This function takes a dataframe and returns the data frame sorted into different seasonal periods
    @param data: Input data frame
    @return: winter, spring, summer, fall
    """
    summer = pd.DataFrame(columns=data.columns)
    fall = pd.DataFrame(columns=data.columns)
    winter = pd.DataFrame(columns=data.columns)
    spring = pd.DataFrame(columns=data.columns)

    for i in range(len(data)):
        if (data.iloc[i].loc['dt'].month in range(0, 3)) or (data.iloc[i].loc['dt'].month == 12):  # Criteria for winter
            winter.loc[len(winter)] = data.iloc[i]
        if data.iloc[i].loc['dt'].month in range(3, 6):  # Criteria for spring
            spring.loc[len(spring)] = data.iloc[i]
        if data.iloc[i].loc['dt'].month in range(6, 9):  # Criteria for summer
            summer.loc[len(summer)] = data.iloc[i]
        if data.iloc[i].loc['dt'].month in range(9, 12):  # Criteria for fall
            fall.loc[len(fall)] = data.iloc[i]

    # Return the data frames
    return winter, spring, summer, fall


def weekends(data):
    """
    This function takes a data frame and returns data that is sorted into weekend and weekday time categories
    @param data:
    @return:
    """
    weekdays = pd.DataFrame(columns=data.columns)
    weekends = pd.DataFrame(columns=data.columns)

    # Define the weekdays as Saturday and Sunday
    weekend_days = ['Sunday', 'Saturday']

    # Run a loop that checks to see if a row of data is a weekend and then adds it to the correct dataframe
    for i in range(len(data)):
        if (data.iloc[i].loc['dt'].day_name() in weekend_days):
            weekends.loc[len(weekends)] = data.iloc[i]

        else:
            weekdays.loc[len(weekdays)] = data.iloc[i]

    # Return the dataframes
    return weekends, weekdays


def sum_data(outpath, filename):
    """
    This function sums all of the VOCs in a dataset and saves them to an output file
    @param outpath: This is the path where the data is saved
    """
    print(f'[INFO] Sorting and summing data')
    # TODO: Comment all of this to make it easier to fallow

    file = filename.split('/')[-1]
    file = file.split('.')[0]
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    if not os.path.exists(f'{outpath}/not_summed/seasonal'):
        os.makedirs(f'{outpath}/not_summed/seasonal')
    if not os.path.exists(f'{outpath}/not_summed/week'):
        os.makedirs(f'{outpath}/not_summed/week')
    if not os.path.exists(f'{outpath}/summed/seasonal'):
        os.makedirs(f'{outpath}/summed/seasonal')
    if not os.path.exists(f'{outpath}/summed/week'):
        os.makedirs(f'{outpath}/summed/week')

    data = pd.read_csv(f'{outpath}/{file}_reformatted.csv', parse_dates=['dt'])
    data['dt'] = pd.to_datetime(data['dt'], format='mixed')
    clean_data(data)
    daytimedata = daytime(data)
    change_units(daytimedata)
    max_data = get_max_ozone(daytimedata)
    max_data.to_csv(f'{outpath}/not_summed/{file}_all_data.csv', index=False)
    print(f'[INFO] Saving not summed all data')

    summed_max_data = sumdf(max_data)
    summed_max_data.to_csv(f'{outpath}/summed/{file}_all_data.csv', index=False)

    get_seasonal(file, max_data, outpath, summed_max_data)
    weekendn, weekdayn = weekends(max_data)
    print(f'[INFO] saving not summed weekend and weekday data')
    weekendn.to_csv(f'{outpath}/not_summed/week/{file}_weekend.csv', index=False)

    weekdayn.to_csv(f'{outpath}/not_summed/week/{file}_weekday.csv', index=False)
    print(f'[INFO] saving summed weekend and weekday data')
    weekend, weekday = weekends(summed_max_data)
    weekday.to_csv(f'{outpath}/summed/week/{file}_weekday.csv', index=False)
    weekend.to_csv(f'{outpath}/summed/week/{file}_weekend.csv', index=False)
    print(f'[INFO] Finished reformatting data')


def get_seasonal(file, max_data, outpath, summed_max_data):
    """
    This is a function to sort data into the different seasons
    @param file: This is the filename of the unsorted data
    @param max_data: This is the raw maximum data
    @param outpath: This is the output file path for saving the data
    @param summed_max_data: This is same as max data, but it is summed
    """
    print(f'[INFO] saving summed all data')
    wintern, springn, summern, falln = sort_by_season(max_data)
    print(f'[INFO] saving not summed seasonal data')
    wintern.to_csv(f'{outpath}/not_summed/seasonal/{file}_winter_not_summed.csv', index=False)
    summern.to_csv(f'{outpath}/not_summed/seasonal/{file}_summer_not_summed.csv', index=False)
    springn.to_csv(f'{outpath}/not_summed/seasonal/{file}_spring_not_summed.csv', index=False)
    falln.to_csv(f'{outpath}/not_summed/seasonal/{file}_fall_not_summed.csv', index=False)
    winter, spring, summer, fall = sort_by_season(summed_max_data)
    print(f'[INFO] saving summed seasonal data')
    winter.to_csv(f'{outpath}/summed/seasonal/{file}_winter.csv', index=False)
    summer.to_csv(f'{outpath}/summed/seasonal/{file}_summer.csv', index=False)
    spring.to_csv(f'{outpath}/summed/seasonal/{file}_spring.csv', index=False)
    fall.to_csv(f'{outpath}/summed/seasonal/{file}_fall.csv', index=False)


def clean_data(df):
    """
    This function cleans data by getting rid of things such as missing values
    @param df: This is the data frame containing the data to be cleaned
    @return:
    """
    try:
        df.dropna(inplace=True, how='all')
        df.dropna(inplace=True, subset='Ozone')
        df.dropna(inplace=True, subset='Oxides of nitrogen (NOx)')
        df.fillna(0, inplace=True)
    except KeyError:
        print(f'[ERROR] The data frame does not contain required species Ozone or Oxides of nitrogen (NOx)')


def sort_by_hour(df):
    """
    This function returns a dictionary with each hour of the data
    @param df: The data to be sorted
    @return: The returned dictionary
    """
    dfwtime = df
    dfwtime['time'] = dfwtime['dt'].dt.time
    return dict(tuple(dfwtime.groupby('time')))


def daytime(df):
    """
    This function returns a data frame that only contains data for times between 8am and 5pm
    @param df: The data to be sorted in this manner
    @return: The data with only the certain times
    """
    hourdict = sort_by_hour(df)
    out = pd.DataFrame(columns=df.columns)
    list = []
    for i in range(8, 18):
        time = datetime.time(i, 0)
        list.append(hourdict[time])
        out = pd.concat([out, hourdict[time]], ignore_index=True)
    return out
