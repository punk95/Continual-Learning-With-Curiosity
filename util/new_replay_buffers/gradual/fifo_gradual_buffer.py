import numpy as np
import heapq
import random
from itertools import count


class Transition_tuple():

    def __init__(self, state, action, action_mean, reward, curiosity, next_state, done_mask, t):
        #expects as list of items for each initalization variable
        self.state = np.array(state)
        self.action = np.array(action)
        self.action_mean = np.array(action_mean)
        self.reward = np.array(reward)
        self.curiosity = np.array(curiosity)
        self.next_state = np.array(next_state)
        self.done_mask = np.array(done_mask)
        self.t = np.array(t)

    def get_all_attributes(self):
        return [self.state, self.action,  self.action_mean, self.reward, self.curiosity, self.next_state, self.done_mask, self.t]


class FIFO_Replay_Memory_Gradual():

    def __init__(self, capacity=10000, avg_len_snr=60, repetition_threshold=30000,
                 snr_factor=3, ):
        self.capacity = capacity
        self.storage = [[]]
        self.residual_buffer = []
        self.tiebreaker = count()

        self.no_data = 0
        self.position = 0

        self.current_index = 0
        self.no_tasks = 1
        self.individual_buffer_capacity = capacity

        # task seperation parameters
        self.delta = 1e-10  # to avoid zero division

        self.avg_len_snr = avg_len_snr
        self.snr_factor = snr_factor
        self.last_spike_since = 0
        self.repetition_threshold = repetition_threshold

        self.curisoity_time_frame = [0 for i in range(avg_len_snr)]
        self.time = 0

        # debug stuff
        self.PUSH = []
        self.SNR = []
        self.MEAN = []
        self.MEASURE = []
        self.BOOL = []
        self.max = 0

        self.task_seperation_initiated = False


    def task_change(self):

        self.task_seperation_initiated = True

        l = []
        for  b in self.storage:
            l.append(len(b))
        l.append(len(self.residual_buffer))
        print(self.time, l)

        self.current_index += 1
        self.no_tasks += 1
        self.individual_buffer_capacity = self.capacity//self.no_tasks

        x = self.capacity//(self.no_tasks*(self.no_tasks-1))

        self.residual_buffer = []

        for (i, buff) in enumerate(self.storage):
            if len(buff) > self.individual_buffer_capacity:
                self.storage[i] = buff[x:]
                self.residual_buffer += buff[:x-1]


        self.storage.append([])
        self.position = 0

    def check_for_task_change(self, curiosity):

        self.time = next(self.tiebreaker)  # both tiebreaker and timing is solved

        cur = curiosity

        if self.time < self.avg_len_snr:
            self.curisoity_time_frame[self.time] = cur

        else:
            self.curisoity_time_frame.pop(0)
            self.curisoity_time_frame.append(cur)

            mean = np.mean(self.curisoity_time_frame).item()
            std = np.std(self.curisoity_time_frame).item()
            SNR = mean / (std + self.delta)

            # setting the idling threshold
            if SNR < self.snr_factor * mean:
                self.BOOL.append(1.0)

                if self.last_spike_since > self.repetition_threshold:
                    self.task_change()
                self.last_spike_since = 0
            else:
                self.BOOL.append(0.0)
                self.last_spike_since += 1

            self.SNR.append(SNR)
            self.MEAN.append(mean)


    def push(self, state, action, action_mean, reward, curiosity, next_state, done_mask, tiebreaker):
        self.check_for_task_change(curiosity=curiosity)

        if tiebreaker == None:
            tiebreaker = self.time

        data = (None, tiebreaker, (state, action, action_mean, reward, curiosity, next_state, done_mask))

        if len(self.storage[self.current_index]) < self.individual_buffer_capacity:
            self.storage[self.current_index].append(data)
            self.no_data += 1
            self.position = (self.position + 1) % self.individual_buffer_capacity

            if len(self.residual_buffer) != 0:
                self.residual_buffer.pop(0)

            return

        old_data = self.storage[self.current_index][self.position]
        self.storage[self.current_index][self.position] = data
        self.position = (self.position + 1) % self.individual_buffer_capacity

        if len(self.residual_buffer) != 0:
            self.residual_buffer.pop(0)

        # for MTR and Flow through FIFO buffer
        return old_data


    def get_total_buffer_data(self):
        S = []
        for buff in self.storage:
            S += buff

        S += self.residual_buffer
        return S

    def sample(self, batch_size):
        indices = self.get_sample_indices(batch_size)
        state, action, action_mean, reward, curiosity, next_state, done_mask = self.encode_sample(
            indices=indices)
        return Transition_tuple(state, action, action_mean, reward, curiosity, next_state, done_mask, None)


    def encode_sample(self, indices):
        state, action, action_mean, reward, curiosity, next_state, done_mask, t_array = [], [], [], [], [], [], [], []
        for (j,idxs) in enumerate(indices[:-1]):
            for i in idxs:
                if j == 0:
                    data = self.residual_buffer[i][2]
                else:
                    data = self.storage[j-1][i][2]

                s, a, a_m, r, c, n_s, d = data
                state.append(s)
                action.append(a)
                action_mean.append(a_m)
                reward.append(r)
                curiosity.append(c)
                next_state.append(n_s)
                done_mask.append(d)


        return state, action, action_mean, reward, curiosity, next_state, done_mask

    def get_sample_indices(self, batch_size):
        prop = self.get_proportion()
        batch_sizes = []
        temp = 0
        for i in range(len(self.storage)-1):
            temp += int(batch_size*prop[i])
            batch_sizes.append(int(batch_size*prop[i]))
        batch_sizes.append(batch_size-temp)

        indices = []
        for (i,buff) in enumerate(self.storage):
            if len(buff) < self.individual_buffer_capacity:
                indices.append(np.random.choice(len(buff), batch_sizes[i]))
            else:
                indices.append(np.random.choice(self.individual_buffer_capacity, batch_sizes[i]))

        #for residual buffer
        buff = self.residual_buffer
        if len(buff) != 0:
            indices.insert(0, np.random.choice(len(buff), batch_sizes[-1]))
        else:
            indices.insert(0, np.array([]))


        return indices



    def get_proportion(self):
        size = self.__len__()
        if size == 0:
            return [1.0]
        prop = []
        for buff in self.storage:
            prop.append(len(buff)/size)

        prop.append(len(self.residual_buffer)/size)

        return prop


    def __len__(self):
        l = 0
        for buff in self.storage:
            l += len(buff)

        l += len(self.residual_buffer)
        return l