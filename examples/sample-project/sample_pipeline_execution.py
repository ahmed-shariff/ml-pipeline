import subprocess
from mlpipeline import (mlpipeline_execute_exeperiment, mlpipeline_execute_pipeline)
from mlpipeline.utils import (ExperimentModeKeys, ExperimentWrapper)


def train_experiment_with_whitelist():
    print("*"*20, "EXPERIMENT WITH WHITELIST", "*"*20)
    subprocess.run(["rm", "-rf", "experiments/outputs"])
    mlpipeline_execute_exeperiment("experiments/sample_experiment.py",
                                   "experiments",
                                   ExperimentModeKeys.RUN,
                                   whitelist_versions=["version5"])


def train_experiment_with_blacklist():
    print("*"*20, "EXPERIMENT WITH BLACKLIST", "*"*20)
    subprocess.run(["rm", "-rf", "experiments/outputs"])
    mlpipeline_execute_exeperiment("experiments/sample_experiment.py",
                                   "experiments",
                                   ExperimentModeKeys.RUN,
                                   blacklist_versions=["version2", "version5"])


def train_pipeline_with_whitelist():
    print("*"*20, "PIPELINE WITH WHITELIST", "*"*20)
    subprocess.run(["rm", "-rf", "experiments/outputs"])
    mlpipeline_execute_pipeline([ExperimentWrapper("experiments/sample_experiment.py",
                                                   whitelist_versions=["version5"])],
                                "experiments",
                                ExperimentModeKeys.RUN)


def train_pipeline_with_blacklist():
    print("*"*20, "PIPELINE WITH BALCKLIST", "*"*20)
    subprocess.run(["rm", "-rf", "experiments/outputs"])
    mlpipeline_execute_pipeline([ExperimentWrapper("experiments/sample_experiment.py",
                                                   blacklist_versions=["version2", "version5"])],
                                "experiments",
                                ExperimentModeKeys.RUN)


if __name__ == "__main__":
    train_pipeline_with_blacklist()
    train_pipeline_with_whitelist()
    train_experiment_with_blacklist()
    train_experiment_with_whitelist()
