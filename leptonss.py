import wx
import os
import cv2
import sys
import csv

from uvctypes import *
import time
import numpy as np
from cv2def import *
import cv2def as cd
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
q = Queue(2)

class CircleEval:
    def __init__(self, coord, eva, number):
        self.number = number
        self.coord = coord
        self.eva = eva


class CircleConf:
    def __init__(self, line):
        words = line.split(':')
        self.default = False
        self.name = words[0]
        
        if self.name[0]=='*':
            self.name = self.name[1:]
            self.default=True
        self.coords = []
        for i in words[1].split('/'):
            numbers = i[1:-1].split(',')
            self.coords.append( (int(numbers[0]),int(numbers[1])) )     

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
            
def saveCallibrationMsg(self):
    dlg = wx.TextEntryDialog(None, 'Escriba nombre','Nueva Lista', style=wx.OK|wx.CANCEL)
    if dlg.ShowModal() == wx.ID_OK:
        self.name=dlg.GetValue()
        if self.name == '':
            return False
        aux = self.name.split(' ')
        if len(aux)>1:
            self.name=''
            for i in aux:
                self.name = self.name + i + '_'
            self.name = self.name[:-1]
        dlg.Destroy()
        return True
    else:
        return False
        
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

def add_line(self, coords, t):
    line = "%s" % self.index
    x,y = coords
    self.list_ctrl.InsertItem(self.index, line)
    self.list_ctrl.SetItem(self.index, 1, str(x)+', '+str(y))
    self.list_ctrl.SetItem(self.index, 2, str(ktoc(t)))
    self.index += 1

def eraseLine(self, index):
    self.list_ctrl.DeleteItem(index)

def loadConf():
    conf = []
    with open('conf.txt','r') as f:
        for i in range(5):
            l=f.readline().strip()
            conf.append(int(l))

        q = conf[-1]
        if q>0:
            for i in range(q):
                l=f.readline().strip()
                conf.append(CircleConf(l))
    return conf


