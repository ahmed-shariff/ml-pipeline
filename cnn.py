import numpy as np
import tensorflow as tf
import os
import sys
import random
import importlib.util
import shutil
import subprocess
import configparser
import logging
import socket
import string
from datetime import datetime

from dataLoader import CLASSES_JSON
from dataLoader import TEST_JSON
from dataLoader import TRAIN_JSON
from dataLoader import DataLoader
from dataLoader import DataLoaderJson
from dataLoader import DataLoaderJsonSized
from dataLoader import cifar10Loader
from utils import VersionLog

from global_values import MODELS_DIR
from global_values import DATA_FILE_LOCATION
from global_values import TEST_FILE_LOCATION
from global_values import OUTPUT_FILE
from global_values import HISTORY_FILE
from global_values import TRAINING_HISTORY_LOG_FILE
from global_values import LOG_FILE
from global_values import NO_LOG
from global_values import DATA_CODE_MAPPING
from global_values import EXECUTED_MODELS
from global_values import USE_BLACKLIST
from global_values import LISTED_MODELS
from global_values import EPOC_COUNT

from global_values import TEST_MODE

from global_values import mtime
from global_values import version
from global_values import train_time
from global_values import vless

from global_values import BATCH_SIZE
from global_values import USE_ALL_CLASSES
from global_values import CLASSES_COUNT
from global_values import CLASSES_OFFSET
from global_values import ALLOW_DELETE_MODEL_DIR
from global_values import RESTART_GLOBAL_STEP
from global_values import MODEL_DIR_SUFFIX

tf.logging.set_verbosity(tf.logging.INFO)

