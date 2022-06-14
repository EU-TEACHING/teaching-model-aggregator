""" testingclient class to test the federated server with storage based interaction

this is developed under the intermediate assumption that the model structure
is embedded in the h5 file and it is going to be reused by the FederatedServer.
Next development will see the model structure associated to some form of application ID.

 * it uses the same env variables as the Federated server
 * it produces, tests and saves a full model (not just the weights)
 * it sends always the same model

TODO

 * receive the aggregate model and check that it matches with the one sent

"""

import os

from pathlib import Path
import logging
# import socket
import argparse

import tensorflow
from tensorflow import keras

# from teaching_comm import KafkaTopics, KafkaConfig, create_teaching_model_structure, compile_teaching_model, \
#    evaluate_teaching_model, write_modelfile, read_modelfile, model_weight_ensemble

from teaching_comm import create_teaching_model_structure, compile_teaching_model, \
    evaluate_teaching_model, write_modelfile, read_modelfile, model_weight_ensemble

import time
# manage watching files; not yet used in testingclient
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler



def clientloop(msg_timeout, upwardpath, senderID, model_filename, model_ext):

    print('called testing_client client_loop(', msg_timeout,',', upwardpath, ',', senderID, ',', model_filename, ',', model_ext, ')')
    #create and compile a model using teaching_comm methods
    local_model=create_teaching_model_structure()
    compile_teaching_model(local_model)
    print('testingclient main loop init, evaluating generated model')
    evaluate_teaching_model(local_model)
    local_model.summary()
    count=0

    try:
        while True:
            dir_path = Path(upwardpath + "/" +senderID + "/" + model_filename + str(count)+'.'+model_ext)
            # write full model using Keras
            local_model.save(dir_path, save_format='h5')
            print('clientloop model saved')
            count+=1
            time.sleep(msg_timeout)
    finally:
        print("exception in main testingclient loop, exiting")




def argparsing():
    parser = argparse.ArgumentParser(description='Start Federated Learning Server.')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
#    parser.add_argument('--broker', action='store', default="UNUSED", help='Address of the Kafka Broker')
#    parser.add_argument('--groupid', action='store', default="UNUSED", help='group id in the broker')
    parser.add_argument('--testmode', action='store_true')
    parser.add_argument('--n-models', action='store', default=3, type=int, help='Number of models before the average')
    parser.add_argument('--avg-timeout', action='store', default=300, type=int, help='Timeout before the average')
    parser.add_argument('--msg-timeout', action='store', default=3.0, type=float, help='Timeout foreach message')
    parser.add_argument('--logfile', action='store', default='FederatedServer.log',
                        help='Filename of the logfile')
    parser.add_argument('--client-model-prefix', action='store', default='client_model',
                        help='Filename prefix of the client model')
    parser.add_argument('--client-model-ext', action='store', default='h5',
                        help='Filename extension of the client model')
    parser.add_argument('--aggr-model', action='store', default='aggregate_model_tmp.h5',
                        help='Filename of the aggregate model')
    parser.add_argument('--upwarddir',action='store', default='', help='the directory for uploading client models')
    parser.add_argument('--downwarddir',action='store', default='', help='the directory for awaiting aggregate models (unused)')

    print(parser.parse_args())
    return parser.parse_args()



def main():
    global ARGUMENTS

    ARGUMENTS = argparsing()
    logging.basicConfig(filename=ARGUMENTS.logfile,
                        level=logging.INFO)

    # note that env vars overrride cli args

    da_logfile = os.environ.get('DA_LOGFILE')
    da_client_model_prefix = os.environ.get('DA_CLIENT_MODEL_PREFIX')
    if da_client_model_prefix == None:
        da_client_model_prefix = ARGUMENTS.client_model_prefix
    da_client_model_ext = os.environ.get('DA_CLIENT_MODEL_EXT')
    if da_client_model_ext == None:
        da_client_model_ext = ARGUMENTS.client_model_ext
    da_n_models = os.environ.get('DA_N_MODELS')
    da_avg_timeout = os.environ.get('DA_AVG_TIMEOUT')
    da_aggr_model = os.environ.get('DA_AGGR_MODEL')

    da_msg_timeout = os.environ.get('DA_MSG_TIMEOUT')
    if da_msg_timeout == None:
        da_msg_timeout = 3.0

    # communication via files - paths
    #
    da_upward_path = os.environ.get('DA_UPWARD_PATH')
    if da_upward_path == None:
        da_upward_path = ARGUMENTS.upwarddir
    #
    da_downward_path = os.environ.get('DA_DOWNWARD_PATH')
    if da_downward_path == None:
        da_downward_path = ARGUMENTS.downwarddir

    senderID="XXX"
    clientloop(da_msg_timeout, da_upward_path, senderID, da_client_model_prefix, da_client_model_ext)

if __name__ == "__main__":
    main()
