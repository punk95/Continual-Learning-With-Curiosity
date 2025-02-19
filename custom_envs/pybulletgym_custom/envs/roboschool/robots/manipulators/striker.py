from custom_envs.pybulletgym_custom.envs.roboschool.robots.robot_bases import MJCFBasedRobot
import numpy as np


class Striker(MJCFBasedRobot):
    min_target_placement_radius = 0.1
    max_target_placement_radius = 0.8
    min_object_placement_radius = 0.1
    max_object_placement_radius = 0.8

    def __init__(self):
        MJCFBasedRobot.__init__(self, 'striker.xml', 'body0', action_dim=7, obs_dim=56)

    def robot_specific_reset(self, bullet_client):
        # parts
        self.fingertip = self.parts["tips_arm"]
        self.target = self.parts["coaster"] # TODO: goal does not show up, but coaster is great too
        self.object = self.parts["object"]

        # joints
        self.shoulder_pan_joint = self.jdict["r_shoulder_pan_joint"]
        self.shoulder_lift_joint = self.jdict["r_shoulder_lift_joint"]
        self.upper_arm_roll_joint = self.jdict["r_upper_arm_roll_joint"]
        self.elbow_flex_joint = self.jdict["r_elbow_flex_joint"]
        self.forearm_roll_joint = self.jdict["r_forearm_roll_joint"]
        self.wrist_flex_joint = self.jdict["r_wrist_flex_joint"]
        self.wrist_roll_joint = self.jdict["r_wrist_roll_joint"]

        self._min_strike_dist = np.inf
        self._striked = False
        self._strike_pos = None

        # reset position and speed of manipulator
        # TODO: Will this work or do we have to constrain this resetting in some way?
        self.shoulder_pan_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.shoulder_lift_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.upper_arm_roll_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.elbow_flex_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.forearm_roll_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.wrist_flex_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.wrist_roll_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)

        self.zero_offset = np.array([0.45, 0.55, 0])
        self.object_pos = np.concatenate([
            self.np_random.uniform(low=-1, high=1, size=1),
            self.np_random.uniform(low=-1, high=1, size=1),
            self.np_random.uniform(low=-1, high=1, size=1)
        ])

        # make length of vector between min and max_object_placement_radius
        self.object_pos = self.object_pos \
                          / np.linalg.norm(self.object_pos) \
                          * self.np_random.uniform(low=self.min_object_placement_radius,
                                                   high=self.max_object_placement_radius, size=1)

        # reset object position
        self.jdict["obj_slidex"].reset_current_position(self.object_pos[0] - self.zero_offset[0], 0)
        self.jdict["obj_slidey"].reset_current_position(self.object_pos[1] - self.zero_offset[1], 0)

        self.target_pos = np.concatenate([
            self.np_random.uniform(low=-1, high=1, size=1),
            self.np_random.uniform(low=-1, high=1, size=1),#self.np_random.uniform(low=-1, high=1, size=1),
            np.array([-0.2])
        ])

        # make length of vector between min and max_target_placement_radius
        # self.target_pos = self.target_pos \
        # 				  / np.linalg.norm(self.target_pos) \
        # 				  * self.np_random.uniform(low=self.min_target_placement_radius,
        # 										   high=self.max_target_placement_radius, size=1)

        self.jdict["goal_slidex"].reset_current_position(self.target_pos[0] - self.zero_offset[0], 0)
        self.jdict["goal_slidey"].reset_current_position(self.target_pos[1] - self.zero_offset[1], 0)
    #self.target.reset_pose(self.target_pos - self.zero_offset, np.array([0, 0, 0, 1]))

    def apply_action(self, a):
        assert (np.isfinite(a).all())
        self.shoulder_pan_joint.set_motor_torque(0.05 * float(np.clip(a[0], -1, +1)))
        self.shoulder_lift_joint.set_motor_torque(0.05 * float(np.clip(a[1], -1, +1)))
        self.upper_arm_roll_joint.set_motor_torque(0.05 * float(np.clip(a[2], -1, +1)))
        self.elbow_flex_joint.set_motor_torque(0.05 * float(np.clip(a[3], -1, +1)))
        self.forearm_roll_joint.set_motor_torque(0.05 * float(np.clip(a[4], -1, +1)))
        self.wrist_flex_joint.set_motor_torque(0.05 * float(np.clip(a[5], -1, +1)))
        self.wrist_roll_joint.set_motor_torque(0.05 * float(np.clip(a[6], -1, +1)))

    def calc_state(self):
        self.to_target_vec = self.target_pos - self.object_pos
        return np.concatenate([
            np.array([j.current_position() for j in self.ordered_joints]).flatten(),  # all positions
            np.array([j.current_relative_position() for j in self.ordered_joints]).flatten(),  # all speeds
            self.to_target_vec,
            self.fingertip.pose().xyz(),
            self.object.pose().xyz(),
            self.target.pose().xyz(),
        ])