def _main():
  # sys.path.append(os.getcwd())
  print(list((k, m[version].exectued_versions)  for k,m in EXECUTED_MODELS.items()))
  
  if TEST_MODE:
    #shutil.rmtree("models/model_ckpts", ignore_errors=True)
    logging_iteration_count = 1
    classification_steps = 1
    tf.reset_default_graph()
    record_training = False
    modestring="\033[1;33mTESTING\033[0m"
  else:
    logging_iteration_count = 2000
    record_training = True
    modestring="\033[1;31mRUNNING MODEL TRAINING\033[0m"


  # dataLoader = cifar10Loader(None,
  #                            ["../Datasets/cifar-10-batches-py/data_batch_1",
  #                             "../Datasets/cifar-10-batches-py/data_batch_2",
  #                             "../Datasets/cifar-10-batches-py/data_batch_3",
  #                             "../Datasets/cifar-10-batches-py/data_batch_4",
  #                             "../Datasets/cifar-10-batches-py/data_batch_5"],
  #                            ["../Datasets/cifar-10-batches-py/test_batch"])
  
  dataLoader = DataLoaderJsonSized(CLASSES_JSON,
                                   DATA_FILE_LOCATION,
                                   TEST_FILE_LOCATION,
                                   batch_size =  BATCH_SIZE,
                                   use_all_classes = USE_ALL_CLASSES,
                                   classes_count = CLASSES_COUNT,
                                   classes_offset = CLASSES_OFFSET)

  # dataLoader = DataLoader(DATA_FILE_LOCATION,
  #                         #TEST_FILE_LOCATION,
  #                         batch_size =  BATCH_SIZE,
  #                         use_all_classes = USE_ALL_CLASSES,
  #                         classes_count = CLASSES_COUNT)
  # dataLoader.set_classes(False,20, classes_offset = 10)
  # f = dataLoader.test_files
  # l = dataLoader.test_labels
  # o = 10
  # print(len(f), len(l))
  # for x in range(25):
  #   i = int(random.uniform(1, len(l)))
  #   print("{0}--{1}\t{2}\n".format(
  #     f[i].split("/")[-2] == dataLoader.DATA_CODE_MAPPING[o + l[i]],
  #     f[i].split("/")[-2],
  #     dataLoader.DATA_CODE_MAPPING[o + l[i]]))
  # print(dataLoader.default_classes_offset)
  print({i:dataLoader.DATA_CODE_MAPPING[i] for i in [71, 72, 73, 74, 75, 76, 77, 78, 79, 80]})
  
  current_model, version_name, clean_model_dir = getNextModel()
  while current_model is not None:
    
    log("Model loaded: {0}".format(current_model.__name__))
    if version_name is None:
      print("\033[1;32mNo Version Specifications\033[0m")
      log("No version specs")
    else:
      print("\033[1;32mVersion: {0}\033[0m".format(version_name))
      log("version loaded: {0}".format(version_name))
      
    print("\033[1;32mMode: {0}\033[0m".format(modestring))
    try:
      allow_delete_model_dir = current_model.ALLOW_DELETE_MODEL_DIR
    except:
      allow_delete_model_dir = ALLOW_DELETE_MODEL_DIR

    try:
      restart_global_step = current_model.RESTART_GLOBAL_STEP
    except:
      restart_global_step = RESTART_GLOBAL_STEP
    if version_name is None:
      try:
        use_all_classes =  current_model.USE_ALL_CLASSES
      except:
        use_all_classes = USE_ALL_CLASSES
      try:
        classes_count = current_model.CLASSES_COUNT
      except:
        classes_count = CLASSES_COUNT
      try:
        batch_size = current_model.BATCH_SIZE
      except:
        batch_size = BATCH_SIZE
      try:
        epoc_count = current_model.EPOC_COUNT
      except:
        epoc_count = EPOC_COUNT
      try:
        classes_offset = current_model.CLASSES_OFFSET
      except:
        classes_offset = CLASSES_OFFSET
      try:
        model_dir_suffix = current_model.MODEL_DIR_SUFFIX
      except:
        model_dir_suffix = MODEL_DIR_SUFFIX
      try:
        verion_hooks = current_model.VERSION_HOOKS
      except:
        verion_hooks = VERSION_HOOKS
    else:
      version_spec = current_model.VERSIONS.getVersion(version_name)
      use_all_classes = version_spec.use_all_classes
      classes_count = version_spec.classes_count
      batch_size = version_spec.batch_size
      epoc_count = version_spec.epoc_count
      classes_offset = version_spec.classes_offset
      model_dir_suffix = version_spec.model_dir_suffix
      verion_hooks = version_spec.hooks

    dataLoader.batch_size = batch_size
    dataLoader.set_classes(use_all_classes, classes_count, classes_offset)

    if TEST_MODE:
      model_dir = "models/model_ckpts/temp"
      shutil.rmtree(model_dir, ignore_errors=True)
      evaluation_steps = 1
      train_eval_steps = 1
    else:
      model_dir="models/model_ckpts/{0}-{1}".format(current_model.__name__.split(".")[-2], model_dir_suffix)
      evaluation_steps = len(dataLoader.test_files)
      train_eval_steps = len(dataLoader.train_files)
      #int(len(dataLoader.train_files)/dataLoader.batch_size)
    # Create the Estimator
    # Set up logging for predictions
    # Log the values in the "Softmax" tensor with label "probabilities"
    tensors_to_log = {"probabilities": "softmax_tensor"}
    logging_hook = tf.train.LoggingTensorHook(tensors=tensors_to_log, every_n_iter= logging_iteration_count)

    # Train the model
    classifier_executed=False
    exception_count = batch_size #maximum numeber of possible time this cal loop!! if more, prolly inifinite loop
    eval_complete=False
    training_done = False
    while not classifier_executed:
      tf.logging.set_verbosity(tf.logging.INFO)
      try:
        if clean_model_dir and allow_delete_model_dir:
          shutil.rmtree(model_dir, ignore_errors=True)
          log("cleaning model dir: {0}".format(model_dir))
          print("\033[1;038mclearning folder {0}\033[0m".format(model_dir))

        if clean_model_dir and not allow_delete_model_dir and restart_global_step:
          reset_gs = True
        else:
          reset_gs = False
        s = mySess()
        hooks = [s, logging_hook] + verion_hooks
        classifier = tf.estimator.Estimator(
          model_fn=current_model.get_model_fn(version_name, dataLoader.classes_count, reset_gs),
          model_dir=model_dir)

          
        #this wont work!! need seperate file to track launched training
        # if EXECUTED_MODELS[current_model.__name__][mtime] > EXECUTED_MODELS[current_model.__name__][train_time]:
        #   subprocess.run(["rm", "-rf", model_dir], check = True)
        # EXECUTED_MODELS[current_model.__name__][train_time] = datetime.now().timestamp()
        save_training_time(current_model, version_name)
        classification_steps = getClassificationSteps(TEST_MODE, dataLoader, model_dir, epoc_count, reset_gs)
        log("Steps: {0}".format(classification_steps), log_tf=True)
        if classification_steps > 0:
          classifier.train(input_fn = dataLoader.get_train_input_fn(),
                           steps= classification_steps,
                           hooks = hooks)
          log("Model trained")
          training_done = True
        else:
          # classifier.train(input_fn = dataLoader.get_train_input_fn(),
          #                  steps= 1,
          #                  hooks = [logging_hook,s])
          log("No training. Loaded pretrained model", log_tf=True)
          training_done = False
        classifier_executed = True

        if s.tvar is not None:
          log("Trainable parms: {0}".format(
            sum([v.flatten().shape[0] for k,v in s.tvar.items()])),
              log_tf=True)
          print({k: v.flatten().shape[0] for k,v in s.tvar.items()})
        # print("*************************************************")
        # print(len([k for k,v in s.mvar.items()]))
        # print([k for k,v in s.mvar.items()])
        # print("*************************************************")
        # print(len([k for k,v in s.gvar.items()]))
        # print([k for k,v in s.gvar.items()])
        # Evaluate the model and print results
        try:
          log("Training evaluation started: {0} steps".format(train_eval_steps), log_tf=True)
          tf.logging.set_verbosity(tf.logging.ERROR)
          train_results = classifier.evaluate(input_fn = dataLoader.get_train_input_fn(tf.estimator.ModeKeys.EVAL),# dataLoader.get_test_input_fn(),
                                              steps = train_eval_steps)
        except tf.errors.InvalidArgumentError:
          tf.logging.set_verbosity(tf.logging.INFO)
          raise
        except Exception as e:
          tf.logging.set_verbosity(tf.logging.INFO)
          train_results = "Training evaluation failed: {0}".format(str(e))
          log(train_results)
        
        try:
          log("Testing evaluation started: {0} steps".format(evaluation_steps), log_tf=True)
          tf.logging.set_verbosity(tf.logging.ERROR)
          eval_results = classifier.evaluate(input_fn = dataLoader.get_test_input_fn(),
                                             steps = evaluation_steps)
        except tf.errors.InvalidArgumentError:
          tf.logging.set_verbosity(tf.logging.INFO)
          raise
        except Exception as e:
          tf.logging.set_verbosity(tf.logging.INFO)
          eval_results = "Test evaluation failed: {0}".format(str(e))
          log(eval_results)

        
        log("Model evaluation complete")
      except tf.errors.ResourceExhaustedError:
        dataLoader.batch_size -= 1
        log("ResourceExhaustedError: reducing batch_size to {0}".format(dataLoader.batch_size))
        print("\033[1;031mResourceExhaustedError: reducing batch_size to {0}\033[0m".format(dataLoader.batch_size))
      except tf.errors.InvalidArgumentError as e:
        if not allow_delete_model_dir:
          log("{0}".format(str(e)))
          log("Not cleaning folder, skiping evaluation")
        else:
          classifier_executed = False
          classifier =None
          #shutil.rmtree(model_dir, ignore_errors=True)
          subprocess.run(["rm", "-rf", model_dir])
          log("InvalidArgumentError: clearning folder {0}".format(model_dir), logging.ERROR)
          print("\033[1;031mInvalidArgumentError: clearning folder {0}\033[0m".format(model_dir))
      # TODO: Nan error: reduce learning rate
      except Exception as e:
        exception_count -= 1
        if TEST_MODE is True or exception_count == 0:
          raise
        else:
          log("Exception: {0}".format(str(e)), logging.ERROR)
          if NO_LOG:
            raise
          else:
            break
    classifier = None  
    try:
      print("Training result: {0}".format(train_results))
    except                  :
      print("Training result: evaluation failed")
      eval_results="Evaluation failed due to unknown reason"
    try:
      print("Evaluation result: {0}".format(eval_results))
    except:
      print("Evaluation result: evaluation failed")
      eval_results="Evaluation failed due to unknown reason"
    if record_training:
      save_results_to_file(current_model, eval_results, train_results, dataLoader, training_done, model_dir)
    current_model,version_name, clean_model_dir  = getNextModel()


