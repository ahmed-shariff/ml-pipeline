import os
import sys
import subprocess
import configparser
import socket
import argparse
import logging

from mlpipeline.utils import (log,
                              log_special_tokens,
                              set_logger,
                              is_no_log,
                              ExperimentModeKeys,
                              ExperimentWrapper,
                              _PipelineConfig)
import mlpipeline._default_configurations as _default_config
# why not check for this
if sys.version_info < (3, 5):
    sys.stderr.write("ERROR: python version should be greater than or equal 3.5\n")
    sys.exit(1)


# Use_history is a lil funkcy for now, so leaving it here. If using should move it to _PipelineConfig
USE_HISTORY = False
CONFIG = _PipelineConfig()


def _mlpipeline_main_loop(experiments=None):
    completed_experiments = []
    if experiments is not None:
        assert any([isinstance(e, ExperimentWrapper) for e in experiments])
    current_experiment = _get_experiment(experiments=experiments)
    while current_experiment is not None:
        # exec subprocess
        current_experiment_name = current_experiment.file_path
        output = _execute_subprocess(current_experiment_name,
                                     current_experiment.whitelist_versions,
                                     current_experiment.blacklist_versions)
        if output == 3 or output == 1:
            completed_experiments.append(current_experiment_name)
        if is_no_log():
            break
        current_experiment = _get_experiment(experiments=experiments,
                                             completed_experiments=completed_experiments)


def _execute_subprocess(experiment_name, whitelist_versions=None, blacklist_versions=None):
    args = ["mlpipeline",
            "--experiments", experiment_name,
            "--experiments-dir", CONFIG.experiments_dir,
            "--mlflow_tracking_uri", CONFIG.mlflow_tracking_uri]
    if CONFIG.no_log:
        args.append("--no-log")
    args.append("single")
    if CONFIG.experiment_mode == ExperimentModeKeys.RUN:
        args.append("run")
    elif CONFIG.experiment_mode == ExperimentModeKeys.EXPORT:
        args.append("export")
    else:
        args.append("test")

    if whitelist_versions is not None:
        args.append("--whitelist-versions")
        for version in whitelist_versions:
            args.append(version)
    if blacklist_versions is not None:
        args.append("--blacklist-versions")
        for version in blacklist_versions:
            args.append(version)
    # if USE_HISTORY:
    #     args.append("-u")
    return subprocess.call(args, universal_newlines=True)


def _get_experiment(experiments=None, completed_experiments=[]):
    if CONFIG.cmd_mode:
        _config_update()
    if experiments is not None:
        for experiment in experiments:
            if experiment.file_path not in completed_experiments:
                return experiment
        return None
    for rdir, dirs, files in os.walk(CONFIG.experiments_dir):
        for f in files:
            if f.endswith(".py"):
                file_path = os.path.join(rdir, f)
                if completed_experiments is not None and file_path in completed_experiments:
                    continue
                # TODO: Should remove this check, prolly has no use!
                if CONFIG.use_blacklist and file_path in CONFIG.listed_experiments:
                    continue
                if not CONFIG.use_blacklist and file_path not in CONFIG.listed_experiments:
                    continue
                skip_experiment_for_now = False
                # Ensure the files loaded are in the order they are
                # specified in the config file
                for listed_experiment_file in CONFIG.listed_experiments:
                    if listed_experiment_file != file_path:
                        if listed_experiment_file not in completed_experiments:
                            skip_experiment_for_now = True
                            break
                    else:
                        break
                if skip_experiment_for_now:
                    continue
                return ExperimentWrapper(file_path)
    return None


def _config_update():
    log("Updating configuration")
    if CONFIG.experiment_mode == ExperimentModeKeys.TEST:
        config_from = "experiments_test.config"
    else:
        config_from = "experiments.config"
    config = configparser.ConfigParser(allow_no_value=True)
    config_file = config.read(config_from)

    if len(config_file) == 0:
        log("\033[1;031mWARNING:\033[0:031mNo 'experiments.config' file found\033[0m", log_to_file=True)
    else:
        try:
            config["MLP"]
        except KeyError:
            log("\033[1;031mWARNING:\033[0:031mNo MLP section in 'experiments.config' file\033[0m",
                log_to_file=True,
                level=logging.WARNING)
        CONFIG.use_blacklist = config.getboolean("MLP", "use_blacklist", fallback=CONFIG.use_blacklist)
        try:
            if CONFIG.use_blacklist:
                CONFIG.listed_experiments = config["BLACKLISTED_EXPERIMENTS"]
            else:
                CONFIG.listed_experiments = config["WHITELISTED_EXPERIMENTS"]
            listed_experiments = []
            for experiment in CONFIG.listed_experiments:
                listed_experiments.append(os.path.join(CONFIG.experiments_dir, experiment))

            for experiment in listed_experiments:
                if not os.path.exists(experiment):
                    listed_experiments.remove(experiment)
                    log("Script missing: {}".format(experiment), level=logging.WARNING)
            CONFIG.listed_experiments = listed_experiments
            log("\033[1;036m{0}\033[0;036m: {1}\033[0m".format(
                ["BLACKLISTED_EXPERIMENTS"
                 if CONFIG.use_blacklist else "WHITELISTED_EXPERIMENTS"][0].replace("_", " "),
                CONFIG.listed_experiments).lower(), log_to_file=True)
        except KeyError:
            log("\033[1;031mWARNING:\033[0:031mNo {0} section in 'cnn.config' file\033[0m".format(
                ["BLACKLISTED_EXPERIMENTS" if CONFIG.use_blacklist else "WHITELISTED_EXPERIMENTS"][0]),
                log_to_file=True,
                level=logging.ERROR)