class MyFrame(wx.Frame):
    def __init__(self, parent, ID, title):
        wx.Frame.__init__(self, parent, ID, title, size=(914, 500))

        # valores necesarios de tener en memoria
        self.coordsSaved=[]
        self.analizeCoord=[]
        self.currentImage=[]
        self.stream = True
        self.analizing = True
        self.currentData=[]
        self.pointTemps=[]
        self.callibrating = False
        self.index = 0
        self.image = wx.Image(640,480)
        self.conf=[]
        try:
            self.conf=loadConf()
        except:
            print('error')
        
        # main_panel es el panel principal(la ventana entera)
        # panel1 es la izqda, panel 2 la derecha.
        main_panel = wx.Panel(self)
        panel1 = wx.Panel(main_panel,-1)
        self.streamPanel = wx.Panel(panel1,-1)

        # define the tabs
        confPanel = wx.Notebook(main_panel, -1)

        #panel3 is the main panel, #panel4 is the conf panel
        panel3 = wx.Panel(confPanel, -1, size=(230, 500))
        panel4 = wx.Panel(confPanel, -1, size=(230, 500))
        panel5 = wx.Panel(confPanel, -1, size=(230, 500))


        confPanel.AddPage(panel3, 'main')
        confPanel.AddPage(panel4, 'config')
        confPanel.AddPage(panel5, 'norm')


        imageBitmap = wx.Bitmap(self.image)
        self.videobmp = wx.StaticBitmap(self.streamPanel, wx.ID_ANY, imageBitmap)
        
        panel1.SetBackgroundColour("#000000")
        panel3.SetBackgroundColour("#e4e4e4")
        panel4.SetBackgroundColour("#e4e4e4")
        panel5.SetBackgroundColour("#e4e4e4")


        #sbox is stream box. Contains streampanel. Fitted to panel1 
        sbox = wx.BoxSizer(wx.VERTICAL)
        sbox.Add(self.streamPanel, 1,wx.EXPAND | wx.ALL, 10)
        panel1.SetSizer(sbox)
    
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(panel1, 0, wx.EXPAND)
        box.Add(confPanel, 0, wx.EXPAND)

        boxMain = wx.BoxSizer(wx.VERTICAL)
        boxConfigInit = wx.BoxSizer(wx.VERTICAL)
        boxNorm = wx.BoxSizer(wx.VERTICAL)

        # Titulo resultados
        restitsizer = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(panel3, -1, '  Resultados del análisis')
        font = self.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        restitsizer.Add(title, 0, wx.ALL, 2)

        # Resultados listBox
        resBox= wx.BoxSizer(wx.HORIZONTAL)

        self.lister = wx.ListCtrl(panel3, wx.ID_ANY, style=wx.LC_REPORT)
        self.lister.InsertColumn(0, 'circulo', wx.LIST_FORMAT_CENTRE)
        self.lister.InsertColumn(1, 'max', wx.LIST_FORMAT_CENTRE)
        self.lister.InsertColumn(2, 'mean', wx.LIST_FORMAT_CENTRE)
        

        resBox.Add(self.lister,0,wx.EXPAND) 


        # Analizar button
        startBox = wx.BoxSizer(wx.HORIZONTAL)

        startButton = wx.Button(panel3, -1, "Analizar")
        startBox.AddStretchSpacer()
        startBox.Add(startButton, 1, wx.ALL, 5)
        
        # titulo umbral
        boxtitlesizer = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(panel4, -1, '  Umbral de selección')
        font = self.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        boxtitlesizer.Add(title, 0, wx.ALL, 2)


        # criterio de selección
        radSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.meanrad = wx.RadioButton(panel4,wx.ID_ANY, label = 'mean', style=wx.RB_GROUP) 
        self.maxrad = wx.RadioButton(panel4,wx.ID_ANY, label = 'max')

        if len(self.conf)>1:
            if self.conf[0] == 0:
                self.meanrad.SetValue(True)
            elif self.conf[0] == 1:
                self.maxrad.SetValue(True)

        radSizer.Add(self.meanrad, 0, wx.ALL, 5)
        radSizer.Add(self.maxrad, 0 , wx.ALL, 5)

        # inputs y labels
        supInputBox = wx.BoxSizer(wx.HORIZONTAL)
        labelOne = wx.StaticText(panel4, wx.ID_ANY, '  superior')
        self.umbralSupInput = wx.TextCtrl(panel4, wx.ID_ANY, '')

        supInputBox.Add(labelOne, 0, wx.ALL, 5)
        supInputBox.Add(self.umbralSupInput, 1 , wx.ALL|wx.EXPAND, 5)
        
        infInputBox = wx.BoxSizer(wx.HORIZONTAL)
        labelTwo = wx.StaticText(panel4, wx.ID_ANY, '  inferior  ')
        self.umbralInfInput = wx.TextCtrl(panel4, wx.ID_ANY, '')

        infInputBox.Add(labelTwo, 0, wx.ALL, 5)
        infInputBox.Add(self.umbralInfInput, 1 , wx.ALL|wx.EXPAND, 5)

        self.umbralSupInput.SetValue(str(self.conf[1]))
        self.umbralInfInput.SetValue(str(self.conf[2]))

        
        # titulo calibracion
        circtitlesizer = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(panel4, -1, '  Calibrar circulos')
        title.SetFont(font)
        circtitlesizer.Add(title, 0, wx.ALL, 2)

        # radio de circulo
        diamSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.srad = wx.RadioButton(panel4,wx.ID_ANY, label = 'S', style=wx.RB_GROUP)
        self.mrad = wx.RadioButton(panel4,wx.ID_ANY, label = 'M')
        self.lrad = wx.RadioButton(panel4,wx.ID_ANY, label = 'L')
                 
        diamSizer.Add(self.srad, 0, wx.ALL, 5)
        diamSizer.Add(self.mrad, 0 , wx.ALL, 5)
        diamSizer.Add(self.lrad, 0 , wx.ALL, 5)

        if self.conf[3] == 0:
            self.srad.SetValue(True)
        elif self.conf[3] == 1:
            self.mrad.SetValue(True)
        else:
            self.lrad.SetValue(True)


        # lista de posiciones predefinidas
        self.choices=[]
        self.confcoords=[]       
        self.defsec=0 
        for i in range(self.conf[4]):
            self.choices.append(self.conf[i+5].name)
            self.confcoords.append(self.conf[i+5].coords)
            if self.conf[i+5].default:
                self.defsec=i


        self.lst = wx.ComboBox(panel4, choices = self.choices , style = wx.CB_DROPDOWN|wx.CB_READONLY)
        self.lst.SetSelection(self.defsec)

        # botones para borrar y/o guardar la lista de circulos.
        lstCirSizer = wx.BoxSizer(wx.HORIZONTAL)
        confSaveSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.newButton = wx.Button(panel4, -1, "Nueva")
        self.eraseButton = wx.Button(panel4, -1, "Borrar")
        self.saveButton = wx.Button(panel4, -1, "Guardar/Cancelar Calibracion")
        self.saveButton.Disable()
        confButton = wx.Button(panel4, -1, "Guardar Configuracion")

        confSaveSizer.AddStretchSpacer()
        confSaveSizer.Add(confButton, 1, wx.ALL, 5)

        lstCirSizer.Add(self.newButton, 1, wx.ALL|wx.EXPAND, 5)
        lstCirSizer.Add(self.eraseButton, 1, wx.ALL|wx.EXPAND, 5)

        # titulo automatico vs manual.
        automansizer = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(panel5, -1, '  Normalizacion')
        font = self.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        automansizer.Add(title, 0, wx.ALL, 2)

        # tipo de seleccion
        automanradsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.autorad = wx.RadioButton(panel5,wx.ID_ANY, label = 'auto', style=wx.RB_GROUP) 
        self.manrad = wx.RadioButton(panel5,wx.ID_ANY, label = 'manual')

        automanradsizer.Add(self.autorad, 0, wx.ALL, 5)
        automanradsizer.Add(self.manrad, 0, wx.ALL, 5)

        self.autorad.SetValue(True)

        # inputs y labels
        abInputBox = wx.BoxSizer(wx.HORIZONTAL)
        
        labelOne = wx.StaticText(panel5, wx.ID_ANY, 'min')
        self.aInput = wx.TextCtrl(panel5, wx.ID_ANY, '')
        labelTwo = wx.StaticText(panel5, wx.ID_ANY, 'max')
        self.bInput = wx.TextCtrl(panel5, wx.ID_ANY, '')

        abInputBox.Add(labelOne, 0, wx.ALL, 5)
        abInputBox.Add(self.aInput, 0 , wx.EXPAND, 5)
        abInputBox.Add(labelTwo, 0, wx.ALL, 5)
        abInputBox.Add(self.bInput, 0 , wx.EXPAND, 5)
        self.bInput.Disable()
        self.aInput.Disable()

        # boxes para panel3
        boxMain.Add(restitsizer, 0, wx.ALL, 5)
        boxMain.Add(resBox, 0, wx.ALL|wx.EXPAND, 5)
        boxMain.AddStretchSpacer()
        boxMain.Add(startBox, 0, wx.ALL|wx.EXPAND, 2)

        panel3.SetSizer(boxMain)

        # botones para guardar o dejar por defecto la configuracion.
        boxConfigInit.Add(boxtitlesizer, 0, wx.ALL, 5)
        boxConfigInit.Add(radSizer, 0, wx.ALL, 2)
        boxConfigInit.Add(supInputBox, 0 , wx.ALL|wx.EXPAND, 2)
        boxConfigInit.Add(infInputBox, 0 , wx.ALL|wx.EXPAND, 2)
        boxConfigInit.Add(wx.StaticLine(panel4,), 0, wx.ALL|wx.EXPAND, 5)
        boxConfigInit.Add(circtitlesizer, 0, wx.ALL, 5)
        boxConfigInit.Add(diamSizer, 0, wx.ALL, 2)
        boxConfigInit.Add(self.lst, 0, wx.ALL|wx.EXPAND, 2)
        boxConfigInit.Add(lstCirSizer, 0, wx.ALL|wx.EXPAND, 2)
        boxConfigInit.Add(self.saveButton, 1, wx.ALL|wx.EXPAND, 7)
        boxConfigInit.Add(wx.StaticLine(panel4,), 0, wx.ALL|wx.EXPAND, 5)
        boxConfigInit.AddStretchSpacer()
        boxConfigInit.Add(confSaveSizer, 0, wx.ALL|wx.EXPAND, 2)


        panel4.SetSizer(boxConfigInit)
        main_panel.SetSizer(box)

        # boxes para panel5
        boxNorm.Add(automansizer, 0, wx.ALL, 5)
        boxNorm.Add(automanradsizer, 0, wx.ALL, 5)
        boxNorm.Add(abInputBox, 0, wx.ALL|wx.EXPAND, 5)
        boxNorm.Add(wx.StaticLine(panel5,), 0, wx.ALL|wx.EXPAND, 5)
        
        panel5.SetSizer(boxNorm)
        
        self.timer = wx.Timer(self)
        self.tick=0
        self.Bind(wx.EVT_TIMER, self.onTimer)        
        self.videobmp.Bind(wx.EVT_LEFT_DOWN, self.getCoordinates)
        self.videobmp.Bind(wx.EVT_RIGHT_DOWN, self.undoCord)
        self.saveButton.Bind(wx.EVT_BUTTON , self.saveCircles)
        self.newButton.Bind(wx.EVT_BUTTON, self.on_open)
        self.eraseButton.Bind(wx.EVT_BUTTON, self.deleteList)
        confButton.Bind(wx.EVT_BUTTON, self.saveConf)
        self.autorad.Bind(wx.EVT_RADIOBUTTON, self.radioButtonEvt)
        self.manrad.Bind(wx.EVT_RADIOBUTTON, self.radioButtonEvt)
        startButton.Bind(wx.EVT_BUTTON, self.analize)
        self.lst.Bind(wx.EVT_COMBOBOX_CLOSEUP, self.lstUpdate)

        self.timer.Start(1000/8)

    def lstUpdate(self, event):
        self.analizeCoord = []

    def radioButtonEvt(self, event):
        a=event.GetEventObject().GetLabel()
        if a == 'auto':
            self.bInput.Disable()
            self.aInput.Disable()
        else:
            self.bInput.Enable()
            self.aInput.Enable()

    def undoCord(self, event):
        size = len(self.coordsSaved)
        if size > 0:
            self.coordsSaved = self.coordsSaved[:-1]
        else:
            self.callibrating = False
            self.saveButton.Disable()
            self.lst.Enable()
            self.eraseButton.Enable()
            self.newButton.Enable()
    
    def saveCircles(self, event):
        if len(self.coordsSaved)==0:
            print('gg')
        msg='Calibracion Cancelada'
        if saveCallibrationMsg(self):
            self.confcoords.append(self.coordsSaved)
            self.choices.append(self.name)
            self.lst.Append(self.name)

            with open('conf.txt','r') as f:
                data=f.readlines()
            
            data[4] = str(len(self.confcoords))+'\n'
            s = self.name+':'
            for i in self.coordsSaved:
                s = s+str(i)
                if i != self.coordsSaved[-1]:
                    s = s+'/'
            data[-1] =data[-1]+'\n' 
            data.append(s)
            
            with open('conf.txt','w') as f:
                f.writelines(data)

            msg = 'Guardado exitoso'
            self.conf[4]+=1
        dlg = wx.MessageDialog(None, msg, '',wx.OK)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            dlg.Destroy()
        self.name=''
        self.callibrating=False
        self.saveButton.Disable()
        self.lst.Enable()
        self.eraseButton.Enable()
        self.newButton.Enable()
        self.coordsSaved=[]

    def on_open(self, event):
        dlg = wx.MessageDialog(None, 'Use el click derecho para colocar un nuevo circulo. \nUse el click izquierdo para deshacer el ultimo circulo.', 'Instrucciones de calibración',wx.OK)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            dlg.Destroy()
            self.coordsSaved = []
            self.callibrating=True
            self.saveButton.Enable()
            self.lst.Disable()
            self.eraseButton.Disable()
            self.newButton.Disable()
                
    def getCoordinates(self, event):
        x, y=event.GetPosition()
        if self.callibrating:    
            self.coordsSaved.append((x,y))

    def deleteList(self, event):
        l = self.lst.GetStrings()
        if len(l)>1:
            n = self.lst.GetCurrentSelection()
            self.lst.Delete(n)
            self.lst.SetSelection(0)
            self.confcoords.pop(n)
            self.choices.pop(n)
        else:
            self.lst.Append('')
            self.lst.SetSelection(1)
            self.lst.Clear()
            self.eraseButton.Disable()

    def onTimer(self, event):
        if self.stream:
            self.currentData = q.get(True, 500)
            if data is None:
                print("no hay camera feed")
            else:
                ab = (self.aInput.GetValue(), self.bInput.GetValue())
                img=[]
                if self.autorad.GetValue():
                    img = getImage2(self.currentData)
                else:
                    try:
                        ab = (int(ab[0]),int(ab[1]))
                        img = getImage2(self.currentData, ab)
                    except:
                        img = getImage2(self.currentData)
                
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                index=self.lst.GetCurrentSelection()
                l=self.confcoords[index] 
                if self.callibrating:
                    for i in range(len(self.coordsSaved)):
                        cv2.circle(img, self.coordsSaved[i], 15, (0,0,0), 3)
                        drawNumbers(img, self.coordsSaved[i], i+1, (0,0,0))
                else:
                    c=1
                    if len(self.analizeCoord)>0:
                        for i in self.analizeCoord:
                            cv2.circle(img, i.coord, 15, i.eva, 3)
                            drawNumbers(img, i.coord, i.number, i.eva)
                    else:
                        for i in l:
                            cv2.circle(img, i, 15, (0,0,0), 3)
                            drawNumbers(img, i, c, (0,0,0))
                            c+=1
                self.image.SetData(img)
                self.videobmp.SetBitmap(wx.Bitmap(self.image))
                self.Layout()
    
    def saveConf(self, event):
        with open('conf.txt', 'r') as file:
            data = file.readlines()
        a=1
        if self.meanrad.GetValue():
            a=0
        newConf = [str(a)+'\n',self.umbralSupInput.GetValue()+'\n',self.umbralInfInput.GetValue()+'\n']
        if self.mrad.GetValue():
            newConf.append('1\n')
        else:
            newConf.append('0\n')
        data[:4] = newConf

        aux=[]
        if int(data[4])!=len(self.confcoords):
            for i in range(len(self.confcoords)):
                s = self.choices[i]+':'
                for j in self.confcoords[i]:
                    s = s+str(j)
                    if j != self.confcoords[i][-1]:
                        s = s+'/'
                aux.append(s+'\n')
            data[4] = str(len(self.confcoords))+'\n'
            data[5:] = aux
            data[-1] = data[-1][:-1]

        
        with open('conf.txt','w') as f:
            f.writelines(data)
                
    def analize(self, event):
        self.lister.DeleteAllItems()
        index=self.lst.GetCurrentSelection()
        rawCoords=[]
        evals = []
        count=1
        for i in self.confcoords[index]:
            x,y =getLocRaw(i)
            temps=[]
            square=[]
            value=0.0
            if self.mrad.GetValue():
                temps, square = getCropMedium(self.currentData, x, y)
            else:
                temps, square = getCrop(self.currentData, x, y)

            if self.meanrad.GetValue():
                value=np.mean(temps)
            else:
                value=np.max(temps)

            sup = int(self.umbralSupInput.GetValue())
            inf = int(self.umbralInfInput.GetValue())

            resp=None
            if value>sup:
                resp=CircleEval(i, (41,255,0), count)
            elif value<sup and value>inf:
                resp=CircleEval(i, (255,214,0), count)
            else:
                resp=CircleEval(i, (255,0,0), count)
            count+=1

            index = self.lister.InsertItem(sys.maxsize, str(resp.number)) 
            self.lister.SetItem(index, 1, "{0:.2f}".format(np.max(temps)) ) 
            self.lister.SetItem(index, 2, "{0:.2f}".format(np.mean(temps)) )
            rawCoords.append(resp)

        self.analizeCoord=rawCoords


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