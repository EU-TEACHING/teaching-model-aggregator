# DataAggregator
Teaching Data Aggregator

This software manages the aggregation of weigths retrieved from the neural networks built by vehicles of TEACHING project.



# Instructions
Federated Server has a bunch of comand line args.
Most of them are now superseded by corresponding ENV variables. A few remain as lauch parameters, and some of those are still unimplemented.
See within FederatedServer.py main function.

## To build
Assuming all the github folder was downloaded. 
The following creates an image named TEACHING

`docker build -t teaching_aggregator teaching-model-aggregator-master/`

## Hacks
How to install tensorflow on the J Nano
https://pulsebit.wordpress.com/2021/06/03/installing-tensorflow-on-jetson-nano/

https://forums.developer.nvidia.com/t/official-tensorflow-for-jetson-nano/71770

## How to launch - example
Example of how to run the image, overriding the DA_BROKER env variable

`docker run -e "DA_BROKER=146.48.80.10" teaching_aggregator:latest`
