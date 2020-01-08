import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import csv


def apply_custom_colormap(image_gray, cmap=plt.get_cmap('seismic')):

    assert image_gray.dtype == np.uint8, 'must be np.uint8 image'
    if image_gray.ndim == 3: image_gray = np.squeeze(image_gray, axis=-1)

    # Initialize the matplotlib color map
    sm = plt.cm.ScalarMappable(cmap=cmap)

    # Obtain linear color range
    color_range = sm.to_rgba(np.linspace(0, 1, 256))[:,0:3]    # color range RGBA => RGB
    color_range = (color_range*255.0).astype(np.uint8)         # [0,1] => [0,255]
    color_range = np.squeeze(np.dstack([color_range[:,2], color_range[:,1], color_range[:,0]]), 0)  # RGB => BGR

    # Apply colormap for each channel individually
    channels = [cv2.LUT(image_gray, color_range[:,i]) for i in range(3)]
    return np.dstack(channels)

def getCropMedium(imageData, x, y):
    m=4
    p=4

    if x-m < 0:
        m = m-x
        xl = 0
    else:
        xl = x-m


    if y-p < 0:
        p = p-y
        yd = 0
    else:
        yd = y-p
    
    xr = x + 5
    yu = y + 5

    square = imageData[xl:xr,yd:yu]
    csq = np.array(ktoc(square))
    csv=[]
    # print(csq.shape)

    for i in range(1,m-1):
        csq[0][i-1]=0
        csq[-1][i-1]=0
        csq[i-1][0]=0
        csq[i-1][-1]=0

    for i in range(1,p-1):
        csq[0][-i]=0
        csq[-1][-i]=0
        csq[-i][0]=0
        csq[-i][-1]=0

    for i in range(0,9):
        for j in range(0,9):
            if i==0 or i==8:
                if not (j in [0,1,7,8]):
                    csv.append(csq[i][j])
            elif i==1 or i==7:
                if not (j in [0,8]):
                    csv.append(csq[i][j])
            else:
                csv.append(csq[i][j])
    
    return csv, csq
    
def getCrop(imageData, x, y):
    m=5
    p=5

    if x-m < 0:
        m = m-x
        xl = 0
    else:
        xl = x-m


    if y-p < 0:
        p = p-y
        yd = 0
    else:
        yd = y-p
                    
    xr = x + 6
    yu = y + 6

    # sq = []
    # if m != 5:
    #     a =[]
    #     for i in range(0,11):
    #         a.append(0)
    #     for i in range(0,m):
    #         sq.append(a)
    
    square = imageData[xl:xr,yd:yu]
    csq = ktoc(square)
    csv=[]
    # csq =square

    for i in range(1,m-1):
        csq[0][i-1]=0
        csq[-1][i-1]=0
        csq[i-1][0]=0
        csq[i-1][-1]=0

    for i in range(1,p-1):
        csq[0][-i]=0
        csq[-1][-i]=0
        csq[-i][0]=0
        csq[-i][-1]=0  

    for i in range(0,11):
        for j in range(0,11):
            if i==0 or i==10:
                if not (j in [0,1,2,8,9,10]):
                    csv.append(csq[i][j])
            elif i==1 or i==2 or i==9 or i==8:
                if not (j in [0,10]):
                    csv.append(csq[i][j])
            else:
                csv.append(csq[i][j])

    return csv, csq

def ktof(val):
    return (1.8 * ktoc(val) + 32.0)

def ktoc(val):
    return (val - 27315) / 100.0

def getLocRaw(coords):
    return (np.int(coords[1]*120/480),np.int(coords[0]*160/640))

def raw_to_8bit(data):
    # normalize considers a 16bit usage, and then does an 8 bit shift
    # to fit the unsigned 8bit int array format.
    cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
    np.right_shift(data, 8, data)
    # create rgb image from raw data
    # img = cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)
    # img = cv2.applyColorMap(img, cv2.COLORMAP_JET)
    return np.uint8(data)

def getImage(data):
    data = cv2.resize(data[:,:], (640, 480))
    # minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
    img = raw_to_8bit(data)
    # display_temperature(img, minVal, minLoc, (255, 255, 255))
    # display_temperature(img, maxVal, maxLoc, (255, 255, 255))
    # img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img

def display_temperature(img, val_k, loc, color):
    val = ktoc(val_k)
    cv2.putText(img,"{0:.1f} degC".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)

def drawNumbers(img, ca, ind, col):
    number = str(ind)
    if (ind-1) < 10:
        coords = (ca[0]-5, ca[1]+6)
    else:
        coords = (ca[0]-10, ca[1]+6)
    fontFace = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
    thickness = 2  
    # fontScale 
    fontScale = 0.5
    
    # Black color in BGR 
    color = col
    
    # Line thickness of 2 px 
    thickness = 2
    
    # Using cv2.putText() method 
    cv2.putText(img, number, coords, fontFace,fontScale, color, thickness, cv2.LINE_AA)

def colorize(image, colormap):
    im = cv2.imread(image)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    colorized = colormap(im)
    cv2.imshow("colorized", colorized)
    cv2.waitKey(0)
    cv2.imwrite("colorized.jpg", colorized)

def plot_examples(cms):
    """
    helper function to plot two colormaps
    """
    np.random.seed(19680801)
    data = np.random.randn(30, 30)

    fig, axs = plt.subplots(1, 2, figsize=(6, 3), constrained_layout=True)
    for [ax, cmap] in zip(axs, cms):
        psm = ax.pcolormesh(data, cmap=cmap, rasterized=True, vmin=-4, vmax=4)
        fig.colorbar(psm, ax=ax)
    plt.show()

def getCmpMod():
    viridis = cm.get_cmap('jet', 256)
    newcolors = viridis(np.linspace(0, 1, 256))
    pink = np.array([1, 0.7, 1, 1])
    newcolors[222:] = pink
    newcmp = ListedColormap(newcolors)
    # newcmp = ListedColormap(viridis)
    return newcmp

def norm(data):
    mi = np.min(data)
    ma = np.max(data)
    mins=19
    maxs=36
    
    data = data - mins
    return data/(maxs-mins)

def getPicture(path):       
    rows = []
    with open(path, 'r') as file:
        reader = csv.reader(file,delimiter=" ")
        for r in reader:
            row=[]
            for i in r:
                row.append(np.float(i))
            rows.append(np.array(row))
    return np.array(rows)

def getImage2(rows):
    m = getCmpMod()
    rows=ktoc(rows)
    rows = cv2.resize(rows[:,:], (640, 480))
    im =norm(rows)*255
    return apply_custom_colormap(np.uint8(im), m)
