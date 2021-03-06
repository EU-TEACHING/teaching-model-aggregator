# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Set parameters for the aggregation server
ENV DA_BROKER="127.0.0.1"
ENV DA_GROUPID="TEACHING"
ENV DA_N_MODELS=3
ENV DA_AVG_TIMEOUT=300
ENV DA_MSG_TIMEOUT=3
ENV DA_LOGFILE="FederatedServer.log"
ENV DA_CLIENT_MODEL_PREFIX="client_model"
ENV DA_CLIENT_MODEL_EXT="h5"
ENV DA_AGGR_MODEL="aggregate_model_tmp.h5"
# crypto disabled now
ENV DA_CRYPT_SELECT="plaintext"

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "/app/src/FederatedServer.py", "--testmode"]
