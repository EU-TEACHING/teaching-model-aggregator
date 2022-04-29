# Demo Testbed Configurations
Short memo of testing configurations for integration activities.

HW : Jetson Nano + ...

## at CNR
+ kafka broker on node247...
+ disable crypto on model aggregator (MA) and model transfer (MT)
+ TODO deploy MA on node247

where to deploy the MT?

we need to check the results of the aggregation go back successfully to the edge client

 + reenable crypto on MA and MT 
 + redeploy MA and MT
 + check that nothing breaks 

crypto will be an issue

### commands at CNR



## at HUA 
reconfigure the JNano on new address

model transfer will be on the IMX8

update docker files with new addresses of broker, aggregator, model transfer
