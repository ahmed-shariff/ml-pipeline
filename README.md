# ml-pipeline
I use this pipeline to simplify my life when working on ML projects. 

## Usage (tl;dr version)
1. Extend `mlp_helper.Model` and `mlp_helper.Dataloader` to suit your needs.
2. Define the versions using the interface provided by `mlp_utils.Versions`.
   - Version parameters that must be defined: 
	 - `mlp_utils.version_parameters.NAME`
	 - `mlp_utils.version_parameters.DATALOADER`
	 - `mlp_utils.version_parameters.BATCH_SIZE`
	 - `mlp_utils.version_parameters.EPOC_COUNT`
3. Place the script(s) containing above in a specified directory.
4. Add the directory to `mlp.config`
5. Add the name of the script to the `models.config`
6. (optional) Add the name of the script to the `models_test.config`
7. (optional) Run the model in test mode to ensure the safety of your sanity.

``` bash
python pipeline.py
```
8. Execute the pipeline

``` bash
python pipeline.py -r -u
```
9. Anything saved to the `model_dir` passed through the `mlp_utils.Model.train_model` and `mlp_utils.Model.evaluate_model` will be available to access. The output and logs can be found in `outputs/log-<hostname>` and `output-<hostname>` files relative to the directory in 3. above.

## Usage (Long version)
### Model scripts
The model script is a python script that contain a global variable `MODEL` which holds an `mlp_helper.Model` object. Ideally, one would extend the `mlp_helper.Model` class and implement it's methods to perform the intended tasks (Refer documentation in [mlp_helper](mlp_helper.py) for more details). 

Place model scripts in a separate folder. Note that this folder can be anywhere in your system. Add the path to the folder in which the code is placed in the `mlp.config` file.

For example: A sample model can be seen in [models/sample_model.py](models/sample_model.py). The default [mlp.config](mlp.config) file has points to the [models](models) folder. 


### Versions (I should choose a better term for this)
Almost always you'd have to run the same model with different hyper-parameters. Here I group a combination of values for the hyper-parameters and call them a version of a model. Use the `mlp_utils.Versions` class to define groups of parameters to be passed during each incarnation of the model. During each "incarnation", the model will be passed a dictionary which contains the values for each parameter set. For convenience I have defined a set of parameters as default and provided keys you can use in `mlp_utils.version_parameters`. While most of the parameters used will have no consequence out of the model, the parameters represented by the following keys of a version have side-effect (*In the future I will be removing the strong dependency on some of these parameters*):
* `mlp_utils.version_parameters.NAME`: This is a string used to keep track of the training and history and this name will be appended to the logs and outputs. This parameters must be set for each version.
* `mlp_utils.version_parameters.DATALOADER`: An `mlp_helper.DataLoader` object. Simply put, it is a wrapper for a dataset. You'll have extend the `mlp_helper.DataLoader` class to fit your needs. This object will be used by the pipeline to infer details about a training process, such as the number of steps (Refer documentation in [mlp_helper](mlp_helper.py) for more details). As of the current version of the pipeline, this parameter is mandatory.
* `mlp_utils.version_parameters.MODEL_DIR_SUFFIX`: Each model trained will be allocated a directory which can be used to save outputs (e.g. checkpoint files). When a model is being trained with a different set of versions if `allow_delete_model_dir` is set to `True` in the `MODEL`, the directory will be cleared as defined in `mlp_helper.Model.clean_model_dir` (Note that the behaviour of this function is not implemented by default to avoid a disaster). Some times you may want to have different directories to for each version of the model, in such a case, pass a string to this parameter, which will be appended to the directory name.
* `mlp_utils.version_parameters.BATCH_SIZE`: The batch size used in the model training. As of the current version of the pipeline, this parameter is mandatory.
* `mlp_utils.version_parameters.EPOC_COUNT`: The number of epocs that will be used. As of the current version of the pipeline, this parameter is mandatory.
* `mlp_utils.version_parameters.ORDER`: This is set to ensure the versions are loaded in the order they are defined. This value can be passed to a version to override this behaviour.

### Executing models
You can have any number of models in the `models` folder. Add the names of the scripts to the `models.config` file. If the `use_blacklist` is false, only the scripts whose names are under `[WHITELISTED_MODELS]` will be executed. if it is set to true all scripts except the ones under the `[BLACKLISTED_MODELS]` will be executed. Note that models can be added or removed (assuming it has not been executed) to the execution queue while the pipeline is running. That is after each model is executed, the pipeline will re-load the config file.

You can execute the pipeline by running the python script:

``` bash
python pipeline.py
```
Note: this will run the pipeline in test mode (Read [The two modes](#the-two-modes) for more information)
#### Outputs
The outputs and logs will be saved in files in a folder named `outputs` in the `models` folder. There are two files the user would want to keep track of (note that the \<hostname\> is the host name of the system on which the pipeline is being executed):
- `log-<hostname>`: This file contains the logs
- `output-<hostname>`: This file contains the output results of each "incarnation" of a model.

Note that the other files are used by the pipeline to keep track of training sessions previously launched.

#### The two modes
The pipeline can be executed in two modes: **test mode** and **execution mode**. When you are developing a model, you'd want to use the test mode. The pipeline when executed without any additional arguments will be executed in the test mode. Note that the test mode uses it's own config file `models_test.config`, that functions similar to the `models.config` file. To execute in execution mode, pass `-r` to the above command:

``` bash
python pipeline.py -r
```
Differences between test mode and execution mode (default behaviour):

Test mode | Execution mode
----------|---------------
Uses `models_test.config` | Uses `models.config`
The model directory is a temporary directory which will be cleared each time the model is executed | The model directory is a directory defined by the name of the model and versions `MODEL_DIR_SUFFIX`
If an exception is raised, the pipeline will halt is execution by raising the exception to the top level | Any exception raised will not stop the pipeline, the error will be logged and the pipeline will continue process with other versions and models
No results or logs will be recorded in the output files | All logs and outputs will be recorded in the output files

## Extra
I use an experiment log to maintain the experiments, which kinda ties into how I use the pipeline. For more info on that: https://ahmed-shariff.github.io/2018/06/11/Experiment-log/
