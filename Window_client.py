from itertools import chain

from game import *
from collections import defaultdict
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as font
from tkinter import messagebox as msgBox
import random
import asyncio
import socket
import datetime
import time
import json
import sys
import uuid


class Mode:

	def initialize(self):
		pass

	def run(self):
		pass

	def update(self):
		pass

	def close(self):
		pass


class BattleField:

	def __init__(self, root):
		self.WIDTH = 500
		self.HEIGHT = 680
		self.root = root
		self.canvas = tk.Canvas(root, width=self.WIDTH, height=self.HEIGHT, bg='white')
		self.canvas.focus_set()
		self.canvas.pack()
		self.root.resizable(False, False)
		self.background = self.canvas.create_image(
			self.WIDTH / 2, self.HEIGHT / 2, image=Resources.space_img)

		self.rockets = SmartConteiner()
		self.ship = ShipDrawCreator.createShip(
			Ship(0, 0, name="Ship"), self.canvas)

		self.rockets = SmartConteiner()
		id_getter = lambda x: x.get_revolving_obj().id
		self.enemy_rockets = SmartConteiner(id_getter=id_getter)
		self.asteroids = SmartConteiner(id_getter=id_getter)
		self.bonuses = SmartConteiner(id_getter=id_getter)

	def remove_not_exists(self):
		for sc in (self.asteroids, self.rockets, self.bonuses, self.enemy_rockets):
			sc.remove_not_exists()

	def dispose_all(self):
		self.canvas.delete("all")
		self.canvas.pack_forget()


