#!/usr/bin/env python

import json
import sys


class TaskSetJsonKeys(object):
    # Task set
    KEY_TASKSET = "taskset"

    # Task
    KEY_TASK_ID = "task_id"
    KEY_TASK_PERIOD = "period"
    KEY_TASK_WCET = "wcet"
    KEY_TASK_DEADLINE = "deadline"
    KEY_TASK_OFFSET = "offset"
    KEY_TASK_SECTIONS = "sections"

    # Schedule
    KEY_SCHEDULE_START = "startTime"
    KEY_SCHEDULE_END = "endTime"

    # Release times
    KEY_release_timeS = "release_times"
    KEY_release_timeS_JOBRELEASE = "timeInstant"
    KEY_release_timeS_TASKID = "task_id"


class TaskSetIterator:
    def __init__(self, _taskset):
        self.taskset = _taskset
        self.index = 0
        self.keys = iter(_taskset.tasks)

    def __next__(self):
        key = next(self.keys)
        return self.taskset.tasks[key]


class TaskSet(object):
    def __init__(self, _data):
        self.parse_data_to_tasks(_data)
        self.build_job_releases(_data)
        self.jobs = None
        self.tasks = None

    def parse_data_to_tasks(self, _data):
        _taskset = {}

        for taskData in _data[TaskSetJsonKeys.KEY_TASKSET]:
            task = Task(taskData)

            if task.id in _taskset:
                print("Error: duplicate task ID: {0}".format(task.id))
                return

            if task.period < 0 and task.relativeDeadline < 0:
                print("Error: aperiodic task must have positive relative deadline")
                return

            _taskset[task.id] = task

        self.tasks = _taskset

    def build_job_releases(self, _data):
        jobs = []

        if TaskSetJsonKeys.KEY_release_timeS in _data:  # necessary for sporadic releases
            for jobRelease in _data[TaskSetJsonKeys.KEY_release_timeS]:
                release_time = float(jobRelease[TaskSetJsonKeys.KEY_release_timeS_JOBRELEASE])
                task_id = int(jobRelease[TaskSetJsonKeys.KEY_release_timeS_TASKID])

                job = self.get_task_by_id(task_id).spawn_job(release_time)
                jobs.append(job)
        else:
            schedule_start_time = float(_data[TaskSetJsonKeys.KEY_SCHEDULE_START])
            schedule_end_time = float(_data[TaskSetJsonKeys.KEY_SCHEDULE_END])
            for task in self:
                t = max(task.offset, schedule_start_time)
                while t < schedule_end_time:
                    job = task.spawn_job(t)
                    if job is not None:
                        jobs.append(job)

                    if task.period >= 0:
                        t += task.period  # periodic
                    else:
                        t = schedule_end_time  # aperiodic

        self.jobs = jobs

    def __contains__(self, elt):
        return elt in self.tasks

    def __iter__(self):
        return TaskSetIterator(self)

    def __len__(self):
        return len(self.tasks)

    def get_task_by_id(self, task_id):
        return self.tasks[task_id]

    def print_tasks(self):
        print("\nTask Set:")
        for task in self:
            print(task)

    def print_jobs(self):
        print("\nJobs:")
        for task in self:
            for job in task.get_jobs():
                print(job)


class Task(object):
    def __init__(self, task_dict):
        self.id = int(task_dict[TaskSetJsonKeys.KEY_TASK_ID])
        self.period = float(task_dict[TaskSetJsonKeys.KEY_TASK_PERIOD])
        self.wcet = float(task_dict[TaskSetJsonKeys.KEY_TASK_WCET])
        self.relativeDeadline = float(
            task_dict.get(TaskSetJsonKeys.KEY_TASK_DEADLINE, task_dict[TaskSetJsonKeys.KEY_TASK_PERIOD]))
        self.offset = float(task_dict.get(TaskSetJsonKeys.KEY_TASK_OFFSET, 0.0))
        self.sections = task_dict[TaskSetJsonKeys.KEY_TASK_SECTIONS]

        self.last_job_id = 0
        self.last_released_time = 0.0

        self.jobs = []

    def get_all_resources(self):
        # CHECK
        return list(set([sec[0] for sec in self.sections]))

    def spawn_job(self, release_time):
        if self.last_released_time > 0 and release_time < self.last_released_time:
            print("INVALID: release time of job is not monotonic")
            return None

        if self.last_released_time > 0 and release_time < self.last_released_time + self.period:
            print("INVALID: release times are not separated by period")
            return None

        self.last_job_id += 1
        self.last_released_time = release_time

        job = Job(self, self.last_job_id, release_time)

        self.jobs.append(job)
        return job

    def get_jobs(self):
        return self.jobs

    def get_job_by_id(self, job_id):
        if job_id > self.last_job_id:
            return None

        job = self.jobs[job_id - 1]
        if job.id == job_id:
            return job

        for job in self.jobs:
            if job.id == job_id:
                return job

        return None

    def get_utilization(self):
        # CHECK
        return self.wcet / self.period

    def __str__(self):
        return "\n  task {0}:\n    Φ{0} = {1}\n    T{0} = {2}\n    C{0} = {3}\n    D{0} = {4}\n    ∆{0} = {5}".format(
            self.id, self.offset, self.period, self.wcet,
            self.relativeDeadline, self.sections)


class Job(object):
    def __init__(self, task, job_id, release_time):
        # CHECK
        self.task = task
        self.id = job_id
        self.release_time = release_time
        self.holding_resources = []
        self.waiting_resources = []
        self.is_executing = False
        self.deadline = release_time + task.relativeDeadline

    def get_resource_held(self):
        """the resources that it's currently holding"""
        # CHECK
        return self.holding_resources

    def get_resource_waiting(self):
        """a resource that is being waited on, but not currently executing"""
        # CHECK
        return self.waiting_resources

    def get_remaining_section_time(self):
        # TODO
        pass

    def execute(self, time):
        # TODO
        self.is_executing = True

    def execute_to_completion(self):
        # TODO
        self.is_executing = True

    def is_completed(self):
        # TODO
        pass

    def __str__(self):
        return "  [{0}:{1}] released at {2} with deadline {3}".format(
            self.task.id, 
            self.id, 
            self.release_time, 
            self.deadline
        )


current_time = 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "taskset.json"

    with open(file_path) as json_data:
        data = json.load(json_data)

    taskset = TaskSet(data)

    taskset.print_tasks()
    taskset.print_jobs()
