# Demo Testbed Configurations
Short memo of testing configurations for integration activities. Incomplete.

HW : Jetson Nano + ...

## at CNR
+ kafka broker on node247...
+ disable crypto on model aggregator (MA) and model transfer (MT)
+ TODO deploy MA on node247

where to deploy the MT? remote machine or on the Nano?

we need to check that the results of the aggregation return back successfully to the edge client

 + reenable crypto on MA and MT 
 + redeploy MA and MT
 + check that nothing breaks 

crypto will be an issue IMO

### commands at CNR
cd ~/teaching-model-aggregator

## at HUA 
reconfigure the JNano on new address

model transfer will be on the IMX8

update docker files with new addresses of broker, aggregator, model transfer