class SingleMode(Mode):

	def __init__(self, battlefield, nullable_arg):
		self.bf = battlefield
		self.score = 0
		self.speed = 0.5

	def initialize(self):
		self.binds = []
		self.tasks = []
		self.hp_label = Label(self.bf.canvas, 100, 20, text=self.get_hp_bar(), font=('Helvetica', 10), fill='#00ACE6')
		self.score_label = Label(self.bf.canvas, 100, 20, text="Score: {}".format(self.score), font=('Helvetica', 12), fill='#00435A')
		self.binds.append(self.bf.canvas.bind("<Button-1>", self.on_l_click))
		self.binds.append(self.bf.canvas.bind("<Button-3>", self.on_r_click))
		self.bf.root.config(cursor='none')

	def get_hp_bar(self):
		count = self.bf.ship.health // 20
		bar = ''
		for i in range(count):
			bar += '\u2B1B'
		return bar

	def update_score(self):
		for asteroid in (x for x in self.bf.asteroids if not x):
			if asteroid.killer is not None:
				self.score += 1
		self.score_label.text = str(self.score)


	def on_l_click(self, event):
		new_rocket = self.bf.ship.fire()
		self.bf.rockets.append(RocketDrawDecorator(new_rocket, self.bf.canvas))

	def on_r_click(self, event):
		self.bf.ship.special(self.bf.asteroids)

	def run(self):
		self.tasks.append(asyncio.ensure_future(self.change_speed()))
		self.tasks.append(asyncio.ensure_future(self.update()))

	async def change_speed(self):
		while True:
			await asyncio.sleep(2)
			self.speed += 0.125

	def handle_msg(self, msg):
		pass

	def update_ship_coords(self):
		x = self.bf.root.winfo_pointerx() - self.bf.root.winfo_rootx()
		y = self.bf.root.winfo_pointery() - self.bf.root.winfo_rooty()
		if x > 0 and x < self.bf.WIDTH:
			self.bf.ship.x = x
			self.hp_label.x = x
			self.score_label.x = x
		if y > 0 and y < self.bf.HEIGHT:
			self.bf.ship.y = y
			self.hp_label.y = y + 70
			self.score_label.y = y + 90

	def close(self):
		[task.cancel() for task in self.tasks]
		[self.bf.canvas.unbind(x) for x in self.binds]
		self.bf.dispose_all()
		self.bf.root.config(cursor='arrow')

	async def show_result(self):
		kw = {'font': ('Helvetica', 16), 'fill': 'white'}
		text = "РЕЗУЛЬТАТ: {}".format(self.score)
		Label(self.bf.canvas, self.bf.WIDTH / 2 , self.bf.HEIGHT / 2, text=text, **kw)
		await asyncio.sleep(0.5)
		Label(self.bf.canvas, self.bf.WIDTH / 2 , self.bf.HEIGHT / 2 + 100, text="Нажмите ESC для выхода", **kw)

	async def update(self):
		while True:
			await asyncio.sleep(0.000005)
			current_time = datetime.datetime.now().time()
			self.update_ship_coords()
			self.bf.ship.redraw()
			self.hp_label.redraw()
			self.score_label.redraw()

			if self.bf.ship.health <= 0:
				await self.show_result()
				return 0

			objs = (self.bf.asteroids, self.bf.rockets, self.bf.bonuses, self.bf.enemy_rockets)
			for obj in chain(*objs):
				obj.fly()
				if obj.y < 0 or obj.y > self.bf.HEIGHT:
					obj.dispose()
			self.update_score()
			self.bf.remove_not_exists()

			ship_bbox = self.bf.ship.get_boundbox()
			for asteroid in self.bf.asteroids:
				asteroid_bbox = asteroid.get_boundbox()
				if bbox_in_bbox(*ship_bbox, *asteroid_bbox):
					self.bf.ship.health -= 20
					self.hp_label.text = self.get_hp_bar()
					self.tasks.append(asyncio.ensure_future(asteroid.destroy()))

			for bonus in self.bf.bonuses:
					bonus_bbox = bonus.get_boundbox()
					if bbox_in_bbox(*ship_bbox, *bonus_bbox):
						bonus.install_special(self.bf.ship)
						bonus.dispose()

			self.bf.root.title(string="CLIENT: " + str(current_time) + str(self.speed))

			for rocket in self.bf.rockets:
				for asteroid in self.bf.asteroids:
					try:
						if point_in_bbox(rocket.x, rocket.y, asteroid.get_boundbox()):
							asteroid.killer = rocket.owner
							self.tasks.append(asyncio.ensure_future(asteroid.destroy()))
							rocket.dispose()
					except TypeError:
						asteroid.dispose()
						self.asteroids.remove(asteroid)


			pick = random.randint(1, self.bf.WIDTH)

			if pick % 2 == 0 and len(self.bf.asteroids) < 7:
				new_asteroids = [Asteroid(random.randint(10, self.bf.WIDTH - 10), 0, self.speed) for x in range(random.randint(1, 2))]
				for new_asteroid in new_asteroids:
					self.bf.asteroids.append(AsteroidDrawDecorator(new_asteroid, self.bf.canvas))

			if current_time.second % 5 == 0 and len(self.bf.bonuses) < 2:
				new_bonuses = BonusCreator.createBonus(pick, random.randint(10, self.bf.WIDTH - 10), 0)
				self.bf.bonuses.append(BonusDrawDecorator(new_bonuses, self.bf.canvas))


