from pathlib import Path

import numpy as np

from tensorflow import keras

import tensorflow as tf
import tensorflow_datasets as tfds


class KafkaTopics(object):
    # as of now, the clients will use the first element of the list
    CLIENT_MODEL_TOPIC = 'TopicNum'
    FEDERATED_MODEL_TOPIC = 'FederatedModel'


class KafkaConfig(object):
    FED_KAFKA_BROKER_URL = "node247-hpc.isti.cnr.it:9092"
    FED_KAFKA_BROKER_groupid = "foo"


#    FED_READ_TIMEOUT = 1.0
#    CLIENT_READ_TIMEOUT = 0.0

def create_teaching_model_structure():
    return tf.keras.models.Sequential([
        tf.keras.layers.Flatten(input_shape=(28, 28)),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(10)
    ])


def compile_teaching_model(model):
    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )

# this is only to be used in internal testing as of integration meeting 3
def evaluate_teaching_model(model, ds_test=None):
    if ds_test is None:
        (ds_train, ds_test), ds_info = tfds.load(
            'mnist',
            split=['train', 'test'],
            shuffle_files=True,
            as_supervised=True,
            with_info=True,
        )

        def normalize_img(image, label):
            """Normalizes images: `uint8` -> `float32`."""
            return tf.cast(image, tf.float32) / 255., label

        ds_test = ds_test.map(normalize_img, num_parallel_calls=tf.data.AUTOTUNE)
        ds_test = ds_test.batch(128)
        ds_test = ds_test.cache()
        ds_test = ds_test.prefetch(tf.data.AUTOTUNE)

    model.evaluate(ds_test)


# create a model from the weights of multiple models
def model_weight_ensemble(members):
    # determine how many layers need to be averaged
    n_layers = len(members[0].get_weights())

    # create an set of average model weights
    avg_model_weights = list()

    for layer in range(n_layers):
        # collect this layer from each model
        layer_weights = np.array([model.get_weights()[layer] for model in members])

        # weighted average of weights for this layer
        avg_layer_weights = np.average(layer_weights, axis=0)

        # store average layer weights
        avg_model_weights.append(avg_layer_weights)

    # create a new model with the same structure
    model = keras.models.clone_model(members[0])

    # set the weights in the new
    model.set_weights(avg_model_weights)

    compile_teaching_model(model)
    return model


# you need to explicitly add a path prefix to the filename to manage a separate save directory
def write_modelfile(filename, data):
    p = Path(filename)
    p.write_bytes(data)


def read_modelfile(aggregate_filename):
    return Path(aggregate_filename).read_bytes()
