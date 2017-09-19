from itertools import chain
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import tkinter as tk
import random
import asyncio
import socket
import datetime
import time
import json
import os
import uuid
from game import Bonus, BonusCreator, Asteroid, Rocket, СontainerWithIds

MODE = 1

def onclose(root, loop):
	for task in asyncio.Task.all_tasks():
		task.cancel()
	asyncio.ensure_future(exit(loop))


async def exit(loop):
	loop.stop()


class Server:

	def __init__(self, loop):
		self.loop = loop
		self.MODE = 1
		self.connections = []
		self.asteroids = СontainerWithIds()
		self.bonuses = СontainerWithIds()
		self.WIDTH = 500
		self.HEIGHT = 680

		self.sock = socket.socket()
		self.sock.bind(('localhost', 5678))
		self.sock.listen(2)
		self.sock.setblocking(False)
		print("=======Server run on {}:{}=======".format(socket.gethostbyname(socket.gethostname()), 5678))

	async def accept_connections(self):
		print("Connections reaminig...")
		while True:
			conn, addr = await loop.sock_accept(self.sock)
			self.connections.append(conn)
			conn.send(b"/hello")
			print("New conn:", addr, conn, len(self.connections))
			if len(self.connections) == 2:
				asyncio.ensure_future(self.get_req())
				return 0

	async def end_coo(self):
		await asyncio.sleep(20)
		self.MODE = 0
		[await loop.sock_sendall(c, b'/end') for c in self.connections]
		pass

	async def update(self):
		await asyncio.sleep(3)
		while self.MODE == 1:
			msg = defaultdict(list)
			current_time = datetime.datetime.now().time()
			pick = random.randint(1, self.WIDTH)
			await asyncio.sleep(0.0005)

			if pick % 2 == 0 and len(self.asteroids) < 7:
				new_asteroids = [Asteroid(random.randint(10, self.WIDTH - 10), 0) for x in range(random.randint(1, 2))]
				msg['create'] += [x.serialize() for x in new_asteroids]
				for new_asteroid in new_asteroids:
					self.asteroids.append(new_asteroid)
				if len(new_asteroids):
					print("POST S[{}]".format(datetime.datetime.now().time()), msg)
					[await self.loop.sock_sendall(c, json.dumps(msg).encode()) for c in self.connections]


			print("B:{}".format(len(self.asteroids)))

			self.asteroids =  СontainerWithIds([x for x in self.asteroids if x])
			

			for objs in (self.asteroids,):
				for obj in objs:
					if obj.y < 0 or obj.y > self.HEIGHT:
						obj.сease_to_exist()
						objs.remove_by_id(obj.id)

	async def get_req(self):
		while True:
			await asyncio.sleep(0.00005)
			for conn in self.connections:
				try:
					msg = conn.recv(1024)
					msg_decoded = msg.decode()
					print("GET S [{}]".format(datetime.datetime.now().time()), msg_decoded)
					if msg_decoded == "/duel":
						self.MODE = 2
						continue
					elif msg_decoded == "/co":
						self.MODE = 1
						asyncio.ensure_future(self.update())
						asyncio.ensure_future(self.end_coo())
						continue
					if msg_decoded == "/close":
						self.MODE = 0
						[await loop.sock_sendall(c, b'/close') for c in self.connections if c != conn]
						continue
					if not msg:
						self.connections.remove(conn)
						asyncio.ensure_future(self.accept_connections())
						return 0
					
					msg_decoded = json.loads(msg_decoded)
					if 'dispose' in msg_decoded:
						for item in msg_decoded['dispose']:
							_id = item['id']
							self.asteroids.remove_by_id(_id)
							self.bonuses.remove_by_id(_id)
					[await loop.sock_sendall(c, msg) for c in self.connections if c != conn]
				except socket.error:
					pass
				except json.decoder.JSONDecodeError:
					pass


async def exit():
	loop.stop()

loop = asyncio.get_event_loop()

server = Server(loop)
asyncio.ensure_future(server.accept_connections())

try:
	loop.run_forever()
finally:
	loop.close()