class DuelMode(Mode):
	def __init__(self, battlefield, socket):
		self.bf = battlefield
		self.score = defaultdict(int)
		self.socket = socket
		self.msg = defaultdict(list)
		self.last_pos = None
		self.last_shoot_time = time.time()
		self.binds = []

	def initialize(self):
		self.bf.ship_enemy = ShipDrawCreator.createShip(
			Ship(0, 0, name="Enemy ship"),
			self.bf.canvas, _type='reverse'
		)
		self.binds.append(self.bf.canvas.bind("<Button-1>", self.on_l_click))
		self.bf.root.config(cursor='none')
		self.hp_label = Label(self.bf.canvas, 100, 20, text=self.get_hp_bar(self.bf.ship), font=('Helvetica', 10), fill='#00ACE6')
		self.hp_enemy_label = Label(self.bf.canvas, 100, 20, text=self.get_hp_bar(self.bf.ship_enemy), font=('Helvetica', 10), fill='red')

	def on_l_click(self, event):
		now = time.time()
		if now - self.last_shoot_time >= 0.5:
			self.last_shoot_time = now
			new_rocket = self.bf.ship.fire()
			self.bf.rockets.append(RocketDrawDecorator(new_rocket, self.bf.canvas))
			self.msg['create'].append(new_rocket.serialize())

	def run(self):
		self.socket.send(b"/duel")
		tasks = (self.update(), self.get_ship_pos(), self.send_msg())
		self.tasks = [asyncio.ensure_future(task) for task in tasks]

	def close(self):
		[task.cancel() for task in self.tasks]
		[self.bf.canvas.unbind(x) for x in self.binds]
		self.bf.dispose_all()
		self.bf.root.config(cursor='arrow')

	async def show_result(self):
		kw = {'font': ('Helvetica', 16), 'fill': 'white'}
		text = "ПОБЕДА" if self.bf.ship_enemy.health < self.bf.ship.health else "ПОРАЖЕНИЕ" 
		Label(self.bf.canvas, self.bf.WIDTH / 2 , self.bf.WIDTH / 2, text=text, **kw)
		await asyncio.sleep(0.5)
		Label(self.bf.canvas, self.bf.WIDTH / 2 , self.bf.HEIGHT / 2 + 100, text="Нажмите ESC для выхода", **kw)

	def get_hp_bar(self, ship):
		count = ship.health // 10
		bar = ''
		for i in range(count):
			bar += '\u2B1B'
		return bar

	async def get_ship_pos(self):
		while True:
			await asyncio.sleep(0.05)
			if self.last_pos != (self.bf.ship.x, self.bf.ship.y):
				self.last_pos = (self.bf.ship.x, self.bf.ship.y)
				self.msg['ship'] = 0

	def update_ship_coords(self):
		x = self.bf.root.winfo_pointerx() - self.bf.root.winfo_rootx()
		y = self.bf.root.winfo_pointery() - self.bf.root.winfo_rooty()

		if x > 20 and x < self.bf.WIDTH - 20:
			self.bf.ship.x = x
			self.hp_label.x = x
		elif x < 20:
			self.bf.ship.x = 20
			self.hp_label.x = 20
		else:
			self.bf.ship.x = self.bf.WIDTH - 20
			self.hp_label.x = self.bf.HEIGHT - 20

		if y >= self.bf.HEIGHT / 2 + 20 and y < self.bf.HEIGHT:
			self.bf.ship.y = y
			self.hp_label.y = y + 80

	async def send_msg(self):
		while True:
			await asyncio.sleep(0.005)
			if self.msg:
				self.msg['ship'] = self.bf.ship.serialize()
				print("POST C[{}]".format(datetime.datetime.now().time()), self.msg)
				# self.socket.send(json.dumps(self.msg).encode())
				await loop.sock_sendall(self.socket, json.dumps(self.msg).encode())
				self.msg = defaultdict(list)

	def handle_msg(self, msg):
		try:
			msg = json.loads(msg)
			if 'create' in msg:
				for item in msg['create']:
					rocket = Rocket(
						item['coords'][0], self.bf.HEIGHT - item['coords'][1],
						owner=self.bf.ship_enemy
					)
					rocket.id = item['id']
					rocket = ReversedRocketDecorator(rocket)
					self.bf.enemy_rockets.append(
						RocketDrawDecorator(rocket, self.bf.canvas, Resources.reversed_rocket_img)
					)

			if 'dispose' in msg:
				print('dispose')
				for item in msg['dispose']:
					[x.dispose() for x in self.bf.enemy_rockets if x.get_revolving_obj().id == item['id']]
				self.bf.remove_not_exists()

			if 'hp' in msg:
				self.bf.ship.health = msg['hp']
				self.hp_label.text = self.get_hp_bar(self.bf.ship)

			if 'ship' in msg:
				print("ENEMY: ", msg['ship']['coords'])
				self.bf.ship_enemy.x = msg['ship']['coords'][0]
				self.bf.ship_enemy.y = self.bf.HEIGHT - msg['ship']['coords'][1]
				self.hp_enemy_label.x = msg['ship']['coords'][0]
				self.hp_enemy_label.y = self.bf.HEIGHT - msg['ship']['coords'][1] - 80
		except json.decoder.JSONDecodeError:
			pass


	async def update(self):
		while True:
			await asyncio.sleep(0.0000005)
			current_time = datetime.datetime.now().time()

			if self.bf.ship.health <= 0 or self.bf.ship_enemy.health <= 0:
				await self.show_result()
				return 0

			self.update_ship_coords()

			self.bf.ship.redraw()
			self.bf.ship_enemy.redraw()
			self.hp_label.redraw()
			self.hp_enemy_label.redraw()
			for obj in chain(self.bf.rockets, self.bf.enemy_rockets):
				obj.fly()
				if obj.y < 0 or obj.y > self.bf.HEIGHT:
					obj.dispose()

			self.bf.remove_not_exists()

			self.bf.root.title(string="CLIENT: " + str(current_time) + " Rockets: %d Ast.: %d" % (len(self.bf.rockets), len(self.bf.asteroids)) + str(self.score.items()))

			enemy_ship_bbox = self.bf.ship_enemy.get_boundbox()
			shoots = 0
			for rocket in self.bf.rockets:
				try:
					if point_in_bbox(rocket.x, rocket.y, enemy_ship_bbox):
						self.bf.ship_enemy.health -= 10
						shoots += 10
						self.hp_enemy_label.text = self.get_hp_bar(self.bf.ship_enemy)
						self.msg['dispose'].append(rocket.serialize())
						rocket.dispose()
				except TypeError:
					rocket.dispose()
					self.bf.rockets.remove(rocket)
			if shoots:
				self.msg['hp'] = self.bf.ship_enemy.health


