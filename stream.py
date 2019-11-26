import wx
import cv2
import numpy as np

import os
import re

from wx.lib.masked import NumCtrl

from uvctypes import *
import time
from datetime import datetime

try:
  from queue import Queue
except ImportError:
  from Queue import Queue
import platform


BUF_SIZE = 2
COLORS = [cv2.COLORMAP_AUTUMN, cv2.COLORMAP_BONE, cv2.COLORMAP_JET, cv2.COLORMAP_HOT, cv2.COLORMAP_OCEAN]
SELECTED_COLOR = 0
q = Queue(BUF_SIZE)


current_directory = ''
iteration = 1
mirror = True
width, height = (1920,1080)

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

PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)

def ktof(val):
  return (1.8 * ktoc(val) + 32.0)

def ktoc(val):
  return (val - 27315) / 100.0

def raw_to_8bit(data):
  cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
  np.right_shift(data, 8, data)
  img = cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)
  # img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) # convert it to hsv
  #return cv2.applyColorMap(img, cv2.COLORMAP_JET)
  return img

def display_temperature(img, val_k, loc, color):
    val = ktof(val_k)
    cv2.putText(img,"{0:.1f} degF".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)

def main():
    ctx = POINTER(uvc_context)()
    dev = POINTER(uvc_device)()
    devh = POINTER(uvc_device_handle)()
    ctrl = uvc_stream_ctrl()

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

            print_device_info(devh)
            print_device_formats(devh)

            frame_formats = uvc_get_frame_formats_by_guid(devh, VS_FMT_GUID_Y16)
            if len(frame_formats) == 0:
                print("device does not support Y16")
                exit(1)

            libuvc.uvc_get_stream_ctrl_format_size(devh, byref(ctrl), UVC_FRAME_FORMAT_Y16,
                frame_formats[0].wWidth, frame_formats[0].wHeight, int(1e7 / frame_formats[0].dwDefaultFrameInterval)
            )

            res = libuvc.uvc_start_streaming(devh, byref(ctrl), PTR_PY_FRAME_CALLBACK, None, 0)
            if res < 0:
                print("uvc_start_streaming failed: {0}".format(res))
                exit(1)
            
            try:
                counter = 3
                while True:
                    data = q.get(True, 500)
                    if data is None:
                        break
                    data = cv2.resize(data[:,:], (640, 480))
                    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
                    img = raw_to_8bit(data)
                    display_temperature(img, minVal, minLoc, (255, 0, 0))
                    display_temperature(img, maxVal, maxLoc, (0, 0, 255))
                    return img
            finally:
                libuvc.uvc_stop_streaming(devh)
        finally:
            libuvc.uvc_unref_device(dev)
    finally:
        libuvc.uvc_exit(ctx)

    
     

class webcamPanel(wx.Panel):
	
	def __init__(self, parent, camera, fps=12):
		global mirror
		
		wx.Panel.__init__(self, parent)
		
		self.camera = camera
		return_value, frame = self.camera.read()
		data = cv2.resize(frame[:,:], (640, 480))
		height, width = data.shape[:2]
		frame = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)
		if mirror:
			frame = cv2.flip(frame, 1)
		self.bmp = wx.Bitmap.FromBuffer(width, height, frame)
		
		
		self.SetSize((width,height))
		
		self.timer = wx.Timer(self)
		self.timer.Start(1000./fps)
		
		self.Bind(wx.EVT_PAINT, self.OnPaint)
		self.Bind(wx.EVT_TIMER, self.NextFrame)
		
	def OnPaint(self, e):
		dc = wx.BufferedPaintDC(self)
		dc.DrawBitmap(self.bmp, 0, 0)
		
	def NextFrame(self, e):
		return_value, frame = self.camera.read()
		print(frame.shape)
		if return_value:
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			if mirror:
				frame = cv2.flip(frame, 1)
			self.bmp.CopyFromBuffer(frame)
			self.Refresh()
			
