import sys, os, requests, json, uuid;
import json, hashlib;
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.server import Server;
import base64;
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5

class ConnectObject:
    def __init__(self):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        server = Server();
        self.ip = server.ip;
        self.port = server.port;
        self.protocol = server.protocol;
    
    def __execute__(self, class_name, method_name, parameters, crypto_v="000"):
        envelop = { "version" : "001", "class" : class_name, "method" :  method_name, "token" : ""}
        if crypto_v == "000":
            envelop["parameters"] = "00000000" + json.dumps(parameters);
        elif crypto_v == "001":
            server = Server();
            key = RSA.importKey( server.public_key );
            cipher = Cipher_PKCS1_v1_5.new(key)
            envelop["parameters"] = "00000001" +  base64.b64encode( cipher.encrypt(json.dumps(parameters).encode("utf-8"))).decode();
        url = self.protocol + "://"+ self.ip +":"+ str(self.port) +"/cml/services/execute.php";
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'};
        r = requests.post(url, data=json.dumps(envelop), headers=headers);
        print("RETURN:", r.text);
        return json.loads(r.text);