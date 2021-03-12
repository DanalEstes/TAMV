#!/usr/bin/env python3
# Copyright (C) 2021 Haytham Bennani all rights reserved.
import os
import json
import argparse
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as patches
from matplotlib.ticker import FormatStrFormatter
import matplotlib
import numpy as np
import math

def init():
    parser = argparse.ArgumentParser(description='Program to allign multiple tools on Duet based printers, using machine vision.', allow_abbrev=False)
    parser.add_argument('-filename',type=str,nargs=1,default=['./output.json'],help='Path and filename of data file to process for plotting. Can be a relative or an absolute path. Default is \"./output.json\".')
    
    args=vars(parser.parse_args())
    inputFilename = args['filename'][0]
    matplotlib.use('Qt5Agg',force=True)
    return( inputFilename )

def loadDataFile( filename="./output.json" ):
    try:
        with open(filename,"r") as text_file:
            data = text_file.read().replace('\n', '')
        result = json.loads(data)
        print( str(filename) + " has been loaded.")
        return result
    except OSError:
        print( 'Error opening file: \"' + str(filename) + '\"')
        return -1

def parseData( rawData ):
    # create empty output array
    toolDataResult = []
    
    for i, tool in enumerate(rawData['tools']):
        # x, y are temp objects to calculate stats
        x = []
        y = []
        # variable to hold return data coordinates per tool formatted as a 2D array [x_value, y_value]
        tempPairs = []
        # loop over coordinates and form results
        for run in tool['runs']:
            x.append(np.around(float(run['X']),3))
            y.append(np.around(float(run['Y']),3))
            mpp = float(run['MPP'])

        # calculate stats
        # mean values
        x_mean = np.around(np.mean(x),3)
        y_mean = np.around(np.mean(y),3)
        # median values
        x_median = np.around(np.median(x),3)
        y_median = np.around(np.median(y),3)
        # ranges (max - min per axis)
        x_range = np.around(np.max(x) - np.min(x),3)
        y_range = np.around(np.max(y) - np.min(y),3)
        # standard deviations
        x_sig = np.around(np.std(x),3)
        y_sig = np.around(np.std(y),3)

        # normalize data around mean
        x -= x_mean
        y -= y_mean
        
        # temporary object to append coordinate pairs into return value
        tempPairs.append(x)
        tempPairs.append(y)

        # add data to return object
        toolDataResult.append(tempPairs)

        # display summary data to terminal
        print( 'Summary for Tool '+str(i) +':' )
        print( '   Xmean:     {0:6.3f}    Ymean:     {1:7.3f}'.format(x_mean,y_mean))
        print( '   Xmedian:   {0:6.3f}    Ymedian:   {1:7.3f}'.format(x_median,y_median))
        print( '   Xsigma:    {0:7.3f}    Ysigma:    {1:7.3f}'.format(x_sig,y_sig))
        print( '   Xrange:    {0:7.3f}    Yrange:    {1:7.3f}'.format(x_range,y_range))
        print('')
    
    # return dataset
    return toolDataResult