def _init_pipeline(experiment_mode, experiments_dir=None, no_log=False, experiments_output_dir=None,
                   mlflow_tracking_uri=None, _cmd_mode=False):
    config = configparser.ConfigParser(allow_no_value=True)
    config_file = config.read("mlp.config")

    CONFIG.no_log = no_log
    CONFIG.experiment_mode = experiment_mode
    CONFIG.cmd_mode = _cmd_mode
    if experiments_dir is None:
        if len(config_file) == 0:
            print("\033[1;031mWARNING:\033[0:031mNo 'mlp.config' file found\033[0m")
        else:
            try:
                config["MLP"]
            except KeyError:
                print("\033[1;031mWARNING:\033[0:031mNo MLP section in 'mlp.config' file\033[0m")
            CONFIG.experiments_dir = config.get("MLP", "experiments_dir",
                                                fallback=_default_config.EXPERIMENTS_DIR)
    else:
        CONFIG.experiments_dir = experiments_dir

    if mlflow_tracking_uri is None:
        CONFIG.mlflow_tracking_uri = os.path.abspath(config.get("MLFLOW", "tracking_uri",
                                                                fallback=CONFIG.mlflow_tracking_uri))
    else:
        CONFIG.mlflow_tracking_uri = mlflow_tracking_uri

    hostName = socket.gethostname()
    EXPERIMENTS_DIR_OUTPUTS = experiments_output_dir or _default_config.OUTPUT_DIR.format(
        CONFIG.experiments_dir)
    CONFIG.experiments_outputs_dir = EXPERIMENTS_DIR_OUTPUTS
    if not os.path.exists(EXPERIMENTS_DIR_OUTPUTS):
        os.makedirs(EXPERIMENTS_DIR_OUTPUTS)
    log_file = os.path.join(EXPERIMENTS_DIR_OUTPUTS, "log-{0}".format(hostName))
    try:
        open(log_file, "a").close()
    except FileNotFoundError:
        if os.path.isdir(EXPERIMENTS_DIR_OUTPUTS):
            os.makedirs(EXPERIMENTS_DIR_OUTPUTS)
            open(log_file, "a").close()
        else:
            raise

    CONFIG.logger = set_logger(experiment_mode=CONFIG.experiment_mode,
                               no_log=CONFIG.no_log,
                               log_file=log_file)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Machine Learning Pipeline\n"
                                     "(DEPRECATED) use `mlpipeline`")
    parser.add_argument('-r', '--run',
                        help='Will set the pipeline to execute the pipline fully,'
                        ' if not set will be executed in test mode',
                        action='store_true')
    parser.add_argument('-u', '--use-history',
                        help='If set will use the history log to determine '
                        'if a experiment script has been executed.',
                        action='store_true')
    parser.add_argument('-n', '--no_log',
                        help='If set non of the logs will be appended to the log files.',
                        action='store_true')
    parser.add_argument('-e', '--export',
                        help='If set, will run the experiment in export mode instead of training/eval loop.',
                        action='store_true')
    argv = parser.parse_args()
    if argv.run and argv.export:
        print("ERROR: Cannot have both 'run' and 'export'")
        return
    if argv.run:
        experiment_mode = ExperimentModeKeys.RUN
    elif argv.export:
        experiment_mode = ExperimentModeKeys.EXPORT
    else:
        experiment_mode = ExperimentModeKeys.TEST

    # if argv.use_history:#any("h" in s for s in unused_argv):
    #     USE_HISTORY = True
    # else:
    #     USE_HISTORY = False

    _init_pipeline(experiment_mode, no_log=argv.no_log, _cmd_mode=True)
    log_special_tokens.log_session_started()
    _mlpipeline_main_loop()
    log_special_tokens.log_session_ended()


if __name__ == "__main__":
    main()
