import threading
import re
import time

class SerialJob:
	done = False
	result = ""

	def __init__(self, regex):
		self.regex = regex

class GlobalJob:
	def __init__(self, regex, f):
		self.callback = f
		self.regex = regex

class SerialPoller:
	buf = ""
	jobs = []
	logs = []

	def __init__(self, dev, serial):
		self.device = dev
		self.serial = serial
		self.global_jobs = [
			GlobalJob("\+CIEV:[0-9]+,[0-9]+\r", dev._handle_signal)
		]
		self.thread = threading.Thread(target=self.worker)
		self.thread.start()

	def worker(self):
		while True:
			byte = self.serial.read(1)
			self.buf += byte

			for job in self.jobs:
				if re.match(job.regex, self.buf) != None:
					job.done = True
					job.result = self.buf
					self.jobs.remove(job)

			if byte == "\r" or byte == "\n":
				# check for unsolicited updates
				for job in self.global_jobs:
					if re.match(job.regex, self.buf):
						job.callback(self.buf[:-1])
				self.logs.append(self.buf[:-1])
				self.buf = ""

	def _reset(self):
		self.jobs = []
		self.buffer = ""
		self.logs = []

	def read_until(self, regex):
		self._reset()
		job = SerialJob(regex)
		self.jobs.append(job)
		while not job.done:
			time.sleep(0.5)
		return job.result, self.logs

	def wait_for(self, regex):
		self._reset()
		job = SerialJob(regex)
		self.jobs.append(job)
		while not job.done:
			time.sleep(0.5)
		return job.result