def getClassificationSteps(test_mode, dataLoader, model_dir, epoc_count=EPOC_COUNT, reset_gs=False):
  if test_mode:
    return 1
  else:
    complete_steps = epoc_count * len(dataLoader.train_files) / dataLoader.batch_size
    global_step = tf.train.get_checkpoint_state(model_dir)
    
    if global_step is None or reset_gs:
      return complete_steps
    else:
      gs = int(global_step.model_checkpoint_path.split("-")[-1])
      if complete_steps > gs:
        return complete_steps - gs
      else:
        return 0
      

def getNextModel(just_return_model=False):
  config_update()
  for rdir, dirs, files in os.walk("models"):
    for f in files:
      if f.endswith(".py"):
        file_path = os.path.join(rdir,f)
        # TODO: Should remove this check, prolly has no use!
        if True:#file_path not in EXECUTED_MODELS or EXECUTED_MODELS[file_path][mtime] + 5 < os.path.getmtime(file_path): 
          if USE_BLACKLIST and file_path in LISTED_MODELS:
            continue
          if not USE_BLACKLIST and file_path not in LISTED_MODELS:
            continue
          spec = importlib.util.spec_from_file_location(f,file_path)
          module = importlib.util.module_from_spec(spec)
          spec.loader.exec_module(module)
          clean_model_dir = False
          try:
            if module.IS_MODEL is False:
              continue
          except:
            continue
          if just_return_model:
            print("\033[1;33mJust returning module\033[1;0m")
            return module
          module.__name__ = file_path
          returning_version = None
          try:
            versions = module.VERSIONS
          except:
            versions = None
            returning_version = None
          print("\n\033[1;32mProcessing new model: {0}\033[1;0m\n".format(module.__name__))  
          
          with open(TRAINING_HISTORY_LOG_FILE, "r") as t_hist_file:
            t_history = [line.rstrip("\n") for line in t_hist_file]
            all_history = [t_entry.split("::") for t_entry in t_history]
            module_history = [(v,float(t)) for n,v,t in all_history if n == module.__name__]
          
          #print("\n\033[1;32mEvaluating model: {0}\033[1;0m\n".format(module.__name__))
          if file_path not in EXECUTED_MODELS:
            EXECUTED_MODELS[module.__name__] = {}
            EXECUTED_MODELS[module.__name__][train_time]=0
            EXECUTED_MODELS[module.__name__][version]=VersionLog()
            
          EXECUTED_MODELS[module.__name__][mtime] = os.path.getmtime(file_path)

          if versions is None:
            l = [t for v,t in module_history if v == vless]
            if len(l) == 0 or  max(l) < os.path.getmtime(file_path):
              clean_model_dir= True
              EXECUTED_MODELS[module.__name__][version].clean()
          else:
            reset_model_dir = True
            for v,t in module_history:
              if t > os.path.getmtime(file_path):
                reset_model_dir = False
            if reset_model_dir:
              clean_model_dir = True
              EXECUTED_MODELS[module.__name__][version].clean()
            else:
              t_ = os.path.getmtime(file_path)
              versions__ = [v_.name for v_ in versions.versions]
              for v,t in module_history:
                #print(v,t)
                if t > t_:
                  if EXECUTED_MODELS[module.__name__][version].executed(v) is not VersionLog.EXECUTED and v in versions__:
                    t_ = t
                    returning_version = v
            if returning_version is None:
              for v in versions.versions:
                if EXECUTED_MODELS[module.__name__][version].executed(v.name) is not VersionLog.EXECUTED:
                  returning_version = v.name
                  clean_model_dir = True
            print(EXECUTED_MODELS[module.__name__][version].exectued_versions)
            print(EXECUTED_MODELS[module.__name__][version].executing_version)
            if returning_version is None:
              continue
          return module, returning_version, clean_model_dir
  return None, None, False