class CompetitiveMode(Mode):
	def __init__(self, battlefield, socket):
		self.binds = []
		self.bf = battlefield
		self.last_score = 0
		self.score = 0
		self.enemy_score = 0
		self.socket = socket
		self.msg = defaultdict(list)
		self.last_pos = None
		self.last_shoot_time = time.time()
		self.RUN = True

	def initialize(self):
		self.bf.ship_enemy = ShipDrawCreator.createShip(
			Ship(self.bf.WIDTH / 2, self.bf.HEIGHT - 80, name="Enemy ship"),
			self.bf.canvas, _type=''
		)
		bind = self.bf.canvas.bind("<Button-1>", self.on_l_click)
		self.binds.append(bind)
		self.bf.root.config(cursor='none')
		self.score_label = Label(self.bf.canvas, 100, 20, text='0', font=('Helvetica', 10), fill='#00ACE6')
		self.score_enemy_label = Label(self.bf.canvas, 100, 20, text='0', font=('Helvetica', 10), fill='red')

	def on_l_click(self, event):
		now = time.time()
		if now - self.last_shoot_time >= 0.2:
			self.last_shoot_time = now
			new_rocket = self.bf.ship.fire()
			self.bf.rockets.append(RocketDrawDecorator(new_rocket, self.bf.canvas))
			self.msg['create'].append(new_rocket.serialize())

	def update_score(self):
		self.score_label.text = str(self.score)
		self.score_enemy_label.text = str(self.enemy_score)
		if self.score != self.last_score:
			self.last_score = self.score
			self.msg['score'] = self.score

	async def show_result(self):
		if self.score > self.enemy_score:
			text = "Ты выиграл!"
		elif self.score < self.enemy_score:
			text = "Ты проиграл"
		else:
			text = "Ничья"
		kw = {'font': ('Helvetica', 16), 'fill': 'white'}
		Label(self.bf.canvas, self.bf.WIDTH / 2 , self.bf.HEIGHT / 2, text=text, **kw)
		await asyncio.sleep(0.5)
		Label(self.bf.canvas, self.bf.WIDTH / 2 , self.bf.HEIGHT / 2 + 100, text="Нажмите ESC для выхода", **kw)

	def run(self):
		self.socket.send(b"/co")
		tasks = (self.update(), self.get_ship_pos(), self.send_msg())
		self.tasks = [asyncio.ensure_future(task) for task in tasks]

	def close(self):
		[task.cancel() for task in self.tasks]
		[self.bf.canvas.unbind(x) for x in self.binds]
		self.bf.dispose_all()
		self.bf.root.config(cursor='arrow')

	async def get_ship_pos(self):
		while True:
			await asyncio.sleep(0.05)
			if self.last_pos != (self.bf.ship.x, self.bf.ship.y):
				self.last_pos = (self.bf.ship.x, self.bf.ship.y)
				self.msg['ship'] = 0

	def update_ship_coords(self):
		x = self.bf.root.winfo_pointerx() - self.bf.root.winfo_rootx()
		y = self.bf.root.winfo_pointery() - self.bf.root.winfo_rooty()

		if x > 20 and x < self.bf.WIDTH - 20:
			self.bf.ship.x = x
			self.score_label.x = x
		elif x < 20:
			self.bf.ship.x = 20
			self.score_label.x = 20
		else:
			self.bf.ship.x = self.bf.WIDTH - 20
			self.score_label.x = self.bf.HEIGHT - 20

		if y >= self.bf.HEIGHT / 2 + 20 and y < self.bf.HEIGHT:
			self.bf.ship.y = y
			self.score_label.y = y + 80

	async def send_msg(self):
		while True:
			await asyncio.sleep(0.005)
			if self.msg:
				self.msg['ship'] = self.bf.ship.serialize()
				print("POST C[{}]".format(datetime.datetime.now().time()), self.msg)
				# self.socket.send(json.dumps(self.msg).encode())
				try:
					await loop.sock_sendall(self.socket, json.dumps(self.msg).encode())
				except ConnectionAbortedError:
					break
				self.msg = defaultdict(list)

	def handle_msg(self, msg):
		try:
			if msg == '/end':
				self.RUN = False
				asyncio.ensure_future(self.show_result())
				return 0

			msg = json.loads(msg)
			print("GET C[{}]".format(datetime.datetime.now().time()), msg)

			if 'create' in msg:
				for item in msg['create']:
					coords = item['coords']
					_id = item['id']

					if item['type'] == 'Asteroid':
						asteroid = Asteroid(coords[0], coords[1])
						asteroid.id = _id
						self.bf.asteroids.append(AsteroidDrawDecorator(asteroid, self.bf.canvas))

					if item['type'] == 'Rocket':
						rocket = Rocket(
							coords[0], coords[1],
							owner=self.bf.ship_enemy
						)
						rocket.id = _id
						self.bf.enemy_rockets.append(
							RocketDrawDecorator(rocket, self.bf.canvas, Resources.rocket_img)
						)

			if 'dispose' in msg:
				print('dispose')
				for item in msg['dispose']:
					[x.dispose() for x in self.bf.enemy_rockets if x.get_revolving_obj().id == item['id']]
				self.bf.remove_not_exists()

			if 'dispose' in msg:
				for item in msg['dispose']:
					asteroid = self.bf.asteroids.get_by_id(item['id'])
					if asteroid is None:
						[x.dispose() for x in self.bf.enemy_rockets if x.id == item['id']]
					else:
						asyncio.ensure_future(asteroid.destroy())
				self.bf.remove_not_exists()

			if 'score' in msg:
				self.enemy_score = msg['score']
				self.score_enemy_label.text = str(self.enemy_score)

			if 'ship' in msg:
				print("ENEMY: ", msg['ship']['coords'])
				self.bf.ship_enemy.x = msg['ship']['coords'][0]
				self.bf.ship_enemy.y = msg['ship']['coords'][1]
				self.score_enemy_label.x = msg['ship']['coords'][0]
				self.score_enemy_label.y = msg['ship']['coords'][1] + 80
		except json.decoder.JSONDecodeError:
			pass

	async def update(self):
		while self.RUN:
			await asyncio.sleep(0.0000005)
			current_time = datetime.datetime.now().time()

			self.update_ship_coords()

			self.bf.ship.redraw()
			self.bf.ship_enemy.redraw()
			self.score_label.redraw()
			self.score_enemy_label.redraw()

			for obj in chain(self.bf.rockets, self.bf.enemy_rockets, self.bf.asteroids):
				obj.fly()
				if obj.y < 0 or obj.y > self.bf.HEIGHT:
					obj.dispose()
					self.msg['dispose'].append(obj.serialize())

			self.bf.remove_not_exists()

			self.bf.root.title(string="CLIENT: " + str(current_time) + " Rockets: %d Ast.: %d" % (len(self.bf.rockets), len(self.bf.asteroids)))

			for rocket in self.bf.rockets:
				for asteroid in self.bf.asteroids:
					try:
						if point_in_bbox(rocket.x, rocket.y, asteroid.get_boundbox()):
							self.score += 1
							asteroid.killer = rocket.owner
							asyncio.ensure_future(asteroid.destroy())
							self.msg['dispose'].append(asteroid.serialize())
							self.msg['dispose'].append(rocket.serialize())
							rocket.dispose()
					except TypeError:
						self.msg['dispose'].append(asteroid.serialize())
						self.msg['dispose'].append(rocket.serialize())
						asteroid.dispose()
						self.bf.asteroids.remove(asteroid)

			self.update_score()


