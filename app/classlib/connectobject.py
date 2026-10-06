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

DEPURAR = (os.environ.get("CML_DEBUG_RPC") or "").strip() not in ("", "0", "nao", "não", "false");
__SEGREDOS__ = ("session", "token", "password", "simetric_key");


def __mascarar__(valor, chave=None):
    """Troca o conteudo dos campos sensiveis por um aviso, mantendo a forma do envelope."""
    if isinstance(valor, dict):
        return {k: ("<omitido>" if k in __SEGREDOS__ and str(v or "") != "" else __mascarar__(v, k))
                for k, v in valor.items()};
    if isinstance(valor, list):
        return [__mascarar__(v) for v in valor];
    if chave == "parameters" and isinstance(valor, str) and len(valor) > 8:
        # 'parameters' e uma STRING com o prefixo de 8 caracteres e um JSON dentro -- e e ai
        # que a senha viaja. Mascarar so o nivel de cima deixava o segredo passar.
        prefixo, corpo = valor[:8], valor[8:];
        try:
            return prefixo + json.dumps(__mascarar__(json.loads(corpo)), ensure_ascii=False);
        except Exception:
            return prefixo + "<ilegível>";
    return valor;


def __registrar__(prefixo, conteudo):
    """O envelope so vai para a saida com CML_DEBUG_RPC ligado, e ainda assim MASCARADO.

    Antes isto era um print() direto do envelope inteiro: quem rodasse o cliente redirecionando
    a saida gravava em texto puro o TOKEN DE SESSAO e o valor de senha transmitido -- e, como o
    servidor compara esse valor direto com a coluna (session.php), ele e a propria credencial.
    Saida de depuracao nao pode custar a conta de quem depura."""
    if not DEPURAR:
        return;
    if isinstance(conteudo, str):
        try:
            conteudo = json.loads(conteudo);
        except Exception:
            pass;
    print(prefixo, __mascarar__(conteudo) if not isinstance(conteudo, str) else conteudo);


class ConnectObject:
    def __init__(self):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        server = Server.instancia();
        self.ip = server.ip;
        self.port = server.port;
        self.protocol = server.protocol;

    def __error__(self, mensagem):
        # Todo chamador faz js["status"] logo depois da chamada, entao a falha tem que
        # devolver um envelope com o mesmo formato do sucesso. Devolver None aqui
        # estoura TypeError no chamador e esconde a causa real.
        print("\033[95m", mensagem, "\033[0m");
        return { "status" : False, "return" : None, "error" : mensagem };

    def __execute__(self, class_name, method_name, parameters, crypto_v="000"):
        server = Server.instancia();
        if server.ip == "":
            return self.__error__("Servidor não configurado.");
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
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-Transfer-Encoding': 'chunked'};
        #proxies = { 
        #      "http"  : "http://127.0.0.1:9051", 
        #      "https" : "http://127.0.0.1:9051"
        #};
        #r = requests.post(url, data=json.dumps(envelop), headers=headers, proxies=proxies);
        __registrar__("-> ", envelop);
        # allow_redirects=False: seguir um 301 converte o POST em GET e o envelope se
        # perde. O servidor recebe corpo vazio e responde um erro de banco sem relacao
        # com a causa real (tipicamente http:// contra um host que so fala https).
        r = requests.post(url, data=json.dumps(envelop), headers=headers, allow_redirects=False);
        if r.is_redirect:
            return self.__error__("O servidor redirecionou " + url + " para " + r.headers.get("Location", "?") + ". Corrija a URL do servidor (verifique http/https).");
        __registrar__("<- ", r.text.strip());
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
            return self.__error__( r.text.strip() );
    
    def __proxy__(self, class_name, method_name, parameters, crypto_v="000"):
        server = Server.instancia();
        if server.ip == "":
            return self.__error__("Servidor não configurado.");
        envelop = { "version" : "001", "class" : class_name, "method" :  method_name, "token" : "", "domain" : server.domain}
        envelop["parameters"] = "00000000" + json.dumps(parameters);
        envelop["session"] = server.token;
        url = self.ip +"/cml/services/federation_proxy.php";
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'};
        r = requests.post(url, data=json.dumps(envelop), headers=headers, allow_redirects=False);
        if r.is_redirect:
            return self.__error__("O servidor redirecionou " + url + " para " + r.headers.get("Location", "?") + ". Corrija a URL do servidor (verifique http/https).");
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
            return self.__error__( r.text.strip() );