def save_training_time(model, version_):
  if TEST_MODE:
    return
  name = model.__name__
  if version_ is None:
    version_ = vless
  with open(TRAINING_HISTORY_LOG_FILE, "a") as log_file:
    time = datetime.now().timestamp()
    EXECUTED_MODELS[name][version].addExecutingVersion(version_, time)
    log_file.write("{0}::{1}::{2}\n".format(name,
                                            EXECUTED_MODELS[name][version].executing_version,
                                            time))

    
def save_results_to_file(model, result, train_result, dataloader, training_done, model_dir):
  modified_dt = datetime.isoformat(datetime.fromtimestamp(EXECUTED_MODELS[model.__name__][mtime]))
  result_dt = datetime.now().isoformat()
  with open(OUTPUT_FILE, 'a', encoding = "utf-8") as outfile:
    outfile.write("[{0}]: Evaluation on test-set of model{1}: \n\t\t\t{2}\n".format(result_dt,
                                                            model.__name__,
                                                            result))
    outfile.write("\tEvaluation on train-set of model{0}: \n\t\t\t{1}\n".format(model.__name__, train_result))
    outfile.write("\t\tused models mtime:{0}\n".format(modified_dt))
    outfile.write("\t\tmodel dir: {0}".format(model_dir))
    if not training_done:
      outfile.write("\tNO TRAINING. ONLY EVAL\n\n")
    try:
      outfile.write("\t\tModel Summery:\n{0}\n".format(model.MODEL_SUMMERY))
    except:
      outfile.write("\t\tModel Summery not provided\n")
    outfile.write("\t\tdataSummery:\n\t\t Loader summery: {0}\n".format(dataloader.summery))
    outfile.write("\t\tClasses: {0}\n".format(dataloader.classes_count))
    outfile.write("\t\tTraining data: {0}\n".format(len(dataloader.train_files)))
    outfile.write("\t\tTesting data: {0}\n".format(len(dataloader.test_files)))
    outfile.write("\t\tTraining batch size: {0}\n".format(dataloader.batch_size))
    try:
      outfile.write("\t\tTraining epocs: {0}\n".format(model.EPOC_COUNT))
    except:
      outfile.write("\t\tTraining epocs: {0}\n".format(EPOC_COUNT))
    outfile.write("\n\t\tUsed labels: {0}\n\n".format({i:dataloader.DATA_CODE_MAPPING[i] for i in dataloader.used_labels}))
      
  with open(HISTORY_FILE, 'a', encoding = "utf-8") as hist_file:
    hist_file.write("{0}::{1}::{2}\n".format(model.__name__,
                                             EXECUTED_MODELS[model.__name__][mtime],
                                             EXECUTED_MODELS[model.__name__][version]
                                             .executing_version))
  EXECUTED_MODELS[model.__name__][version].moveExecutingToExecuted()

