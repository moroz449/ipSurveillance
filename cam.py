import socket
import os
import numpy as np
import requests
from json import loads
from hashlib import md5
from time import time, sleep
import cv2
from datetime import datetime
from queue import Queue, Empty
from multiprocessing import Process
from multiprocessing import Queue as QueueP
from threading import Thread
from shutil import rmtree


def findCameraIP():
	while True:
		try:
			cameraIP=socket.gethostbyname("DCS-2132LB")
			print("camera found",cameraIP)
			return cameraIP
		except (socket.herror,socket.gaierror,): 
			print("camera not found, sleeping 5")
			sleep(5)



for path in ["./audio/", "./video/", "./audio/g711/", "./audio/wav/"]:
	if not os.path.exists(path): os.mkdir(path)

def dumpData(data, fileName):
	if isinstance(data,bytearray) or isinstance(data,bytes):
		with open(fileName,"wb") as f: f.write(data)
	elif isinstance(data, str):
		with open(fileName,"a") as f: f.write(data)
	else:
		bs



def oldCleaner():
	import shutil
	while True:
		try:
			while True:
				total, used, free = shutil.disk_usage("/")
				while (free//(2**30))<11:
					l0=listdir("./video/")
					l1=listdir("./audio/g711/")
					l0=min(l0)
					l1=min(l1)
					if l0<l1:
						os.remove("./video/"+l0)
					else:
						os.remove("./audio/g711/"+l1)
					total, used, free = shutil.disk_usage("/")
				sleep(300)
		except Exception as e:
			print("exception at old cleaner:",e)


def videoDumper(q):
	out = None
	while True:
		try:
			while True:
				el=q.get()
				if isinstance(el[0],str):
					if el[0]=="newFile": 
						# name, fourcc, framerate, shape
						if not out is None: bs
						out = cv2.VideoWriter("./video/"+el[1]+".mp4",cv2.VideoWriter_fourcc(*'mp4v'), el[2], el[3])
						continue
					elif el[0]=="endFile":
						out.release()
						out=None
					else: bs
				else:
					out.write(el[0])
		except Exception as e:
			print("exception at videoDumper:",e)





def videoCapture(qP):
	def makeBlurred(frame):
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		gray = cv2.GaussianBlur(gray, (21,21,), 0)
		return gray
	motionSensitivityThreshold=0.001
	frameRate=7
	qLock=0

	while True:
		try:
			cameraIP=findCameraIP()
			startTime=time()
			frameCnt=0
			cap=cv2.VideoCapture("rtsp://admin:admin@"+cameraIP+"/live2.sdp")
			q=Queue()
			_,prevFrame=cap.read()
			q.put([prevFrame,datetime.now()])
			prevFrame=makeBlurred(prevFrame)
			framesToSkip=frameRate
			oldestIx=0
			while True:
				_, frame=cap.read()
				frameCnt+=1
				if not frameCnt%100: 
					frameRate=int(round(frameCnt/(time()-startTime)))
				if qLock: qP.put((frame,))
				else: 
					q.put([frame,datetime.now()])
					if not qLock and q.qsize()>=frameRate*10: 
						q.get()


				if framesToSkip: 
					framesToSkip-=1
					continue
				framesToSkip=frameRate
				curFrame=makeBlurred(frame)
				diff_frame = cv2.absdiff(curFrame, prevFrame)
				thresh_frame = cv2.threshold(diff_frame, 30, 1, cv2.THRESH_BINARY)[1]
				thresh_frame = cv2.dilate(thresh_frame, None, iterations = 2)
				val=np.sum(thresh_frame)/(curFrame.shape[0]*curFrame.shape[1])
				motion=val>motionSensitivityThreshold
				prevFrame=curFrame
				if motion: 
					if not qLock: 
						print("motion detected @", datetime.now())
						qP.put(("newFile",datetime.now().isoformat(),frameRate,(frame.shape[1],frame.shape[0],)))
						while not q.empty():
							el=q.get_nowait()
							qP.put((el[0],))
					qLock=10
				if qLock==1:
					qP.put(("endFile",))
				if qLock: qLock-=1

		except Exception as e:
			print("exception video:",e)
			with open("./debug.log","a") as fl: fl.write(datetime.now().isoformat()+" video "+str(e)+"\n")
			exceptionOccured=True
			sleep(1)


def audioCapture():
	def getV(inp,key):
		ix=inp.find(key)
		if ix==-1: bs
		return inp[ix+len(key):inp.find(b"\r\n",ix)]
	def getHeader(raw):
		data=bytearray()
		while data[-4:]!=b"\r\n\r\n": data.append(raw.read(1)[0])
		return data

	buf=bytearray()
	fileStart=[time(), datetime.now().isoformat()]
	lastSend=time()
	lastTS=0
	exceptionOccured=False
	lastReceive=time()
	while True:
		try:
			cameraIP=findCameraIP()
			s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(3)
			s.connect((cameraIP,554))  
			req=b"SETUP rtsp://"+cameraIP.encode()+b"/live2.sdp/track2 RTSP/1.0\r\nCSeq: 1\r\nTransport: RTP/AVP;unicast;client_port=8002-8003\r\n\r\n"
			s.send(req)  
			resp = s.recv(1024)
			servPort=getV(resp,b"server_port=").decode()
			servPort=servPort.split("-")
			servPort=[int(l) for l in servPort]
			sessionN=getV(resp,b"Session: ")
			req=b"PLAY rtsp://"+cameraIP.encode()+b"/live2.sdp/track2 RTSP/1.0\r\nCSeq: 3\r\nRange: npt=0-\r\nSession: "+sessionN+b"\r\n\r\n"
			s.send(req)  
			resp = s.recv(1024)

			s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
			s1.settimeout(3)
			s1.bind(("", 8002))
			# s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
			# s2.settimeout(0.05)
			# s2.bind(("", 8003))

			seqNum=-1
			# ffmpeg -f mulaw -ar 8000 -i 0.g711 output_file3.wav
			while True:
				if time()-lastSend>10:
					# print("sending")
					req=b"PLAY rtsp://"+cameraIP.encode()+b"/live2.sdp/track2 RTSP/1.0\r\nCSeq: 3\r\nRange: npt=0-\r\nSession: "+sessionN+b"\r\n\r\n"
					s.send(req)  
					resp = s.recv(1024)
					# print(resp)
					# print()
					lastSend=time()
				# 	f.write(s1.recv(2**26)[12:])
				data=s1.recv(2**16)
				if exceptionOccured:
					exceptionOccured=False
					for _ in range(int(round((time()-lastReceive)/0.096))):
						buf.extend(data[12:])
				lastReceive=time()

				buf.extend(data[12:])
				if len(data)-12!=960: bs
				ts=int.from_bytes(data[4:8],"big")
				lastTS=ts
				if time()//3600!=fileStart[0]//3600:
					fName="./audio/g711/"+fileStart[1]+".g711"
					with open(fName,"wb") as f:
						f.write(buf)
						del buf[:]
						fileStart=[time(), datetime.now().isoformat()]
		except Exception as e:
			print("exception audio:",e)
			with open("./debug.log","a") as fl: fl.write(datetime.now().isoformat()+" audio "+str(e)+"\n")
			exceptionOccured=True
			sleep(1)



qP=QueueP()
oc=Process(target=oldCleaner, daemon=True)
vd=Process(target=videoDumper, args=(qP,), daemon=True)
vc=Process(target=videoCapture, args=(qP,), daemon=True)
ac=Process(target=audioCapture, daemon=True)

oc.start()
vd.start()
vc.start()
ac.start()

vc.join()
vd.join()
ac.join()
oc.join()














