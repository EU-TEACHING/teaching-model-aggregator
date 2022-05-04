"""FederatedServer class - via Kafka it reads AI models from Far Edge, writes aggregated model

The class is both a Kafka consumer and a producer. It is designed to
run on Near-Edge devices or in the Cloud. It consumes Edge-produced AI
local models and aggregates them via a specified function to support
federated learning schemes. By design the result can be sent to a
higher level aggregator for further processing, or back down toward
the edge. The models are stored until a condition is met, then they
are aggregated and sent away (there is no query-reply behaviour).

Current implementation :
 * uses tensorflow and keras to process H5 model
 * assumes a fixed, known model, only the weights are sent from the Edge
 * imports Kafka topic and broker config from the teaching_comm.py
 * aggregates after receiving a prefixed number of models
 * recomputes and validates the model often to ease debug
 * does not yet send the model upward
 * computes the aggregation by weight average on all model weights

Future work
 * TODO split h5 model work to a separate class
 * TODO allow per-app model configuration
 * TODO allow per-app choice of aggregation function
 * TODO implement hierarchical federated aggregation (Far E./Near E./Cloud)
"""

import os

from pathlib import Path
import logging
# import socket
import argparse

# from confluent_kafka import Consumer, Producer
# from confluent_kafka import KafkaError, KafkaException
from tensorflow import keras

# from teaching_comm import KafkaTopics, KafkaConfig, create_teaching_model_structure, compile_teaching_model, \
#    evaluate_teaching_model, write_modelfile, read_modelfile, model_weight_ensemble

from teaching_comm import create_teaching_model_structure, compile_teaching_model, \
    evaluate_teaching_model, write_modelfile, read_modelfile, model_weight_ensemble

# manage watching files...
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ARGUMENTS = None