def log(message, level = logging.INFO, log_tf=False):
  if level is not logging.INFO and level is not logging.ERROR:
    raise AttributeError("level cannot be other than logging.INFO or logging.ERROR, coz i am lazy to get others in here")
  if log_tf:
    tf.logging.log(level, message)
  if TEST_MODE or NO_LOG:
    print(message)
  else:
    with open(LOG_FILE, 'a', encoding="utf-8") as log_file:
      level = ["INFO" if level is logging.INFO else "ERROR"]
      time = datetime.now().isoformat()
      log_file.write("[{0}]::{1} - {2}\n".format(time, level[0], message))

def config_update():
  config = configparser.ConfigParser(allow_no_value=True)
  config_file = config.read("cnn.config")
  global MODELS_DIR
  global DATA_FILE_LOCATION
  global TEST_FILE_LOCATION
  global EPOC_COUNT
  global USE_BLACKLIST
  global LISTED_MODELS
  
  global HISTORY_FILE
  global LOG_FILE
  global OUTPUT_FILE
  global TRAINING_HISTORY_LOG_FILE
  if len(config_file)==0:
    print("\033[1;031mWARNING:\033[0:031mNo 'cnn.config' file found\033[0m")
  else:
    try:
      config["CNN_PARAM"]
    except KeyError:
      print("\033[1;031mWARNING:\033[0:031mNo CNN_PARAM section in 'cnn.config' file\033[0m")
    MODELS_DIR = config.get("CNN_PARAM", "models_dir", fallback=MODELS_DIR)
    DATA_FILE_LOCATION = config.get("CNN_PARAM", "data_file_location", fallback=DATA_FILE_LOCATION)
    TEST_FILE_LOCATION = config.get("CNN_PARAM", "test_file_location", fallback=TEST_FILE_LOCATION)
    EPOC_COUNT = config.getint("CNN_PARAM", "epoc_count", fallback=EPOC_COUNT)
    USE_BLACKLIST =  config.getboolean("CNN_PARAM", "use_blacklist", fallback=USE_BLACKLIST)
    try:
      if USE_BLACKLIST:
        LISTED_MODELS = config["BLACKLISTED_MODELS"]
      else:
        LISTED_MODELS = config["WHITELISTED_MODELS"]
      l = []
      for model in LISTED_MODELS:
        l.append(os.path.join(MODELS_DIR, model))
      LISTED_MODELS = l
      print("\033[1;036m{0}\033[0;036m: {1}\033[0m".format(
        ["BLACKLISTED_MODELS" if USE_BLACKLIST else "WHITELISTED_MODELS"][0].replace("_"," "),
        LISTED_MODELS).lower())
    except KeyError:
      print("\033[1;031mWARNING:\033[0:031mNo {0} section in 'cnn.config' file\033[0m".format(
        ["BLACKLISTED_MODELS" if USE_BLACKLIST else "WHITELISTED_MODELS"][0]))

  hostName = socket.gethostname()
  OUTPUT_FILE = MODELS_DIR + "/output-{0}".format(hostName)
  HISTORY_FILE = MODELS_DIR + "/history-{0}".format(hostName)
  TRAINING_HISTORY_LOG_FILE = MODELS_DIR + "/t_history-{0}".format(hostName)
  LOG_FILE = MODELS_DIR + "/log-{0}".format(hostName)
  open(OUTPUT_FILE, "a").close()
  open(HISTORY_FILE, "a").close()
  open(TRAINING_HISTORY_LOG_FILE, "a").close()
  open(LOG_FILE, "a").close()

      
