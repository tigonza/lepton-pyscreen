import cv2
import numpy as np

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
    cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
    np.right_shift(data, 8, data)
    img = cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)
    img = cv2.applyColorMap(img, cv2.COLORMAP_JET)
    return img

def getImage(data):
    data = cv2.resize(data[:,:], (640, 480))
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
    img = raw_to_8bit(data)
    display_temperature(img, minVal, minLoc, (255, 255, 255))
    display_temperature(img, maxVal, maxLoc, (255, 255, 255))
    # img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img


def display_temperature(img, val_k, loc, color):
    val = ktoc(val_k)
    cv2.putText(img,"{0:.1f} degC".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)


def drawNumbers(img, ca, ind):
    number = str(ind - 1)
    if (ind-1) < 10:
        coords = (ca[0]-5, ca[1]+6)
    else:
        coords = (ca[0]-10, ca[1]+6)
    fontFace = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
    thickness = 2  
    # fontScale 
    fontScale = 0.5
    
    # Black color in BGR 
    color = (0, 0, 0) 
    
    # Line thickness of 2 px 
    thickness = 2
    
    # Using cv2.putText() method 
    cv2.putText(img, number, coords, fontFace,fontScale, color, thickness, cv2.LINE_AA)