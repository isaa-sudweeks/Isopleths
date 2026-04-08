"""

Created on Wed June 26, 2024

@author: Isaac Sudweeks

"""
import build_isopleths
import find_isopleth_parameters
# Imports
import helpers
import get_data
import reformat_data
import pandas as pd



def main():
    response = input(
        "[INPUT] Hello, what would you like to do this run (enter a number 1-4)?\n1. download AQS data\n2. reformat AQS data\n3. Get isopleth parameters\n4. Create an isopleth\n")
    if (response == "1"):
        get_data.get_data()
    elif (response == "2"):
        outpath = input('[INPUT] Please enter your desired output directory\n')
        response = input('[INPUT] Please enter the function(s) you would like to perform:\n1. Reformat data, sum data, produce data products\n2. reformat data\n')

        # Get the input file and output information
        filename = input('[INPUT] Please enter the filepath/filename of the data you want to reformat\n')
        if (response == "1"):
            #reformat_data.reformat_data(outpath,filename)
            reformat_data.sum_data(outpath,filename)
        elif (response == "2"):
            reformat_data.reformat_data(outpath,filename)
    elif (response == "3"):
        filename = input('[INPUT] Please enter the filepath for the data that you would like to build an isopleth from: ')
        num = int(input('[INPUT] Please enter the number of isopleths you want to try to find the best one'))
        find_isopleth_parameters.get_params(filename, num)
    elif (response == "4"):
        filename = input('[INPUT] Please enter the file path of the data that you want to build an isopleth from: ')
        kx = int(input('[INPUT] Please enter the number of knots in the x direction'))
        ky = int(input('[INPUT] Please enter the number of knots in the y direction'))
        e =float(input('[INPUT] Please enter the epsilon value'))
        data = pd.read_csv(filename)
        build_isopleths.build_isopleths(data,ky,kx,e, filename)


if (__name__ == "__main__"):
    main()
