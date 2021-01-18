#!/usr/bin/env python3

import os
import json
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as patches
from matplotlib.ticker import FormatStrFormatter
import numpy as np
import math

try:
    with open("./output.json","r") as text_file:
        data = text_file.read().replace('\n', '')
    j = json.loads(data)
    print( "Output.json has been loaded.")
except OSError:
    print('Error opening output.json')
    exit(-1)

numTools = len(j['tools'])
totalRuns = len(j['tools'][0]['runs'])
print( 'Found data for {} tools'.format(numTools))
print( "Tools ran for a total of " + str(totalRuns) + " runs.")
print('')

toolData = []
counter = 0

for tool in j['tools']:
    x = []
    y = []
    x_float = []
    y_float = []
    
    for run in tool['runs']:
        x.append(np.around(float(run['X']),3))
        y.append(np.around(float(run['Y']),3))
        mpp = float(run['MPP'])
    x_mean = np.around(np.mean(x),3)
    y_mean = np.around(np.mean(y),3)
    x_median = np.around(np.median(x),3)
    y_median = np.around(np.median(y),3)
    x_range = np.around(np.max(x) - np.min(x),3)
    y_range = np.around(np.max(y) - np.min(y),3)
    x_sig = np.around(np.std(x),3)
    y_sig = np.around(np.std(y),3)
    x -= x_mean
    y -= y_mean

    print( 'Summary for Tool '+str(counter) +':' )
    print( '   Xmean:     {0:6.3f}    Ymean:     {1:7.3f}'.format(x_mean,y_mean))
    print( '   Xmedian:   {0:6.3f}    Ymedian:   {1:7.3f}'.format(x_median,y_median))
    print( '   Xsigma:    {0:7.3f}    Ysigma:    {1:7.3f}'.format(x_sig,y_sig))
    print( '   Xrange:    {0:7.3f}    Yrange:    {1:7.3f}'.format(x_range,y_range))
    print('')
    counter += 1
    toolData.append( (x,y) )

counter = 0
colorMap = ["Blues", "Reds","Greens","Oranges"]
colors = ['blue','red','green','orange']
fig, axes = plt.subplots(nrows=1,ncols=numTools)

for data in toolData:
    title = "Tool " + str(counter)
    color = np.arange(len(data[0]))
    axes[counter].yaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    axes[counter].xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    # 0,0 lines
    axes[counter].axhline()
    axes[counter].axvline()
    # x&y std deviation lines
    x_sigma = np.around(np.std(data[0]),3)
    y_sigma = np.around(np.std(data[1]),3)
    axes[counter].add_patch(patches.Rectangle((-1*x_sigma,-1*y_sigma), 2*x_sigma, 2*y_sigma, color="red",fill=False, linestyle='dotted'))

    axes[counter].scatter(data[0], data[1], c=color, cmap=colorMap[counter])
    axes[counter].set_title(title)
    counter += 1
plt.show()

counter = 0
for tool in toolData:
    plotX = []
    plotY = []
    for coordinate in tool[0]:
        plotX.append(float(coordinate))
    for coordinate in tool[1]:
        plotY.append(float(coordinate))
        
    fig, axes = plt.subplots(nrows=1,ncols=2)
    x_intervals = np.around(math.sqrt(len(plotX)),0)+1
    y_intervals = np.around(math.sqrt(len(plotY)),0)+1
    x_width = (np.around((np.max(plotX)-np.min(plotX))/x_intervals,3))
    y_width = (np.around((np.max(plotY)-np.min(plotY))/y_intervals,3))
    x_bins = []
    y_bins = []

    for index in range(-3,int(x_intervals)+6):
        x_bins.append(np.around(np.min(plotX)+x_width*index,3))
        y_bins.append(np.around(np.min(plotY)+y_width*index,3))
    
    bins = [x_bins, y_bins]
    
    axes[0].set_title("Tool " + str(counter))
    axes[0].hist(plotX, density=False,bins=bins[0],color=colors[0],rwidth=0.9)
    axes[1].set_title("Tool " + str(counter))
    axes[1].hist(plotY, density=False,bins=bins[1],color=colors[1],rwidth=0.9)
    axes[0].set_xlabel('X')
    axes[1].set_xlabel('Y')

    counter += 1
    plt.show()


exit()