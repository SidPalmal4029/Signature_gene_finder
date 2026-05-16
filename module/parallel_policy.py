import multiprocessing
import math


class ParallelismPolicy:

    def __init__(self, total_cpus=None):
        self.total_cpus = total_cpus or multiprocessing.cpu_count()

    # -----------------------------
    # GLOBAL THREAD STRATEGY
    # -----------------------------
    def base_threads(self):

        n = self.total_cpus

        if n <= 4:
            return max(1, n // 2)
        elif n <= 8:
            return n
        else:
            return int(n * 0.95)

    # -----------------------------
    # DFAST STRATEGY
    # -----------------------------
    def dfast_policy(self, n_genomes):

        total = self.base_threads()

        # split CPUs across genomes
        if n_genomes == 1:
            return {"jobs": 1, "threads_per_job": total}

        # heuristic split
        jobs = min(n_genomes, max(1, total // 4))
        threads = max(1, total // jobs)

        return {
            "jobs": jobs,
            "threads_per_job": threads
        }

    # -----------------------------
    # ORTHOFINDER STRATEGY
    # -----------------------------
    def orthofinder_policy(self):

        total = self.base_threads()

        return {
            "threads": total
        }

    # -----------------------------
    # GENERIC SPLIT
    # -----------------------------
    def split(self, n_tasks):

        total = self.base_threads()

        jobs = min(n_tasks, total)
        threads = max(1, total // jobs)

        return jobs, threads
