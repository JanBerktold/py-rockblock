import threading
import re
import time

class SerialJob:
	done = False
	result = ""

	def __init__(self, regex):
		if isinstance(regex, str):
			self.regex = re.compile(regex)
		else:
			self.regex = regex

class GlobalJob:
	def __init__(self, regex, f, arg = None):
		self.callback = f
		self.regex = regex
		self.arg = arg

class SerialPoller:
	buf = ""
	jobs = []
	logs = []
	running = True

	def __init__(self, dev, serial):
		self.device = dev
		self.serial = serial
		self.global_jobs = [
			GlobalJob("SBDRING", dev._initiate_session_async, True),
			GlobalJob("\+AREG", dev._interpret_registration)
		]
		self.thread = threading.Thread(target=self.worker)
		self.thread.start()

	def worker(self):
		while self.running and self.serial.isOpen():
			try:
				byte = self.serial.read(1)
			except Exception:
				break
			if len(byte) > 0:
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
							job.callback(self.buf[:-1], job.arg)
					self.logs.append(self.buf[:-1])
					self.buf = ""

		self.running = False

	def _reset(self):
		self.jobs = []
		self.buffer = ""
		self.logs = []

	def read_until(self, regex):
		self._reset()
		job = SerialJob(regex)
		self.jobs.append(job)
		while not job.done and self.running:
			time.sleep(0.5)
		return job.result, self.logs

	def wait_for(self, regex):
		self._reset()
		job = SerialJob(regex)
		self.jobs.append(job)
		while not job.done and self.running:
			time.sleep(0.5)
		return job.result
