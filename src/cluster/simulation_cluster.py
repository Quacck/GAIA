from typing import Dict
from carbon import CarbonModel
from scheduling.carbon_waiting_policy import compute_carbon_consumption
from task import Task
from .base_cluster import BaseCluster


class SimulationCluster(BaseCluster):
    def __init__(
        self, reserved_instances: int, carbon_model: CarbonModel, experiment_name: str, allow_spot: True
    ) -> None:
        super().__init__(
            reserved_instances=reserved_instances,
            carbon_model=carbon_model,
            experiment_name=experiment_name,
            allow_spot=allow_spot,
        )
        self.release_instance: Dict[int, int] = {}

    def submit(self, current_time: int, task: Task) -> None:
        try:
            c_model = self.carbon_model.subtrace(
                current_time, current_time + max(task.task_length, task.expected_time)
            )

            # we calculate the carbon consimption again, because 
            # tasks may be submitted via carbon_aware = false
            schedule = compute_carbon_consumption(task, 0, c_model)
            finish_time = schedule.actual_finish_time(current_time)
            # if self.allow_spot and task.task_length_class == "0-2":
            #     self.total_carbon_cost += schedule.carbon_cost
            #     self.total_dollar_cost += task.CPUs * task.task_length * self.spot_cost
            #     self.log_task(
            #         current_time,
            #         task,
            #         task.CPUs * task.task_length * self.spot_cost,
            #         schedule.carbon_cost,
            #     )

            if self.available_reserved_instances >= task.CPUs:
                if finish_time not in self.release_instance:
                    self.release_instance[finish_time] = 0
                self.release_instance[finish_time] += task.CPUs
                on_demand = 0
                self.available_reserved_instances -= task.CPUs
            else:
                on_demand = task.CPUs

            self.total_carbon_cost += schedule.carbon_cost
            self.total_dollar_cost += (
                on_demand * task.task_length * self.on_demand_cost
            )

            self.log_task(
                current_time,
                task,
                on_demand * task.task_length * self.on_demand_cost,
                schedule.carbon_cost,
            )
        except:
            print("RealClusterCost: execute error")
            raise

    def refresh_data(self, current_time: int) -> None:
        # release used resource
        self.release_reserved(current_time)

    def release_reserved(self, current_time: int) -> None:
        if current_time in self.release_instance:
            self.available_reserved_instances += self.release_instance[current_time]
            del self.release_instance[current_time]
        assert (
            self.available_reserved_instances <= self.total_reserved_instances
        ), "Available Reserved greater thant Total"
        assert self.available_reserved_instances >= 0, "Greater than zero"

    def done(self) -> bool:
        return True

    def sleep(self) -> None:
        return

    def save_results(
        self,
        cluster_type: str,
        scheduling_policy: str,
        carbon_policy: str,
        carbon_trace: str,
        task_trace: str,
        waiting_times: str,
        set_filename: str | None,
    ) -> None:
        super().save_results(
            cluster_type,
            scheduling_policy,
            carbon_policy,
            carbon_trace,
            task_trace,
            waiting_times,
            set_filename,
        )
