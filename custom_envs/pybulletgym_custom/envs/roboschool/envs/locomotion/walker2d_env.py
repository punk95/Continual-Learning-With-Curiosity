from custom_envs.pybulletgym_custom.envs.roboschool.envs.locomotion.walker_base_env import WalkerBaseBulletEnv
from custom_envs.pybulletgym_custom.envs.roboschool.robots.locomotors import Walker2D


class Walker2DBulletEnv(WalkerBaseBulletEnv):
    def __init__(self, power=0.40, leg_length = 0.5, thigh_length= 0.45, foot_length = 0.20, leg_size = 0.04,
                 thigh_size=0.05,  index=0):
        self.power = power
        self.l_length = leg_length
        self.t_length = thigh_length
        self.f_length = foot_length

        self.l_size = leg_size
        self.t_size = thigh_size

        self.robot = Walker2D(power=power, leg_length=self.l_length, thigh_length=self.t_length,
                            foot_length=self.f_length, leg_size=leg_size, thigh_size=thigh_size, index=index)
        WalkerBaseBulletEnv.__init__(self, self.robot)

