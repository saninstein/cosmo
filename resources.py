import tkinter as tk
import os


PATH = os.getcwd()
SPRITE_PATH = os.path.join(PATH, 'res', 'sprites/')


class Resources:
	def __new__(cls):
		raise TypeError

	root = tk.Tk()
	rocket_img = tk.PhotoImage(file=SPRITE_PATH + "rocket.png")
	reversed_rocket_img = tk.PhotoImage(file=SPRITE_PATH + "rocket_rotated.png")
	ship_img = tk.PhotoImage(file=SPRITE_PATH + "cs.png").subsample(3, 3)
	asteroid_img = tk.PhotoImage(
		file=SPRITE_PATH + "asteroid.png").subsample(3, 3)
	asteroid_smoke_img = tk.PhotoImage(
		file=SPRITE_PATH + "smoke.png").subsample(2, 2)
	space_img = tk.PhotoImage(file=SPRITE_PATH + "space.png").zoom(1, 2)
	bonus_img = tk.PhotoImage(file=SPRITE_PATH + "bonus.png").subsample(5, 5)
	ship_enemy_img = tk.PhotoImage(file=SPRITE_PATH + "cs_enemy.png").subsample(2, 2)
	ship_reversed_enemy_img = tk.PhotoImage(file=SPRITE_PATH + "cs_enemy_rotated.png").subsample(2, 2)