import wx
import os
import cv2
import csv

from uvctypes import *
import time
import numpy as np
from datetime import datetime
from zipfile import ZipFile

try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import platform

COLORS = [cv2.COLORMAP_AUTUMN, cv2.COLORMAP_BONE, cv2.COLORMAP_JET, cv2.COLORMAP_HOT, cv2.COLORMAP_OCEAN]
SELECTED_COLOR = 0
PATH = ""
COORDS_PICT =[]
q = Queue(2)


def py_frame_callback(frame, userptr):
    array_pointer = cast(frame.contents.data, POINTER(c_uint16 * (frame.contents.width * frame.contents.height)))
    data = np.frombuffer(
    array_pointer.contents, dtype=np.dtype(np.uint16)
    ).reshape(
    frame.contents.height, frame.contents.width
    ) # no copy

    # data = np.fromiter(
    #   frame.contents.data, dtype=np.dtype(np.uint8), count=frame.contents.data_bytes
    # ).reshape(
    #   frame.contents.height, frame.contents.width, 2
    # ) # copy

    if frame.contents.data_bytes != (2 * frame.contents.width * frame.contents.height):
        return

    if not q.full():
        q.put(data)


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

def zipResults(names):
    # img = raw_to_8bit(data)
    now = datetime.now()
    zipString=now.strftime("/home/pi/Desktop/resultados/%d-%m-%Y_%H:%M:%S:%f")
    # zipString=now.strftime("%d-%m-%Y_%H:%M:%S:%f")
    with ZipFile(zipString,'w') as z:
        for i in names:
            z.write(i)

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



def saveCsv(csv, temps):
    cstring = "circulos_info"
    rstring = "circulos_full"

    csv = np.mat(csv)
    c=0
    res=[]
    # mean = np.mean(csv)
    for i in csv:
        line=[c, temps[c], np.mean(i), np.max(i)]
        res.append(line)
        c+=1

    with open(cstring+'.csv','w') as f:
        f.write('index,Temp Center,Promedio,Max\n')

    with open(cstring+'.csv','wb') as f:
        # f.write('index,Center,Promedio,Max\n')
        for i in np.mat(res):
            np.savetxt(f, np.array(i), fmt='%.2f', delimiter=',')
        f.close()

    with open(rstring+'.csv','wb') as f:
        # f.write('index,Center,Promedio,Max\n')
        for i in np.mat(csv):
            np.savetxt(f, np.array(i), fmt='%.2f', delimiter=',')
        f.close()

def saveData(data):
    data = ktoc(data)
    cstring = "dataCompleta"
    csv = np.mat(data)
    with open(cstring+'.csv','wb') as f:
        for i in csv:
            np.savetxt(f, np.array(i), fmt='%.3f', delimiter=' ')
        f.close()

def savePhotoData(name, data):
    csv = np.mat(data)
    with open(name+".csv",'w') as f:
        for i in csv:
            np.savetxt(f, np.array(i), fmt='%d', delimiter=' ')
        f.close()



def display_temperature(img, val_k, loc, color):
    val = ktoc(val_k)
    cv2.putText(img,"{0:.1f} degC".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)

def add_line(self, coords, t):
    line = "%s" % self.index
    x,y = coords
    self.list_ctrl.InsertItem(self.index, line)
    self.list_ctrl.SetItem(self.index, 1, str(x)+', '+str(y))
    self.list_ctrl.SetItem(self.index, 2, str(ktoc(t)))
    self.index += 1

def eraseLine(self, index):
    self.list_ctrl.DeleteItem(index)


