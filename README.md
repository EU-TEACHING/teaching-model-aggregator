# TEACHING Model Aggregator
Teaching Model Aggregator, or Model Aggregation service.

This software manages the aggregation of model weights retrieved from the neural networks built by client (vehicles) within the TEACHING platform.

Written by Patrizio Dazzi, Massimo Coppola (ISTI-CNR)

# Instructions

## Development notes
 - _The first version of this code was named Data Aggregator,  **DA\_** prefixed variable are still in the code_
 - Federated Server haD a bunch of command line args.
Most of them are now superseded by corresponding ENV variables and ignored. 
A few remain as launch-time parameters (e.g. `--testmode` ), and some of those are still unimplemented.
See within FederatedServer.py main function.
 - The main branch in git uses Kafka libraries to interface directly to the Kafka broker. This version has incomplete crypto support that can be disabled via environment vars.
 - The new version (currently a repo branch) interfaces to the Model Transfer Service container via a shared storage volume and file monitoring. The MTS thus handles Kafka as well as model data encryption/decryption.

## How to build
Assuming all the GitHub folder was downloaded or copied in **teaching-model-aggregator-master** . 
The following creates an image named **teaching_aggregator**

`docker build -t teaching_aggregator teaching-model-aggregator-master/`

## Hacking notes
Hints about how to install tensorflow on the NVIDIA Jetson Nano
https://pulsebit.wordpress.com/2021/06/03/installing-tensorflow-on-jetson-nano/
https://forums.developer.nvidia.com/t/official-tensorflow-for-jetson-nano/71770

Latest issue with the JN was an incompatibility between the tensorflow and Confluent Kafka dependencies. Should be solved by splitting the MAS and the MTS in two separate containers and removing Kafka from MAS requirements.

TO DO : commit to repo the JN Dockerfile.

## How to launch - local volume interfacing example
When using the test configuration on the JN node247-hpc under the *coppola* account

`docker run --volume=/home/coppola/teaching-test/shared_storage:/shared_storage  teaching_aggregator:latest`

## How to launch - Kafka interface example
Example of how to run the image, overriding the DA_BROKER env variable
    
`docker run -e "DA_BROKER=146.48.80.10" teaching_aggregator:latest`