def main():
    # parse command line arguments
    dataFilename = init()
    

    # set up color and colormap arrays
    colorMap = ["Greens","Oranges","Blues", "Reds"] #["Blues", "Reds","Greens","Oranges"]
    colors = ['blue','red','green','orange']

    # attempt to load data file
    j=loadDataFile(dataFilename)
    # handle file not opened errors and exit
    if j == -1:
        return

    # data file has been loaded, proceed with processing the data
    numTools = len(j['tools'])
    totalRuns = len(j['tools'][0]['runs'])
    print('')
    print( "Found data for {} tools".format(numTools) + " and " + str(totalRuns) + " alignment cycles.")
    print('')

    # get data as 3 dimensional array [tool][axis][datapoints] normalized around mean of each axis
    toolData = parseData(j)

    # initiate graph data - 1 tool per column
    # Row 0: scatter plot with standard deviation box
    # Row 1: histogram of X axis data
    # Row 2: histogram of Y axis data
    plt.switch_backend('QT4Agg') 
    
    fig, axes = plt.subplots(ncols=3,nrows=numTools,constrained_layout=False)
    

    for i, data in enumerate(toolData):
        # create a color array the length of the number of tools in the data
        color = np.arange(len(data[0]))

        # Axis formatting
        # Major ticks
        axes[i][0].xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
        axes[i][0].yaxis.set_major_formatter(FormatStrFormatter('%.3f'))
        # Minor ticks
        axes[i][0].xaxis.set_minor_formatter(FormatStrFormatter('%.3f'))
        axes[i][0].yaxis.set_minor_formatter(FormatStrFormatter('%.3f'))
        # Draw 0,0 lines
        axes[i][0].axhline()
        axes[i][0].axvline()
        # x&y std deviation box
        x_sigma = np.around(np.std(data[0]),3)
        y_sigma = np.around(np.std(data[1]),3)
        axes[i][0].add_patch(patches.Rectangle((-1*x_sigma,-1*y_sigma), 2*x_sigma, 2*y_sigma, color="green",fill=False, linestyle='dotted'))
        axes[i][0].add_patch(patches.Rectangle((-2*x_sigma,-2*y_sigma), 4*x_sigma, 4*y_sigma, color="red",fill=False, linestyle='-.'))
        
        # scatter plot for tool data
        axes[i][0].scatter(data[0], data[1], c=color, cmap=colorMap[i])
        axes[i][0].autoscale = True
        
        # Histogram data setup
        # Calculate number of bins per axis
        x_intervals = int(np.around(math.sqrt(len(data[0])),0)+1)
        y_intervals = int(np.around(math.sqrt(len(data[1])),0)+1)
        
        # plot histograms
        x_kwargs = dict(alpha=0.5, bins=x_intervals,rwidth=.92, density=True)
        n, bins, hist_patches = axes[i][1].hist([data[0],data[1]],**x_kwargs, color=[colors[0],colors[1]], label=['X','Y'])
        axes[i][2].hist2d(data[0], data[1], bins=x_intervals, cmap='Blues')
        axes[i][1].legend()


        # add a 'best fit' line
        # calculate mean and std deviation per axis
        x_mean = np.mean(data[0])
        y_mean = np.mean(data[1])
        x_sigma = np.around(np.std(data[0]),3)
        y_sigma = np.around(np.std(data[1]),3)
        # calculate function lines for best fit
        x_best = ((1 / (np.sqrt(2 * np.pi) * x_sigma)) *
            np.exp(-0.5 * (1 / x_sigma * (bins - x_mean))**2))
        y_best = ((1 / (np.sqrt(2 * np.pi) * y_sigma)) *
            np.exp(-0.5 * (1 / y_sigma * (bins - y_mean))**2))
        # add best fit line to plots
        axes[i][1].plot(bins, x_best, '-.',color=colors[0])
        axes[i][1].plot(bins, y_best, '--',color=colors[1])

        x_count = int(sum( p == True for p in ((data[0] >= (x_mean - x_sigma)) & (data[0] <= (x_mean + x_sigma))) )/len(data[0])*100)
        y_count = int(sum( p == True for p in ((data[1] >= (y_mean - y_sigma)) & (data[1] <= (y_mean + y_sigma))) )/len(data[1])*100)
        # annotate std dev values
        annotation_text = "Xσ: " + str(x_sigma) + " ("+str(x_count) + "%)"
        if x_count < 68:
            x_count = int(sum( p == True for p in ((data[0] >= (x_mean - 2*x_sigma)) & (data[0] <= (x_mean + 2*x_sigma))) )/len(data[0])*100) 
            annotation_text += " --> 2σ: " + str(x_count) + "%"
            if x_count < 95 and x_sigma*2 > 0.1:
                annotation_text += " -- check axis!"
            else: annotation_text += " -- OK"
        annotation_text += "\nYσ: " + str(y_sigma) + " ("+str(y_count) + "%)"
        if y_count < 68: 
            y_count = int(sum( p == True for p in ((data[1] >= (y_mean - 2*y_sigma)) & (data[1] <= (y_mean + 2*y_sigma))) )/len(data[1])*100) 
            annotation_text += " --> 2σ: " + str(y_count) + "%"
            if y_count < 95 and y_sigma*2 > 0.1:
                annotation_text += " -- check axis!"
            else: annotation_text += " -- OK"
        axes[i][0].annotate(annotation_text, (10,10),xycoords='axes pixels')
        axes[i][0].annotate('σ',(1.1*x_sigma,-1.1*y_sigma),xycoords='data',color='green')
        axes[i][0].annotate('2σ',(1.1*2*x_sigma,-1.1*2*y_sigma),xycoords='data',color='red')
        # # place title for graph
        axes[i][0].set_ylabel("Tool " + str(i) + "\nY")
        axes[i][0].set_xlabel("X")
        axes[i][2].set_ylabel("Y")
        axes[i][2].set_xlabel("X")
        
        if i == 0:
            axes[i][0].set_title('Scatter Plot')
            axes[i][1].set_title('Histogram')
            axes[i][2].set_title('2D Histogram')
    plt.tight_layout()
    figManager = plt.get_current_fig_manager()
    figManager.window.showMaximized()
    plt.show()
    


if __name__ == "__main__":
    main()
    exit()