class MyFrame(wx.Frame):
    def __init__(self, parent, ID, title):
        wx.Frame.__init__(self, parent, ID, title, size=(1010, 500))
        self.coordsSaved=[]
        self.savedCrops=[]
        self.currentImage=[]
        self.stream = True
        self.snapshot = 0
        self.currentData=[]
        self.pointTemps=[]

        # main_panel es el panel principal(la ventana entera)
        # panel1 es la izqda, panel 2 la derecha.
        main_panel = wx.Panel(self)
        panel1 = wx.Panel(main_panel,-1)

        self.streamPanel = wx.Panel(panel1,-1)
        panel2 = ButtonPanel(main_panel,-1)

        panel3 = wx.Panel(main_panel, -1, size=(230, 480))
        sbox = wx.BoxSizer(wx.VERTICAL)
        
 
        image = wx.Image(640, 480)
        imageBitmap = wx.Bitmap(image)
        self.videobmp = wx.StaticBitmap(self.streamPanel, wx.ID_ANY, imageBitmap)
        
        panel1.SetBackgroundColour("#000000")
        panel2.SetBackgroundColour("#e4e4e4")
        panel2.width = 300
        panel3.SetBackgroundColour("#e4e4e4")

        self.loadBtn = wx.Button(panel2, -1, "Abrir csv")
        self.loadBtn.Bind(wx.EVT_BUTTON,self.OnOpen)

        self.strBtn = wx.Button(panel2, -1, "video")
        self.strBtn.Bind(wx.EVT_BUTTON,self.s_stream)

        self.tenBtn = wx.Button(panel2, -1, "rafaga 10 fotos")
        self.tenBtn.Bind(wx.EVT_BUTTON,self.ten_pictures)
        
        self.btn = wx.Button(panel2, -1, "tomar foto")
        self.btn.Bind(wx.EVT_BUTTON,self.screenshot)

        self.button = wx.Button(panel3, -1, "guardar temps")
        self.button.Bind(wx.EVT_BUTTON,self.save_ts)
                    
        self.bbtn = wx.Button(panel3, -1, "deshacer circulo")
        self.bbtn.Bind(wx.EVT_BUTTON,self.undoCord)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        
        self.tick=0
        self.timer.Start(1000/9)

        sbox.Add(self.streamPanel, 1,wx.EXPAND | wx.ALL, 10)
        panel1.SetSizer(sbox)
    
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(panel2, 0, wx.EXPAND)
        box.Add(panel1, 0, wx.EXPAND)
        box.Add(panel3, 0, wx.EXPAND)
        
        box2 = wx.BoxSizer(wx.VERTICAL)
        box3 = wx.BoxSizer(wx.HORIZONTAL)
        
        box22 = wx.BoxSizer(wx.HORIZONTAL)
        box23 = wx.BoxSizer(wx.HORIZONTAL)
        box33 = wx.BoxSizer(wx.VERTICAL)
        
        box2.Add(self.strBtn, 0, wx.ALIGN_CENTER)
        box2.Add(self.btn, 0, wx.ALIGN_CENTER)
        box2.Add(self.tenBtn, 0, wx.ALIGN_CENTER)

        box3.Add(box2, 1, wx.ALIGN_CENTER)

        box22.Add(self.button, 0, wx.ALIGN_CENTER)
        box23.Add(self.bbtn, 0, wx.ALIGN_CENTER)

      

        self.index = 0
 
        self.list_ctrl = wx.ListCtrl(panel3, wx.ID_ANY, size=(220,-1),
                         style=wx.LC_REPORT | wx.BORDER_SUNKEN
                         )
        self.list_ctrl.InsertColumn(0, 'id', width=40)
        self.list_ctrl.InsertColumn(1, 'center', width=90)
        self.list_ctrl.InsertColumn(2, 'T en C', width=90)





        box33.Add(self.list_ctrl, 3, wx.EXPAND | wx.ALL, 5)
        box33.Add(box22, 1, wx.ALIGN_CENTER)
        box33.Add(box23, 1, wx.ALIGN_CENTER)


        panel2.SetSizer(box3)
        panel3.SetSizer(box33)



        main_panel.SetSizer(box)
        self.videobmp.Bind(wx.EVT_LEFT_DOWN, self.getCoordinates)

    def s_stream(self, event):
        self.stream = True

    def ten_pictures(self, event):
        self.snapshot=10

    def load_csv(self, event):
        self.stream = False

    def undoCord(self, event):
        size = len(self.coordsSaved)
        if len(self.coordsSaved)==len(self.savedCrops):
            if not self.stream:
                if len(self.coordsSaved)!=0:
                    eraseLine(self, size-1)
                    self.index-=1
                    self.coordsSaved = self.coordsSaved[:-1]
                    self.savedCrops = self.savedCrops[:-1]
                    self.pointTemps = self.pointTemps[:-1]
                    self.currentImage = getImage(self.currentData)
                    if self.currentImage != []:
                        j=0
                        for i in self.coordsSaved:
                            # print(i)        
                            j+=1
                            cv2.circle(self.currentImage, i, 15, (0,0,0), 3)
                            drawNumbers(self.currentImage, i, j)
                        width, height = 640, 480
                        image = wx.Image(width,height)
                        img = cv2.cvtColor(self.currentImage, cv2.COLOR_RGB2BGR)
                        image.SetData(img)
                        self.videobmp.SetBitmap(wx.Bitmap(image))
                        self.Refresh()
    
        else:
            print("ERROR FATAL")
            print(len(self.coordsSaved), len(self.savedCrops))
            exit(1)

            
    def save_ts(self, event):
        if len(self.savedCrops) > 0:
            path = './foto.tiff'
            # cv2.imwrite(path, cv2.cvtColor(self.currentImage, cv2.COLOR_RGB2BGR))
            cv2.imwrite(path, self.currentImage)
            saveData(self.currentData)
            saveCsv(self.savedCrops, self.pointTemps)
            
            if not os.path.exists("/home/pi/Desktop/resultados"):
                os.makedirs("/home/pi/Desktop/resultados")

            # if not os.path.exists("resultados"):
            #     os.makedirs("resultados") 

            names = ['foto.tiff', 'circulos_info.csv', 'circulos_full.csv','dataCompleta.csv']
            zipResults(names)
            for i in names:
                os.remove(i)
            self.currentImage = getImage(self.currentData)
            width, height = 640, 480
            image = wx.Image(width,height)
            img = cv2.cvtColor(self.currentImage, cv2.COLOR_RGB2BGR)
            image.SetData(img)
            self.videobmp.SetBitmap(wx.Bitmap(image))
            self.Refresh()
            self.coordsSaved=[]
            self.savedCrops=[]
            self.pointTemps=[]

            for _ in range(self.index):
                self.index-=1
                eraseLine(self, self.index)

        else:
            print("no hay mano bro")
    
    def OnOpen(self, event):
        # if self.currentData!=[]:
        #     print("has data!")
        #     return
        
        # otherwise ask the user what new file to open
        with wx.FileDialog(self, "Open .CSV file", wildcard="CSV files (*.csv)|*.csv",
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            prefix=pathname[:-4]
            suffix=['.csv', '.tiff']
            rows=[]
            try:
                with open(prefix+suffix[0], 'r') as file:
                    reader = csv.reader(file,delimiter=" ")
                    for r in reader:
                        row=[]
                        for i in r:
                            row.append(np.uint16(i))
                        rows.append(np.array(row))
            except IOError:
                wx.LogError("Cannot open file ")
            data=np.array(rows)
        self.stream=False
        self.coordsSaved = []
        if len(self.savedCrops) > 0:
            for _ in range(self.index):
                self.index-=1
                eraseLine(self, self.index)
            self.savedCrops = []
            self.pointTemps = []
        
        self.currentData=np.array(data)                  
        self.currentImage = getImage(data)

        #img = cv2.imread(prefix+suffix[1], cv2.IMREAD_COLOR)

        img = cv2.cvtColor(self.currentImage, cv2.COLOR_RGB2BGR)
        width, height = 640, 480
        image = wx.Image(width,height)
        image.SetData(img)
        self.videobmp.SetBitmap(wx.Bitmap(image))
        self.Refresh()
        

    def getCoordinates(self, event):
        x, y=event.GetPosition()
        # ss = str(x)+' '+str(y)
        img = self.currentImage
        crop =[]
        csv = []
        if img != []:    
            cv2.circle(img, (x,y), 15, (0,0,0), 3)
            self.coordsSaved.append((x,y))
            drawNumbers(img, self.coordsSaved[-1], len(self.coordsSaved))
            width, height = 640, 480
            image = wx.Image(width,height)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            image.SetData(img)
            self.videobmp.SetBitmap(wx.Bitmap(image))
            self.Refresh()
            x,y = getLocRaw((x,y))
            try:
                csv, crop=getCropMedium(self.currentData, x, y)
                #getCropMedium(self.currentData, x, y)
            except:
                self.coordsSaved = self.coordsSaved[:-1]
            if crop.shape != (9,9):
                print('circulo fuera de la imagen!')
            # elif len(self.coordsSaved)==len(self.savedCrops):
            #     print(len(self.coordsSaved), len(self.savedCrops))
            #     self.coordsSaved = self.coordsSaved[:-1]
            else:
                self.savedCrops.append(csv)
                self.pointTemps.append(ktoc(self.currentData[x][y]))
                add_line(self, (x,y), self.currentData[x][y])

        
    def screenshot(self, event):
        self.coordsSaved = []
        self.stream=False
        
        if len(self.savedCrops) > 0:
            for _ in range(self.index):
                self.index-=1
                eraseLine(self, self.index)
            self.savedCrops = []
            self.pointTemps = []

        data = q.get(True, 500)
        if data is None:
            print("no hay camera feed")
        else:
            # print(type(data), type(data[0]), type(data[0][1]), type(data[10][10]))
            self.currentData=np.array(data)    
            self.currentImage = getImage(data)
            img = cv2.cvtColor(self.currentImage, cv2.COLOR_RGB2BGR)
            width, height = 640, 480
            image = wx.Image(width,height)
            image.SetData(img)
            self.videobmp.SetBitmap(wx.Bitmap(image))
            self.Refresh()

    def onTimer(self, event):
        if self.tick==3:
            self.tick=0
        if self.stream:
            data = q.get(True, 500)
            if data is None:
                print("no hay camera feed")
            else:
                # print(type(data[0][3]))
                img = getImage(data)
                if self.snapshot>0 and self.tick==0:
                    now = datetime.now()
                    fstring=now.strftime("/home/pi/Desktop/resultados/%d-%m-%Y_%H:%M:%S:%f-foto_00"+str(11-self.snapshot))
                    # fstring=now.strftime("resultados/%d-%m-%Y_%H:%M:%S:%f-foto_00"+str(11-self.snapshot))
                    savePhotoData(fstring,data)
                    cv2.imwrite(fstring+".tiff", img)
                    self.snapshot-=1
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                width, height = 640, 480
                image = wx.Image(width,height)
                image.SetData(img)
                self.videobmp.SetBitmap(wx.Bitmap(image))
                self.Refresh()
        self.tick+=1


                

    

class ButtonPanel(wx.Panel):
    def __init__(self, parent, ID):
        wx.Panel.__init__(self, parent, ID, size=(120, 480))
       

if __name__ == "__main__":
    ctx = POINTER(uvc_context)()
    dev = POINTER(uvc_device)()
    devh = POINTER(uvc_device_handle)()
    ctrl = uvc_stream_ctrl()
    PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)

    res = libuvc.uvc_init(byref(ctx), 0)
    if res < 0:
        print("uvc_init error")
        exit(1)

    try:
        res = libuvc.uvc_find_device(ctx, byref(dev), PT_USB_VID, PT_USB_PID, 0)
        if res < 0:
            print("uvc_find_device error")
            exit(1)

        try:
            res = libuvc.uvc_open(dev, byref(devh))
            if res < 0:
                print("uvc_open error")
                exit(1)

            print("device opened!")
            frame_formats = uvc_get_frame_formats_by_guid(devh, VS_FMT_GUID_Y16)
            if len(frame_formats) == 0:
                print("device does not support Y16")
                exit(1)
            print(frame_formats)
            libuvc.uvc_get_stream_ctrl_format_size(devh, byref(ctrl), UVC_FRAME_FORMAT_Y16, frame_formats[0].wWidth, frame_formats[0].wHeight, int(1e7 / frame_formats[0].dwDefaultFrameInterval))
            res = libuvc.uvc_start_streaming(devh, byref(ctrl), PTR_PY_FRAME_CALLBACK, None, 0)
            if res < 0:
                print("uvc_start_streaming failed: {0}".format(res))
                exit(1)

            data = q.get(True, 500)
            if data is None:
                print("no hay camera feed")   
            app = wx.App()
            frame = MyFrame(None, -1, "Lepton Screen-Shoter")
            frame.Show()
            app.MainLoop()             
        finally:
            libuvc.uvc_unref_device(dev)
    finally:
        libuvc.uvc_exit(ctx)
    