class Form:
	def __init__(self, root):
		self.socket = socket.socket()
		self.font = font.Font(family='Arial', size=20)
		self.root = root
		self.root.bind('<Escape>', lambda x: self.quit_from_mode())
		self.mods = {"sm": SingleMode, "dm": DuelMode, "cp": CompetitiveMode}
		self.menu = tk.Frame(root, bg='#00ACE6', bd=5)
		self.mode = None
		props = {
			"master": self.menu,
			"bg": "#00435A",
			"activebackground": "#00435A",
			"borderwidth": 0,
			"font": self.font,
			"fg": "#00ACE6"
		}

		self.btnSM = tk.Button(**props, text="Одиночная игра", command=lambda: self.run_mode("sm"))

		try:
			self.connect_to_server()
			self.btnDM = tk.Button(**props, text="Дуэль", command=lambda: self.run_mode("dm"))
			# self.btnCM = tk.Button(**props, text="Соревновательный", command=lambda: self.run_mode("cp"))
			self.btnDM.place(relwidth=0.75, relheight=0.1, relx=0.125, rely=0.41)
			# self.btnCM.place(relwidth=0.75, relheight=0.1, relx=0.125, rely=0.53)
		except socket.error:
			msgBox.showwarning("Не удалось подключиться к серверу!", "Вам доступна только одиночная игра")
			self.socket = None

		self.menu.place(relwidth=1, relheight=1)
		self.btnSM.place(relwidth=0.75, relheight=0.1, relx=0.125, rely=0.29)

	def connect_to_server(self, sock_pair=('localhost', 5678)):
		self.socket.connect(sock_pair)
		self.socket.setblocking(False)
		self.socket.send(b'/hello')
		asyncio.ensure_future(self.get_msg())

	def run_mode(self, mode):
		self.menu.place_forget()
		self.mode = self.mods[mode](BattleField(self.root), self.socket)
		self.mode.initialize()
		self.mode.run()

	async def get_msg(self):
		while True:
			msg = await loop.sock_recv(self.socket, 1024)
			msg = msg.decode()
			self.handle_msg(msg)

	def handle_msg(self, msg):
		print("GET C[{}]".format(datetime.datetime.now().time()), msg)
		if msg == '/close' and self.mode is not None:
			self.quit_from_mode()
			msgBox.showinfo("Сообщение", "Противник покинул состязание")

		if self.mode is not None:
			self.mode.handle_msg(msg)

	def quit_from_mode(self):
		print("ESC", self.mode)
		if self.mode is not None:
			if self.socket is not None:
				self.socket.send(b'/close')
			self.mode.close()
			self.mode = None
			self.menu.place(relwidth=1, relheight=1)


async def run(root):
	while True:
		root.update()
		await asyncio.sleep(0.000005)


def onclose(root, loop):
	for task in asyncio.Task.all_tasks():
		task.cancel()
	asyncio.ensure_future(exit(loop))
	root.destroy()


async def exit(loop):
	loop.stop()



root = Resources.root
# form = AuthForm(root)

root.title(string="COSMO")

root.geometry(sys.argv[1] if len(sys.argv) > 1 else '+850+0')

loop = asyncio.get_event_loop()
asyncio.ensure_future(run(root))
# asyncio.ensure_future(form.update_field())
# asyncio.ensure_future(form.get_msg())
# asyncio.ensure_future(form.send_msg())
# asyncio.ensure_future(form.get_ship_pos())
form = Form(root)
root.protocol("WM_DELETE_WINDOW", lambda: onclose(root, loop))
root.minsize(width=500, height=680)
try:
	loop.run_forever()
finally:
	loop.close()
