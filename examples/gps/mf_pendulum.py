#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Filename: mb_pendulum.py
# @Date: 2019-06-16-18-38
# @Author: Hany Abdulsamad
# @Contact: hany@robot-learning.de


import gym
from trajopt.gps import MFGPS


# pendulum env
env = gym.make('Pendulum-TO-v0')
env._max_episode_steps = 150

alg = MFGPS(env, nb_steps=150,
            kl_bound=50.,
            init_ctl_sigma=1.0)

# run gps
for _ in range(5):
    alg.run(nb_episodes=10)

# plot dists
alg.plot()

# execute and plot
nb_episodes = 25
data = alg.sample(nb_episodes, stoch=False)

import matplotlib.pyplot as plt

plt.figure()

plt.subplot(3, 1, 1)
plt.plot(data['x'][0, ...])

plt.subplot(3, 1, 2)
plt.plot(data['x'][1, ...])

plt.subplot(3, 1, 3)
plt.plot(data['u'][0, ...])
plt.show()
