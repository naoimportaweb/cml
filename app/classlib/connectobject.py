import sys, os, requests, json, uuid;
import json, hashlib;
import os, sys, inspect;
import os
import unicodedata
from Crypto.Cipher import AES
from base64 import b64decode,b64encode

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.server import Server;
from classlib.aes import AESHelper;
import base64;
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5

BLOCK_SIZE = 16
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]


#def aes_decript(key, encriptado):
#    encriptado = base64.b64decode(encriptado)
#    iv = encriptado[:16];
#    encriptado = encriptado[16:];
#    cipher = AES.new( key.encode() , AES.MODE_CBC, iv);
#    return unpad(cipher.decrypt( encriptado ));

#def aes_encript(key, raw):
#    raw = "12345678901234561234567890123456".encode();
#    #private_key = hashlib.sha256(password.encode("utf-8")).digest()
#    raw = pad(raw.decode()).encode();
#    iv = "1234567890123456".encode(); #Random.new().read(16);
#    cipher = AES.new(key.encode(), AES.MODE_CBC, iv);
#    return base64.b64encode(cipher.encrypt(raw));

class ConnectObject:
    def __init__(self):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        server = Server.instancia();
        self.ip = server.ip;
        self.port = server.port;
        self.protocol = server.protocol;
    
    def __execute__(self, class_name, method_name, parameters, crypto_v="000"):
        server = Server.instancia();
        if server.ip == "":
            return None;
        envelop = { "version" : "001", "class" : class_name, "method" :  method_name, "token" : "", "domain" : server.domain}
        if crypto_v == "000":
            envelop["parameters"] = "00000000" + json.dumps(parameters);
        elif crypto_v == "001":
            key = RSA.importKey( server.public_key );
            cipher = Cipher_PKCS1_v1_5.new(key)
            envelop["parameters"] = "00000001" +  base64.b64encode( cipher.encrypt(json.dumps(parameters).encode("utf-8"))).decode();
        #elif crypto_v == "002":
        #    envelop["parameters"] = "00000002" +  base64.b64encode(aes_encript(server.simetric_key ,json.dumps(parameters).encode("utf-8"))).decode();
        #    envelop["parameters"] = "00000002" + json.dumps(parameters);
        envelop["session"] = server.token;
        url = self.ip +"/cml/services/execute.php";
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'};
        #proxies = { 
        #      "http"  : "http://127.0.0.1:9051", 
        #      "https" : "http://127.0.0.1:9051"
        #};
        #r = requests.post(url, data=json.dumps(envelop), headers=headers, proxies=proxies);
        r = requests.post(url, data=json.dumps(envelop), headers=headers);
        #print(r.text.strip());
        try:
            retorno_json = json.loads(r.text.strip());
            if retorno_json["status"] == False or type(retorno_json["return"]) == None:
                raise Exception("Error:");
            if type(retorno_json["return"]) == type(""):
                retorno_body = retorno_json["return"][8:];
                retorno_json["return"] = json.loads(base64.b64decode( retorno_body ) );
            #    if retorno_body[: len("00000002")] == "00000002":
            #        encriptado = retorno_body[len("00000002"):];
            #        retorno_json["return"] = json.loads( aes_decript(server.simetric_key, encriptado) );
            return retorno_json;
        except:
            print("\033[95m", r.text.strip(), "\033[0m");
            return None;
    
    def __proxy__(self, class_name, method_name, parameters, crypto_v="000"):
        server = Server.instancia();
        if server.ip == "":
            return None;
        envelop = { "version" : "001", "class" : class_name, "method" :  method_name, "token" : "", "domain" : server.domain}
        envelop["parameters"] = "00000000" + json.dumps(parameters);
        envelop["session"] = server.token;
        url = self.ip +"/cml/services/federation_proxy.php";
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'};
        r = requests.post(url, data=json.dumps(envelop), headers=headers);
        #print(r.text.strip());
        try:
            retorno_json = json.loads(r.text.strip());
            if retorno_json["status"] == False or type(retorno_json["return"]) == None:
                raise Exception("Error:");
            if type(retorno_json["return"]) == type(""):
                retorno_body = retorno_json["return"][8:];
                retorno_json["return"] = json.loads(base64.b64decode( retorno_body ) );
            return retorno_json;
        except:
            print("\033[95m", r.text.strip(), "\033[0m");
            return None;