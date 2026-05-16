import multiprocessing
import math

class ParallelismPolicy:

    def __init__(self, total_cpus=None):
        self.total_cpus = total_cpus or multiprocessing.cpu_count()
    # GLOBAL THREAD STRATEGY
    def base_threads(self):
        n = self.total_cpus

        if n <= 4:
            return max(1, n // 2)
        elif n <= 8:
            return n
        else:
            return int(n * 0.95)
    # DFAST STRATEGY
    def dfast_policy(self, n_genomes):

        total_cpus = self.base_threads()

        T_TARGET = 12
        T_MIN = 4
        T_MAX = 16

        # small systems → sequential
        if total_cpus <= 16:
            return {
                "jobs": 1,
                "threads": [total_cpus]
            }

        # compute jobs
        jobs = max(1, total_cpus // T_TARGET)
        jobs = min(jobs, n_genomes)

        # distribute threads
        base = total_cpus // jobs
        remainder = total_cpus % jobs

        threads = []

        for i in range(jobs):
            t = base + (1 if i < remainder else 0)

            # clamp only if extreme
            if t > T_MAX:
                t = T_MAX
            if t < T_MIN:
                t = T_MIN

            threads.append(t)

        return {
            "jobs": jobs,
            "threads": threads
        }
    # ORTHOFINDER STRATEGY
    def orthofinder_policy(self):
        total = self.base_threads()
        return {
            "threads": total
        }
    # GENERIC SPLIT
    def split(self, n_tasks):
        total = self.base_threads()
        jobs = min(n_tasks, total)
        threads = max(1, total // jobs)
        return jobs, threads