# derived from pypi example
class FileWatchLoop:

    def __init__(self, directory, fedserver):
        self.observer = Observer()
        # Set the directory on watch
        self.watchDirectory = directory
        # Federated Server object, will process the received data
        self.FedServer = fedserver

    def run(self):
        event_handler = Handler(self.FedServer)
        self.observer.schedule(event_handler, self.watchDirectory, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            #  revise the exception clause here
            self.observer.stop()
            # TODO add proper logging to file
            print("Observer Stopped")

        self.observer.join()


# this object class handles actual event dispatching and selection
# will forward file creation events to the FederatedServer
class Handler(FileSystemEventHandler):

    def __init__(self, fedserver):
        # we forward the important events to the FedServer code
        self.FedServer = fedserver
        # Set the patterns for PatternMatchingEventHandler
        # watchdog.events.PatternMatchingEventHandler.__init__(self, patterns=['*.csv'],
        #                                                     ignore_directories=True, case_sensitive=False)

    def on_created(self, event):
        # call federated server receive model
        averaged = self.FedServer.process_model(event.src_path)
        print("Watchdog received created event - % s." % event.src_path)
        if averaged:
            averaged.save_weights(self.FedServer.aggregate_filename)
            self.FedServer.federated_model_resend()


class FederatedServer(object):

    def __init__(self, num_msg, testmode, aggrfilename, client_model_prefix, client_model_ext,
                 broker_addr, groupid, outgoing_path):
        # no incoming_path as it is handled by the FileWatchLoop class
        # , cryptselect, crypt_passwords, crypt_salts):
        self.receiver = None
        self.producer = None

        self.local_store = []
        self.NUM_MSGS = num_msg

        self.rcvd_model = None
        self.avg_model = None
        self.model_common = None

        self.ds_test = None
        self.receiver_running = True
        self.test_mode = testmode
        self.aggregate_filename = aggrfilename

        self.client_model_prefix = client_model_prefix
        self.client_model_ext = client_model_ext

        # hack for the second integration demo, it will contain the last seen Sender ID, used in asnwering back
        self.SenderId = "X"

        # self.init_communication(broker_addr, groupid)
        self.init_local_models()

        # self.incoming_path = incomingpath
        self.outgoing_path = outgoing_path

    # method to compute models that we will use to send around or as a reference when loading weights
    def init_local_models(self):

        # Eventually the model shall be a parameter of the aggregator (e.g. a saved full model)
        self.rcvd_model = create_teaching_model_structure()
        compile_teaching_model(self.rcvd_model)

        # create a new model with the same structure
        self.model_common = keras.models.clone_model(self.rcvd_model)

    # load all models from files referenced in the local storage (local dir)
    def load_all_client_models(self, n_start, n_end):
        all_client_models = list()

        for epoch in range(n_start, n_end):
            # define filename for this ensemble
            filename = self.client_model_prefix + "_" + str(epoch) + "." + self.client_model_ext

            # load model from file
            model = keras.models.clone_model(self.model_common)

            # load weights
            model.load_weights(filename)

            # add to list of members
            all_client_models.append(model)

        return all_client_models

    # propagate a processed/aggregate model. Now only back to clients, later on we will push it to the Cloud
    def federated_model_resend(self):

        # read the model weights as a binary file
        data = read_modelfile(self.aggregate_filename)

        # copy the data to a given filename in the downward path
        # having sender_id in the path is a hack for the integration demo

        # create the directory if not already there
        dir_path = Path(self.outgoing_path + "/" + self.SenderId)
        if dir_path.exists() and dir_path.is_dir():
            print("aggregate model dir found")
        else:
            dir_path.mkdir()
            print("aggregate model dir created")

        file_pathname = self.outgoing_path + "/" + self.SenderId + "/" + self.aggregate_filename

        # delete file if already there, to generate creation event
        # we assume the MTS will sense the create event and present to kafka
        file_path = Path(file_pathname)
        if file_path.exists():
            file_path.unlink()

        # write data to the above path
        write_modelfile(file_pathname, data)

    # process function for a single model received;
    # return averaged models data if it is generated, otherwise return None
    def process_model(self, full_filename):
        # we get a filename naw, we nee to parse it to extract the sender id as well as copy it to our private storage
        # we will need to rework the management to avoid copying twice the files
        # we will need in the future to add metadata like timestamps

        full_path = Path(full_filename)
        #  parsing
        msg_filename =  Path.name
        # last dir is expected to be the sender id
        msg_sender_id = Path(full_path.parent).name

        print("process_model after parsing: ", full_filename, msg_filename, msg_sender_id)

        if len(self.local_store) < self.NUM_MSGS:
            print("Event received", full_filename)
            # choose a filename in the local store, copy the received file message there
            filename = f'{self.client_model_prefix}_{len(self.local_store)}.{self.client_model_ext}'
            # copy msg_filename to filename, binary content
            data = read_modelfile(msg_filename)
            write_modelfile(filename, data)
            self.local_store.append(filename)
            # if in test mode, received weights will be assigned to a model for testing purpose
            if self.test_mode:

                # check if the local testing model has been initialised
                if self.rcvd_model is None:
                    self.init_local_models()

                # reload weights
                self.rcvd_model.load_weights(filename)

                # and test
                evaluate_teaching_model(self.rcvd_model)

                # print model summary
                self.rcvd_model.summary()

            # this is a duplicate, as we have the file on storage
            # self.local_store.append(msg.value())
            logging.info(f'Model received (possibly encrypted), length {len(data)}')
        else:
            logging.info(f'Average to be computed on {len(self.local_store)} models')

            # reference https://machinelearningmastery.com/polyak-neural-network-model-weight-ensemble/
            members = self.load_all_client_models(0, self.NUM_MSGS)
            averaged = model_weight_ensemble(members)
            if self.test_mode:
                evaluate_teaching_model(averaged)
                averaged.summary()
            #  we are not using the local store indeed, clear it for the side effect of resetting the file names
            self.local_store.clear()
            #  return the averaged model to the caller when we produce one
            return averaged

    # TODO no longer used, remove as new method is ready
    # Processor of each single message
    # def msg_process(self, msg):
    #     if len(self.local_store) < self.NUM_MSGS:
    #
    #         print("Message received", msg.value())
    #
    #         # choose a filename in the local store, dump the kafka message there
    #         filename = f'{self.client_model_prefix}_{len(self.local_store)}.{self.client_model_ext}'
    #         # write_modelfile(filename, msg.value()) # when no encryption was supported
    #         write_modelfile(filename, msg.value())
    #         self.local_store.append(filename)
    #
    #         # if in test mode, received weights will be assigned to a model for testing purpose
    #         if self.test_mode:
    #
    #             # check if the local testing model has been initialised
    #             if self.rcvd_model is None:
    #                 self.init_local_models()
    #
    #             # reload weights
    #             self.rcvd_model.load_weights(filename)
    #
    #             # and test
    #             evaluate_teaching_model(self.rcvd_model)
    #
    #             # print model summary
    #             self.rcvd_model.summary()
    #
    #         # this is a duplicate, as we have the file on storage
    #         # self.local_store.append(msg.value())
    #         logging.info(f'Model received (possibly encrypted), length {len(msg.value())}')
    #
    #     else:
    #         logging.info(f'Average to be computed on {len(self.local_store)} models')
    #
    #         # reference https://machinelearningmastery.com/polyak-neural-network-model-weight-ensemble/
    #         members = self.load_all_client_models(0, self.NUM_MSGS)
    #         averaged = model_weight_ensemble(members)
    #
    #         if self.test_mode:
    #             evaluate_teaching_model(averaged)
    #             averaged.summary()
    #
    #         #  we are not using the local store indeed, clear it for the side effect of resetting the file names
    #         self.local_store.clear()
    #
    #         #  return the averaged model to the caller when we produce one
    #         return averaged

    # def oldmain_loop(self, msg_timeout):
    #     try:
    #         self.receiver.subscribe([KafkaTopics.CLIENT_MODEL_TOPIC])
    #
    #         # TODO in case we need an initial handshake with clients it should be likely coded here, e.g.
    #         # 1) gather client ip / names
    #         # 2) send each client some init message to solicit first model
    #
    #         while self.receiver_running:
    #             msg = self.receiver.poll(msg_timeout)
    #
    #             # print("Message received")
    #
    #             if msg is None:
    #                 continue
    #
    #             if msg.error():
    #                 if msg.error().code() == KafkaError._PARTITION_EOF:
    #                     # End of partition event
    #                     logging.error('%% %s [%d] end at offset %d\n' % (msg.topic(), msg.partition(), msg.offset()))
    #                     print("There is an error")
    #                 elif msg.error():
    #                     raise KafkaException(msg.error())
    #             else:
    #                 averaged = self.msg_process(msg)
    #                 if averaged:
    #                     averaged.save_weights(self.aggregate_filename)
    #                     self.federated_model_resend()
    #
    #     finally:
    #         # Close down consumer to commit final offsets.
    #         self.receiver.close()
    #

    def shutdown(self):
        self.receiver_running = False


def argparsing():
    parser = argparse.ArgumentParser(description='Start Federated Learning Server.')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
#    parser.add_argument('--broker', action='store', default=KafkaConfig.FED_KAFKA_BROKER_URL,
#                        help='Address of the Kafka Broker')
#    parser.add_argument('--groupid', action='store', default=KafkaConfig.FED_KAFKA_BROKER_groupid,
#                        help='group id in the broker')
    parser.add_argument('--broker', action='store', default="UNUSED", help='Address of the Kafka Broker')
    parser.add_argument('--groupid', action='store', default="UNUSED", help='group id in the broker')
    parser.add_argument('--testmode', action='store_true')
    parser.add_argument('--n-models', action='store', default=3, type=int, help='Number of models before the average')
    parser.add_argument('--avg-timeout', action='store', default=300, type=int, help='Timeout before the average')
    parser.add_argument('--msg-timeout', action='store', default=3, type=int, help='Timeout foreach message')
    parser.add_argument('--logfile', action='store', default='FederatedServer.log',
                        help='Filename of the logfile')
    parser.add_argument('--client-model-prefix', action='store', default='client_model',
                        help='Filename prefix of the client model')
    parser.add_argument('--client-model-ext', action='store', default='h5',
                        help='Filename extension of the client model')
    parser.add_argument('--aggr-model', action='store', default='aggregate_model_tmp.h5',
                        help='Filename of the aggregate model')
    parser.add_argument('--crypt-aes-passwords', action='store', default={"testSender": "NULLPWD"},
                        help='Dictionary of {FileId:password} used for crypto')
    parser.add_argument('--crypt-aes-salts', action='store', default={"testSender": ""},
                        help='Dictionary of {FileId:salt} used for crypto')
    parser.add_argument('--crypt-select', action='store', default='plaintext',
                        help='Enable and select message encryption from ["plaintext", "AES"]')

    print(parser.parse_args())
    return parser.parse_args()


def main():
    global ARGUMENTS

    ARGUMENTS = argparsing()
    logging.basicConfig(filename=ARGUMENTS.logfile,
                        level=logging.INFO)

    # TODO not urgent, change the parameters to match the container name
    da_logfile = os.environ.get('DA_LOGFILE')
    da_client_model_prefix = os.environ.get('DA_CLIENT_MODEL_PREFIX')
    da_client_model_ext = os.environ.get('DA_CLIENT_MODEL_EXT')
    da_n_models = os.environ.get('DA_N_MODELS')
    da_avg_timeout = os.environ.get('DA_AVG_TIMEOUT')
    da_aggr_model = os.environ.get('DA_AGGR_MODEL')
    #
    # these may disappear with KAFKA removal
    da_broker = os.environ.get('DA_BROKER')
    da_groupid = os.environ.get('DA_GROUPID')
    da_msg_timeout = os.environ.get('DA_MSG_TIMEOUT')
    # communication via files - paths
    da_upward_path = os.environ.get('DA_UPWARD_PATH')
    da_downward_path = os.environ.get('DA_DOWNWARD_PATH')

    # da_crypt_select = os.environ.get('DA_CRYPT_SELECT')

    # fed_server = FederatedServer(testmode=ARGUMENTS.testmode,
    #                              num_msg=ARGUMENTS.n_models,
    #                              aggrfilename=ARGUMENTS.aggr_model,
    #                              client_model_ext=ARGUMENTS.client_model_ext,
    #                              client_model_prefix=ARGUMENTS.client_model_prefix,
    #                              broker_addr=ARGUMENTS.broker,
    #                              groupid=ARGUMENTS.groupid,
    #                              cryptselect=ARGUMENTS.crypt_select,
    #                              crypt_passwords=ARGUMENTS.crypt_aes_passwords,
    #                              crypt_salts=ARGUMENTS.crypt_aes_salts
    # )

    fed_server = FederatedServer(testmode=ARGUMENTS.testmode,
                                 num_msg=da_n_models,
                                 aggrfilename=da_aggr_model,
                                 client_model_ext=da_client_model_ext,
                                 client_model_prefix=da_client_model_prefix,
                                 broker_addr=da_broker,
                                 groupid=da_groupid,
                                 # cryptselect=da_crypt_select,
                                 # crypt_passwords=ARGUMENTS.crypt_aes_passwords,
                                 # crypt_salts=ARGUMENTS.crypt_aes_salts
                                 outgoing_path=da_downward_path
                                 )

    # fed_server.main_loop(msg_timeout=ARGUMENTS.msg_timeout)
    # fed_server.main_loop(msg_timeout=da_msg_timeout)

    my_watch_begins = FileWatchLoop(da_upward_path, fed_server)
    my_watch_begins.run()


if __name__ == "__main__":
    main()
