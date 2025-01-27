#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Filename: doublecartpole.py
# @Date: 2019-06-16-18-38
# @Author: Hany Abdulsamad
# @Contact: hany@robot-learning.de


import gym
from trajopt.ilqr import iLQR

# double cartpole env
env = gym.make('DoubleCartpole-TO-v0')
env._max_episode_steps = 200

alg = iLQR(env, nb_steps=200,
           activation=range(150, 200))

# run iLQR
trace = alg.run()

# plot forward pass
alg.plot()

# plot objective
import matplotlib.pyplot as plt

plt.figure()
plt.plot(trace)
plt.show()