def main(unused_argv):
  global TEST_MODE
  global NO_LOG
  config_update()
  if len(unused_argv)> 1:
    if any("r" in s for s in unused_argv) :
      TEST_MODE = False
    else:
      TEST_MODE = True
      
    if any("h" in s for s in unused_argv):
      if not os.path.isfile(HISTORY_FILE) and not os.path.isfile(TRAINING_HISTORY_LOG_FILE):
        print("\033[1;31mWARNING: No 'history' file in 'models' folder. No history read\033[0m")
      else:
        with open(HISTORY_FILE, 'r', encoding = "utf-8") as hist_file:
          history = [line.rstrip("\n") for line in hist_file]
          for hist_entry in history:
            hist_entry = hist_entry.split("::")
            name=hist_entry[0]
            time=hist_entry[1]
            ttime=0
            v = None
            if len(hist_entry) > 2:
              v = hist_entry[2]
            if name not in EXECUTED_MODELS:
              EXECUTED_MODELS[name] = {}
              EXECUTED_MODELS[name][mtime] = float(time)
              EXECUTED_MODELS[name][version] = VersionLog()
              if v is not None and v is not "":
                EXECUTED_MODELS[name][version].addExecutedVersion(v)
              #needs to be taken from seperate file
              #EXECUTED_MODELS[name][train_time] = float(ttime)
            else:
              if EXECUTED_MODELS[name][mtime] < float(time):
                EXECUTED_MODELS[name][mtime] = float(time)
                EXECUTED_MODELS[name][version].clean()
              if v is not None and v is not "":
                EXECUTED_MODELS[name][version].addExecutedVersion(v)
                #EXECUTED_MODELS[name][train_time] = float(ttime)
        with open(TRAINING_HISTORY_LOG_FILE, "r") as t_hist_file:
          t_history = [line.rstrip("\n") for line in t_hist_file]
          for t_entry in t_history:
            n,v,t = t_entry.split("::")
            t = float(t)
            if n in EXECUTED_MODELS:
              if EXECUTED_MODELS[n][mtime] < t and EXECUTED_MODELS[n][version].executed(v) is not VersionLog.EXECUTED:
                EXECUTED_MODELS[n][version].addExecutingVersion(v,t)
                
    if any("nl" in s for s in unused_argv):
      NO_LOG=True
    else:
      NO_LOG=False
      
    # if any("-b" in s for s in unused_argv):
    #   if not os.path.isfile(HISTORY_FILE):
    #     print("\033[1;31mWARNING: No 'blacklist' file in 'models' folder, No models blacklisted\033[0m")
    #   else:
    #     with open(HISTORY_FILE, 'r') as bl_file:
    #       BLACKLISTED_MODELS = [line.rstrip("\n") for line in bl_file]    

  # if not TEST_MODE:
  #   logging.basicConfig(filename=LOG_FILE, format = '%(asctime)s ::%(levelname)s - %(message)s')
  # else:
  #   logging.basicConfig(format = '%(acstime)s ::%(levelname)s - %(message)s')
  log("=====================CNN session started")
  _main()
  log("=====================CNN Session ended")


class mySess(tf.train.SessionRunHook):
  def __init__(self):
    self.tvar = None
    self.mvar = None
    self.gvar = None

  def end(self, session):
    self.session = session
    
    self.tvar = session.run({v.name:v.value() for v in tf.trainable_variables()})
    self.mvar = session.run({v.name:v.value() for v in tf.model_variables()})
    self.gvar = session.run({v.name:v.value() for v in tf.global_variables()})
  def after_create_session(self, session, coord):
    #log("Session devices: {0}".format([dev.name for dev in session.list_devices()]), log_tf=True)
    pass
    
if __name__ == "__main__":
  tf.app.run()
