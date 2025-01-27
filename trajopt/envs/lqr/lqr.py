import gym
from gym import spaces
from gym.utils import seeding

import autograd.numpy as np


class LQR(gym.Env):

    def __init__(self):
        self.nb_xdim = 2
        self.nb_udim = 1

        self._dt = 0.1
        self._g = np.array([10., 10.])

        # stochastic dynamics
        self._A = np.array([[1.1, 0.], [1.0, 1.0]])
        self._B = np.array([[1.], [0.]])
        self._c = - self._A @ self._g  # stable at goal

        self._sigma = 1.e-8 * np.eye(2)

        self._gw = np.array([1.e1, 1.e1])
        self._uw = np.array([1.])

        self._xmax = np.array([np.inf, np.inf])
        self._umax = np.inf

        self.action_space = spaces.Box(low=-self._umax,
                                       high=self._umax, shape=(1,))

        self.observation_space = spaces.Box(low=-self._xmax,
                                            high=self._xmax)

        self.seed()
        self.reset()

    @property
    def xlim(self):
        return self._xmax

    @property
    def ulim(self):
        return self._umax

    @property
    def dt(self):
        return self._dt

    @property
    def goal(self):
        return self._g

    def init(self):
        # mu, sigma
        return np.array([5., 5.]), 1.e-4 * np.eye(2)

    def dynamics(self, x, u):
        u = np.clip(u, -self._umax, self._umax)

        def f(x, u):
            return self._A @ x + self._B @ u + self._c

        k1 = f(x, u)
        k2 = f(x + 0.5 * self.dt * k1, u)
        k3 = f(x + 0.5 * self.dt * k2, u)
        k4 = f(x + self.dt * k3, u)

        xn = x + self.dt / 6. * (k1 + 2. * k2 + 2. * k3 + k4)
        xn = np.clip(xn, -self._xmax, self._xmax)

        return xn

    def inverse_dynamics(self, x, u):
        u = np.clip(u, -self._umax, self._umax)

        def f(x, u):
            return self._A @ x + self._B @ u + self._c

        k1 = f(x, u)
        k2 = f(x - 0.5 * self.dt * k1, u)
        k3 = f(x - 0.5 * self.dt * k2, u)
        k4 = f(x - self.dt * k3, u)

        xn = x - self.dt / 6. * (k1 + 2. * k2 + 2. * k3 + k4)
        xn = np.clip(xn, -self._xmax, self._xmax)

        return xn

    def noise(self, x=None, u=None):
        u = np.clip(u, -self._umax, self._umax)
        x = np.clip(x, -self._xmax, self._xmax)
        return self._sigma

    def cost(self, x, u, a, xref=None):
        if a:
            return (x - self._g).T @ np.diag(self._gw) @ (x - self._g) + u.T @ np.diag(self._uw) @ u
        else:
            return u.T @ np.diag(self._uw) @ u

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, u):
        # state-action dependent noise
        _sigma = self.noise(self.state, u)
        # evolve deterministic dynamics
        self.state = self.dynamics(self.state, u)
        # add noise
        self.state = self.np_random.multivariate_normal(mean=self.state, cov=_sigma)
        return self.state, [], False, {}

    def reset(self):
        _mu_0, _sigma_0 = self.init()
        self.state = self.np_random.multivariate_normal(mean=_mu_0, cov=_sigma_0)
        return self.state
