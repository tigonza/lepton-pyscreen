import wx
import cv2

from uvctypes import *
import time
import numpy as np
from datetime import datetime

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
    return (coords[1]*120/480,coords[0]*160/640)

def raw_to_8bit(data):
    cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
    np.right_shift(data, 8, data)
    img = cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) # convert it to hsv
    # return cv2.applyColorMap(img, cv2.COLORMAP_JET)
    return img

def imgShow(data):
    data = cv2.resize(data[:,:], (640, 480))
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
    img = raw_to_8bit(data)
    display_temperature(img, minVal, minLoc, (0, 0, 255))
    display_temperature(img, maxVal, maxLoc, (255, 0, 0))
    return img

def getImage(data):
    data = cv2.resize(data[:,:], (640, 480))
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
    img = raw_to_8bit(data)
    display_temperature(img, minVal, minLoc, (0, 0, 255))
    display_temperature(img, maxVal, maxLoc, (255, 0, 0))
    return img

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

    sq = []
    if m != 5:
        a =[]
        for i in range(0,11):
            a.append(0)
        for i in range(0,m):
            sq.append(a)
    
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

def saveCsv(csv):
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H:%M:%S:%f")
    csv = np.mat(csv)
    with open(dt_string+'.csv','wb') as f:
        for i in csv:
            np.savetxt(f, np.array(i), fmt='%.2f', delimiter=',')
        f.close()


def display_temperature(img, val_k, loc, color):
    val = ktoc(val_k)
    cv2.putText(img,"{0:.1f} degC".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)

class MyFrame(wx.Frame):
    def __init__(self, parent, ID, title):
        wx.Frame.__init__(self, parent, ID, title, size=(1010, 500))
        self.coordsSaved=[]
        self.savedCrops=[]
        self.currentImage=[]
        self.currentData=[]

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
        # self.streamPanel.bitmap1 = wx.StaticBitmap(self.streamPanel, -1, img, (0, 0))
        
        panel1.SetBackgroundColour("#000000")
        panel2.SetBackgroundColour("#e4e4e4")
        panel2.width = 300
        panel3.SetBackgroundColour("#e4e4e4")

        
        
        
        self.btn = wx.Button(panel2, -1, "Tomar foto")
        self.btn.Bind(wx.EVT_BUTTON,self.screenshot)

        self.button = wx.Button(panel3, -1, "guardar temps")
        self.button.Bind(wx.EVT_BUTTON,self.save_ts)
                    
        self.bbtn = wx.Button(panel3, -1, "deshacer circulo")
        self.bbtn.Bind(wx.EVT_BUTTON,self.undoCord)
        

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
        
        box2.Add(self.btn, 0, wx.ALIGN_CENTER)
        box3.Add(box2, 1, wx.ALIGN_CENTER)

        box22.Add(self.button, 0, wx.ALIGN_CENTER)
        box23.Add(self.bbtn, 0, wx.ALIGN_CENTER)
        # box23 = wx.BoxSizer(wx.HORIZONTAL)

        listPanel = wx.Panel(panel3, -1)
        listPanel.height = 200
        listPanel.SetBackgroundColour("#FFFFFF")


        # box33.Add(box23, 1, wx.ALIGN_CENTER)
        box33.Add(listPanel, 1, wx.EXPAND | wx.ALL, 5)
        box33.Add(box22, 1, wx.ALIGN_CENTER)
        box33.Add(box23, 1, wx.ALIGN_CENTER)


        panel2.SetSizer(box3)
        panel3.SetSizer(box33)
        print("hah")



        main_panel.SetSizer(box)
        self.videobmp.Bind(wx.EVT_LEFT_DOWN, self.getCoordinates)

    def undoCord(self, event):
        print(len(self.coordsSaved),len(self.savedCrops) )
        if len(self.coordsSaved)==len(self.savedCrops) and len(self.coordsSaved)>0:
            self.coordsSaved = self.coordsSaved[:-1]
            self.savedCrops = self.savedCrops[:-1]
            self.currentImage = getImage(self.currentData)
            if self.currentImage != []:
                for i in self.coordsSaved:
                    print(i)        
                    cv2.circle(self.currentImage, i, 20, (0,0,255), 3)
                width, height = 640, 480
                image = wx.Image(width,height)
                image.SetData(self.currentImage)
                self.videobmp.SetBitmap(wx.Bitmap(image))
                self.Refresh()

            
    def save_ts(self, event):
        if len(self.savedCrops) > 0:
            saveCsv(self.savedCrops)
            self.currentImage = getImage(self.currentData)
            width, height = 640, 480
            image = wx.Image(width,height)
            image.SetData(self.currentImage)
            self.videobmp.SetBitmap(wx.Bitmap(image))
            self.Refresh()
            self.coordsSaved=[]
            self.savedCrops=[]
        else:
            print("no hay mano bro")


    def getCoordinates(self, event):
        x, y=event.GetPosition()
        # ss = str(x)+' '+str(y)
        img = self.currentImage
        if img != []:    
            cv2.circle(img, (x,y), 20, (0,0,255), 3)
            self.coordsSaved.append((x,y))
            width, height = 640, 480
            image = wx.Image(width,height)
            image.SetData(self.currentImage)
            self.videobmp.SetBitmap(wx.Bitmap(image))
            self.Refresh()
            x,y = getLocRaw((x,y))
            csv, crop=getCrop(self.currentData, x, y)
            if crop.shape != (11,11):
                print('circulo fuera de la imagen!')

            self.savedCrops.append(csv)

        
    def screenshot(self, event):
        self.coordsSaved = []
        ctx = POINTER(uvc_context)()
        dev = POINTER(uvc_device)()
        devh = POINTER(uvc_device_handle)()
        ctrl = uvc_stream_ctrl()
        PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)


        # print('Enter the path where the pictures will be saved:')
        # PATH = input()

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
                else:
                    self.currentData=np.array(data)
                    # now = datetime.now()
                    # dt_string = now.strftime("%d-%m-%Y_%H:%M:%S:%f")
                    # mat = np.matrix(data)

                    # with open(dt_string+'.csv','wb') as f:
                    #     for line in mat:
                    #         np.savetxt(f, line, fmt='%.2f', delimiter=',')
                    #     f.close()
                    
                    self.currentImage = getImage(data)
                    width, height = 640, 480
                    image = wx.Image(width,height)
                    image.SetData(self.currentImage)
                    self.videobmp.SetBitmap(wx.Bitmap(image))
                    self.Refresh()
                    # path = '/home/tomasgonzalez/Pictures/'+'LP_'+dt_string+'.tiff'
                    # cv2.imwrite(path, img)
            finally:
                libuvc.uvc_unref_device(dev)
        finally:
            libuvc.uvc_exit(ctx)

    # def capture(self, event):
    #     self.data = q.get(True, 500)
    #     if self.data is None:
    #         print("no hay camera feed")
    #     else:         
    #         img = getImage(self.data)
    #         width, height = 640, 480
    #         image = wx.Image(width,height)
    #         image.SetData(img)
    #         self.videobmp.SetBitmap(wx.Bitmap(image))
    #         self.Refresh()

    

class ButtonPanel(wx.Panel):
    def __init__(self, parent, ID):
        wx.Panel.__init__(self, parent, ID, size=(120, 480))


        

if __name__ == "__main__":
    app = wx.App()
    frame = MyFrame(None, -1, "Lepton Screen-Shoter")
    frame.Show()
    app.MainLoop()


