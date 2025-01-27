import autograd.numpy as np
from autograd import jacobian

from trajopt.envs.quanser.common import VelocityFilter
from trajopt.envs.quanser.qube.base import QubeBase, QubeDynamics


class Qube(QubeBase):
    def __init__(self, fs, fs_ctrl):
        super(Qube, self).__init__(fs, fs_ctrl)
        self.dyn = QubeDynamics()
        self._sim_state = None
        self._vis = {'vp': None, 'arm': None, 'pole': None, 'curve': None}

    def _set_gui(self):
        scene_range = 0.2
        arm_radius = 0.003
        arm_length = 0.085
        pole_radius = 0.0045
        pole_length = 0.129
        # http://www.glowscript.org/docs/VPythonDocs/canvas.html
        self._vis['vp'].scene.width = 400
        self._vis['vp'].scene.height = 300
        self._vis['vp'].scene.background = self._vis['vp'].color.gray(0.95)
        self._vis['vp'].scene.lights = []
        self._vis['vp'].distant_light(
            direction=self._vis['vp'].vector(0.2, 0.2, 0.5),
            color=self._vis['vp'].color.white)
        self._vis['vp'].scene.up = self._vis['vp'].vector(0, 0, 1)
        self._vis['vp'].scene.range = scene_range
        self._vis['vp'].scene.center = self._vis['vp'].vector(0.04, 0, 0)
        self._vis['vp'].scene.forward = self._vis['vp'].vector(-2, 1.2, -1)
        self._vis['vp'].box(pos=self._vis['vp'].vector(0, 0, -0.07),
                            length=0.09, width=0.1, height=0.09,
                            color=self._vis['vp'].color.gray(0.5))
        self._vis['vp'].cylinder(
            axis=self._vis['vp'].vector(0, 0, -1), radius=0.005,
            length=0.03, color=self._vis['vp'].color.gray(0.5))
        # Arm
        arm = self._vis['vp'].cylinder()
        arm.radius = arm_radius
        arm.length = arm_length
        arm.color = self._vis['vp'].color.blue
        # Pole
        pole = self._vis['vp'].cylinder()
        pole.radius = pole_radius
        pole.length = pole_length
        pole.color = self._vis['vp'].color.red
        # Curve
        curve = self._vis['vp'].curve(color=self._vis['vp'].color.white,
                                      radius=0.0005, retain=2000)
        return arm, pole, curve

    def _calibrate(self):
        self._vel_filt = VelocityFilter(x_len=self.sensor_space.shape[0],
                                        x_init=np.array([0., np.pi]),
                                        dt=self.timing.dt)
        self._sim_state = np.array([0., np.pi + 0.01 * self._np_random.randn(), 0., 0.])
        self._state = self._zero_sim_step()

    def _sim_step(self, u):
        # Add a bit of noise to action for robustness
        u_noisy = u + 1e-6 * np.float32(
            self._np_random.randn(self.action_space.shape[0]))

        thdd, aldd = self.dyn(self._sim_state, u_noisy)

        # Update internal simulation state
        self._sim_state[3] += self.timing.dt * aldd
        self._sim_state[2] += self.timing.dt * thdd
        self._sim_state[1] += self.timing.dt * self._sim_state[3]
        self._sim_state[0] += self.timing.dt * self._sim_state[2]

        # Pretend to only observe position and obtain velocity by filtering
        pos = self._sim_state[:2]
        # vel = self._sim_state[2:]
        vel = self._vel_filt(pos)
        return np.concatenate([pos, vel])

    def reset(self):
        self._calibrate()
        if self._vis['curve'] is not None:
            self._vis['curve'].clear()
        return self.step(np.array([0.0]))[0]

    def render(self, mode='human'):
        if self._vis['vp'] is None:
            import importlib
            self._vis['vp'] = importlib.import_module('vpython')
            self._vis['arm'],\
            self._vis['pole'],\
            self._vis['curve'] = self._set_gui()
        th, al, _, _ = self._state
        arm_pos = (self.dyn.Lr * np.cos(th), self.dyn.Lr * np.sin(th), 0.0)
        pole_ax = (-self.dyn.Lp * np.sin(al) * np.sin(th),
                   self.dyn.Lp * np.sin(al) * np.cos(th),
                   self.dyn.Lp * np.cos(al))
        self._vis['arm'].axis = self._vis['vp'].vector(*arm_pos)
        self._vis['pole'].pos = self._vis['vp'].vector(*arm_pos)
        self._vis['pole'].axis = self._vis['vp'].vector(*pole_ax)
        self._vis['curve'].append(
            self._vis['pole'].pos + self._vis['pole'].axis)
        self._vis['vp'].rate(self.timing.render_rate)


class QubeTO(QubeBase):

    def __init__(self, fs, fs_ctrl):
        super(QubeTO, self).__init__(fs, fs_ctrl)
        self.dyn = QubeDynamics()

        self._x0 = np.array([0., np.pi, 0., 0.])
        self._sigma_0 = 1.e-4 * np.eye(4)

        self._sigma = 1.e-4 * np.eye(4)

        self._g = np.array([0., 2. * np.pi, 0., 0.])
        self._gw = np.array([1.e-1, 1.e1, 1.e-1, 1.e-1])

        self._uw = np.array([1.e-3])

    def init(self):
        return self._x0, self._sigma_0

    def dynamics(self, x, u):
        def f(x, u):
            _acc = self.dyn(x, u)
            return np.hstack((x[2], x[3], _acc))

        k1 = f(x, u)
        k2 = f(x + 0.5 * self.timing.dt * k1, u)
        k3 = f(x + 0.5 * self.timing.dt * k2, u)
        k4 = f(x + self.timing.dt * k3, u)

        xn = x + self.timing.dt / 6. * (k1 + 2. * k2 + 2. * k3 + k4)
        return xn

    def features(self, x):
        return x

    def features_jacobian(self, x):
        _J = jacobian(self.features, 0)
        _j = self.features(x) - _J(x) @ x
        return _J, _j

    def noise(self, x=None, u=None):
        return self._sigma

    # xref is a hack to avoid autograd diffing through the jacobian
    def cost(self, x, u, a, xref):
        if a:
            _J, _j = self.features_jacobian(xref)
            _x = _J(xref) @ x + _j
            return (_x - self._g).T @ np.diag(self._gw) @ (_x - self._g) + u.T @ np.diag(self._uw) @ u
        else:
            return u.T @ np.diag(self._uw) @ u
