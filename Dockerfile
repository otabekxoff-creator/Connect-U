# MUAMMOLI VERSIYA:
# COPY requirements.txt /tmp/
# RUN pip install -r /tmp/requirements.txt

# TO'G'RI VERSIYA:
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt
WORKDIR /app