class mainWindow(wx.Frame):
	def __init__(self, camera):
		
		#set up directory to save photos
		global current_directory
		current_directory = os.getcwd()
		
		#inheritence
		wx.Frame.__init__(self, None, style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN)
		self.Title = "webcam"
		#menubar
		menubar = wx.MenuBar()
		
		filemenu = wx.Menu()
		change_dir = filemenu.Append(-1, 'Change Directory', "Change the directory to save Photos")
		menubar.Append(filemenu, '&File')
		
		optionsmenu = wx.Menu()
		self.mirrorcheckbox = optionsmenu.AppendCheckItem(-1, 'Mirror Image', "Mirror")
		optionsmenu.Check(self.mirrorcheckbox.GetId(), True)
		resolutionsmenu = wx.Menu()
		self.sixforty = resolutionsmenu.AppendRadioItem(-1, '640x480', "640x480")
		self.ninteentwenty = resolutionsmenu.AppendRadioItem(-1, '1920x1080', "1920x1080")
		self.custom = resolutionsmenu.AppendRadioItem(-1, 'Custom', "Custom")
		resolutionsmenu.Check(self.ninteentwenty.GetId(), True)
		optionsmenu.Append(wx.ID_ANY, '&Resolutions', resolutionsmenu)
		menubar.Append(optionsmenu,'&Options')
		
		self.SetMenuBar(menubar)
		
		
		#main ui
		self.webcampanel = webcamPanel(self, camera)
		self.button = wx.Button(self, label="Take Picture!")
		
		main_window_sizer = wx.BoxSizer(wx.VERTICAL)
		
		main_window_sizer.Add(self.webcampanel, 7, wx.CENTER | wx.BOTTOM | wx.EXPAND, 1)
		main_window_sizer.SetItemMinSize(self.webcampanel, (640,480))
		main_window_sizer.Add(self.button, 1, wx.CENTER | wx.EXPAND)
		
		self.SetSizer(main_window_sizer)
		main_window_sizer.Fit(self)
		
		self.Bind(wx.EVT_MENU, self.change_dir, change_dir)
		self.Bind(wx.EVT_MENU, self.mirror, self.mirrorcheckbox)
		self.Bind(wx.EVT_MENU, self.resolution, self.sixforty)
		self.Bind(wx.EVT_MENU, self.resolution, self.ninteentwenty)
		self.Bind(wx.EVT_MENU, self.custom_resolution, self.custom)
		self.Bind(wx.EVT_BUTTON, self.take_picture, self.button)
			
	def change_dir(self, e):
		#declare global variables
		global current_directory
		global iteration
		#open the choose folder directory
		dialog = wx.DirDialog(None, "Choose a directory:",style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
		#wait for the okay
		if dialog.ShowModal() == wx.ID_OK:
			#grab the new directory
			current_directory = dialog.GetPath()
		#close the window
		dialog.Destroy()
		#reset the count for files
		iteration = 1

	def mirror(self, e):
		global mirror
		mirror = self.mirrorcheckbox.IsChecked()
			
	def resolution(self, e):
		global width
		global height
		
		if self.sixforty.IsChecked() == True:
			width = 640
			height = 480
		elif self.ninteentwenty.IsChecked() == True:
			width = 1920
			height = 1080
	
	def custom_resolution(self, e):
		
		global width
		global height
		
		dlg = wx.Dialog(self, size = (300,150))
		self.instructions = wx.StaticText(dlg, wx.ID_ANY, 'Here you can input a custom resolution. Make sure your camera supports it.')
		
		self.width = NumCtrl(dlg)
		self.width.SetAllowNegative(False)
		self.width.SetAllowNone(False)
		self.width.SetValue(width)
		self.placex = wx.StaticText(dlg, wx.ID_ANY, 'x')
		self.height = NumCtrl(dlg)
		self.height.SetAllowNegative(False)
		self.height.SetAllowNone(False)
		self.height.SetValue(height)
		
		self.enter = wx.Button(dlg, wx.ID_OK)
		self.cancel = wx.Button(dlg, wx.ID_CANCEL)
		
		wrap_sizer = wx.BoxSizer(wx.VERTICAL)
		instructions_sizer = wx.BoxSizer(wx.HORIZONTAL)
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		
		button_sizer.Add(self.enter, 0, wx.CENTER | wx.RIGHT, 5)
		button_sizer.Add(self.cancel, 0, wx.CENTER)
		instructions_sizer.Add(self.width, 1, wx.CENTER | wx.EXPAND)
		instructions_sizer.Add(self.placex, 0, wx.CENTER)
		instructions_sizer.Add(self.height, 1, wx.CENTER | wx.EXPAND)
		wrap_sizer.Add(self.instructions, 1, wx.CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
		wrap_sizer.Add(instructions_sizer, 0, wx.CENTER | wx.EXPAND | wx.ALL, 10)
		wrap_sizer.Add(button_sizer, 0, wx.CENTER | wx.BOTTOM, 10)
		
		dlg.SetSizer(wrap_sizer)
		dlg.Centre()
		dlg.Show()
		
		if dlg.ShowModal() == wx.ID_OK:
			height = self.height.GetValue()
			width = self.width.GetValue()
		
	def take_picture(self, e):
		#declare global variables
		global current_directory
		global iteration
		global mirror
		global height
		global width
		
		#get current frame from camera
		camera.set(3,width)
		camera.set(4,height)
		
		return_value, image = camera.read()
		#check to see if you should mirror image
		if mirror:
			image = cv2.flip(image, 1)
		#get the directory to save it in.
		filename = current_directory + "/000" + str(iteration) + ".png"
		#update the count
		iteration += 1
		#save the image
		cv2.imwrite(filename,image)
		#read the image (this is backwards isn't it?!
		saved_image = cv2.imread(filename)
		
		if height > 500:
			multiplyer = float(500.0 / height)
			multiplyer = round(multiplyer, 3)
			height *= multiplyer
			height = int(height)
			width *= multiplyer
			width = int(width)
		
		saved_image = cv2.resize(saved_image, (width,height))
		#show the image in a new window!
		cv2.imshow('Snapshot!',saved_image)
		camera.set(3, 640)
		camera.set(4,480)


DEFAULT_CAMERA_NAME = '/dev/v4l/by-id/usb-GroupGets_PureThermal_1_v1.1.0-video-index0'
device_num = 0
if os.path.exists(DEFAULT_CAMERA_NAME):
    device_path = os.path.realpath(DEFAULT_CAMERA_NAME)
    device_re = re.compile("\/dev\/video(\d+)")
    info = device_re.match(device_path)
    if info:
        device_num = int(info.group(1))
        print(device_num)
        print("Using default video capture device on /dev/video" + str(device_num))
else:
    print('default device num')
camera = cv2.VideoCapture(0)
app = wx.App()
window = mainWindow(camera)
window.Show()
app.MainLoop()